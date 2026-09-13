"""Docker lifetime controls, separated from the opt-in real-container probe.

The folded checks inject a local Docker protocol fixture. Explicit opt-in
qualification launches a real bounded container and checks late-write denial.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class _DockerFixture:
    """Local protocol fixture. It never invokes Docker or claims containment."""

    def __init__(self, cleanup="ok", timeout=True):
        self.cleanup, self.timeout = cleanup, timeout
        self.calls, self.names = [], []
        self.name, self.owner = "", ""
        self.container_id = "a" * 64
        self.removed = False

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[1] == "run":
            self.name = argv[argv.index("--name") + 1]
            self.owner = argv[argv.index("--label") + 1].split("=", 1)[1]
            self.names.append(self.name)
            self.removed = False
            if self.timeout:
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return SimpleNamespace(returncode=0, stdout="completed\n", stderr="")
        if argv[2] == "rm":
            if self.cleanup != "survives":
                self.removed = True
            if self.cleanup == "remove_timeout":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return SimpleNamespace(returncode=0, stdout=self.container_id, stderr="")
        if self.cleanup == "inspection_failure":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if self.cleanup == "wrong_missing_ref":
            return SimpleNamespace(returncode=1, stdout="",
                                   stderr="Error: No such container: " + argv[-1] + "-another")
        if self.cleanup == "missing" or self.removed:
            return SimpleNamespace(returncode=1, stdout="",
                                   stderr="Error: No such container: " + argv[-1])
        body = {"id": self.container_id, "name": "/" + self.name,
                "owner": "unrelated-owner" if self.cleanup == "foreign" else self.owner}
        if self.cleanup == "invalid_id":
            body["id"] = "not-a-container-id"
        return SimpleNamespace(returncode=0,
                               stdout="invalid-json" if self.cleanup == "malformed" else json.dumps(body),
                               stderr="")


def run_checks() -> list[dict]:
    """Offline enforcement, consumed by workspace_backends.self_test."""
    from .workspace_contracts import CommandRequest, FileOperation, FileRequest, WorkspaceSpec
    from .workspace_optional import DockerWorkspace, DockerWorkspaceDeclaration

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "local Docker protocol fixture; no real container"})

    with tempfile.TemporaryDirectory(prefix="docker-cleanup-contract-") as directory:
        def workspace():
            return DockerWorkspace(WorkspaceSpec("lifetime", directory, backend_kind="docker",
                execution_enabled=True, allowed_commands=("python3",)),
                DockerWorkspaceDeclaration("python@sha256:" + "0" * 64))

        request = CommandRequest(("python3", "-V"), execution_authorized=True, timeout_seconds=1)
        with patch("loop_engine.core.workspace_optional.shutil.which", return_value=None), \
                patch("loop_engine.core.workspace_optional.subprocess.run") as invoked:
            missing = workspace().command(request)
        check("missing_docker_does_not_start_or_clean_any_container",
              missing.error_code == "dependency_unavailable" and not invoked.called)

        with patch("loop_engine.core.workspace_optional.shutil.which", return_value="/fixture/docker"):
            success = _DockerFixture(timeout=False)
            with patch("loop_engine.core.workspace_optional.subprocess.run", side_effect=success):
                first = workspace().command(request)
                second = workspace().command(request)
            check("successful_docker_commands_have_unique_owned_names",
                  first.ok and second.ok and first.stdout == "completed\n"
                  and len(set(success.names)) == 2
                  and all(name.startswith("loop-engine-command-") for name in success.names))

            stopped = _DockerFixture()
            with patch("loop_engine.core.workspace_optional.subprocess.run", side_effect=stopped):
                result = workspace().command(request)
            removed = [argv for argv in stopped.calls if argv[1:3] == ["container", "rm"]]
            check("timeout_removes_only_the_verified_full_container_id_then_confirms_absence",
                  result.error_code == "command_timeout"
                  and removed == [["docker", "container", "rm", "--force", "a" * 64]]
                  and stopped.calls[-1][-1] == "a" * 64 and "inspect" in stopped.calls[-1])

            for mode in ("missing", "remove_timeout"):
                fixture = _DockerFixture(cleanup=mode)
                with patch("loop_engine.core.workspace_optional.subprocess.run", side_effect=fixture):
                    result = workspace().command(request)
                check("timeout_is_known_after_confirmed_absence_" + mode,
                      result.error_code == "command_timeout"
                      and (mode != "missing" or not any("rm" in argv for argv in fixture.calls)))

            for mode in ("foreign", "malformed", "survives", "wrong_missing_ref", "invalid_id"):
                fixture = _DockerFixture(cleanup=mode)
                with patch("loop_engine.core.workspace_optional.subprocess.run", side_effect=fixture):
                    result = workspace().command(request)
                check("unconfirmed_cleanup_refuses_" + mode,
                      result.error_code == "docker_cleanup_unknown"
                      and (mode == "survives" or not any("rm" in argv for argv in fixture.calls)))

            fixture = _DockerFixture(cleanup="inspection_failure")
            active = workspace()
            with patch("loop_engine.core.workspace_optional.subprocess.run", side_effect=fixture):
                first = active.command(request)
                second = active.command(request)
                write = active.file(FileRequest(FileOperation.WRITE, "blocked.txt", content=b"unsafe next effect"))
                denied = active.command(CommandRequest(("python3", "-V")))
                check("cleanup_unknown_fences_following_commands_and_file_writes",
                      first.error_code == second.error_code == write.error_code == "docker_cleanup_unknown"
                      and denied.error_code == "execution_not_authorized"
                      and len(fixture.names) == 1 and not (Path(directory) / "blocked.txt").exists())
                fixture.cleanup, fixture.timeout = "ok", False
                recovered = active.command(request)
            check("known_cleanup_reconciliation_allows_a_new_authorized_command",
                  recovered.ok and len(fixture.names) == 2)
    return tests


def qualify_timeout(image: str, output_root: str) -> dict:
    """Explicit real Docker check: sleep three seconds, timeout after one."""
    from .workspace_contracts import CommandRequest, WorkspaceSpec
    from .workspace_optional import DockerWorkspace, DockerWorkspaceDeclaration

    root = Path(output_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or any(root.iterdir()):
        raise ValueError("qualification needs an existing empty absolute output directory")
    active = DockerWorkspace(WorkspaceSpec("docker_timeout_qualification", str(root), backend_kind="docker",
        execution_enabled=True, allowed_commands=("python3",), network_access=False),
        DockerWorkspaceDeclaration(image))
    success = active.command(CommandRequest(("python3", "-c", "print('container started')"),
        execution_authorized=True, timeout_seconds=30))
    started = time.monotonic()
    timed = active.command(CommandRequest(("python3", "-c",
        "from pathlib import Path; import time; Path('started.txt').write_text('started'); "
        "time.sleep(3); Path('late.txt').write_text('must not appear')"),
        execution_authorized=True, timeout_seconds=1))
    elapsed = time.monotonic() - started
    time.sleep(3.2)
    tests = [
        {"test": "real_pinned_container_command_succeeds", "passed": success.ok and success.stdout.strip() == "container started"},
        {"test": "timed_container_actually_entered_the_workload", "passed": (root / "started.txt").is_file()},
        {"test": "timeout_requires_confirmed_container_termination", "passed": timed.error_code == "command_timeout"},
        {"test": "late_write_does_not_occur_after_timeout", "passed": not (root / "late.txt").exists()},
    ]
    result = {"record_type": "docker_timeout_qualification/v1", "image": image,
        "model_calls": 0, "network_policy": "none", "execution_timeout_seconds": 1,
        "delayed_write_seconds": 3, "post_return_observation_seconds": 3.2,
        "elapsed_until_timeout_result": elapsed, "command_result": timed.to_dict(),
        "tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
        "all_passed": all(item["passed"] for item in tests)}
    (root / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
