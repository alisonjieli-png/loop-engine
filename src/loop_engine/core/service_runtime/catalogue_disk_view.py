"""A served catalogue view whose search index and item descriptors stay on disk (engine `sqlite_disk_index`).

The view the in-memory engine serves holds, for every item, the catalogue item,
its binding, package, attributes, approval and item version: about 4.2
kilobytes an item beside the 3.2 kilobytes of its index, measured on October 5,
2026. This view holds none of them. It answers the same `CatalogueView`
questions from one disk index (or an overlay of a base index and a small delta),
reading the stored item record of an identity when a request asks about it and
keeping a bounded cache of the records it read recently.

```text
<index_root>
├── indexes/<name>/            immutable disk indexes (catalogue_disk_index)
└── releases/<release_id>.json catalogue_disk_index_overlay/v1: which index serves a release
    ├── base                   a full index of some release
    ├── delta                  an index of the items added or changed since that release, or null
    └── removed                the identities whose base record the release no longer serves as it is
```

A full build reads every item record of the release once, applies the same
family, licence, attribute and tier rules as the in-memory view, reads and
checks every body, and writes the index. A release that shares segments with
the release of an existing full index gets an overlay instead: only the items
in segments the two releases do not share are read, checked and indexed, so
the work follows the change rather than the library. An overlay past
`OVERLAY_REBUILD_FRACTION` of its base is replaced by a full build.

A durable withdrawal recorded after an index was built is honoured without a
rebuild: the view leaves the identity out of every lookup, so search never
returns it and every read refuses it, and the body reader still checks the
withdrawal record first, as the in-memory view does.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import hashlib
import heapq
import json
from pathlib import Path
import threading
import time

from ..harness_intelligence import HarnessIntelligenceCatalogue
from ..provisioning_server import RUNNABLE_EFFECT, ProvisioningItemBinding, ProvisioningQualification
from .catalogue_disk_index import OVERLAY_FORMAT, DiskIndex, DiskSearchIndex, build_disk_index
from .catalogue_packages import FILE_BODY, CataloguePackage
from .catalogue_serving import STORE_RESOLVER_ID, STORE_SOURCE, CatalogueView, _approved_resolver, _withdrawal_check
from .records import ServiceRuntimeError
from .storage import ServiceCatalogBinding

INDEXES_FOLDER, RELEASES_FOLDER = "indexes", "releases"
#: Item records a view keeps parsed in memory, most recently used first.
RECORD_CACHE = 4096


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def policy_fingerprint(license_policy, family_policy):
    """The host rules an index was built under; an index built under other rules is never served."""
    value = {"licences": sorted(getattr(license_policy, "accepted_licenses", ()) or ()),
             "families": sorted(getattr(family_policy, "accepted_families", ()) or ()),
             "licence_record": getattr(license_policy, "record_type", ""),
             "family_record": getattr(family_policy, "record_type", "")}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class DiskItem:
    """Everything a view answers about one served item, parsed once from its stored record."""

    item: object
    package: CataloguePackage
    attributes: dict
    binding: ProvisioningItemBinding
    approval: ProvisioningQualification
    version: str


def _disk_item(record, version, schema, license_policy, family_policy):
    """Apply the in-memory view's rules to one stored item record and return what the view serves of it."""
    from ..practitioner_runtime.provisioning import _item
    from .catalogue_bundle import item_version_tier, validated_attributes
    item = _item(record["reference"])
    package = CataloguePackage.from_dict(record["package"])
    if license_policy is not None:
        refused = family_policy.refusal(item.family) or license_policy.refusal(item.license_name)
        if refused:
            _refuse(refused, "the host family or licence policy refuses an item of the active release")
    if item.digest != package.served_digest or item.size_bytes != package.served_size:
        _refuse("catalogue_release_digest_mismatch", "an item reference names other bytes than its package")
    tier = item_version_tier(record)
    values = validated_attributes(schema, record["attributes"]) if schema is not None else record["attributes"]
    exact = ProvisioningItemBinding.from_item(item)
    approval = ProvisioningQualification(exact, "approved", "host_attested", record["approval_ref"], tier)
    return DiskItem(item, package, values, exact, approval, version)


