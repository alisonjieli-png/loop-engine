"""Workspace-backed execution for one canonical Spawned Loop.

The executor accepts only the public ``SpawnedExecutionRequest``. A typed,
immutable plan binds one exact command approval to one workspace policy. The
physical command crosses ``WorkspaceOperationService`` once from inside the
Spawned Loop's single execution step. Large output is stored through the
existing ``ContextArtifactManager`` before a bounded result is returned.

Restricted host execution is accepted only under an explicit trusted-host
policy. Untrusted work requires a declared sandbox backend. The executor does
not receive or return the spawning Loop, event ledger, secrets, Runtime
Memory, or host environment values.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from ..core.context_artifacts import (
    ContextArtifactManager, ContextArtifactRef)
from ..core.workspace_contracts import (
    CommandRequest, CommandResult)
from ..core.workspace_operations import (
    WorkspaceApprovalPlan, WorkspaceOperationService)
from .delegation_runtime import (
    DelegationError, LoopPortValue, SpawnedExecutionRequest,
    SpawnedLoopResult, SpawnedTaskStatus)
from .loop_role import LoopRelationshipKind, LoopRole
from .recursive_loop import StepOutcome


WORKSPACE_COMMAND_OUTPUT_ROLE = "workspace_command_output/v1"
WORKSPACE_EXECUTION_PLAN_VERSION = "workspace_spawned_execution_plan/v1"
_SANDBOX_BACKENDS = ("docker", "e2b", "modal")
_NO_PHYSICAL_ATTEMPT_CODES = frozenset({
    "adapter_not_registered", "approval_not_found", "approval_not_usable",
    "approval_required", "command_not_allowed", "dependency_unavailable",
    "execution_disabled", "execution_not_authorized",
    "path_outside_workspace", "workspace_root_unavailable",
    "working_directory_unavailable",
})


class SpawnedWorkspaceExecutorError(RuntimeError):
    """A workspace execution plan or Spawned Loop request failed closed."""


class WorkspaceTrustMode(str, Enum):
    """Whether command code is trusted to run on the configured host."""

    UNTRUSTED = "untrusted"
    TRUSTED_HOST = "trusted_host"


@dataclass(frozen=True)
class WorkspaceExecutionPolicy:
    """Explicit trust decision and admitted sandbox backend kinds."""

    trust_mode: WorkspaceTrustMode = WorkspaceTrustMode.UNTRUSTED
    trusted_host_acknowledged: bool = False
    sandbox_backend_kinds: tuple[str, ...] = _SANDBOX_BACKENDS

    def __post_init__(self) -> None:
        mode = self.trust_mode
        if not isinstance(mode, WorkspaceTrustMode):
            try:
                mode = WorkspaceTrustMode(mode)
            except (TypeError, ValueError) as exc:
                raise SpawnedWorkspaceExecutorError(
                    "workspace trust mode is not recognized") from exc
            object.__setattr__(self, "trust_mode", mode)
        if not isinstance(self.trusted_host_acknowledged, bool):
            raise SpawnedWorkspaceExecutorError(
                "trusted_host_acknowledged must be a boolean")
        backends = tuple(self.sandbox_backend_kinds)
        if (not backends
                or any(not isinstance(item, str) or not item.strip()
                       for item in backends)
                or len(backends) != len(set(backends))
                or "restricted_local" in backends):
            raise SpawnedWorkspaceExecutorError(
                "sandbox backend kinds must be unique, non-empty, and not "
                "restricted_local")
        object.__setattr__(self, "sandbox_backend_kinds", backends)
        if (mode is WorkspaceTrustMode.TRUSTED_HOST
                and not self.trusted_host_acknowledged):
            raise SpawnedWorkspaceExecutorError(
                "trusted host execution needs explicit acknowledgement")
        if (mode is WorkspaceTrustMode.UNTRUSTED
                and self.trusted_host_acknowledged):
            raise SpawnedWorkspaceExecutorError(
                "untrusted policy cannot acknowledge trusted host execution")

    def permits(self, backend_kind: str) -> bool:
        if backend_kind == "restricted_local":
            return (self.trust_mode is WorkspaceTrustMode.TRUSTED_HOST
                    and self.trusted_host_acknowledged)
        return backend_kind in self.sandbox_backend_kinds

    def to_dict(self) -> dict:
        return {
            "trust_mode": self.trust_mode.value,
            "trusted_host_acknowledged": self.trusted_host_acknowledged,
            "sandbox_backend_kinds": list(self.sandbox_backend_kinds),
        }


@dataclass(frozen=True)
class WorkspaceSpawnedExecutionPlan:
    """One exact approved command and the policy that permits its backend."""

    workspace_policy_ref: str
    approval_plan: WorkspaceApprovalPlan
    policy: WorkspaceExecutionPolicy
    output_role: str = WORKSPACE_COMMAND_OUTPUT_ROLE
    plan_version: str = WORKSPACE_EXECUTION_PLAN_VERSION

    def __post_init__(self) -> None:
        if (not isinstance(self.workspace_policy_ref, str)
                or not self.workspace_policy_ref.strip()):
            raise SpawnedWorkspaceExecutorError(
                "workspace plan needs workspace_policy_ref")
        if not isinstance(self.approval_plan, WorkspaceApprovalPlan):
            raise SpawnedWorkspaceExecutorError(
                "workspace plan needs WorkspaceApprovalPlan")
        if not isinstance(self.approval_plan.request, CommandRequest):
            raise SpawnedWorkspaceExecutorError(
                "workspace spawned execution supports commands only")
        if not isinstance(self.policy, WorkspaceExecutionPolicy):
            raise SpawnedWorkspaceExecutorError(
                "workspace plan needs WorkspaceExecutionPolicy")
        if not isinstance(self.output_role, str) or not self.output_role.strip():
            raise SpawnedWorkspaceExecutorError(
                "workspace plan needs a typed output role")
        if self.plan_version != WORKSPACE_EXECUTION_PLAN_VERSION:
            raise SpawnedWorkspaceExecutorError(
                "workspace execution plan version is not supported")
        request = self.approval_plan.request
        if not request.execution_authorized:
            raise SpawnedWorkspaceExecutorError(
                "workspace command needs explicit request authority")
        if request.environment_keys:
            raise SpawnedWorkspaceExecutorError(
                "spawned workspace commands cannot import host environment")
        if request.stdin_text:
            raise SpawnedWorkspaceExecutorError(
                "spawned workspace commands cannot carry secret-prone stdin")
        if self.approval_plan.approval.requested_by != "workspace_operation":
            raise SpawnedWorkspaceExecutorError(
                "workspace command approval must come from the workspace "
                "operation service")

    @property
    def digest(self) -> str:
        body = {
            "approval": self.approval_plan.approval.to_dict(),
            "command": self.approval_plan.request.to_dict(),
            "effect": self.approval_plan.effect.to_dict(),
            "output_role": self.output_role,
            "plan_version": self.plan_version,
            "policy": self.policy.to_dict(),
            "workspace_policy_ref": self.workspace_policy_ref,
        }
        return hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()

    @property
    def policy_ref(self) -> str:
        return f"workspace-execution-plan:{self.digest}"


@dataclass(frozen=True)
class WorkspaceSpawnedCommandOutput:
    """Bounded command result with an immutable raw-output reference."""

    plan_digest: str
    workspace_id: str
    backend_kind: str
    ok: bool
    exit_code: "int | None"
    output_ref: ContextArtifactRef
    stdout_inline: str = ""
    stderr_inline: str = ""
    offloaded: bool = False
    output_truncated: bool = False
    command_attempts: int = 0
    error_code: str = ""
    record_type: str = "workspace_spawned_command_output/v1"

    def __post_init__(self) -> None:
        _require_digest(self.plan_digest, "plan_digest")
        if not self.workspace_id or not self.backend_kind:
            raise SpawnedWorkspaceExecutorError(
                "workspace output needs workspace identity")
        if not isinstance(self.output_ref, ContextArtifactRef):
            raise SpawnedWorkspaceExecutorError(
                "workspace output needs ContextArtifactRef")
        if self.offloaded and (self.stdout_inline or self.stderr_inline):
            raise SpawnedWorkspaceExecutorError(
                "offloaded output cannot also carry inline text")
        if self.command_attempts not in (0, 1):
            raise SpawnedWorkspaceExecutorError(
                "workspace command attempts must be zero or one")
        if self.record_type != "workspace_spawned_command_output/v1":
            raise SpawnedWorkspaceExecutorError(
                "workspace output record type is not supported")

    def safe_summary(self) -> dict:
        return {
            "record_type": self.record_type,
            "plan_digest": self.plan_digest,
            "workspace_id": self.workspace_id,
            "backend_kind": self.backend_kind,
            "ok": self.ok,
            "exit_code": self.exit_code,
            "output_ref": self.output_ref.to_dict(),
            "offloaded": self.offloaded,
            "output_truncated": self.output_truncated,
            "command_attempts": self.command_attempts,
            "error_code": self.error_code,
        }


def _require_digest(value: str, label: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef"
                   for character in value)):
        raise SpawnedWorkspaceExecutorError(
            f"{label} must be a lowercase SHA-256 value")


class WorkspaceSpawnedExecutor:
    """Asynchronous adapter from SpawnedTaskManager to workspace command."""

    __slots__ = ("__operations", "__artifacts", "__plan")

    def __init__(self, plan: WorkspaceSpawnedExecutionPlan,
                 operations: WorkspaceOperationService,
                 artifacts: ContextArtifactManager) -> None:
        if not isinstance(plan, WorkspaceSpawnedExecutionPlan):
            raise TypeError("plan must be WorkspaceSpawnedExecutionPlan")
        if not isinstance(operations, WorkspaceOperationService):
            raise TypeError("operations must be WorkspaceOperationService")
        if operations.approvals is None:
            raise SpawnedWorkspaceExecutorError(
                "workspace executor needs EffectApprovalService")
        if not isinstance(artifacts, ContextArtifactManager):
            raise TypeError("artifacts must be ContextArtifactManager")
        self.__plan = plan
        self.__operations = operations
        self.__artifacts = artifacts

    async def __call__(
            self, request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        plan = self._validate_request(request)
        return await asyncio.to_thread(self._execute, request, plan)

    def _validate_request(
            self, request: SpawnedExecutionRequest
            ) -> WorkspaceSpawnedExecutionPlan:
        if not isinstance(request, SpawnedExecutionRequest):
            raise SpawnedWorkspaceExecutorError(
                "executor needs SpawnedExecutionRequest")
        plan = self.__plan
        spec = request.spec
        if spec.mode != "deterministic":
            raise SpawnedWorkspaceExecutorError(
                "workspace executor supports deterministic Spawned Loops")
        if (request.runtime.identity.role is not LoopRole.PRACTITIONER
                or request.runtime.identity.profile_id
                != "practitioner.code_execution"):
            raise SpawnedWorkspaceExecutorError(
                "workspace executor needs the code-execution Practitioner "
                "profile")
        if (request.runtime.relationship.kind
                is not LoopRelationshipKind.SPAWNED_BY):
            raise SpawnedWorkspaceExecutorError(
                "workspace executor needs one canonical Spawned Loop")
        if spec.workspace_policy_ref != plan.policy_ref:
            raise SpawnedWorkspaceExecutorError(
                "Spawned Loop workspace policy does not match the plan")
        if spec.inputs or spec.contract.input_roles:
            raise SpawnedWorkspaceExecutorError(
                "workspace command plans do not accept hidden task inputs")
        if tuple(spec.contract.output_roles) != (plan.output_role,):
            raise SpawnedWorkspaceExecutorError(
                "Spawned Loop output role does not match the plan")
        if tuple(spec.contract.effects) != ("spawns_process",):
            raise SpawnedWorkspaceExecutorError(
                "workspace command contract must declare spawns_process")
        if "spawns_process" not in spec.constraints.allowed_effects:
            raise SpawnedWorkspaceExecutorError(
                "delegation constraints do not permit command execution")
        if request.runtime_memory is not None:
            raise SpawnedWorkspaceExecutorError(
                "workspace executor does not accept Runtime Memory")
        if (spec.context.selected_refs or spec.context.shared_runtime_memory):
            raise SpawnedWorkspaceExecutorError(
                "workspace executor accepts no spawning context references")
        command = plan.approval_plan.request
        if (spec.budget.max_output_bytes is not None
                and command.max_output_bytes > spec.budget.max_output_bytes):
            raise SpawnedWorkspaceExecutorError(
                "command output limit exceeds the Spawned Loop output budget")
        wall_time = spec.budget.wall_time_seconds
        if (wall_time is not None
                and command.timeout_seconds >= float(wall_time)):
            raise SpawnedWorkspaceExecutorError(
                "command timeout must be shorter than the Spawned Loop "
                "wall-time deadline")
        workspace = self.__operations.backend.reference()
        if not plan.policy.permits(workspace.backend_kind):
            raise SpawnedWorkspaceExecutorError(
                f"workspace backend {workspace.backend_kind!r} is not "
                "permitted by the execution policy")
        expected_effect = self.__operations.command_effect(command)
        if expected_effect != plan.approval_plan.effect:
            raise SpawnedWorkspaceExecutorError(
                "workspace backend or command changed after approval")
        return plan

    def _execute(
            self, request: SpawnedExecutionRequest,
            plan: WorkspaceSpawnedExecutionPlan) -> SpawnedLoopResult:
        if request.control.cancel_requested:
            counters = request.runtime.cancel(
                "workspace execution canceled before command")
            return SpawnedLoopResult(
                request.task_id, SpawnedTaskStatus.CANCELED,
                terminal_code=counters.terminal_code,
                steps_run=counters.steps_run,
                model_calls=counters.model_calls,
                error_code="CANCELED", error="workspace execution canceled")

        holder: dict[str, object] = {"crossed": False}

        def handler(_step_request):
            if holder["crossed"]:
                raise SpawnedWorkspaceExecutorError(
                    "workspace command boundary can be crossed only once")
            holder["crossed"] = True
            result = self.__operations.command(
                plan.approval_plan.request,
                approval_id=plan.approval_plan.approval.request_id)
            holder["command"] = result
            holder["output"] = self._capture(plan, result)
            return StepOutcome(
                output=("workspace_command:completed" if result.ok
                        else "workspace_command:failed"),
                mode="deterministic", confidence=1.0)

        runtime_result = request.runtime.run(handler=handler, max_steps=1)
        command = holder.get("command")
        output = holder.get("output")
        if not isinstance(command, CommandResult) \
                or not isinstance(output, WorkspaceSpawnedCommandOutput):
            raise SpawnedWorkspaceExecutorError(
                "workspace command returned no typed result")
        status = (SpawnedTaskStatus.SUCCEEDED if command.ok
                  else SpawnedTaskStatus.FAILED)
        summary = (
            f"Workspace command finished with status {status.value}; "
            f"output is stored as {output.output_ref.object_key}.")
        return SpawnedLoopResult(
            task_id=request.task_id,
            status=status,
            outputs=(LoopPortValue(plan.output_role, output),),
            summary=summary,
            terminal_code=(runtime_result.counters.terminal_code
                           if command.ok else "EFFECT_FAILED"),
            steps_run=runtime_result.counters.steps_run,
            model_calls=runtime_result.counters.model_calls,
            error_code="" if command.ok else (
                command.error_code or "workspace_command_failed"),
            error="" if command.ok else "workspace command failed",
        )

    def _capture(
            self, plan: WorkspaceSpawnedExecutionPlan,
            result: CommandResult) -> WorkspaceSpawnedCommandOutput:
        value = json.dumps({
            "error": result.error,
            "error_code": result.error_code,
            "exit_code": result.exit_code,
            "ok": result.ok,
            "stderr": result.stderr,
            "stdout": result.stdout,
            "output_truncated": result.output_truncated,
        }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload = self.__artifacts.capture(
            value, media_type="application/json",
            artifact_kind="spawned_workspace_command_output")
        workspace = self.__operations.backend.reference()
        attempts = (0 if result.error_code in _NO_PHYSICAL_ATTEMPT_CODES
                    else 1)
        return WorkspaceSpawnedCommandOutput(
            plan_digest=plan.digest,
            workspace_id=workspace.workspace_id,
            backend_kind=workspace.backend_kind,
            ok=result.ok,
            exit_code=result.exit_code,
            output_ref=payload.raw,
            stdout_inline="" if payload.offloaded else result.stdout,
            stderr_inline="" if payload.offloaded else result.stderr,
            offloaded=payload.offloaded,
            output_truncated=result.output_truncated,
            command_attempts=attempts,
            error_code=result.error_code,
        )


def verify_live_docker_spawned_executor(image: str) -> dict:
    """Run the connected executor check using one existing immutable image."""
    from .spawned_workspace_executor_checks import run_live_docker_check
    return run_live_docker_check(image)


def self_test() -> dict:
    """Run trusted-host, sandbox-policy, approval, and offload checks."""
    from .spawned_workspace_executor_checks import run_checks
    return run_checks()
