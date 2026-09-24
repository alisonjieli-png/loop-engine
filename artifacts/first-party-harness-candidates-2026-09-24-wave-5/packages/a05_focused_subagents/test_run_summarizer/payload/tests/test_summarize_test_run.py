"""Tests for scripts/summarize_test_run.py. Effects: starts the script and small Python commands as subprocesses, sends a stop signal to one script subprocess, reads the reply schema and, on Linux, the process table under /proc; writes no file.

Run from the package root:

    python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "summarize_test_run.py"
SCHEMA = PACKAGE / "contracts" / "reply.schema.json"
MISSING_FOLDER = "folder-that-does-not-exist-for-the-guard-tests"

FAILING_SUITE = (
    "import unittest\n"
    "class Prices(unittest.TestCase):\n"
    "    def test_total(self):\n"
    "        self.assertEqual(2 + 2, 4)\n"
    "    def test_rounding(self):\n"
    "        self.assertEqual(round(2.675, 2), 2.68)\n"
    "unittest.main(argv=['prices'])\n"
)
PASSING_SUITE = FAILING_SUITE.replace("round(2.675, 2), 2.68", "round(2.5), 2")

PYTEST_LOG = (
    "============================= test session starts ==============================\n"
    "collected 4 items\n"
    "\n"
    "tests/test_prices.py .F.s                                                [100%]\n"
    "\n"
    "=================================== FAILURES ===================================\n"
    "________________________________ test_rounding _________________________________\n"
    "\n"
    "    def test_rounding():\n"
    ">       assert round(10.005, 2) == 10.01\n"
    "E       assert 10.0 == 10.01\n"
    "\n"
    "tests/test_prices.py:14: AssertionError\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_prices.py::test_rounding - assert 10.0 == 10.01\n"
    "==================== 1 failed, 2 passed, 1 skipped in 0.05s ====================\n"
)
PYTEST_SETUP_ERROR_LOG = (
    "============================= test session starts ==============================\n"
    "collected 4 items\n"
    "\n"
    "tests/test_orders.py ...E                                                [100%]\n"
    "\n"
    "==================================== ERRORS ====================================\n"
    "_________________________ ERROR at setup of test_refund _________________________\n"
    "\n"
    "    def ledger():\n"
    ">       return load_ledger('fixtures/ledger.json')\n"
    "E       FileNotFoundError: fixtures/ledger.json\n"
    "\n"
    "tests/conftest.py:8: FileNotFoundError\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/test_orders.py::test_refund - FileNotFoundError: fixtures/ledger.json\n"
    "========================== 3 passed, 1 error in 0.20s ==========================\n"
)
# pytest prints the ERRORS section before FAILURES, but lists FAILED before ERROR in its short summary.
PYTEST_ERRORS_PART = (
    "==================================== ERRORS ====================================\n"
    "_________________________ ERROR at setup of test_refund _________________________\n"
    "\n"
    "    def ledger():\n"
    ">       return load_ledger('fixtures/ledger.json')\n"
    "E       FileNotFoundError: fixtures/ledger.json\n"
    "\n"
    "tests/conftest.py:8: FileNotFoundError\n"
)
PYTEST_FAILURES_PART = (
    "=================================== FAILURES ===================================\n"
    "_____________________________ TestOrders.test_total ______________________________\n"
    "\n"
    "    def test_total(self):\n"
    ">       assert total([1, 2]) == 4\n"
    "E       assert 3 == 4\n"
    "\n"
    "tests/test_orders.py:20: AssertionError\n"
)
PYTEST_ERROR_AND_FAILURE_LOG = (
    "============================= test session starts ==============================\n"
    "collected 3 items\n"
    "\n"
    "tests/test_orders.py E.F                                                 [100%]\n"
    "\n"
    + PYTEST_ERRORS_PART + PYTEST_FAILURES_PART +
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_orders.py::TestOrders::test_total - assert 3 == 4\n"
    "ERROR tests/test_orders.py::test_refund - FileNotFoundError: fixtures/ledger.json\n"
    "===================== 1 failed, 1 passed, 1 error in 0.20s =====================\n"
)
PYTEST_CLASS_FAILURE_LOG = (
    "collected 2 items\n"
    "\n"
    + PYTEST_FAILURES_PART +
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_orders.py::TestOrders::test_total - assert 3 == 4\n"
    "========================= 1 failed, 1 passed in 0.10s ==========================\n"
)
GO_LOG = (
    "=== RUN   TestAdd\n"
    "    add_test.go:9: Add(1, 2) = 4, want 3\n"
    "--- FAIL: TestAdd (0.00s)\n"
    "=== RUN   TestSub\n"
    "--- PASS: TestSub (0.00s)\n"
    "=== RUN   TestDiv\n"
    "    div_test.go:5: needs a fixture file\n"
    "--- SKIP: TestDiv (0.00s)\n"
    "FAIL\n"
    "FAIL\texample.com/calc\t0.002s\n"
    "FAIL\n"
)
CARGO_LOG = (
    "\n"
    "running 2 tests\n"
    "test tests::adds ... ok\n"
    "test tests::subtracts ... FAILED\n"
    "\n"
    "failures:\n"
    "\n"
    "---- tests::subtracts stdout ----\n"
    "\n"
    "thread 'tests::subtracts' panicked at src/lib.rs:12:9:\n"
    "assertion `left == right` failed\n"
    "  left: 1\n"
    " right: 2\n"
    "note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace\n"
    "\n"
    "\n"
    "failures:\n"
    "    tests::subtracts\n"
    "\n"
    "test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
    "\n"
)
JEST_LOG = (
    " FAIL  src/prices.test.js\n"
    "  prices\n"
    "    \u2713 adds tax (3 ms)\n"
    "    \u2715 rounds half up (4 ms)\n"
    "\n"
    "  \u25cf prices \u203a rounds half up\n"
    "\n"
    "    expect(received).toBe(expected) // Object.is equality\n"
    "\n"
    "    Expected: 10.01\n"
    "    Received: 10\n"
    "\n"
    "Test Suites: 1 failed, 1 total\n"
    "Tests:       1 failed, 3 passed, 4 total\n"
    "Snapshots:   0 total\n"
    "Time:        0.512 s\n"
)


def printer(text: str, status: int) -> list[str]:
    """A command that prints text and exits with the status, as a stand-in for a real runner."""
    code = "import sys\nsys.stdout.write(" + repr(text) + ")\nsys.stdout.flush()\nsys.exit(" + str(status) + ")\n"
    return [sys.executable, "-c", code]


def summarize(command: list[str], options: tuple[str, ...] = ()) -> tuple[int, dict]:
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *options, "--", *command],
                          capture_output=True, text=True, timeout=120)
    lines = done.stdout.strip().splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected one JSON line, got {done.stdout!r} and {done.stderr!r}")
    return done.returncode, json.loads(lines[0])


def process_ids_with(marker: str) -> list[int]:
    """Process ids whose command line holds the marker but not the script name, from /proc."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            words = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if marker.encode() in words and not any(SCRIPT.name.encode() in word for word in words):
            found.append(int(entry.name))
    return found