class DiskItemSource:
    """identity -> served item, read from a base index, its removed identities and a delta index, never held whole."""

    def __init__(self, base, delta=None, removed=frozenset(), left_out=frozenset(), *, schema=None,
                 population=None):
        self.base, self.delta = base, delta
        self.removed, self.left_out = frozenset(removed), frozenset(left_out)
        self.schema = schema
        self._population = population
        self._cache, self._lock = OrderedDict(), threading.Lock()
        self._size = (base.size - len(self.removed) + (delta.size if delta is not None else 0)) - len(self.left_out)

    def with_left_out(self, more):
        """The same source with more identities left out; the index files are shared."""
        return DiskItemSource(self.base, self.delta, self.removed, self.left_out | frozenset(more), schema=self.schema)

    def lookup_many(self, identities):
        """identity -> DiskItem for the identities this source serves; others are absent."""
        found, missing = {}, []
        with self._lock:
            for identity in identities:
                if identity in self.left_out:
                    continue
                held = self._cache.get(identity)
                if held is not None:
                    self._cache.move_to_end(identity)
                    found[identity] = held
                else:
                    missing.append(identity)
        if missing:
            rows = self.delta.records(missing) if self.delta is not None else {}
            rest = [identity for identity in missing if identity not in rows and identity not in self.removed]
            rows.update(self.base.records(rest) if rest else {})
            parsed = {}
            for identity, (_position, version, record) in rows.items():
                parsed[identity] = _disk_item(json.loads(record), version, None, None, None)
            with self._lock:
                for identity, value in parsed.items():
                    self._cache[identity] = value
                    self._cache.move_to_end(identity)
                while len(self._cache) > RECORD_CACHE:
                    self._cache.popitem(last=False)
            found.update(parsed)
        return found

    def lookup(self, identity):
        return self.lookup_many((identity,)).get(identity)

    def __len__(self):
        return self._size

    def __iter__(self):
        base = (identity for identity in self.base.iter_identities() if identity not in self.removed)
        streams = [base] + ([self.delta.iter_identities()] if self.delta is not None else [])
        for identity in heapq.merge(*streams):
            if identity not in self.left_out:
                yield identity

    def population(self):
        """The distinct delivered files of the served items: the base's counts, adjusted exactly for the removed,
        left-out and delta items by the base's per-file reference counts. Reads only those items."""
        if self._population is None:
            self._population = _population(self.base, self.delta, self.removed, self.left_out)
        return dict(self._population)


class DiskMapping(Mapping):
    """A read-only mapping over a `DiskItemSource`, projecting each served item to one of its parts."""

    def __init__(self, source, part):
        self.source, self.part = source, part

    def __getitem__(self, identity):
        found = self.source.lookup(identity) if isinstance(identity, str) else None
        if found is None:
            raise KeyError(identity)
        return getattr(found, self.part)

    def get(self, identity, default=None):
        found = self.source.lookup(identity) if isinstance(identity, str) else None
        return getattr(found, self.part) if found is not None else default

    def __contains__(self, identity):
        return isinstance(identity, str) and self.source.lookup(identity) is not None

    def __len__(self):
        return len(self.source)

    def __iter__(self):
        return iter(self.source)


