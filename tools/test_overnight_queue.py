"""Tests for tools/overnight_queue.py: graceful abandonment and checkpoint reading.

`subprocess.run(timeout=...)` kills a hung task with SIGKILL, which no handler
can catch, so the engine's interrupt checkpoint was never written for an
abandoned task. `run_task` sends SIGTERM first and SIGKILL only after
`--grace-seconds`. `summarise` reads the interrupt checkpoint at
`<runs_dir>/checkpoint.json` as well as the per-run one.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, HERE)
sys.path.insert(0, SRC)

import overnight_queue  # noqa: E402

#: A child that arms the engine's interrupt checkpoint and then waits.
_CHILD = textwrap.dedent("""
    import signal, sys, time
    sys.path.insert(0, {src!r})
    from loop_engine.core.run_checkpoint import RunCheckpoint, install_signal_checkpoint
    cp = RunCheckpoint(run_id="child", workspace_base=sys.argv[1], checkpoint_dir=sys.argv[1])
    install_signal_checkpoint(cp)
    if len(sys.argv) > 2 and sys.argv[2] == "ignore-term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print("armed", flush=True)
    time.sleep(60)
""")


class RunTaskChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="queue-test-"))

    def _child(self, *extra) -> list:
        return [sys.executable, "-c", _CHILD.format(src=SRC),
                str(self.root), *extra]

    def test_sigterm_first_lets_the_checkpoint_land(self):
        code, tail, ended = overnight_queue.run_task(
            self._child(), timeout=1.0, grace_seconds=20.0)
        self.assertEqual(code, 124)
        self.assertTrue(ended.startswith("terminated"), ended)
        checkpoint = self.root / "checkpoint.json"
        self.assertTrue(checkpoint.is_file(), "SIGTERM handler wrote nothing")
        self.assertEqual(json.loads(checkpoint.read_text())["reason"],
                         "interrupted by SIGTERM")

    def test_zero_grace_is_the_earlier_immediate_kill(self):
        code, _, ended = overnight_queue.run_task(
            self._child(), timeout=1.0, grace_seconds=0)
        self.assertEqual(code, 124)
        self.assertTrue(ended.startswith("killed"), ended)
        time.sleep(0.2)
        self.assertFalse((self.root / "checkpoint.json").exists())

    def test_a_task_that_ignores_sigterm_is_killed_after_the_grace(self):
        began = time.time()
        code, _, ended = overnight_queue.run_task(
            self._child("ignore-term"), timeout=1.0, grace_seconds=0.5)
        self.assertEqual(code, 124)
        self.assertIn("SIGTERM ignored", ended)
        self.assertLess(time.time() - began, 20)

    def test_a_finished_task_reports_its_own_exit_code(self):
        code, tail, ended = overnight_queue.run_task(
            [sys.executable, "-c", "print('done'); raise SystemExit(3)"],
            timeout=30, grace_seconds=1)
        self.assertEqual((code, ended), (3, "finished"))
        self.assertIn("done", tail)

    def test_timeout_stops_owned_descendants_that_hold_output_pipes(self):
        child = (
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)']); "
            "print('spawned', flush=True); time.sleep(20)")
        began = time.monotonic()
        code, tail, ended = overnight_queue.run_task(
            [sys.executable, "-c", child], timeout=0.5, grace_seconds=0.5)
        self.assertEqual(code, 124)
        self.assertIn("spawned", tail)
        self.assertLess(time.monotonic() - began, 5, ended)


class SummariseChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="queue-summarise-"))
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.workspace = self.root / "ws"
        self.workspace.mkdir()

    def _write(self, path: Path, payload: dict, age: float = 0.0) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))

    def test_interrupt_checkpoint_at_the_top_of_runs_dir_is_read(self):
        self._write(self.runs / "checkpoint.json", {
            "attempts": ["a", "b"], "retained": "/x/attempt-1",
            "retained_is_ranked": True, "reason": "interrupted by SIGTERM"})
        result = overnight_queue.summarise(self.workspace, self.runs)
        self.assertEqual(result["attempts"], 2)
        self.assertTrue(result["ranked"])
        self.assertEqual(result["reason"], "interrupted by SIGTERM")
        self.assertEqual(result["checkpoint"], str(self.runs / "checkpoint.json"))

    def test_the_newest_of_both_locations_wins(self):
        self._write(self.runs / "checkpoint.json",
                    {"attempts": ["old"], "reason": "old"}, age=120)
        self._write(self.runs / "run-1" / "checkpoint.json",
                    {"attempts": ["a", "b", "c"], "reason": "run completed"})
        result = overnight_queue.summarise(self.workspace, self.runs)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["reason"], "run completed")
        found = overnight_queue.checkpoint_candidates(self.runs)
        self.assertEqual([p.parent.name for p in found], ["runs", "run-1"])

    def test_no_checkpoint_reads_as_empty(self):
        result = overnight_queue.summarise(self.workspace, self.runs)
        self.assertEqual((result["attempts"], result["checkpoint"]), (0, ""))


if __name__ == "__main__":
    unittest.main()
