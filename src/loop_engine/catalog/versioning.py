"""Record versioning over any CatalogStore: history, diff, and rollback.

A catalog store keeps one current row per record identity and refuses a
stale precondition. That protects a write, but it forgets the past. This
module keeps the past as immutable revision records inside the same store,
so there is no second store and no second authority: a revision is a
catalog record whose artifact kind is ``record_revision`` and whose
lifecycle is ``revision``, which ordinary lifecycle filters exclude.

Operations: ``revise`` writes a new current version under a precondition
and preserves the previous version as a revision; ``history`` lists every
version with its digest; ``diff`` names the changed top-level fields and
the changed attribute and payload keys; ``rollback`` writes a new version
whose content equals an earlier one and names where it came from. Nothing
here deletes a row.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass

from .handshake import negotiate
from .protocol import CatalogStore, PreconditionFailed, StoreError
from .query import IntelligenceQuery

REVISION_ARTIFACT_KIND = "record_revision"
REVISION_LIFECYCLE = "revision"
HISTORY_RECORD_TYPE = "record_history/v1"
DIFF_RECORD_TYPE = "record_diff/v1"
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class VersioningError(StoreError):
    """A revision, history, diff, or rollback request is invalid."""


def content_digest(record: dict) -> str:
    """The digest of a record without its revision bookkeeping."""
    body = {key: value for key, value in record.items()
            if key not in ("record_id", "record_version")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def _parse_version(version: str) -> tuple[int, int, int]:
    match = _VERSION.fullmatch(str(version or ""))
    if match is None:
        raise VersioningError(f"record_version must be major.minor.patch, got {version!r}")
    return tuple(int(part) for part in match.groups())


def next_version(version: str, part: str = "patch") -> str:
    major, minor, patch = _parse_version(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise VersioningError("part must be major, minor, or patch")


def revision_id(record_id: str, version: str) -> str:
    return f"{record_id}::{version}"


@dataclass(frozen=True)
class RecordRevision:
    """One preserved version of a record."""

    record_id: str
    version: str
    digest: str
    current: bool
    restored_from: str = ""

    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "version": self.version, "digest": self.digest,
                "current": self.current, "restored_from": self.restored_from}


def _revision_record(record: dict) -> dict:
    """The immutable copy of one version, stored beside the current record."""
    record_id = record["record_id"]
    version = record["record_version"]
    attributes = {"revision_of": record_id, "revision_version": version,
                  "revision_digest": content_digest(record)}
    return {**deepcopy(record), "record_id": revision_id(record_id, version),
            "artifact_kind": REVISION_ARTIFACT_KIND, "lifecycle": REVISION_LIFECYCLE,
            "attributes": attributes,
            "payload": {"record_type": "catalog_record_revision/v2",
                        "record": deepcopy(record)}}


def _restored_revision(preserved: dict, record_id: str, version: str) -> dict:
    attributes = preserved.get("attributes") or {}
    if (preserved.get("record_id") != revision_id(record_id, version)
            or preserved.get("artifact_kind") != REVISION_ARTIFACT_KIND
            or preserved.get("lifecycle") != REVISION_LIFECYCLE
            or attributes.get("revision_of") != record_id
            or attributes.get("revision_version") != version):
        raise VersioningError("revision identity is inconsistent")
    payload = preserved.get("payload") or {}
    if not isinstance(payload, dict) or payload.get("record_type") != "catalog_record_revision/v2":
        raise VersioningError("unsupported revision version: current revision records are required")
    restored = deepcopy(payload.get("record"))
    if (not isinstance(restored, dict) or restored.get("record_id") != record_id
            or restored.get("record_version") != version
            or content_digest(restored) != attributes.get("revision_digest")):
        raise VersioningError("revision content digest does not match")
    return restored


def _stored_form(record):
    """The record as a durable store returns it: JSON has lists, not tuples."""
    return json.loads(json.dumps(record, sort_keys=True))


def _confirmed_put(store: CatalogStore, record: dict, precondition: dict) -> None:
    confirmation = store.put(deepcopy(record), precondition=precondition)
    if (not isinstance(confirmation, dict) or confirmation.get("stored") is not True
            or confirmation.get("record_id") != record["record_id"]):
        raise VersioningError("record write outcome is unknown: invalid acknowledgment")
    # Compare stored forms. An in-memory store keeps a tuple and a durable
    # store returns a list; neither difference means the write was lost.
    expected = _stored_form(record)
    actual = store.get(record["record_id"])
    if isinstance(actual, dict) and _stored_form(actual) == expected:
        return
    # A concurrent, later revision may already have moved the current pointer.
    # Its immutable predecessor can still establish that our version committed.
    if (record.get("artifact_kind") != REVISION_ARTIFACT_KIND
            and isinstance(actual, dict)
            and _parse_version(actual.get("record_version")) > _parse_version(record["record_version"])):
        preserved = store.get(revision_id(record["record_id"], record["record_version"]))
        if preserved is not None and _stored_form(_restored_revision(
                preserved, record["record_id"], record["record_version"])) == expected:
            return
    raise VersioningError("record write outcome is unknown: readback did not confirm it")


def revise(store: CatalogStore, record: dict, *, expected_version: str | None) -> RecordRevision:
    """Write ``record`` as the new current version and preserve the previous one.

    ``expected_version`` is the version the caller last read; None means the
    record must not exist yet. A stale expectation is refused by the store,
    so two writers cannot both win.
    """
    capabilities = store.capabilities()
    handshake = negotiate(capabilities, required_operations=("get", "write"), write_requested=True)
    if (not handshake.permits("write") or capabilities.authority != "authoritative"
            or capabilities.transactions.get("atomic_preconditions") is not True):
        raise VersioningError("versioning requires atomic authoritative write preconditions")
    if not isinstance(record, dict):
        raise VersioningError("a versioned record must be an object")
    record = deepcopy(record)
    for field in ("intelligence_layer", "source_collection", "artifact_kind", "lifecycle", "namespace"):
        record.setdefault(field, "")
    record.setdefault("attributes", {})
    record.setdefault("payload", {})
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id or "::" in record_id:
        raise VersioningError("a versioned record needs a record_id without '::'")
    version = record.get("record_version")
    _parse_version(version)
    current = store.get(record_id)
    if expected_version is None:
        if current is not None:
            raise VersioningError(f"{record_id!r} already exists at {current.get('record_version')!r}")
    else:
        if current is None or current.get("record_version") != expected_version:
            raise VersioningError(f"expected {record_id!r} at {expected_version!r}; "
                                  f"found {(current or {}).get('record_version')!r}")
        if _parse_version(version) <= _parse_version(expected_version):
            raise VersioningError("a revision must carry a higher version than the one it replaces")
        preserved = _revision_record(current)
        try:
            _confirmed_put(store, preserved, {"exists": False})
        except PreconditionFailed:
            existing = store.get(preserved["record_id"])
            if (existing is None
                    or _restored_revision(existing, record_id, expected_version) != current):
                raise VersioningError("an immutable revision already names different content") from None
    if expected_version is None:
        _confirmed_put(store, record, {"exists": False})
    else:
        _confirmed_put(store, record, {"record_version": expected_version})
    return RecordRevision(record_id, version, content_digest(record), True,
                          str((record.get("attributes") or {}).get("restored_from") or ""))


def history(store: CatalogStore, record_id: str) -> dict:
    """Every version of a record, oldest first, with the current one last."""
    current = store.get(record_id)
    revisions = store.query(IntelligenceQuery(
        artifact_kinds=(REVISION_ARTIFACT_KIND,), lifecycle=(REVISION_LIFECYCLE,),
        attributes={"revision_of": {"equals": record_id}}))
    items = []
    for item in revisions:
        version = item["attributes"]["revision_version"]
        restored = _restored_revision(item, record_id, version)
        # Preserving the predecessor precedes the guarded head update. A
        # refused update can leave an identical copy of the still-current row.
        if current is not None and _parse_version(version) >= _parse_version(current["record_version"]):
            continue
        items.append(RecordRevision(record_id, version, content_digest(restored), False,
                                    str((restored.get("attributes") or {}).get("restored_from") or "")))
    items.sort(key=lambda item: _parse_version(item.version))
    if current is not None:
        items.append(RecordRevision(record_id, current["record_version"], content_digest(current), True,
                                    str((current.get("attributes") or {}).get("restored_from") or "")))
    return {"record_type": HISTORY_RECORD_TYPE, "record_id": record_id,
            "versions": [item.to_dict() for item in items], "count": len(items)}


def version_record(store: CatalogStore, record_id: str, version: str) -> dict | None:
    """The content of one version as it was stored, current or preserved."""
    current = store.get(record_id)
    if current is not None and current.get("record_version") == version:
        return current
    preserved = store.get(revision_id(record_id, version))
    if preserved is None:
        return None
    restored = _restored_revision(preserved, record_id, version)
    if current is None or _parse_version(version) >= _parse_version(current["record_version"]):
        return None
    return restored


def diff(store: CatalogStore, record_id: str, from_version: str, to_version: str) -> dict:
    """The fields and keys that differ between two versions."""
    before = version_record(store, record_id, from_version)
    after = version_record(store, record_id, to_version)
    if before is None or after is None:
        raise VersioningError("both versions must exist to diff them")
    changed_fields = sorted(key for key in set(before) | set(after)
                            if key not in ("record_version", "attributes", "payload")
                            and before.get(key) != after.get(key))
    result = {"record_type": DIFF_RECORD_TYPE, "record_id": record_id,
              "from_version": from_version, "to_version": to_version,
              "changed_fields": changed_fields}
    for section in ("attributes", "payload"):
        left = before.get(section) or {}
        right = after.get(section) or {}
        if not isinstance(left, dict) or not isinstance(right, dict):
            result[section] = {"replaced": left != right}
            continue
        result[section] = {"added": sorted(set(right) - set(left)),
                           "removed": sorted(set(left) - set(right)),
                           "changed": sorted(key for key in set(left) & set(right)
                                             if left[key] != right[key])}
    return result


def rollback(store: CatalogStore, record_id: str, to_version: str, *,
             expected_version: str) -> RecordRevision:
    """A new version whose content equals ``to_version``; nothing is deleted."""
    target = version_record(store, record_id, to_version)
    if target is None:
        raise VersioningError(f"{record_id!r} has no version {to_version!r}")
    restored = deepcopy(target)
    attributes = dict(restored.get("attributes") or {})
    attributes["restored_from"] = to_version
    restored["attributes"] = attributes
    restored["record_version"] = next_version(expected_version, "minor")
    return revise(store, restored, expected_version=expected_version)


def self_test() -> dict:
    """History grows, diffs name changes, rollback restores content, nothing is deleted."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except StoreError:
            return True
        return False

    from .stores.in_memory import EphemeralRecordStore
    store = EphemeralRecordStore()
    base = {"record_id": "ctx.fact.python", "record_version": "1.0.0",
            "intelligence_layer": "context", "source_collection": "learned",
            "artifact_kind": "note", "lifecycle": "active", "namespace": "org:example",
            "attributes": {"topic": "python"}, "payload": {"text": "requires 3.10"}}
    first = revise(store, base, expected_version=None)
    second = revise(store, {**base, "record_version": "1.1.0",
                            "payload": {"text": "requires 3.11"},
                            "attributes": {"topic": "python", "reviewed": True}},
                    expected_version="1.0.0")
    check("revise_keeps_the_previous_version_as_an_immutable_revision",
          first.current and second.current
          and store.get("ctx.fact.python")["record_version"] == "1.1.0"
          and store.get(revision_id("ctx.fact.python", "1.0.0"))["lifecycle"] == REVISION_LIFECYCLE
          and version_record(store, "ctx.fact.python", "1.0.0")["payload"] == {"text": "requires 3.10"})
    listed = history(store, "ctx.fact.python")
    check("history_lists_every_version_oldest_first_with_the_current_last",
          [item["version"] for item in listed["versions"]] == ["1.0.0", "1.1.0"]
          and [item["current"] for item in listed["versions"]] == [False, True]
          and listed["versions"][0]["digest"] == content_digest(base))
    changes = diff(store, "ctx.fact.python", "1.0.0", "1.1.0")
    check("diff_names_changed_fields_and_keys",
          changes["changed_fields"] == [] and changes["attributes"]["added"] == ["reviewed"]
          and changes["payload"]["changed"] == ["text"])
    check("stale_and_lower_versions_are_refused",
          refuses(lambda: revise(store, {**base, "record_version": "1.2.0"}, expected_version="1.0.0"))
          and refuses(lambda: revise(store, {**base, "record_version": "1.0.5"}, expected_version="1.1.0"))
          and refuses(lambda: revise(store, base, expected_version=None))
          and refuses(lambda: revise(store, {**base, "record_id": "a::b"}, expected_version=None))
          and refuses(lambda: revise(store, {**base, "record_version": "v2"}, expected_version=None)))
    restored = rollback(store, "ctx.fact.python", "1.0.0", expected_version="1.1.0")
    current = store.get("ctx.fact.python")
    check("rollback_writes_a_new_version_equal_to_the_old_content_and_names_its_origin",
          restored.version == "1.2.0" and restored.restored_from == "1.0.0"
          and current["payload"] == {"text": "requires 3.10"}
          and current["attributes"] == {"topic": "python", "restored_from": "1.0.0"}
          and [item["version"] for item in history(store, "ctx.fact.python")["versions"]]
          == ["1.0.0", "1.1.0", "1.2.0"]
          and refuses(lambda: rollback(store, "ctx.fact.python", "9.9.9", expected_version="1.2.0")))
    active = store.query(IntelligenceQuery(lifecycle=("active",)))
    check("ordinary_lifecycle_queries_do_not_see_revisions",
          [item["record_id"] for item in active] == ["ctx.fact.python"]
          and len(store.query(IntelligenceQuery(artifact_kinds=(REVISION_ARTIFACT_KIND,)))) == 2)

    prefixed = {**base, "record_id": "prefixed",
                "attributes": {"revision_customer_field": "keep", "revision_of": "customer-value"}}
    preserve = EphemeralRecordStore()
    revise(preserve, prefixed, expected_version=None)
    revise(preserve, {**prefixed, "record_version": "1.0.1"}, expected_version="1.0.0")
    original = version_record(preserve, "prefixed", "1.0.0")
    check("historical_records_preserve_all_caller_attributes",
          original == prefixed and content_digest(original) == content_digest(prefixed))
    corrupted = preserve.get(revision_id("prefixed", "1.0.0"))
    corrupted["payload"]["record"]["payload"] = {"tampered": True}
    preserve.put(corrupted)
    check("tampered_history_is_refused_by_read_history_and_rollback",
          refuses(lambda: version_record(preserve, "prefixed", "1.0.0"))
          and refuses(lambda: history(preserve, "prefixed"))
          and refuses(lambda: rollback(preserve, "prefixed", "1.0.0", expected_version="1.0.1")))

    legacy_base = {**base, "record_id": "legacy", "attributes": {"revision_customer_field": "keep"}}
    legacy = {**deepcopy(legacy_base), "record_id": revision_id("legacy", "1.0.0"),
              "artifact_kind": REVISION_ARTIFACT_KIND, "lifecycle": REVISION_LIFECYCLE,
              "attributes": {**legacy_base["attributes"], "revision_of": "legacy",
                             "revision_version": "1.0.0", "revision_digest": content_digest(legacy_base),
                             "revision_layer": "context", "revision_artifact_kind": "note",
                             "revision_lifecycle": "active"}}
    compatible = EphemeralRecordStore([legacy, {**legacy_base, "record_version": "1.0.1"}])
    check("unsupported_inline_revision_shape_is_refused_without_mutation",
          refuses(lambda: version_record(compatible, "legacy", "1.0.0"))
          and compatible.get(legacy["record_id"]) == legacy)

    class FailedCurrentWrite(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            if precondition is not None and "record_version" in precondition:
                raise StoreError("injected head write interruption")
            return super().put(record, precondition=precondition)

    failed = FailedCurrentWrite()
    revise(failed, base, expected_version=None)
    rejected = refuses(lambda: revise(failed, {**base, "record_version": "1.1.0"}, expected_version="1.0.0"))
    check("failed_current_update_keeps_one_current_history_entry",
          rejected and failed.get(base["record_id"]) == base
          and [item["version"] for item in history(failed, base["record_id"])["versions"]] == ["1.0.0"])

    class LostAcknowledgment(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            super().put(record, precondition=precondition)
            return None

    uncertain = LostAcknowledgment()
    check("unacknowledged_write_never_returns_a_successful_revision",
          refuses(lambda: revise(uncertain, base, expected_version=None))
          and uncertain.get(base["record_id"]) is not None)

    class IgnoredWrite(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            return {"record_id": record["record_id"], "stored": True}

    check("false_write_acknowledgment_is_refused_on_readback",
          refuses(lambda: revise(IgnoredWrite(), base, expected_version=None)))

    class GuardRecorder(EphemeralRecordStore):
        def put(self, record, *, precondition=None):
            self.last_precondition = precondition
            return super().put(record, precondition=precondition)

    guarded = GuardRecorder()
    revise(guarded, base, expected_version=None)
    check("initial_revision_uses_the_stores_atomic_absence_guard",
          guarded.last_precondition == {"exists": False})

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    class ConcurrentCreationStore(EphemeralRecordStore):
        def __init__(self):
            super().__init__()
            self.barrier = Barrier(2)

        def get(self, record_id, version=None):
            observed = super().get(record_id, version)
            if record_id == "new" and observed is None:
                self.barrier.wait(timeout=5)
            return observed

    concurrent = ConcurrentCreationStore()

    def create(index):
        try:
            revise(concurrent, {**base, "record_id": "new", "payload": {"writer": index}},
                   expected_version=None)
            return True
        except StoreError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        wins = list(pool.map(create, (1, 2)))
    check("concurrent_revision_creation_has_one_winner", sum(wins) == 1)

    import tempfile
    from pathlib import Path
    from .stores.sqlite_store import SQLiteRecordStore
    from .stores.duckdb_store import DuckDBRecordStore
    with tempfile.TemporaryDirectory() as folder:
        for backend, suffix in ((SQLiteRecordStore, "sqlite"), (DuckDBRecordStore, "duckdb")):
            path = str(Path(folder) / ("history." + suffix))
            durable = backend(path)
            revise(durable, prefixed, expected_version=None)
            revise(durable, {**prefixed, "record_version": "1.1.0",
                             "payload": {"text": "changed"}}, expected_version="1.0.0")
            durable.close()
            reopened = backend(path)
            retained = version_record(reopened, "prefixed", "1.0.0")
            restored = rollback(reopened, "prefixed", "1.0.0", expected_version="1.1.0")
            check("durable_revision_restart_and_rollback:" + suffix,
                  retained == prefixed and restored.version == "1.2.0"
                  and reopened.get("prefixed")["payload"] == prefixed["payload"]
                  and history(reopened, "prefixed")["count"] == 3)
            reopened.close()
            # A durable store returns JSON: a tuple comes back as a list. The
            # write confirmation must compare stored forms, or a committed
            # record is reported as an unknown outcome.
            shaped = backend(str(Path(folder) / ("shapes." + suffix)))
            sequence = {**prefixed, "record_id": "shaped", "payload": {"pairs": (("a", 1), ("b", 2))}}
            try:
                confirmed = revise(shaped, sequence, expected_version=None).current
            except StoreError:
                confirmed = False
            check("durable_write_with_a_tuple_is_confirmed_not_reported_unknown:" + suffix,
                  confirmed and shaped.get("shaped")["payload"] == {"pairs": [["a", 1], ["b", 2]]})
            shaped.close()
    passed = sum(item["passed"] for item in results)
    return {"record_type": "catalog_versioning_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
