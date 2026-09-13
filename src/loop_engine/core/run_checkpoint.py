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

DIGESTS AND THE SIGNAL HANDLER (2026-09-13).  Ranking attempts executes
generated code -- in a contained driver process, but still -- and a checkpoint
had no way to say whether the tree it described was still the tree on disk.
A snapshot now records a sha256 per attempt directory, and ``read_checkpoint``
recomputes them and marks the checkpoint ``stale`` with the changed paths when
they differ.  The signal handler no longer ranks: it reuses the ranking from
the last pass boundary when one exists and otherwise writes the inventory
unranked, unless ``rank_on_signal=True`` asks for the old behaviour.  A
handler that runs model code during a shutdown is a handler that fails during
a shutdown.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .solution_ratchet import rank_attempts, sort_attempts

CHECKPOINT_FILENAME = "checkpoint.json"

#: Signals worth catching.  SIGKILL cannot be caught by design, so a hard kill
#: still loses the checkpoint -- the periodic write below is what covers it.
_CAUGHT_SIGNALS = ("SIGTERM", "SIGINT", "SIGHUP")

#: Directories whose contents never change what an attempt IS.
_DIGEST_IGNORED_DIRECTORIES = ("__pycache__",)


def tree_digest(directory: "str | Path") -> str:
    """sha256 over every file's relative path and bytes, in a fixed order.

    Hashing READS the tree; it never imports or runs anything in it.  An
    unreadable tree digests to the empty string, which never matches a real
    digest, so it reads back as changed rather than as unchanged.
    """
    root = Path(directory)
    if not root.is_dir() or root.is_symlink():
        return ""
    digest = hashlib.sha256()
    try:
        files = sorted(
            path for path in root.rglob("*")
            if path.is_file() and not any(
                part in _DIGEST_IGNORED_DIRECTORIES
                for part in path.relative_to(root).parts))
        for path in files:
            if path.is_symlink():
                return ""
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return ""
    return digest.hexdigest()


def attempt_digests(attempts) -> dict:
    """One digest per attempt directory, keyed by its path."""
    return {str(attempt): tree_digest(attempt) for attempt in attempts}


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
    #: Whether an interruption may rank -- that is, execute generated code
    #: inside the signal handler.  Off by default; the last pass-boundary
    #: ranking is reused instead.
    rank_on_signal: bool = False
    #: Explicit host permission for trusted diagnostic implementations only.
    #: A checkpoint alone never authorizes executing generated code.
    host_execution_permitted: bool = False
    #: The ranking the last ranked write produced, with the digests of the
    #: tree it ranked, so an unranked write can reuse it and say how current
    #: it is.
    last_ranking: dict = field(default_factory=dict, repr=False)

    def path(self) -> Path:
        return Path(self.checkpoint_dir) / CHECKPOINT_FILENAME

    def attempts(self) -> list:
        """Attempt directories in natural order (attempt-10 after attempt-9)."""
        base = Path(self.workspace_base) if self.workspace_base else None
        if base is None or not base.is_dir():
            return []
        return sort_attempts(p for p in base.glob("attempt-*") if p.is_dir())

    def snapshot(self, *, rank: bool = True) -> dict:
        """Describe the run's surviving work, ranking attempts if asked to.

        ``rank=False`` never executes generated code: it reuses the ranking
        from the last ranked snapshot when there is one and otherwise leaves
        the ranking empty and says why.
        """
        attempts = self.attempts()
        digests = attempt_digests(attempts)
        ranking: dict = {}
        retained = ""
        sole_note = ""
        ranking_note = ""
        ranking_is_current = False
        if len(attempts) >= 2:
            if rank:
                try:
                    ranking = rank_attempts(
                        attempts, host_execution_permitted=(
                            self.host_execution_permitted is True)).to_dict()
                    retained = ranking.get("retained", "")
                    ranking_is_current = (
                        bool(ranking.get("scores"))
                        and all(digests.values())
                        and attempt_digests(attempts) == digests)
                    self.last_ranking = {
                        "ranking": ranking, "retained": retained,
                        "attempt_digests": dict(digests),
                        "passes_completed": self.passes_completed}
                except Exception:                        # noqa: BLE001
                    # A checkpoint that raises is worse than a checkpoint that
                    # is merely incomplete: the interruption already happened.
                    ranking = {}
            elif self.last_ranking:
                ranking = dict(self.last_ranking.get("ranking") or {})
                retained = str(self.last_ranking.get("retained") or "")
                ranked_digests = self.last_ranking.get("attempt_digests") or {}
                changed = sorted(path for path in set(digests) | set(ranked_digests)
                                 if not digests.get(path)
                                 or ranked_digests.get(path) != digests.get(path))
                ranking_is_current = not changed
                ranking_note = (
                    "ranking reused from the last pass boundary (pass "
                    f"{self.last_ranking.get('passes_completed')}); not "
                    "recomputed on interruption")
                if changed:
                    ranking_note += (" -- attempts changed since: "
                                     f"{[Path(p).name for p in changed]}")
            else:
                ranking_note = (
                    "ranking skipped: ranking executes generated code, which "
                    "an interruption handler does not do unless "
                    "rank_on_signal=True, and no pass-boundary ranking exists "
                    "to reuse")
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
            "attempt_digests": digests,
            "ranking": ranking,
            "ranking_is_current": ranking_is_current,
            "ranking_note": ranking_note,
            "ranked_on_write": bool(rank),
            "retained": retained,
            "retained_is_ranked": bool(ranking.get("scores")) and ranking_is_current,
            "sole_attempt_note": sole_note,
            "reason": self.reason,
            "note": ("Reasoning state is not resumable: provider state was "
                     "never captured. This records the work that survived."),
        }

    def write(self, *, rank: bool = True) -> str:
        """Write the checkpoint atomically, so a kill mid-write cannot corrupt it."""
        directory = Path(self.checkpoint_dir)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self.snapshot(rank=rank), indent=1,
                                 sort_keys=True)
            handle, temporary = tempfile.mkstemp(
                dir=str(directory), prefix=".checkpoint-", suffix=".json")
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.replace(temporary, self.path())
            return str(self.path())
        except OSError:
            return ""

    def write_on_signal(self, signal_name: str) -> str:
        """What the handler does: name the reason, write without ranking.

        Ranking on a signal happens only when ``rank_on_signal`` is set; the
        default reuses the last pass-boundary ranking or writes unranked.
        """
        self.reason = f"interrupted by {signal_name}"
        return self.write(rank=self.rank_on_signal)


