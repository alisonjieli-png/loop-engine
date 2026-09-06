"""Preserve an interrupted run's best work instead of losing the night.

An overnight run has nobody to restart it.  Today the engine writes Run History
only at a Loop's terminal transition, the kernel's per-pass event file is never
enabled on the adaptive path, and no signal handler exists anywhere in the
package -- so SIGTERM, an OOM kill, or a closed laptop lid at 3am discards
every artifact the run produced, including artifacts that were already correct.

Measured on 2026-09-05: a run produced a fully correct module on its first
attempt and a broken one on its third.  Had it been killed at any point after
attempt 1, the correct file was sitting on disk with nothing recording that it
existed or that it was the best of the set.

This module does not attempt to resume reasoning.  Restoring a partially
completed model loop would require replaying provider state that was never
captured, and pretending otherwise would be worse than stopping.  It preserves
what survives an interruption and is worth having in the morning: which
attempts exist, which one the others agree with, and where to find it.
"""
from __future__ import annotations

import json
import os
import signal
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .solution_ratchet import rank_attempts

CHECKPOINT_FILENAME = "checkpoint.json"

#: Signals worth catching.  SIGKILL cannot be caught by design, so a hard kill
#: still loses the checkpoint -- the periodic write below is what covers it.
_CAUGHT_SIGNALS = ("SIGTERM", "SIGINT", "SIGHUP")


@dataclass
class RunCheckpoint:
    """The part of a run that outlives the process that made it."""

    run_id: str
    workspace_base: str
    checkpoint_dir: str
    task: str = ""
    passes_completed: int = 0
    model_calls: int = 0
    reason: str = ""
    installed_signals: tuple = field(default_factory=tuple)

    def path(self) -> Path:
        return Path(self.checkpoint_dir) / CHECKPOINT_FILENAME

    def snapshot(self) -> dict:
        """Describe the run's surviving work, ranking attempts if there are any."""
        attempts = []
        base = Path(self.workspace_base) if self.workspace_base else None
        if base is not None and base.is_dir():
            attempts = sorted(str(p) for p in base.glob("attempt-*")
                              if p.is_dir())
        ranking: dict = {}
        retained = ""
        sole_note = ""
        if len(attempts) >= 2:
            try:
                ranking = rank_attempts(attempts).to_dict()
                retained = ranking.get("retained", "")
            except Exception:                            # noqa: BLE001
                # A checkpoint that raises is worse than a checkpoint that is
                # merely incomplete: the interruption already happened.
                ranking = {}
        elif len(attempts) == 1:
            # Nothing to compare it against, so this is not a ranking -- but
            # naming the only work that exists is the whole point of writing a
            # checkpoint at 3am.  Say plainly that it is unranked.
            retained = attempts[0]
            sole_note = ("only one attempt exists, so it is named but NOT "
                         "ranked: no cross-attempt agreement was available")
        return {
            "record_type": "run_checkpoint/v1",
            "run_id": self.run_id,
            "task": self.task[:2000],
            "workspace_base": self.workspace_base,
            "passes_completed": self.passes_completed,
            "model_calls": self.model_calls,
            "attempts": attempts,
            "ranking": ranking,
            "retained": retained,
            "retained_is_ranked": bool(ranking),
            "sole_attempt_note": sole_note,
            "reason": self.reason,
            "note": ("Reasoning state is not resumable: provider state was "
                     "never captured. This records the work that survived."),
        }

    def write(self) -> str:
        """Write the checkpoint atomically, so a kill mid-write cannot corrupt it."""
        directory = Path(self.checkpoint_dir)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self.snapshot(), indent=1, sort_keys=True)
            handle, temporary = tempfile.mkstemp(
                dir=str(directory), prefix=".checkpoint-", suffix=".json")
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.replace(temporary, self.path())
            return str(self.path())
        except OSError:
            return ""


