"""Deployment supervision under lost replies, concurrency and failed commands."""
import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import check_fly_service_container as container_check
import fly_reconcile as controller
import fly_reconcile_remote as remote


class FlyReconcileTests(unittest.TestCase):
    def setUp(self):
        self.record = remote.binding("apply-grants", "a" * 40, "123")
        self.children = []

    def tearDown(self):
        for child in self.children:
            child.wait(timeout=8)

    def test_only_container_qualified_commands_are_available(self):
        with self.assertRaises(ValueError):
            controller.remote_command("erase", self.record)
        self.assertEqual(remote.COMMANDS["apply-grants"], list(container_check.POST_DEPLOY_GRANT_COMMAND))
        self.assertEqual(remote.COMMANDS["apply-billing-policy"], list(container_check.POST_DEPLOY_BILLING_POLICY_COMMAND))
        for arguments in (("configure", "a" * 40, "123"), ("apply-grants", "../escape", "123"),
                          ("apply-grants", "a" * 40, "123; echo nope")):
            with self.assertRaises(ValueError):
                remote.binding(*arguments)
        command = [sys.executable, str(Path(controller.__file__)), "--app", "fixture-app", "--machine", "123456789abc",
                   "--operation", "apply-grants", "--command", "echo unsafe", "--revision", "a" * 40,
                   "--run-id", "123", "--timeout", "660"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("container-qualified command", result.stderr)

    def test_lost_start_and_status_responses_never_redispatch(self):
        attempts, ticks = [], [0]
        def call(app, machine, mode, record):
            attempts.append(mode)
            if len(attempts) < 3:
                raise subprocess.TimeoutExpired("fake", 30)
            return {"state": "succeeded", "exit_code": 0, "stdout": "{}", "elapsed_seconds": 213.5}
        with redirect_stderr(io.StringIO()):
            result = controller.reconcile("fixture-app", "123456789abc", self.record, call=call,
                clock=lambda: ticks[0], sleep=lambda seconds: ticks.__setitem__(0, ticks[0] + seconds))
        self.assertEqual(result["stdout"], "{}")
        self.assertEqual(attempts, ["start", "status", "status"])

    def test_controller_deadline_failure_and_invalid_success_are_not_success(self):
        for state in ("absent", "pending", "failed", "uncertain", "succeeded"):
            attempts, ticks = [], [0]
            def call(app, machine, mode, record):
                attempts.append(mode)
                return {"state": state, "exit_code": None}
            with self.subTest(state=state), self.assertRaises(RuntimeError):
                controller.reconcile("fixture-app", "123456789abc", self.record, call=call,
                    clock=lambda: ticks[0], sleep=lambda seconds: ticks.__setitem__(0, ticks[0] + seconds))
            self.assertEqual(attempts.count("start"), 1)
            self.assertLessEqual(ticks[0], 660)

    def test_transport_validates_binding_and_has_a_short_finite_timeout(self):
        report = {"binding": self.record, "state": "pending"}
        result = subprocess.CompletedProcess([], 0, json.dumps({"stdout": json.dumps(report)}), "")
        with patch.object(controller.subprocess, "run", return_value=result) as run:
            self.assertEqual(controller.invoke("fixture-app", "123456789abc", "status", self.record), report)
            self.assertEqual(run.call_args.args[0][-2:], ["--timeout", "30"])
            self.assertEqual(run.call_args.kwargs["timeout"], 40)
            wrong = copy.deepcopy(report)
            wrong["binding"]["revision"] = "b" * 40
            result.stdout = json.dumps({"stdout": json.dumps(wrong)})
            with self.assertRaisesRegex(ValueError, "binding_mismatch"):
                controller.invoke("fixture-app", "123456789abc", "status", self.record)

    def test_false_is_not_an_exit_code(self):
        def call(*args):
            return {"state": "succeeded", "exit_code": False, "stdout": "{}", "elapsed_seconds": 0}
        with self.assertRaisesRegex(RuntimeError, "invalid_operation_success"):
            controller.reconcile("fixture-app", "123456789abc", self.record, call=call)

    def start_local(self, directory, command, limit=5):
        """Run the actual detached supervisor with a local, model-free fixture."""
        source = Path(remote.__file__).read_text().replace(
            'ROOT = Path("/data/incoming/deployment-operations")', "ROOT = Path(" + repr(str(directory)) + ")")
        source = source.replace("if __name__ == \"__main__\":", "COMMANDS['apply-grants'] = " + repr(command)
                                + "\nLIMIT_SECONDS = " + repr(limit) + "\nif __name__ == \"__main__\":")
        spawn = remote.subprocess.Popen
        def tracked(*args, **kwargs):
            child = spawn(*args, **kwargs)
            self.children.append(child)
            return child
        with patch.object(remote, "ROOT", directory), patch.object(remote.subprocess, "Popen", side_effect=tracked):
            return remote.start(self.record, source)

    def wait_local(self, directory):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            with patch.object(remote, "ROOT", directory):
                report = remote.status(self.record)
            if report["state"] != "pending":
                return report
            time.sleep(0.02)
        self.fail("fixture supervisor did not finish")

    def test_real_detached_success_writes_once_and_refuses_parallel_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            output = Path(temporary) / "effect.txt"
            command = [sys.executable, "-c", "import pathlib,time; time.sleep(.25); pathlib.Path(" + repr(str(output))
                       + ").open('a').write('once\\n'); print('{}')"]
            self.assertEqual(self.start_local(directory, command)["state"], "pending")
            with patch.object(remote, "ROOT", directory), self.assertRaises(BlockingIOError):
                remote.start(self.record, "unused source")
            report = self.wait_local(directory)
            self.assertEqual(report["state"], "succeeded")
            self.assertEqual(report["stdout"], "{}\n")
            with patch.object(remote, "ROOT", directory):
                self.assertEqual(remote.start(self.record, "unused source"), report)
            self.assertEqual(output.read_text(), "once\n")

    def test_timeout_is_uncertain_and_cannot_start_a_different_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            self.start_local(directory, [sys.executable, "-c", "import time; time.sleep(10)"], limit=0.1)
            report = self.wait_local(directory)
            self.assertEqual(report["state"], "uncertain")
            self.assertEqual(report["reason"], "deadline_requires_reconciliation")
            different = remote.binding("apply-grants", "b" * 40, "124")
            with patch.object(remote, "ROOT", directory), self.assertRaisesRegex(ValueError, "requires_reconciliation"):
                remote.start(different, "unused source")
            # Removing the uncertain-state guard would admit another effect.
            with patch.object(remote, "ROOT", directory), patch.object(remote, "status", return_value={"state": "failed"}), \
                    patch.object(remote.subprocess, "Popen") as process:
                self.assertEqual(remote.start(different, "unused source")["state"], "pending")
                process.assert_called_once()

    def test_failed_command_is_not_success_and_oversize_output_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            self.start_local(directory, [sys.executable, "-c", "raise SystemExit(9)"])
            self.assertEqual(self.wait_local(directory)["exit_code"], 9)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            self.start_local(directory, [sys.executable, "-c", "print('0123456789')"])
            self.assertEqual(self.wait_local(directory)["state"], "succeeded")
            with patch.object(remote, "ROOT", directory), patch.object(remote, "OUTPUT_LIMIT", 5), \
                    self.assertRaisesRegex(ValueError, "too_large"):
                remote.status(self.record)


if __name__ == "__main__":
    unittest.main()
