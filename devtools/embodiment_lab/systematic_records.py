"""DuckDB projections for systematic experiments; canonical run history stays separate.

These records describe the experiment, source identities, observations and
outcomes. They are not a replacement runtime, intelligence authority or
managed-note collection. JSON files are generated only by database exports.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
import uuid

import duckdb


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class CampaignProjection:
    """One writer for derived experiment records and JSON materializations."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(self.path))
        self.connection.execute("SET threads=2")
        self.connection.execute("CREATE TABLE IF NOT EXISTS experiment_records (namespace VARCHAR, record_id VARCHAR, revision BIGINT, recorded_at TIMESTAMP DEFAULT current_timestamp, payload JSON, digest VARCHAR, PRIMARY KEY(namespace,record_id,revision))")
        self.lock = RLock()

    def record(self, namespace, record_id, payload):
        body = canonical(payload)
        with self.lock:
            revision = self.connection.execute(
                "SELECT coalesce(max(revision),0)+1 FROM experiment_records WHERE namespace=? AND record_id=?",
                [namespace, record_id]).fetchone()[0]
            self.connection.execute(
                "INSERT INTO experiment_records(namespace,record_id,revision,payload,digest) VALUES (?,?,?,?::JSON,?)",
                [namespace, record_id, revision, body, hashlib.sha256(body.encode()).hexdigest()])
        return revision

    def latest(self, namespace, record_id):
        with self.lock:
            row = self.connection.execute(
                "SELECT payload FROM experiment_records WHERE namespace=? AND record_id=? ORDER BY revision DESC LIMIT 1",
                [namespace, record_id]).fetchone()
        return json.loads(row[0]) if row else None

    def export_object(self, path, payload):
        """Export one exact JSON object through DuckDB, never a hand-written file."""
        if type(payload) is not dict or not payload:
            raise ValueError("export_object requires a nonempty JSON object")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(path)
        columns = []
        parameters = []
        for key, value in payload.items():
            columns.append('?::JSON AS "' + key.replace('"', '""') + '"')
            parameters.append(canonical(value))
        with self.lock:
            self.connection.execute("CREATE OR REPLACE TEMP TABLE export_payload AS SELECT " + ",".join(columns), parameters)
            self.connection.execute("COPY export_payload TO '" + str(path).replace("'", "''") + "' (FORMAT JSON, ARRAY false)")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def close(self):
        with self.lock:
            self.connection.execute("CHECKPOINT")
            self.connection.close()

    def refresh_export(self, path, payload):
        """Atomically refresh an owned analytical view from a database export."""
        path = Path(path)
        if not path.resolve().is_relative_to(self.path.parent.resolve()) or path.is_symlink():
            raise ValueError('projection export must stay within its owned directory')
        temporary = path.with_name(path.name + '.export-' + uuid.uuid4().hex)
        self.export_object(temporary, payload)
        os.replace(temporary, path)
