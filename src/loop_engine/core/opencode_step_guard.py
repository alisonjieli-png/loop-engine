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

The rollback itself never follows a symlink. A step that swaps a tracked
file, or a directory above it, for a link pointing outside the workspace
is reported as its own change class (``replaced_by_symlink``), and restore
unlinks the link, rebuilds real directories, opens the file O_NOFOLLOW and
checks the final path against the resolved root before writing a byte.
"""

from __future__ import annotations

import hashlib
import os
import shutil
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


def _relevant_links(root: Path) -> dict:
    """Symlinks under root (to files or directories) -> what they point at."""
    links = {}
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRECTORY_NAMES for part in path.parts):
            continue
        if path.is_symlink():
            try:
                links[str(path.relative_to(root))] = os.readlink(path)
            except OSError:
                continue
    return links


def _symlink_in_path(root: Path, name: str) -> bool:
    """True if the name, or any directory on the way to it, is now a symlink."""
    current = Path(root)
    for part in Path(name).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _write_without_following(root: Path, name: str, data: bytes) -> None:
    """Put bytes back at root/name without ever following a symlink.

    A step that swapped a tracked file, or a directory above it, for a
    symlink pointing outside the workspace must not turn the rollback into
    a write to wherever the link points. Every symlink on the path is
    unlinked (the link, never its target), directories are recreated as
    real directories, the file is opened O_NOFOLLOW, and the final path is
    checked against the resolved root before a byte is written.
    """
    real_root = os.path.realpath(root)
    current = Path(root)
    parts = Path(name).parts
    for part in parts[:-1]:
        current = current / part
        if os.path.islink(current) or (
                os.path.lexists(current) and not os.path.isdir(current)):
            os.unlink(current)
        if not os.path.lexists(current):
            os.mkdir(current)
    target = current / parts[-1]
    if os.path.islink(target):
        os.unlink(target)
    elif os.path.isdir(target):
        shutil.rmtree(target)
    resolved = os.path.realpath(target)
    if resolved == real_root or os.path.commonpath(
            (real_root, resolved)) != real_root:
        raise WorkspaceGuardError(
            f"refusing to restore {name!r}: it resolves to {resolved}, "
            f"outside the workspace {real_root}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(str(target), flags, 0o644)
    with os.fdopen(handle, "wb") as stream:
        stream.write(data)


@dataclass
class WorkspaceGuard:
    """Snapshot a workspace, then say exactly what a step did to it."""

    root: Path
    _before: dict = field(default_factory=dict, repr=False)
    _before_links: dict = field(default_factory=dict, repr=False)

    def snapshot(self) -> "WorkspaceGuard":
        self._before = _relevant_files(Path(self.root))
        self._before_links = _relevant_links(Path(self.root))
        return self

    def changes(self) -> dict:
        """Return what a step did, by class.

        ``modified``, ``created`` and ``deleted`` are what they say.
        ``replaced_by_symlink`` is a tracked file whose name, or a directory
        above it, is now a symlink: its own class, because a rollback that
        read it as "deleted" would write the original bytes through the
        link. ``symlinks_created`` are new links at untracked names.
        """
        root = Path(self.root)
        after = _relevant_files(root)
        links = _relevant_links(root)
        before = self._before
        missing = before.keys() - after.keys()
        replaced = sorted(name for name in missing
                          if _symlink_in_path(root, name))
        modified = sorted(name for name in before.keys() & after.keys()
                          if before[name] != after[name])
        return {"modified": modified,
                "created": sorted(after.keys() - before.keys()),
                "deleted": sorted(missing - set(replaced)),
                "replaced_by_symlink": replaced,
                "symlinks_created": sorted(
                    name for name in links.keys() - self._before_links.keys()
                    if name not in before)}

    def clean(self) -> bool:
        return not any(self.changes().values())

    def restore(self) -> dict:
        """Put the bytes back. A guard that only warned would be theatre.

        Nothing here follows a symlink: links a step created are unlinked
        (the link, never what it points at) and tracked files come back
        through ``_write_without_following``, so a rollback cannot be turned
        into a write outside the workspace.
        """
        changed = self.changes()
        root = Path(self.root)
        for name in changed["symlinks_created"]:
            try:
                os.unlink(root / name)
            except OSError:
                pass
        for name in (changed["replaced_by_symlink"] + changed["modified"]
                     + changed["deleted"]):
            _write_without_following(root, name, self._before[name])
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

        # --- symlink swaps: the rollback must never follow a link ---
        ws, outside = root / "ws", root / "outside"
        ws.mkdir()
        outside.mkdir()
        (ws / "keep.py").write_bytes(b"ORIGINAL\n")
        (ws / "sub").mkdir()
        (ws / "sub" / "a.txt").write_bytes(b"A\n")
        victim = outside / "victim.cfg"
        victim.write_bytes(b"outside, untouched\n")
        (outside / "dir_target").mkdir()
        swapped = WorkspaceGuard(root=ws).snapshot()
        (ws / "keep.py").unlink()
        (ws / "keep.py").symlink_to(victim)          # what `ln -sf` does
        shutil.rmtree(ws / "sub")
        (ws / "sub").symlink_to(outside / "dir_target")
        (ws / "stray").symlink_to(victim)
        seen = swapped.changes()
        check("a_tracked_file_replaced_by_a_symlink_is_its_own_change_class",
              seen["replaced_by_symlink"] == ["keep.py", "sub/a.txt"]
              and seen["deleted"] == []
              and seen["symlinks_created"] == ["stray", "sub"],
              str(seen))
        try:
            swapped.enforce()
            check("enforce_rolls_a_symlink_swap_back", False, "did not raise")
        except WorkspaceGuardError:
            check("enforce_rolls_a_symlink_swap_back",
                  (ws / "keep.py").read_bytes() == b"ORIGINAL\n"
                  and not (ws / "keep.py").is_symlink()
                  and (ws / "sub" / "a.txt").read_bytes() == b"A\n"
                  and not (ws / "sub").is_symlink())
        check("restore_never_writes_through_a_file_symlink",
              victim.read_bytes() == b"outside, untouched\n",
              "the original bytes went to a real file, not the link target")
        check("restore_never_writes_through_a_directory_symlink",
              not (outside / "dir_target" / "a.txt").exists()
              and list((outside / "dir_target").iterdir()) == [])
        check("a_created_symlink_is_removed_without_touching_its_target",
              not (ws / "stray").is_symlink() and not (ws / "stray").exists()
              and victim.exists())
        check("the_workspace_is_clean_after_a_symlink_rollback", swapped.clean())

    return {"module": "core.opencode_step_guard", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
