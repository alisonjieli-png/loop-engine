"""Package JSONL store: streaming reads over neutral record shards.

The authoritative Core representation. Records stream line by line; the
store never loads a whole shard into memory unless a query requires it.
"""
from __future__ import annotations

import json
import os

from ..capabilities import StoreCapabilities
from ..protocol import StoreError, UnsupportedOperationError
from ..query import IntelligenceQuery, iter_query_records


class PackageJsonlStore:
    """Read-only CatalogStore over package-shipped JSONL shards."""

    def __init__(self, shard_paths: "list[str] | tuple[str, ...]") -> None:
        missing = [p for p in shard_paths if not os.path.isfile(p)]
        if missing:
            raise StoreError(f"missing JSONL shards: {missing}")
        self._shards = tuple(shard_paths)

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="core.package-jsonl", adapter_version="1.0.0",
            adapter_kind="package_jsonl", engine="python",
            source_collections=("core",),
            operations={"get": True, "query": True, "stream": True,
                        "write": False, "export": True, "import": False},
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": False, "attributes": False,
                      "limit": False, "order": False},
            transactions={"supported": False, "snapshot_reads": False},
            result_formats=("python_records",),
            materializations=("jsonl",),
            authority="authoritative")

    def _iter_records(self):
        for shard in self._shards:
            with open(shard, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise StoreError(
                            f"corrupt JSONL line in {shard}: {exc}") from exc
                    if not isinstance(record, dict):
                        raise StoreError("catalog JSONL records must be objects")
                    yield record

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        for record in self._iter_records():
            if record.get("record_id") == record_id:
                if version is None or record.get("record_version") == version:
                    return record
        return None

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def stream(self, query: IntelligenceQuery):
        return iter_query_records(self._iter_records(), query)

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        raise UnsupportedOperationError("package JSONL store is read-only")

    def import_bundle(self, bundle: dict) -> dict:
        raise UnsupportedOperationError("package JSONL store is read-only")

    def export(self, selection: dict | None = None) -> dict:
        records = list(self._iter_records())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def health(self) -> dict:
        return {"adapter_id": "core.package-jsonl", "healthy": True,
                "shards": len(self._shards)}

    def close(self) -> None:
        return None


def self_test() -> dict:
    """Prove streaming reads, filtering, and corruption refusal."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        shard = os.path.join(tmp, "part-00000.jsonl")
        with open(shard, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "record_id": "core.r1", "record_version": "1.0.0",
                "intelligence_layer": "code", "source_collection": "core",
                "artifact_kind": "loop_definition", "lifecycle": "active",
                "namespace": "core", "attributes": {}}) + "\n")
            handle.write(json.dumps({
                "record_id": "core.r2", "record_version": "1.0.0",
                "intelligence_layer": "context",
                "source_collection": "core",
                "artifact_kind": "intelligence_record",
                "lifecycle": "active", "namespace": "core",
                "attributes": {}}) + "\n")
        store = PackageJsonlStore((shard,))
        check("get_resolves_exact_record",
              store.get("core.r1")["record_id"] == "core.r1"
              and store.get("core.r1", version="9.0.0") is None)
        query = IntelligenceQuery(layers=("code",), limit=10)
        check("query_filters_by_layer", len(store.query(query)) == 1)
        check("stream_yields_same_records",
              [r["record_id"] for r in store.stream(query)] == ["core.r1"])
        check("read_only_store_refuses_write",
              not store.capabilities().supports("write"))
        with open(shard, "a", encoding="utf-8") as handle:
            handle.write("{not json\n")
        try:
            store.query(IntelligenceQuery(limit=10))
            check("corrupt_line_is_refused", False)
        except StoreError:
            check("corrupt_line_is_refused", True)
    return {"tests": results}
