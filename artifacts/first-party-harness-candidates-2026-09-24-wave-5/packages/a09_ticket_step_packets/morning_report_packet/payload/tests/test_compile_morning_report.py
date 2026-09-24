"""Effects: creates temporary folders with a synthetic night, runs scripts/compile_morning_report.py, reads the reports it writes.

Tests for scripts/compile_morning_report.py. Run from the payload root:

    python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v

The night built here is the one behind examples/input.json and examples/output.json.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "compile_morning_report.py"
EXAMPLE_INPUT = PAYLOAD / "examples" / "input.json"
EXAMPLE_OUTPUT = PAYLOAD / "examples" / "output.json"
HANDOFFS = ".baltor/night/handoffs/"
REPORT = ".baltor/night/morning-report.json"
MARKDOWN = ".baltor/night/morning-report.md"


def handoff(step_id, ticket_id, status, written_at, claims=(), blocker=None, first_action=None):
    return {"record_type": "night_step_handoff/v1", "step_id": step_id, "ticket_id": ticket_id, "status": status,
            "written_at": written_at, "revision": None, "files": [],
            "claims": [{"text": text, "evidence": evidence} for text, evidence in claims],
            "blocker": blocker, "first_action": first_action, "remaining_actions": [], "done_when": []}


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=1) + "\n", encoding="utf-8")


def build_night(root):
    """Write the synthetic night of September 23 below root and return root."""
    write(root, "tickets/T-105.md", "Export totals in the right currency.\n")
    write(root, "shop/totals.py", "def total(lines):\n    return sum(lines)\n")
    write(root, ".baltor/night/evidence/t-104/reproduction-run.json", {"verdict": "nonzero_exit_recorded"})
    write(root, ".baltor/night/evidence/t-104/verification.json", {"verdict": "ready_for_review"})
    write(root, HANDOFFS + "t-104-verification.json", handoff(
        "t-104-verification", "T-104", "complete", "2026-09-23T03:12:40Z", claims=[
            ("The new test test_badge_uses_singular_for_one_item failed before the fix.",
             ".baltor/night/evidence/t-104/reproduction-run.json"),
            ("The relevant and full test runs passed after the fix, and every changed path is allowed.",
             ".baltor/night/evidence/t-104/verification.json")]))
    write(root, HANDOFFS + "t-105-triage.json", handoff(
        "t-105-triage", "T-105", "blocked", "2026-09-23T01:20:05Z",
        blocker={"reason": "The ticket does not say which currency the export should use.",
                 "question": "Should the export use the account currency or the order currency?",
                 "evidence": "tickets/T-105.md"}))
    write(root, HANDOFFS + "t-106-fix-0215.json", handoff(
        "t-106-fix", "T-106", "unfinished", "2026-09-23T02:15:00Z",
        first_action="Write the rounding fix in shop/totals.py."))
    write(root, HANDOFFS + "t-106-fix-0241.json", handoff(
        "t-106-fix", "T-106", "unfinished", "2026-09-23T02:41:07Z",
        claims=[("The rounding fix in shop/totals.py is written but not yet tested.", "shop/totals.py")],
        first_action="Run the verification checks again; the last run was stopped by the step time limit."))
    write(root, HANDOFFS + "t-108-fix.json", handoff(
        "t-108-fix", "T-108", "complete", "2026-09-23T04:02:19Z",
        claims=[("All tests pass after the change.", ".baltor/night/evidence/t-108/full-run.json")]))
    write(root, ".baltor/night/queue.json", {"tickets": [
        {"ticket_id": ticket, "final_step_id": ticket.lower() + "-verification"}
        for ticket in ("T-104", "T-105", "T-106", "T-107", "T-108")]})
    lines = [{"time": "2026-09-23T01:02:03Z", "step_id": "t-104-verification", "tool": "shell"},
             {"time": "2026-09-23T03:09:44Z", "step_id": "t-104-verification", "tool": "read"},
             {"time": "2026-09-23T02:40:59Z", "step_id": "t-106-fix", "tool": "shell"},
             {"time": "2026-09-23T04:30:12Z", "step_id": "t-109-scout", "tool": "read"}]
    write(root, ".baltor/state/log-tool-activity/night.jsonl", "".join(json.dumps(line) + "\n" for line in lines))
    write(root, ".baltor/step/input.json", EXAMPLE_INPUT.read_text(encoding="utf-8"))
    return root


def run_compiler(root):
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--input", ".baltor/step/input.json",
                           "--root", str(root)], capture_output=True, text=True, timeout=120)
    return done.returncode, json.loads(done.stdout)


class CompileMorningReport(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = build_night(Path(self.directory.name) / "work")

    def tearDown(self):
        self.directory.cleanup()

    def report(self):
        return json.loads((self.root / REPORT).read_text(encoding="utf-8"))

    def steps(self, bucket):
        return [(item["ticket_id"], item["step_id"]) for item in self.report()[bucket]]

    def tickets(self):
        return {row["ticket_id"]: (row["status"], row["reason"]) for row in self.report()["tickets"]}

    def unsupported(self):
        return [(item["step_id"], item["problem"]) for item in self.report()["unsupported_claims"]]

    def test_example_output_is_the_output_for_the_example_night(self):
        code, summary = run_compiler(self.root)
        self.assertEqual(code, 1, summary)
        produced, expected = self.report(), json.loads(EXAMPLE_OUTPUT.read_text(encoding="utf-8"))
        produced.pop("compiled_at")
        expected.pop("compiled_at")
        self.assertEqual(produced, expected)

    def test_sections_follow_the_handoffs_and_evidence(self):
        run_compiler(self.root)
        self.assertEqual(self.steps("complete"), [("T-104", "t-104-verification")])
        self.assertEqual(self.steps("blocked"), [("T-105", "t-105-triage")])
        unfinished = {(item["ticket_id"], item["step_id"]): item["reason"] for item in self.report()["unfinished"]}
        self.assertEqual(unfinished, {("T-106", "t-106-fix"): "handoff_status_unfinished",
                                      ("T-107", None): "no_handoff_found",
                                      ("T-108", "t-108-fix"): "complete_without_evidence",
                                      (None, "t-109-scout"): "activity_without_handoff"})
        self.assertEqual([item["handoff"] for item in self.report()["superseded"]],
                         [".baltor/night/handoffs/t-106-fix-0215.json"])
        self.assertEqual(self.tickets(), {"T-104": ("complete", None), "T-105": ("blocked", "step_blocked"),
                                          "T-106": ("unfinished", "final_step_not_complete"),
                                          "T-107": ("unfinished", "no_handoff_found"),
                                          "T-108": ("unfinished", "final_step_not_complete")})

    def test_known_wrong_complete_claim_without_evidence_is_not_complete(self):
        run_compiler(self.root)
        self.assertNotIn(("T-108", "t-108-fix"), self.steps("complete"))
        self.assertEqual(self.unsupported(), [("t-108-fix", "evidence_missing")])
        markdown = (self.root / MARKDOWN).read_text(encoding="utf-8")
        complete_section = markdown.split("## Complete steps")[1].split("## Blocked steps")[0]
        self.assertNotIn("T-108", complete_section)
        self.assertIn("All tests pass after the change.", markdown.split("## Claims without evidence")[1])

    def test_known_wrong_ticket_with_only_a_triage_handoff_is_not_finished(self):
        write(self.root, "tickets/T-107.md", "Fix the badge.\n")
        write(self.root, HANDOFFS + "t-107-triage.json", handoff(
            "t-107-triage", "T-107", "complete", "2026-09-23T01:00:00Z",
            claims=[("Triage answered go.", "tickets/T-107.md")]))
        code, summary = run_compiler(self.root)
        self.assertIn(("T-107", "t-107-triage"), self.steps("complete"))
        self.assertEqual(self.tickets()["T-107"], ("unfinished", "final_step_not_complete"))
        self.assertIn("T-107", summary["unfinished_tickets"])
        markdown = (self.root / MARKDOWN).read_text(encoding="utf-8")
        tickets_section = markdown.split("## Tickets")[1].split("## Complete steps")[0]
        self.assertIn("- T-107: unfinished: its final step t-107-verification has no complete handoff.", tickets_section)

    def test_ticket_without_a_declared_final_step_stays_unfinished(self):
        write(self.root, ".baltor/night/queue.json", {"tickets": [{"ticket_id": "T-104"}]})
        code, summary = run_compiler(self.root)
        self.assertEqual(self.tickets()["T-104"], ("unfinished", "final_step_not_declared"))
        self.assertIn(("T-104", "t-104-verification"), self.steps("complete"))

    def test_night_queue_record_is_read(self):
        write(self.root, ".baltor/night/queue.json", {
            "record_type": "night_queue/v1", "items": [
                {"position": 1, "id": "T-104", "status": "queued", "final_step_id": "t-104-verification"},
                {"position": 2, "id": "T-107", "status": "queued"}], "held": []})
        run_compiler(self.root)
        tickets = self.tickets()
        self.assertEqual(tickets["T-104"], ("complete", None))
        self.assertEqual(tickets["T-107"], ("unfinished", "no_handoff_found"))
        self.assertNotIn(".baltor/night/queue.json", [item["path"] for item in self.report()["problems"]])

    def test_self_cited_folder_and_night_record_evidence_is_not_complete(self):
        (self.root / "tests").mkdir()
        write(self.root, HANDOFFS + "t-120-fix.json", handoff(
            "t-120-fix", "T-120", "complete", "2026-09-23T03:00:00Z",
            claims=[("All tests pass after the fix.", HANDOFFS + "t-120-fix.json")]))
        write(self.root, HANDOFFS + "t-121-fix.json", handoff(
            "t-121-fix", "T-121", "complete", "2026-09-23T03:00:00Z",
            claims=[("All tests pass after the fix.", "tests")]))
        write(self.root, HANDOFFS + "t-122-fix.json", handoff(
            "t-122-fix", "T-122", "complete", "2026-09-23T03:00:00Z",
            claims=[("All tests pass after the fix.", ".baltor/night/queue.json")]))
        run_compiler(self.root)
        complete = [step_id for _, step_id in self.steps("complete")]
        for step_id in ("t-120-fix", "t-121-fix", "t-122-fix"):
            self.assertNotIn(step_id, complete)
        problems = dict((step_id, problem) for step_id, problem in self.unsupported() if step_id != "t-108-fix")
        self.assertEqual(problems, {"t-120-fix": "evidence_is_a_night_record", "t-121-fix": "evidence_is_a_folder",
                                    "t-122-fix": "evidence_is_a_night_record"})

    def test_report_fields_stay_within_the_contract_bounds(self):
        wide = {f"field_number_{index:03d}_with_a_long_name": index for index in range(60)}
        write(self.root, HANDOFFS + "config-export.json", wide)
        deep = HANDOFFS + "/".join(["a-very-long-folder-name-for-this-test"] * 12) + "/t-130-fix.json"
        write(self.root, deep, handoff("t-130-fix", "T-130", "unfinished", "2026-09-23T03:00:00Z",
                                       first_action="Run the checks again."))
        notes = [{"text": "A note with a long path.", "evidence": "x" * 450}]
        write(self.root, ".baltor/night/report-notes.json", notes)
        code, _summary = run_compiler(self.root)
        self.assertEqual(code, 1)
        report = self.report()
        self.assertTrue(report["problems"])
        for item in report["problems"]:
            self.assertLessEqual(len(item["problem"]), 600, item)
            self.assertLessEqual(len(item["path"]), 400, item)
        self.assertTrue(any("longer than 400 characters" in item["problem"] for item in report["problems"]))
        for item in report["unsupported_claims"]:
            self.assertLessEqual(len(item["evidence"] or ""), 400, item)

    def test_report_is_never_written_through_a_link(self):
        outside = Path(self.directory.name) / "outside.txt"
        outside.write_text("keep\n", encoding="utf-8")
        (self.root / ".baltor/night/morning-report.json.partial").symlink_to(outside)
        (self.root / MARKDOWN).symlink_to(self.root / "shop/totals.py")
        code, summary = run_compiler(self.root)
        self.assertEqual(code, 1, summary)
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual((self.root / "shop/totals.py").read_text(encoding="utf-8"),
                         "def total(lines):\n    return sum(lines)\n")
        self.assertFalse((self.root / MARKDOWN).is_symlink())
        self.assertIn("# Morning report", (self.root / MARKDOWN).read_text(encoding="utf-8"))
        self.assertEqual(self.report()["record_type"], "night_morning_report/v1")

    def test_report_path_that_links_out_of_the_workspace_is_refused(self):
        outside = Path(self.directory.name) / "outside.txt"
        outside.write_text("keep\n", encoding="utf-8")
        (self.root / MARKDOWN).symlink_to(outside)
        code, summary = run_compiler(self.root)
        self.assertEqual(code, 2, summary)
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((self.root / REPORT).exists())

    def test_clean_night_exits_zero(self):
        (self.root / HANDOFFS / "t-108-fix.json").unlink()
        write(self.root, ".baltor/night/queue.json",
              {"tickets": [{"ticket_id": "T-104", "final_step_id": "t-104-verification"}]})
        code, summary = run_compiler(self.root)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["counts"]["unsupported_claims"], 0)

    def test_unreadable_records_are_listed_not_skipped(self):
        (self.root / HANDOFFS / "broken.json").write_text("{not json", encoding="utf-8")
        wrong = handoff("t-110-fix", "T-110", "blocked", "2026-09-23T05:00:00Z")
        (self.root / HANDOFFS / "t-110-fix.json").write_text(json.dumps(wrong), encoding="utf-8")
        log = self.root / ".baltor/state/log-tool-activity/night.jsonl"
        log.write_text(log.read_text(encoding="utf-8") + "not a record\n", encoding="utf-8")
        code, _summary = run_compiler(self.root)
        self.assertEqual(code, 1)
        problems = {item["path"]: item["problem"] for item in self.report()["problems"]}
        self.assertIn(HANDOFFS + "broken.json", problems)
        self.assertIn("a blocked handoff names its blocker", problems[HANDOFFS + "t-110-fix.json"])
        self.assertIn("1 lines could not be read", problems[".baltor/state/log-tool-activity/night.jsonl"])
        self.assertIn(("T-110", "t-110-fix"), self.steps("unfinished"))
        self.assertEqual(self.tickets()["T-110"], ("unfinished", "final_step_not_declared"))

    def test_notes_need_existing_file_evidence(self):
        notes = [{"text": "Two tickets waited on product decisions.", "evidence": "tickets/T-105.md"},
                 {"text": "T-105 stopped at triage.", "evidence": HANDOFFS + "t-105-triage.json"},
                 {"text": "The disk filled up at 04:00.", "evidence": ".baltor/night/disk.log"},
                 {"text": "See the report.", "evidence": REPORT}]
        write(self.root, ".baltor/night/report-notes.json", notes)
        run_compiler(self.root)
        report = self.report()
        self.assertEqual([note["evidence"] for note in report["notes"]],
                         ["tickets/T-105.md", HANDOFFS + "t-105-triage.json"])
        notes_problems = [item["problem"] for item in report["unsupported_claims"] if item["source"] == "notes"]
        self.assertEqual(sorted(notes_problems), ["evidence_is_a_night_record", "evidence_missing"])

    def test_markdown_neutralizes_hidden_text_and_evidence_that_leaves_the_workspace(self):
        sneaky = handoff("t-111-fix", "T-111", "complete", "2026-09-23T05:10:00Z",
                         claims=[("Done " + "<" + "!-- hidden --" + ">" + " here.", "../outside.json")])
        (self.root / HANDOFFS / "t-111-fix.json").write_text(json.dumps(sneaky), encoding="utf-8")
        run_compiler(self.root)
        markdown = (self.root / MARKDOWN).read_text(encoding="utf-8")
        self.assertNotIn("<" + "!--", markdown)
        self.assertIn(("t-111-fix", "evidence_outside_workspace"), self.unsupported())

    def test_unusable_input_is_refused_without_writing(self):
        step_file = self.root / ".baltor/step/input.json"
        step = json.loads(step_file.read_text(encoding="utf-8"))
        for change in ({"night_id": "{" * 2 + "NIGHT_ID" + "}" * 2},
                       {"report_json_path": "reports/morning.json"},
                       {"report_json_path": HANDOFFS + "report.json"},
                       {"report_json_path": ".baltor/step/morning-report.json"},
                       {"notes_path": ".baltor/step/report-notes.json"},
                       {"handoff_dir": ".baltor/missing"}):
            step_file.write_text(json.dumps({**step, **change}), encoding="utf-8")
            code, summary = run_compiler(self.root)
            self.assertEqual(code, 2, (change, summary))
        self.assertFalse((self.root / REPORT).exists())
        self.assertFalse((self.root / MARKDOWN).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
