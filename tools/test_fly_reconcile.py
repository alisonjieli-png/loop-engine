"""Deployment supervision under lost replies, concurrency and failed commands."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import signal
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

    def test_every_command_fits_the_machines_api_and_carries_the_exact_source(self):
        # October 5, 2026: the Machines API refused an 18,853-byte command (the source inlined twice) with
        # PayloadTooLarge, so the deploy's apply-grants step never started. The source now travels compressed, once.
        import base64
        import shlex
        import zlib
        source = Path(remote.__file__).read_text()
        for mode in ("start", "status", "reconcile"):
            command = controller.remote_command(mode, self.record)
            self.assertLessEqual(len(command.encode("utf-8")), controller.MAXIMUM_COMMAND_BYTES)
            program = shlex.split(command)[2]
            packed = program.split("b64decode(", 1)[1].split(")", 1)[0].strip("'")
            self.assertEqual(zlib.decompress(base64.b64decode(packed)).decode("utf-8"), source)
        # KNOWN_WRONG: the form that failed live, the source inlined twice and uncompressed, is over the bound.
        doubled = ("scope={'__name__':'deployment_operation'}; exec(" + repr(source) + ",scope); scope['main'](" +
                   repr(source) + ")")
        self.assertGreater(len(shlex.join(["python", "-c", doubled, "status", "apply-grants", "a" * 40, "123"]).encode()),
                           controller.MAXIMUM_COMMAND_BYTES)

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

    def test_operator_reconcile_sends_one_reconcile_call_and_checks_the_closure(self):
        closure = {"binding": self.record, "state": "uncertain", "exit_code": None, "reason": "interrupted_without_result",
                   "reconciliation": {"binding": self.record, "reason": "interrupted_without_result", "reconciled_at": 1}}
        result = subprocess.CompletedProcess([], 0, json.dumps({"stdout": json.dumps(closure)}), "")
        arguments = ["fly_reconcile.py", "--app", "fixture-app", "--machine", "123456789abc", "--operation", "apply-grants",
                     "--command", shlex.join(remote.COMMANDS["apply-grants"]), "--revision", "a" * 40, "--run-id", "123",
                     "--timeout", "660", "--reconcile"]
        printed = io.StringIO()
        with patch.object(controller.subprocess, "run", return_value=result) as run, patch.object(sys, "argv", arguments), \
                redirect_stdout(printed), redirect_stderr(io.StringIO()):
            self.assertEqual(controller.main(), 0)
        run.assert_called_once()
        self.assertEqual(shlex.split(run.call_args.args[0][4])[-4:], ["reconcile", "apply-grants", "a" * 40, "123"])
        self.assertEqual(json.loads(printed.getvalue()), closure)
        def lost(*args):
            raise subprocess.TimeoutExpired("fake", 40)
        for call, error in ((lost, "outcome_unknown"), (lambda *args: {**closure, "state": "failed"}, "invalid_reconciliation"),
                            (lambda *args: {**closure, "reconciliation": None}, "invalid_reconciliation")):
            with self.subTest(error=error), redirect_stderr(io.StringIO()), self.assertRaisesRegex(RuntimeError, error):
                controller.close("fixture-app", "123456789abc", self.record, call=call)

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
                with self.assertRaisesRegex(ValueError, "operation_not_uncertain"):
                    remote.reconcile(self.record)
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
            # The operator closes it after checking its effect; only then may the next operation start.
            third = remote.binding("apply-grants", "c" * 40, "125")
            with patch.object(remote, "ROOT", directory), patch.object(remote.subprocess, "Popen") as process:
                closed = remote.reconcile(self.record)
                self.assertEqual(closed["reconciliation"]["reason"], "deadline_requires_reconciliation")
                self.assertEqual(remote.start(third, "unused source")["state"], "pending")
                process.assert_called_once()
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

    def test_a_killed_supervisor_is_pending_while_its_command_runs_then_uncertain_and_reconcilable(self):
        # Known wrong until October 5, 2026: a supervisor killed before its result left the operation pending for ever,
        # and the protocol had no call that could close it, so every later deployment operation was refused.
        with tempfile.TemporaryDirectory() as temporary:
            directory, started, release = (Path(temporary) / name for name in ("operations", "started", "release"))
            command = [sys.executable, "-c", "\n".join((
                "import pathlib, time", "pathlib.Path(" + repr(str(started)) + ").touch()", "for _ in range(1000):",
                "    if pathlib.Path(" + repr(str(release)) + ").exists(): break", "    time.sleep(.02)"))]
            self.start_local(directory, command, limit=30)
            try:
                deadline = time.monotonic() + 8
                while not started.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(started.exists())
                os.kill(self.children[0].pid, signal.SIGKILL)
                self.children[0].wait(timeout=8)
                with patch.object(remote, "ROOT", directory):
                    # The command still holds the lock, so nothing may close the operation while it runs.
                    self.assertEqual(remote.status(self.record)["state"], "pending")
                    with self.assertRaises(BlockingIOError):
                        remote.reconcile(self.record)
            finally:
                release.touch()
            report = self.wait_local(directory)
            self.assertEqual((report["state"], report["reason"]), ("uncertain", "interrupted_without_result"))
            different = remote.binding("apply-grants", "b" * 40, "124")
            with patch.object(remote, "ROOT", directory):
                with self.assertRaisesRegex(ValueError, "requires_reconciliation"):
                    remote.start(different, "unused source")
                # An interrupted earlier reconcile left its temporary file; it must not stop this one.
                (remote.directory_for(self.record) / "reconciliation.pending").write_text("{")
                closed = remote.reconcile(self.record)
                self.assertEqual(closed["reconciliation"]["binding"], self.record)
                self.assertEqual(remote.reconcile(self.record), closed)
                self.assertEqual(remote.start(self.record, "unused source"), closed)
                with patch.object(remote.subprocess, "Popen") as process:
                    self.assertEqual(remote.start(different, "unused source")["state"], "pending")
                    process.assert_called_once()

    def test_a_leftover_active_pending_never_stops_a_start(self):
        # Known wrong until October 5, 2026: save created its temporary file exclusively, so an active.pending left by an
        # interrupted save raised FileExistsError after the reservation was written; no worker ran and status answered
        # pending for ever.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            directory.mkdir(mode=0o700)
            (directory / "active.pending").write_text("{")
            self.assertEqual(self.start_local(directory, [sys.executable, "-c", "print('{}')"])["state"], "pending")
            self.assertEqual(json.loads((directory / "active.json").read_text()), self.record)
            self.assertEqual(self.wait_local(directory)["state"], "succeeded")
            self.assertEqual(list(directory.rglob("*.pending")), [])

    def test_a_leftover_result_pending_never_hides_a_finished_command(self):
        # Known wrong until October 5, 2026: the supervisor's final save raised FileExistsError, so an operation whose
        # command had finished answered pending for ever. The fixture command leaves the temporary file itself.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            leftover = directory / "-".join(("a" * 40, "123", "apply-grants")) / "result.pending"
            command = [sys.executable, "-c", "import pathlib; pathlib.Path(" + repr(str(leftover)) + ").write_text('{'); print('{}')"]
            self.start_local(directory, command)
            report = self.wait_local(directory)
            self.assertEqual((report["state"], report["exit_code"], report["stdout"]), ("succeeded", 0, "{}\n"))
            self.assertFalse(leftover.exists())

    def test_a_start_interrupted_before_its_reservation_launched_nothing_and_may_finish(self):
        # Known wrong until October 5, 2026: the folder such a start leaves made every status, start and reconcile call for
        # its binding raise FileNotFoundError. The worker starts only after the reservation is published.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "operations"
            operation = directory / "-".join(("a" * 40, "123", "apply-grants"))
            operation.mkdir(parents=True, mode=0o700)
            (operation / "reservation.pending").write_text("{")
            with patch.object(remote, "ROOT", directory):
                self.assertEqual(remote.status(self.record)["state"], "absent")
            self.assertEqual(self.start_local(directory, [sys.executable, "-c", "print('{}')"])["state"], "pending")
            self.assertEqual(self.wait_local(directory)["state"], "succeeded")
            self.assertEqual(json.loads((operation / "reservation.json").read_text()), self.record)


if __name__ == "__main__":
    unittest.main()
