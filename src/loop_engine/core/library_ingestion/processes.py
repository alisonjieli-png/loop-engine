"""Bounded external commands, the one place this component starts a process.

A command is an exact argument list, never a shell string. It runs with a
timeout, a ceiling on the bytes it may return and an environment built from
a declared list of names, so a credential held in some other variable never
reaches the process. The GitHub reader uses it for read-only requests
through the existing gh login, and the external validator and scanner
engines use it inside a bubblewrap sandbox that has no network and can
write only to the folders the caller names.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass

#: What gh needs to find its own login in the system keyring. Values are read at
#: use and never written anywhere by this module.
GH_ENVIRONMENT = ("HOME", "PATH", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "DBUS_SESSION_BUS_ADDRESS",
                  "GH_CONFIG_DIR", "GH_HOST", "LANG")
#: A sandboxed tool gets a fixed, credential-free environment.
SYSTEM_PATH = "/usr/bin:/bin"
SANDBOX_ENVIRONMENT = (("HOME", "/tmp"), ("LANG", "C.UTF-8"), ("PYTHONDONTWRITEBYTECODE", "1"),
                       ("NO_COLOR", "1"), ("TERM", "dumb"), ("PATH", SYSTEM_PATH))


class CommandRefused(ValueError):
    """The command was not an exact argument list, or its limits were invalid."""


@dataclass(frozen=True)
class CommandResult:
    exit_code: "int | None"
    stdout: bytes
    stderr_tail: str
    elapsed_ms: float
    timed_out: bool
    truncated: bool


def passthrough_environment(names=GH_ENVIRONMENT) -> dict:
    return {name: os.environ[name] for name in names if name in os.environ}


def launcher_environment() -> dict:
    """What the sandbox launcher itself runs with: the system path and nothing else."""
    return {"PATH": SYSTEM_PATH}


def executable(name: str) -> "str | None":
    return shutil.which(name)


def run_command(argv, *, timeout_seconds: float, maximum_output_bytes: int, environment: dict,
                cwd: "str | None" = None) -> CommandResult:
    """Run one exact argument list and return what it printed, within the declared limits."""
    argv = tuple(argv)
    if not argv or any(type(part) is not str or "\x00" in part for part in argv):
        raise CommandRefused("a command is a nonempty list of exact text arguments")
    if timeout_seconds <= 0 or maximum_output_bytes <= 0:
        raise CommandRefused("a command needs a positive timeout and output ceiling")
    started = time.monotonic()
    try:
        finished = subprocess.run(argv, capture_output=True, timeout=timeout_seconds, check=False,
                                  env=dict(environment), cwd=cwd, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as expired:
        return CommandResult(None, (expired.stdout or b"")[:maximum_output_bytes], "timed out",
                             (time.monotonic() - started) * 1000, True, False)
    except OSError as error:
        return CommandResult(None, b"", type(error).__name__, (time.monotonic() - started) * 1000,
                             False, False)
    truncated = len(finished.stdout) > maximum_output_bytes
    return CommandResult(finished.returncode, finished.stdout[:maximum_output_bytes],
                         finished.stderr.decode("utf-8", "replace")[-400:],
                         (time.monotonic() - started) * 1000, False, truncated)


def sandbox_argv(argv, *, read_only_paths=(), writable_paths=(), bwrap: str = "bwrap") -> tuple:
    """Wrap a command in bubblewrap: read-only system, private temporary folder, no network."""
    wrapped = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
               "--unshare-net", "--unshare-ipc", "--unshare-pid", "--die-with-parent"]
    for path in read_only_paths:
        wrapped += ["--ro-bind", str(path), str(path)]
    for path in writable_paths:
        wrapped += ["--bind", str(path), str(path)]
    wrapped.append("--clearenv")
    for name, value in SANDBOX_ENVIRONMENT:
        wrapped += ["--setenv", name, value]
    return (*wrapped, "--", *argv)
