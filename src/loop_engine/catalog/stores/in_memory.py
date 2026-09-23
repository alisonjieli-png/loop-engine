"""Ephemeral in-memory record store.

The simplest conformant backend: records live in a dict for one process
lifetime. It is the reference implementation for the conformance suite
and the default store for tests and read-only demos. It applies atomic
batches, removals included, under one lock: every precondition is checked
and every record validated before the first change, so a batch changes
everything it names or nothing.
"""
from __future__ import annotations

from copy import deepcopy
from threading import RLock

from ..capabilities import StoreCapabilities
from ..protocol import (ATOMIC_BATCH_OPERATION, ATOMIC_BATCH_VERSION, ATOMIC_REMOVAL_BATCH_VERSION,
                        ATOMIC_REMOVAL_OPERATION, CatalogBatchAcknowledgment, CatalogWriteBatch,
                        PreconditionFailed, StoreError, UnsupportedOperationError)
from ..query import IntelligenceQuery, iter_query_records

#: The atomic batch versions this reference store applies.
APPLIED_BATCH_VERSIONS = (ATOMIC_BATCH_VERSION, ATOMIC_REMOVAL_BATCH_VERSION)


class EphemeralRecordStore:
    """In-memory CatalogStore with query, get, and put."""

    def __init__(self, records: "list[dict] | None" = None) -> None:
        self._records: dict[str, dict] = {}
        self._lock = RLock()
        for record in records or ():
            self.put(record)

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.in-memory", adapter_version="1.0.0",
            adapter_kind="in_memory", engine="python",
            operations={"get": True, "query": True, "stream": True,
                        "write": True, "export": True, "import": True,
                        ATOMIC_BATCH_OPERATION: True, ATOMIC_REMOVAL_OPERATION: True},
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": False, "attributes": False,
                      "limit": False, "order": False},
            transactions={"supported": False, "snapshot_reads": True,
                          "snapshot_scope": "operation",
                          "atomic_preconditions": True, "atomic_import": True,
                          "atomic_batch_version": ATOMIC_BATCH_VERSION,
                          "atomic_removal_batch_version": ATOMIC_REMOVAL_BATCH_VERSION,
                          "atomic_read_set": True,
                          "atomic_scope": "one_store_instance",
                          "writer_topology": "serialized_within_process"},
            result_formats=("python_records",),
            materializations=(),
            authority="authoritative")

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        with self._lock:
            record = self._records.get(record_id)
            if record is None:
                return None
            if version is not None and record.get("record_version") != version:
                return None
            return deepcopy(record)

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def stream(self, query: IntelligenceQuery):
        with self._lock:
            records = deepcopy(list(self._records.values()))
        return iter_query_records(records, query)

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        prepared = _prepared_record(record)
        record_id = prepared["record_id"]
        precondition = deepcopy(precondition)
        if precondition is not None and not (
                isinstance(precondition, dict)
                and ((set(precondition) == {"exists"}
                      and precondition["exists"] is False)
                     or (set(precondition) == {"record_version"}
                         and isinstance(precondition["record_version"], str)))):
            raise StoreError("unsupported record precondition")
        if (precondition is not None and "record_version" in precondition
                and (not isinstance(prepared.get("record_version"), str)
                     or not prepared["record_version"]
                     or prepared["record_version"] == precondition["record_version"])):
            raise StoreError("a guarded update must use a new record_version")
        with self._lock:
            if precondition is not None:
                current = self._records.get(record_id)
                if (("exists" in precondition and current is not None)
                        or ("record_version" in precondition
                            and (current is None or current.get("record_version")
                                 != precondition["record_version"]))):
                    raise PreconditionFailed("record precondition failed")
            self._records[record_id] = prepared
        return {"record_id": record_id, "stored": True}

    def apply_batch(self, request: CatalogWriteBatch) -> CatalogBatchAcknowledgment:
        """Check the whole read set, then apply every write and every removal under one lock."""
        if not isinstance(request, CatalogWriteBatch):
            raise StoreError("a typed atomic batch request is required")
        request.__post_init__()
        if request.record_type not in APPLIED_BATCH_VERSIONS:
            raise UnsupportedOperationError("this atomic batch version is not applied here")
        prepared = [_prepared_record(record) for record in request.records]
        with self._lock:
            for expected in request.preconditions:
                held = self._records.get(expected.record_id)
                if ((expected.must_not_exist and held is not None)
                        or (not expected.must_not_exist
                            and (held is None or held.get("record_version") != expected.record_version))):
                    raise PreconditionFailed("atomic batch read-set precondition failed")
            for record in prepared:
                self._records[record["record_id"]] = record
            for identity in request.removals:
                del self._records[identity]
        return CatalogBatchAcknowledgment(request.digest, True)

    def export(self, selection: dict | None = None) -> dict:
        with self._lock:
            records = deepcopy(list(self._records.values()))
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def import_bundle(self, bundle: dict) -> dict:
        records = bundle.get("records", [])
        if not isinstance(records, list):
            raise StoreError("a bundle needs a records list")
        prepared = [_prepared_record(record) for record in records]
        with self._lock:
            self._records.update((record["record_id"], record) for record in prepared)
        return {"imported": len(records)}

    def health(self) -> dict:
        with self._lock:
            return {"adapter_id": "local.in-memory", "healthy": True,
                    "record_count": len(self._records)}

    def close(self) -> None:
        with self._lock:
            self._records.clear()


