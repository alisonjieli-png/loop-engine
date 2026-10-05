"""Publishing a version 2 (segmented) catalogue release into the service store.

The formats, records and readers are in `catalogue_segments`. This module is
the one writer: it checks a version 2 bundle against the store and the active
release, writes only the bodies, item versions and segments the store lacks,
and commits the release, the pointer, the withdrawals and the marker in one
atomic batch, as a version 1 publish (`catalogue_releases.publish`) does.

```text
publish_segmented
├── read      every segment the release names, from the store or the bundle, each checked against its
│             reference, the canonical cuts, identity order, the count and the content digest
├── resolve   every pair of a segment new to the store: the item version from the store, or the bundle's
│             line validated with every rule a version 1 line passes
├── refuse    a durably withdrawn item version listed again; a withdrawal of an item the active release
│             does not list, or that the new release still lists
├── write     bodies, flushed once, then item versions and segments, content-addressed
└── commit    release, pointer, withdrawals and marker, after everything reads back
```

The work follows the change: segments the store holds were checked when they
were first published, so a publish reads the segments it does not share with
the active release, the item versions those segments name and their bodies.
"""
from __future__ import annotations

from bisect import bisect_right
import time

from .catalogue_bundle import ITEM_VERSION_RECORD_TYPES
from .catalogue_packages import CataloguePackage
from .catalogue_segments import (RELEASE_V2_RECORD_TYPE, SEGMENT_KIND, SEGMENTED_STATE_VERSION, ContentDigest,
                                 SegmentedRelease, bounded_changes, segment_entries, segment_reader,
                                 verified_segment)
from .records import ServiceRuntimeError


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def _active_pairs(binding, store, active):
    """Every (identity, version) pair of the active release, in identity order, whichever version it is."""
    if active is None:
        return iter(())
    if isinstance(active, SegmentedRelease):
        return active.entries(segment_reader(binding, store))
    return iter(tuple(active.items))


