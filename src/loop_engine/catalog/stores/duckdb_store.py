"""DuckDB record store: a persistent DuckDB-backed catalog authority.

The writable local profile. Records live in DuckDB tables; content
addressing and version checks stay explicit. This is one supported
backend, not the ontology.
"""
from __future__ import annotations

import os

from ..capabilities import StoreCapabilities
from ..protocol import StoreError
from ..query import IntelligenceQuery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id VARCHAR PRIMARY KEY,
    record_version VARCHAR NOT NULL,
    intelligence_layer VARCHAR,
    source_collection VARCHAR,
    artifact_kind VARCHAR,
    lifecycle VARCHAR,
    namespace VARCHAR,
    attributes JSON,
    payload JSON
)
"""


class DuckDBRecordStore:
    """Writable CatalogStore over a DuckDB database file."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._con = None
        self._connect()
        self._con.execute(_SCHEMA)

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.duckdb", adapter_version="1.0.0",
            adapter_kind="embedded_database", engine="duckdb",
            operations={"get": True, "query": True, "stream": True,
                        "write": True, "export": True, "import": True},
            query_capabilities={"projection": True, "filter": True,
                               "join": True, "aggregation": True,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": True, "filter": True, "limit": True,
                      "order": True},
            transactions={"supported": True, "snapshot_reads": True},
            result_formats=("python_records", "arrow_table"),
            materializations=("duckdb", "jsonl", "parquet"),
            authority="authoritative")

    def _connect(self):
        if self._con is None:
            import duckdb
            self._con = duckdb.connect(self._db_path)
        return self._con

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        con = self._connect()
        rows = con.execute(
            "SELECT * FROM records WHERE record_id = ?",
            [record_id]).fetchall()
        for row in rows:
            record = self._row_to_record(row)
            if version is None or record.get("record_version") == version:
                return record
        return None

    @staticmethod
    def _row_to_record(row) -> dict:
        import json as _json
        keys = ("record_id", "record_version", "intelligence_layer",
                "source_collection", "artifact_kind", "lifecycle",
                "namespace", "attributes", "payload")
        record = dict(zip(keys, row))
        for key in ("attributes", "payload"):
            value = record.get(key)
            if isinstance(value, str):
                try:
                    record[key] = _json.loads(value)
                except _json.JSONDecodeError:
                    record[key] = {}
        return record

    def query(self, query: IntelligenceQuery) -> list[dict]:
        con = self._connect()
        sql = "SELECT * FROM records"
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
        rows = con.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def stream(self, query: IntelligenceQuery):
        for record in self.query(query):
            yield record

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        import json as _json
        con = self._connect()
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise StoreError("a record needs a non-empty record_id")
        if precondition is not None:
            current = self.get(record_id)
            if current is None or current.get("record_version") != \
                    precondition.get("record_version"):
                raise StoreError(f"precondition failed for {record_id!r}")
        con.execute(
            "INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [record_id, record.get("record_version", ""),
             record.get("intelligence_layer", ""),
             record.get("source_collection", ""),
             record.get("artifact_kind", ""),
             record.get("lifecycle", ""),
             record.get("namespace", ""),
             _json.dumps(record.get("attributes", {})),
             _json.dumps(record.get("payload", {}))])
        return {"record_id": record_id, "stored": True}

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery())
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
        try:
            con = self._connect()
            count = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            return {"adapter_id": "local.duckdb", "healthy": True,
                    "record_count": count}
        except Exception as exc:                                 # noqa: BLE001
            return {"adapter_id": "local.duckdb", "healthy": False,
                    "error": str(exc)}

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None


def self_test() -> dict:
    """Prove the DuckDB record store round-trips records."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "catalog.duckdb")
        try:
            store = DuckDBRecordStore(db_path)
        except StoreError as exc:
            check("duckdb_store_connects", False, str(exc))
            return {"tests": results}
        check("duckdb_store_connects", True)
        record = {"record_id": "learned.r1", "record_version": "1.0.0",
                  "intelligence_layer": "code", "source_collection": "learned",
                  "artifact_kind": "loop_canvas", "lifecycle": "active",
                  "namespace": "org:example",
                  "attributes": {"core.problem_type": ["tabular"]},
                  "payload": {"goal": "predict churn"}}
        store.put(record)
        loaded = store.get("learned.r1")
        check("record_round_trips_through_duckdb",
              loaded is not None
              and loaded["attributes"] == {"core.problem_type": ["tabular"]}
              and loaded["payload"] == {"goal": "predict churn"})
        query = IntelligenceQuery(artifact_kinds=("loop_canvas",), limit=10)
        check("query_filters_by_artifact_kind",
              [r["record_id"] for r in store.query(query)] == ["learned.r1"])
        store.close()
    return {"tests": results}
