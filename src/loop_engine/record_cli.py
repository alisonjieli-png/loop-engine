"""JSON-stdin tool for host-scoped generic record operations.

Backend paths, namespace policy, and approval are launcher configuration, not
fields accepted from model output. Report/note bodies use the existing catalog
and artifact stores. This CLI does not edit Markdown or persist a new history
store; each operational call is owned by an ordinary Loop.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core.record_operations import (
    RecordOperationService,
    RecordOperationServices,
    RecordStorageBinding,
    effect_digest,
)
from .core.record_operations_records import (
    MUTATIONS,
    RecordOperationError,
    RecordOperationPolicy,
    RecordOperationRequest,
    parse_json,
)
from .core.runtime_observer import RuntimeObservationServices
from .loop.effect_approval import (
    ApprovalDecision,
    ApprovalRequest,
    EffectApprovalService,
)
from .loop.recursive_loop import LoopLedger
from .loop.service_loop_envelope import ServiceLoopSpec, run_service_operation

MAXIMUM_REQUEST_BYTES = 1_048_576


def _no_symlinks(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RecordOperationError("backend_path_symlink_refused")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loop-engine records")
    parser.add_argument("--policy", required=True, help="host-owned policy JSON file")
    parser.add_argument("--backend", choices=("sqlite", "package-jsonl"), default="sqlite")
    parser.add_argument("--database", help="host-owned SQLite path")
    parser.add_argument("--shard", action="append", default=[], help="host-owned read-only JSONL shard")
    parser.add_argument("--artifact-root", required=True, help="host-owned revision artifact root")
    parser.add_argument("--approve-effect-digest", default="",
                        help="exact effect digest explicitly approved by the host")
    return parser


def _binding(args) -> RecordStorageBinding:
    artifact_root = Path(args.artifact_root).expanduser().absolute()
    _no_symlinks(artifact_root)
    if args.backend == "sqlite":
        if not args.database or args.shard:
            raise RecordOperationError("sqlite_database_configuration_required")
        database = Path(args.database).expanduser().absolute()
        _no_symlinks(database)

        def open_backend(write):
            from .catalog.stores.sqlite_store import SQLiteRecordStore
            _no_symlinks(database)
            if not write and not database.is_file():
                raise FileNotFoundError("record_backend_not_found")
            if write:
                database.parent.mkdir(parents=True, exist_ok=True)
            return SQLiteRecordStore(str(database), read_only=not write)

        locator = "sqlite:" + str(database)
    else:
        if args.database or not args.shard:
            raise RecordOperationError("package_shards_configuration_required")
        shards = tuple(Path(path).expanduser().absolute() for path in args.shard)
        for shard in shards:
            _no_symlinks(shard)

        def open_backend(write):
            from .catalog.stores.package_jsonl import PackageJsonlStore
            if write:
                raise RecordOperationError("package_backend_is_read_only")
            for shard in shards:
                _no_symlinks(shard)
            return PackageJsonlStore(tuple(str(path) for path in shards))

        locator = "package-jsonl:" + json.dumps([str(path) for path in shards])
    return RecordStorageBinding(locator, str(artifact_root), open_backend)


def record_command(argv: list[str] | None = None) -> int:
    """Process exactly one bounded JSON request from stdin; emit one JSON result."""
    args = _parser().parse_args(argv)
    try:
        raw_request = sys.stdin.read(MAXIMUM_REQUEST_BYTES + 1)
        if len(raw_request.encode("utf-8")) > MAXIMUM_REQUEST_BYTES:
            raise RecordOperationError("record_request_too_large")
        policy_path = Path(args.policy).expanduser()
        if policy_path.stat().st_size > MAXIMUM_REQUEST_BYTES:
            raise RecordOperationError("record_policy_too_large")
        policy = RecordOperationPolicy.from_mapping(parse_json(policy_path.read_text(encoding="utf-8")))
        request = RecordOperationRequest.from_mapping(parse_json(raw_request))
        binding = _binding(args)
        plan_service = RecordOperationService(policy, RecordOperationServices(binding))
        effect = plan_service.effect_for(request) if request.operation in MUTATIONS else None
        if effect is not None and not args.approve_effect_digest:
            print(json.dumps({"record_type": "record_operation_plan/v1",
                              "status": "approval_required", "effect": effect.to_dict(),
                              "effect_digest": effect_digest(effect), "request_digest": request.digest,
                              "policy_digest": policy.digest, "effects_executed": False}, sort_keys=True))
            return 0
        if effect is not None and args.approve_effect_digest != effect_digest(effect):
            raise RecordOperationError("approved_effect_digest_mismatch")
        if effect is None and args.approve_effect_digest:
            raise RecordOperationError("unexpected_write_approval")
        ledger = LoopLedger()
        runtime = RuntimeObservationServices(ledger=ledger)

        def operation(active):
            spawned_runtime = RuntimeObservationServices(parent=active, ledger=ledger)
            approvals = EffectApprovalService(runtime=spawned_runtime)
            service = RecordOperationService(policy, RecordOperationServices(binding, spawned_runtime, approvals))
            approval_id = ""
            if effect is not None:
                approval = ApprovalRequest.create(active.loop_id, effect,
                    "Host approved the exact scoped record effect digest", requested_by="record_cli")
                checkpoint = approvals.create(approval)
                approvals.resume(checkpoint.pending, checkpoint.resume_token,
                                 ApprovalDecision.approve(approval.request_id, "host_cli"))
                approval_id = approval.request_id
            result = service.execute(request, approval_id=approval_id)
            return {**result.to_dict(), "owner_loop_id": active.loop_id}

        result = run_service_operation(runtime, ServiceLoopSpec(
            operation="record_cli_dispatch", profile_id="practitioner.code_execution",
            input_role="record_operation_request", output_role="record_operation_result",
            effects=("reads_fs", "writes_fs") if effect is not None else ("reads_fs",),
            objective="dispatch one host-scoped record request", failure_kind="record_cli_failed"), operation)
        result.update({"loop_event_count": len(ledger.events), "run_history_persisted": False,
                       "history_scope": "immutable managed-record revisions only", "model_calls": 0})
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 1 if result["status"] in ("conflict", "commit_unknown") else 0
    except RecordOperationError as exc:
        code = str(exc)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        code = "record_operation_unavailable"
    print(json.dumps({"record_type": "record_operation_failure/v1", "error_code": code,
                      "committed": False, "grants_authority": False, "model_calls": 0}, sort_keys=True))
    return 2


def self_test() -> dict:
    """Run command-surface checks with local temporary fixtures only."""
    from .core.record_operations_checks import cli_checks
    tests = cli_checks()
    return {"tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests), "all_passed": all(item["passed"] for item in tests)}


if __name__ == "__main__":
    raise SystemExit(record_command())
