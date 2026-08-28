"""Approval-aware operations over the existing workspace backend contract.

This service maps writes and commands to exact native EffectSpec objects,
consumes one approval, and calls the supplied backend at most once. It does
not implement files, commands, snapshots, or another approval system.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable, TypeVar

from ..loop.effect_approval import (
    ApprovalRequest, EffectApprovalService, EffectClass, EffectSpec)
from .workspace_contracts import (
    CommandRequest, CommandResult, FileOperation, FileRequest, FileResult,
    SnapshotRequest, WorkspaceBackend, WorkspaceSnapshotRef,
    _command_error, _file_error)


_T = TypeVar("_T")

_WORKSPACE_OPERATION_PORTS = {
    "workspace_file_read": ("file_request", "file_result", ("reads_fs",)),
    "workspace_file_list": ("file_request", "file_result", ("reads_fs",)),
    "workspace_file_stat": ("file_request", "file_result", ("reads_fs",)),
    "workspace_file_write": ("file_request", "file_result", ("writes_fs",)),
    "workspace_command": (
        "command_request", "command_result", ("spawns_process",)),
    "workspace_snapshot": (
        "snapshot_request", "workspace_snapshot_ref", ("reads_fs",)),
}


class WorkspaceOperationError(RuntimeError):
    """A workspace operation could not reach its typed backend safely."""


@dataclass(frozen=True)
class WorkspaceApprovalPlan:
    """One exact mutating request and its native approval request."""

    request: FileRequest | CommandRequest
    approval: ApprovalRequest
    effect: EffectSpec

    def __post_init__(self) -> None:
        if self.approval.effect != self.effect:
            raise WorkspaceOperationError(
                "workspace approval does not match its effect")
        if (isinstance(self.request, FileRequest)
                and self.request.operation is not FileOperation.WRITE):
            raise WorkspaceOperationError(
                "only a file write can enter an approval plan")
        if not isinstance(self.request, (FileRequest, CommandRequest)):
            raise TypeError(
                "workspace plan needs FileRequest or CommandRequest")


class WorkspaceOperationService:
    """Apply policy, exact approval, and one backend boundary crossing."""

    def __init__(self, backend: WorkspaceBackend, *,
                 approvals: EffectApprovalService | None = None,
                 runtime=None):
        required = ("reference", "file", "command", "snapshot")
        if any(not callable(getattr(backend, name, None)) for name in required):
            raise TypeError("backend must implement WorkspaceBackend")
        if approvals is not None and not isinstance(
                approvals, EffectApprovalService):
            raise TypeError("approvals must be EffectApprovalService")
        from .runtime_observer import RuntimeObservationServices
        if runtime is not None and not isinstance(
                runtime, RuntimeObservationServices):
            raise TypeError("runtime must be RuntimeObservationServices")
        if (runtime is not None and approvals is not None
                and approvals.runtime is not runtime):
            raise WorkspaceOperationError(
                "workspace and approval services must share one runtime")
        self.backend = backend
        self.approvals = approvals
        self.runtime = (runtime or (
            approvals.runtime if approvals is not None
            else RuntimeObservationServices()))

    def plan_file_write(self, request: FileRequest, *, loop_id: str,
                        reason: str) -> WorkspaceApprovalPlan:
        effect = self.file_effect(request)
        approval = ApprovalRequest.create(
            loop_id, effect, reason, requested_by="workspace_operation")
        return WorkspaceApprovalPlan(request, approval, effect)

    def plan_command(self, request: CommandRequest, *, loop_id: str,
                     reason: str) -> WorkspaceApprovalPlan:
        effect = self.command_effect(request)
        approval = ApprovalRequest.create(
            loop_id, effect, reason, requested_by="workspace_operation")
        return WorkspaceApprovalPlan(request, approval, effect)

    def file_effect(self, request: FileRequest) -> EffectSpec:
        if (not isinstance(request, FileRequest)
                or request.operation is not FileOperation.WRITE):
            raise WorkspaceOperationError(
                "file effect mapping accepts writes only")
        workspace = self.backend.reference()
        return EffectSpec(
            EffectClass.LOCAL_WRITE,
            "workspace_file_write",
            f"workspace:{workspace.workspace_id}:file:{request.path}",
            tuple(sorted({
                "backend_kind": workspace.backend_kind,
                "content_digest": hashlib.sha256(
                    request.content).hexdigest(),
                "create_parents": str(request.create_parents).lower(),
                "expected_digest": request.expected_digest,
                "replace_existing": str(request.replace_existing).lower(),
                "root_digest": _text_digest(workspace.root),
                "workspace_id": workspace.workspace_id,
            }.items())),
        )

    def command_effect(self, request: CommandRequest) -> EffectSpec:
        if not isinstance(request, CommandRequest):
            raise TypeError("command effect mapping needs CommandRequest")
        workspace = self.backend.reference()
        return EffectSpec(
            EffectClass.COMMAND_EXECUTION,
            "workspace_command",
            f"workspace:{workspace.workspace_id}:command:{request.argv[0]}",
            tuple(sorted({
                "backend_kind": workspace.backend_kind,
                "network_access": str(
                    bool(self.backend.spec.network_access)).lower(),
                "request_digest": _mapping_digest(request.to_dict()),
                "root_digest": _text_digest(workspace.root),
                "workspace_id": workspace.workspace_id,
            }.items())),
        )

    def file(self, request: FileRequest, *, approval_id: str = "") -> FileResult:
        if not isinstance(request, FileRequest):
            raise TypeError("file needs FileRequest")
        operation = {
            FileOperation.READ: "workspace_file_read",
            FileOperation.LIST: "workspace_file_list",
            FileOperation.STAT: "workspace_file_stat",
            FileOperation.WRITE: "workspace_file_write",
        }[request.operation]
        return self._run_operation(
            operation, lambda _loop: self._file_core(
                request, approval_id=approval_id))

    def _file_core(
            self, request: FileRequest, *, approval_id: str) -> FileResult:
        if request.operation is not FileOperation.WRITE:
            return self._call_file_once(request)
        error = self._consume(approval_id, self.file_effect(request))
        if error:
            return _file_error(request, error, _approval_error_text(error))
        return self._call_file_once(request)

    def command(self, request: CommandRequest, *,
                approval_id: str = "") -> CommandResult:
        if not isinstance(request, CommandRequest):
            raise TypeError("command needs CommandRequest")
        return self._run_operation(
            "workspace_command", lambda _loop: self._command_core(
                request, approval_id=approval_id))

    def _command_core(
            self, request: CommandRequest, *,
            approval_id: str) -> CommandResult:
        error = self._consume(approval_id, self.command_effect(request))
        if error:
            return _command_error(request, error, _approval_error_text(error))
        return self._call_command_once(request)

    def snapshot(self, request: SnapshotRequest) -> WorkspaceSnapshotRef:
        if not isinstance(request, SnapshotRequest):
            raise TypeError("snapshot needs SnapshotRequest")
        return self._run_operation(
            "workspace_snapshot",
            lambda _loop: self.backend.snapshot(request))

    def _run_operation(
            self, operation: str,
            action: Callable[[object], _T]) -> _T:
        """Run one typed backend operation in one code-execution Loop."""
        from ..loop.service_loop_envelope import (
            ServiceLoopSpec, run_service_operation)
        input_role, output_role, effects = _WORKSPACE_OPERATION_PORTS[operation]
        return run_service_operation(self.runtime, ServiceLoopSpec(
            operation=operation,
            profile_id="practitioner.code_execution",
            input_role=input_role, output_role=output_role, effects=effects,
            objective=f"execute workspace operation: {operation}",
            failure_kind="workspace_operation_failed"), action)

    def _consume(self, approval_id: str, effect: EffectSpec) -> str:
        if not approval_id or self.approvals is None:
            return "approval_required"
        try:
            self.approvals.consume(approval_id, effect)
        except KeyError:
            return "approval_not_found"
        except (PermissionError, RuntimeError, ValueError):
            return "approval_not_usable"
        return ""

    def _call_file_once(self, request: FileRequest) -> FileResult:
        try:
            return self.backend.file(request)
        except Exception as exc:  # noqa: BLE001
            return _file_error(
                request, "backend_failed",
                f"{type(exc).__name__}: {str(exc)[:160]}")

    def _call_command_once(self, request: CommandRequest) -> CommandResult:
        try:
            return self.backend.command(request)
        except Exception as exc:  # noqa: BLE001
            return _command_error(
                request, "backend_failed",
                f"{type(exc).__name__}: {str(exc)[:160]}")


def _mapping_digest(value: dict) -> str:
    body = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _approval_error_text(code: str) -> str:
    return {
        "approval_required": "exact effect approval is required",
        "approval_not_found": "approval request id is unavailable",
        "approval_not_usable": "approval does not match or was already used",
    }[code]


def self_test() -> dict:
    """Run write, command, failure, replay, and changed-request checks."""
    from .workspace_operation_checks import run_checks
    return run_checks()