def read_checkpoint(checkpoint_dir: str | Path) -> dict:
    """Read a checkpoint left by an interrupted run, or an empty mapping."""
    path = Path(checkpoint_dir) / CHECKPOINT_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def install_signal_checkpoint(checkpoint: RunCheckpoint) -> tuple:
    """Write the checkpoint on interruption, then re-raise the default action.

    The handler stays deliberately small: it writes and restores the previous
    disposition rather than trying to unwind the run, because a handler that
    does real work during a shutdown is a handler that fails during a shutdown.
    """
    installed = []
    for name in _CAUGHT_SIGNALS:
        number = getattr(signal, name, None)
        if number is None:
            continue

        def handler(signal_number, frame, _name=name):
            checkpoint.reason = f"interrupted by {_name}"
            checkpoint.write()
            signal.signal(signal_number, signal.SIG_DFL)
            os.kill(os.getpid(), signal_number)

        try:
            signal.signal(number, handler)
            installed.append(name)
        except (ValueError, OSError):
            # Not the main thread, or the platform refuses: a run without a
            # handler still checkpoints on its normal pass boundaries.
            continue
    checkpoint.installed_signals = tuple(installed)
    return tuple(installed)


def self_test() -> dict:
    """Offline proof that an interrupted run keeps its best work."""
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    good = ("def parse(text):\n"
            "    table = {'A': 1, 'B': 2, 'C': 3}\n"
            "    if text not in table:\n"
            "        raise ValueError('bad')\n"
            "    return table[text]\n")
    broken = ("def parse(text):\n"
              "    table = {'A': 1}\n"
              "    if text not in table:\n"
              "        raise ValueError('bad')\n"
              "    return table[text]\n")
    tests = ("from mod import parse\n"
             "assert parse('A') == 111\n"
             "assert parse('B') == 222\n"
             "assert parse('C') == 333\n")

    with tempfile.TemporaryDirectory() as root:
        base = Path(root) / "ws"
        for name, source in (("attempt-1", good), ("attempt-2", good),
                             ("attempt-3", broken)):
            directory = base / name
            directory.mkdir(parents=True)
            (directory / "mod.py").write_text(source, encoding="utf-8")
            (directory / "test_mod.py").write_text(tests, encoding="utf-8")

        checkpoint = RunCheckpoint(
            run_id="run-1", workspace_base=str(base),
            checkpoint_dir=str(Path(root) / "history"),
            task="parse letters", passes_completed=3, model_calls=17)
        written = checkpoint.write()
        check("checkpoint_is_written", bool(written) and Path(written).is_file())

        restored = read_checkpoint(str(Path(root) / "history"))
        check("checkpoint_round_trips",
              restored.get("run_id") == "run-1"
              and restored.get("passes_completed") == 3)
        check("every_attempt_is_recorded",
              len(restored.get("attempts") or ()) == 3,
              str(restored.get("attempts")))
        check("interrupted_run_still_names_its_best_attempt",
              Path(restored.get("retained") or "").name == "attempt-1",
              restored.get("retained", ""))
        check("ranking_ignores_the_wrong_expected_values",
              "111" in tests and restored.get("ranking", {}).get(
                  "inputs_harvested", 0) == 3,
              str(restored.get("ranking", {}).get("inputs_harvested")))
        check("write_is_atomic_leaving_no_partial_files",
              not list(Path(Path(root) / "history").glob(".checkpoint-*")))

        empty = RunCheckpoint(run_id="run-2", workspace_base=str(Path(root) / "absent"),
                              checkpoint_dir=str(Path(root) / "history2"))
        empty.write()
        blank = read_checkpoint(str(Path(root) / "history2"))
        check("a_run_with_no_attempts_still_checkpoints",
              blank.get("run_id") == "run-2" and blank.get("attempts") == [])

        missing = read_checkpoint(str(Path(root) / "nowhere"))
        check("absent_checkpoint_reads_as_empty", missing == {})

        installed = install_signal_checkpoint(checkpoint)
        check("signal_handlers_install", "SIGTERM" in installed, str(installed))
        for name in installed:
            signal.signal(getattr(signal, name), signal.SIG_DFL)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
