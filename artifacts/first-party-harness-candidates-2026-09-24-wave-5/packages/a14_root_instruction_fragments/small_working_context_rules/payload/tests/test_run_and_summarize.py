"""Tests for scripts/run_and_summarize.py. Effects: writes files only inside temporary folders and starts the script and small Python commands with the running Python; no network."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "run_and_summarize.py"
DEFAULT_OUTPUT = Path(".baltor") / "state" / "small-working-context-rules" / "out.txt"


class RunAndSummarize(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    def helper(self, *arguments, timeout=60):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                                  capture_output=True, text=True, timeout=timeout)
        return finished.returncode, json.loads(finished.stdout)

    def python(self, code: str) -> list:
        """A Python command with unbuffered output, so its lines keep their order in the saved file."""
        return ["--", sys.executable, "-I", "-B", "-u", "-c", code]

    def test_long_passing_output_is_saved_and_summarized(self):
        status, answer = self.helper(*self.python("for n in range(1, 501): print('line', n)"))
        self.assertEqual((status, answer["result"], answer["exit_code"]), (0, "exited", 0), answer)
        self.assertEqual(answer["output_file"], DEFAULT_OUTPUT.as_posix())
        self.assertEqual(answer["output_lines"], 500)
        self.assertEqual(len(answer["tail"]), 40)
        self.assertEqual((answer["tail"][0], answer["tail"][-1]), ("line 461", "line 500"))
        self.assertEqual(answer["error_lines"], [])
        saved = (self.root / DEFAULT_OUTPUT).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(saved), 500)

    def test_failure_names_the_error_lines_with_their_numbers(self):
        """Known-wrong case: a failing test log where the error sits far from the first lines."""
        code = ("import sys\n"
                "for n in range(300): print('ok', n)\n"
                "print('ERROR: test_parse_dates failed', file=sys.stderr)\n"
                "print('Traceback (most recent call last):')\n"
                "for n in range(60): print('detail', n)\n"
                "sys.exit(3)")
        status, answer = self.helper(*self.python(code))
        self.assertEqual((status, answer["exit_code"], answer["result"]), (1, 3, "exited"), answer)
        self.assertEqual(answer["error_lines"], ["301: ERROR: test_parse_dates failed",
                                                 "302: Traceback (most recent call last):"])
        self.assertNotIn("ok 0", answer["tail"])
        self.assertIn("Read error_lines first", answer["next"])

    def test_long_lines_are_cut(self):
        status, answer = self.helper(*self.python("print('x' * 5000)"))
        self.assertEqual(status, 0)
        self.assertEqual(len(answer["tail"][0]), 300)
        self.assertEqual(answer["saved_bytes"], 5001)

    def test_save_path_for_the_run_ledger_is_accepted(self):
        target = ".baltor/state/unattended-run-rules/ABC-12-checks.txt"
        status, answer = self.helper("--save", target, *self.python("print('Ran 4 tests'); print('OK')"))
        self.assertEqual((status, answer["output_file"]), (0, target), answer)
        self.assertEqual((self.root / target).read_text(encoding="utf-8"), "Ran 4 tests\nOK\n")

    def test_save_path_outside_the_state_folder_is_refused(self):
        """Known-wrong case: the helper is asked to write over a project file."""
        for target in ("src/app.py", "../outside.txt", "/tmp/out.txt", ".baltor/out.txt", ".baltor/state"):
            status, answer = self.helper("--save", target, *self.python("print('overwritten')"))
            self.assertEqual((status, answer["code"]), (2, "save_path_refused"), target)
        self.assertEqual((self.root / "src" / "app.py").read_text(encoding="utf-8"), "x = 1\n")

    def test_state_folder_that_is_a_link_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            (self.root / ".baltor").mkdir()
            os.symlink(other, self.root / ".baltor" / "state")
            status, answer = self.helper(*self.python("print('x')"))
            self.assertEqual((status, answer["code"]), (2, "save_path_refused"))
            self.assertEqual(os.listdir(other), [])

    def test_missing_command_and_unknown_program_are_refused(self):
        status, answer = self.helper()
        self.assertEqual((status, answer["code"]), (2, "command_missing"))
        status, answer = self.helper("--")
        self.assertEqual((status, answer["code"]), (2, "command_missing"))
        status, answer = self.helper("--", "no-such-program-for-this-test")
        self.assertEqual((status, answer["code"]), (2, "command_not_started"))

    def test_command_that_runs_too_long_is_stopped(self):
        began = time.monotonic()
        status, answer = self.helper("--timeout", "1", *self.python("import time; print('started', flush=True); "
                                                                    "time.sleep(30)"))
        self.assertLess(time.monotonic() - began, 20)
        self.assertEqual((status, answer["result"]), (1, "timed_out"), answer)
        self.assertEqual(answer["tail"], ["started"])

    def test_instruction_section_names_this_script(self):
        text = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("python3 -I -B .baltor/small-working-context-rules/scripts/run_and_summarize.py --", text)
        self.assertIn("sed -n '200,319p' FILE", text)
        self.assertIn("tail -n 40 FILE", text)
        self.assertEqual((PACKAGE / "GEMINI.md").read_bytes(), (PACKAGE / "AGENTS.md").read_bytes())
        self.assertEqual((PACKAGE / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")


if __name__ == "__main__":
    unittest.main()