def publish_segmented(context, bundle, *, expected_release=None, clock=time.time):
    """Publish one validated version 2 bundle and move the pointer, idempotently by content.

    Nothing is written until every segment the release names, every item version those segments name and every
    body of every item version new to the store is present, read back and checked. Records and bodies are then
    written content-addressed, and the release, the pointer, the withdrawals and the marker commit in one batch,
    as a version 1 publish commits them.
    """
    from .catalogue_releases import (ITEM_KIND, POINTER_KIND, POINTER_LOGICAL, RELEASE_KIND, SCHEMA_KIND,
                                     STATE_KIND, STATE_LOGICAL, WITHDRAWAL_KIND, WITHDRAWAL_RECORD_TYPE,
                                     COMMUNITY_STATE_VERSION, OPERATION_RECORD_TYPE, POINTER_RECORD_TYPE,
                                     _marker_row, _write_immutable, load_any_release, load_item_version,
                                     read_pointer, read_state, release_digest, withdrawal_keys)
    from .catalogue_tiers import VERIFIED_TIER
    binding, body_store = context.binding, context.body_store(write=True)
    held_segments, new_segments, new_items, community = {}, {}, {}, False
    with binding.store() as store:
        read_state(binding, store)
        _pointer_row, pointer = read_pointer(binding, store)
        active_id = pointer["release_id"] if pointer is not None else ""
        if expected_release is not None and expected_release != active_id:
            _refuse("catalogue_pointer_moved", "the active release is not the one this publish expected")
        active = load_any_release(binding, store, active_id) if pointer is not None else None
        withdrawn = withdrawal_keys(binding, store)
        # A release with other cuts than the active one shares no segment with it; that is allowed and costs an
        # upload of every segment, as the first version 2 release after a version 1 release does.
        read_held = segment_reader(binding, store)
        stream, previous, pairs_by_segment = ContentDigest(bundle.schema.digest), None, []
        for position, ref in enumerate(bundle.segments):
            document = read_held(ref.digest)
            if document is None:
                document = bundle.carried_segment(ref.digest)
                if document is None:
                    _refuse("catalogue_release_incomplete",
                            "the bundle names a segment that neither it nor the store holds")
                new_segments[ref.digest] = document
            else:
                held_segments[ref.digest] = True
            pairs = verified_segment(ref, document, bundle.segmentation, last=position == len(bundle.segments) - 1)
            if previous is not None and pairs[0][0] <= previous:
                _refuse("bundle_segments_changed", "segments overlap or are out of identity order")
            previous = pairs[-1][0]
            for identity, version in pairs:
                stream.add(identity, version)
            if ref.digest in new_segments:
                pairs_by_segment.append(pairs)
        if stream.count != bundle.release_items or stream.hexdigest() != bundle.content_digest:
            _refuse("bundle_segments_changed", "the segments differ from the item count and content the header states")
        # Every pair of a new segment names an item version the store holds or the bundle carries.
        for pairs in pairs_by_segment:
            for identity, version in pairs:
                if version in new_items:
                    continue
                row = binding.read(store, ITEM_KIND, version)
                if row is not None:
                    payload = load_item_version(binding, store, identity, version)
                    community = community or payload.get("record_type") != ITEM_VERSION_RECORD_TYPES[0]
                    continue
                entry = bundle.carried_item(version)
                if entry is None:
                    _refuse("catalogue_release_incomplete",
                            "a segment names an item version that neither the bundle nor the store holds")
                if entry.identity != identity:
                    _refuse("bundle_item_digest_mismatch", "a carried item version belongs to another identity")
                new_items[version] = entry
                community = community or entry.tier != VERIFIED_TIER
        # A release never lists a durably withdrawn item version: check every withdrawal against this release.
        for identity, served in sorted(withdrawn):
            version = _find_in_bundle(bundle, identity, read_held, new_segments)
            if version is None:
                continue
            if version in new_items:
                listed_digest = new_items[version].package.served_digest
            else:
                payload = load_item_version(binding, store, identity, version)
                listed_digest = CataloguePackage.from_dict(payload["package"]).served_digest
            if listed_digest == served:
                _refuse("catalogue_release_lists_withdrawn_item",
                        "the bundle lists a withdrawn item version; a withdrawal is never undone by a release")
        # The withdrawals this bundle records: items of the active release that the new release no longer lists.
        durable = {}
        for row in bundle.withdrawals:
            version = _find_in_active(binding, store, active, row["identity"])
            if version is None:
                _refuse("catalogue_withdrawal_unknown", "a bundle withdraws only an item of the active release")
            if _find_in_bundle(bundle, row["identity"], read_held, new_segments) == version:
                _refuse("catalogue_withdrawal_still_listed", "a withdrawn item version cannot stay in the release")
            payload = load_item_version(binding, store, row["identity"], version)
            served = CataloguePackage.from_dict(payload["package"]).served_digest
            durable[row["identity"]] = {"version": version, "body_digest": served, "note": row["note"]}
        changes = _segment_changes(binding, store, active, bundle, read_held, new_segments, set(durable))
    if (active is not None and _content_of(active) == bundle.content_digest and not durable
            and _schema_of(active) == bundle.schema.digest and isinstance(active, SegmentedRelease)
            and [ref.digest for ref in active.segments] == [ref.digest for ref in bundle.segments]):
        return {"record_type": OPERATION_RECORD_TYPE, "operation": "publish", "state": "unchanged",
                "release_id": active_id, "content_digest": bundle.content_digest, "items": bundle.release_items,
                "bundle_digest": bundle.digest, "bodies_written": 0, "segments_written": 0, "items_written": 0}
    document = {"record_type": RELEASE_V2_RECORD_TYPE, "schema_digest": bundle.schema.digest,
                "segmentation": bundle.segmentation.to_dict(),
                "segments": [ref.to_list() for ref in bundle.segments], "items": bundle.release_items,
                "content_digest": bundle.content_digest, "based_on": active_id, "changes": changes,
                "notes": bundle.notes}
    release_id = release_digest(document)
    # Bodies first: every file of every new item version, from the bundle or already in the body store.
    written, blobs = 0, bundle.blobs()
    for entry in new_items.values():
        for file in entry.package.files:
            payload = None
            if blobs is not None:
                try:
                    payload = blobs.read(file.digest, file.size_bytes)
                except ServiceRuntimeError as error:
                    if error.code != "body_missing":
                        raise
            if payload is not None:
                written += body_store.put(payload, expected_digest=file.digest, durable=False)["written"]
    body_store.sync()
    for entry in new_items.values():
        for file in entry.package.files:
            data = body_store.read(file.digest, file.size_bytes)
            if entry.package.body_form == "file":
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    _refuse("package_file_not_text", "the file body form serves UTF-8 text only")
    _write_immutable(binding, [(SCHEMA_KIND, bundle.schema.digest, bundle.schema.to_dict())]
                     + [(ITEM_KIND, version, entry.document) for version, entry in sorted(new_items.items())]
                     + [(SEGMENT_KIND, digest, document) for digest, document in sorted(new_segments.items())])
    now = int(clock())
    with binding.store(write=True) as store:
        state_row, _state = read_state(binding, store)
        latest_row, latest = read_pointer(binding, store)
        if (latest["release_id"] if latest is not None else "") != active_id:
            _refuse("catalogue_pointer_moved", "another operator moved the pointer while this release was written")
        records, guards = [], [binding.guard(state_row, binding.identity(STATE_KIND, STATE_LOGICAL)),
                               binding.guard(latest_row, binding.identity(POINTER_KIND, POINTER_LOGICAL))]
        # Nothing becomes active until everything it names reads back: the schema, every segment, and every item
        # version of every segment that is new to the store.
        _require_complete_segmented(binding, store, document, new_segments, new_items, body_store)
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
        needed = max(SEGMENTED_STATE_VERSION, COMMUNITY_STATE_VERSION if community else 1)
        records.append(_marker_row(binding, state_row, clock, state_version=needed))
        binding.commit(store, tuple(records), tuple(guards))
    counts = changes["counts"]
    return {"record_type": OPERATION_RECORD_TYPE, "operation": "publish",
            "state": "published" if held is None else "pointer_moved", "release_id": release_id,
            "release_record_type": RELEASE_V2_RECORD_TYPE, "previous_release_id": active_id,
            "content_digest": bundle.content_digest, "items": bundle.release_items,
            "added": counts["added"], "changed": counts["changed"], "withdrawn": counts["withdrawn"],
            "durable_withdrawals": len(durable), "bundle_digest": bundle.digest, "bodies_written": written,
            "segments": len(bundle.segments), "segments_written": len(new_segments),
            "segments_held": len(held_segments), "items_written": len(new_items)}


