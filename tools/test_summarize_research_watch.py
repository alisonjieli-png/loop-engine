"""The research watch summary names changed and unreachable sources and refuses other records."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import summarize_research_watch as summary  # noqa: E402

REPORT = {"record_type": "research_source_watch_report/v1", "created_at": "2026-09-24T14:13:02Z", "sources": [
    {"id": "zcode", "name": "ZCode source", "kind": "github_repository", "change": "changed",
     "url": "https://github.com/zai-org/ZCode", "roadmap_step": "S-6.42", "observed": {"revision": "29628c9a"}},
    {"id": "spec", "name": "A specification", "kind": "web_page", "change": "unknown",
     "failure": {"kind": "network_error"}},
    {"id": "steady", "name": "Steady", "kind": "web_page", "change": "unchanged"}]}


def run(argv):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        summary.main(argv)
    return stream.getvalue()


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "report.json"
        self.path.write_text(json.dumps(REPORT))

    def tearDown(self):
        self.folder.cleanup()

    def test_the_count_is_the_number_of_changed_sources(self):
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "1")

    def test_the_summary_names_the_changed_source_and_the_unreachable_one(self):
        text = run([str(self.path)])
        self.assertIn("[ZCode source](https://github.com/zai-org/ZCode)", text)
        self.assertIn("Not reached: spec (network_error).", text)
        self.assertNotIn("Steady", text)

    def test_known_wrong_another_record_is_refused(self):
        self.path.write_text(json.dumps({"record_type": "something_else/v1", "sources": []}))
        with self.assertRaises(SystemExit):
            run([str(self.path)])

    def test_known_wrong_a_report_with_no_change_counts_zero(self):
        self.path.write_text(json.dumps({**REPORT, "sources": REPORT["sources"][1:]}))
        self.assertEqual(run([str(self.path), "--changed-count"]).strip(), "0")


if __name__ == "__main__":
    unittest.main()
