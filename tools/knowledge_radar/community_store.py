"""Private community records through RecordOperationService, never a parallel content store.

The operator's local-write grant approves exact scoped record effects. It
does not approve intelligence, execution, publication, a message or spending.
Every update uses the observed revision; unknown commits stop the caller.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.record_operations import (
    RecordOperationService,
    RecordOperationServices,
    RecordStorageBinding,
)
from loop_engine.core.record_operations_records import (
    RecordOperationPolicy,
    RecordOperationRequest,
    RecordScope,
    canonical_json,
)
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.loop.effect_approval import (
    ApprovalDecision,
    ApprovalRequest,
    EffectApprovalService,
)
from loop_engine.loop.recursive_loop import LoopLedger

DOCUMENT_VERSION = "community_watch_document/v1"
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["record_type", "kind", "source_id", "state", "data"], "properties": {
              "record_type": {"const": DOCUMENT_VERSION},
              "kind": {"enum": ["source", "lead", "research_brief", "run", "harness_budget"]},
              "source_id": {"type": "string", "maxLength": 160},
              "state": {"enum": ["recorded", "queued", "needs_research", "dismissed", "deferred", "failed", "complete"]},
              "data": {"type": "object"}}}


class CommunityStore:
    """Scoped adapter over the existing managed-record contract and SQLite backend."""
    def __init__(self, root: Path, *, writes_allowed=False):
        self.root = Path(root).absolute()
        self.writes_allowed = writes_allowed
        repository = Path(__file__).resolve().parents[2]
        if self.root == Path(self.root.anchor) or self.root == Path.home() or self.root.is_relative_to(repository):
            raise ValueError("community_state_must_be_private_and_outside_repository")
        self._safe()
        self.run_id = uuid4().hex
        self.ledger = LoopLedger(id_namespace="community-watch-" + self.run_id)
        self.runtime = RuntimeObservationServices(ledger=self.ledger)
        approvals = EffectApprovalService(runtime=self.runtime)
        database = self.root / "records.sqlite"

        def open_backend(write):
            self._safe()
            if write and not self.writes_allowed:
                raise PermissionError("local_write_grant_required")
            if not write and not database.exists():
                raise FileNotFoundError("no_records")
            if write:
                self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            return SQLiteRecordStore(str(database), read_only=not write)

        policy = RecordOperationPolicy("baltor.community.watch.v1", RecordScope(
            "baltor.internal.community", "community_research", "context_intelligence", "intelligence_record", "community."),
            canonical_json(SCHEMA), indexed_fields=("kind", "source_id", "state"), maximum_document_bytes=65536,
            maximum_query_results=1000)
        self.service = RecordOperationService(policy, RecordOperationServices(
            RecordStorageBinding("sqlite:" + str(database), str(self.root / "artifacts"), open_backend),
            self.runtime, approvals))

    def _safe(self):
        if ".." in self.root.parts or any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise ValueError("community_path_symlink_or_parent_refused")
        if any((self.root / name).is_symlink() for name in ("records.sqlite", "scheduler.sqlite", "scan.lock", "runs")):
            raise ValueError("community_path_symlink_refused")

    def get(self, identity, version=""):
        result = self.service.execute(RecordOperationRequest("get", identity, record_version=version, materialize=True))
        if result.status == "not_found":
            return None
        if result.status != "found" or not result.document_json:
            raise ValueError("community_record_unavailable:" + result.status)
        return {"version": result.records[0]["record_version"], "document": json.loads(result.document_json)}

    def put(self, identity, kind, source_id, state, data, *, expected=None):
        if not self.writes_allowed:
            raise PermissionError("local_write_grant_required")
        document = {"record_type": DOCUMENT_VERSION, "kind": kind, "source_id": source_id, "state": state, "data": data}
        if expected is not None and expected["document"] == document:
            return expected["version"]
        request = RecordOperationRequest("update" if expected else "create", identity,
            expected_record_version=expected["version"] if expected else "", document_json=canonical_json(document))
        effect = self.service.effect_for(request)
        approval = ApprovalRequest.create("community.operator", effect, "Operator authorized this exact private record write.")
        gate = self.service.services.approvals
        checkpoint = gate.create(approval)
        gate.resume(checkpoint.pending, checkpoint.resume_token, ApprovalDecision.approve(approval.request_id, "community.host"))
        result = self.service.execute(request, approval_id=approval.request_id)
        if result.committed is not True:
            raise RuntimeError("community_write_not_committed:" + result.status)
        return result.records[0]["record_version"]

    def query(self, *, kind="", state="", limit=100):
        filters = {key: value for key, value in (("kind", kind), ("state", state)) if value}
        result = self.service.execute(RecordOperationRequest("query", filters_json=canonical_json(filters), limit=limit))
        return [{"identity": row["record_id"], **self.get(row["record_id"])} for row in result.records]
