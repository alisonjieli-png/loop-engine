"""Ephemeral in-memory record store.

The simplest conformant backend: records live in a dict for one process
lifetime. It is the reference implementation for the conformance suite
and the default store for tests and read-only demos.
"""
from __future__ import annotations

from ..capabilities import StoreCapabilities
from ..protocol import StoreError
from ..query import IntelligenceQuery


class EphemeralRecordStore:
    """In-memory CatalogStore with query, get, and put."""

    def __init__(self, records: "list[dict] | None" = None) -> None:
        self._records: dict[str, dict] = {}
        for record in records or ():
            self.put(record)

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.in-memory", adapter_version="1.0.0",
            adapter_kind="in_memory", engine="python",
            operations={"get": True, "query": True, "stream": True,
                        "write": True, "export": True, "import": True},
            query_capabilities={"projection": True, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": True, "filter": True, "limit": True,
                      "order": False},
            transactions={"supported": False, "snapshot_reads": True},
            result_formats=("python_records",),
            materializations=("jsonl",),
            authority="authoritative")

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        record = self._records.get(record_id)
        if record is None:
            return None
        if version is not None and record.get("record_version") != version:
            return None
        return dict(record)

    def query(self, query: IntelligenceQuery) -> list[dict]:
        matched = [dict(r) for r in self._records.values()
                   if query.matches(r)]
        stop = None if query.limit is None else query.offset + query.limit
        return matched[query.offset:stop]

    def stream(self, query: IntelligenceQuery):
        for record in self.query(query):
            yield record

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise StoreError("a record needs a non-empty record_id")
        if precondition is not None:
            current = self._records.get(record_id)
            if current is None or current.get("record_version") != \
                    precondition.get("record_version"):
                raise StoreError(
                    f"precondition failed for {record_id!r}")
        self._records[record_id] = dict(record)
        return {"record_id": record_id, "stored": True}

    def export(self, selection: dict | None = None) -> dict:
        records = [dict(r) for r in self._records.values()]
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def import_bundle(self, bundle: dict) -> dict:
        records = bundle.get("records", [])
        if not isinstance(records, list):
            raise StoreError("a bundle needs a records list")
        for record in records:
            self.put(record)
        return {"imported": len(records)}

    def health(self) -> dict:
        return {"adapter_id": "local.in-memory", "healthy": True,
                "record_count": len(self._records)}

    def close(self) -> None:
        self._records.clear()


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
    return {"tests": results}
