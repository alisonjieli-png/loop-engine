"""SQLite record store: a writable embedded catalog authority.

The portable local profile. Records live in a SQLite database with
transactional writes and optimistic concurrency through version
preconditions. One supported backend, not the ontology.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from ..capabilities import StoreCapabilities
from ..protocol import PreconditionFailed, StoreError, UnsupportedOperationError
from ..query import (
    IntelligenceQuery,
    iter_query_records,
    scalar_sql_predicates,
    snapshot_query,
)

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

    def __init__(self, db_path: str, *, read_only: bool = False) -> None:
        self._db_path = db_path
        self._read_only = read_only
        if type(read_only) is not bool:
            raise StoreError("read_only must be a Boolean")
        if read_only:
            if db_path == ":memory:":
                raise StoreError("read-only mode requires an existing database")
            target = Path(db_path).absolute().as_uri() + "?mode=ro"
        else:
            target = db_path
        try:
            self._con = sqlite3.connect(target, uri=read_only, timeout=5.0)
            self._con.execute("PRAGMA trusted_schema=OFF")
            self._journal_mode = self._con.execute(
                "PRAGMA journal_mode").fetchone()[0]
            if (not read_only and self._journal_mode == "wal"
                    and not _wal_runtime_qualified()):
                raise StoreError(
                    "SQLite runtime is not qualified for WAL writes; use a "
                    "patched SQLite runtime or a separately approved "
                    "rollback-journal database")
            if read_only:
                self._con.execute("SELECT record_id FROM records LIMIT 0")
            else:
                self._con.execute(_SCHEMA)
                self._con.execute(
                    "CREATE INDEX IF NOT EXISTS records_scope "
                    "ON records(namespace, source_collection, artifact_kind)")
                self._con.commit()
        except (sqlite3.Error, StoreError) as exc:
            if hasattr(self, "_con"):
                self._con.close()
            if isinstance(exc, StoreError):
                raise
            raise StoreError("SQLite store could not be opened") from exc

    def capabilities(self) -> StoreCapabilities:
        return StoreCapabilities(
            adapter_id="local.sqlite", adapter_version="1.0.0",
            adapter_kind="embedded_database", engine="sqlite",
            operations={"get": True, "query": True, "stream": True,
                        "write": not self._read_only, "export": True,
                        "import": not self._read_only},
            query_capabilities={"projection": False, "filter": True,
                               "join": False, "aggregation": False,
                               "relationship_traversal": False,
                               "full_text_search": False,
                               "vector_search": False},
            pushdown={"projection": False, "filter": True, "limit": False,
                      "attributes": False, "order": False},
            transactions={"supported": True, "snapshot_reads": True,
                          "snapshot_scope": "statement",
                          "atomic_preconditions": not self._read_only,
                          "atomic_import": not self._read_only,
                          "atomic_scope": "one_database",
                          "writer_topology": "serialized_single_writer",
                          "journal_mode_last_observed": self._journal_mode,
                          "engine_version": sqlite3.sqlite_version},
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
                except json.JSONDecodeError as exc:
                    raise StoreError(
                        "SQLite record contains corrupt JSON") from exc
        return record

    def query(self, query: IntelligenceQuery) -> list[dict]:
        return list(self.stream(query))

    def stream(self, query: IntelligenceQuery):
        query = snapshot_query(query)
        return self._stream_snapshot(query)

    def _stream_snapshot(self, query: IntelligenceQuery):
        if query.limit == 0:
            return
        where, params = scalar_sql_predicates(query)
        cursor = self._con.execute("SELECT * FROM records" + where, params)
        try:
            records = (self._row_to_record(row) for row in cursor)
            yield from iter_query_records(records, query)
        finally:
            cursor.close()

    def put(self, record: dict, *, precondition: dict | None = None) -> dict:
        if self._read_only:
            raise UnsupportedOperationError("SQLite store is read-only")
        values = _record_values(record)
        if precondition is not None and not (
                isinstance(precondition, dict)
                and ((set(precondition) == {"exists"}
                      and precondition["exists"] is False)
                     or (set(precondition) == {"record_version"}
                         and isinstance(precondition["record_version"], str)))):
            raise StoreError("unsupported record precondition")
        try:
            self._begin_write()
            if precondition is not None:
                current = self._con.execute(
                    "SELECT record_version FROM records WHERE record_id = ?",
                    (record["record_id"],)).fetchone()
                if (("exists" in precondition and current is not None)
                        or ("record_version" in precondition
                            and (current is None or current[0]
                                 != precondition["record_version"]))):
                    raise PreconditionFailed("record precondition failed")
            self._write_values(values)
            self._con.commit()
        except (sqlite3.Error, StoreError) as exc:
            self._con.rollback()
            if isinstance(exc, StoreError):
                raise
            raise StoreError("SQLite record write failed") from exc
        return {"record_id": record["record_id"], "stored": True}

    def _write_values(self, values: tuple) -> None:
        self._con.execute(
            "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(record_id) DO UPDATE SET "
            "record_version=excluded.record_version, "
            "intelligence_layer=excluded.intelligence_layer, "
            "source_collection=excluded.source_collection, "
            "artifact_kind=excluded.artifact_kind, lifecycle=excluded.lifecycle, "
            "namespace=excluded.namespace, attributes=excluded.attributes, "
            "payload=excluded.payload", values)

    def _begin_write(self) -> None:
        # Acquiring the transaction refreshes SQLite's cached file mode and
        # excludes a journal-mode change until this transaction terminates.
        self._con.execute("BEGIN IMMEDIATE")
        self._journal_mode = self._con.execute(
            "PRAGMA journal_mode").fetchone()[0]
        if self._journal_mode == "wal" and not _wal_runtime_qualified():
            raise StoreError("SQLite runtime is not qualified for WAL writes")

    def export(self, selection: dict | None = None) -> dict:
        if selection:
            raise UnsupportedOperationError("export selection is not implemented")
        records = self.query(IntelligenceQuery())
        return {"record_type": "catalog_export/v1", "records": records,
                "count": len(records)}

    def import_bundle(self, bundle: dict) -> dict:
        if self._read_only:
            raise UnsupportedOperationError("SQLite store is read-only")
        records = bundle.get("records", [])
        if not isinstance(records, list):
            raise StoreError("a bundle needs a records list")
        values = [_record_values(record) for record in records]
        try:
            self._begin_write()
            for row in values:
                self._write_values(row)
            self._con.commit()
        except (sqlite3.Error, StoreError) as exc:
            self._con.rollback()
            if isinstance(exc, StoreError):
                raise
            raise StoreError("SQLite bundle import failed") from exc
        return {"imported": len(records)}

    def health(self) -> dict:
        try:
            count = self._con.execute(
                "SELECT COUNT(*) FROM records").fetchone()[0]
            return {"adapter_id": "local.sqlite", "healthy": True,
                    "record_count": count, "read_only": self._read_only,
                    "journal_mode_last_observed": self._journal_mode,
                    "engine_version": sqlite3.sqlite_version}
        except sqlite3.Error:
            return {"adapter_id": "local.sqlite", "healthy": False,
                    "error": "sqlite_health_check_failed"}

    def close(self) -> None:
        self._con.close()


def _wal_runtime_qualified() -> bool:
    """Recognize the published fix and patched release branches, not guesses."""
    version = sqlite3.sqlite_version_info
    return (version >= (3, 51, 3)
            or ((3, 50, 7) <= version < (3, 51, 0))
            or ((3, 44, 6) <= version < (3, 45, 0)))


def _record_values(record: dict) -> tuple:
    if not isinstance(record, dict):
        raise StoreError("a record must be an object")
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        raise StoreError("a record needs a non-empty record_id")
    try:
        return (record_id, record.get("record_version", ""),
                record.get("intelligence_layer", ""),
                record.get("source_collection", ""),
                record.get("artifact_kind", ""),
                record.get("lifecycle", ""),
                record.get("namespace", ""),
                json.dumps(record.get("attributes", {}), allow_nan=False),
                json.dumps(record.get("payload", {}), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise StoreError("record values must be JSON serializable") from exc


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
        created = dict(record, record_id="new", record_version="1")
        store.put(created, precondition={"exists": False})
        try:
            store.put(dict(created, payload={"changed": True}),
                      precondition={"exists": False})
            check("create_only_refuses_existing_record", False)
        except StoreError:
            check("create_only_refuses_existing_record",
                  store.get("new")["payload"] == created["payload"])
        try:
            store.put(created, precondition={"exists": 0})
            check("ambiguous_precondition_is_refused", False)
        except StoreError:
            check("ambiguous_precondition_is_refused", True)

        store.put(dict(record, record_id="foreign", namespace="other",
                       attributes={"selected": True}))
        store.put(dict(record, record_id="unselected",
                       attributes={"selected": False}))
        store.put(dict(record, record_id="selected",
                       attributes={"selected": True}))
        scoped = IntelligenceQuery(
            namespaces=("org:example",), attributes={"selected": {"equals": True}},
            limit=1)
        check("sqlite_filters_namespace_and_attributes_before_limit",
              [r["record_id"] for r in store.query(scoped)] == ["selected"])
        iterator = store.stream(scoped)
        scoped.attributes.clear()
        check("sqlite_query_is_frozen_before_first_iteration",
              [r["record_id"] for r in iterator] == ["selected"])
        check("sqlite_zero_limit_stream_returns_nothing",
              list(store.stream(IntelligenceQuery(limit=0))) == [])

        store._con.execute(
            "CREATE TRIGGER reject_fixture BEFORE INSERT ON records "
            "WHEN NEW.record_id = 'reject_import' BEGIN "
            "SELECT RAISE(ABORT, 'fixture'); END")
        store._con.commit()
        try:
            store.import_bundle({"records": [
                dict(record, record_id="before_reject"),
                dict(record, record_id="reject_import")]})
            check("bundle_import_rolls_back_after_database_failure", False)
        except StoreError:
            check("bundle_import_rolls_back_after_database_failure",
                  store.get("before_reject") is None
                  and store.get("reject_import") is None)
        store._con.execute("DROP TRIGGER reject_fixture")
        store._con.execute(
            "UPDATE records SET payload = ? WHERE record_id = ?",
            ("not-json", "new"))
        store._con.commit()
        try:
            store.get("new")
            check("corrupt_record_does_not_become_empty_payload", False)
        except StoreError:
            check("corrupt_record_does_not_become_empty_payload", True)
        store.close()

        readonly = SQLiteRecordStore(db_path, read_only=True)
        before_bytes = Path(db_path).read_bytes()
        try:
            readonly.put(record)
            check("readonly_store_refuses_mutation", False)
        except UnsupportedOperationError:
            check("readonly_store_refuses_mutation",
                  not readonly.capabilities().supports("write")
                  and Path(db_path).read_bytes() == before_bytes)
        readonly.close()
        missing_path = os.path.join(tmp, "missing.sqlite")
        try:
            SQLiteRecordStore(missing_path, read_only=True)
            check("readonly_open_does_not_create_database", False)
        except StoreError:
            check("readonly_open_does_not_create_database",
                  not os.path.exists(missing_path))

        # Independent connections contend for one version. The lock begins
        # before reading the precondition, so only one writer can accept it.
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        contest = os.path.join(tmp, "contest.sqlite")
        seed = SQLiteRecordStore(contest)
        seed.put(dict(record, record_id="contested", record_version="1"))
        seed.close()
        barrier = Barrier(2)

        def contend(index):
            writer = SQLiteRecordStore(contest)
            try:
                barrier.wait(timeout=5)
                writer.put(dict(record, record_id="contested",
                                record_version="2", payload={"writer": index}),
                           precondition={"record_version": "1"})
                return True
            except StoreError:
                return False
            finally:
                writer.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            wins = list(pool.map(contend, (1, 2)))
        check("atomic_version_precondition_has_one_concurrent_winner",
              sum(wins) == 1)
        from unittest.mock import patch
        with patch.object(sqlite3, "sqlite_version_info", (3, 46, 1)):
            old_rejected = not _wal_runtime_qualified()
        with patch.object(sqlite3, "sqlite_version_info", (3, 51, 3)):
            fixed_accepted = _wal_runtime_qualified()
        with patch.object(sqlite3, "sqlite_version_info", (3, 44, 6)):
            backport_accepted = _wal_runtime_qualified()
        check("wal_qualification_distinguishes_affected_and_patched_runtimes",
              old_rejected and fixed_accepted and backport_accepted)
        changed_mode = os.path.join(tmp, "mode_change.sqlite")
        writer = SQLiteRecordStore(changed_mode)
        writer.put(dict(record, record_id="mode", record_version="1"))
        external = sqlite3.connect(changed_mode)
        external.execute("PRAGMA journal_mode=WAL")
        external.close()
        refused_operations = []
        with patch.object(sqlite3, "sqlite_version_info", (3, 46, 1)):
            for operation in (
                lambda: writer.put(dict(record, record_id="mode", record_version="2")),
                lambda: writer.import_bundle({"records": [dict(record, record_id="new_mode")]}),
            ):
                try:
                    operation()
                    refused_operations.append(False)
                except StoreError:
                    refused_operations.append(True)
        check("external_wal_mode_switch_is_refused_inside_each_write_transaction",
              all(refused_operations)
              and writer.get("mode")["record_version"] == "1"
              and writer.get("new_mode") is None
              and not writer._con.in_transaction)
        writer.close()
    return {"tests": results}