def running(pid: int) -> bool:
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return False
    return fields[0] != "Z"


class RealRunnerOutput(unittest.TestCase):
    def test_failing_unittest_suite_is_summarized(self):
        command = [sys.executable, "-c", FAILING_SUITE]
        status, reply = summarize(command)
        self.assertEqual(status, 1)
        self.assertEqual(reply["command"], command)
        self.assertEqual(reply["result"], "failed")
        self.assertEqual(reply["runner"], "unittest")
        self.assertEqual(reply["counts"], {"passed": 1, "failed": 1, "errors": 0, "skipped": 0})
        self.assertTrue(reply["first_failure"]["test"].startswith("test_rounding"))
        self.assertIn("AssertionError: 2.67 != 2.68", reply["first_failure"]["excerpt"])
        self.assertNotEqual(reply["exit_status"], 0)

    def test_passing_unittest_suite_is_summarized(self):
        status, reply = summarize([sys.executable, "-c", PASSING_SUITE])
        self.assertEqual(status, 0)
        self.assertEqual(reply["result"], "passed")
        self.assertEqual(reply["counts"], {"passed": 2, "failed": 0, "errors": 0, "skipped": 0})
        self.assertIsNone(reply["first_failure"])
        self.assertEqual(reply["tail"], [])

    def test_leading_assignment_reaches_the_command(self):
        code = ("import os, unittest\n"
                "class Mode(unittest.TestCase):\n"
                "    def test_mode(self):\n"
                "        self.assertEqual(os.environ.get('LEDGER_MODE'), 'strict')\n"
                "unittest.main(argv=['mode'])\n")
        command = ["LEDGER_MODE=strict", sys.executable, "-c", code]
        status, reply = summarize(command)
        self.assertEqual((status, reply["result"], reply["exit_status"]), (0, "passed", 0))
        self.assertEqual(reply["counts"], {"passed": 1, "failed": 0, "errors": 0, "skipped": 0})
        self.assertEqual(reply["command"], command)
        status, reply = summarize(command[1:])
        self.assertEqual((status, reply["result"]), (1, "failed"))


