"""Typed requests, results, references, and policies for workspaces.

This module owns data only. Backend implementations accept these objects so a
Loop does not need a long provider-specific argument list.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class FileOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    LIST = "list"
    STAT = "stat"


@dataclass(frozen=True)
class WorkspaceSpec:
    """Shared policy and identity for one bounded workspace."""

    workspace_id: str
    root: str
    backend_kind: str = "restricted_local"
    execution_enabled: bool = False
    allowed_commands: tuple[str, ...] = ()
    max_file_bytes: int = 16 * 1024 * 1024
    network_access: bool = False

    def __post_init__(self):
        if not self.workspace_id:
            raise ValueError("a workspace needs workspace_id")
        if not self.root:
            raise ValueError("a workspace needs an explicit root")
        if not self.backend_kind:
            raise ValueError("a workspace needs backend_kind")
        if self.max_file_bytes < 1:
            raise ValueError("max_file_bytes must be positive")
        if any(not command for command in self.allowed_commands):
            raise ValueError("allowed command names cannot be empty")


@dataclass(frozen=True)
class WorkspaceRef:
    """A serializable reference to a configured workspace boundary."""

    workspace_id: str
    backend_kind: str
    root: str

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "backend_kind": self.backend_kind,
            "root": self.root,
        }


@dataclass(frozen=True)
class BackendAvailability:
    available: bool
    backend_kind: str
    reason_code: str
    detail: str = ""
    dependency_detected: bool = False
    runtime_verified: bool = False

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "backend_kind": self.backend_kind,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "dependency_detected": self.dependency_detected,
            "runtime_verified": self.runtime_verified,
        }


@dataclass(frozen=True)
class FileRequest:
    """One file operation relative to a workspace root."""

    operation: FileOperation
    path: str
    content: bytes = b""
    replace_existing: bool = False
    create_parents: bool = False
    expected_digest: str = ""

    def __post_init__(self):
        if not isinstance(self.operation, FileOperation):
            raise TypeError("operation must be a known FileOperation")
        if self.operation is not FileOperation.LIST and not self.path:
            raise ValueError("file operation needs a relative path")
        if not isinstance(self.content, bytes):
            raise TypeError("file content must be bytes")
        if self.operation is not FileOperation.WRITE and self.content:
            raise ValueError("only a write request can carry content")
        if self.expected_digest and (
                len(self.expected_digest) != 64 or any(
                    char not in "0123456789abcdef"
                    for char in self.expected_digest)):
            raise ValueError("expected_digest must be a lowercase SHA-256 value")

    def to_dict(self) -> dict:
        return {
            "operation": self.operation.value,
            "path": self.path,
            "content_base64": (
                base64.b64encode(self.content).decode("ascii")
                if self.content else ""),
            "replace_existing": self.replace_existing,
            "create_parents": self.create_parents,
            "expected_digest": self.expected_digest,
        }


@dataclass(frozen=True)
class FileResult:
    ok: bool
    operation: FileOperation
    path: str
    content: bytes = b""
    entries: tuple[str, ...] = ()
    digest: str = ""
    byte_count: int = 0
    error_code: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "operation": self.operation.value,
            "path": self.path,
            "content_base64": (
                base64.b64encode(self.content).decode("ascii")
                if self.content else ""),
            "entries": list(self.entries),
            "digest": self.digest,
            "byte_count": self.byte_count,
            "error_code": self.error_code,
            "error": self.error,
        }


@dataclass(frozen=True)
class CommandRequest:
    """One argv-based command request with explicit execution authority."""

    argv: tuple[str, ...]
    cwd: str = "."
    environment_keys: tuple[str, ...] = ()
    stdin_text: str = ""
    timeout_seconds: float = 60.0
    max_output_bytes: int = 1024 * 1024
    execution_authorized: bool = False

    def __post_init__(self):
        if not self.argv or any(not value for value in self.argv):
            raise ValueError("a command needs nonempty argv values")
        if any("\x00" in value for value in self.argv):
            raise ValueError("command argv cannot contain null bytes")
        if self.timeout_seconds <= 0:
            raise ValueError("command timeout_seconds must be positive")
        if self.max_output_bytes < 1:
            raise ValueError("command max_output_bytes must be positive")
        keys = self.environment_keys
        if (len(keys) != len(set(keys)) or any(
                not key or "=" in key or "\x00" in key for key in keys)):
            raise ValueError("environment keys must be unique and nonempty")

    def to_dict(self) -> dict:
        return {
            "argv": list(self.argv),
            "cwd": self.cwd,
            "environment_keys": list(self.environment_keys),
            "stdin_text": self.stdin_text,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    argv: tuple[str, ...]
    exit_code: "int | None" = None
    stdout: str = ""
    stderr: str = ""
    error_code: str = ""
    error: str = ""
    output_truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "argv": list(self.argv),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_code": self.error_code,
            "error": self.error,
            "output_truncated": self.output_truncated,
        }


@dataclass(frozen=True)
class SnapshotRequest:
    include_hidden: bool = False
    max_files: int = 10_000

    def __post_init__(self):
        if self.max_files < 1:
            raise ValueError("snapshot max_files must be positive")


@dataclass(frozen=True)
class WorkspaceSnapshotRef:
    workspace: WorkspaceRef
    digest: str
    file_count: int
    total_bytes: int
    algorithm: str = "sha256_path_and_content_v1"

    def __post_init__(self):
        if (len(self.digest) != 64 or any(
                char not in "0123456789abcdef" for char in self.digest)):
            raise ValueError("snapshot digest must be a lowercase SHA-256 value")
        if self.file_count < 0 or self.total_bytes < 0:
            raise ValueError("snapshot counts cannot be negative")

    def to_dict(self) -> dict:
        return {
            "workspace": self.workspace.to_dict(),
            "digest": self.digest,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "algorithm": self.algorithm,
        }


class WorkspaceBackend(Protocol):
    """Common contract for local, sandboxed, and remote workspaces."""

    spec: WorkspaceSpec

    def reference(self) -> WorkspaceRef: ...

    def availability(self) -> BackendAvailability: ...

    def file(self, request: FileRequest) -> FileResult: ...

    def command(self, request: CommandRequest) -> CommandResult: ...

    def snapshot(self, request: SnapshotRequest) -> WorkspaceSnapshotRef: ...


def _file_error(request: FileRequest, code: str, detail: str) -> FileResult:
    return FileResult(
        ok=False, operation=request.operation, path=request.path,
        error_code=code, error=detail)


def _command_error(request: CommandRequest, code: str,
                   detail: str) -> CommandResult:
    return CommandResult(
        ok=False, argv=request.argv, error_code=code, error=detail)


def _bounded_text(value: str, max_bytes: int) -> tuple[str, bool]:
    raw = value.encode("utf-8")
    if len(raw) <= max_bytes:
        return value, False
    return raw[:max_bytes].decode("utf-8", errors="ignore"), True
