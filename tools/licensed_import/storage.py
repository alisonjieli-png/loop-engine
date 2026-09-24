"""Where imported candidates live: bodies by digest, records in the catalogue store.

Committing hundreds of thousands of third-party files to git would make
every clone carry them forever and would put licensed text in the public
repository. The import therefore keeps two stores outside git, each behind
an edge the service already reads:

```text
Import store root (a folder on this machine; object storage later, behind the same edges)
├── bodies/        catalogue_body_store/v1, engine service_volume_files: each file once, named
│                  sha256/<first two>/<digest>, written once and never replaced
├── records.db     catalog_store/v1, engine local.sqlite: one record per candidate version, idea,
│                  withdrawal and source state, written in atomic batches with exact preconditions
└── quarantine/    every fetched byte, read-only, named by its digest, never executed
```

The repository keeps only the evidence of each run: counts, the compact
candidate index with digests, refusals, duplicates and the request records.
A candidate version is one immutable record. A new upstream version is a
new record, and the version it replaces changes only its lifecycle, to
superseded; a deleted upstream file or a licence that stopped allowing
copies writes a withdrawal record and changes the candidate's lifecycle to
withdrawn. History is never deleted.
"""
from __future__ import annotations

import os
from pathlib import Path

from loop_engine.catalog.protocol import (
    CatalogRecordPrecondition, CatalogWriteBatch, require_atomic_batch)
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.library_ingestion.quarantine import Quarantine
from loop_engine.core.library_ingestion.record_rules import canonical_digest
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore, require_body_store

from .records import (
    CANDIDATE_LIFECYCLE, IDEA_LIFECYCLE, KIND_LAYERS, SOURCE_STATE_LIFECYCLE, WITHDRAWAL_LIFECYCLE,
    WITHDRAWN_LIFECYCLE)

NAMESPACE = "library.import"
SUPERSEDED_LIFECYCLE = "superseded"
_BATCH_RECORDS = 200


def record_version(payload: dict) -> str:
    return canonical_digest(payload)


