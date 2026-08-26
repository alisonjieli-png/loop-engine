"""SQLite record store: a writable embedded catalog authority.

The portable local profile. Records live in a SQLite database with
transactional writes and optimistic concurrency through version
preconditions. One supported backend, not the ontology.
"""
from __future__ import annotations

import json
import os
import sqlite3

from ..capabilities import StoreCapabilities
from ..protocol import StoreError
from ..query import IntelligenceQuery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    record_id TEXT PRIMARY KEY,
    record_version TEXT NOT NULL,
    intelligence_layer TEXT,
    source_collection TEXT,
    artifact_kind TEXT,
    lifecycle TEXT,
    namespace TEXT,
    attributes TEXT,
    payload TEXT
)
"""


class SQLiteRecordStore:
    """Writable CatalogStore over a SQLite database file."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._con = sqlite3.connect(db_path)
        self._con.execute(_SCHEMA)
        self._con.commit()

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.sqlite", adapter_version="1.0.0",
            adapter_kind="embedded_database", engine="sqlite",
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
            result_formats=("python_records",),
            materializations=("sqlite", "jsonl"),
            authority="authoritative")

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        row = self._con.execute(
            "SELECT * FROM records WHERE record_id = ?",
            (record_id,)).fetchone()
        if row is None:
            return None
        record = self._row_to_record(row)
        if version is not None and record.get("record_version") != version:
            return None
        return record

    @staticmethod
    def _row_to_record(row) -> dict:
        keys = ("record_id", "record_version", "intelligence_layer",
                "source_collection", "artifact_kind", "lifecycle",
                "namespace", "attributes", "payload")
        record = dict(zip(keys, row))
        for key in ("attributes", "payload"):
            value = record.get(key)
            if isinstance(value, str):
                try:
                    record[key] = json.loads(value)
                except json.JSONDecodeError:
                    record[key] = {}
        return record

    def query(self, query: IntelligenceQuery) -> list[dict]:
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
        sql += f" LIMIT {int(query.limit)} OFFSET {int(query.offset)}"
        rows = self._con.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def stream(self, query: IntelligenceQuery):
        for record in self.query(query):
            yield record

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise StoreError("a record needs a non-empty record_id")
        if precondition is not None:
            current = self.get(record_id)
            if current is None or current.get("record_version") != \
                    precondition.get("record_version"):
                raise StoreError(f"precondition failed for {record_id!r}")
        self._con.execute(
            "INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, record.get("record_version", ""),
             record.get("intelligence_layer", ""),
             record.get("source_collection", ""),
             record.get("artifact_kind", ""),
             record.get("lifecycle", ""),
             record.get("namespace", ""),
             json.dumps(record.get("attributes", {})),
             json.dumps(record.get("payload", {}))))
        self._con.commit()
        return {"record_id": record_id, "stored": True}

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery(limit=10_000_000))
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
            count = self._con.execute(
                "SELECT COUNT(*) FROM records").fetchone()[0]
            return {"adapter_id": "local.sqlite", "healthy": True,
                    "record_count": count}
        except sqlite3.Error as exc:
            return {"adapter_id": "local.sqlite", "healthy": False,
                    "error": str(exc)}

    def close(self) -> None:
        self._con.close()


def self_test() -> dict:
    """Prove the SQLite record store round-trips and transacts."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "catalog.sqlite")
        store = SQLiteRecordStore(db_path)
        record = {"record_id": "learned.r1", "record_version": "1.0.0",
                  "intelligence_layer": "code", "source_collection": "learned",
                  "artifact_kind": "loop_canvas", "lifecycle": "active",
                  "namespace": "org:example",
                  "attributes": {"core.problem_type": ["tabular"]},
                  "payload": {"goal": "predict churn"}}
        store.put(record)
        loaded = store.get("learned.r1")
        check("record_round_trips_through_sqlite",
              loaded is not None
              and loaded["attributes"] == {"core.problem_type": ["tabular"]}
              and loaded["payload"] == {"goal": "predict churn"})
        query = IntelligenceQuery(artifact_kinds=("loop_canvas",), limit=10)
        check("query_filters_by_artifact_kind",
              [r["record_id"] for r in store.query(query)] == ["learned.r1"])
        try:
            store.put(dict(record, record_version="2.0.0"),
                      precondition={"record_version": "1.0.0"})
            check("precondition_compare_and_swap", True)
        except StoreError:
            check("precondition_compare_and_swap", False)
        try:
            store.put(dict(record, record_version="3.0.0"),
                      precondition={"record_version": "1.0.0"})
            check("stale_precondition_is_refused", False)
        except StoreError:
            check("stale_precondition_is_refused", True)
        store.close()
    return {"tests": results}