def read_checkpoint(checkpoint_dir: "str | Path", *,
                    verify_digests: bool = True) -> dict:
    """Read a checkpoint left by an interrupted run, or an empty mapping.

    When the checkpoint carries attempt digests they are recomputed against
    the tree on disk: ``stale`` is True and ``changed_paths`` names every
    attempt that differs or has gone, so a reader never takes a ranking of
    yesterday's tree for a ranking of today's.
    """
    path = Path(checkpoint_dir) / CHECKPOINT_FILENAME
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(snapshot, dict):
        return {}
    recorded = snapshot.get("attempt_digests")
    if verify_digests and isinstance(recorded, dict) and recorded:
        changed = []
        for attempt, digest in recorded.items():
            current = tree_digest(attempt) if Path(attempt).is_dir() else ""
            if current != digest:
                changed.append(attempt)
        snapshot["stale"] = bool(changed)
        snapshot["changed_paths"] = changed
    return snapshot


def install_signal_checkpoint(checkpoint: RunCheckpoint, *,
                              rank_on_signal: "bool | None" = None) -> tuple:
    """Write the checkpoint on interruption, then re-raise the default action.

    The handler stays deliberately small: it writes and restores the previous
    disposition rather than trying to unwind the run, because a handler that
    does real work during a shutdown is a handler that fails during a shutdown.
    It does not rank unless ``rank_on_signal`` says so.
    """
    if rank_on_signal is not None:
        checkpoint.rank_on_signal = bool(rank_on_signal)
    installed = []
    for name in _CAUGHT_SIGNALS:
        number = getattr(signal, name, None)
        if number is None:
            continue

        def handler(signal_number, frame, _name=name):
            checkpoint.write_on_signal(_name)
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
            task="parse letters", passes_completed=3, model_calls=17,
            host_execution_permitted=True)
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

        # M4: digests per attempt, and a stale marker when the tree moves on.
        digests = restored.get("attempt_digests") or {}
        check("checkpoint_records_a_digest_per_attempt",
              len(digests) == 3 and all(
                  len(d) == 64 for d in digests.values()), str(digests))
        check("an_unchanged_tree_reads_back_as_fresh",
              restored.get("stale") is False
              and restored.get("changed_paths") == []
              and restored.get("ranking_is_current") is True)
        (base / "attempt-1" / "mod.py").write_text(
            "def parse(t):\n    return 'REGRESSED'\n", encoding="utf-8")
        again = read_checkpoint(str(Path(root) / "history"))
        check("a_changed_tree_reads_back_as_stale",
              again.get("stale") is True
              and [Path(p).name for p in again.get("changed_paths", [])]
              == ["attempt-1"], str(again.get("changed_paths")))
        unverified = read_checkpoint(str(Path(root) / "history"),
                                     verify_digests=False)
        check("digest_verification_can_be_switched_off",
              "stale" not in unverified and unverified.get("run_id") == "run-1")
        (base / "attempt-1" / "mod.py").write_text(good, encoding="utf-8")

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
        check("signal_handlers_do_not_rank_by_default",
              checkpoint.rank_on_signal is False)
        for name in installed:
            signal.signal(getattr(signal, name), signal.SIG_DFL)
        opted = install_signal_checkpoint(checkpoint, rank_on_signal=True)
        check("rank_on_signal_is_an_explicit_opt_in",
              checkpoint.rank_on_signal is True and "SIGTERM" in opted)
        for name in opted:
            signal.signal(getattr(signal, name), signal.SIG_DFL)
        checkpoint.rank_on_signal = False

        # M4: the interruption path never executes generated code by default.
        marker = Path(root) / "executed-by-checkpoint.txt"
        side_effects = Path(root) / "ws2"
        for name, source in (("attempt-1", good), ("attempt-2", good)):
            directory = side_effects / name
            directory.mkdir(parents=True)
            (directory / "mod.py").write_text(source, encoding="utf-8")
            (directory / "test_mod.py").write_text(tests, encoding="utf-8")
        (side_effects / "attempt-2" / "mod.py").write_text(
            f"open({str(marker)!r}, 'w').write('ran')\n" + good,
            encoding="utf-8")
        interrupted = RunCheckpoint(
            run_id="run-3", workspace_base=str(side_effects),
            checkpoint_dir=str(Path(root) / "history3"), passes_completed=1)
        interrupted.write_on_signal("SIGTERM")
        first = read_checkpoint(str(Path(root) / "history3"))
        check("signal_write_does_not_execute_generated_code_by_default",
              not marker.exists() and first.get("ranking") == {}
              and first.get("ranked_on_write") is False
              and "skipped" in first.get("ranking_note", "")
              and first.get("reason") == "interrupted by SIGTERM",
              first.get("ranking_note", ""))
        interrupted.write()
        check("a_pass_boundary_does_not_grant_host_execution",
              not marker.exists()
              and not interrupted.last_ranking.get("retained"))
        interrupted.host_execution_permitted = True
        interrupted.write()                       # a pass boundary: ranks
        check("a_pass_boundary_write_still_ranks",
              marker.exists() and interrupted.last_ranking.get("retained"),
              str(interrupted.last_ranking.get("retained")))
        marker.unlink()
        interrupted.write_on_signal("SIGINT")
        reused = read_checkpoint(str(Path(root) / "history3"))
        check("signal_write_reuses_the_last_pass_boundary_ranking",
              not marker.exists()
              and Path(reused.get("retained") or "").name == "attempt-1"
              and reused.get("retained_is_ranked") is True
              and reused.get("ranking_is_current") is True
              and "reused from the last pass boundary"
              in reused.get("ranking_note", ""),
              reused.get("ranking_note", ""))
        (side_effects / "attempt-1" / "mod.py").write_text(
            good + "\n# edited after the last ranking\n", encoding="utf-8")
        interrupted.write_on_signal("SIGHUP")
        moved = read_checkpoint(str(Path(root) / "history3"))
        check("a_reused_ranking_says_which_attempts_changed_since",
              moved.get("ranking_is_current") is False
              and "attempt-1" in moved.get("ranking_note", "")
              and not marker.exists(), moved.get("ranking_note", ""))
        interrupted.rank_on_signal = True
        interrupted.write_on_signal("SIGTERM")
        check("rank_on_signal_option_still_ranks",
              marker.exists()
              and read_checkpoint(str(Path(root) / "history3")).get(
                  "ranking_is_current") is True)

        # L5: attempts are listed in natural order.
        many = Path(root) / "ws3"
        for name in ("attempt-9", "attempt-10", "attempt-11"):
            (many / name).mkdir(parents=True)
            (many / name / "mod.py").write_text(good, encoding="utf-8")
        listing = RunCheckpoint(run_id="run-4", workspace_base=str(many),
                                checkpoint_dir=str(Path(root) / "history4"))
        check("attempts_are_listed_in_natural_order",
              [Path(p).name for p in listing.snapshot(rank=False)["attempts"]]
              == ["attempt-9", "attempt-10", "attempt-11"])

        check("tree_digest_reads_without_running_anything",
              tree_digest(side_effects / "attempt-2") != ""
              and tree_digest(side_effects / "attempt-2")
              != tree_digest(side_effects / "attempt-1")
              and tree_digest(Path(root) / "nowhere") == "")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
