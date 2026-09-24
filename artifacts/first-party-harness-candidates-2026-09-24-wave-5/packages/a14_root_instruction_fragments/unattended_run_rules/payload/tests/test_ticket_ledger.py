"""Tests for scripts/ticket_ledger.py. Effects: writes files only inside temporary folders and starts the script with the running Python; no network."""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "ticket_ledger.py"
STATE = Path(".baltor") / "state" / "unattended-run-rules"
LEDGER = STATE / "ledger.jsonl"


def run(root: Path, *arguments: str):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(root)],
                              capture_output=True, text=True, timeout=60)
    return finished.returncode, json.loads(finished.stdout)


class TicketLedger(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / "AGENTS.md").write_text("# Project rules\n", encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    def evidence(self, name: str, text: str = "Ran 4 tests\nOK\n") -> str:
        """Write one evidence file in the state folder and return its workspace-relative path."""
        path = self.root / STATE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return (STATE / name).as_posix()

    def lines(self):
        return [json.loads(line) for line in (self.root / LEDGER).read_text(encoding="utf-8").splitlines()]

    def test_one_ticket_from_start_to_done(self):
        status, answer = run(self.root, "start", "--ticket", "ABC-12")
        self.assertEqual((status, answer["result"]), (0, "started"))
        proof = self.evidence("ABC-12-checks.txt")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done",
                             "--summary", "Fixed the date parser", "--evidence", proof)
        self.assertEqual((status, answer["result"]), (0, "finished"), answer)
        status, answer = run(self.root, "status")
        self.assertEqual(status, 0)
        self.assertIsNone(answer["open_ticket"])
        self.assertEqual(answer["finished"], {"done": 1, "blocked": 0, "skipped": 0})
        self.assertEqual(answer["finished_tickets"], [{"ticket": "ABC-12", "status": "done"}])
        self.assertEqual([line["event"] for line in self.lines()], ["start", "finish"])
        self.assertEqual(self.lines()[1]["evidence"], [proof])

    def test_status_before_any_ticket_writes_nothing(self):
        status, answer = run(self.root, "status")
        self.assertEqual((status, answer["open_ticket"], answer["finished_tickets"]), (0, None, []))
        self.assertFalse((self.root / ".baltor").exists())

    def test_second_ticket_while_one_is_open_is_refused(self):
        """Known-wrong case: starting a second ticket before the first one is finished."""
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "start", "--ticket", "ABC-13")
        self.assertEqual((status, answer["code"]), (1, "another_ticket_open"))
        self.assertIn("Finish the open ticket first", answer["next"])
        self.assertEqual(len(self.lines()), 1)

    def test_same_open_ticket_again_points_to_the_earlier_attempt(self):
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "start", "--ticket", "ABC-12")
        self.assertEqual((status, answer["code"]), (1, "ticket_already_open"))

    def test_done_without_evidence_is_refused(self):
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed")
        self.assertEqual((status, answer["code"]), (1, "done_without_evidence"))
        self.assertIn(".baltor/state/unattended-run-rules/ABC-12-checks.txt", answer["next"])

    def test_instruction_file_as_evidence_is_refused(self):
        """Known-wrong case: the model names the instruction file itself as proof of passing checks."""
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", "AGENTS.md")
        self.assertEqual((status, answer["code"]), (1, "evidence_outside_state_folder"))
        self.assertEqual(len(self.lines()), 1)

    def test_link_in_the_state_folder_to_a_workspace_file_is_refused(self):
        run(self.root, "start", "--ticket", "ABC-12")
        os.symlink(self.root / "AGENTS.md", self.root / STATE / "ABC-12-checks.txt")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", (STATE / "ABC-12-checks.txt").as_posix())
        self.assertEqual((status, answer["code"]), (1, "evidence_outside_state_folder"))

    def test_the_ledger_itself_is_not_evidence(self):
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", LEDGER.as_posix())
        self.assertEqual((status, answer["code"]), (1, "evidence_is_ledger"))

    def test_evidence_written_before_the_ticket_started_is_refused(self):
        proof = self.evidence("ABC-12-checks.txt")
        an_hour_ago = time.time() - 3600
        os.utime(self.root / proof, (an_hour_ago, an_hour_ago))
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", proof)
        self.assertEqual((status, answer["code"]), (1, "evidence_older_than_ticket"))

    def test_evidence_of_an_earlier_ticket_is_refused(self):
        """Known-wrong case: one test log is offered as the proof for two tickets."""
        run(self.root, "start", "--ticket", "ABC-12")
        proof = self.evidence("checks.txt")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", proof)
        self.assertEqual(status, 0, answer)
        run(self.root, "start", "--ticket", "ABC-13")
        self.evidence("checks.txt", "Ran 4 tests\nOK\nrewritten\n")
        status, answer = run(self.root, "finish", "--ticket", "ABC-13", "--status", "done", "--summary", "Fixed",
                             "--evidence", proof)
        self.assertEqual((status, answer["code"]), (1, "evidence_reused"))

    def test_empty_evidence_file_is_refused(self):
        run(self.root, "start", "--ticket", "ABC-12")
        proof = self.evidence("ABC-12-checks.txt", "")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "Fixed",
                             "--evidence", proof)
        self.assertEqual((status, answer["code"]), (1, "evidence_missing"))

    def test_blocked_needs_what_is_needed(self):
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "blocked",
                             "--summary", "The fixture file is missing")
        self.assertEqual((status, answer["code"]), (1, "blocked_without_needs"))
        answer_file = self.evidence("ABC-12-git.json", '{"result": "fail"}\n')
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "blocked",
                             "--summary", "The fixture file is missing",
                             "--needs", "The ticket author must attach the sample input", "--evidence", answer_file)
        self.assertEqual((status, answer["status"]), (0, "blocked"))
        self.assertEqual(self.lines()[1]["evidence"], [answer_file])

    def test_finished_ticket_cannot_start_again(self):
        run(self.root, "start", "--ticket", "ABC-12")
        run(self.root, "finish", "--ticket", "ABC-12", "--status", "skipped", "--summary", "Out of scope tonight")
        status, answer = run(self.root, "start", "--ticket", "ABC-12")
        self.assertEqual((status, answer["code"]), (1, "ticket_already_finished"))
        self.assertIn("next ticket on the host's list", answer["next"])

    def test_finishing_a_ticket_that_is_not_open_is_refused(self):
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "skipped", "--summary", "x")
        self.assertEqual((status, answer["code"]), (1, "no_open_ticket"))
        self.assertIn("start --ticket ABC-12", answer["next"])
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-99", "--status", "skipped", "--summary", "x")
        self.assertEqual((status, answer["code"]), (1, "ticket_not_open"))

    def test_evidence_outside_the_workspace_is_refused(self):
        run(self.root, "start", "--ticket", "ABC-12")
        proof = self.evidence("ABC-12-checks.txt")
        for value in ("../outside.txt", str(self.root / proof)):
            status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "x",
                                 "--evidence", value)
            self.assertEqual((status, answer["code"]), (2, "evidence_path_unsafe"), value)

    def test_evidence_link_that_leaves_the_workspace_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            target = Path(other) / "log.txt"
            target.write_text("OK\n", encoding="utf-8")
            run(self.root, "start", "--ticket", "ABC-12")
            os.symlink(target, self.root / STATE / "link.txt")
            status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "done", "--summary", "x",
                                 "--evidence", (STATE / "link.txt").as_posix())
            self.assertEqual((status, answer["code"]), (2, "evidence_path_unsafe"))

    def test_bad_ticket_key_and_bad_summary_are_refused(self):
        status, answer = run(self.root, "start", "--ticket", "../ABC")
        self.assertEqual((status, answer["code"]), (2, "ticket_invalid"))
        run(self.root, "start", "--ticket", "ABC-12")
        status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "skipped",
                             "--summary", "two\nlines")
        self.assertEqual((status, answer["code"]), (2, "text_invalid"))

    def test_unreadable_ledger_is_refused(self):
        (self.root / LEDGER).parent.mkdir(parents=True)
        (self.root / LEDGER).write_text("{not json\n", encoding="utf-8")
        status, answer = run(self.root, "status")
        self.assertEqual((status, answer["code"]), (2, "ledger_unreadable"))
        self.assertTrue(answer["stop_run"])

    def test_state_folder_that_is_a_link_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            (self.root / ".baltor").mkdir()
            os.symlink(other, self.root / ".baltor" / "state")
            status, answer = run(self.root, "start", "--ticket", "ABC-12")
            self.assertEqual((status, answer["code"]), (2, "unsafe_state_path"))
            self.assertEqual(os.listdir(other), [])

    def test_missing_arguments_answer_with_json(self):
        status, answer = run(self.root, "finish", "--ticket", "ABC-12")
        self.assertEqual((status, answer["code"]), (2, "arguments_invalid"))
        self.assertFalse(answer["stop_run"])

    @unittest.skipIf(fcntl is None, "the fcntl module is missing on this system")
    def test_busy_ledger_is_refused_without_a_write(self):
        """Known-wrong case: a second harness writes while another ledger command holds the lock."""
        run(self.root, "start", "--ticket", "ABC-12")
        before = (self.root / LEDGER).read_bytes()
        descriptor = os.open(self.root / STATE / "ledger.lock", os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            status, answer = run(self.root, "finish", "--ticket", "ABC-12", "--status", "skipped",
                                 "--summary", "x", "--lock-timeout", "0.3")
        finally:
            os.close(descriptor)
        self.assertEqual((status, answer["code"], answer["stop_run"]), (1, "ledger_busy", False))
        self.assertEqual((self.root / LEDGER).read_bytes(), before)

    def test_two_starts_at_the_same_moment_keep_one_ticket_open(self):
        """Two harnesses start different tickets at once; exactly one opens and the ledger stays readable."""
        for attempt in range(12):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                processes = [subprocess.Popen([sys.executable, "-I", "-B", str(SCRIPT), "start", "--ticket", key,
                                               "--root", str(root)], stdout=subprocess.PIPE, text=True)
                             for key in ("R-1", "R-2")]
                answers = [json.loads(process.communicate(timeout=60)[0]) for process in processes]
                self.assertEqual(sorted(answer["result"] for answer in answers), ["refused", "started"],
                                 (attempt, answers))
                status, answer = run(root, "status")
                self.assertEqual((status, answer["result"]), (0, "ok"), (attempt, answer))

    def test_instruction_section_names_this_script(self):
        text = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("python3 -I -B .baltor/unattended-run-rules/scripts/ticket_ledger.py", text)

    def test_finish_command_of_the_section_works_as_written(self):
        """The file rule 7 says to save is the file its finish command names, and the ledger accepts that command."""
        text = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        saved = re.findall(r"in the new file `([^`]+)`", text)
        command = re.findall(r"`(finish --ticket KEY --status done [^`]+)`", text)
        self.assertEqual((len(saved), len(command)), (1, 1))
        arguments = shlex.split(command[0].replace("KEY", "ABC-12").replace("WHAT CHANGED", "Fixed the parser"))
        self.assertEqual(arguments[arguments.index("--evidence") + 1], saved[0].replace("KEY", "ABC-12"))
        run(self.root, "start", "--ticket", "ABC-12")
        self.evidence(Path(saved[0].replace("KEY", "ABC-12")).name)
        status, answer = run(self.root, *arguments)
        self.assertEqual((status, answer["result"]), (0, "finished"), answer)
        self.assertEqual((PACKAGE / "GEMINI.md").read_bytes(), (PACKAGE / "AGENTS.md").read_bytes())
        self.assertEqual((PACKAGE / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")


if __name__ == "__main__":
    unittest.main()
