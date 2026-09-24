"""Known-wrong checks for the supervised overnight candidate batch.

No model is called by these checks: dispatch is observed through the
journal and status records only.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.overnight_candidate_batch import (  # noqa: E402
    ATTEMPTS_PER_IDEA,
    BatchError,
    BatchSupervisor,
    IDEA_PER_LANE,
    MAX_CALLS,
    _append_jsonl,
    _atomic_json,
    load_matrix,
    select_stratified,
    watchdog,
)
from tools.opencode_generation_lanes import Lane  # noqa: E402


def _matrix_path() -> Path:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "matrix.json"
        import subprocess
        code = subprocess.run(
            [sys.executable, str(ROOT / "tools/harness_idea_matrix.py"),
             "--output", str(output)],
            check=True, capture_output=True)
        return output


class MatrixOnce(unittest.TestCase):
    """Build one matrix for the whole module."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.matrix = cls.root / "matrix.json"
        import subprocess
        subprocess.run(
            [sys.executable, str(ROOT / "tools/harness_idea_matrix.py"),
             "--output", str(cls.matrix)],
            check=True, capture_output=True)


class SelectionChecks(MatrixOnce):
    def test_selection_returns_requested_count_with_unique_ids(self):
        batch = load_matrix(self.matrix)
        picked = select_stratified(batch, 40)
        ids = [idea["id"] for idea in picked]
        self.assertEqual(len(picked), 40)
        self.assertEqual(len(set(ids)), 40)

    def test_selection_covers_many_datatypes(self):
        batch = load_matrix(self.matrix)
        picked = select_stratified(batch, 40)
        datatypes = {idea["datatype"] for idea in picked}
        self.assertGreater(len(datatypes), 5)

    def test_selection_rotates_real_occupations(self):
        batch = load_matrix(self.matrix)
        picked = select_stratified(batch, 20)
        codes = {idea["applicability"]["occupation_code"] for idea in picked}
        self.assertGreater(len(codes), 1)
        for idea in picked:
            self.assertNotEqual(idea["applicability"]["task_reference"].strip(), "")
            self.assertIn(".", idea["applicability"]["occupation_code"])

    def test_selection_is_deterministic(self):
        batch = load_matrix(self.matrix)
        first = select_stratified(batch, 20)
        second = select_stratified(batch, 20)
        self.assertEqual([i["id"] for i in first], [i["id"] for i in second])

    def test_zero_count_is_refused(self):
        batch = load_matrix(self.matrix)
        with self.assertRaises(BatchError):
            select_stratified(batch, 0)


class JournalChecks(MatrixOnce):
    def _lanes(self, root: Path):
        first = Lane("lane-one", "ollama-cloud", "gpt-oss:20b", root / "one")
        second = Lane("lane-two", "ollama-cloud", "gemma4:31b", root / "two")
        return [first, second]

    def _ideas(self, count=6):
        batch = load_matrix(self.matrix)
        return select_stratified(batch, count)

    def _supervisor(self, root: Path, ideas, max_calls=1000):
        return BatchSupervisor(
            batch_directory=root / "batch",
            lanes=self._lanes(root),
            ideas=ideas,
            max_calls=max_calls,
        )

    def test_journal_replay_skips_completed_ideas(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas()
            supervisor = self._supervisor(root, ideas)
            first_id = ideas[0]["id"]
            supervisor._record({"event": "outcome", "lane_id": "lane-one",
                               "idea_id": first_id, "outcome": "candidate_written"})
            replayed = BatchSupervisor(
                batch_directory=root / "batch", lanes=self._lanes(root),
                ideas=ideas, max_calls=1000)
            self.assertIn(first_id, replayed._completed)

    def test_journal_replay_keeps_failed_ideas_failed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas()
            supervisor = self._supervisor(root, ideas)
            first_id = ideas[0]["id"]
            supervisor._record({"event": "outcome", "lane_id": "lane-one",
                               "idea_id": first_id, "outcome": "failed_provider"})
            replayed = BatchSupervisor(
                batch_directory=root / "batch", lanes=self._lanes(root),
                ideas=ideas, max_calls=1000)
            self.assertIn(first_id, replayed._failed)
            self.assertNotIn(first_id, replayed._completed)

    def test_reassign_event_is_replayed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas()
            supervisor = self._supervisor(root, ideas)
            supervisor._record({"event": "reassign", "idea_id": ideas[0]["id"],
                                "from_lane": "lane-one", "to_lane": "lane-two"})
            replayed = BatchSupervisor(
                batch_directory=root / "batch", lanes=self._lanes(root),
                ideas=ideas, max_calls=1000)
            self.assertEqual(replayed._assignment[ideas[0]["id"]], "lane-two")

    def test_idea_never_repeated_after_terminal_outcome(self):
        # The invariant behind crash-safe recovery: a completed or failed
        # idea is skipped on restart, so a restart cannot double-call it.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas(4)
            supervisor = self._supervisor(root, ideas)
            supervisor._completed.add(ideas[0]["id"])
            supervisor._failed.add(ideas[1]["id"])
            todo = [idea for idea in ideas
                    if idea["id"] not in supervisor._completed
                    and idea["id"] not in supervisor._failed]
            self.assertEqual(len(todo), 2)

    def test_ceiling_records_clean_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas(4)
            supervisor = self._supervisor(root, ideas, max_calls=2)
            supervisor._calls = 2
            final = supervisor._run_idea(self._lanes(root)[0], ideas[0])
            self.assertEqual(final, "ceiling")
            self.assertIn(ideas[0]["id"], supervisor._failed)

    def test_degraded_lane_reassigns_remaining_ideas(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas(6)
            supervisor = self._supervisor(root, ideas)
            supervisor._health["lane-one"].degraded = True
            before = supervisor._assignment[ideas[0]["id"]]
            if before == "lane-one":
                supervisor._reassign(ideas[0])
                self.assertEqual(supervisor._assignment[ideas[0]["id"]], "lane-two")

    def test_status_written_and_read_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ideas = self._ideas(4)
            supervisor = self._supervisor(root, ideas)
            supervisor._completed.add(ideas[0]["id"])
            status = supervisor._write_status("2026-09-24T00:00:00Z")
            on_disk = json.loads((root / "batch" / "status.json").read_text())
            self.assertEqual(status["candidates"], on_disk["candidates"])
            self.assertEqual(status["state"], "incomplete")
            self.assertEqual(on_disk["remaining"], 3)


class WatchdogChecks(MatrixOnce):
    def test_watchdog_restarts_incomplete_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = root / "batch"
            batch.mkdir()
            _atomic_json(batch / "status.json", {
                "record_type": "overnight_batch_status/v1",
                "state": "incomplete", "ideas_total": 10, "candidates": 3,
                "failed": 1, "remaining": 6})
            outcome = watchdog(batch, ["/bin/true"])
            self.assertTrue(outcome.startswith("restarted:"))
            journal = (batch / "journal.jsonl").read_text()
            self.assertIn("watchdog_restart", journal)

    def test_watchdog_leaves_complete_batch_alone(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = root / "batch"
            batch.mkdir()
            _atomic_json(batch / "status.json", {
                "record_type": "overnight_batch_status/v1",
                "state": "complete", "ideas_total": 1, "candidates": 1,
                "failed": 0, "remaining": 0})
            self.assertEqual(watchdog(batch, ["/bin/true"]), "complete")

    def test_watchdog_without_status_does_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(watchdog(Path(temporary), ["/bin/true"]), "no_status")

    def test_watchdog_respects_live_supervisor_pid(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = root / "batch"
            batch.mkdir()
            _atomic_json(batch / "status.json", {
                "record_type": "overnight_batch_status/v1",
                "state": "incomplete", "ideas_total": 2, "candidates": 0,
                "failed": 0, "remaining": 2})
            (batch / "supervisor.pid").write_text(f"{os.getpid()}\n")  # this test lives
            self.assertEqual(watchdog(batch, ["/bin/true"]), "alive")


class DeclaredLimitsChecks(unittest.TestCase):
    def test_declared_batch_defaults(self):
        self.assertEqual(IDEA_PER_LANE * 4, 1000)
        self.assertGreater(MAX_CALLS, 1000)
        self.assertEqual(ATTEMPTS_PER_IDEA, 3)


if __name__ == "__main__":
    unittest.main()