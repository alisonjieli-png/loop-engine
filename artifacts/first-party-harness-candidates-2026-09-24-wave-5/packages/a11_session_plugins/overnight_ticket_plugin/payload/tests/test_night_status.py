"""Tests for scripts/night_status.py. Temporary workspaces only; the payload stays unchanged."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "night_status.py"
EXAMPLE = ROOT / "examples" / "night"
RESULTS = Path(".baltor/state/overnight-ticket-plugin/results")


def run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})


def queue_bytes(tickets=("T-1", "T-2", "T-3"), record_type="night_queue/v1", **extra) -> bytes:
    items = [{"position": index, "id": ticket, "title": f"Title of {ticket}", "status": "queued"}
             for index, ticket in enumerate(tickets, start=1)]
    return json.dumps({"record_type": record_type, "items": items, "held": [], **extra}).encode()


def record(ticket_id: str, position: int, digest: str, outcome: str = "fixed",
           closed_at: str = "2026-09-23T01:00:00Z", handoff: str = "Notes for the next session.") -> dict:
    return {"record_type": "overnight_ticket_result/v1", "queue_sha256": digest, "ticket_id": ticket_id,
            "position": position, "outcome": outcome, "summary": "A short summary.", "evidence": [],
            "changed_files": [], "handoff": handoff, "closed_at": closed_at}


def make_night(root: Path, queue: bytes, records=()) -> str:
    (root / ".baltor" / "night").mkdir(parents=True)
    (root / ".baltor" / "night" / "queue.json").write_bytes(queue)
    (root / RESULTS).mkdir(parents=True)
    for item in records:
        (root / RESULTS / f"{item['ticket_id']}.json").write_text(json.dumps(item), encoding="utf-8")
    return hashlib.sha256(queue).hexdigest()


class NightStatusTests(unittest.TestCase):
    def test_example_night_names_next_ticket_its_check_and_last_handoff(self):
        finished = run("--root", str(EXAMPLE))
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        summary = json.loads(finished.stdout)
        upcoming = summary["next_ticket"]
        self.assertEqual((upcoming["ticket_id"], upcoming["position"]), ("T-102", 2))
        self.assertEqual(upcoming["check"], "python3 -m unittest tests.test_totals")
        self.assertEqual(len(upcoming["acceptance_criteria"]), 2)
        self.assertEqual((summary["closed"], summary["tickets_total"], summary["held_total"]), (1, 3, 1))
        self.assertEqual(summary["last_handoff"]["ticket_id"], "T-101")
        self.assertEqual([row["outcome"] for row in summary["tickets"]], ["fixed", "open", "open"])
        self.assertEqual(summary["problems"], [])
        queue = EXAMPLE / ".baltor" / "night" / "queue.json"
        self.assertEqual(summary["queue_sha256"], hashlib.sha256(queue.read_bytes()).hexdigest())

    def test_last_handoff_follows_closing_time_not_queue_order(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = queue_bytes()
            digest = hashlib.sha256(queue).hexdigest()
            make_night(Path(directory), queue, records=[
                record("T-2", 2, digest, closed_at="2026-09-23T02:00:00Z", handoff="Closed second in the queue."),
                record("T-1", 1, digest, closed_at="2026-09-23T03:00:00Z", handoff="Closed last in time.")])
            summary = json.loads(run("--root", directory).stdout)
        self.assertEqual(summary["last_handoff"]["handoff"], "Closed last in time.")
        self.assertEqual(summary["next_ticket"]["ticket_id"], "T-3")

    def test_record_for_unknown_ticket_is_reported_and_not_counted(self):
        # Known-wrong case: a record for a ticket outside the queue must not count as progress.
        with tempfile.TemporaryDirectory() as directory:
            queue = queue_bytes()
            make_night(Path(directory), queue, records=[record("T-9", 9, hashlib.sha256(queue).hexdigest())])
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 1)
        summary = json.loads(finished.stdout)
        self.assertEqual(summary["closed"], 0)
        self.assertEqual(summary["next_ticket"]["ticket_id"], "T-1")
        self.assertEqual([problem["code"] for problem in summary["problems"]], ["record_for_unknown_ticket"])

    def test_record_written_for_another_queue_is_a_problem_not_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), queue_bytes(), records=[record("T-1", 1, "0" * 64)])
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 1)
        summary = json.loads(finished.stdout)
        self.assertEqual(summary["problems"][0]["code"], "record_from_another_queue")
        self.assertEqual(summary["next_ticket"]["ticket_id"], "T-1")

    def test_queue_extra_fields_are_ignored_but_positions_must_follow_the_list(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), queue_bytes(order="risk_first", budget={"time_minutes": 60}))
            self.assertEqual(run("--root", directory).returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            items = [{"position": 2, "id": "T-1", "title": "One"}, {"position": 1, "id": "T-2", "title": "Two"}]
            make_night(Path(directory), json.dumps({"record_type": "night_queue/v1", "items": items}).encode())
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "queue_positions_out_of_order")

    def test_planning_step_queue_with_an_empty_title_is_still_read(self):
        # Known-wrong case: the planning step copies a missing ticket title as "", and an
        # earlier draft refused the whole queue for it, which stopped every ticket of the night.
        with tempfile.TemporaryDirectory() as directory:
            items = [{"position": 1, "id": "T-1", "title": ""}, {"position": 2, "id": "T-2", "title": "x" * 900}]
            make_night(Path(directory), json.dumps({"record_type": "night_queue/v1", "items": items}).encode())
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 0, finished.stdout)
        summary = json.loads(finished.stdout)
        self.assertEqual((summary["next_ticket"]["ticket_id"], summary["next_ticket"]["title"]), ("T-1", ""))
        with tempfile.TemporaryDirectory() as directory:
            items = [{"position": 1, "id": "T-1", "title": 7}]
            make_night(Path(directory), json.dumps({"record_type": "night_queue/v1", "items": items}).encode())
            finished = run("--root", directory)
        self.assertEqual((finished.returncode, json.loads(finished.stdout)["error"]), (2, "ticket_title_invalid"))

    def test_ticket_ids_differing_only_by_case_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), queue_bytes(tickets=("TKT-1", "tkt-1")))
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "duplicate_ticket_id")

    def test_unknown_queue_record_type_and_old_shape_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), queue_bytes(record_type="night_queue/v9"))
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "unsupported_queue_record_type")
        with tempfile.TemporaryDirectory() as directory:
            shape = {"record_type": "night_queue/v1", "tickets": [{"ticket_id": "T-1", "title": "One"}]}
            make_night(Path(directory), json.dumps(shape).encode())
            finished = run("--root", directory)
        self.assertEqual(json.loads(finished.stdout)["error"], "queue_items_invalid")

    def test_duplicate_key_in_queue_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), b'{"record_type": "night_queue/v1", "items": [], "items": []}')
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "duplicate_key")

    def test_missing_queue_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "queue_missing")

    def test_missing_ticket_list_leaves_a_note_and_no_details(self):
        with tempfile.TemporaryDirectory() as directory:
            make_night(Path(directory), queue_bytes())
            summary = json.loads(run("--root", directory).stdout)
        self.assertNotIn("check", summary["next_ticket"])
        self.assertEqual(summary["notes"], ["tickets_file_missing"])

    def test_results_folder_link_leaving_the_root_is_refused(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            make_night(root, queue_bytes())
            (root / RESULTS).rmdir()
            os.symlink(outside, root / RESULTS)
            finished = run("--root", directory)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["error"], "path_leaves_root")

    def test_every_ticket_closed_leaves_no_next_ticket(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = queue_bytes(tickets=("T-1", "T-2"))
            digest = hashlib.sha256(queue).hexdigest()
            make_night(Path(directory), queue, records=[record("T-1", 1, digest),
                                                        record("T-2", 2, digest, outcome="blocked")])
            summary = json.loads(run("--root", directory).stdout)
        self.assertIsNone(summary["next_ticket"])
        self.assertEqual(summary["counts"], {"fixed": 1, "blocked": 1, "skipped": 0, "needs_review": 0})


if __name__ == "__main__":
    unittest.main()