def _prepared_record(record: dict) -> dict:
    if (not isinstance(record, dict)
            or not isinstance(record.get("record_id"), str)
            or not record["record_id"]):
        raise StoreError("a record needs a non-empty record_id")
    return deepcopy(record)


def self_test() -> dict:
    """Prove the reference store behaves correctly."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    store = EphemeralRecordStore()
    store.put({"record_id": "r1", "record_version": "1.0.0",
               "intelligence_layer": "code", "source_collection": "core",
               "artifact_kind": "loop_definition", "lifecycle": "active",
               "namespace": "core", "attributes": {}})
    check("get_returns_exact_record",
          store.get("r1")["record_id"] == "r1"
          and store.get("r1", version="2.0.0") is None
          and store.get("missing") is None)
    query = IntelligenceQuery(layers=("code",), limit=10)
    check("query_filters_by_layer", len(store.query(query)) == 1)
    try:
        store.put({"record_id": "r1", "record_version": "2.0.0"},
                  precondition={"record_version": "1.0.0"})
        check("precondition_compare_and_swap", True)
    except StoreError:
        check("precondition_compare_and_swap", False)
    try:
        store.put({"record_id": "r1", "record_version": "3.0.0"},
                  precondition={"record_version": "1.0.0"})
        check("stale_precondition_is_refused", False)
    except StoreError:
        check("stale_precondition_is_refused", True)
    def refuses(action):
        try:
            action()
        except StoreError:
            return True
        return False

    created = {"record_id": "created", "record_version": "1", "payload": {"value": 1}}
    store.put(created, precondition={"exists": False})
    check("absence_guard_creates_once_and_refuses_ambiguous_guards",
          store.get("created") == created
          and refuses(lambda: store.put(created, precondition={"exists": False}))
          and all(refuses(lambda guard=guard: store.put(created, precondition=guard))
                  for guard in ({"exists": 0}, {"exists": True}, {}, {"unknown": True})))
    check("guarded_updates_cannot_reuse_the_expected_version",
          refuses(lambda: store.put({**created, "payload": {"value": 2}},
                                    precondition={"record_version": "1"}))
          and store.get("created") == created)
    check("bundle_validation_precedes_all_mutations",
          refuses(lambda: store.import_bundle({"records": [
              {"record_id": "imported", "record_version": "1"}, {"record_id": ""}]}))
          and store.get("imported") is None)
    stream = store.stream(IntelligenceQuery())
    store.put({"record_id": "later", "record_version": "1"})
    check("stream_has_an_operation_snapshot",
          "later" not in {item["record_id"] for item in stream})

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import time

    class YieldingRecords(dict):
        def get(self, key, default=None):
            value = super().get(key, default)
            time.sleep(0.02)
            return value

    for existing in (False, True):
        contested = EphemeralRecordStore()
        if existing:
            contested.put({"record_id": "race", "record_version": "1"})
        contested._records = YieldingRecords(contested._records)
        barrier = Barrier(2)

        def contend(index):
            barrier.wait(timeout=5)
            try:
                contested.put({"record_id": "race", "record_version": "2",
                               "payload": {"writer": index}},
                              precondition={"record_version": "1"} if existing else {"exists": False})
                return True
            except PreconditionFailed:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            wins = list(pool.map(contend, (1, 2)))
        check("atomic_guard_has_one_concurrent_winner:" + ("version" if existing else "absence"),
              sum(wins) == 1)

    from ..protocol import CatalogRecordPrecondition, require_atomic_removal
    batches = EphemeralRecordStore([{"record_id": name, "record_version": "1"} for name in ("gone", "kept")])
    require_atomic_removal(batches)
    stale = refuses(lambda: batches.apply_batch(CatalogWriteBatch.from_records(
        (), (CatalogRecordPrecondition("gone", "0"),), ("gone",))))
    missing = refuses(lambda: batches.apply_batch(CatalogWriteBatch.from_records(
        (), (CatalogRecordPrecondition("absent", "1"),), ("absent",))))
    partial = refuses(lambda: batches.apply_batch(CatalogWriteBatch.from_records(
        ({"record_id": "written", "record_version": "1"},),
        (CatalogRecordPrecondition("gone", "1"), CatalogRecordPrecondition("written", must_not_exist=True),
         CatalogRecordPrecondition("kept", "0")), ("gone",))))
    check("a_refused_removal_batch_changes_nothing",
          stale and missing and partial and batches.get("gone") is not None and batches.get("written") is None)
    exact = CatalogWriteBatch.from_records(
        ({"record_id": "written", "record_version": "1"},),
        (CatalogRecordPrecondition("gone", "1"), CatalogRecordPrecondition("written", must_not_exist=True)),
        ("gone",))
    try:
        acknowledgment = batches.apply_batch(exact)
    except StoreError:
        acknowledgment = None
    check("an_exact_removal_applies_with_the_writes_of_its_batch",
          acknowledgment is not None and acknowledgment.batch_digest == exact.digest
          and acknowledgment.committed is True and batches.get("gone") is None
          and batches.get("written") is not None and batches.get("kept") is not None)
    return {"tests": results}
