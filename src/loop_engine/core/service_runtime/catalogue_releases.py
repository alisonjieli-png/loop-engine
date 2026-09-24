"""Catalogue releases, the active release pointer and durable withdrawals.

These records live in the existing service store, through the same scoped
binding and atomic batch contract as every other service record, so no second
store or source of truth is created. A release is content-addressed like an
image index: it lists each item identity with the digest of its immutable item
version, the digest of its attribute schema, and what it added, changed and
withdrew relative to the release it was built on.

```text
Catalogue state in the service store
├── catalogue_state/v1              one marker; its state version gates every image at start
├── catalogue_attribute_schema/v1   one record for each schema digest
├── catalogue_item_version/v1       one immutable record for each verified item version digest
├── catalogue_item_version/v2       the same for a community item version, with its admission
├── catalogue_release/v1            one record for each release digest
├── catalogue_release_pointer/v1    the active release, moved only under an expected-version guard
└── catalogue_withdrawal/v1         one durable record for each withdrawn identity and body digest
```

A partial publish is never active: bodies and immutable records are written
first, and the release record, the pointer move, the withdrawals and the
marker commit together in one atomic batch. A withdrawal is honoured by every
later release, every rollback and every image that understands the marker. An
image that does not understand the marker's state version refuses to start.

The marker's state version is 1 until a release names a community item
version. That publish writes state version 2, and no later write lowers it, so
an image that cannot tell a community item from a verified one refuses to
start against the store instead of serving the community item as reviewed.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

from .catalogue_bundle import ITEM_VERSION_RECORD_TYPES, canonical_bytes, note
from .catalogue_packages import CataloguePackage, sha256_hex
from .catalogue_schema import CatalogueAttributeSchema
from .records import ServiceRuntimeError, identifier
from .storage import ServiceCatalogBinding

STATE_KIND, SCHEMA_KIND, ITEM_KIND, RELEASE_KIND, POINTER_KIND, WITHDRAWAL_KIND = (
    "service_catalogue_state", "service_catalogue_schema", "service_catalogue_item",
    "service_catalogue_release", "service_catalogue_pointer", "service_catalogue_withdrawal")
STATE_RECORD_TYPE = "catalogue_state/v1"
RELEASE_RECORD_TYPE = "catalogue_release/v1"
POINTER_RECORD_TYPE = "catalogue_release_pointer/v1"
WITHDRAWAL_RECORD_TYPE = "catalogue_withdrawal/v1"
STATUS_RECORD_TYPE = "service_catalogue_status/v1"
OPERATION_RECORD_TYPE = "service_catalogue_operation/v1"
#: The catalogue state this release writes. A later release that adds a record
#: an older image must not ignore writes a higher state version, and every
#: image refuses to start against a state version it does not list here.
CATALOGUE_STATE_VERSION = 1
#: Written by the first publish of a release that names a community item
#: version, and never lowered afterwards.
COMMUNITY_STATE_VERSION = 2
SUPPORTED_CATALOGUE_STATE_VERSIONS = (1, 2)
STATE_LOGICAL, POINTER_LOGICAL = "catalogue", "active"
#: Immutable records are written in batches of this size before the release is
#: committed, so a large first release does not hold one enormous batch.
WRITE_CHUNK = 500
MOVES = ("publish", "rollback")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def release_digest(document):
    """The release identity: the digest of its canonical content without its own name and time."""
    return sha256_hex(canonical_bytes({key: value for key, value in document.items()
                                       if key not in ("release_id", "published_at")}))


def content_digest(schema_digest, items):
    """What a release serves: its schema and its exact item versions, and nothing else."""
    return sha256_hex(canonical_bytes({"schema_digest": schema_digest, "items": [list(row) for row in items]}))


@dataclass(frozen=True)
class LoadedRelease:
    """One verified release: its document, schema and item versions in identity order."""

    release_id: str
    document: dict
    schema: CatalogueAttributeSchema
    versions: tuple

    @property
    def items(self):
        return tuple((row["reference"]["identity"], digest) for digest, row in self.versions)


def _payload(binding, store, kind, logical, record_type):
    row = binding.read(store, kind, logical)
    if row is None:
        return None, None
    payload = row["payload"]
    accepted = record_type if isinstance(record_type, tuple) else (record_type,)
    if payload.get("record_type") not in accepted:
        _refuse("catalogue_record_unsupported", f"a {kind} record is not one of {accepted}")
    return row, payload


def read_state(binding, store):
    """Return the marker row and payload, refusing a state version this image does not understand."""
    row = binding.read(store, STATE_KIND, STATE_LOGICAL)
    if row is None:
        return None, None
    payload = row["payload"]
    if (payload.get("record_type") != STATE_RECORD_TYPE
            or payload.get("state_version") not in SUPPORTED_CATALOGUE_STATE_VERSIONS):
        _refuse("catalogue_state_version_unsupported",
                "the service store holds catalogue state this release does not understand; "
                "deploy a release that understands it")
    return row, payload


def read_pointer(binding, store):
    return _payload(binding, store, POINTER_KIND, POINTER_LOGICAL, POINTER_RECORD_TYPE)


def withdrawal_keys(binding, store):
    """Every durable withdrawal as (identity, body digest). An unknown record version refuses."""
    keys = set()
    for row in binding.rows_all(store, WITHDRAWAL_KIND):
        payload = row["payload"]
        if payload.get("record_type") != WITHDRAWAL_RECORD_TYPE:
            _refuse("catalogue_record_unsupported", f"a withdrawal record is not {WITHDRAWAL_RECORD_TYPE}")
        keys.add((payload["identity"], payload["body_digest"]))
    return frozenset(keys)


def is_withdrawn(binding, store, identity, body_digest):
    row = binding.read(store, WITHDRAWAL_KIND, (identity, body_digest))
    if row is not None and row["payload"].get("record_type") != WITHDRAWAL_RECORD_TYPE:
        _refuse("catalogue_record_unsupported", f"a withdrawal record is not {WITHDRAWAL_RECORD_TYPE}")
    return row is not None


def load_release(binding, store, release_id):
    """Read one release and every record it names, verifying each digest."""
    row, document = _payload(binding, store, RELEASE_KIND, release_id, RELEASE_RECORD_TYPE)
    if document is None:
        _refuse("catalogue_release_not_found", "the store holds no release with that identity")
    if document.get("release_id") != release_id or release_digest(document) != release_id:
        _refuse("catalogue_release_digest_mismatch", "the release record differs from its digest")
    _schema_row, schema_payload = _payload(binding, store, SCHEMA_KIND, document["schema_digest"],
                                           "catalogue_attribute_schema/v1")
    if schema_payload is None:
        _refuse("catalogue_release_incomplete", "the release names a schema the store does not hold")
    schema = CatalogueAttributeSchema.from_dict(schema_payload)
    if schema.digest != document["schema_digest"]:
        _refuse("catalogue_release_digest_mismatch", "the schema record differs from its digest")
    versions = []
    for identity, version in document["items"]:
        _item_row, payload = _payload(binding, store, ITEM_KIND, version, ITEM_VERSION_RECORD_TYPES)
        if payload is None:
            _refuse("catalogue_release_incomplete", "the release names an item version the store does not hold")
        if sha256_hex(canonical_bytes(payload)) != version or payload["reference"]["identity"] != identity:
            _refuse("catalogue_release_digest_mismatch", "an item version record differs from its digest")
        versions.append((version, payload))
    return LoadedRelease(release_id, document, schema, tuple(versions))


def _marker_row(binding, previous, clock, *, state_version=CATALOGUE_STATE_VERSION):
    """The next marker. Its state version is the higher of the one held and the one this write needs."""
    revision = (previous["payload"]["revision"] + 1) if previous is not None else 1
    held = previous["payload"]["state_version"] if previous is not None else CATALOGUE_STATE_VERSION
    return binding.record(STATE_KIND, STATE_LOGICAL, {
        "record_type": STATE_RECORD_TYPE, "state_version": max(held, state_version),
        "revision": revision, "updated_at": int(clock())})


def _write_immutable(binding, rows):
    """Write content-addressed records in bounded batches; an identical record is kept, another refused."""
    for start in range(0, len(rows), WRITE_CHUNK):
        chunk = rows[start:start + WRITE_CHUNK]
        with binding.store(write=True) as store:
            fresh = []
            for kind, logical, payload in chunk:
                held = binding.read(store, kind, logical)
                if held is not None:
                    if held["payload"] != payload:
                        _refuse("catalogue_record_conflict", "a content-addressed record already holds other content")
                    continue
                fresh.append(binding.record(kind, logical, payload))
            if fresh:
                binding.commit(store, tuple(fresh), tuple(binding.guard(None, row["record_id"]) for row in fresh))


def _changes(active, bundle, withdrawn_now):
    held = dict(active.items) if active is not None else {}
    offered = {entry.identity: entry.version for entry in bundle.items}
    notes = bundle.change_notes
    added = [{"identity": identity, "item_version": version, "note": notes.get(identity, "")}
             for identity, version in sorted(offered.items()) if identity not in held]
    changed = [{"identity": identity, "item_version": version, "note": notes.get(identity, "")}
               for identity, version in sorted(offered.items()) if identity in held and held[identity] != version]
    removed = [{"identity": identity, "item_version": version, "note": notes.get(identity, ""),
                "durable": identity in withdrawn_now}
               for identity, version in sorted(held.items()) if identity not in offered]
    return {"added": added, "changed": changed, "withdrawn": removed}


def publish(context, bundle, *, expected_release=None, clock=time.time):
    """Publish one validated bundle and move the pointer, idempotently by content.

    `context` is a `CatalogueOperatorContext`. The bundle was already read and
    validated with the host policies. Nothing becomes active until the final
    batch commits the release, the pointer, the withdrawals and the marker
    together.
    """
    binding, body_store = context.binding, context.body_store(write=True)
    with binding.store() as store:
        _state_row, _state = read_state(binding, store)
        pointer_row, pointer = read_pointer(binding, store)
        active = load_release(binding, store, pointer["release_id"]) if pointer is not None else None
        withdrawn = withdrawal_keys(binding, store)
    active_id = pointer["release_id"] if pointer is not None else ""
    if expected_release is not None and expected_release != active_id:
        _refuse("catalogue_pointer_moved", "the active release is not the one this publish expected")
    listed = [entry for entry in bundle.items if (entry.identity, entry.package.served_digest) in withdrawn]
    if listed:
        _refuse("catalogue_release_lists_withdrawn_item",
                f"the bundle lists {len(listed)} withdrawn item versions; a withdrawal is never undone by a release")
    active_versions = dict(active.items) if active is not None else {}
    active_payloads = {digest: payload for digest, payload in active.versions} if active is not None else {}
    durable = {}
    for row in bundle.withdrawals:
        version = active_versions.get(row["identity"])
        if version is None:
            _refuse("catalogue_withdrawal_unknown", "a bundle withdraws only an item of the active release")
        if any(entry.identity == row["identity"] and entry.version == version for entry in bundle.items):
            _refuse("catalogue_withdrawal_still_listed", "a withdrawn item version cannot stay in the release")
        payload = active_payloads[version]
        served = CataloguePackage.from_dict(payload["package"]).served_digest
        durable[row["identity"]] = {"version": version, "body_digest": served, "note": row["note"]}
    items = tuple((entry.identity, entry.version) for entry in bundle.items)
    served_content = content_digest(bundle.schema.digest, items)
    if active is not None and content_digest(active.schema.digest, active.items) == served_content and not durable:
        return {"record_type": OPERATION_RECORD_TYPE, "operation": "publish", "state": "unchanged",
                "release_id": active_id, "content_digest": served_content, "items": len(items),
                "bundle_digest": bundle.digest, "bodies_written": 0}
    document = {"record_type": RELEASE_RECORD_TYPE, "schema_digest": bundle.schema.digest,
                "items": [list(row) for row in items], "based_on": active_id,
                "changes": _changes(active, bundle, set(durable)), "notes": bundle.notes}
    release_id = release_digest(document)
    written = 0
    blobs = bundle.blobs()
    from .catalogue_bundle import bundle_payloads
    for entry in bundle.items:
        for payload, file in bundle_payloads(blobs, entry):
            written += body_store.put(payload, expected_digest=file.digest, durable=False)["written"]
    # One flush for every body written above, before any record names them.
    body_store.sync()
    _write_immutable(binding, [(SCHEMA_KIND, bundle.schema.digest, bundle.schema.to_dict())]
                     + [(ITEM_KIND, entry.version, entry.document) for entry in bundle.items])
    now = int(clock())
    with binding.store(write=True) as store:
        state_row, _state = read_state(binding, store)
        latest_row, latest = read_pointer(binding, store)
        if (latest["release_id"] if latest is not None else "") != active_id:
            _refuse("catalogue_pointer_moved", "another operator moved the pointer while this release was written")
        records, guards = [], [binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL)),
                               binding.guard(latest_row, binding.identity(POINTER_KIND, POINTER_LOGICAL))]
        # Nothing becomes active until everything it names is stored and reads back.
        require_complete_release(binding, store, document, body_store)
        held = binding.read(store, RELEASE_KIND, release_id)
        if held is None:
            row = binding.record(RELEASE_KIND, release_id, {**document, "release_id": release_id, "published_at": now})
            records.append(row)
            guards.append(binding.guard(None, row["record_id"]))
        elif release_digest(held["payload"]) != release_id:
            _refuse("catalogue_release_digest_mismatch", "the stored release differs from its digest")
        for identity, value in sorted(durable.items()):
            if binding.read(store, WITHDRAWAL_KIND, (identity, value["body_digest"])) is None:
                row = binding.record(WITHDRAWAL_KIND, (identity, value["body_digest"]), {
                    "record_type": WITHDRAWAL_RECORD_TYPE, "identity": identity, "body_digest": value["body_digest"],
                    "item_version": value["version"], "note": value["note"], "withdrawn_at": now,
                    "release_id": release_id})
                records.append(row)
                guards.append(binding.guard(None, row["record_id"]))
        records.append(binding.record(POINTER_KIND, POINTER_LOGICAL, {
            "record_type": POINTER_RECORD_TYPE, "release_id": release_id, "moved_at": now, "move": "publish",
            "previous_release_id": active_id,
            "sequence": (latest["sequence"] + 1) if latest is not None else 1}))
        from .catalogue_tiers import VERIFIED_TIER
        needed = (COMMUNITY_STATE_VERSION if any(entry.tier != VERIFIED_TIER for entry in bundle.items)
                  else CATALOGUE_STATE_VERSION)
        records.append(_marker_row(binding, state_row, clock, state_version=needed))
        binding.commit(store, tuple(records), tuple(guards))
    changes = document["changes"]
    return {"record_type": OPERATION_RECORD_TYPE, "operation": "publish",
            "state": "published" if held is None else "pointer_moved", "release_id": release_id,
            "previous_release_id": active_id, "content_digest": served_content, "items": len(items),
            "added": len(changes["added"]), "changed": len(changes["changed"]),
            "withdrawn": len(changes["withdrawn"]), "durable_withdrawals": len(durable),
            "bundle_digest": bundle.digest, "bodies_written": written}


def verify_release_bodies(release, body_store, *, withdrawn=frozenset()):
    """Read every file of every served item version of a release, checking digests and text."""
    for _version, payload in release.versions:
        package = CataloguePackage.from_dict(payload["package"])
        if (payload["reference"]["identity"], package.served_digest) in withdrawn:
            continue
        for file in package.files:
            data = body_store.read(file.digest, file.size_bytes)
            if package.body_form == "file":
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    _refuse("package_file_not_text", "the file body form serves UTF-8 text only")


def require_complete_release(binding, store, document, body_store):
    """Refuse to activate a release unless its schema, every item version and every body are stored."""
    if binding.read(store, SCHEMA_KIND, document["schema_digest"]) is None:
        _refuse("catalogue_release_incomplete", "the release names a schema the store does not hold")
    for _identity, version in document["items"]:
        row = binding.read(store, ITEM_KIND, version)
        if row is None:
            _refuse("catalogue_release_incomplete", "the release names an item version the store does not hold")
        package = CataloguePackage.from_dict(row["payload"]["package"])
        for file in package.files:
            data = body_store.read(file.digest, file.size_bytes)
            if package.body_form == "file":
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    _refuse("package_file_not_text", "the file body form serves UTF-8 text only")


def rollback(context, *, to_release, expected_release, clock=time.time):
    """Move the pointer to an earlier release after verifying it completely; withdrawals stay honoured."""
    identifier(expected_release, "expected release")
    binding = context.binding
    with binding.store() as store:
        read_state(binding, store)
        _row, pointer = read_pointer(binding, store)
        if pointer is None or pointer["release_id"] != expected_release:
            _refuse("catalogue_pointer_moved", "the active release is not the one this rollback expected")
        target = load_release(binding, store, to_release)
        withdrawn = withdrawal_keys(binding, store)
    verify_release_bodies(target, context.body_store())
    held_back = sorted(payload["reference"]["identity"] for _version, payload in target.versions
                       if (payload["reference"]["identity"],
                           CataloguePackage.from_dict(payload["package"]).served_digest) in withdrawn)
    now = int(clock())
    with binding.store(write=True) as store:
        state_row, _state = read_state(binding, store)
        latest_row, latest = read_pointer(binding, store)
        if latest is None or latest["release_id"] != expected_release:
            _refuse("catalogue_pointer_moved", "the active release changed during the rollback")
        binding.commit(store, (
            binding.record(POINTER_KIND, POINTER_LOGICAL, {
                "record_type": POINTER_RECORD_TYPE, "release_id": to_release, "moved_at": now, "move": "rollback",
                "previous_release_id": expected_release, "sequence": latest["sequence"] + 1}),
            _marker_row(binding, state_row, clock)),
            (binding.guard(latest_row), binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL))))
    return {"record_type": OPERATION_RECORD_TYPE, "operation": "rollback", "state": "pointer_moved",
            "release_id": to_release, "previous_release_id": expected_release, "items": len(target.versions),
            "withdrawn_items_kept_withheld": held_back}


def withdraw(context, *, identity, note_text, item_version=None, all_versions=False, clock=time.time):
    """Record durable withdrawals for one identity; serving refuses them at once and forever."""
    if not isinstance(identity, str) or not identity:
        _refuse("invalid_request", "a withdrawal names an item identity")
    note(note_text)
    binding = context.binding
    with binding.store() as store:
        read_state(binding, store)
        _row, pointer = read_pointer(binding, store)
        if all_versions:
            chosen = {}
            for row in binding.rows_all(store, ITEM_KIND):
                payload = row["payload"]
                if payload.get("record_type") not in ITEM_VERSION_RECORD_TYPES:
                    _refuse("catalogue_record_unsupported", f"an item record is not one of {ITEM_VERSION_RECORD_TYPES}")
                if payload["reference"]["identity"] == identity:
                    chosen[sha256_hex(canonical_bytes(payload))] = payload
        else:
            if item_version is None:
                active = load_release(binding, store, pointer["release_id"]) if pointer is not None else None
                item_version = dict(active.items).get(identity) if active is not None else None
            _item_row, payload = (_payload(binding, store, ITEM_KIND, item_version, ITEM_VERSION_RECORD_TYPES)
                                  if item_version else (None, None))
            if payload is not None and payload["reference"]["identity"] != identity:
                _refuse("catalogue_item_not_found", "that item version belongs to another identity")
            chosen = {item_version: payload} if payload is not None else {}
    if not chosen:
        _refuse("catalogue_item_not_found", "the store holds no version of that item to withdraw")
    now, recorded = int(clock()), []
    with binding.store(write=True) as store:
        state_row, _state = read_state(binding, store)
        records, guards = [], [binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL))]
        for version, payload in sorted(chosen.items()):
            served = CataloguePackage.from_dict(payload["package"]).served_digest
            if binding.read(store, WITHDRAWAL_KIND, (identity, served)) is not None:
                continue
            row = binding.record(WITHDRAWAL_KIND, (identity, served), {
                "record_type": WITHDRAWAL_RECORD_TYPE, "identity": identity, "body_digest": served,
                "item_version": version, "note": note_text, "withdrawn_at": now, "release_id": ""})
            records.append(row)
            guards.append(binding.guard(None, row["record_id"]))
            recorded.append(version)
        if records:
            records.append(_marker_row(binding, state_row, clock))
            binding.commit(store, tuple(records), tuple(guards))
    return {"record_type": OPERATION_RECORD_TYPE, "operation": "withdraw", "identity": identity,
            "state": "withdrawn" if recorded else "unchanged", "withdrawn_versions": recorded}


def status(context):
    """A read-only view of the catalogue state, for an operator and for a rollback decision."""
    binding = context.binding
    with binding.store() as store:
        _row, state = read_state(binding, store)
        _pointer_row, pointer = read_pointer(binding, store)
        releases = sorted(({"release_id": row["payload"].get("release_id"),
                            "published_at": row["payload"].get("published_at"),
                            "based_on": row["payload"].get("based_on"),
                            "items": len(row["payload"].get("items", ())),
                            "changes": {key: len(value) for key, value in row["payload"].get("changes", {}).items()}}
                           for row in binding.rows_all(store, RELEASE_KIND)),
                          key=lambda row: (row["published_at"] or 0, row["release_id"] or ""))
        withdrawals = len(withdrawal_keys(binding, store))
    return {"record_type": STATUS_RECORD_TYPE, "catalogue_state_version": state["state_version"] if state else None,
            "revision": state["revision"] if state else 0,
            "supported_catalogue_state_versions": list(SUPPORTED_CATALOGUE_STATE_VERSIONS),
            "active_release_id": pointer["release_id"] if pointer else None,
            "pointer_sequence": pointer["sequence"] if pointer else 0, "releases": releases,
            "durable_withdrawals": withdrawals,
            "rollback_rule": "an image that does not list the catalogue state version above refuses to start"}


@dataclass(frozen=True)
class CatalogueOperatorContext:
    """What one operator command may touch: the scoped service store and the declared body folder."""

    binding: ServiceCatalogBinding
    body_store_root: str

    def body_store(self, *, write=False):
        from .catalogue_packages import VolumeBodyStore, require_body_store
        return require_body_store(VolumeBodyStore(self.body_store_root, writes_authorized=write), write=write)
