"""The pre-push summary never lets a skipped gate or a missing command pass for a checked one.

tools/pre_push_summary.py prints the table of a tools/pre_push_check.sh run. These rules hold it to four promises on
small scratch run folders: a failure fails the run, a gate that exits 127 is reported as a command missing from the
local environment (neither a pass nor a code failure, exit 3), everything continuous integration runs that the run did
not is listed as a warning, and the last line says NOT EQUIVALENT TO CI whenever that list is not empty. A step with
nothing to check is not a gap, and a local gate never makes a run equivalent.

The script-level rule reproduces the failure of September 27, 2026: the steps the script copies from the workflow call
`python`, a tree without .venv falls back to python3, and on a machine with no `python` two gates exited 127 and were
reported as failures of the code. It runs the script on a scratch tree whose only step calls `python`, with a PATH that
holds no `python`: the script's shim folder makes the step pass, and a copy of the script without the shim reports the
missing command, not a failure.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import pre_push_summary as summary  # noqa: E402

WORKFLOW = """\
jobs:
  unit-tests:
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
  runtime-checks:
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
"""
#: The commands the pre-push script itself needs, and nothing named python.
SCRIPT_COMMANDS = ("bash", "sh", "env", "git", "date", "mkdir", "sed", "sort", "cut", "tr", "grep", "cat", "chmod",
                   "dirname", "head", "rm", "ls")
#: A scratch workflow whose one mirrored step calls `python` as the real workflow's steps do.
SCRATCH_WORKFLOW = """\
jobs:
  docs:
    steps:
      - name: Validate benchmark registry
        run: |
          python -c "print('the registry step ran')"