def _content_of(release):
    from .catalogue_releases import content_digest
    if isinstance(release, SegmentedRelease):
        return release.content_digest
    return content_digest(release.schema.digest, release.items)


def _schema_of(release):
    return release.schema.digest


def _find_in_bundle(bundle, identity, read_held, new_segments):
    """The item version the bundle's release lists for `identity`, reading one segment, or None."""
    position = bisect_right([ref.first for ref in bundle.segments], identity) - 1
    if position < 0:
        return None
    ref = bundle.segments[position]
    document = new_segments.get(ref.digest) or read_held(ref.digest) or bundle.carried_segment(ref.digest)
    return dict(segment_entries(document, ref.digest)).get(identity)


def _find_in_active(binding, store, active, identity):
    if active is None:
        return None
    if isinstance(active, SegmentedRelease):
        return active.find(identity, segment_reader(binding, store))
    return dict(active.items).get(identity)


def _segment_changes(binding, store, active, bundle, read_held, new_segments, withdrawn_now):
    """What the release adds, changes and removes, read from the segments the two releases do not share."""
    notes = bundle.change_notes
    shared = set()
    if isinstance(active, SegmentedRelease):
        shared = {ref.digest for ref in active.segments} & {ref.digest for ref in bundle.segments}
        old = {}
        for ref in active.segments:
            if ref.digest not in shared:
                old.update(segment_entries(read_held(ref.digest), ref.digest))
    else:
        old = dict(_active_pairs(binding, store, active))
    new = {}
    for ref in bundle.segments:
        if ref.digest in shared:
            continue
        document = new_segments.get(ref.digest) or read_held(ref.digest)
        new.update(segment_entries(document, ref.digest))
    added = [{"identity": identity, "item_version": version, "note": notes.get(identity, "")}
             for identity, version in sorted(new.items()) if identity not in old]
    changed = [{"identity": identity, "item_version": version, "note": notes.get(identity, "")}
               for identity, version in sorted(new.items()) if identity in old and old[identity] != version]
    removed = [{"identity": identity, "item_version": version, "note": notes.get(identity, ""),
                "durable": identity in withdrawn_now}
               for identity, version in sorted(old.items()) if identity not in new]
    return bounded_changes(added, changed, removed)


def _require_complete_segmented(binding, store, document, new_segments, new_items, body_store):
    """Refuse to activate a version 2 release unless its schema, segments and new item versions read back."""
    from .catalogue_releases import ITEM_KIND, SCHEMA_KIND
    if binding.read(store, SCHEMA_KIND, document["schema_digest"]) is None:
        _refuse("catalogue_release_incomplete", "the release names a schema the store does not hold")
    for value in document["segments"]:
        if binding.read(store, SEGMENT_KIND, value[0]) is None:
            _refuse("catalogue_release_incomplete", "the release names a segment the store does not hold")
    for version, entry in new_items.items():
        if binding.read(store, ITEM_KIND, version) is None:
            _refuse("catalogue_release_incomplete", "the release names an item version the store does not hold")
        for file in entry.package.files:
            body_store.read(file.digest, file.size_bytes)
