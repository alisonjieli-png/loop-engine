"""Offline adversarial fixtures for scoped immutable managed records.

Uses temporary SQLite/artifact paths and ordinary Loops only. No provider,
network service, canonical Run History mutation, or intelligence promotion.
"""
from __future__ import annotations

import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ..catalog.protocol import StoreError
from ..catalog.stores.sqlite_store import SQLiteRecordStore
from ..loop.effect_approval import (
    ApprovalDecision,
    ApprovalRequest,
    EffectApprovalService,
)
from ..loop.recursive_loop import LoopLedger
from .record_operations import (
    RecordOperationService,
    RecordOperationServices,
    RecordStorageBinding,
    effect_digest,
)
from .record_operations_records import (
    RecordOperationError,
    RecordOperationPolicy,
    RecordOperationRequest,
    RecordScope,
    canonical_json,
)
from .runtime_observer import RuntimeObservationServices


def _policy(namespace="fixture.records"):
    return RecordOperationPolicy("fixture.record.policy", RecordScope(
        namespace, "learned", "context_intelligence", "intelligence_record", "note."),
        canonical_json({"type": "object", "required": ["title", "body"],
                        "additionalProperties": False,
                        "properties": {"title": {"type": "string"}, "body": {"type": "string"}}}),
        indexed_fields=("title",))


def _request(operation, *, title="first", version="", record_version="", materialize=False):
    return RecordOperationRequest(operation, "note.one", expected_record_version=version,
        record_version=record_version,
        document_json=canonical_json({"title": title, "body": "PRIVATE_RECORD_DOC_MARKER"})
        if operation in ("create", "update") else "", materialize=materialize)


def _service(root: Path, *, policy=None, locator_suffix="", barrier=None):
    database = root / "records.sqlite"
    opened = []

    def open_backend(write):
        opened.append(write)
        if not write and not database.exists():
            raise FileNotFoundError("not_found")
        if write:
            root.mkdir(parents=True, exist_ok=True)
        backend = SQLiteRecordStore(str(database), read_only=not write)
        if barrier is None or not write:
            return backend

        class InterleavedStore:
            initial_read = True

            def capabilities(self):
                return backend.capabilities()

            def get(self, record_id, version=None):
                result = backend.get(record_id, version)
                if self.initial_read:
                    self.initial_read = False
                    barrier.wait(timeout=5)
                return result

            def put(self, record, *, precondition=None):
                return backend.put(record, precondition=precondition)

            def close(self):
                backend.close()

        return InterleavedStore()

    runtime = RuntimeObservationServices(ledger=LoopLedger())
    approvals = EffectApprovalService(runtime=runtime)
    binding = RecordStorageBinding("sqlite:" + str(database) + locator_suffix,
                                   str(root / "artifacts"), open_backend)
    return RecordOperationService(policy or _policy(), RecordOperationServices(binding, runtime, approvals)), opened


def _approve(service, request):
    effect = service.effect_for(request)
    approval = ApprovalRequest.create("fixture.owner", effect, "Fixture host approves exact record effect")
    checkpoint = service.services.approvals.create(approval)
    service.services.approvals.resume(checkpoint.pending, checkpoint.resume_token,
                                     ApprovalDecision.approve(approval.request_id, "fixture.host"))
    return approval.request_id


def _write(service, request):
    return service.execute(request, approval_id=_approve(service, request))


def _refused(operation):
    try:
        operation()
    except (RecordOperationError, ValueError, TypeError):
        return True
    return False


