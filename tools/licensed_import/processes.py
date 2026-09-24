"""Bounded external commands: the one place the licensed import starts a process.

A command is an exact argument list, never a shell string. It runs with a
timeout, a ceiling on the bytes it may return, optional bytes on standard
input and an environment built from declared names, so no credential held
in another variable reaches it. It reuses the result shape of the library
ingestion component's runner and adds standard input, which git needs to
read many objects in one process.

Git runs with no system or user configuration, no terminal prompt, no
hooks and only the HTTPS protocol, so a user's credential helper, URL
rewrite or hook can never change what a fetch does. gh keeps its own login
in the system keyring; the token never passes through this module.
"""
from __future__ import annotations

import os
import subprocess
import time

from loop_engine.core.library_ingestion.processes import (
    GH_ENVIRONMENT, CommandRefused, CommandResult, passthrough_environment)

#: The only protocols a fetch may use, and settings that keep git from running anything.
GIT_SAFETY = ("-c", "protocol.allow=never", "-c", "protocol.https.allow=always", "-c", "core.hooksPath=/dev/null",
              "-c", "core.symlinks=false", "-c", "core.fsmonitor=false", "-c", "submodule.recurse=false",
              "-c", "fetch.recurseSubmodules=false", "-c", "credential.helper=", "-c", "gc.auto=0",
              "-c", "maintenance.auto=false")


def gh_environment() -> dict:
    """What gh needs to find its own login, and nothing else."""
    return passthrough_environment(GH_ENVIRONMENT)


def git_environment(home: str) -> dict:
    """A credential-free environment: no system or user git configuration, no prompt, no lazy fetch.

    GIT_NO_LAZY_FETCH makes a read of a missing object fail instead of fetching
    it silently, so every network read of the git engine is one it asked for.
    """
    return {**passthrough_environment(("PATH",)), "HOME": str(home), "LANG": "C.UTF-8",
            "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ASKPASS": "/bin/false", "SSH_ASKPASS": "/bin/false", "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_NO_LAZY_FETCH": "1"}


def run(argv, *, timeout_seconds: float, maximum_output_bytes: int, environment: dict,
        cwd: "str | None" = None, input_bytes: "bytes | None" = None) -> CommandResult:
    """Run one exact argument list, optionally feeding bytes on standard input, within its limits."""
    argv = tuple(argv)
    if not argv or any(type(part) is not str or "\x00" in part for part in argv):
        raise CommandRefused("a command is a nonempty list of exact text arguments")
    if timeout_seconds <= 0 or maximum_output_bytes <= 0:
        raise CommandRefused("a command needs a positive timeout and output ceiling")
    if input_bytes is not None and type(input_bytes) is not bytes:
        raise CommandRefused("standard input is exact bytes")
    started = time.monotonic()
    try:
        finished = subprocess.run(argv, capture_output=True, timeout=timeout_seconds, check=False,
                                  env=dict(environment), cwd=cwd,
                                  input=input_bytes if input_bytes is not None else b"")
    except subprocess.TimeoutExpired as expired:
        return CommandResult(None, (expired.stdout or b"")[:maximum_output_bytes], "timed out",
                             (time.monotonic() - started) * 1000, True, False)
    except OSError as error:
        return CommandResult(None, b"", type(error).__name__, (time.monotonic() - started) * 1000, False, False)
    truncated = len(finished.stdout) > maximum_output_bytes
    return CommandResult(finished.returncode, finished.stdout[:maximum_output_bytes],
                         finished.stderr.decode("utf-8", "replace")[-400:],
                         (time.monotonic() - started) * 1000, False, truncated)
