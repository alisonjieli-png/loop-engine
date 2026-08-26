"""Focused offline and connected checks for the workspace Spawned executor.

The offline checks use a local restricted backend and a fake approval
service. The connected check runs only when an immutable Docker image is
explicitly supplied. No provider, network, or model call is made here.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from ..core.context_artifacts import (
    ContextArtifactManager, ContextArtifactRef, ContextArtifactStore,
    ContextArtifactStoreSpec, ContextOffloadPolicy)
from ..core.runtime_observer import RuntimeObservationServices
from ..core.workspace_contracts import (
    CommandRequest, SnapshotRequest, WorkspaceSpec)
from ..core.workspace_local import RestrictedLocalWorkspace
from ..core.workspace_operations import (
    WorkspaceApprovalPlan, WorkspaceOperationService)
from ..core.workspace_optional import (
    DockerWorkspace, DockerWorkspaceDeclaration)
from .approval_state_store import LocalJsonApprovalStateStore
from .delegation_runtime import (
    DelegationBudget, DelegationConstraints, DelegationSpec,
    SpawnedTaskManager, SpawnedTaskStatus)
from .effect_approval import (
    ApprovalDecision, EffectApprovalService)
from .loop_contract import LoopContract
from .loop_profile_catalog import resolve_profile_alias
from .recursive_loop import Loop, LoopConfig, LoopLedger
from .spawned_workspace_executor import (
    WORKSPACE_COMMAND_OUTPUT_ROLE, SpawnedWorkspaceExecutorError,
    WorkspaceExecutionPolicy, WorkspaceSpawnedCommandOutput,
    WorkspaceSpawnedExecutionPlan, WorkspaceSpawnedExecutor,
    WorkspaceTrustMode)


class _CountingBackend:
    """Count physical command boundary calls around a real backend."""

    def __init__(self, backend):
        self.backend = backend
        self.spec = backend.spec
        self.command_calls = 0

    def reference(self):
        return self.backend.reference()

    def availability(self):
        return self.backend.availability()

    def file(self, request):
        return self.backend.file(request)

    def command(self, request):
        self.command_calls += 1
        return self.backend.command(request)

    def snapshot(self, request):
        return self.backend.snapshot(request)


def _services(root: str, backend, *, max_inline_bytes: int = 96):
    runtime = RuntimeObservationServices()
    approvals = EffectApprovalService(
        runtime, LocalJsonApprovalStateStore(str(Path(root) / "approvals")))
    operations = WorkspaceOperationService(
        backend, approvals=approvals, runtime=runtime)
    artifacts = ContextArtifactManager(
        ContextArtifactStore(ContextArtifactStoreSpec(
            str(Path(root) / "artifacts"))),
        ContextOffloadPolicy(
            max_inline_bytes=max_inline_bytes,
            max_inline_tokens=max(1, max_inline_bytes // 4)))
    return approvals, operations, artifacts


def _approved_plan(
        approvals: EffectApprovalService,
        operations: WorkspaceOperationService,
        command: CommandRequest,
        policy: WorkspaceExecutionPolicy,
        *, suffix: str) -> WorkspaceSpawnedExecutionPlan:
    approval_plan = operations.plan_command(
        command, loop_id=f"workspace-approval-{suffix}",
        reason="Run one exact reviewed workspace command.")
    checkpoint = approvals.create(approval_plan.approval)
    approvals.resume(
        checkpoint.pending, checkpoint.resume_token,
        ApprovalDecision.approve(
            approval_plan.approval.request_id,
            "workspace-executor-reviewer"))
    return WorkspaceSpawnedExecutionPlan(
        workspace_policy_ref=f"workspace-policy:{suffix}",
        approval_plan=approval_plan, policy=policy)


def _delegation_spec(
        plan: WorkspaceSpawnedExecutionPlan, *,
        goal: str = "run one approved workspace command",
        max_output_bytes: int = 4096,
        wall_time_seconds: float = 15.0) -> DelegationSpec:
    return DelegationSpec(
        goal=goal,
        profile=resolve_profile_alias("practitioner.code_execution"),
        contract=LoopContract(
            "workspace Spawned command", "code_only",
            output_roles=(plan.output_role,),
            effects=("spawns_process",), role="practitioner"),
        mode="deterministic",
        budget=DelegationBudget(
            max_iterations=1, max_model_calls=0,
            max_output_bytes=max_output_bytes,
            wall_time_seconds=wall_time_seconds),
        workspace_policy_ref=plan.policy_ref,
        constraints=DelegationConstraints(
            available_fields=("operation_ref",),
            capability_refs=(
                "loop_spawn", "run_history_write", "code_execution"),
            allowed_effects=("spawns_process",)),
    )


def _parent() -> Loop:
    return Loop(
        "own one workspace-backed Spawned Loop",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",)),
        ledger=LoopLedger())


async def _run_one(executor, spec):
    manager = SpawnedTaskManager(_parent(), executor)
    return manager, await _run_existing(manager, spec)


async def _run_existing(manager, spec):
    task_id = await manager.start_async(spec)
    return await manager.wait(task_id)


def _artifact_body(
        store: ContextArtifactStore,
        output: WorkspaceSpawnedCommandOutput) -> dict:
    ref = ContextArtifactRef(
        output.output_ref.digest, output.output_ref.byte_count,
        media_type=output.output_ref.media_type,
        artifact_kind=output.output_ref.artifact_kind)
    return json.loads(store.get_text(ref))


def run_checks() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    trusted_missing_ack = False
    try:
        WorkspaceExecutionPolicy(WorkspaceTrustMode.TRUSTED_HOST)
    except SpawnedWorkspaceExecutorError:
        trusted_missing_ack = True
    check("trusted_host_policy_needs_explicit_acknowledgement",
          trusted_missing_ack)

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-spawned-workspace-") as root:
        workspace_root = Path(root) / "workspace"
        workspace_root.mkdir()
        local = RestrictedLocalWorkspace(WorkspaceSpec(
            "spawned_local", str(workspace_root),
            execution_enabled=True, allowed_commands=(sys.executable,)))
        backend = _CountingBackend(local)
        approvals, operations, artifacts = _services(root, backend)

        private_name = "LOOP_ENGINE_PRIVATE_EXECUTOR_TEST"
        previous = os.environ.get(private_name)
        os.environ[private_name] = "must-not-cross"
        command = CommandRequest(
            (sys.executable, "-c",
             "import os; print(os.getenv('LOOP_ENGINE_PRIVATE_EXECUTOR_TEST', "
             "'absent')); print('x' * 512)"),
            timeout_seconds=5.0, max_output_bytes=2048,
            execution_authorized=True)
        trusted = WorkspaceExecutionPolicy(
            WorkspaceTrustMode.TRUSTED_HOST,
            trusted_host_acknowledged=True)
        plan = _approved_plan(
            approvals, operations, command, trusted, suffix="trusted-local")
        executor = WorkspaceSpawnedExecutor(plan, operations, artifacts)
        manager, snapshot = asyncio.run(_run_one(
            executor, _delegation_spec(plan)))
        if previous is None:
            os.environ.pop(private_name, None)
        else:
            os.environ[private_name] = previous

        result = snapshot.result
        output = (result.outputs[0].value if result and result.outputs else None)
        body = (_artifact_body(artifacts.store, output)
                if isinstance(output, WorkspaceSpawnedCommandOutput) else {})
        check("real_trusted_host_command_runs_once_through_spawned_manager",
              snapshot.status is SpawnedTaskStatus.SUCCEEDED
              and backend.command_calls == 1
              and isinstance(output, WorkspaceSpawnedCommandOutput)
              and output.command_attempts == 1
              and output.backend_kind == "restricted_local"
              and output.offloaded and not output.stdout_inline
              and body.get("stdout", "").startswith("absent\n")
              and "must-not-cross" not in json.dumps(body),
              str(output.safe_summary() if output else snapshot))

        spawned_inits = [
            event for event in manager._parent.ledger.events
            if event.get("event") == "init"
            and event.get("relationship_kind") == "spawned_by"]
        spawned_terminals = {
            event["loop_id"] for event in manager._parent.ledger.events
            if event.get("event") == "terminal"}
        check("one_canonical_spawned_loop_owns_the_command_result",
              len(spawned_inits) == 1
              and spawned_inits[0]["loop_id"] in spawned_terminals
              and result is not None and result.steps_run == 1
              and result.model_calls == 0)
        serialized = repr(snapshot)
        check("public_result_omits_parent_ledger_environment_and_raw_output",
              "must-not-cross" not in serialized
              and "LoopLedger" not in serialized
              and "parent" not in serialized
              and "x" * 80 not in serialized)

        replay = asyncio.run(_run_existing(
            manager,
            _delegation_spec(plan, goal="try consumed command authority")))
        check("consumed_command_approval_cannot_cross_the_backend_twice",
              replay.status is SpawnedTaskStatus.FAILED
              and backend.command_calls == 1
              and replay.result is not None
              and replay.result.error_code == "approval_not_usable")

        untrusted_plan = _approved_plan(
            approvals, operations, command, WorkspaceExecutionPolicy(),
            suffix="untrusted-local")
        untrusted_executor = WorkspaceSpawnedExecutor(
            untrusted_plan, operations, artifacts)
        _, untrusted_result = asyncio.run(_run_one(
            untrusted_executor, _delegation_spec(untrusted_plan)))
        check("untrusted_code_is_refused_on_restricted_local_backend",
              untrusted_result.status is SpawnedTaskStatus.FAILED
              and backend.command_calls == 1)

        changed_request = replace(
            command, argv=(sys.executable, "-c", "print('changed')"))
        changed_approval_plan = WorkspaceApprovalPlan(
            changed_request, plan.approval_plan.approval,
            plan.approval_plan.effect)
        changed_plan = replace(plan, approval_plan=changed_approval_plan)
        changed_executor = WorkspaceSpawnedExecutor(
            changed_plan, operations, artifacts)
        _, changed_result = asyncio.run(_run_one(
            changed_executor, _delegation_spec(changed_plan)))
        check("changed_command_cannot_reuse_the_exact_approval",
              changed_result.status is SpawnedTaskStatus.FAILED
              and backend.command_calls == 1)

        environment_refused = False
        try:
            environment_command = replace(
                command, environment_keys=(private_name,))
            WorkspaceSpawnedExecutionPlan(
                "workspace-policy:environment",
                operations.plan_command(
                    environment_command, loop_id="environment-plan",
                    reason="This plan must be refused."),
                trusted)
        except SpawnedWorkspaceExecutorError:
            environment_refused = True
        check("execution_plan_cannot_import_host_environment",
              environment_refused)

        async def nonblocking_case():
            slow_command = CommandRequest(
                (sys.executable, "-c",
                 "import time; time.sleep(0.15); print('thread complete')"),
                timeout_seconds=2.0, max_output_bytes=1024,
                execution_authorized=True)
            slow_plan = _approved_plan(
                approvals, operations, slow_command, trusted,
                suffix="async-thread")
            slow_manager = SpawnedTaskManager(
                _parent(), WorkspaceSpawnedExecutor(
                    slow_plan, operations, artifacts))
            task_id = await slow_manager.start_async(
                _delegation_spec(
                    slow_plan, goal="run nonblocking workspace command",
                    wall_time_seconds=5.0))
            await asyncio.wait_for(asyncio.sleep(0.01), timeout=0.1)
            remained_responsive = (
                slow_manager.status(task_id).status
                is SpawnedTaskStatus.RUNNING)
            finished = await slow_manager.wait(task_id)
            return remained_responsive, finished

        responsive, slow = asyncio.run(nonblocking_case())
        check("async_executor_keeps_the_event_loop_responsive",
              responsive and slow.status is SpawnedTaskStatus.SUCCEEDED
              and backend.command_calls == 2)

        short_budget_result = asyncio.run(_run_one(
            WorkspaceSpawnedExecutor(plan, operations, artifacts),
            _delegation_spec(
                plan, goal="refuse oversized command output budget",
                max_output_bytes=1024)))[1]
        check("command_output_limit_cannot_exceed_spawned_budget",
              short_budget_result.status is SpawnedTaskStatus.FAILED
              and backend.command_calls == 2)

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "spawned_workspace_executor_checks/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def run_live_docker_check(image: str) -> dict:
    """Run one approved command through an existing immutable Docker image."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-spawned-docker-") as root:
        backend = _CountingBackend(DockerWorkspace(
            WorkspaceSpec(
                "spawned_docker", root, backend_kind="docker",
                execution_enabled=True, allowed_commands=("python3",),
                network_access=False),
            DockerWorkspaceDeclaration(image=image)))
        approvals, operations, artifacts = _services(
            root, backend, max_inline_bytes=64)
        command = CommandRequest(
            ("python3", "-c", "print('spawned docker workspace')"),
            timeout_seconds=20.0, max_output_bytes=1024,
            execution_authorized=True)
        plan = _approved_plan(
            approvals, operations, command, WorkspaceExecutionPolicy(),
            suffix="untrusted-docker")
        manager, snapshot = asyncio.run(_run_one(
            WorkspaceSpawnedExecutor(plan, operations, artifacts),
            _delegation_spec(
                plan, goal="run one sandboxed Docker command",
                wall_time_seconds=30.0)))
        result = snapshot.result
        output = (result.outputs[0].value if result and result.outputs else None)
        body = (_artifact_body(artifacts.store, output)
                if isinstance(output, WorkspaceSpawnedCommandOutput) else {})
        check("untrusted_plan_uses_declared_docker_sandbox",
              snapshot.status is SpawnedTaskStatus.SUCCEEDED
              and isinstance(output, WorkspaceSpawnedCommandOutput)
              and output.backend_kind == "docker"
              and output.command_attempts == 1
              and backend.command_calls == 1,
              str(snapshot))
        check("docker_command_uses_no_network_and_returns_through_spawned_loop",
              body.get("stdout", "").strip() == "spawned docker workspace"
              and manager._parent.audit_closure()["closed"]
              and not backend.spec.network_access,
              body.get("stderr", ""))
        snapshot_ref = backend.snapshot(SnapshotRequest(include_hidden=True))
        check("docker_workspace_remains_bounded_and_snapshotable",
              snapshot_ref.workspace.backend_kind == "docker")

    passed = sum(1 for test in tests if test["passed"])
    return {
        "record_type": "spawned_workspace_docker_verification/v1",
        "image": image,
        "network_access": False,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }
