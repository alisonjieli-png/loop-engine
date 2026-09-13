"""Tests for the interrupt checkpoint in loop_engine.solve_cli.

The handler is armed before a run has an id, so an interrupted run wrote
`<runs_dir>/checkpoint.json` with an empty run id, where nothing that reads
run history looks. `_follow_run_id` wraps the progress callback so the first
event carrying a run id moves the checkpoint to `<runs_dir>/<run_id>/`, next
to the run's other records, where `overnight_queue.summarise` reads it.
"""
from __future__ import annotations

import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import overnight_queue  # noqa: E402
from loop_engine import solve_cli  # noqa: E402
from loop_engine.core.run_checkpoint import RunCheckpoint  # noqa: E402


class FollowRunIdChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="solve-cli-cp-"))
        self.runs = str(self.root / "runs")
        self.checkpoint = RunCheckpoint(
            run_id="", workspace_base=str(self.root / "ws"),
            checkpoint_dir=self.runs)
        self.seen = []

    def test_first_event_moves_the_checkpoint_next_to_the_run(self):
        follow = solve_cli._follow_run_id(self.checkpoint, self.runs,
                                          self.seen.append)
        follow({"event_type": "practitioner.started", "run_id": "run-abc",
                "model_calls_completed": 0})
        follow({"event_type": "model.step.started", "run_id": "run-abc",
                "model_calls_completed": 3})
        self.assertEqual(self.checkpoint.run_id, "run-abc")
        self.assertEqual(self.checkpoint.checkpoint_dir,
                         os.path.join(self.runs, "run-abc"))
        self.assertEqual(self.checkpoint.model_calls, 3)
        self.assertEqual(len(self.seen), 2, "progress still reaches the writer")
        written = self.checkpoint.write()
        self.assertEqual(Path(written).parent.name, "run-abc")
        # Which is exactly where the queue looks.
        found = overnight_queue.checkpoint_candidates(Path(self.runs))
        self.assertEqual([str(p) for p in found], [written])

    def test_a_run_id_that_is_not_one_path_segment_is_ignored(self):
        follow = solve_cli._follow_run_id(self.checkpoint, self.runs, None)
        for bad in ("../escape", "a/b", "..", "."):
            follow({"run_id": bad})
        self.assertEqual(self.checkpoint.run_id, "")
        self.assertEqual(self.checkpoint.checkpoint_dir, self.runs)

    def test_odd_events_never_raise(self):
        follow = solve_cli._follow_run_id(self.checkpoint, self.runs,
                                          self.seen.append)
        for event in (None, "text", {"run_id": 12}, {"model_calls_completed": "x"}):
            follow(event)
        self.assertEqual(len(self.seen), 4)


class ArmCheckpointChecks(unittest.TestCase):
    def test_nothing_is_armed_without_both_paths(self):
        checkpoint = RunCheckpoint(run_id="", workspace_base="/ws",
                                   checkpoint_dir="")
        self.assertEqual(solve_cli._arm_interrupt_checkpoint(checkpoint), ())
        self.assertEqual(checkpoint.installed_signals, ())

    def test_arming_happens_once(self):
        checkpoint = RunCheckpoint(run_id="", workspace_base="/ws",
                                   checkpoint_dir="/runs")
        previous = {name: signal.getsignal(getattr(signal, name))
                    for name in ("SIGTERM", "SIGINT", "SIGHUP")}
        try:
            first = solve_cli._arm_interrupt_checkpoint(checkpoint)
            self.assertIn("SIGTERM", first)
            handler = signal.getsignal(signal.SIGTERM)
            second = solve_cli._arm_interrupt_checkpoint(checkpoint)
            self.assertEqual(second, first)
            self.assertIs(signal.getsignal(signal.SIGTERM), handler)
        finally:
            for name, disposition in previous.items():
                signal.signal(getattr(signal, name), disposition)


if __name__ == "__main__":
    unittest.main()