class RunnerFormats(unittest.TestCase):
    def test_pytest_counts_and_first_failure(self):
        status, reply = summarize(printer(PYTEST_LOG, 1))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "pytest", "failed"))
        self.assertEqual(reply["counts"], {"passed": 2, "failed": 1, "errors": 0, "skipped": 1})
        self.assertEqual(reply["first_failure"]["test"], "tests/test_prices.py::test_rounding")
        self.assertIn("E       assert 10.0 == 10.01", reply["first_failure"]["excerpt"])
        self.assertIn("tests/test_prices.py:14: AssertionError", reply["first_failure"]["excerpt"])

    def test_known_wrong_passed_tests_do_not_hide_a_setup_error(self):
        status, reply = summarize(printer(PYTEST_SETUP_ERROR_LOG, 1))
        self.assertEqual(reply["result"], "failed")
        self.assertEqual(status, 1)
        self.assertEqual(reply["counts"], {"passed": 3, "failed": 0, "errors": 1, "skipped": 0})
        self.assertEqual(reply["first_failure"]["test"], "tests/test_orders.py::test_refund")
        self.assertIn("E       FileNotFoundError: fixtures/ledger.json", reply["first_failure"]["excerpt"])

    def test_known_wrong_name_and_excerpt_come_from_one_failure(self):
        status, reply = summarize(printer(PYTEST_ERROR_AND_FAILURE_LOG, 1))
        self.assertEqual((status, reply["result"]), (1, "failed"))
        self.assertEqual(reply["counts"], {"passed": 1, "failed": 1, "errors": 1, "skipped": 0})
        first = reply["first_failure"]
        self.assertEqual(first["test"], "tests/test_orders.py::test_refund")
        self.assertIn("E       FileNotFoundError: fixtures/ledger.json", first["excerpt"])
        self.assertNotIn("E       assert 3 == 4", first["excerpt"])

    def test_class_test_name_is_matched_to_its_summary_line(self):
        status, reply = summarize(printer(PYTEST_CLASS_FAILURE_LOG, 1))
        self.assertEqual((status, reply["result"]), (1, "failed"))
        self.assertEqual(reply["first_failure"]["test"], "tests/test_orders.py::TestOrders::test_total")
        self.assertIn("E       assert 3 == 4", reply["first_failure"]["excerpt"])

    def test_zero_exit_status_does_not_hide_reported_failures(self):
        for log in (PYTEST_LOG, PYTEST_SETUP_ERROR_LOG):
            status, reply = summarize(printer(log, 0))
            self.assertEqual((status, reply["result"]), (1, "failed"))
            self.assertIn("exit status is 0", reply["reason"])

    def test_go_verbose_output(self):
        status, reply = summarize(printer(GO_LOG, 1))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "go", "failed"))
        self.assertEqual(reply["counts"], {"passed": 1, "failed": 1, "errors": 0, "skipped": 1})
        self.assertEqual(reply["first_failure"]["test"], "TestAdd")
        self.assertTrue(any("add_test.go:9" in line for line in reply["first_failure"]["excerpt"]))

    def test_cargo_output(self):
        status, reply = summarize(printer(CARGO_LOG, 101))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "cargo", "failed"))
        self.assertEqual(reply["counts"], {"passed": 1, "failed": 1, "errors": 0, "skipped": 0})
        self.assertEqual(reply["first_failure"]["test"], "tests::subtracts")
        self.assertIn("assertion `left == right` failed", reply["first_failure"]["excerpt"])

    def test_jest_output(self):
        status, reply = summarize(printer(JEST_LOG, 1))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "jest", "failed"))
        self.assertEqual(reply["counts"], {"passed": 3, "failed": 1, "errors": 0, "skipped": 0})
        self.assertEqual(reply["first_failure"]["test"], "prices \u203a rounds half up")
        self.assertIn("Expected: 10.01", reply["first_failure"]["excerpt"])

    def test_known_wrong_unknown_output_with_exit_zero_is_not_a_pass(self):
        status, reply = summarize(printer("build ok\nall checks done\n", 0))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "unknown", "unconfirmed"))
        self.assertIsNone(reply["counts"])
        self.assertIn("no test summary", reply["reason"])
        self.assertEqual(reply["tail"], ["build ok", "all checks done"])

    def test_unknown_output_with_other_exit_status_keeps_counts_null(self):
        status, reply = summarize(printer("step one\nstep two failed\n", 3))
        self.assertEqual((status, reply["result"], reply["exit_status"]), (1, "failed", 3))
        self.assertIsNone(reply["counts"])
        self.assertEqual(reply["tail"], ["step one", "step two failed"])

    def test_known_wrong_collection_only_output_is_not_a_pass(self):
        log = "collected 4 items\n<Module tests/test_a.py>\n\n4 tests collected in 0.01s\n"
        status, reply = summarize(printer(log, 0))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "pytest", "no_tests"))

    def test_every_test_skipped_is_not_a_pass(self):
        status, reply = summarize(printer("..\n=========== 3 skipped in 0.01s ===========\n", 0))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "pytest", "no_tests"))
        self.assertIn("skipped", reply["reason"])

    def test_no_tests_is_its_own_result(self):
        status, reply = summarize(printer("\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n", 5))
        self.assertEqual((status, reply["runner"], reply["result"]), (1, "unittest", "no_tests"))


