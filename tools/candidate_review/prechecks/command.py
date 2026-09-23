"""A declared external program that a pre-check engine runs: exact arguments, a timeout, no shell.

The program, its arguments and its version arguments come from the panel's
declared settings. Arguments are a list, never a shell string, and a token is
substituted only when it is exactly one of the engine's named placeholders, so
no value can add an argument or run a second command. A missing program makes
the engine unavailable; it is never treated as a pass.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from ..records import positive_number, read_part, refuse, text_field

OUTPUT_LIMIT = 4000
VERSION_TIMEOUT_SECONDS = 30.0


class DeclaredProgram:
    """One program, its argument list with named placeholders, and its version arguments."""

    def __init__(self, settings: dict, engine_id: str, placeholders: tuple, extra_fields: tuple = ()) -> None:
        part = read_part(settings, engine_id, ("program", "arguments", "version_arguments", "timeout_seconds")
                         + tuple(extra_fields))
        self.program = text_field(part["program"], "program", limit=1000)
        self.arguments = _arguments(part["arguments"], placeholders, engine_id)
        self.version_arguments = _arguments(part["version_arguments"], (), engine_id)
        self.timeout_seconds = positive_number(part["timeout_seconds"], "timeout_seconds")
        self.settings = part

    def resolved(self) -> "str | None":
        if os.sep in self.program:
            path = Path(self.program)
            return str(path) if path.is_file() and os.access(path, os.X_OK) else None
        return shutil.which(self.program)

    def version(self) -> tuple:
        """(available, reason, version text) from the declared version arguments. Never a model call."""
        executable = self.resolved()
        if executable is None:
            return False, f"the program {self.program!r} is not installed on this machine", ""
        try:
            finished = subprocess.run([executable, *self.version_arguments], capture_output=True, text=True,
                                      timeout=VERSION_TIMEOUT_SECONDS, check=False, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as error:
            return False, f"the version of {self.program!r} could not be read: {type(error).__name__}", ""
        text = (finished.stdout or finished.stderr).strip().splitlines()
        if finished.returncode != 0 or not text:
            return False, f"the version of {self.program!r} could not be read", ""
        return True, "", text[0][:200]

    def run(self, substitutions: dict, cwd: Path) -> subprocess.CompletedProcess:
        executable = self.resolved()
        if executable is None:
            refuse("engine_unavailable", f"the program {self.program!r} is not installed on this machine")
        argv = [executable] + [substitutions.get(argument, argument) for argument in self.arguments]
        return subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout_seconds, check=False,
                              cwd=str(cwd), stdin=subprocess.DEVNULL)


def _arguments(value, placeholders: tuple, engine_id: str) -> tuple:
    if type(value) is not list or any(type(item) is not str for item in value):
        refuse("invalid_precheck_settings", f"the arguments of {engine_id} are a list of text values")
    for item in value:
        if ("{" in item or "}" in item) and item not in placeholders:
            refuse("invalid_precheck_settings", f"{engine_id} names an unknown placeholder in {item!r}")
    return tuple(value)


def bounded(text: str) -> str:
    return " ".join(str(text).split())[:OUTPUT_LIMIT]