def self_test() -> dict:
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    with TemporaryDirectory(prefix="loop-record-operations-") as directory:
        root = Path(directory) / "uncreated"
        service, opened = _service(root)
        create = _request("create")
        planned = service.effect_for(create)
        check("planning_and_unapproved_mutation_create_no_backend_or_artifacts",
              len(effect_digest(planned)) == 64
              and _refused(lambda: service.execute(create))
              and not root.exists() and not opened)
        missing = service.execute(_request("get"))
        check("read_of_missing_backend_creates_no_paths", missing.status == "not_found" and not root.exists())
        approval = _approve(service, create)
        stored = service.execute(create, approval_id=approval)
        retrieved = service.execute(_request("get", materialize=True))
        check("approved_create_and_exact_readback_preserve_document",
              stored.committed and stored.records[0]["record_version"] == "1"
              and json.loads(retrieved.document_json)["title"] == "first")
        check("consumed_approval_cannot_replay_mutation",
              _refused(lambda: service.execute(create, approval_id=approval)))
        check("create_is_missing_only", _write(service, create).status == "conflict")
        altered = _request("update", title="altered", version="1")
        approval = _approve(service, altered)
        changed = _request("update", title="not-approved", version="1")
        check("approval_is_bound_to_exact_document", _refused(lambda: service.execute(changed, approval_id=approval)))
        other_binding, _ = _service(root, locator_suffix=":different-backend")
        other_binding = RecordOperationService(other_binding.policy, RecordOperationServices(
            other_binding.services.storage, service.services.runtime, service.services.approvals))
        check("approval_is_bound_to_backend_instance_locator",
              _refused(lambda: other_binding.execute(altered, approval_id=approval)))
        storage = service.services.storage
        relocated = RecordStorageBinding(storage.backend_locator, str(root / "other-artifacts"), storage.open_backend)
        other_artifacts = RecordOperationService(service.policy, RecordOperationServices(
            relocated, service.services.runtime, service.services.approvals))
        check("approval_is_bound_to_artifact_root",
              _refused(lambda: other_artifacts.execute(altered, approval_id=approval))
              and not (root / "other-artifacts").exists())
        updated = service.execute(altered, approval_id=approval)
        old = service.execute(_request("get", record_version="1", materialize=True))
        new = service.execute(_request("get", record_version="2", materialize=True))
        check("update_preserves_immutable_previous_revision",
              updated.committed and json.loads(old.document_json)["title"] == "first"
              and json.loads(new.document_json)["title"] == "altered")
        check("stale_expected_version_refuses_update",
              _write(service, _request("update", version="1")).status == "conflict")
        query = RecordOperationRequest("query", filters_json=canonical_json({"title": "altered"}))
        rows = service.execute(query)
        check("query_returns_scoped_body_free_reference_cards",
              len(rows.records) == 1 and not rows.document_json
              and "PRIVATE_RECORD_DOC_MARKER" not in json.dumps(rows.to_dict()))
        foreign, _ = _service(root, policy=_policy("fixture.foreign"))
        check("cross_namespace_reads_and_updates_are_refused",
              foreign.execute(_request("get")).status == "not_found"
              and not foreign.execute(RecordOperationRequest("query")).records
              and _write(foreign, _request("update", version="2")).status == "not_found")
        retired = _write(service, _request("retire", version="2"))
        historic = service.execute(_request("get", record_version="1", materialize=True))
        check("retirement_preserves_history_and_never_promotes",
              retired.committed and retired.status == "retired"
              and retired.records[0]["lifecycle"] == "retired"
              and json.loads(historic.document_json)["title"] == "first"
              and not retired.to_dict()["promotes_intelligence"])
        check("retired_record_cannot_be_silently_resurrected",
              _write(service, _request("update", version="3")).status == "conflict")
        shallow = RecordOperationRequest("get", "note.one", record_version="1", maximum_history_depth=1)
        check("history_hydration_has_an_explicit_depth_limit",
              _refused(lambda: service.execute(shallow)))
        reference = historic.records[0]["revision_ref"]
        artifact = root / "artifacts/managed_records/objects" / reference["digest"][:2] / reference["digest"]
        artifact.write_bytes(b"changed")
        check("artifact_tampering_fails_closed",
              _refused(lambda: service.execute(_request("get", record_version="1"))))
        check("operational_ledger_never_copies_document_body",
              "PRIVATE_RECORD_DOC_MARKER" not in json.dumps(service.services.runtime.ledger.events))

    malformed = {"record_type": "record_operation_request/v1", "operation": "create",
                 "record_id": "note.one", "document": {"title": "x", "body": "x"}}
    check("model_request_cannot_supply_sql_paths_scope_or_authority",
          all(_refused(lambda field=field: RecordOperationRequest.from_mapping({**malformed, field: "forged"}))
              for field in ("sql", "database", "namespace", "schema", "approval_id", "lifecycle")))
    check("schema_rejection_is_content_free",
          _refused(lambda: RecordOperationPolicy("bad", _policy().scope,
                                                canonical_json({"type": "PRIVATE_SCHEMA"}))))
    check("external_schema_resolution_is_refused",
          _refused(lambda: RecordOperationPolicy("bad", _policy().scope,
                                                canonical_json({"$ref": "https://example.invalid/schema"}))))
    check("boolean_limits_are_not_integers",
          _refused(lambda: RecordOperationRequest("query", limit=True)))

    with TemporaryDirectory(prefix="loop-record-concurrency-") as directory:
        root = Path(directory)
        service, _ = _service(root)
        _write(service, _request("create"))
        barrier = threading.Barrier(2)

        def update(title):
            concurrent, _ = _service(root, barrier=barrier)
            return _write(concurrent, _request("update", title=title, version="1"))

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, ("writer-a", "writer-b")))
        failed = [result for result in results if not result.committed]
        winner = service.execute(_request("get", materialize=True))
        check("concurrent_updates_have_one_winner_and_explicit_orphan",
              sum(result.committed for result in results) == 1
              and failed[0].status == "conflict" and failed[0].orphan_artifact_ref is not None
              and winner.records[0]["record_version"] == "2")
    for fault in ("sqlite_abort", "no_op_write_confirmation", "post_commit_error"):
        with TemporaryDirectory(prefix="loop-record-write-fault-") as directory:
            base, _ = _service(Path(directory))
            binding = base.services.storage

            def fault_backend(write, selected_binding=binding, fault_kind=fault):
                backend = selected_binding.open_backend(write)
                if not write:
                    return backend
                if fault_kind == "sqlite_abort":
                    backend._con.execute(
                        "CREATE TRIGGER reject_managed_insert BEFORE INSERT ON records "
                        "BEGIN SELECT RAISE(ABORT, 'PRIVATE_STORAGE_FAILURE'); END")
                    backend._con.commit()
                    return backend

                class UnreliableStore:
                    def capabilities(self):
                        return backend.capabilities()

                    def get(self, record_id, version=None):
                        return backend.get(record_id, version)

                    def put(self, record, *, precondition=None):
                        if fault_kind == "post_commit_error":
                            backend.put(record, precondition=precondition)
                            raise StoreError("PRIVATE_STORAGE_FAILURE")
                        return {"record_id": record["record_id"], "stored": True}

                    def close(self):
                        backend.close()

                return UnreliableStore()

            service = RecordOperationService(base.policy, RecordOperationServices(
                RecordStorageBinding(binding.backend_locator, binding.artifact_root, fault_backend),
                base.services.runtime, base.services.approvals))
            result = _write(service, _request("create"))
            actual = base.execute(_request("get"))
            check(f"{fault}_never_claims_commit_or_cas_conflict",
                  result.status == "commit_unknown" and result.committed is None
                  and result.orphan_artifact_ref is None
                  and result.potential_orphan_artifact_ref is not None
                  and actual.status == ("found" if fault == "post_commit_error" else "not_found")
                  and "PRIVATE_STORAGE_FAILURE" not in json.dumps(result.to_dict()))

    with TemporaryDirectory(prefix="loop-record-advanced-head-") as directory:
        base, _ = _service(Path(directory))
        _write(base, _request("create"))
        binding = base.services.storage

        def advancing_backend(write):
            backend = binding.open_backend(write)
            if not write:
                return backend

            class AdvancingStore:
                def capabilities(self):
                    return backend.capabilities()

                def get(self, record_id, version=None):
                    return backend.get(record_id, version)

                def put(self, record, *, precondition=None):
                    write_confirmation = backend.put(record, precondition=precondition)
                    later = _write(base, _request("update", title="later-writer",
                                                  version=record["record_version"]))
                    if later.committed is not True:
                        raise StoreError("fixture_followup_failed")
                    return write_confirmation

                def close(self):
                    backend.close()

            return AdvancingStore()

        service = RecordOperationService(base.policy, RecordOperationServices(
            RecordStorageBinding(binding.backend_locator, binding.artifact_root, advancing_backend),
            base.services.runtime, base.services.approvals))
        confirmed = _write(service, _request("update", title="our-writer", version="1"))
        current = base.execute(_request("get", materialize=True))
        check("later_valid_revision_chain_confirms_our_committed_predecessor",
              confirmed.committed is True and confirmed.records[0]["record_version"] == "2"
              and current.records[0]["record_version"] == "3"
              and json.loads(current.document_json)["title"] == "later-writer")
    return {"record_type": "record_operations_checks/v1", "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests), "provider_calls": 0}


def cli_checks() -> list[dict]:
    """Exercise the JSON stdin surface without invoking the public parser twice."""
    from ..record_cli import record_command
    tests = []

    def invoke(argv, request):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(request))), patch("sys.stdout", output):
            code = record_command(argv)
        return code, json.loads(output.getvalue())

    with TemporaryDirectory(prefix="loop-record-cli-") as directory:
        root = Path(directory)
        policy = root / "host-policy.json"
        policy.write_text(json.dumps(_policy().to_dict()))
        database = root / "uncreated/records.sqlite"
        artifacts = root / "uncreated/artifacts"
        argv = ["--policy", str(policy), "--database", str(database), "--artifact-root", str(artifacts)]
        request = _request("create").to_dict()
        code, planned = invoke(argv, request)
        tests.append({"test": "cli_plan_opens_no_database_or_artifact_directory",
                      "passed": code == 0 and planned["status"] == "approval_required"
                      and not database.exists() and not artifacts.exists()})
        code, result = invoke(argv + ["--approve-effect-digest", planned["effect_digest"]], request)
        code2, readback = invoke(argv, _request("get", materialize=True).to_dict())
        tests.append({"test": "cli_approved_stdin_create_and_readback_use_existing_stores",
                      "passed": code == code2 == 0 and result["committed"]
                      and readback["document"]["title"] == "first"
                      and result["run_history_persisted"] is False and result["model_calls"] == 0})
        code, refused = invoke(argv, {**request, "namespace": "forged"})
        tests.append({"test": "cli_stdin_cannot_override_host_scope",
                      "passed": code == 2 and refused["committed"] is False})
        shard = root / "records.jsonl"
        shard.write_text(json.dumps({"record_id": "note.package", "record_version": "1",
            "namespace": "fixture.records", "source_collection": "learned",
            "intelligence_layer": "context_intelligence", "artifact_kind": "intelligence_record",
            "lifecycle": "candidate", "attributes": {}, "payload": {}}) + "\n")
        package_args = ["--policy", str(policy), "--backend", "package-jsonl", "--shard", str(shard),
                        "--artifact-root", str(root / "no-artifacts")]
        code, queried = invoke(package_args, RecordOperationRequest("query").to_dict())
        tests.append({"test": "cli_read_only_package_query_creates_no_artifact_store",
                      "passed": code == 0 and len(queried["records"]) == 1
                      and not (root / "no-artifacts").exists()})
    return tests