class ImportStore:
    """The body store, the record store and the quarantine under one root outside the repository."""

    def __init__(self, root, *, writes_authorized: bool) -> None:
        if type(writes_authorized) is not bool:
            raise ValueError("store write authority is an explicit Boolean")
        self.root = Path(root).resolve()
        for folder in ("bodies", "quarantine"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        self.bodies = require_body_store(VolumeBodyStore(str(self.root / "bodies"),
                                                         writes_authorized=writes_authorized),
                                         write=writes_authorized)
        database = self.root / "records.db"
        self.records = SQLiteRecordStore(str(database), read_only=not writes_authorized and database.is_file())
        if writes_authorized:
            require_atomic_batch(self.records)
        self.quarantine = Quarantine(self.root / "quarantine")
        self.writes_authorized = writes_authorized

    def close(self) -> None:
        self.records.close()

    def put_bodies(self, bodies: dict) -> dict:
        """Store each body once under its digest; one flush for the whole call."""
        written = present = 0
        for digest, payload in sorted(bodies.items()):
            result = self.bodies.put(payload, expected_digest=digest, durable=False)
            written += 1 if result["written"] else 0
            present += 0 if result["written"] else 1
        self.bodies.sync()
        return {"written": written, "already_present": present}

    def get(self, record_id: str) -> "dict | None":
        return self.records.get(record_id)

    def apply(self, records, *, expected: "dict | None" = None) -> int:
        """Write records in atomic batches: each new one must be absent, each update at its read version."""
        expected = dict(expected or {})
        records = list(records)
        for start in range(0, len(records), _BATCH_RECORDS):
            chunk = records[start:start + _BATCH_RECORDS]
            preconditions = [CatalogRecordPrecondition(row["record_id"], expected[row["record_id"]])
                             if row["record_id"] in expected else
                             CatalogRecordPrecondition(row["record_id"], must_not_exist=True) for row in chunk]
            acknowledgment = self.records.apply_batch(CatalogWriteBatch.from_records(chunk, preconditions))
            if acknowledgment.committed is not True:
                raise RuntimeError("the record store did not acknowledge the batch as committed")
        return len(records)

    def size_report(self) -> dict:
        """Bytes and counts of each part, for the cost projection per 100,000 files."""
        report = {}
        for part in ("bodies", "quarantine"):
            files = total = 0
            for folder, _names, names in os.walk(self.root / part):
                for name in names:
                    if name.endswith(".partial"):
                        continue
                    files += 1
                    total += (Path(folder) / name).stat().st_size
            report[part] = {"files": files, "bytes": total}
        database = self.root / "records.db"
        report["records_db"] = {"bytes": database.stat().st_size if database.is_file() else 0}
        return report


def candidate_store_record(payload: dict, lifecycle: str = CANDIDATE_LIFECYCLE) -> dict:
    """The catalogue record of one candidate version; the payload is the candidate record itself."""
    repository = payload["provenance"]["repository"]
    return {"record_id": payload["record_id"], "record_version": record_version({**payload, "lifecycle": lifecycle}),
            "intelligence_layer": KIND_LAYERS[payload["kind"]], "source_collection": "learned",
            "artifact_kind": "intelligence_record", "lifecycle": lifecycle, "namespace": NAMESPACE,
            "attributes": {"family": "harness", "kind": payload["kind"], "title": payload["name"],
                           "upstream_key": payload["upstream_key"], "package_digest": payload["package_digest"],
                           "license_spdx": payload["licence"]["spdx_expression"], "license_state": "pending_review",
                           "authoring": payload["authoring"], "source_origins": [f"github_repository:{repository}"],
                           "content_sha256": record_version(payload),
                           "normalized_sha256": payload["comparison"]["normalized_sha256"],
                           "tags": [payload["kind"], payload["native_format"]]},
            "payload": {**payload, "lifecycle": lifecycle}}


def idea_store_record(payload: dict) -> dict:
    return {"record_id": payload["record_id"], "record_version": record_version(payload),
            "intelligence_layer": KIND_LAYERS[payload["kind"]], "source_collection": "learned",
            "artifact_kind": "intelligence_record", "lifecycle": IDEA_LIFECYCLE, "namespace": NAMESPACE,
            "attributes": {"family": "harness", "kind": payload["kind"], "title": payload["name"],
                           "upstream_key": payload["upstream_key"],
                           "license_spdx": payload["licence"]["spdx_expression"],
                           "license_state": "not_copyable", "tags": [payload["kind"], "idea"]},
            "payload": payload}


def state_store_record(payload: dict, record_id: str) -> dict:
    return {"record_id": record_id, "record_version": record_version(payload), "intelligence_layer": "",
            "source_collection": "learned", "artifact_kind": "import_source_state",
            "lifecycle": SOURCE_STATE_LIFECYCLE, "namespace": NAMESPACE,
            "attributes": {"repository": payload["repository"], "commit": payload["commit"]}, "payload": payload}


def withdrawal_store_record(payload: dict, record_id: str) -> dict:
    return {"record_id": record_id, "record_version": record_version(payload), "intelligence_layer": "",
            "source_collection": "learned", "artifact_kind": "import_withdrawal",
            "lifecycle": WITHDRAWAL_LIFECYCLE, "namespace": NAMESPACE,
            "attributes": {"upstream_key": payload["upstream_key"], "reason": payload["reason"]}, "payload": payload}


def relabelled(record: dict, lifecycle: str) -> dict:
    """The same candidate record with a new lifecycle and a new version; nothing else changes."""
    if lifecycle not in (WITHDRAWN_LIFECYCLE, SUPERSEDED_LIFECYCLE):
        raise ValueError("a stored candidate is only ever withdrawn or superseded")
    payload = {**record["payload"], "lifecycle": lifecycle}
    return {**record, "lifecycle": lifecycle, "payload": payload, "record_version": record_version(payload)}