class Refusals(unittest.TestCase):
    """Each refused command is harmless even if the refusal were broken: it prints help or exits at once."""

    def assert_refused(self, command, options=(), fragment=""):
        status, reply = summarize(command, options)
        self.assertEqual((status, reply["result"]), (2, "refused"), command)
        self.assertIsNone(reply["exit_status"])
        self.assertIsNone(reply["runner"])
        self.assertIn(fragment, reply["reason"], command)

    def assert_passes_the_guard(self, command):
        """The guard runs before the folder check, so a missing folder proves the guard let the command through."""
        status, reply = summarize(command, ("--cwd", MISSING_FOLDER))
        self.assertEqual((status, reply["result"]), (2, "refused"), command)
        self.assertIn("--cwd does not name an existing folder", reply["reason"], command)

    def test_shell_operator_is_refused(self):
        self.assert_refused([sys.executable, "-c", "pass", "&&", "echo", "done"], fragment="shell")

    def test_shell_program_is_refused(self):
        self.assert_refused(["bash", "-c", "exit 0"], fragment="shell")

    def test_package_install_is_refused(self):
        self.assert_refused(["pip", "install", "--help"], fragment="packages")
        self.assert_refused([sys.executable, "-m", "pip", "install", "--help"], fragment="packages")

    def test_known_wrong_short_install_forms_are_refused(self):
        for command in (["npm", "ci", "--help"], ["npm", "i", "--help"], ["npm", "--prefix", "web", "ci", "--help"],
                        ["pnpm", "i", "--help"], ["yarn", "--version"], ["uv", "sync", "--help"],
                        ["pipx", "--help"], ["npx", "--help"],
                        [sys.executable, "-I", "-m", "pip", "download", "--help"]):
            self.assert_refused(command, fragment="packages")

    def test_deletion_tool_is_refused(self):
        self.assert_refused(["rm", "--help"], fragment="not a test runner")

    def test_known_wrong_other_file_tools_are_refused(self):
        for command in (["unlink", "--help"], ["find", "--help"], ["truncate", "--help"]):
            self.assert_refused(command, fragment="not a test runner")

    def test_known_wrong_wrapper_programs_are_refused(self):
        for command in (["env", "rm", "--help"], ["timeout", "5", "rm", "--help"], ["nice", "rm", "--help"],
                        ["nohup", "rm", "--help"], ["xargs", "--help"]):
            self.assert_refused(command, fragment="wrapper")

    def test_ordinary_test_commands_pass_the_guard(self):
        for command in (["npm", "test"], ["npm", "run", "test:unit"], ["yarn", "jest"], ["uv", "run", "pytest"],
                        ["poetry", "run", "pytest", "-k", "install"], ["cargo", "test"], ["go", "test", "./..."],
                        ["make", "test"], [sys.executable, "-m", "pytest", "-q"], ["pytest", "-k", "a;b"]):
            self.assert_passes_the_guard(command)

    def test_missing_command_is_refused(self):
        self.assert_refused([], fragment="no declared test command")

    def test_missing_separator_is_refused(self):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), sys.executable, "-c", "pass"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 2)
        self.assertEqual(json.loads(done.stdout)["result"], "refused")

    def test_folder_outside_the_root_is_refused(self):
        self.assert_refused([sys.executable, "-c", "pass"], ("--cwd", ".."), fragment="--cwd")
        self.assert_refused([sys.executable, "-c", "pass"], ("--cwd", "/"), fragment="--cwd")

    @unittest.skipUnless(sys.platform.startswith("linux") and Path("/proc/self/root").is_symlink(),
                         "uses the Linux process table")
    def test_folder_link_that_leaves_the_root_is_refused(self):
        # Started in its own /proc entry, the script sees "root" as a link to "/", outside its working folder.
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--cwd", "root", "--", sys.executable, "-c",
                               "pass"], cwd="/proc/self", capture_output=True, text=True, timeout=60)
        reply = json.loads(done.stdout)
        self.assertEqual((done.returncode, reply["result"]), (2, "refused"))
        self.assertIn("outside the repository root", reply["reason"])

    def test_bad_timeout_is_refused(self):
        self.assert_refused([sys.executable, "-c", "pass"], ("--timeout", "0"), fragment="--timeout")

    def test_known_wrong_non_ascii_digit_timeout_is_refused_with_json(self):
        self.assert_refused([sys.executable, "-c", "pass"], ("--timeout", "\u00b2"), fragment="--timeout")
        self.assert_refused([sys.executable, "-c", "pass"], ("--timeout", "\u0661\u0662"), fragment="--timeout")


