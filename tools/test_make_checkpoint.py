"""Tests for tools/make_checkpoint.py with a fake command runner.

No test runs the real self-test or conformance suite; every engine and git
command is answered by an in-memory fake that records what was asked and
answers from a script. One test runs a tiny real subprocess to prove the
real runner keeps stdout, stderr, and the return code apart. Checkpoints
are written into a temporary directory, never into checkpoints/.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_checkpoint  # noqa: E402

DATE = "2026-09-13"
SELF_TEST_SUMMARY = {
    "record_type": "loop_engine_self_test_summary/v1",
    "passed": 12, "total": 12, "all_passed": True,
    "missing_dependencies": [], "optional_adapters_not_tested": [],
    "captured_output_lines": 3, "elapsed_seconds": 1.5,
    "provider_calls_made": 0, "failures": [],
}
SELF_TEST_STDERR = (
    "Running the full offline self-test. This scans the installed package "
    "and may take about a minute. No provider is called.\n"
    "Self-test still running: 10 seconds elapsed.\n")
CONFORMANCE_STDOUT = (
    "ZERO-TOLERANCE CONFORMANCE GATES\n"
    "  PASS  unclassified_files = 0\n"
    "  manifest: architecture_conformance.json | ALL GATES PASS\n")
GIT_STATUS = "## main...origin/main\n M tools/make_checkpoint.py\n?? notes.txt\n"
GIT_TRACKED = "README.md\ntools/make_checkpoint.py\n"
GIT_UNTRACKED = "notes.txt\n"
GIT_HEAD = "0123456789abcdef0123456789abcdef01234567\n"


class FakeRunner:
    """Answers checkpoint commands from a script and records every call."""

    def __init__(self, manifest_path, *, self_test_rc=0,
                 self_test_stdout=None, self_test_all_passed=True,
                 conformance_rc=0, all_gates_pass=True,
                 write_manifest=True, git_head_rc=0):
        self.manifest_path = manifest_path
        self.self_test_rc = self_test_rc
        if self_test_stdout is None:
            summary = dict(SELF_TEST_SUMMARY, all_passed=self_test_all_passed)
            if not self_test_all_passed:
                summary["passed"] = 11
                summary["failures"] = [{"test": "one", "detail": "broke"}]
            self_test_stdout = json.dumps(summary, indent=1) + "\n"
        self.self_test_stdout = self_test_stdout
        self.conformance_rc = conformance_rc
        self.all_gates_pass = all_gates_pass
        self.write_manifest = write_manifest
        self.git_head_rc = git_head_rc
        self.calls = []

    def __call__(self, command, *, env=None, timeout=None):
        command = list(command)
        self.calls.append({"command": command, "env": env,
                           "timeout": timeout})

        def result(rc, stdout, stderr=""):
            return make_checkpoint.CommandResult(
                tuple(command), rc, stdout, stderr)

        if "--self-test" in command:
            return result(self.self_test_rc, self.self_test_stdout,
                          SELF_TEST_STDERR)
        if "--conformance" in command:
            if self.write_manifest:
                with open(self.manifest_path, "w", encoding="utf-8") as handle:
                    json.dump({"record_type": "architecture_conformance/v1",
                               "all_gates_pass": self.all_gates_pass,
                               "zero_tolerance_gates": {
                                   "unclassified_files":
                                       0 if self.all_gates_pass else 2}},
                              handle)
            return result(self.conformance_rc, CONFORMANCE_STDOUT,
                          "conformance stderr noise\n")
        if command[:2] == ["git", "branch"]:
            return result(0, "main\n")
        if command[:2] == ["git", "status"]:
            return result(0, GIT_STATUS)
        if command[:2] == ["git", "rev-parse"]:
            if self.git_head_rc:
                return result(self.git_head_rc, "",
                              "fatal: not a git repository\n")
            return result(0, GIT_HEAD)
        if command[:3] == ["git", "ls-files", "--others"]:
            return result(0, GIT_UNTRACKED)
        if command[:2] == ["git", "ls-files"]:
            return result(0, GIT_TRACKED)
        raise AssertionError(f"unexpected command {command}")

    def commands(self):
        return [call["command"] for call in self.calls]


class CheckpointChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="checkpoint-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = os.path.join(self.directory.name, "checkpoints")
        os.makedirs(self.root)
        self.manifest = os.path.join(self.directory.name,
                                     "architecture_conformance.json")
        self.original_manifest = make_checkpoint.CONFORMANCE_MANIFEST
        make_checkpoint.CONFORMANCE_MANIFEST = self.manifest
        self.addCleanup(setattr, make_checkpoint, "CONFORMANCE_MANIFEST",
                        self.original_manifest)
        self.runner = FakeRunner(self.manifest)

    def run_main(self, slug, *extra, runner=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            code = make_checkpoint.main(
                [slug, "--checkpoints-dir", self.root, "--date", DATE, *extra],
                runner=runner or self.runner)
        return code, stdout.getvalue(), stderr.getvalue()

    def target(self, slug):
        return Path(self.root) / f"{DATE}-{slug}"

    def read_json(self, slug, name):
        return json.loads((self.target(slug) / name).read_text(encoding="utf-8"))

    def test_stdout_and_stderr_are_kept_apart(self):
        code, _out, _err = self.run_main("streams")
        self.assertEqual(code, 0)
        report = self.read_json("streams", "test-report.json")
        self.assertEqual(report["summary"], SELF_TEST_SUMMARY)
        self.assertEqual(report["parse_mode"], "whole_stdout")
        self.assertEqual(report["parse_error"], "")
        self.assertIn("still running", report["stderr_tail"])
        self.assertNotIn("still running", report["stdout_tail"])
        self.assertEqual(report["returncode"], 0)
        self_test_call = next(call for call in self.runner.calls
                              if "--self-test" in call["command"])
        self.assertEqual(self_test_call["command"][-3:],
                         ["--self-test", "--format", "json"])
        self.assertTrue(self_test_call["env"]["PYTHONPATH"].startswith(
            os.path.join(make_checkpoint.REPO, "src")))
        conformance = self.read_json("streams", "conformance.json")
        self.assertEqual(conformance["stderr_tail"],
                         "conformance stderr noise\n")
        self.assertNotIn("noise", conformance["stdout"])

    def test_real_runner_separates_streams_and_keeps_the_return_code(self):
        result = make_checkpoint.run_command([
            sys.executable, "-c",
            "import sys; print('to stdout'); "
            "print('to stderr', file=sys.stderr); sys.exit(3)"])
        self.assertEqual(result.stdout, "to stdout\n")
        self.assertEqual(result.stderr, "to stderr\n")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.error, "")

    def test_real_runner_records_a_launch_failure_instead_of_raising(self):
        result = make_checkpoint.run_command(
            [os.path.join(self.directory.name, "no-such-program")])
        self.assertIsNone(result.returncode)
        self.assertIn("launch failed", result.error)

    def test_return_codes_are_preserved_in_every_record(self):
        runner = FakeRunner(self.manifest, self_test_rc=1,
                            self_test_all_passed=False, conformance_rc=1,
                            all_gates_pass=False, git_head_rc=128)
        code, out, _err = self.run_main("codes", runner=runner)
        self.assertEqual(code, 1)
        state = self.read_json("codes", "state.json")
        self.assertEqual(state["self_test_returncode"], 1)
        self.assertEqual(state["conformance_returncode"], 1)
        self.assertEqual(state["conformance"]["returncode"], 1)
        self.assertFalse(state["self_test_all_passed"])
        self.assertFalse(state["conformance_all_gates_pass"])
        self.assertFalse(state["checkpoint_passed"])
        self.assertEqual(state["git"]["returncodes"]["head"], 128)
        self.assertEqual(state["git"]["returncodes"]["status"], 0)
        self.assertEqual(state["git"]["commit"], "")
        by_name = {item["name"]: item["returncode"]
                   for item in state["commands"]}
        self.assertEqual(by_name["self_test"], 1)
        self.assertEqual(by_name["conformance"], 1)
        self.assertEqual(by_name["git_head"], 128)
        self.assertEqual(by_name["git_tracked"], 0)
        self.assertEqual(self.read_json("codes", "test-report.json")["returncode"], 1)
        self.assertEqual(self.read_json("codes", "conformance.json")["returncode"], 1)
        self.assertIn("rc=1", out)

    def test_slug_must_be_a_bounded_identifier(self):
        for bad in ("../escape", ".hidden", "a/b", "a b", "", "x" * 65,
                    "-dash", "a\\b", "tab\there"):
            with self.assertRaises(make_checkpoint.CheckpointRefused):
                make_checkpoint.validate_slug(bad)
        for good in ("checkpoint", "a", "x" * 64, "2026.09.13_rev-2"):
            self.assertEqual(make_checkpoint.validate_slug(good), good)
        for bad in ("../escape", ".hidden", "a/b", "a b", "x" * 65):
            code, out, err = self.run_main(bad)
            self.assertEqual(code, 2, bad)
            self.assertIn("refused", err)
            self.assertEqual(out, "")
        self.assertEqual(self.runner.calls, [])
        self.assertEqual(os.listdir(self.root), [])

    def test_target_is_confined_to_the_checkpoints_directory(self):
        target = make_checkpoint.checkpoint_target(self.root, DATE, "fine")
        self.assertTrue(target.startswith(os.path.realpath(self.root)))
        self.assertEqual(os.path.basename(target), f"{DATE}-fine")

    def test_invalid_date_is_refused(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            code = make_checkpoint.main(
                ["ok", "--checkpoints-dir", self.root, "--date", "13/09/2026"],
                runner=self.runner)
        self.assertEqual(code, 2)
        self.assertIn("refused", stderr.getvalue())
        self.assertEqual(self.runner.calls, [])

    def test_existing_target_is_refused_and_left_alone(self):
        existing = self.target("taken")
        existing.mkdir()
        (existing / "keep.txt").write_text("do not touch\n", encoding="utf-8")
        code, out, err = self.run_main("taken")
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual(out, "")
        self.assertEqual(self.runner.calls, [])
        self.assertEqual(os.listdir(existing), ["keep.txt"])
        self.assertEqual((existing / "keep.txt").read_text(encoding="utf-8"),
                         "do not touch\n")

    def test_parse_failure_is_a_recorded_failure_not_unknown(self):
        runner = FakeRunner(
            self.manifest, self_test_rc=0,
            self_test_stdout="Traceback (most recent call last):\n  boom\n")
        code, out, _err = self.run_main("noparse", runner=runner)
        self.assertEqual(code, 1)
        report = self.read_json("noparse", "test-report.json")
        self.assertIsNone(report["summary"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["returncode"], 0)
        self.assertTrue(report["parse_error"])
        self.assertIn("still running", report["stderr_tail"])
        self.assertIn("Traceback", report["stdout_tail"])
        state = self.read_json("noparse", "state.json")
        self.assertFalse(state["self_test_all_passed"])
        self.assertFalse(state["self_test_run_passed"])
        self.assertIsNone(state["self_test_passed"])
        self.assertEqual(state["self_test_parse_error"], report["parse_error"])
        self.assertFalse(state["checkpoint_passed"])
        raw_state = (self.target("noparse") / "state.json").read_text(
            encoding="utf-8")
        self.assertNotIn("unknown", raw_state)
        self.assertIn("parse_error", out)
        self.assertIn("FAILED", out)
        snapshot = (self.target("noparse") / "SNAPSHOT.md").read_text(
            encoding="utf-8")
        self.assertIn("FAILED to parse", snapshot)

    def test_json_after_a_stray_stdout_line_still_parses(self):
        runner = FakeRunner(
            self.manifest,
            self_test_stdout="stray progress line\n"
                             + json.dumps(SELF_TEST_SUMMARY, indent=1) + "\n")
        code, _out, _err = self.run_main("stray", runner=runner)
        self.assertEqual(code, 0)
        report = self.read_json("stray", "test-report.json")
        self.assertEqual(report["summary"], SELF_TEST_SUMMARY)
        self.assertEqual(report["parse_mode"], "last_object_in_stdout")

    def test_conformance_json_is_written_with_manifest_and_text(self):
        code, _out, _err = self.run_main("gates")
        self.assertEqual(code, 0)
        record = self.read_json("gates", "conformance.json")
        self.assertEqual(record["returncode"], 0)
        self.assertTrue(record["passed"])
        self.assertTrue(record["all_gates_pass"])
        self.assertEqual(record["manifest_source"], "manifest_file")
        self.assertEqual(record["manifest_path"], self.manifest)
        self.assertEqual(record["manifest"]["record_type"],
                         "architecture_conformance/v1")
        self.assertIn("ZERO-TOLERANCE", record["stdout"])
        self.assertFalse(record["stdout_truncated"])
        self.assertEqual(record["parse_error"], "")
        self.assertEqual(record["command"][-3:],
                         ["--conformance", "--format", "json"])

    def test_conformance_json_on_stdout_is_honored_first(self):
        manifest = {"record_type": "architecture_conformance/v1",
                    "all_gates_pass": True}
        runner = FakeRunner(self.manifest, write_manifest=False)
        conformance_stdout = json.dumps(manifest)

        def stdout_json_runner(command, *, env=None, timeout=None):
            if "--conformance" in command:
                return {"returncode": 0, "stdout": conformance_stdout,
                        "stderr": ""}
            return runner(command, env=env, timeout=timeout)

        code, _out, _err = self.run_main("stdoutjson", runner=stdout_json_runner)
        self.assertEqual(code, 0)
        record = self.read_json("stdoutjson", "conformance.json")
        self.assertEqual(record["manifest_source"], "stdout")
        self.assertEqual(record["manifest"], manifest)

    def test_stale_manifest_is_refused(self):
        with open(self.manifest, "w", encoding="utf-8") as handle:
            json.dump({"record_type": "architecture_conformance/v1",
                       "all_gates_pass": True}, handle)
        old = time.time() - 100
        os.utime(self.manifest, (old, old))
        runner = FakeRunner(self.manifest, write_manifest=False)
        code, out, _err = self.run_main("stale", runner=runner)
        self.assertEqual(code, 1)
        record = self.read_json("stale", "conformance.json")
        self.assertIsNone(record["manifest"])
        self.assertIn("predates this run", record["parse_error"])
        self.assertEqual(record["returncode"], 0)
        self.assertFalse(record["passed"])
        self.assertIsNone(record["all_gates_pass"])
        self.assertIn("NO MANIFEST", out)

    def test_exit_status_is_zero_only_when_both_suites_pass(self):
        self.assertEqual(self.run_main("both")[0], 0)
        self.assertTrue(self.read_json("both", "state.json")["checkpoint_passed"])
        failing_gates = FakeRunner(self.manifest, conformance_rc=1,
                                   all_gates_pass=False)
        self.assertEqual(self.run_main("gatesfail", runner=failing_gates)[0], 1)
        state = self.read_json("gatesfail", "state.json")
        self.assertTrue(state["self_test_run_passed"])
        self.assertFalse(state["conformance_run_passed"])
        self.assertEqual(state["exit_status"], 1)
        failing_tests = FakeRunner(self.manifest, self_test_rc=1,
                                   self_test_all_passed=False)
        self.assertEqual(self.run_main("testsfail", runner=failing_tests)[0], 1)
        # A zero return code with a false all_passed flag is still a failure.
        contradictory = FakeRunner(self.manifest, self_test_rc=0,
                                   self_test_all_passed=False)
        self.assertEqual(self.run_main("contradict", runner=contradictory)[0], 1)

    def test_git_state_records_untracked_paths_and_the_tree_note(self):
        self.run_main("git")
        target = self.target("git")
        state = self.read_json("git", "state.json")
        self.assertEqual(state["git"]["branch"], "main")
        self.assertEqual(state["git"]["commit"], GIT_HEAD.strip())
        self.assertEqual(state["git"]["untracked_paths"], ["notes.txt"])
        self.assertEqual(state["git"]["untracked_count"], 1)
        self.assertEqual(state["git"]["tracked_count"], 2)
        self.assertIn("tracked files only", state["git"]["tree_note"])
        self.assertEqual((target / "tree.txt").read_text(encoding="utf-8"),
                         GIT_TRACKED)
        self.assertEqual((target / "untracked.txt").read_text(encoding="utf-8"),
                         GIT_UNTRACKED)
        git_state = (target / "git-state.txt").read_text(encoding="utf-8")
        self.assertIn("## main...origin/main", git_state)
        self.assertIn("commit: " + GIT_HEAD.strip(), git_state)
        self.assertIn("untracked paths (git ls-files --others "
                      "--exclude-standard, rc=0): 1", git_state)
        self.assertIn("notes.txt", git_state)
        self.assertIn("note: tree.txt lists tracked files only", git_state)
        commands = self.runner.commands()
        self.assertIn(["git", "status", "--short", "--branch"], commands)
        self.assertIn(["git", "rev-parse", "HEAD"], commands)
        self.assertIn(["git", "ls-files"], commands)
        self.assertIn(["git", "ls-files", "--others", "--exclude-standard"],
                      commands)
        snapshot = (target / "SNAPSHOT.md").read_text(encoding="utf-8")
        self.assertIn("tracked files only", snapshot)
        self.assertIn("1 untracked path(s)", snapshot)

    def test_every_documented_file_is_written(self):
        self.run_main("files")
        self.assertEqual(sorted(os.listdir(self.target("files"))),
                         sorted(make_checkpoint.CHECKPOINT_FILES))
        self.assertEqual(self.read_json("files", "state.json")["files"],
                         list(make_checkpoint.CHECKPOINT_FILES))

    def test_summary_is_one_line(self):
        code, out, err = self.run_main("oneline")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        lines = out.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith(f"checkpoint {DATE}-oneline:"))
        self.assertIn("self-test 12/12 rc=0 PASSED", lines[0])
        self.assertIn("conformance rc=0 ALL GATES PASS", lines[0])
        self.assertIn("exit 0", lines[0])

    def test_dry_run_validates_and_prints_without_running_anything(self):
        code, out, err = self.run_main("preview", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(self.runner.calls, [])
        self.assertFalse(self.target("preview").exists())
        self.assertEqual(os.listdir(self.root), [])
        self.assertIn(f"would create {self.target('preview')}", out)
        self.assertIn("--self-test --format json", out)
        self.assertIn("--conformance --format json", out)
        self.assertIn("git ls-files --others --exclude-standard", out)
        for name in make_checkpoint.CHECKPOINT_FILES:
            self.assertIn(name, out)
        self.assertIn("nothing was written", out)

    def test_dry_run_still_refuses_a_bad_slug_or_existing_target(self):
        code, _out, err = self.run_main("../escape", "--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("refused", err)
        self.target("exists").mkdir()
        code, _out, err = self.run_main("exists", "--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual(self.runner.calls, [])

    def test_module_attribute_runner_is_used_when_none_is_passed(self):
        original = make_checkpoint.COMMAND_RUNNER
        make_checkpoint.COMMAND_RUNNER = self.runner
        self.addCleanup(setattr, make_checkpoint, "COMMAND_RUNNER", original)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = make_checkpoint.main(
                ["attr", "--checkpoints-dir", self.root, "--date", DATE])
        self.assertEqual(code, 0)
        self.assertTrue(any("--self-test" in command
                            for command in self.runner.commands()))


if __name__ == "__main__":
    unittest.main()
