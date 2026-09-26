"""The feedback report holds counts only, and a request or a gap becomes a valid idea for the lanes.

Known-wrong cases: a report that would carry a customer's words, an idea whose
facets leave the matrix vocabulary, an unsupported record, and a guide whose
field names drift from the service source.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

import feedback_report as report  # noqa: E402
from check_service_documentation import check as documentation_check  # noqa: E402
from harness_idea_matrix import DATATYPES, FILE_KINDS, OPERATIONS, USE_CASES  # noqa: E402
from opencode_generation_lanes import _render_prompt  # noqa: E402

REPOSITORY = HERE.parent
GUIDE = "docs/guides/customer-feedback-and-requests.md"
NOTE = "Saved me the source review"
DESCRIPTION = "A hook that refuses a commit without a changelog line, for a Terraform repository."


def rows():
    return {
        report.RATING_KIND: [
            {"record_type": "catalogue_item_rating/v1", "tenant_id": "acct-one", "item_identity": "skill.alpha",
             "body_digest": "a" * 64, "value": "useful", "note": NOTE, "at": 1790000000, "revision": 1},
            {"record_type": "catalogue_item_rating/v1", "tenant_id": "acct-two", "item_identity": "skill.alpha",
             "body_digest": "a" * 64, "value": "not_useful", "note": "", "at": 1790000100, "revision": 2}],
        report.REQUEST_KIND: [
            {"record_type": "material_request/v1", "tenant_id": "acct-one", "request_id_digest": "b" * 64,
             "content_digest": "c" * 64, "description": DESCRIPTION, "at": 1790000200, "state": "open"}],
        report.GAP_KIND: [
            {"record_type": "search_gap/v1", "hour": "2026-09-26T13Z", "mode": "lexical",
             "filters": {"harness_kind": ["equals:rules"], "step_functions": ["any_of:acting", "any_of:building"]},
             "library_tiers": ["verified"], "hit_count": 0, "searches": 3}]}


class FeedbackReportTest(unittest.TestCase):
    def test_the_report_holds_counts_and_nothing_a_customer_wrote_or_is(self):
        summary = report.summarise(rows(), "2026-09-26")
        text = json.dumps(summary)
        self.assertEqual(summary["record_type"], "feedback_report/v1")
        self.assertEqual(summary["ratings"], {"useful": 1, "not_useful": 1, "with_a_note": 1, "items_rated": 1,
                                              "items": [{"item_identity": "skill.alpha", "useful": 1, "not_useful": 1}]})
        self.assertEqual(summary["material_requests"], {"total": 1, "open": 1, "accounts": 1})
        self.assertEqual(summary["search_gaps"]["searches"], 3)
        self.assertEqual(summary["search_gaps"]["by_hour"], {"2026-09-26T13Z": 3})
        self.assertEqual(summary["search_gaps"]["by_mode"], {"lexical": 1})
        for private in (NOTE, DESCRIPTION, "acct-one", "acct-two", "b" * 64):
            self.assertNotIn(private, text)

    def test_a_request_becomes_an_idea_in_the_matrix_vocabulary(self):
        idea = report.idea_from_request(rows()[report.REQUEST_KIND][0])
        self.assertEqual(idea["record_type"], "harness_idea_record/v1")
        self.assertEqual(idea["file_kind"], "hook")
        self.assertEqual(idea["operation"], "validation")
        self.assertEqual(idea["use_case"], "devops")
        self.assertIn(idea["datatype"], DATATYPES)
        self.assertIn(idea["operation"], OPERATIONS)
        self.assertIn(idea["use_case"], USE_CASES)
        self.assertIn(idea["file_kind"], FILE_KINDS)
        self.assertEqual(idea["lifecycle"], "candidate")
        self.assertIn(DESCRIPTION, idea["applicability"]["task_reference"])
        self.assertEqual(idea["applicability"]["feedback"]["source"], "material_request")
        self.assertNotIn("acct-one", json.dumps(idea))
        self.assertTrue(idea["id"].startswith("req-"))
        # The lanes render the idea as they render every other idea.
        self.assertIn(idea["id"], _render_prompt(idea))

    def test_a_gap_becomes_an_idea_shaped_by_its_filters_alone(self):
        idea = report.idea_from_gap(rows()[report.GAP_KIND][0])
        self.assertEqual(idea["file_kind"], "rules")
        self.assertIn("harness_kind rules", idea["applicability"]["task_reference"])
        self.assertIn("3 searches", idea["applicability"]["task_reference"])
        self.assertEqual(idea["applicability"]["feedback"], {"source": "search_gap", "hour": "2026-09-26T13Z",
                                                             "mode": "lexical", "searches": 3,
                                                             "library_tiers": ["verified"]})
        self.assertTrue(idea["id"].startswith("gap-"))
        self.assertIn(idea["id"], _render_prompt(idea))

    def test_the_mapping_is_deterministic_and_the_batch_is_whole(self):
        first, second = report.ideas_from(rows()), report.ideas_from(rows())
        self.assertEqual(first, second)
        self.assertEqual(first["record_type"], "harness_idea_batch/v1")
        self.assertEqual(first["idea_count"], 2)
        self.assertEqual(first["unique_ids"], 2)
        self.assertEqual(first["unique_method_signatures"], 2)

    def test_an_unsupported_record_or_facet_is_refused(self):
        with self.assertRaises(report.FeedbackReportError):
            report.idea_from_request({"record_type": "material_request/v2", "description": "x"})
        with self.assertRaises(report.FeedbackReportError):
            report.summarise({report.RATING_KIND: [{"record_type": "something_else/v1"}]}, "2026-09-26")
        with self.assertRaises(report.FeedbackReportError):
            report._idea("req-000000000000", {"operation": "levitation", "datatype": "text",
                                              "use_case": "agentic_task", "file_kind": "skill"}, "t", "b", {})

    def test_the_facet_tables_name_only_matrix_values(self):
        for table, vocabulary in ((report.OPERATION_WORDS, OPERATIONS), (report.DATATYPE_WORDS, DATATYPES),
                                  (report.USE_CASE_WORDS, USE_CASES), (report.FILE_KIND_WORDS, FILE_KINDS)):
            for _word, value in table:
                self.assertIn(value, vocabulary)
        for name, vocabulary in (("operation", OPERATIONS), ("datatype", DATATYPES), ("use_case", USE_CASES),
                                 ("file_kind", FILE_KINDS)):
            self.assertIn(report.DEFAULTS[name], vocabulary)

    def test_the_tool_writes_the_dated_report_and_the_ignored_suggestion_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "rows.json"
            exported = [row for kind in rows().values() for row in kind]
            records.write_text(json.dumps(exported))
            self.assertEqual(report.main(["--records", str(records), "--output", str(root / "out"), "--day", "2026-09-26"]), 0)
            written = json.loads((root / "out" / "feedback-report-2026-09-26.json").read_text())
            self.assertEqual(written["record_type"], "feedback_report/v1")
            ideas = json.loads((root / "out" / "ideas" / "feedback-ideas-2026-09-26.json").read_text())
            self.assertEqual(ideas["idea_count"], 2)
            self.assertNotIn(DESCRIPTION, json.dumps(written))
            self.assertIn(DESCRIPTION, json.dumps(ideas))
            broken = root / "broken.json"
            broken.write_text(json.dumps([{"record_type": "unknown/v1"}]))
            self.assertEqual(report.main(["--records", str(broken), "--output", str(root / "out2")]), 1)
        ignored = (REPOSITORY / "artifacts" / "feedback" / ".gitignore").read_text()
        self.assertIn("ideas/", ignored)

    def test_the_guide_names_only_fields_records_addresses_and_refusals_the_source_has(self):
        outcome = documentation_check(REPOSITORY, pages=(GUIDE,))
        # Recipe coverage belongs to the customer pages as a set; this page is held to its own facts.
        self.assertEqual([row for row in outcome["findings"] if row["page"] == GUIDE], [], outcome)
        self.assertGreater(outcome["facts_checked"], 20)
        # The check refuses a field the source never had.
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            for entry in ("src/loop_engine/core/service_runtime", "src/loop_engine/core/provisioning_server.py",
                          "src/loop_engine/core/provisioning_mcp.py", "src/loop_engine/core/harness_intelligence.py",
                          "src/loop_engine/core/retrieval.py", "src/loop_engine/service_cli.py",
                          "src/loop_engine/cli_help.py", GUIDE):
                source, target = REPOSITORY / entry, copy / entry
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    import shutil
                    shutil.copytree(source, target)
                else:
                    target.write_bytes(source.read_bytes())
            page = copy / GUIDE
            page.write_text(page.read_text().replace("`expected_digest`", "`expected_digest_of_nothing`", 1))
            drifted = documentation_check(copy, pages=(GUIDE,))
            self.assertTrue(any(row["value"] == "expected_digest_of_nothing" for row in drifted["findings"]), drifted)


if __name__ == "__main__":
    unittest.main()