"""


class SummaryTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory(prefix="pre-push-summary-")
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)
        self.workflow = self.folder / "ci.yml"
        self.workflow.write_text(WORKFLOW, encoding="utf-8")

    def write(self, results=(), declined=(), local=(), logs=None):
        (self.folder / "results.txt").write_text("".join(f"{code} {seconds} {name}\n"
                                                         for code, seconds, name in results), encoding="utf-8")
        (self.folder / "declined.txt").write_text("".join(f"{step} | {reason}\n" for step, reason in declined),
                                                  encoding="utf-8")
        (self.folder / "local.txt").write_text("".join(f"{name}\n" for name in local), encoding="utf-8")
        for name, text in (logs or {}).items():
            (self.folder / f"{name}.log").write_text(text, encoding="utf-8")

    def run_summary(self, **options):
        options.setdefault("workflow", self.workflow)
        lines, status = summary.summarize(self.folder, **options)
        return "\n".join(lines), lines[-1], status

    def test_a_run_that_covers_everything_on_the_one_workflow_version_is_equivalent(self):
        self.workflow.write_text(WORKFLOW.replace('"3.10", "3.11", "3.12"', '"3.12"'), encoding="utf-8")
        self.write(results=[(0, 12, "self-test"), (0, 3, "benchmark-registry")],
                   declined=[("Check public language", "nothing to check: no Markdown file differs from origin/main")])
        text, last, status = self.run_summary(python="3.12")
        self.assertEqual(status, 0)
        self.assertEqual(last, "RESULT: all 2 gates passed; equivalent to CI")
        self.assertNotIn("WARNING", text)

    def test_a_failed_gate_fails_the_run_and_shows_its_failing_lines(self):
        self.write(results=[(0, 12, "self-test"), (1, 40, "tools-shard-a")],
                   logs={"tools-shard-a": "ok\nFAIL: test_something (test_module.Case)\nmore\n"})
        text, last, status = self.run_summary(python="3.12")
        self.assertEqual(status, 1)
        self.assertIn("  FAIL     40s  tools-shard-a  (exit 1", text)
        self.assertIn("          FAIL: test_something (test_module.Case)", text)
        self.assertTrue(last.startswith("RESULT: 1 of 2 gates FAILED; NOT EQUIVALENT TO CI"), last)

    def test_known_wrong_exit_127_is_a_missing_command_not_a_failure_and_not_a_pass(self):
        self.write(results=[(0, 12, "self-test"), (127, 0, "benchmark-registry")],
                   logs={"benchmark-registry": "step.sh: line 2: python: command not found\n"})
        text, last, status = self.run_summary(python="3.12")
        self.assertEqual(status, 3)
        row = next(line for line in text.splitlines() if "benchmark-registry" in line)
        self.assertIn(summary.NOT_FOUND_NOTE, row)
        self.assertEqual(row.split()[0], "----", "the status column says neither pass nor FAIL")
        self.assertIn("python: command not found", text)
        self.assertIn(f"benchmark-registry: {summary.NOT_FOUND_NOTE}", text)
        self.assertIn("could not run", last)
        self.assertIn("NOT EQUIVALENT TO CI (1 skipped in this run", last)

    def test_a_failure_outranks_a_missing_command(self):
        self.write(results=[(1, 5, "examples"), (127, 0, "benchmark-registry")])
        _text, last, status = self.run_summary(python="3.12")
        self.assertEqual(status, 1)
        self.assertTrue(last.startswith("RESULT: 1 of 2 gates FAILED"), last)

    def test_known_wrong_a_missing_tool_or_only_or_a_dirty_tree_is_not_equivalent(self):
        cases = {
            "vale": dict(declined=[("Check public language", "vale is not installed; continuous integration runs it")]),
            "only": dict(only=("self-test",)),
            "dirty": dict(dirty=True),
        }
        for name, case in cases.items():
            with self.subTest(case=name):
                self.workflow.write_text(WORKFLOW.replace('"3.10", "3.11", "3.12"', '"3.12"'), encoding="utf-8")
                self.write(results=[(0, 12, "self-test")], declined=case.get("declined", ()))
                text, last, status = self.run_summary(python="3.12", only=case.get("only", ()),
                                                      dirty=case.get("dirty", False))
                self.assertEqual(status, 0)
                self.assertIn("WARNING: continuous integration runs these, and this run skipped them:", text)
                self.assertEqual(last, "RESULT: all 1 gates passed; NOT EQUIVALENT TO CI (1 skipped in this run, 0 "
                                       "only in continuous integration; listed above)")

    def test_steps_a_local_run_never_covers_are_listed_apart_and_still_not_equivalent(self):
        self.write(results=[(0, 12, "self-test")],
                   declined=[("Product solve acceptance", "continuous integration only: needs Docker")])
        text, last, status = self.run_summary(python="3.12")
        self.assertEqual(status, 0)
        self.assertNotIn("WARNING", text)
        self.assertIn("Continuous integration also runs these, which a local run never covers:", text)
        self.assertIn("  - Product solve acceptance: needs Docker", text)
        self.assertIn("  - every gate here ran on Python 3.12; continuous integration also runs 3.10, 3.11", text)
        self.assertIn("NOT EQUIVALENT TO CI (0 skipped in this run, 2 only in continuous integration", last)

    def test_a_local_gate_is_marked_and_never_counts_as_coverage(self):
        self.workflow.write_text(WORKFLOW.replace('"3.10", "3.11", "3.12"', '"3.12"'), encoding="utf-8")
        self.write(results=[(0, 30, "pristine-tree"), (127, 0, "pristine-manifest")],
                   local=["pristine-tree", "pristine-manifest"])
        text, last, status = self.run_summary(python="3.12")
        self.assertIn("pristine-tree  (local only)", text)
        self.assertEqual(status, 3)
        self.assertNotIn("skipped them", text)
        self.assertIn("equivalent to CI", last)

    def test_an_unreadable_workflow_is_a_gap_not_silence(self):
        self.write(results=[(0, 12, "self-test")])
        _text, last, _status = self.run_summary(python="3.12", workflow=self.folder / "absent.yml")
        self.assertIn("NOT EQUIVALENT TO CI (1 skipped in this run", last)


class ShimTests(unittest.TestCase):
    """The pre-push script on a scratch tree whose one step calls `python`, on a PATH without any python."""

    @classmethod
    def setUpClass(cls):
        missing = [name for name in SCRIPT_COMMANDS if not shutil.which(name)]
        if missing:
            raise unittest.SkipTest(f"this machine lacks {', '.join(missing)}")
        holder = tempfile.TemporaryDirectory(prefix="pre-push-shim-")
        cls.addClassCleanup(holder.cleanup)
        cls.home = Path(holder.name)
        cls.tree = cls.home / "tree"
        (cls.tree / ".github" / "workflows").mkdir(parents=True)
        (cls.tree / ".github" / "workflows" / "ci.yml").write_text(SCRATCH_WORKFLOW, encoding="utf-8")
        (cls.tree / "tools").mkdir()
        for name in ("run_test_shard.py", "ci_test_shards.json", "pre_push_summary.py", "pre_push_check.sh"):
            shutil.copy2(ROOT / "tools" / name, cls.tree / "tools" / name)
        # Only the commands the script needs, each linked by name, and nothing called python.
        cls.bin = cls.home / "bin"
        cls.bin.mkdir()
        for name in SCRIPT_COMMANDS:
            os.symlink(shutil.which(name), cls.bin / name)
        # The interpreter as a tree without .venv finds it: python3 alone in its folder.
        cls.interpreter = cls.home / "interpreter" / "python3"
        cls.interpreter.parent.mkdir()
        cls.interpreter.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        cls.interpreter.chmod(0o755)

    def run_script(self, script: Path):
        # Each run has its own home, so two runs in the same second never share a run folder, and git looks for no
        # repository above the scratch tree.
        home = self.home / f"user-{script.stem}"
        home.mkdir(exist_ok=True)
        environment = {"PATH": str(self.bin), "HOME": str(home), "PY": str(self.interpreter), "LANG": "C.UTF-8",
                       "GIT_CEILING_DIRECTORIES": str(self.home)}
        return subprocess.run([str(self.bin / "bash"), str(script), "--tree", str(self.tree), "--only",
                               "benchmark-registry"], env=environment, capture_output=True, text=True, timeout=300,
                              check=False)

    def test_the_path_of_this_test_holds_no_python(self):
        self.assertEqual([path.name for path in self.bin.iterdir() if path.name.startswith("python")], [])

    def test_a_copied_step_that_calls_python_runs_through_the_shim(self):
        completed = self.run_script(self.tree / "tools" / "pre_push_check.sh")
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertRegex(output, r"  pass +\d+s  benchmark-registry")
        self.assertIn("NOT EQUIVALENT TO CI", output.splitlines()[-1])

    def test_known_wrong_without_the_shim_the_step_is_a_missing_command_not_a_code_failure(self):
        text = (self.tree / "tools" / "pre_push_check.sh").read_text(encoding="utf-8")
        broken = text.replace('gate_path="$shim:', 'gate_path="', 1)
        self.assertNotEqual(broken, text, "the script no longer puts the shim on the gates' PATH")
        script = self.home / "without-shim.sh"
        script.write_text(broken, encoding="utf-8")
        completed = self.run_script(script)
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 3, output)
        row = next(line for line in output.splitlines() if "benchmark-registry" in line and "exit 127" in line)
        self.assertIn(summary.NOT_FOUND_NOTE, row)
        self.assertEqual(row.split()[0], "----", "the status column says neither pass nor FAIL")


if __name__ == "__main__":
    unittest.main()
