"""Focused checks for approval-aware workspace operations.

The fixtures use the existing restricted local backend behind a counting
wrapper. They perform no network or provider operation.
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from ..loop.approval_state_store import LocalJsonApprovalStateStore
from ..loop.effect_approval import (
    ApprovalDecision, EffectApprovalService)
from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger
from .runtime_observer import RuntimeObservationServices
from .workspace_contracts import (
    CommandRequest, FileOperation, FileRequest, SnapshotRequest, WorkspaceSpec)
from .workspace_local import RestrictedLocalWorkspace
from .workspace_operations import WorkspaceOperationService


class _CountingBackend:
    def __init__(self, backend):
        self.backend = backend
        self.spec = backend.spec
        self.file_calls = 0
        self.command_calls = 0
        self.snapshot_calls = 0
        self.reference_calls = 0
        self.fail_next_file = False
        self.fail_next_command = False
        self.ledger = None
        self.call_order: list[tuple[str, int]] = []

    def _mark(self, name: str):
        count = (sum(event.get("event") == "init"
                     for event in self.ledger.events)
                 if self.ledger is not None else 0)
        self.call_order.append((name, count))

    def reference(self):
        self.reference_calls += 1
        self._mark("reference")
        return self.backend.reference()

    def availability(self):
        return self.backend.availability()

    def file(self, request):
        self._mark("file")
        self.file_calls += 1
        if self.fail_next_file:
            self.fail_next_file = False
            raise RuntimeError("fixture file boundary failure")
        return self.backend.file(request)

    def command(self, request):
        self._mark("command")
        self.command_calls += 1
        if self.fail_next_command:
            self.fail_next_command = False
            raise RuntimeError("fixture command boundary failure")
        return self.backend.command(request)

    def snapshot(self, request):
        self._mark("snapshot")
        self.snapshot_calls += 1
        return self.backend.snapshot(request)


def run_checks() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-workspace-operation-") as outer:
        workspace_root = Path(outer) / "workspace"
        workspace_root.mkdir()
        approval_root = Path(outer) / "approvals"
        local = RestrictedLocalWorkspace(WorkspaceSpec(
            "workspace_operation_test", str(workspace_root),
            execution_enabled=True, allowed_commands=(sys.executable,)))
        backend = _CountingBackend(local)
        runtime = RuntimeObservationServices(ledger=LoopLedger())
        backend.ledger = runtime.ledger
        approvals = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(str(approval_root)))
        operations = WorkspaceOperationService(backend, approvals=approvals)

        init_count = sum(event.get("event") == "init"
                         for event in runtime.ledger.events)
        backend.call_order.clear()
        missing = operations.file(FileRequest(
            FileOperation.WRITE, "reviewed.txt", content=b"body-value-483"))
        check("file_write_requires_native_effect_approval_before_backend",
              not missing.ok and missing.error_code == "approval_required"
              and backend.file_calls == 0
              and backend.call_order == [("reference", init_count + 1)])

        write_request = FileRequest(
            FileOperation.WRITE, "reviewed.txt", content=b"body-value-483")
        write_plan = operations.plan_file_write(
            write_request, loop_id="loop_workspace_write",
            reason="Write the reviewed fixture file.")
        write_checkpoint = approvals.create(write_plan.approval)
        write_decided = approvals.resume(
            write_checkpoint.pending, write_checkpoint.resume_token,
            ApprovalDecision.approve(
                write_plan.approval.request_id, "reviewer"))
        restarted_approvals = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(str(approval_root)))
        restarted_approvals.restore(write_decided)
        restarted_operations = WorkspaceOperationService(
            backend, approvals=restarted_approvals)
        written = restarted_operations.file(
            write_plan.request, approval_id=write_plan.approval.request_id)
        check("approved_file_write_survives_restart_and_crosses_once",
              written.ok and backend.file_calls == 1
              and (workspace_root / "reviewed.txt").read_bytes()
              == b"body-value-483")

        duplicate = restarted_operations.file(
            write_plan.request, approval_id=write_plan.approval.request_id)
        check("duplicate_file_effect_cannot_cross_backend_twice",
              not duplicate.ok and duplicate.error_code == "approval_not_usable"
              and backend.file_calls == 1)

        changed_plan = operations.plan_file_write(
            FileRequest(
                FileOperation.WRITE, "changed.txt", content=b"original"),
            loop_id="loop_workspace_changed",
            reason="Write the original reviewed bytes.")
        changed_checkpoint = approvals.create(changed_plan.approval)
        approvals.resume(
            changed_checkpoint.pending, changed_checkpoint.resume_token,
            ApprovalDecision.approve(
                changed_plan.approval.request_id, "reviewer"))
        before_changed = backend.file_calls
        changed = operations.file(
            replace(changed_plan.request, content=b"edited"),
            approval_id=changed_plan.approval.request_id)
        check("changed_file_request_fails_before_backend",
              not changed.ok and changed.error_code == "approval_not_usable"
              and backend.file_calls == before_changed
              and not (workspace_root / "changed.txt").exists())

        read = operations.file(FileRequest(
            FileOperation.READ, "reviewed.txt"))
        listing = operations.file(FileRequest(FileOperation.LIST, "."))
        stat = operations.file(FileRequest(
            FileOperation.STAT, "reviewed.txt"))
        snapshot = operations.snapshot(SnapshotRequest(include_hidden=True))
        check("read_list_stat_and_snapshot_remain_backend_policy_operations",
              read.ok and read.content == b"body-value-483"
              and listing.ok and "reviewed.txt" in listing.entries
              and stat.ok and snapshot.file_count == 1
              and backend.file_calls == before_changed + 3
              and backend.snapshot_calls == 1)

        command_request = CommandRequest(
            (sys.executable, "-c", "print('approved command')"),
            execution_authorized=True)
        command_plan = operations.plan_command(
            command_request, loop_id="loop_workspace_command",
            reason="Run one reviewed local command.")
        command_checkpoint = approvals.create(command_plan.approval)
        approvals.resume(
            command_checkpoint.pending, command_checkpoint.resume_token,
            ApprovalDecision.approve(
                command_plan.approval.request_id, "reviewer"))
        command = operations.command(
            command_plan.request,
            approval_id=command_plan.approval.request_id)
        check("approved_command_crosses_existing_backend_once",
              command.ok and command.stdout.strip() == "approved command"
              and backend.command_calls == 1)

        changed_command_plan = operations.plan_command(
            command_request, loop_id="loop_workspace_command_changed",
            reason="Run the exact reviewed command.")
        changed_command_checkpoint = approvals.create(
            changed_command_plan.approval)
        approvals.resume(
            changed_command_checkpoint.pending,
            changed_command_checkpoint.resume_token,
            ApprovalDecision.approve(
                changed_command_plan.approval.request_id, "reviewer"))
        changed_command = operations.command(
            replace(command_request, argv=(
                sys.executable, "-c", "print('edited command')")),
            approval_id=changed_command_plan.approval.request_id)
        check("changed_command_request_fails_before_backend",
              not changed_command.ok
              and changed_command.error_code == "approval_not_usable"
              and backend.command_calls == 1)

        failed_write_request = FileRequest(
            FileOperation.WRITE, "failure.txt", content=b"one attempt")
        failed_write_plan = operations.plan_file_write(
            failed_write_request, loop_id="loop_workspace_failure",
            reason="Attempt one reviewed write.")
        failed_write_checkpoint = approvals.create(
            failed_write_plan.approval)
        approvals.resume(
            failed_write_checkpoint.pending,
            failed_write_checkpoint.resume_token,
            ApprovalDecision.approve(
                failed_write_plan.approval.request_id, "reviewer"))
        backend.fail_next_file = True
        before_failure = backend.file_calls
        failed_write = operations.file(
            failed_write_plan.request,
            approval_id=failed_write_plan.approval.request_id)
        failed_write_retry = operations.file(
            failed_write_plan.request,
            approval_id=failed_write_plan.approval.request_id)
        check("failed_write_crosses_backend_once_and_consumes_approval",
              failed_write.error_code == "backend_failed"
              and failed_write_retry.error_code == "approval_not_usable"
              and backend.file_calls == before_failure + 1)

        failed_command_plan = operations.plan_command(
            command_request, loop_id="loop_workspace_command_failure",
            reason="Attempt one reviewed command.")
        failed_command_checkpoint = approvals.create(
            failed_command_plan.approval)
        approvals.resume(
            failed_command_checkpoint.pending,
            failed_command_checkpoint.resume_token,
            ApprovalDecision.approve(
                failed_command_plan.approval.request_id, "reviewer"))
        backend.fail_next_command = True
        before_command_failure = backend.command_calls
        failed_command = operations.command(
            failed_command_plan.request,
            approval_id=failed_command_plan.approval.request_id)
        failed_command_retry = operations.command(
            failed_command_plan.request,
            approval_id=failed_command_plan.approval.request_id)
        check("failed_command_crosses_backend_once_and_consumes_approval",
              failed_command.error_code == "backend_failed"
              and failed_command_retry.error_code == "approval_not_usable"
              and backend.command_calls == before_command_failure + 1)

        check("workspace_effects_store_digests_not_file_or_stdin_bodies",
              "body-value-483" not in json_for_effect(write_plan.effect)
              and "approved command" not in json_for_effect(
                  command_plan.effect))

        workspace_inits = [event for event in runtime.ledger.events
                           if event.get("event") == "init"
                           and event.get("profile_id")
                           == "practitioner.code_execution"]
        terminal_ids = {event["loop_id"] for event in runtime.ledger.events
                        if event.get("event") == "terminal"}
        run_step_counts = {
            event["loop_id"]: sum(
                item.get("event") == "run_step"
                and item.get("loop_id") == event["loop_id"]
                for item in runtime.ledger.events)
            for event in workspace_inits}
        check("workspace_calls_are_one_typed_terminal_code_execution_loop",
              len(workspace_inits) == 14
              and all(event.get("relationship_kind") == "starting"
                      and event.get("role") == "practitioner"
                      and len(event.get("input_roles", ())) == 1
                      and len(event.get("output_roles", ())) == 1
                      and event["loop_id"] in terminal_ids
                      and run_step_counts[event["loop_id"]] == 1
                      for event in workspace_inits))
        check("workspace_and_approval_services_share_one_runtime_object",
              operations.runtime is approvals.runtime is runtime)

        spawned_ledger = LoopLedger()
        spawning = Loop(
            "own spawned workspace operations",
            LoopConfig(allowable_modes=("deterministic",),
                       preferred_modes=("deterministic",),
                       delegated_modes=("deterministic",)),
            ledger=spawned_ledger)
        spawned_backend = _CountingBackend(local)
        spawned_backend.ledger = spawned_ledger
        spawned_runtime = RuntimeObservationServices(
            parent=spawning, ledger=spawned_ledger)
        spawned_operations = WorkspaceOperationService(
            spawned_backend, runtime=spawned_runtime)
        spawned_read = spawned_operations.file(FileRequest(
            FileOperation.READ, "reviewed.txt"))
        spawned_init = [event for event in spawned_ledger.events
                        if event.get("event") == "init"][-1]
        check("workspace_service_names_its_spawning_loop",
              spawned_read.ok
              and spawned_init.get("relationship_kind") == "spawned_by"
              and spawned_init.get("spawned_by_loop_id") == spawning.loop_id
              and spawned_init.get("profile_id")
              == "practitioner.code_execution"
              and spawned_backend.call_order[0][1] == 2
              and any(event.get("event") == "terminal"
                      and event.get("loop_id") == spawned_init["loop_id"]
                      for event in spawned_ledger.events))

    passed = sum(1 for test in tests if test["passed"])
    return {
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def json_for_effect(effect) -> str:
    import json
    return json.dumps(effect.to_dict(), sort_keys=True)
