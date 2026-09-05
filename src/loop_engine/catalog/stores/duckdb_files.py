"""DuckDB file query engine: typed queries over JSONL record shards.

DuckDB queries files directly as tables. This adapter is a read-only
query engine over file-backed intelligence; the files remain the
authority. The engine is a capability used by Loops, not a second store.
"""
from __future__ import annotations

import json
import os

from ..capabilities import StoreCapabilities
from ..protocol import StoreError, UnsupportedOperationError
from ..query import (
    _FACET_COLUMNS,
    IntelligenceQuery,
    iter_query_records,
    scalar_sql_predicates,
    snapshot_query,
)


def _exact_local_file(path: str) -> str:
    """This unbound reader accepts literal local files, not globs or symlinks."""
    path = os.path.abspath(os.fspath(path))
    if any(character in path for character in "*?["):
        raise StoreError("file query sources cannot contain glob metacharacters")
    if os.path.realpath(path) != path:
        raise StoreError("file query sources cannot traverse symbolic links")
    if not os.path.isfile(path):
        raise StoreError("file query source must be an existing local file")
    return path


class DuckDBFileQueryEngine:
    """Read-only SQL query engine over file-backed record shards."""

    def __init__(self, shard_paths: "list[str] | tuple[str, ...]",
                 *, db_path: str = ":memory:") -> None:
        self._shards = tuple(_exact_local_file(path) for path in shard_paths)
        self._db_path = db_path if db_path == ":memory:" else _exact_local_file(db_path)
        self._con = None

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="core.duckdb-files", adapter_version="1.0.0",
            adapter_kind="file_sql", engine="duckdb",
            source_collections=("core",),
            operations={"get": True, "query": True, "stream": True,
                        "write": False, "export": True, "import": False},
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": True, "attributes": False,
                      "limit": False, "order": False},
            transactions={"supported": False, "snapshot_reads": False},
            result_formats=("python_records",),
            materializations=("jsonl",),
            authority="authoritative")

    def _connect(self):
        if self._con is None:
            import duckdb
            if self._db_path != ":memory:":
                _exact_local_file(self._db_path)
            self._con = duckdb.connect(
                self._db_path, read_only=self._db_path != ":memory:")
        return self._con

    def _records(self, where: str, params: list):
        """Bind source paths as data and retain complete original JSON records."""
        if not self._shards:
            return
        shards = [_exact_local_file(path) for path in self._shards]
        facets = ", ".join(
            f"json_extract_string(json, '$.{column}') AS {column}"
            for _field, column in _FACET_COLUMNS)
        sql = ("SELECT json FROM (SELECT json, " + facets
               + " FROM read_json_objects(?, format='newline_delimited'))"
               + where)
        cursor = self._connect().cursor()
        try:
            cursor.execute(sql, [shards, *params])
            for row in iter(cursor.fetchone, None):
                record = json.loads(row[0])
                if not isinstance(record, dict):
                    raise StoreError("catalog JSONL records must be objects")
                yield record
        finally:
            cursor.close()

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        records = self._records(
            " WHERE json_extract_string(json, '$.record_id') = ?", [record_id])
        try:
            for record in records:
                if (record.get("record_id") == record_id
                        and (version is None or record.get("record_version") == version)):
                    return record
        finally:
            records.close()
        return None

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def stream(self, query: IntelligenceQuery):
        query = snapshot_query(query)
        where, params = scalar_sql_predicates(query)
        return iter_query_records(self._records(where, params), query)

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        raise UnsupportedOperationError("DuckDB file query engine is read-only")

    def import_bundle(self, bundle: dict) -> dict:
        raise UnsupportedOperationError("DuckDB file query engine is read-only")

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def health(self) -> dict:
        try:
            for path in self._shards:
                _exact_local_file(path)
            self._connect()
            return {"adapter_id": "core.duckdb-files", "healthy": True,
                    "shards": len(self._shards)}
        except Exception as exc:
            return {"adapter_id": "core.duckdb-files", "healthy": False,
                    "error": str(exc)}

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None


def self_test() -> dict:
    """Prove DuckDB SQL over files agrees with direct record iteration."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        shard = os.path.join(tmp, "part-00000.jsonl")
        records = [
            {"record_id": "core.r1", "record_version": "1.0.0",
             "intelligence_layer": "code", "source_collection": "core",
             "artifact_kind": "loop_definition", "lifecycle": "active",
             "namespace": "core", "attributes": {}},
            {"record_id": "core.r2", "record_version": "1.0.0",
             "intelligence_layer": "context", "source_collection": "core",
             "artifact_kind": "intelligence_record", "lifecycle": "active",
             "namespace": "core", "attributes": {}},
        ]
        with open(shard, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        try:
            engine = DuckDBFileQueryEngine((shard,))
        except StoreError as exc:
            check("duckdb_engine_connects", False, str(exc))
            return {"tests": results}
        check("duckdb_engine_connects", True)
        check("get_resolves_exact_record",
              engine.get("core.r1")["record_id"] == "core.r1")
        query = IntelligenceQuery(layers=("code",), limit=10)
        check("sql_query_filters_by_layer",
              [r["record_id"] for r in engine.query(query)] == ["core.r1"])
        check("sql_results_agree_with_direct_iteration",
              {r["record_id"] for r in engine.query(
                  IntelligenceQuery(limit=10))} == {"core.r1", "core.r2"})
        engine.close()
    return {"tests": results}