class Limits(unittest.TestCase):
    def test_timeout_stops_the_command(self):
        status, reply = summarize([sys.executable, "-c", "import time\ntime.sleep(30)\n"], ("--timeout", "1"))
        self.assertEqual((status, reply["result"], reply["timed_out"]), (1, "timeout", True))
        self.assertLess(reply["seconds"], 20)

    def test_missing_program_is_not_started(self):
        status, reply = summarize(["no-such-test-runner-in-this-sandbox"])
        self.assertEqual((status, reply["result"]), (1, "not_started"))
        self.assertIsNone(reply["exit_status"])

    def test_long_output_is_bounded(self):
        code = ("import sys\n"
                "for number in range(45000):\n"
                "    sys.stdout.write('progress %d ' % number + 'x' * 190 + '\\n')\n"
                "sys.stdout.write(" + repr(PYTEST_LOG) + ")\n"
                "sys.exit(1)\n")
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--", sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=120)
        reply = json.loads(done.stdout)
        self.assertGreater(reply["output_bytes"], 8 * 1024 * 1024)
        self.assertEqual(reply["counts"], {"passed": 2, "failed": 1, "errors": 0, "skipped": 1})
        self.assertEqual(reply["first_failure"]["test"], "tests/test_prices.py::test_rounding")
        self.assertLess(len(done.stdout), 16 * 1024)

    @unittest.skipUnless(sys.platform.startswith("linux") and Path("/proc/self/stat").exists(),
                         "reads the Linux process table")
    def test_known_wrong_stop_signal_leaves_no_test_process_and_still_prints_json(self):
        marker = f"summarizer-stop-signal-test-{os.getpid()}"
        command = [sys.executable, "-c", "import time\ntime.sleep(60)\n", marker]
        script = subprocess.Popen([sys.executable, "-I", "-B", str(SCRIPT), "--timeout", "120", "--", *command],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        test_pids: list[int] = []
        try:
            deadline = time.monotonic() + 30
            while not test_pids and time.monotonic() < deadline:
                time.sleep(0.05)
                test_pids = process_ids_with(marker)
            self.assertEqual(len(test_pids), 1, "the test command did not start")
            os.killpg(script.pid, signal.SIGTERM)  # what a harness does to the command it started
            out, _err = script.communicate(timeout=30)
            lines = out.strip().splitlines()
            self.assertEqual(len(lines), 1, out)
            reply = json.loads(lines[0])
            self.assertEqual((script.returncode, reply["result"]), (1, "interrupted"))
            self.assertIn("SIGTERM", reply["reason"])
            gone_by = time.monotonic() + 10
            while running(test_pids[0]) and time.monotonic() < gone_by:
                time.sleep(0.05)
            self.assertFalse(running(test_pids[0]), "the test command outlived the stopped script")
        finally:
            if script.poll() is None:
                os.killpg(script.pid, signal.SIGKILL)
                script.wait()
            for pid in test_pids:
                if running(pid):
                    os.kill(pid, signal.SIGKILL)


class ReplyContract(unittest.TestCase):
    def test_script_output_matches_the_schema_keys(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        summary_shape = schema["$defs"]["summary"]
        refusal_shape = schema["$defs"]["refusal"]
        for command in ([sys.executable, "-c", FAILING_SUITE], ["bash", "-c", "exit 0"],
                        printer("build ok\n", 0)):
            _status, reply = summarize(command)
            self.assertEqual(set(reply), set(summary_shape["properties"]))
            self.assertEqual(set(reply), set(summary_shape["required"]))
            self.assertIn(reply["result"], summary_shape["properties"]["result"]["enum"])
            self.assertIn(reply["runner"], summary_shape["properties"]["runner"]["enum"])
            self.assertLessEqual(len(reply["first_failure"]["excerpt"] if reply["first_failure"] else []),
                                 summary_shape["properties"]["first_failure"]["oneOf"][1]["properties"]["excerpt"]
                                 ["maxItems"])
        for value in ("unconfirmed", "interrupted"):
            self.assertIn(value, summary_shape["properties"]["result"]["enum"])
        self.assertEqual(set(refusal_shape["required"]), {"record_type", "result", "reason"})
        self.assertEqual(refusal_shape["properties"]["result"]["const"], "refused")


if __name__ == "__main__":
    unittest.main()
