"""Enforce a step's read-only intent against the workspace, not the prompt.

A composed step can deny the edit, write and patch tools and still be able
to modify files, because bash is a write path: ``sed -i``, a redirect,
``git checkout``, ``patch(1)``, an install that rewrites a lockfile. This
was not theoretical. The observation step shipped with edit denied, bash
allowed, and a system prompt asserting "you cannot edit or write files".
Told to use sed, the model ran

    sed -i 's/return 1/return 2/' victim.py

and the file changed. The denial held for steps with bash off and bought
nothing for steps with bash on, while the prompt claimed otherwise.

Two repairs, in order of strength:

``engine_observed_output`` removes the reason to hold a shell. The engine
already knows the command that failed -- it is the gate -- so it runs the
command itself and hands the step the real output. A step that does not
need bash can be composed without it, and the tool layer, which has been
observed to hold, does the enforcing.

``WorkspaceGuard`` is the backstop for steps that genuinely must run
commands. It hashes the tracked files before and after, and reports exactly
what changed. A guard that only warns would be theatre, so ``restore`` puts
the bytes back. Detection is engine-side and does not ask the model whether
it behaved.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

#: Directories whose contents are build output rather than anyone's work.
#: A guard that trips on __pycache__ appearing would fire on every step
#: that ran a Python command, which is the failure mode that made an
#: earlier dirty-tree check disable the whole overnight run.
IGNORED_DIRECTORY_NAMES = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", "node_modules", ".venv", "venv", ".tox", "dist", "build",
    ".next", ".turbo", ".opencode",
})


class WorkspaceGuardError(RuntimeError):
    """A guarded step changed files it was composed not to change."""


def _relevant_files(root: Path) -> dict:
    files = {}
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRECTORY_NAMES for part in path.parts):
            continue
        if path.is_file() and not path.is_symlink():
            try:
                files[str(path.relative_to(root))] = path.read_bytes()
            except OSError:
                continue
    return files


@dataclass
class WorkspaceGuard:
    """Snapshot a workspace, then say exactly what a step did to it."""

    root: Path
    _before: dict = field(default_factory=dict, repr=False)

    def snapshot(self) -> "WorkspaceGuard":
        self._before = _relevant_files(Path(self.root))
        return self

    def changes(self) -> dict:
        """Return {"modified": [...], "created": [...], "deleted": [...]}."""
        after = _relevant_files(Path(self.root))
        before = self._before
        modified = sorted(name for name in before.keys() & after.keys()
                          if before[name] != after[name])
        return {"modified": modified,
                "created": sorted(after.keys() - before.keys()),
                "deleted": sorted(before.keys() - after.keys())}

    def clean(self) -> bool:
        return not any(self.changes().values())

    def restore(self) -> dict:
        """Put the bytes back. A guard that only warned would be theatre."""
        changed = self.changes()
        root = Path(self.root)
        for name in changed["modified"] + changed["deleted"]:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self._before[name])
        for name in changed["created"]:
            try:
                (root / name).unlink()
            except OSError:
                pass
        return changed

    def enforce(self) -> None:
        """Restore and raise if a read-only step wrote anything."""
        changed = self.changes()
        if any(changed.values()):
            self.restore()
            raise WorkspaceGuardError(
                "a step composed as read-only modified the workspace and was "
                f"rolled back: {changed}. bash is a write path even when the "
                "edit, write and patch tools are absent.")


def engine_observed_output(command: str, workspace, *, timeout: float = 180.0
                           ) -> dict:
    """Run the failing command HERE and return its real result.

    The point is to make bash unnecessary for the step that reads this. The
    engine knows the command, so nothing is gained by handing a shell to a
    model whose job is to interpret output rather than produce it.
    """
    if not str(command).strip():
        raise WorkspaceGuardError("an observation needs a command to run")
    try:
        done = subprocess.run(command, shell=True, cwd=str(workspace),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"command": command, "exit_code": None, "timed_out": True,
                "output": f"no result after {timeout:.0f}s; a hang is an "
                          "observation, not a missing one"}
    output = (done.stdout + done.stderr).strip()
    return {"command": command, "exit_code": done.returncode,
            "timed_out": False, "output": output[-4000:],
            "digest": hashlib.sha256(output.encode("utf-8")).hexdigest()}


def self_test() -> dict:
    """Prove detection, restoration and engine-side observation."""
    import tempfile

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "keep.py").write_text("x = 1\n", encoding="utf-8")
        (root / "gone.py").write_text("y = 2\n", encoding="utf-8")
        guard = WorkspaceGuard(root=root).snapshot()
        check("an_untouched_workspace_is_clean", guard.clean())

        # Exactly the bypass observed live: bash writing through sed.
        subprocess.run(["sed", "-i", "s/x = 1/x = 99/", str(root / "keep.py")],
                       check=True)
        (root / "new.py").write_text("z = 3\n", encoding="utf-8")
        (root / "gone.py").unlink()
        changed = guard.changes()
        check("a_sed_write_is_detected",
              changed["modified"] == ["keep.py"], str(changed["modified"]))
        check("creations_and_deletions_are_detected",
              changed["created"] == ["new.py"]
              and changed["deleted"] == ["gone.py"], str(changed))

        guard.restore()
        check("restore_puts_every_byte_back",
              (root / "keep.py").read_text() == "x = 1\n"
              and (root / "gone.py").read_text() == "y = 2\n"
              and not (root / "new.py").exists())
        check("the_workspace_is_clean_again", guard.clean())

        # Build output must not trip the guard: an earlier dirty-tree check
        # that counted __pycache__ disabled the whole overnight run.
        cache = root / "__pycache__"
        cache.mkdir()
        (cache / "keep.cpython-311.pyc").write_bytes(b"\x00compiled")
        check("build_output_does_not_trip_the_guard", guard.clean(),
              "a guard the system trips by doing its own job stops the system")

        guard2 = WorkspaceGuard(root=root).snapshot()
        (root / "keep.py").write_text("x = 100\n", encoding="utf-8")
        try:
            guard2.enforce()
            check("enforce_raises_and_rolls_back", False, "did not raise")
        except WorkspaceGuardError as exc:
            check("enforce_raises_and_rolls_back",
                  (root / "keep.py").read_text() == "x = 1\n"
                  and "write path" in str(exc), str(exc)[:110])

        observed = engine_observed_output(
            "printf 'boom\\n'; exit 3", root, timeout=30.0)
        check("engine_runs_the_command_and_reports_the_real_exit",
              observed["exit_code"] == 3 and "boom" in observed["output"],
              f"exit={observed['exit_code']}")
        check("engine_observation_carries_a_digest_of_what_it_saw",
              len(observed["digest"]) == 64)

        timed = engine_observed_output("sleep 5", root, timeout=0.4)
        check("a_hang_is_reported_as_an_observation",
              timed["timed_out"] and timed["exit_code"] is None,
              timed["output"][:80])

        try:
            engine_observed_output("   ", root)
            check("an_empty_command_is_refused", False)
        except WorkspaceGuardError as exc:
            check("an_empty_command_is_refused",
                  "needs a command" in str(exc), str(exc)[:80])

    return {"module": "core.opencode_step_guard", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
