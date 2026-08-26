"""Restricted local implementation of the typed workspace contract.

This module owns local file and host-command mechanics. Use the public objects
from ``workspace_backends``. Host command execution is not an operating-system
sandbox and remains disabled unless both policy and the request authorize it.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from .workspace_contracts import (
    BackendAvailability,
    CommandRequest,
    CommandResult,
    FileOperation,
    FileRequest,
    FileResult,
    SnapshotRequest,
    WorkspaceRef,
    WorkspaceSnapshotRef,
    WorkspaceSpec,
    _bounded_text,
    _command_error,
    _file_error,
)


class RestrictedLocalWorkspace:
    """Confine typed file operations to one resolved local root."""

    def __init__(self, spec: WorkspaceSpec):
        if spec.backend_kind != "restricted_local":
            raise ValueError("local workspace needs backend_kind=restricted_local")
        root = Path(spec.root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("local workspace root must be an existing directory")
        self.spec = spec
        self._root = root

    def reference(self) -> WorkspaceRef:
        return WorkspaceRef(
            workspace_id=self.spec.workspace_id,
            backend_kind=self.spec.backend_kind,
            root=str(self._root),
        )

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            available=True,
            backend_kind=self.spec.backend_kind,
            reason_code="ready",
            detail="file boundary ready; host commands are not OS-sandboxed",
            dependency_detected=True,
            runtime_verified=True,
        )

    def file(self, request: FileRequest) -> FileResult:
        try:
            path = self._resolve_relative(request.path, allow_root=(
                request.operation is FileOperation.LIST))
        except (ValueError, OSError) as exc:
            return _file_error(request, "path_outside_workspace", str(exc))
        try:
            if request.operation is FileOperation.READ:
                return self._read(request, path)
            if request.operation is FileOperation.WRITE:
                return self._write(request, path)
            if request.operation is FileOperation.LIST:
                return self._list(request, path)
            if request.operation is FileOperation.STAT:
                return self._stat(request, path)
        except OSError as exc:
            return _file_error(request, "filesystem_error", str(exc))
        return _file_error(request, "unknown_operation", "operation is not supported")

    def command(self, request: CommandRequest) -> CommandResult:
        if not self.spec.execution_enabled:
            return _command_error(
                request, "execution_disabled",
                "workspace command execution is disabled")
        if not request.execution_authorized:
            return _command_error(
                request, "execution_not_authorized",
                "this command request lacks explicit execution authority")
        executable = request.argv[0]
        if executable not in self.spec.allowed_commands:
            return _command_error(
                request, "command_not_allowed",
                f"executable {executable!r} is not in the workspace allowlist")
        try:
            cwd = self._resolve_relative(request.cwd, allow_root=True)
        except (ValueError, OSError) as exc:
            return _command_error(request, "path_outside_workspace", str(exc))
        if not cwd.is_dir():
            return _command_error(
                request, "working_directory_unavailable",
                "command working directory is not a directory")

        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        for key in request.environment_keys:
            if key in os.environ:
                environment[key] = os.environ[key]
        try:
            process = subprocess.run(
                request.argv,
                cwd=str(cwd),
                env=environment,
                input=request.stdin_text,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return _command_error(
                request, "command_timeout",
                f"command exceeded {request.timeout_seconds} seconds")
        except OSError as exc:
            return _command_error(request, "command_start_failed", str(exc))
        stdout, stdout_cut = _bounded_text(
            process.stdout, request.max_output_bytes)
        remaining = max(1, request.max_output_bytes - len(stdout.encode("utf-8")))
        stderr, stderr_cut = _bounded_text(process.stderr, remaining)
        return CommandResult(
            ok=process.returncode == 0,
            argv=request.argv,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            error_code="" if process.returncode == 0 else "command_failed",
            error="" if process.returncode == 0 else "command returned nonzero",
            output_truncated=stdout_cut or stderr_cut,
        )

    def snapshot(self, request: SnapshotRequest) -> WorkspaceSnapshotRef:
        records: list[tuple[str, bytes]] = []
        total_bytes = 0
        for path in sorted(self._root.rglob("*")):
            relative = path.relative_to(self._root).as_posix()
            if not request.include_hidden and any(
                    part.startswith(".") for part in PurePosixPath(relative).parts):
                continue
            if path.is_symlink():
                if len(records) >= request.max_files:
                    raise RuntimeError("workspace snapshot exceeds max_files")
                target = os.readlink(path).encode("utf-8")
                records.append((f"symlink:{relative}", target))
                continue
            if not path.is_file():
                continue
            if len(records) >= request.max_files:
                raise RuntimeError("workspace snapshot exceeds max_files")
            value = path.read_bytes()
            total_bytes += len(value)
            records.append((f"file:{relative}", value))
        digest = hashlib.sha256()
        for relative, value in records:
            digest.update(relative.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(hashlib.sha256(value).digest())
            digest.update(b"\x00")
        return WorkspaceSnapshotRef(
            workspace=self.reference(),
            digest=digest.hexdigest(),
            file_count=len(records),
            total_bytes=total_bytes,
        )

    def _resolve_relative(self, raw_path: str, *, allow_root: bool) -> Path:
        portable = raw_path.replace("\\", "/")
        parsed = PurePosixPath(portable)
        if parsed.is_absolute() or ".." in parsed.parts:
            raise ValueError("workspace paths must be relative and cannot use '..'")
        if not parsed.parts or portable in ("", "."):
            if allow_root:
                return self._root
            raise ValueError("file path cannot name the workspace root")
        candidate = self._root.joinpath(*parsed.parts)
        resolved = candidate.resolve(strict=False)
        try:
            common = Path(os.path.commonpath((str(self._root), str(resolved))))
        except ValueError as exc:
            raise ValueError("workspace path has a different root") from exc
        if common != self._root:
            raise ValueError("workspace path escapes the configured root")
        return resolved

    def _read(self, request: FileRequest, path: Path) -> FileResult:
        if not path.is_file():
            return _file_error(request, "file_unavailable", "path is not a file")
        size = path.stat().st_size
        if size > self.spec.max_file_bytes:
            return _file_error(
                request, "file_too_large",
                f"file exceeds {self.spec.max_file_bytes} bytes")
        value = path.read_bytes()
        digest = hashlib.sha256(value).hexdigest()
        if request.expected_digest and digest != request.expected_digest:
            return _file_error(
                request, "digest_mismatch",
                "file does not match expected_digest")
        return FileResult(
            ok=True, operation=request.operation, path=request.path,
            content=value, digest=digest, byte_count=len(value))

    def _write(self, request: FileRequest, path: Path) -> FileResult:
        if len(request.content) > self.spec.max_file_bytes:
            return _file_error(
                request, "file_too_large",
                f"content exceeds {self.spec.max_file_bytes} bytes")
        if path.exists():
            if not path.is_file():
                return _file_error(request, "not_a_file", "path is not a file")
            existing_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if request.expected_digest and existing_digest != request.expected_digest:
                return _file_error(
                    request, "digest_mismatch",
                    "existing file does not match expected_digest")
            if not request.replace_existing:
                return _file_error(
                    request, "file_exists",
                    "replace_existing is required to change an existing file")
        elif request.expected_digest:
            return _file_error(
                request, "file_unavailable",
                "expected_digest was supplied but the file does not exist")
        if not path.parent.exists():
            if not request.create_parents:
                return _file_error(
                    request, "parent_unavailable",
                    "create_parents is required for a missing parent directory")
            path.parent.mkdir(parents=True, exist_ok=True)
            path = self._resolve_relative(request.path, allow_root=False)
        _atomic_write(path, request.content)
        return FileResult(
            ok=True, operation=request.operation, path=request.path,
            digest=hashlib.sha256(request.content).hexdigest(),
            byte_count=len(request.content))

    def _list(self, request: FileRequest, path: Path) -> FileResult:
        if not path.is_dir():
            return _file_error(
                request, "directory_unavailable", "path is not a directory")
        return FileResult(
            ok=True, operation=request.operation, path=request.path,
            entries=tuple(sorted(item.name for item in path.iterdir())))

    def _stat(self, request: FileRequest, path: Path) -> FileResult:
        if not path.exists():
            return _file_error(request, "path_unavailable", "path does not exist")
        if path.is_file():
            value = path.read_bytes()
            return FileResult(
                ok=True, operation=request.operation, path=request.path,
                digest=hashlib.sha256(value).hexdigest(), byte_count=len(value))
        return FileResult(
            ok=True, operation=request.operation, path=request.path,
            entries=("directory",))


def _local_test_cases() -> list[dict]:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    with tempfile.TemporaryDirectory() as outer:
        root = Path(outer) / "workspace"
        root.mkdir()
        outside = Path(outer) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        local = RestrictedLocalWorkspace(WorkspaceSpec("local_test", str(root)))
        write = local.file(FileRequest(
            FileOperation.WRITE, "nested/value.txt", content=b"inside",
            create_parents=True))
        read = local.file(FileRequest(FileOperation.READ, "nested/value.txt"))
        check("local_file_requests_stay_inside_the_explicit_root",
              write.ok and read.ok and read.content == b"inside",
              "typed file operations use the configured boundary")

        traversal = local.file(FileRequest(FileOperation.READ, "../outside.txt"))
        absolute = local.file(FileRequest(FileOperation.READ, str(outside)))
        check("relative_traversal_and_absolute_paths_are_refused",
              not traversal.ok and not absolute.ok
              and traversal.error_code == "path_outside_workspace"
              and absolute.error_code == "path_outside_workspace",
              "both lexical escape routes fail before any read")

        link = root / "escape-link"
        link.symlink_to(outside)
        symlink_escape = local.file(FileRequest(FileOperation.READ, "escape-link"))
        outside_directory = Path(outer) / "outside-directory"
        outside_directory.mkdir()
        directory_link = root / "escape-directory"
        directory_link.symlink_to(outside_directory, target_is_directory=True)
        symlink_write = local.file(FileRequest(
            FileOperation.WRITE,
            "escape-directory/new.txt",
            content=b"must not leave workspace",
        ))
        check("symlink_read_and_write_escapes_are_refused",
              not symlink_escape.ok
              and symlink_escape.error_code == "path_outside_workspace"
              and not symlink_write.ok
              and symlink_write.error_code == "path_outside_workspace"
              and not (outside_directory / "new.txt").exists(),
              "resolved read and write targets stay under the physical root")

        changed = local.file(FileRequest(
            FileOperation.WRITE, "nested/value.txt", content=b"changed",
            replace_existing=True, expected_digest="0" * 64))
        check("a_digest_precondition_prevents_an_unsafe_overwrite",
              not changed.ok and changed.error_code == "digest_mismatch"
              and (root / "nested/value.txt").read_bytes() == b"inside",
              "the existing file remains unchanged")

        first = local.snapshot(SnapshotRequest(include_hidden=True))
        second = local.snapshot(SnapshotRequest(include_hidden=True))
        check("unchanged_workspace_snapshots_have_stable_digests",
              first.digest == second.digest
              and first.file_count == second.file_count,
              "snapshot identity uses relative paths and content")

        refused = local.command(CommandRequest(
            ("python3", "-V"), execution_authorized=True))
        check("local_command_execution_is_disabled_by_default",
              not refused.ok and refused.error_code == "execution_disabled",
              "constructing a workspace does not grant command authority")

        enabled = RestrictedLocalWorkspace(WorkspaceSpec(
            "local_command_test",
            str(root),
            execution_enabled=True,
            allowed_commands=(sys.executable,),
        ))
        not_authorized = enabled.command(CommandRequest(
            (sys.executable, "-c", "print('not run')")))
        authorized = enabled.command(CommandRequest(
            (sys.executable, "-c", "print('bounded command')"),
            execution_authorized=True,
        ))
        check("a_local_command_needs_policy_and_request_authority",
              not_authorized.error_code == "execution_not_authorized"
              and authorized.ok and authorized.stdout.strip() == "bounded command",
              "the command starts only after both explicit checks pass")

    return results


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
