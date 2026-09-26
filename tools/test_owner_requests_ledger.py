"""Tests for tools/owner_requests_ledger.py.

Kind: development check. The fixtures are a small ledger table and a small
roadmap written to a temporary folder; no network, no model call and no
credential. One test class also reads the committed ledger and the committed
roadmap, so a step identifier that the ledger names and the roadmap does not
know fails here, the same way a stale records index fails its own check.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import owner_requests_ledger as tool  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

HEADER = ("| Id | Date | The owner's words | Source | Roadmap steps | State today | Evidence | Gap |\n"
          "|---|---|---|---|---|---|---|---|\n")

FIXTURE_LEDGER = (
    "# Fixture ledger\n\nSome prose before the table.\n\n## Requests\n\n" + HEADER +
    '| R-01 | 2026-09-22 | "merge everything" | handoff 09-22 | S-1.1 | live | release 1 | None recorded. |\n'
    '| R-02 | 2026-09-23 | "build the page" | handoff 09-23 | S-1.2, S-1.3 | building | commit a | The page waits for a release. |\n'
    '| R-03 | 2026-09-24 | "a question with no step" | decision table | none | on main | decision row | No step names it. |\n'
    "\nProse after the table.\n")

FIXTURE_ROADMAP = {
    "schema_version": "roadmap/v1",
    "statuses": ["proposed", "ready", "building", "offline_verified", "live_qualified", "published",
                 "blocked", "superseded"],
    "steps": [
        {"id": "S-1.1", "status": "live_qualified", "title": "Merged onto main"},
        {"id": "S-1.2", "status": "building", "title": "The page"},
        {"id": "S-1.3", "status": "published", "title": "The table"},
        {"id": "S-1.4", "status": "proposed", "title": "Nobody asked for this"},
    ],
}


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.folder = Path(self.directory.name)
        self.ledger = self.folder / "ledger.md"
        self.roadmap = self.folder / "roadmap.yaml"
        self.ledger.write_text(FIXTURE_LEDGER, "utf-8")
        self.roadmap.write_text(yaml.safe_dump(FIXTURE_ROADMAP), "utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def report(self):
        return tool.build_report(tool.read_ledger(self.ledger), tool.read_roadmap(self.roadmap),
                                 ledger_path="ledger.md", roadmap_path="roadmap.yaml")


class ParseTests(FixtureCase):
    def test_rows_and_step_lists_are_read_from_the_table(self):
        rows = tool.read_ledger(self.ledger)
        self.assertEqual([row.id for row in rows], ["R-01", "R-02", "R-03"])
        self.assertEqual(list(rows[1].steps), ["S-1.2", "S-1.3"])
        self.assertEqual(list(rows[2].steps), [])
        self.assertEqual(rows[2].state, "on main")
        self.assertEqual(rows[0].date, "2026-09-22")
        self.assertEqual(rows[0].words, '"merge everything"')

    def test_an_escaped_pipe_stays_inside_one_cell(self):
        self.ledger.write_text(
            FIXTURE_LEDGER.replace('"build the page"', '"build the page \\| and the table"'), "utf-8")
        rows = tool.read_ledger(self.ledger)
        self.assertEqual(rows[1].words, '"build the page | and the table"')
        self.assertEqual(list(rows[1].steps), ["S-1.2", "S-1.3"])

    def test_a_state_outside_the_vocabulary_is_refused(self):
        self.ledger.write_text(FIXTURE_LEDGER.replace("| building |", "| done |"), "utf-8")
        with self.assertRaises(tool.LedgerError) as caught:
            tool.read_ledger(self.ledger)
        self.assertIn("R-02", str(caught.exception))
        self.assertIn("done", str(caught.exception))

    def test_a_steps_cell_that_is_neither_ids_nor_none_is_refused(self):
        self.ledger.write_text(FIXTURE_LEDGER.replace("| S-1.1 |", "| later |"), "utf-8")
        with self.assertRaises(tool.LedgerError):
            tool.read_ledger(self.ledger)

    def test_a_repeated_request_id_is_refused(self):
        self.ledger.write_text(FIXTURE_LEDGER.replace("| R-03 |", "| R-02 |"), "utf-8")
        with self.assertRaises(tool.LedgerError):
            tool.read_ledger(self.ledger)

    def test_a_ledger_without_the_table_is_refused(self):
        self.ledger.write_text("# Nothing here\n", "utf-8")
        with self.assertRaises(tool.LedgerError):
            tool.read_ledger(self.ledger)


class ReportTests(FixtureCase):
    def test_requests_whose_named_steps_are_not_live_are_listed(self):
        report = self.report()
        self.assertEqual([row["id"] for row in report["requests_with_steps_not_live"]], ["R-02"])
        steps = report["requests_with_steps_not_live"][0]["steps"]
        self.assertEqual(steps, [{"id": "S-1.2", "status": "building", "live": False},
                                 {"id": "S-1.3", "status": "published", "live": True}])

    def test_requests_whose_state_is_not_live_are_listed(self):
        report = self.report()
        self.assertEqual([row["id"] for row in report["requests_not_live"]], ["R-02", "R-03"])
        self.assertEqual(report["requests_not_live"][0]["gap"], "The page waits for a release.")

    def test_steps_with_no_request_are_listed(self):
        report = self.report()
        self.assertEqual(report["steps_without_request"],
                         [{"id": "S-1.4", "status": "proposed", "title": "Nobody asked for this"}])

    def test_requests_without_a_step_are_listed(self):
        report = self.report()
        self.assertEqual([row["id"] for row in report["requests_without_step"]], ["R-03"])

    def test_counts_and_record_type(self):
        report = self.report()
        self.assertEqual(report["record_type"], tool.RECORD_TYPE)
        self.assertEqual(report["counts"], {
            "requests": 3, "requests_live": 1, "requests_not_live": 2, "requests_with_steps_not_live": 1,
            "requests_without_step": 1, "steps_in_roadmap": 4, "steps_named": 3, "steps_without_request": 1,
            "unknown_step_ids": 0})
        self.assertEqual(report["by_state"], {"live": 1, "building": 1, "on main": 1})

    def test_a_step_the_roadmap_does_not_know_is_a_finding_and_the_check_fails(self):
        # The known-wrong case: a ledger row names S-9.9, which no roadmap holds.
        self.ledger.write_text(FIXTURE_LEDGER.replace("| S-1.2, S-1.3 |", "| S-1.2, S-9.9 |"), "utf-8")
        report = self.report()
        self.assertEqual(report["unknown_step_ids"], [{"request": "R-02", "step": "S-9.9"}])
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 1)
        self.ledger.write_text(FIXTURE_LEDGER, "utf-8")
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 0)

    def test_check_fails_on_a_malformed_row_instead_of_raising(self):
        self.ledger.write_text(FIXTURE_LEDGER.replace("| building |", "| done |"), "utf-8")
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 1)


class OutputTests(FixtureCase):
    def test_the_record_is_dated_and_never_overwritten(self):
        out = self.folder / "records"
        args = ["--ledger", str(self.ledger), "--roadmap", str(self.roadmap), "--output-dir", str(out),
                "--date", "2026-09-26", "--quiet"]
        self.assertEqual(tool.main(args), 0)
        self.assertEqual(tool.main(args), 0)
        names = sorted(path.name for path in out.iterdir())
        self.assertEqual(names, ["owner-requests-report-2026-09-26-2.json", "owner-requests-report-2026-09-26.json"])
        record = json.loads((out / "owner-requests-report-2026-09-26.json").read_text("utf-8"))
        self.assertEqual(record["record_type"], tool.RECORD_TYPE)
        self.assertEqual(record["report_date"], "2026-09-26")
        self.assertEqual(record["counts"]["requests"], 3)

    def test_the_summary_names_the_counts_the_gaps_and_the_orphan_steps(self):
        out = self.folder / "records"
        summary = self.folder / "latest.md"
        self.assertEqual(tool.main(["--ledger", str(self.ledger), "--roadmap", str(self.roadmap),
                                    "--output-dir", str(out), "--date", "2026-09-26",
                                    "--summary", str(summary), "--quiet"]), 0)
        text = summary.read_text("utf-8")
        self.assertIn("Requests: 3", text)
        self.assertIn("| R-02 | 2026-09-23 | building | S-1.2 (building), S-1.3 (published) | The page waits for a release. |", text)
        self.assertIn("R-03", text)
        self.assertIn("S-1.4", text)
        self.assertNotIn("S-1.1 (", text.split("## Steps no request names")[0].split("## Requests whose")[1])

    def test_the_plain_table_is_printed_without_a_record_when_asked(self):
        table = tool.plain_table(self.report())
        self.assertIn("R-02", table)
        self.assertIn("S-1.2:building", table)
        self.assertIn("Steps no request names: S-1.4", table)


class CommittedLedgerTests(unittest.TestCase):
    """The committed ledger against the committed roadmap, each read once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.ledger = ROOT / tool.DEFAULT_LEDGER
        cls.roadmap = ROOT / tool.DEFAULT_ROADMAP
        cls.rows = tool.read_ledger(cls.ledger)
        cls.steps = tool.read_roadmap(cls.roadmap)

    def test_every_step_identifier_in_the_ledger_exists_in_the_roadmap(self):
        unknown = [(row.id, step) for row in self.rows for step in row.steps if step not in self.steps]
        self.assertEqual(unknown, [])

    def test_the_committed_check_passes(self):
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 0)

    def test_every_row_is_dated_within_the_ledger_window(self):
        # The ledger starts with the September 22 handoff, which also records the owner's
        # engine-wrapping words of the evening of September 21 (Eastern time), so that one
        # earlier day is accepted.
        first = dt.date(2026, 9, 21)
        for row in self.rows:
            date = dt.date.fromisoformat(row.date)
            self.assertGreaterEqual(date, first, row.id)
            self.assertLessEqual(date, dt.date.today() + dt.timedelta(days=1), row.id)

    def test_every_row_quotes_or_declares_a_summary(self):
        for row in self.rows:
            quoted = '"' in row.words or "'" in row.words
            summary = "summary" in row.words.lower() or "recorded" in row.words.lower()
            self.assertTrue(quoted or summary, f"{row.id} neither quotes the owner nor says it is a summary")

    def test_every_row_that_is_not_live_names_a_gap(self):
        for row in self.rows:
            if row.state != "live":
                self.assertTrue(len(row.gap) > 12, f"{row.id} has no gap sentence")


if __name__ == "__main__":
    unittest.main()
