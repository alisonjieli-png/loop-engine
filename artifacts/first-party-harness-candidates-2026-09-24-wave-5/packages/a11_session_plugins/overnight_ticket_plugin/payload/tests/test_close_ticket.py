"""Tests for scripts/close_ticket.py, the ticket closer's only writing tool."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "close_ticket.py"
EXAMPLE = ROOT / "examples" / "night"
RESULTS = Path(".baltor/state/overnight-ticket-plugin/results")
CHECK = "python3 -m unittest tests.test_totals"


def close(root: Path, draft=None, raw: bytes | None = None) -> subprocess.CompletedProcess:
    payload = raw if raw is not None else json.dumps(draft).encode()
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(root)], input=payload,
                          capture_output=True, timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})


def make_night(root: Path) -> str:
    night = root / ".baltor" / "night"
    night.mkdir(parents=True)
    items = [{"position": index, "id": ticket, "title": f"Title of {ticket}"}
             for index, ticket in enumerate(("T-1", "T-2", "T-3"), start=1)]
    queue = json.dumps({"record_type": "night_queue/v1", "items": items}).encode()
    (night / "queue.json").write_bytes(queue)
    tickets = {"record_type": "night_tickets/v1",
               "tickets": [{"id": "T-1", "title": "Title of T-1", "acceptance_criteria": ["Totals round half up."],
                            "check": CHECK},
                           {"id": "T-2", "title": "Title of T-2", "acceptance_criteria": [], "check": ""}]}
    (night / "tickets.json").write_text(json.dumps(tickets), encoding="utf-8")
    return hashlib.sha256(queue).hexdigest()


def draft(**changes) -> dict:
    value = {"ticket_id": "T-1", "outcome": "fixed", "summary": "Rounding now uses half up for totals.",
             "evidence": [{"command": CHECK, "exit_code": 0, "observed": "OK"}],
             "changed_files": ["src/totals.py", "tests/test_totals.py"],
             "handoff": "Rounding lives in src/totals.py round_total."}
    value.update(changes)
    return value


class CloseTicketTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.digest = make_night(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def output(self, finished) -> dict:
        return json.loads(finished.stdout)

    def test_valid_fixed_draft_writes_exactly_one_record_bound_to_the_queue(self):
        finished = close(self.root, draft())
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        answer = self.output(finished)
        target = self.root / RESULTS / "T-1.json"
        self.assertTrue(target.is_file())
        self.assertEqual(answer["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
        saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(saved["record_type"], "overnight_ticket_result/v1")
        self.assertEqual((saved["queue_sha256"], saved["position"], saved["outcome"]), (self.digest, 1, "fixed"))
        self.assertRegex(saved["closed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(answer["next_ticket"], {"position": 2, "ticket_id": "T-2"})
        self.assertEqual(sorted(path.name for path in (self.root / RESULTS).iterdir()), ["T-1.json"])

    def test_fixed_with_a_failing_check_is_refused(self):
        # Known-wrong case: a small model claims fixed while its own test run failed.
        failing = [{"command": CHECK, "exit_code": 1, "observed": "1 failure"}]
        finished = close(self.root, draft(evidence=failing))
        self.assertEqual(finished.returncode, 1)
        self.assertIn("fixed_with_failing_evidence", self.output(finished)["failures"])
        self.assertFalse((self.root / RESULTS / "T-1.json").exists())

    def test_fixed_without_the_ticket_check_command_is_refused(self):
        other = [{"command": "python3 -m unittest tests.test_other", "exit_code": 0, "observed": "OK"}]
        finished = close(self.root, draft(evidence=other))
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(self.output(finished)["failures"], ["fixed_without_ticket_check"])
        spaced = [{"command": "python3  -m unittest   tests.test_totals", "exit_code": 0, "observed": "OK"}]
        self.assertEqual(close(self.root, draft(evidence=spaced)).returncode, 0)

    def test_fixed_needs_evidence_and_changed_files(self):
        finished = close(self.root, draft(evidence=[], changed_files=[]))
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(set(self.output(finished)["failures"]), {"fixed_needs_evidence", "fixed_needs_changed_files",
                                                                  "fixed_without_ticket_check"})

    def test_ticket_after_an_open_one_is_refused(self):
        finished = close(self.root, draft(ticket_id="T-2", evidence=[]))
        self.assertEqual(finished.returncode, 1)
        self.assertIn("ticket_not_next_in_queue", self.output(finished)["failures"])

    def test_existing_record_is_never_replaced(self):
        self.assertEqual(close(self.root, draft()).returncode, 0)
        target = self.root / RESULTS / "T-1.json"
        before = target.read_bytes()
        finished = close(self.root, draft(summary="A different story told later."))
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(self.output(finished)["failures"], ["record_exists"])
        self.assertEqual(target.read_bytes(), before)

    def test_writer_itself_refuses_to_replace_a_record(self):
        # The exclusive create is checked on its own, apart from the earlier existence check.
        spec = importlib.util.spec_from_file_location("closer_under_test", SCRIPT)
        closer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(closer)
        reader = closer.load_reader()
        first = {"record_type": reader.RESULT_TYPE, "ticket_id": "T-3", "summary": "first"}
        closer.write_record(reader, self.root, first)
        target = self.root / RESULTS / "T-3.json"
        before = target.read_bytes()
        with self.assertRaises(FileExistsError):
            closer.write_record(reader, self.root, {**first, "summary": "second"})
        self.assertEqual(target.read_bytes(), before)

    def test_record_problems_block_closing(self):
        (self.root / RESULTS).mkdir(parents=True)
        stale = {"record_type": "overnight_ticket_result/v1", "queue_sha256": "0" * 64, "ticket_id": "T-3",
                 "position": 3, "outcome": "fixed", "summary": "Old night.", "evidence": [], "changed_files": [],
                 "handoff": "Old.", "closed_at": "2026-09-01T01:00:00Z"}
        (self.root / RESULTS / "T-3.json").write_text(json.dumps(stale), encoding="utf-8")
        finished = close(self.root, draft())
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(self.output(finished)["failures"], ["night_state_has_problems"])

    def test_ticket_outside_the_queue_is_refused(self):
        finished = close(self.root, draft(ticket_id="T-99"))
        self.assertEqual(finished.returncode, 1)
        self.assertIn("ticket_not_in_queue", self.output(finished)["failures"])

    def test_unsafe_changed_file_paths_are_refused(self):
        for path in ("../outside.py", "/etc/hosts", "src/../../x.py", "src\\win.py"):
            finished = close(self.root, draft(changed_files=[path]))
            self.assertEqual(finished.returncode, 1, path)
            self.assertIn("unsafe_changed_file_path", self.output(finished)["failures"])

    def test_secret_shaped_text_is_refused_without_repeating_it(self):
        shaped = "sk" + "-" + "Ab12" * 6  # assembled at run time so no file at rest holds the shape
        finished = close(self.root, draft(summary=f"Used key {shaped} to call the service."))
        self.assertEqual(finished.returncode, 1)
        self.assertIn("secret_shaped_text", self.output(finished)["failures"])
        self.assertNotIn(shaped.encode(), finished.stdout)
        self.assertFalse((self.root / RESULTS).exists() and any((self.root / RESULTS).iterdir()))

    def test_skipped_with_changes_and_blocked_without_handoff_are_refused(self):
        finished = close(self.root, draft(outcome="skipped", evidence=[]))
        self.assertIn("skipped_with_changes", self.output(finished)["failures"])
        finished = close(self.root, draft(outcome="blocked", handoff="Blocked."))
        self.assertIn("blocked_needs_handoff", self.output(finished)["failures"])

    def test_unknown_field_and_boolean_exit_code_are_refused_as_unreadable(self):
        finished = close(self.root, {**draft(), "cv_score": 0.9})
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(self.output(finished)["error"], "draft_refused")
        finished = close(self.root, draft(evidence=[{"command": "make test", "exit_code": True, "observed": ""}]))
        self.assertEqual(finished.returncode, 2)
        finished = close(self.root, raw=b'{"ticket_id": "T-1", "ticket_id": "T-2"}')
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(self.output(finished)["error"], "duplicate_key")

    def test_example_draft_closes_the_next_ticket_in_a_copy_of_the_example_night(self):
        copy = self.root / "copy"
        shutil.copytree(EXAMPLE, copy)
        finished = close(copy, raw=(ROOT / "examples" / "ticket-result-draft.json").read_bytes())
        self.assertEqual(finished.returncode, 0, finished.stdout)
        answer = self.output(finished)
        self.assertEqual((answer["ticket_id"], answer["outcome"]), ("T-102", "blocked"))
        self.assertEqual(answer["next_ticket"]["ticket_id"], "T-103")

    def test_results_folder_link_leaving_the_root_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (self.root / RESULTS).parent.mkdir(parents=True)
        os.symlink(outside.name, self.root / RESULTS)
        finished = close(self.root, draft())
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(self.output(finished)["error"], "path_leaves_root")
        self.assertEqual(os.listdir(outside.name), [])

    def test_script_text_names_its_effects_first(self):
        first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(re.match(r'^"""Effects: ', first_line))


if __name__ == "__main__":
    unittest.main()
