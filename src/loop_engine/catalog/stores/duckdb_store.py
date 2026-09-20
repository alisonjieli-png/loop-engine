"""DuckDB record store: a persistent DuckDB-backed catalog authority.

The writable local profile. Records live in DuckDB tables; content
addressing and version checks stay explicit. This is one supported
backend, not the ontology.
"""
from __future__ import annotations

import os
from copy import deepcopy
from threading import RLock

from ..capabilities import StoreCapabilities
from ..protocol import PreconditionFailed, StoreError
from ..query import (
    IntelligenceQuery,
    iter_query_records,
    scalar_sql_predicates,
    snapshot_query,
)

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
        self._lock = RLock()
        self._connect()
        self._con.execute(_SCHEMA)

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.duckdb", adapter_version="1.0.0",
            adapter_kind="embedded_database", engine="duckdb",
            operations={"get": True, "query": True, "stream": True,
                        "write": True, "export": True, "import": True},
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": True, "attributes": False,
                      "limit": False, "order": False},
            transactions={"supported": True, "snapshot_reads": True,
                          "snapshot_scope": "statement",
                          "atomic_preconditions": True, "atomic_import": True,
                          "atomic_scope": "one_database",
                          "writer_topology": "optimistic_within_process"},
            result_formats=("python_records",),
            materializations=("duckdb",),
            authority="authoritative")

    def _connect(self):
        if self._con is None:
            import duckdb
            self._con = duckdb.connect(self._db_path)
        return self._con

    def get(self, record_id: str, version: str | None = None) -> dict | None:
        with self._lock:
            rows = self._connect().execute(
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
                except _json.JSONDecodeError as exc:
                    raise StoreError("DuckDB record contains corrupt JSON") from exc
        return record

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def stream(self, query: IntelligenceQuery):
        query = snapshot_query(query)
        where, params = scalar_sql_predicates(query)
        def records():
            with self._lock:
                cursor = self._connect().cursor()
            try:
                cursor.execute("SELECT * FROM records" + where, params)
                for row in iter(cursor.fetchone, None):
                    yield self._row_to_record(row)
            finally:
                cursor.close()
        return iter_query_records(records(), query)

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        values = _record_values(record)
        record_id = values[0]
        precondition = deepcopy(precondition)
        if precondition is not None and not (
                isinstance(precondition, dict)
                and ((set(precondition) == {"exists"}
                      and precondition["exists"] is False)
                     or (set(precondition) == {"record_version"}
                         and isinstance(precondition["record_version"], str)))):
            raise StoreError("unsupported record precondition")
        if (precondition is not None and "record_version" in precondition
                and (not isinstance(values[1], str) or not values[1]
                     or values[1] == precondition["record_version"])):
            raise StoreError("a guarded update must use a new record_version")
        with self._lock:
            con = self._connect()
            try:
                con.execute("BEGIN TRANSACTION")
                if precondition is not None:
                    current = con.execute(
                        "SELECT record_version FROM records WHERE record_id = ?",
                        [record_id]).fetchone()
                    if (("exists" in precondition and current is not None)
                            or ("record_version" in precondition
                                and (current is None or current[0]
                                     != precondition["record_version"]))):
                        raise PreconditionFailed("record precondition failed")
                self._write_values(values)
                con.execute("COMMIT")
            except Exception as exc:
                self._rollback()
                if isinstance(exc, StoreError):
                    raise
                raise StoreError("DuckDB record write was not confirmed") from exc
        return {"record_id": record_id, "stored": True}

    def _write_values(self, values: tuple) -> None:
        self._connect().execute(
            "INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values)

    def _rollback(self) -> None:
        try:
            self._connect().execute("ROLLBACK")
        except Exception:
            # A failed commit may already have ended the transaction. The
            # caller still receives an unconfirmed-write failure, never success.
            pass

    def export(self, selection: dict | None = None) -> dict:
        records = self.query(IntelligenceQuery())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def import_bundle(self, bundle: dict) -> dict:
        records = bundle.get("records", [])
        if not isinstance(records, list):
            raise StoreError("a bundle needs a records list")
        values = [_record_values(record) for record in records]
        with self._lock:
            try:
                self._connect().execute("BEGIN TRANSACTION")
                for row in values:
                    self._write_values(row)
                self._connect().execute("COMMIT")
            except Exception as exc:
                self._rollback()
                if isinstance(exc, StoreError):
                    raise
                raise StoreError("DuckDB bundle import was not confirmed") from exc
        return {"imported": len(records)}

    def health(self) -> dict:
        try:
            con = self._connect()
            count = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            return {"adapter_id": "local.duckdb", "healthy": True,
                    "record_count": count}
        except Exception as exc:
            return {"adapter_id": "local.duckdb", "healthy": False,
                    "error": str(exc)}

    def close(self) -> None:
        with self._lock:
            if self._con is not None:
                self._con.close()
                self._con = None


def _record_values(record: dict) -> tuple:
    import json
    if (not isinstance(record, dict)
            or not isinstance(record.get("record_id"), str)
            or not record["record_id"]):
        raise StoreError("a record needs a non-empty record_id")
    try:
        return (record["record_id"], record.get("record_version", ""),
                record.get("intelligence_layer", ""),
                record.get("source_collection", ""),
                record.get("artifact_kind", ""), record.get("lifecycle", ""),
                record.get("namespace", ""),
                json.dumps(record.get("attributes", {}), allow_nan=False),
                json.dumps(record.get("payload", {}), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise StoreError("record values must be finite JSON") from exc


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
        def refuses(action):
            try:
                action()
            except StoreError:
                return True
            return False

        created = dict(record, record_id="created", record_version="1")
        store.put(created, precondition={"exists": False})
        check("absence_guard_creates_once_and_refuses_ambiguous_guards",
              store.get("created")["payload"] == created["payload"]
              and refuses(lambda: store.put(created, precondition={"exists": False}))
              and all(refuses(lambda guard=guard: store.put(created, precondition=guard))
                      for guard in ({"exists": 0}, {"exists": True}, {}, {"unknown": True})))
        check("guarded_updates_cannot_reuse_the_expected_version",
              refuses(lambda: store.put(dict(created, payload={"changed": True}),
                                        precondition={"record_version": "1"}))
              and store.get("created")["payload"] == created["payload"])
        store.put(dict(created, record_version="2"), precondition={"record_version": "1"})
        check("stale_version_guard_is_refused",
              refuses(lambda: store.put(dict(created, record_version="3"),
                                        precondition={"record_version": "1"}))
              and store.get("created")["record_version"] == "2")
        from unittest.mock import patch
        original_write = store._write_values

        def fail_second(values):
            if values[0] == "reject_import":
                raise StoreError("injected import interruption")
            original_write(values)

        with patch.object(store, "_write_values", fail_second):
            refused = refuses(lambda: store.import_bundle({"records": [
                dict(record, record_id="before_reject"),
                dict(record, record_id="reject_import")]}))
        check("bundle_import_rolls_back_after_write_failure",
              refused and store.get("before_reject") is None
              and store.get("reject_import") is None)
        check("nonfinite_payload_is_refused_before_mutation",
              refuses(lambda: store.put(dict(record, record_id="nonfinite", payload={"value": float("nan")})))
              and store.get("nonfinite") is None)
        store.close()

        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        for existing in (False, True):
            contest_path = os.path.join(tmp, "contest-" + str(existing) + ".duckdb")
            seed = DuckDBRecordStore(contest_path)
            if existing:
                seed.put(dict(record, record_id="race", record_version="1"))
            seed.close()
            barrier = Barrier(2)

            class ContendedStore(DuckDBRecordStore):
                def _write_values(self, values):
                    barrier.wait(timeout=5)
                    super()._write_values(values)

            def contend(index):
                writer = ContendedStore(contest_path)
                try:
                    writer.put(dict(record, record_id="race", record_version="2",
                                    payload={"writer": index}),
                               precondition={"record_version": "1"} if existing else {"exists": False})
                    return True
                except StoreError:
                    return False
                finally:
                    writer.close()

            with ThreadPoolExecutor(max_workers=2) as pool:
                wins = list(pool.map(contend, (1, 2)))
            check("atomic_guard_has_one_concurrent_winner:" + ("version" if existing else "absence"),
                  sum(wins) == 1)
    return {"tests": results}
