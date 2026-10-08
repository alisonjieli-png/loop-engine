"""Offline operator queue admission, durable accounting and crash controls."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import overnight_queue as queue
import overnight_queue_state as records


class QueueChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="queue-v2-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tasks = [self.root / f"input-{index}.txt" for index in range(3)]
        for index, path in enumerate(self.tasks):
            path.write_text(f"Offline synthetic task {index}\n")
        self.manifest = self.root / "tasks.txt"
        self.manifest.write_text("\n".join(map(str, self.tasks)) + "\n")
        self.args = SimpleNamespace(manifest=str(self.manifest), runs_dir=str(self.root / "runs"),
            workspace_root=str(self.root / "work"), python=sys.executable, task_timeout=10,
            grace_seconds=0.1, max_calls_per_task=120, queue_call_budget=125, max_passes=2,
            queue_timeout=60, fresh=False, status=False, reconcile=None, authorize_reconcile=False)
        self.state_path = Path(self.args.runs_dir) / queue.STATE_FILENAME

    def run_queue(self, runner):
        with redirect_stdout(io.StringIO()):
            return queue.run_queue(self.args, runner=runner)

    def state(self):
        return records.load_state(self.state_path)

    def good(self, command, **kwargs):
        state = self.state()
        attempt = state["attempts"][-1]
        self.assertEqual(attempt["status"], "reserved")
        self.assertEqual(int(command[command.index("--max-model-calls") + 1]), attempt["allocation"])
        self.assertTrue(kwargs["pass_fds"])
        snapshot = Path(command[command.index("--file") + 1])
        self.assertEqual(snapshot.read_bytes(), self.tasks[attempt["task_index"]].read_bytes())
        return 0, "private fixture output is not retained", "finished"

    def fail(self, command, **kwargs):
        self.good(command, **kwargs)
        return 7, "fixture", "finished"

    def test_remaining_allocation_is_reserved_before_each_child(self):
        self.assertEqual(self.run_queue(self.good), 0)
        state = self.state()
        self.assertEqual([row["allocation"] for row in state["attempts"]], [120, 5])
        self.assertEqual(records.calls_allocated(state), 125)
        self.assertTrue(all(row["outcome"]["observed_model_calls"] is None for row in state["attempts"]))

    def test_positive_resume_skips_finished_without_replenishing(self):
        self.run_queue(self.good)
        before = self.state_path.read_bytes()
        runner = mock.Mock(side_effect=AssertionError("must not dispatch"))
        self.assertEqual(self.run_queue(runner), 0)
        runner.assert_not_called()
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_failed_child_consumes_full_reservation_and_holds_queue(self):
        self.assertEqual(self.run_queue(self.fail), 2)
        state = self.state()
        self.assertEqual(records.calls_allocated(state), 120)
        self.assertEqual(state["attempts"][0]["status"], "unknown")
        self.assertIsNone(state["attempts"][0]["outcome"]["observed_model_calls"])
        with self.assertRaisesRegex(queue.QueueRefusal, "unknown_outcome_requires_reconciliation"):
            self.run_queue(mock.Mock(side_effect=AssertionError("unsafe retry")))

    def test_interruption_before_dispatch_retains_unknown_reservation(self):
        def interrupted(command, **kwargs):
            self.good(command, **kwargs)
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_queue(interrupted)
        self.assertEqual(records.calls_allocated(self.state()), 120)
        self.assertEqual(self.state()["attempts"][0]["status"], "unknown")

    def test_failed_durable_reservation_makes_no_child_call(self):
        original = queue.save_state
        def broken(path, state):
            if state["attempts"]:
                raise OSError("offline injected persistence failure")
            return original(path, state)
        runner = mock.Mock()
        with mock.patch.object(queue, "save_state", side_effect=broken), self.assertRaises(OSError):
            self.run_queue(runner)
        runner.assert_not_called()
        self.assertEqual(records.calls_allocated(self.state()), 0)

    def test_failure_after_child_before_outcome_commit_is_not_replayed(self):
        original = queue.save_state
        def broken(path, state):
            if state["attempts"] and state["attempts"][-1]["status"] != "reserved":
                raise OSError("offline injected completion failure")
            return original(path, state)
        runner = mock.Mock(side_effect=self.good)
        with mock.patch.object(queue, "save_state", side_effect=broken), self.assertRaises(OSError):
            self.run_queue(runner)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(self.state()["attempts"][0]["status"], "reserved")
        with self.assertRaisesRegex(queue.QueueRefusal, "unknown_outcome_requires_reconciliation"):
            self.run_queue(runner)
        self.assertEqual(runner.call_count, 1)

    def test_fresh_is_refused_and_does_not_rewrite_historical_evidence(self):
        self.run_queue(self.fail)
        before = self.state_path.read_bytes()
        self.args.fresh = True
        with self.assertRaisesRegex(queue.QueueRefusal, "fresh_allowance_reset_forbidden"):
            self.run_queue(mock.Mock())
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_corrupt_legacy_and_unknown_versions_never_become_new_budget(self):
        Path(self.args.runs_dir).mkdir()
        for raw in (b"{", b"[]", b'{"completed":{},"calls_used":0}',
                    b'{"record_type":"overnight_queue_state/v1"}',
                    b'{"record_type":"overnight_queue_state/v999"}'):
            with self.subTest(raw=raw):
                self.state_path.write_bytes(raw)
                runner = mock.Mock()
                with self.assertRaises(queue.QueueRefusal):
                    self.run_queue(runner)
                runner.assert_not_called()
                self.assertEqual(self.state_path.read_bytes(), raw)

    def test_missing_state_with_prior_artifacts_refuses_reinitialization(self):
        Path(self.args.runs_dir).mkdir()
        (Path(self.args.runs_dir) / "old-attempt").mkdir()
        with self.assertRaisesRegex(queue.QueueRefusal, "state_missing_in_nonempty_runs_root"):
            self.run_queue(mock.Mock())

    def test_manifest_task_and_limit_changes_refuse_without_mutation(self):
        self.run_queue(self.fail)
        before = self.state_path.read_bytes()
        for field, value in (("queue_call_budget", 126), ("max_calls_per_task", 121),
                             ("task_timeout", 20), ("max_passes", 3), ("queue_timeout", 61)):
            old = getattr(self.args, field)
            setattr(self.args, field, value)
            with self.subTest(field=field), self.assertRaisesRegex(queue.QueueRefusal, "queue_binding_changed"):
                self.run_queue(mock.Mock())
            setattr(self.args, field, old)
        self.tasks[0].write_text("changed task")
        with self.assertRaisesRegex(queue.QueueRefusal, "queue_binding_changed"):
            self.run_queue(mock.Mock())
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_invalid_positive_limits_and_nonfinite_wall_limits_refuse_before_files(self):
        for field, value in (("queue_call_budget", 0), ("max_calls_per_task", -1),
                             ("max_passes", True), ("task_timeout", float("inf")),
                             ("grace_seconds", -1), ("queue_timeout", 10 ** 400)):
            old = getattr(self.args, field)
            setattr(self.args, field, value)
            with self.subTest(field=field), self.assertRaises(queue.QueueRefusal):
                self.run_queue(mock.Mock())
            setattr(self.args, field, old)
        self.assertFalse(Path(self.args.runs_dir).exists())

    def test_symlink_state_and_duplicate_task_refused(self):
        Path(self.args.runs_dir).mkdir()
        other = self.root / "other-state"
        other.write_text("{}")
        self.state_path.symlink_to(other)
        with self.assertRaises(queue.QueueRefusal):
            self.run_queue(mock.Mock())
        self.assertEqual(other.read_text(), "{}")
        self.manifest.write_text(str(self.tasks[0]) + "\n" + str(self.tasks[0]))
        with self.assertRaisesRegex(queue.QueueRefusal, "task_missing_or_duplicate"):
            queue.bind_queue(self.args)

    def test_typed_reconciliation_preserves_accounting_and_never_dispatches(self):
        self.run_queue(self.fail)
        state = self.state()
        evidence = self.root / "operator-evidence.json"
        evidence.write_text('{"fixture":"verified no external effect; child stopped"}')
        request = {"record_type": "overnight_queue_reconciliation/v1", "binding_sha256": state["binding_sha256"],
                   "attempt_id": "attempt-000001", "action": "retry", "external_outcome": "effects_reconciled",
                   "operator_confirmation": "checked_external_effects_and_child_quiescence",
                   "evidence_path": str(evidence), "evidence_sha256": records.bytes_digest(evidence.read_bytes())}
        request_path = self.root / "reconcile.json"
        request_path.write_text(json.dumps(request))
        self.args.reconcile = request_path
        with self.assertRaisesRegex(queue.QueueRefusal, "reconciliation_authority_required"):
            self.run_queue(mock.Mock())
        self.args.authorize_reconcile = True
        runner = mock.Mock(side_effect=AssertionError("reconcile cannot dispatch"))
        self.assertEqual(self.run_queue(runner), 0)
        runner.assert_not_called()
        self.assertEqual(records.calls_allocated(self.state()), 120)
        self.args.reconcile, self.args.authorize_reconcile = None, False
        self.run_queue(self.good)
        state = self.state()
        self.assertEqual([row["allocation"] for row in state["attempts"]], [120, 5])
        self.assertEqual([row["task_index"] for row in state["attempts"]], [0, 0])
        self.assertTrue((Path(self.args.runs_dir) / "attempt-000001/task.txt").is_file())
        self.assertTrue((Path(self.args.runs_dir) / "attempt-000002/task.txt").is_file())

    def test_changed_reconciliation_evidence_and_bindings_are_refused(self):
        self.run_queue(self.fail)
        state = self.state()
        evidence = self.root / "evidence.json"
        evidence.write_text("{}")
        request = {"record_type": "overnight_queue_reconciliation/v1", "binding_sha256": state["binding_sha256"],
                   "attempt_id": "attempt-000001", "action": "retire", "external_outcome": "not_dispatched",
                   "operator_confirmation": "checked_external_effects_and_child_quiescence",
                   "evidence_path": str(evidence), "evidence_sha256": "0" * 64}
        with self.assertRaisesRegex(queue.QueueRefusal, "reconciliation_evidence_changed"):
            queue.reconcile(state, request)
        request["binding_sha256"] = "0" * 64
        with self.assertRaisesRegex(queue.QueueRefusal, "reconciliation_binding_mismatch"):
            queue.reconcile(state, request)

    def test_expired_queue_cannot_restart_its_wall_clock(self):
        binding = queue.bind_queue(self.args)
        with records.queue_lock(Path(self.args.runs_dir)):
            records.save_state(self.state_path, records.new_state(binding, time.time() - 100))
        runner = mock.Mock()
        self.assertEqual(self.run_queue(runner), 0)
        runner.assert_not_called()
        self.assertLess(self.state()["deadline"], time.time())

    def test_known_wrong_overallocation_and_unresolved_continuation_records_refuse(self):
        self.run_queue(self.good)
        state = self.state()
        wrong = deepcopy(state)
        wrong["attempts"][1]["allocation"] = 120
        with self.assertRaisesRegex(queue.QueueRefusal, "queue_allocation_exceeded"):
            records.validate_state(wrong)
        wrong = deepcopy(state)
        wrong["attempts"][0]["status"] = "unknown"
        with self.assertRaisesRegex(queue.QueueRefusal, "unreconciled_queue_continuation"):
            records.validate_state(wrong)

    def test_single_writer_and_removed_guard_control(self):
        with records.queue_lock(Path(self.args.runs_dir)):
            with self.assertRaisesRegex(queue.QueueRefusal, "queue_writer_active"):
                self.run_queue(mock.Mock())
            # Deliberately removed flock admits the forbidden second writer:
            # this is the known-wrong control for the lock assertion above.
            with mock.patch.object(records.fcntl, "flock", return_value=None):
                with records.queue_lock(Path(self.args.runs_dir)):
                    admitted_without_guard = True
            self.assertTrue(admitted_without_guard)

    def test_killed_supervisor_keeps_child_lock_and_durable_hold(self):
        marker = self.root / "child.pid"
        helper = self.root / "supervisor.py"
        helper.write_text("import os,sys,subprocess,json\n"
            f"sys.path[:0]=[{str(HERE)!r},{str(HERE.parent / 'src')!r}]\n"
            "from types import SimpleNamespace\nimport overnight_queue as q\n"
            f"args=SimpleNamespace(**json.loads({json.dumps(vars(self.args))!r}))\n"
            "def runner(command, **kwargs):\n"
            f" child=subprocess.Popen([sys.executable,'-c',\"import os,pathlib,time; pathlib.Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)\"],pass_fds=kwargs['pass_fds'])\n"
            " child.wait()\n return 0,'','finished'\n"
            "q.run_queue(args,runner=runner)\n")
        parent = subprocess.Popen([sys.executable, str(helper)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        child_pid = None
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists(), "fixture child did not start")
            child_pid = int(marker.read_text())
            parent.kill()
            parent.wait(timeout=3)
            self.assertEqual(self.state()["attempts"][0]["status"], "reserved")
            self.assertEqual(records.calls_allocated(self.state()), 120)
            with self.assertRaisesRegex(queue.QueueRefusal, "queue_writer_active"):
                self.run_queue(mock.Mock())
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=3)
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            parent.stderr.close()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                with records.queue_lock(Path(self.args.runs_dir)):
                    break
            except queue.QueueRefusal:
                time.sleep(0.02)
        with self.assertRaisesRegex(queue.QueueRefusal, "unknown_outcome_requires_reconciliation"):
            self.run_queue(mock.Mock())


if __name__ == "__main__":
    unittest.main()
