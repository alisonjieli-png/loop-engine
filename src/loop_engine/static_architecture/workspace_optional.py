"""Explicit Docker and inert remote workspace adapters.

Docker execution requires policy authority and request authority. E2B and
Modal remain typed declarations until an executor is registered. Importing
this module does not probe a daemon, load an SDK, or contact a service.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
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


@dataclass(frozen=True)
class DockerResourceLimits:
    """Resource ceilings applied to every Docker workspace command."""

    memory: str = "2g"
    cpus: float = 2.0
    pids: int = 256
    temporary_bytes: int = 256 * 1024 * 1024

    def __post_init__(self):
        if not self.memory or self.cpus <= 0 or self.pids < 1:
            raise ValueError("Docker resource limits must be positive")
        if self.temporary_bytes < 1024 * 1024:
            raise ValueError("Docker temporary storage must be at least 1 MiB")


@dataclass(frozen=True)
class DockerWorkspaceDeclaration:
    """Configuration only. Construction and availability checks run nothing."""

    image: str
    container_root: str = "/workspace"
    docker_binary: str = "docker"
    limits: DockerResourceLimits = DockerResourceLimits()
    require_image_digest: bool = True

    def __post_init__(self):
        if not self.image:
            raise ValueError("Docker workspace needs an image")
        if not self.container_root.startswith("/"):
            raise ValueError("Docker container_root must be absolute")
        if not self.docker_binary:
            raise ValueError("Docker workspace needs a binary name")
        if self.require_image_digest:
            marker = "@sha256:"
            digest = self.image.rsplit(marker, 1)[-1] if marker in self.image else ""
            if (len(digest) != 64 or any(
                    character not in "0123456789abcdef" for character in digest)):
                raise ValueError(
                    "Docker image must use an immutable sha256 digest")


class DockerWorkspace:
    """Explicit Docker command adapter with two execution checks."""

    def __init__(self, spec: WorkspaceSpec,
                 declaration: DockerWorkspaceDeclaration):
        if spec.backend_kind != "docker":
            raise ValueError("Docker workspace needs backend_kind=docker")
        self.spec = spec
        self.declaration = declaration
        self._host_root = Path(spec.root).expanduser().resolve(strict=False)
        from .workspace_local import RestrictedLocalWorkspace
        self._files = RestrictedLocalWorkspace(WorkspaceSpec(
            workspace_id=spec.workspace_id,
            root=str(self._host_root),
            backend_kind="restricted_local",
            max_file_bytes=spec.max_file_bytes,
        ))

    def reference(self) -> WorkspaceRef:
        return WorkspaceRef(
            self.spec.workspace_id, self.spec.backend_kind, str(self._host_root))

    def availability(self) -> BackendAvailability:
        binary = shutil.which(self.declaration.docker_binary)
        if binary is None:
            return BackendAvailability(
                False, "docker", "dependency_unavailable",
                "Docker command was not found; no process was started")
        if not self._host_root.is_dir():
            return BackendAvailability(
                False, "docker", "workspace_root_unavailable",
                "host workspace root is not an existing directory",
                dependency_detected=True)
        return BackendAvailability(
            True, "docker", "binary_detected",
            "Docker command exists; daemon and image were not contacted",
            dependency_detected=True,
            runtime_verified=False,
        )

    def file(self, request: FileRequest) -> FileResult:
        # The host directory is the exact directory mounted into the
        # container. File preparation and collection use the same confined
        # path checks as the local backend and do not need to start a process.
        return self._files.file(request)

    def command(self, request: CommandRequest) -> CommandResult:
        availability = self.availability()
        if not availability.available:
            return _command_error(
                request, availability.reason_code, availability.detail)
        if not self.spec.execution_enabled:
            return _command_error(
                request, "execution_disabled",
                "Docker execution is disabled in WorkspaceSpec")
        if not request.execution_authorized:
            return _command_error(
                request, "execution_not_authorized",
                "Docker request lacks explicit execution authority")
        executable = request.argv[0]
        if executable not in self.spec.allowed_commands:
            return _command_error(
                request, "command_not_allowed",
                f"executable {executable!r} is not in the workspace allowlist")
        try:
            container_cwd = _container_cwd(
                self.declaration.container_root, request.cwd)
        except ValueError as exc:
            return _command_error(request, "path_outside_workspace", str(exc))
        docker_argv = [
            self.declaration.docker_binary, "run", "--rm", "--pull", "never",
            "--read-only", "--cap-drop", "ALL", "--security-opt",
            "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
            "--pids-limit",
            str(self.declaration.limits.pids), "--memory",
            self.declaration.limits.memory, "--cpus",
            str(self.declaration.limits.cpus), "--tmpfs",
            "/tmp:rw,noexec,nosuid,size="
            f"{self.declaration.limits.temporary_bytes}", "--network",
            "bridge" if self.spec.network_access else "none", "--workdir",
            container_cwd, "--volume",
            f"{self._host_root}:{self.declaration.container_root}:rw",
        ]
        for key in request.environment_keys:
            docker_argv.extend(("--env", key))
        docker_argv.extend((self.declaration.image, *request.argv))
        docker_environment = {
            "PATH": os.environ.get("PATH", os.defpath),
        }
        for key in request.environment_keys:
            if key in os.environ:
                docker_environment[key] = os.environ[key]
        try:
            process = subprocess.run(
                docker_argv,
                env=docker_environment,
                input=request.stdin_text,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return _command_error(
                request, "command_timeout",
                f"Docker command exceeded {request.timeout_seconds} seconds")
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
            error="" if process.returncode == 0 else "Docker command returned nonzero",
            output_truncated=stdout_cut or stderr_cut,
        )

    def snapshot(self, request: SnapshotRequest) -> WorkspaceSnapshotRef:
        local = self._files.snapshot(request)
        return WorkspaceSnapshotRef(
            workspace=self.reference(),
            digest=local.digest,
            file_count=local.file_count,
            total_bytes=local.total_bytes,
            algorithm=local.algorithm,
        )


def verify_live_docker_workspace(
        image: str, *, docker_binary: str = "docker") -> dict:
    """Exercise the real Docker backend with one immutable local image.

    This function contacts the local Docker daemon and starts one confined
    container. It never pulls an image because the adapter always passes
    ``--pull never``.
    """
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="loop_engine_docker_") as root:
        spec = WorkspaceSpec(
            "docker_live_test", root, backend_kind="docker",
            execution_enabled=True, allowed_commands=("python3",),
            network_access=False)
        workspace = DockerWorkspace(
            spec, DockerWorkspaceDeclaration(
                image=image, docker_binary=docker_binary))
        prepared = workspace.file(FileRequest(
            operation=FileOperation.WRITE,
            path="input.txt", content=b"inside docker workspace"))
        before = workspace.snapshot(SnapshotRequest(include_hidden=True))
        command = workspace.command(CommandRequest(
            ("python3", "-c",
             "from pathlib import Path; print(Path('input.txt').read_text())"),
            execution_authorized=True,
            timeout_seconds=30.0,
            max_output_bytes=4096))
        after = workspace.snapshot(SnapshotRequest(include_hidden=True))
        check("typed_files_prepare_the_exact_mounted_workspace",
              prepared.ok and before.file_count == 1
              and before.workspace.backend_kind == "docker",
              "file preparation used the confined workspace contract")
        check("real_container_reads_the_prepared_file_without_network",
              command.ok
              and command.stdout.strip() == "inside docker workspace",
              command.error or command.stderr)
        check("read_only_command_keeps_the_workspace_snapshot_stable",
              before.digest == after.digest,
              "the command did not change the mounted workspace")
        check("runtime_used_an_immutable_image_and_no_pull",
              "@sha256:" in image,
              image)
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "docker_workspace_live_verification/v1",
        "image": image,
        "network_access": False,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


@dataclass(frozen=True)
class E2BWorkspaceDeclaration:
    """Optional E2B configuration without an SDK dependency."""

    template: str = "base"
    api_key_ref: str = "env:E2B_API_KEY"
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not self.template or not self.api_key_ref:
            raise ValueError("E2B declaration needs template and api_key_ref")
        _validate_metadata(self.metadata)


@dataclass(frozen=True)
class ModalWorkspaceDeclaration:
    """Optional Modal configuration without an SDK dependency."""

    image: str = "debian-slim"
    token_id_ref: str = "env:MODAL_TOKEN_ID"
    token_secret_ref: str = "env:MODAL_TOKEN_SECRET"
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not self.image or not self.token_id_ref or not self.token_secret_ref:
            raise ValueError("Modal declaration needs image and token references")
        _validate_metadata(self.metadata)


class DeclaredRemoteWorkspace:
    """A non-executing placeholder until a remote SDK adapter is registered."""

    def __init__(self, spec: WorkspaceSpec, declaration: object):
        if spec.backend_kind not in ("e2b", "modal"):
            raise ValueError("remote declaration supports e2b or modal")
        expected = (E2BWorkspaceDeclaration if spec.backend_kind == "e2b"
                    else ModalWorkspaceDeclaration)
        if not isinstance(declaration, expected):
            raise TypeError(
                f"{spec.backend_kind} workspace needs {expected.__name__}")
        self.spec = spec
        self.declaration = declaration

    def reference(self) -> WorkspaceRef:
        return WorkspaceRef(
            self.spec.workspace_id, self.spec.backend_kind, self.spec.root)

    def availability(self) -> BackendAvailability:
        return BackendAvailability(
            False,
            self.spec.backend_kind,
            "adapter_not_registered",
            "optional SDK declaration is valid but no executor is registered",
            dependency_detected=False,
            runtime_verified=False,
        )

    def file(self, request: FileRequest) -> FileResult:
        return _file_error(
            request, "adapter_not_registered",
            f"{self.spec.backend_kind} executor is not registered")

    def command(self, request: CommandRequest) -> CommandResult:
        return _command_error(
            request, "adapter_not_registered",
            f"{self.spec.backend_kind} executor is not registered")

    def snapshot(self, request: SnapshotRequest) -> WorkspaceSnapshotRef:
        raise RuntimeError(f"{self.spec.backend_kind} executor is not registered")


def _container_cwd(container_root: str, requested: str) -> str:
    portable = requested.replace("\\", "/")
    parsed = PurePosixPath(portable)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError("container cwd must be relative and cannot use '..'")
    if portable in ("", "."):
        return container_root
    return str(PurePosixPath(container_root).joinpath(*parsed.parts))


def _validate_metadata(metadata: tuple[tuple[str, str], ...]) -> None:
    keys = [key for key, _value in metadata]
    if len(keys) != len(set(keys)) or any(not key for key in keys):
        raise ValueError("workspace metadata keys must be unique and nonempty")


def _optional_test_cases() -> list[dict]:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    mutable_tag_failed = False
    try:
        DockerWorkspaceDeclaration(image="python:latest")
    except ValueError:
        mutable_tag_failed = True
    check("docker_images_are_immutable_by_default",
          mutable_tag_failed,
          "an image tag cannot drift between two benchmark runs")

    with tempfile.TemporaryDirectory() as root:
        docker = DockerWorkspace(
            WorkspaceSpec(
                "docker_test", root, backend_kind="docker",
                execution_enabled=True, allowed_commands=("python3",)),
            DockerWorkspaceDeclaration(
                image="python@sha256:" + "0" * 64,
                docker_binary="loop-engine-test-docker-does-not-exist"),
        )
        state = docker.availability()
        result = docker.command(CommandRequest(
            ("python3", "-V"), execution_authorized=True))
        check("missing_docker_is_reported_without_starting_a_process",
              not state.available and state.reason_code == "dependency_unavailable"
              and result.error_code == "dependency_unavailable",
              "availability is a binary lookup, not a daemon or image call")

    e2b = DeclaredRemoteWorkspace(
        WorkspaceSpec("e2b_test", "/workspace", backend_kind="e2b"),
        E2BWorkspaceDeclaration())
    modal = DeclaredRemoteWorkspace(
        WorkspaceSpec("modal_test", "/workspace", backend_kind="modal"),
        ModalWorkspaceDeclaration())
    check("optional_remote_declarations_remain_inert",
          not e2b.availability().available and not modal.availability().available
          and e2b.availability().reason_code == "adapter_not_registered"
          and modal.availability().reason_code == "adapter_not_registered",
          "E2B and Modal need no import, credential, or network call")
    return results
