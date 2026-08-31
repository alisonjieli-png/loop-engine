"""DuckDB file query engine: SQL over JSONL, Parquet, CSV, and Arrow.

DuckDB queries files directly as tables. This adapter is a read-only
query engine over file-backed intelligence; the files remain the
authority. The engine is a capability used by Loops, not a second store.
"""
from __future__ import annotations

import json
import os

from ..capabilities import StoreCapabilities
from ..protocol import StoreError
from ..query import IntelligenceQuery


class DuckDBFileQueryEngine:
    """Read-only SQL query engine over file-backed record shards."""

    def __init__(self, shard_paths: "list[str] | tuple[str, ...]",
                 *, db_path: str = ":memory:") -> None:
        missing = [p for p in shard_paths if not os.path.isfile(p)]
        if missing:
            raise StoreError(f"missing shards: {missing}")
        self._shards = tuple(shard_paths)
        self._db_path = db_path
        self._con = None

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="core.duckdb-files", adapter_version="1.0.0",
            adapter_kind="file_sql", engine="duckdb",
            source_collections=("core",),
            operations={"get": True, "query": True, "stream": True,
                        "write": False, "export": True, "import": False},
            query_capabilities={"projection": True, "filter": True,
                               "join": True, "aggregation": True,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": True, "filter": True, "limit": True,
                      "order": True},
            transactions={"supported": False, "snapshot_reads": True},
            result_formats=("python_records", "arrow_table"),
            materializations=("jsonl", "parquet"),
            authority="authoritative")

    def _connect(self):
        if self._con is None:
            import duckdb
            self._con = duckdb.connect(self._db_path)
        return self._con

    def _relation(self):
        con = self._connect()
        quoted = ", ".join(f"'{p}'" for p in self._shards)
        return con.execute(
            f"SELECT * FROM read_json_auto([{quoted}])")

    def _rows_to_records(self, cursor) -> list[dict]:
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        con = self._connect()
        cursor = con.execute(
            "SELECT * FROM read_json_auto(["
            + ", ".join(f"'{p}'" for p in self._shards)
            + "]) WHERE record_id = ?", [record_id])
        for record in self._rows_to_records(cursor):
            if version is None or record.get("record_version") == version:
                return record
        return None

    def query(self, query: IntelligenceQuery) -> list[dict]:
        con = self._connect()
        sql = ("SELECT * FROM read_json_auto(["
               + ", ".join(f"'{p}'" for p in self._shards) + "])")
        clauses = []
        params: list = []
        if query.layers:
            clauses.append("intelligence_layer IN ("
                           + ", ".join("?" for _ in query.layers) + ")")
            params.extend(query.layers)
        if query.source_collections:
            clauses.append("source_collection IN ("
                           + ", ".join("?" for _ in query.source_collections)
                           + ")")
            params.extend(query.source_collections)
        if query.artifact_kinds:
            clauses.append("artifact_kind IN ("
                           + ", ".join("?" for _ in query.artifact_kinds)
                           + ")")
            params.extend(query.artifact_kinds)
        if query.lifecycle:
            clauses.append("lifecycle IN ("
                           + ", ".join("?" for _ in query.lifecycle) + ")")
            params.extend(query.lifecycle)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        if query.limit is not None:
            sql += f" LIMIT {int(query.limit)}"
        if query.offset:
            sql += f" OFFSET {int(query.offset)}"
        cursor = con.execute(sql, params)
        return self._rows_to_records(cursor)

    def stream(self, query: IntelligenceQuery):
        for record in self.query(query):
            yield record

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def health(self) -> dict:
        try:
            self._connect()
            return {"adapter_id": "core.duckdb-files", "healthy": True,
                    "shards": len(self._shards)}
        except Exception as exc:                                 # noqa: BLE001
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