@dataclass(frozen=True)
class DiskCatalogueView(CatalogueView):
    """A `CatalogueView` whose per-item parts are read from disk on demand."""

    disk: object = field(default=None, repr=False, compare=False)

    def file_population(self):
        population = self.disk.population()
        if not population:
            return super().file_population()
        return dict(population)

    def served_package_count(self):
        return len(self.disk)

    def without(self, withdrawn, *, state_revision, notes=None):
        """A new view leaving out every durably withdrawn item it serves; the index files are shared."""
        newly = set()
        for identity, digest in withdrawn:
            found = self.disk.lookup(identity)
            if found is not None and found.binding.body_digest == digest:
                newly.add(identity)
        source = self.disk.with_left_out(newly)
        left_out = frozenset((identity, digest) for identity, digest in withdrawn if identity in newly)
        return _view_over(source, self, withdrawn=self.withdrawn | left_out, state_revision=state_revision,
                          withdrawal_notes={**self.withdrawal_notes,
                                            **{key: value for key, value in (notes or {}).items() if key in withdrawn}})


def _view_over(source, template, **changes):
    resolver = _approved_resolver(STORE_RESOLVER_ID, DiskMapping(source, "approval"))
    packages = DiskMapping(source, "package")
    body_store, check = template.body_store, template.withdrawal_check

    def reader(item):
        package = packages[item.identity]
        if check is not None:
            check(item.identity, package.served_digest)
        if package.body_form == FILE_BODY:
            entry = package.files[0]
            return body_store.read(entry.digest, entry.size_bytes).decode("utf-8")
        return package.document().decode("utf-8")
    return replace(template, catalogue=HarnessIntelligenceCatalogue(DiskMapping(source, "item")),
                   qualification_resolver=resolver, body_reader=reader, packages=packages,
                   attributes=DiskMapping(source, "attributes"), bindings=DiskMapping(source, "binding"),
                   item_versions=DiskMapping(source, "version"), disk=source, built_at=time.time(), _lazy={},
                   **changes)


# ---------------------------------------------------------------------------
# Building and opening the index of a release
# ---------------------------------------------------------------------------

def _excluded(binding, store, header, withdrawn, read_segment):
    """The (identity, body digest) pairs of the release whose listed item version was durably withdrawn: the
    in-memory view leaves them out, and so does the index build. Reads one segment and one record per withdrawal,
    not the release."""
    from .catalogue_releases import load_item_version
    excluded = set()
    for identity, digest in withdrawn:
        version = header.version_of(identity, read_segment)
        if version is None:
            continue
        record = load_item_version(binding, store, identity, version)
        if CataloguePackage.from_dict(record["package"]).served_digest == digest:
            excluded.add((identity, digest))
    return excluded


def _pairs(binding, store, header, read_segment):
    from .catalogue_segments import SegmentedRelease
    return header.entries(read_segment) if isinstance(header, SegmentedRelease) else iter(header.items)


def _rows(binding, store, pairs, schema, excluded, license_policy, family_policy, body_store, verify_bodies):
    """(IndexEntry, version, record) for every served pair, with the in-memory view's rules, as a stream."""
    from .catalogue_releases import load_item_version
    from .catalogue_search import IndexEntry, entry_text
    for identity, version in pairs:
        if identity in excluded:
            continue
        record = load_item_version(binding, store, identity, version)
        served = _disk_item(record, version, schema, license_policy, family_policy)
        if verify_bodies:
            for file in served.package.files:
                data = body_store.read(file.digest, file.size_bytes)
                if served.package.body_form == FILE_BODY:
                    try:
                        data.decode("utf-8")
                    except UnicodeDecodeError:
                        _refuse("package_file_not_text", "the file body form serves UTF-8 text only")
        entry = IndexEntry(identity, entry_text(served.item, schema.search_text(served.attributes)), served.attributes,
                           served.approval.library_tier, RUNNABLE_EFFECT in served.item.declared_effects)
        yield entry, version, record


def _descriptor_path(root, release_id):
    return Path(root) / RELEASES_FOLDER / f"{release_id}.json"


def _write_descriptor(root, release_id, value):
    folder = Path(root) / RELEASES_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / f".{release_id}.json.partial"
    partial.write_text(json.dumps(value, sort_keys=True, indent=1))
    partial.replace(folder / f"{release_id}.json")


def _read_descriptor(root, release_id):
    try:
        value = json.loads(_descriptor_path(root, release_id).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or value.get("record_type") != OVERLAY_FORMAT:
        return None
    return value


def _overlay_base(root, header, fingerprint, schema_digest):
    """The newest full index of a version 2 release with the same schema and rules, to build an overlay on."""
    from .catalogue_segments import SegmentedRelease
    if not isinstance(header, SegmentedRelease):
        return None
    candidates = []
    for path in (Path(root) / RELEASES_FOLDER).glob("*.json"):
        try:
            value = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if (isinstance(value, dict) and value.get("record_type") == OVERLAY_FORMAT and value.get("delta") is None
                and value.get("policy_fingerprint") == fingerprint and value.get("schema_digest") == schema_digest
                and value.get("segments") and value.get("segmentation") == header.segmentation.to_dict()):
            candidates.append((value.get("built_at", 0), value))
    return max(candidates, key=lambda row: row[0])[1] if candidates else None


def ensure_release_index(config, settings, *, license_policy, family_policy, verify_bodies=True, clock=time.time):
    """Open the disk index of the active release, building a full index or an overlay when none exists yet.

    Returns `(header, descriptor, state)` for the release the pointer names. The build reads the release through
    the same verified readers as the in-memory view and writes nothing to the service store.
    """
    from .catalogue_packages import VolumeBodyStore, require_body_store
    from .catalogue_releases import (load_release_header, read_pointer, read_state, segment_reader,
                                     withdrawal_keys)
    from .catalogue_segments import SegmentedRelease
    root = Path(settings.index_root)
    binding = ServiceCatalogBinding(config)
    body_store = require_body_store(VolumeBodyStore(settings.body_store_root))
    fingerprint = policy_fingerprint(license_policy, family_policy)
    with binding.store() as store:
        _state_row, state = read_state(binding, store)
        _pointer_row, pointer = read_pointer(binding, store)
        if pointer is None:
            _refuse("catalogue_release_not_published", "the store source needs a published release")
        header = load_release_header(binding, store, pointer["release_id"])
        held = _read_descriptor(root, header.release_id)
        if held is not None and held.get("policy_fingerprint") == fingerprint:
            return header, held, state
        read_segment = segment_reader(binding, store)
        withdrawn = withdrawal_keys(binding, store)
        excluded_pairs = _excluded(binding, store, header, withdrawn, read_segment)
        excluded = {identity for identity, _digest in excluded_pairs}
        content = header.content_digest
        base = _overlay_base(root, header, fingerprint, header.schema.digest)
        descriptor = None
        if base is not None:
            descriptor = _build_overlay(root, binding, store, header, base, excluded_pairs, read_segment,
                                        license_policy, family_policy, body_store, verify_bodies, fingerprint, clock)
        if descriptor is None:
            name = f"full-{header.release_id[:16]}-{fingerprint[:8]}-{int(clock())}"
            count = (header.item_count if isinstance(header, SegmentedRelease) else len(header.items)) - len(excluded)
            build_disk_index(root / INDEXES_FOLDER / name,
                             _rows(binding, store, _pairs(binding, store, header, read_segment), header.schema,
                                   excluded, license_policy, family_policy, body_store, verify_bodies),
                             header.schema, count=count, release_id=header.release_id, content_digest=content,
                             policy_fingerprint=fingerprint)
            descriptor = {"record_type": OVERLAY_FORMAT, "release_id": header.release_id, "content_digest": content,
                          "base": name, "delta": None, "removed": [],
                          "excluded": sorted([identity, digest] for identity, digest in excluded_pairs),
                          "policy_fingerprint": fingerprint, "schema_digest": header.schema.digest,
                          "segmentation": (header.segmentation.to_dict() if isinstance(header, SegmentedRelease)
                                           else None),
                          "segments": ([ref.digest for ref in header.segments]
                                       if isinstance(header, SegmentedRelease) else None),
                          "built_at": clock()}
    _write_descriptor(root, header.release_id, descriptor)
    return header, descriptor, state


def _build_overlay(root, binding, store, header, base, excluded_pairs, read_segment, license_policy, family_policy,
                   body_store, verify_bodies, fingerprint, clock):
    """An overlay of `header` on the full index of an earlier release, or None when a full build is cheaper."""
    from .catalogue_segments import segment_entries
    excluded = {identity for identity, _digest in excluded_pairs}
    shared = set(base["segments"]) & {ref.digest for ref in header.segments}
    old, new = {}, {}
    for digest in base["segments"]:
        if digest not in shared:
            old.update(segment_entries(read_segment(digest), digest))
    for ref in header.segments:
        if ref.digest not in shared:
            new.update(segment_entries(read_segment(ref.digest), ref.digest))
    base_excluded = {identity for identity, _digest in base.get("excluded", ())}
    delta = sorted((identity, version) for identity, version in new.items()
                   if old.get(identity) != version and identity not in excluded)
    # A base record leaves the served set when the new release drops or changes it, or a withdrawal now excludes it.
    removed = sorted((set(old) - set(new)) | {identity for identity, _version in delta if identity in old}
                     | {identity for identity in excluded if identity not in base_excluded})
    from . import catalogue_disk_index
    base_index = DiskIndex(Path(root) / INDEXES_FOLDER / base["base"])
    if base_index.size < catalogue_disk_index.OVERLAY_MINIMUM_BASE:
        return None
    # Only identities the base index holds can be removed from it.
    removed = sorted(base_index.positions_of([identity for identity in removed if identity not in base_excluded]))
    if len(delta) + len(removed) > catalogue_disk_index.OVERLAY_REBUILD_FRACTION * max(1, base_index.size):
        return None
    name = f"delta-{header.release_id[:16]}-{fingerprint[:8]}-{int(clock())}"
    build_disk_index(root / INDEXES_FOLDER / name,
                     _rows(binding, store, iter(delta), header.schema, excluded, license_policy, family_policy,
                           body_store, verify_bodies),
                     header.schema, count=len(delta), release_id=header.release_id,
                     content_digest=header.content_digest, policy_fingerprint=fingerprint, note=f"delta on {base['base']}")
    return {"record_type": OVERLAY_FORMAT, "release_id": header.release_id, "content_digest": header.content_digest,
            "base": base["base"], "delta": name, "removed": removed,
            "excluded": sorted([identity, digest] for identity, digest in excluded_pairs),
            "policy_fingerprint": fingerprint, "schema_digest": header.schema.digest,
            "segmentation": header.segmentation.to_dict(), "segments": [ref.digest for ref in header.segments],
            "base_release_id": base["release_id"], "built_at": clock()}


def _population(base, delta, removed, left_out):
    """The served file population of a base index with removed, left-out and delta items, from the base's
    reference counts, exactly, reading only those items' records."""
    population = dict(base.marker["population"])
    if delta is None and not removed and not left_out:
        return _population_record(population)
    dropped = base.records(sorted(set(removed) | set(left_out)))
    removed_records = [json.loads(record) for _position, _version, record in dropped.values()]
    drop = {}
    for record in removed_records:
        for file in record["package"]["files"]:
            drop[file["digest"]] = drop.get(file["digest"], 0) + 1
    add, added_packages = {}, 0
    if delta is not None:
        connection = delta.connection()
        for identity, record in connection.execute("SELECT identity, record FROM entries"):
            if identity in left_out:
                continue
            added_packages += 1
            for file in json.loads(record)["package"]["files"]:
                held = add.setdefault(file["digest"], [file["size_bytes"], 0])
                held[1] += 1
    refs = base.file_refs(list(drop) + list(add))
    distinct, distinct_bytes = population["distinct_files"], population["distinct_file_bytes"]
    for digest, count in drop.items():
        size, held = refs[digest]
        if held - count <= 0 and digest not in add:
            distinct, distinct_bytes = distinct - 1, distinct_bytes - size
    for digest, (size, count) in add.items():
        held = refs.get(digest, (size, 0))[1] - drop.get(digest, 0)
        if held <= 0:
            distinct, distinct_bytes = distinct + 1, distinct_bytes + size
    placements = (population["file_placements"] - sum(drop.values())
                  + sum(count for _size, count in add.values()))
    packages = population["packages"] - len(removed_records) + added_packages
    return _population_record({"packages": packages, "file_placements": placements, "distinct_files": distinct,
                               "distinct_file_bytes": distinct_bytes,
                               "packages_without_file_manifest": population["packages_without_file_manifest"]})


def _population_record(value):
    complete = not value["packages_without_file_manifest"]
    return {"record_type": "catalogue_file_population/v1", "packages": value["packages"],
            "file_placements": value["file_placements"],
            "distinct_files": value["distinct_files"] if complete else None,
            "observed_distinct_files": value["distinct_files"],
            "distinct_file_bytes": value["distinct_file_bytes"] if complete else None,
            "duplicate_file_placements": value["file_placements"] - value["distinct_files"],
            "packages_without_file_manifest": value["packages_without_file_manifest"], "complete": complete}


def disk_store_view(config, settings, *, license_policy, family_policy, verify_bodies=True):
    """The served view of the active release over its disk index, building the index when none exists yet."""
    from .catalogue_packages import VolumeBodyStore, require_body_store
    from .catalogue_releases import withdrawal_notes
    header, descriptor, state = ensure_release_index(config, settings, license_policy=license_policy,
                                                     family_policy=family_policy, verify_bodies=verify_bodies)
    root = Path(settings.index_root)
    base = DiskIndex(root / INDEXES_FOLDER / descriptor["base"])
    delta = DiskIndex(root / INDEXES_FOLDER / descriptor["delta"]) if descriptor["delta"] else None
    if base.marker.get("policy_fingerprint") != policy_fingerprint(license_policy, family_policy):
        _refuse("search_index_unavailable", "the disk index was built under other host rules")
    removed_rows = base.records(sorted(descriptor["removed"]))
    removed = frozenset(removed_rows)
    binding = ServiceCatalogBinding(config)
    with binding.store() as store:
        from .catalogue_releases import segment_reader
        notes = withdrawal_notes(binding, store)
        read_segment = segment_reader(binding, store)
        in_release = {key for key in notes if header.version_of(key[0], read_segment) is not None}
    source = DiskItemSource(base, delta, removed, schema=header.schema)
    left_out, left_out_keys = set(), set()
    for identity, digest in notes:
        found = source.lookup(identity)
        if found is not None and found.binding.body_digest == digest:
            left_out.add(identity)
            left_out_keys.add((identity, digest))
    source = source.with_left_out(left_out)
    excluded_keys = {tuple(pair) for pair in descriptor.get("excluded", ())}
    index = DiskSearchIndex(base, header.schema, removed=frozenset(position for position, _v, _r
                                                                   in removed_rows.values()), delta=delta)
    body_store = require_body_store(VolumeBodyStore(settings.body_store_root))
    template = CatalogueView(HarnessIntelligenceCatalogue(), _approved_resolver(STORE_RESOLVER_ID, {}), None,
                             source=STORE_SOURCE, release_id=header.release_id,
                             content_digest=header.content_digest, schema=header.schema,
                             withdrawal_check=_withdrawal_check(config), body_store=body_store, index=index,
                             state_revision=state["revision"] if state else 0,
                             changes=dict(header.document.get("changes") or {}),
                             withdrawal_notes={key: value for key, value in notes.items() if key in in_release})
    template = DiskCatalogueView(**{name: getattr(template, name) for name in template.__dataclass_fields__})
    return _view_over(source, template, withdrawn=frozenset(left_out_keys) | frozenset(excluded_keys))
