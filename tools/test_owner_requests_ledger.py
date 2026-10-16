"""Tests for tools/owner_requests_ledger.py.

Kind: development check. The fixtures are small ledger tables and a small
roadmap written to a temporary folder; no network, no model call and no
credential. One test class also reads the committed monthly ledgers and the
committed roadmap, so a step identifier that a ledger names and the roadmap
does not know fails here, the same way a stale records index fails its own
check, and so does a default run that would miss a monthly ledger.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
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

FIXTURE_OCTOBER_LEDGER = (
    "# Fixture October ledger\n\n## Requests\n\n" + HEADER +
    '| R-04 | 2026-10-02 | "serve the subtask" | owner prompt history, Codex, 2026-10-02; measured 3 times '
    '| S-1.4.01 | live | release 2 | None recorded. |\n'
    '| R-05 | 2026-10-03 | "finish the rest" | owner prompt history, Codex, 2026-10-03; measured 1 time '
    '| S-1.4.02, S-1.2 | proposed | the step exists | Nothing is built yet. |\n')

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

#: The same roadmap with two subtasks under S-1.4, as roadmap.yaml nests them.
FIXTURE_ROADMAP_WITH_SUBTASKS = {
    **FIXTURE_ROADMAP,
    "steps": FIXTURE_ROADMAP["steps"][:3] + [
        {"id": "S-1.4", "status": "building", "title": "A step with subtasks",
         "subtasks": [{"id": "S-1.4.01", "status": "live_qualified", "title": "The served part"},
                      {"id": "S-1.4.02", "status": "proposed", "title": "The rest"}]},
        {"id": "S-1.5", "status": "proposed", "title": "Nobody asked for this"},
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
                                 ledger_paths=["ledger.md"], roadmap_path="roadmap.yaml")


class ParseTests(FixtureCase):
    def test_rows_and_step_lists_are_read_from_the_table(self):
        rows = tool.read_ledger(self.ledger)
        self.assertEqual([row.id for row in rows], ["R-01", "R-02", "R-03"])
        self.assertEqual(list(rows[1].steps), ["S-1.2", "S-1.3"])
        self.assertEqual(list(rows[2].steps), [])
        self.assertEqual(rows[2].state, "on main")
        self.assertEqual(rows[0].date, "2026-09-22")
        self.assertEqual(rows[0].words, '"merge everything"')
        self.assertEqual(rows[0].ledger, str(self.ledger))

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

    def test_subtask_identifiers_are_read_beside_step_identifiers(self):
        self.assertEqual(tool.parse_steps("S-6.214.12, S-6.35", "R-1"), ("S-6.214.12", "S-6.35"))
        with self.assertRaises(tool.LedgerError):
            tool.parse_steps("S-6.214.12.3", "R-1")

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
            "requests_without_step": 1, "steps_in_roadmap": 4, "subtasks_in_roadmap": 0, "steps_named": 3,
            "subtasks_named": 0, "steps_without_request": 1, "unknown_step_ids": 0})
        self.assertEqual(report["by_state"], {"live": 1, "building": 1, "on main": 1})
        self.assertEqual(report["ledgers"], ["ledger.md"])
        self.assertEqual(report["by_ledger"][str(self.ledger)],
                         {"requests": 3, "requests_live": 1, "by_state": {"live": 1, "building": 1, "on main": 1}})

    def test_a_step_the_roadmap_does_not_know_is_a_finding_and_the_check_fails(self):
        # The known-wrong case: a ledger row names S-9.9, which no roadmap holds.
        self.ledger.write_text(FIXTURE_LEDGER.replace("| S-1.2, S-1.3 |", "| S-1.2, S-9.9 |"), "utf-8")
        report = self.report()
        self.assertEqual(report["unknown_step_ids"], [{"request": "R-02", "step": "S-9.9", "ledger": str(self.ledger)}])
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 1)
        self.ledger.write_text(FIXTURE_LEDGER, "utf-8")
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 0)

    def test_check_fails_on_a_malformed_row_instead_of_raising(self):
        self.ledger.write_text(FIXTURE_LEDGER.replace("| building |", "| done |"), "utf-8")
        self.assertEqual(tool.main(["--check", "--ledger", str(self.ledger), "--roadmap", str(self.roadmap)]), 1)


class SubtaskTests(FixtureCase):
    def setUp(self):
        super().setUp()
        self.roadmap.write_text(yaml.safe_dump(FIXTURE_ROADMAP_WITH_SUBTASKS), "utf-8")
        self.october = self.folder / "october.md"
        self.october.write_text(FIXTURE_OCTOBER_LEDGER, "utf-8")

    def report(self):
        return tool.build_report(tool.read_ledgers([self.ledger, self.october]), tool.read_roadmap(self.roadmap))

    def test_the_roadmap_reader_keeps_subtasks_with_their_parent(self):
        steps = tool.read_roadmap(self.roadmap)
        self.assertEqual(steps["S-1.4.01"], {"status": "live_qualified", "title": "The served part", "parent": "S-1.4"})
        self.assertIsNone(steps["S-1.4"]["parent"])

    def test_a_subtask_decides_its_own_liveness_and_names_its_step(self):
        report = self.report()
        live_request = [row for row in report["requests_with_steps_not_live"] if row["id"] == "R-04"]
        self.assertEqual(live_request, [], "R-04 names only the live subtask S-1.4.01")
        r05 = [row for row in report["requests_with_steps_not_live"] if row["id"] == "R-05"][0]
        self.assertEqual(r05["steps"][0], {"id": "S-1.4.02", "status": "proposed", "live": False})
        # S-1.4 is named through its subtasks, so only S-1.5 is named by no request.
        self.assertEqual([step["id"] for step in report["steps_without_request"]], ["S-1.5"])
        self.assertEqual(report["counts"]["steps_in_roadmap"], 5)
        self.assertEqual(report["counts"]["subtasks_in_roadmap"], 2)
        self.assertEqual(report["counts"]["subtasks_named"], 2)

    def test_an_unknown_subtask_is_a_finding(self):
        # The known-wrong case for subtasks: S-1.4.99 does not exist under S-1.4.
        self.october.write_text(FIXTURE_OCTOBER_LEDGER.replace("| S-1.4.01 |", "| S-1.4.99 |"), "utf-8")
        report = self.report()
        self.assertEqual([(row["request"], row["step"]) for row in report["unknown_step_ids"]], [("R-04", "S-1.4.99")])


class MonthlyLedgerTests(FixtureCase):
    """The default run reads every monthly ledger and reports them together."""

    def setUp(self):
        super().setUp()
        self.roadmap.write_text(yaml.safe_dump(FIXTURE_ROADMAP_WITH_SUBTASKS), "utf-8")
        self.context = self.folder / "docs" / "context"
        self.context.mkdir(parents=True)
        self.september = self.context / "OWNER-REQUESTS-LEDGER-2026-09.md"
        self.october = self.context / "OWNER-REQUESTS-LEDGER-2026-10.md"
        self.september.write_text(FIXTURE_LEDGER, "utf-8")
        self.october.write_text(FIXTURE_OCTOBER_LEDGER, "utf-8")
        # Neither is a monthly ledger, so neither is read.
        (self.context / "OWNER-REQUESTS-LEDGER-NOTES.md").write_text("# Notes\n", "utf-8")
        (self.context / "OWNER-REQUESTS-LEDGER-2026-10.md.bak").write_text("# Old copy\n", "utf-8")

    def run_tool(self, *extra):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tool.main(["--ledger-dir", str(self.context), "--roadmap", str(self.roadmap), *extra])
        return code, output.getvalue()

    def test_every_monthly_ledger_is_found_in_month_order(self):
        self.assertEqual(tool.default_ledgers(self.context), [str(self.september), str(self.october)])

    def test_the_default_run_reports_both_ledgers_together(self):
        records = self.folder / "records"
        summary = self.folder / "latest.md"
        code, _ = self.run_tool("--output-dir", str(records), "--date", "2026-10-16", "--summary", str(summary),
                                "--quiet")
        self.assertEqual(code, 0)
        record = json.loads((records / "owner-requests-report-2026-10-16.json").read_text("utf-8"))
        self.assertEqual(record["record_type"], "owner_requests_report/v2")
        self.assertEqual(record["ledgers"], [str(self.september), str(self.october)])
        self.assertEqual(record["counts"]["requests"], 5)
        self.assertEqual(record["by_ledger"][str(self.october)]["requests"], 2)
        self.assertEqual(record["by_ledger"][str(self.october)]["by_state"], {"live": 1, "proposed": 1})
        self.assertEqual([row["id"] for row in record["requests_not_live"]], ["R-02", "R-03", "R-05"])
        text = summary.read_text("utf-8")
        self.assertIn(f"{self.september}: 3 requests (1 live, 1 on main, 1 building)", text)
        self.assertIn(f"{self.october}: 2 requests (1 live, 1 proposed)", text)
        self.assertIn("| R-05 | 2026-10-03 | proposed | S-1.4.02 (proposed), S-1.2 (building) | Nothing is built yet. |",
                      text)

    def test_an_october_row_naming_an_unknown_step_is_reported_and_the_check_fails(self):
        # The known-wrong control: the October ledger names S-9.9, which the roadmap does not hold.
        self.october.write_text(FIXTURE_OCTOBER_LEDGER.replace("| S-1.4.02, S-1.2 |", "| S-1.4.02, S-9.9 |"), "utf-8")
        code, output = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("R-05 names S-9.9, which the roadmap does not hold", output)
        self.assertIn("5 requests in 2 ledgers, 1 findings", output)
        report = tool.build_report(tool.read_ledgers(tool.default_ledgers(self.context)),
                                   tool.read_roadmap(self.roadmap))
        self.assertEqual(report["unknown_step_ids"], [{"request": "R-05", "step": "S-9.9", "ledger": str(self.october)}])
        # The September ledger alone passes, so the finding comes from the October file.
        code, _ = self.run_tool("--check", "--ledger", str(self.september))
        self.assertEqual(code, 0)

    def test_an_identifier_two_ledgers_share_is_refused(self):
        self.october.write_text(FIXTURE_OCTOBER_LEDGER.replace("| R-05 |", "| R-02 |"), "utf-8")
        with self.assertRaises(tool.LedgerError) as caught:
            tool.read_ledgers(tool.default_ledgers(self.context))
        self.assertIn("R-02", str(caught.exception))
        self.assertIn(str(self.october), str(caught.exception))
        with contextlib.redirect_stderr(io.StringIO()):
            code, _ = self.run_tool("--check")
        self.assertEqual(code, 1)

    def test_an_explicit_ledger_reads_that_file_only(self):
        records = self.folder / "records"
        code, _ = self.run_tool("--ledger", str(self.october), "--output-dir", str(records), "--date", "2026-10-16",
                                "--quiet")
        self.assertEqual(code, 0)
        record = json.loads((records / "owner-requests-report-2026-10-16.json").read_text("utf-8"))
        self.assertEqual(record["ledgers"], [str(self.october)])
        self.assertEqual(record["counts"]["requests"], 2)

    def test_a_folder_without_a_monthly_ledger_fails(self):
        self.september.unlink()
        self.october.unlink()
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            code, _ = self.run_tool("--check")
        self.assertEqual(code, 1)
        self.assertIn("no file named OWNER-REQUESTS-LEDGER-YYYY-MM.md", errors.getvalue())


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
        self.assertEqual(record["ledgers"], [str(self.ledger)])

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
        self.assertIn(f"{self.ledger}: 3 requests (1 live, 1 on main, 1 building)", table)


class CommittedLedgerTests(unittest.TestCase):
    """The committed monthly ledgers against the committed roadmap, each read once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.ledgers = tool.default_ledgers(ROOT / tool.LEDGER_DIRECTORY)
        cls.roadmap = ROOT / tool.DEFAULT_ROADMAP
        cls.rows = tool.read_ledgers(cls.ledgers)
        cls.steps = tool.read_roadmap(cls.roadmap)

    def test_the_default_reads_the_september_and_october_ledgers(self):
        names = [Path(path).name for path in self.ledgers]
        self.assertEqual(names[:2], ["OWNER-REQUESTS-LEDGER-2026-09.md", "OWNER-REQUESTS-LEDGER-2026-10.md"])

    def test_the_cron_invocation_reads_every_monthly_ledger(self):
        # The daily cron runs the tool from a checkout root with no --ledger argument.
        before = os.getcwd()
        try:
            os.chdir(ROOT)
            relative = tool.default_ledgers()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = tool.main(["--check"])
        finally:
            os.chdir(before)
        self.assertIn("docs/context/OWNER-REQUESTS-LEDGER-2026-10.md", relative)
        self.assertEqual(code, 0)
        self.assertIn(f"{len(self.rows)} requests in {len(self.ledgers)} ledgers, 0 findings", output.getvalue())

    def test_every_step_identifier_in_the_ledgers_exists_in_the_roadmap(self):
        unknown = [(row.id, step) for row in self.rows for step in row.steps if step not in self.steps]
        self.assertEqual(unknown, [])

    def test_the_committed_check_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = tool.main(["--check", "--ledger-dir", str(ROOT / tool.LEDGER_DIRECTORY),
                              "--roadmap", str(self.roadmap)])
        self.assertEqual(code, 0)

    def test_every_row_is_dated_within_its_ledger_month(self):
        # A monthly ledger holds the requests of its own month. The September ledger starts with
        # the September 22 handoff, which also records the owner's engine-wrapping words of the
        # evening of September 21 (Eastern time); that day is still in September.
        for row in self.rows:
            match = tool.LEDGER_NAME.match(Path(row.ledger).name)
            date = dt.date.fromisoformat(row.date)
            self.assertEqual((date.year, date.month), (int(match.group(1)), int(match.group(2))), row.id)
            self.assertLessEqual(date, dt.date.today() + dt.timedelta(days=1), row.id)

    def test_identifiers_continue_from_one_ledger_to_the_next(self):
        numbers = [int(row.id.split("-")[1]) for row in self.rows]
        october = [int(row.id.split("-")[1]) for row in self.rows if row.ledger.endswith("2026-10.md")]
        september = [int(row.id.split("-")[1]) for row in self.rows if row.ledger.endswith("2026-09.md")]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(october[0], max(september) + 1)
        self.assertEqual(october, list(range(october[0], october[0] + len(october))))

    def test_every_row_quotes_or_declares_a_summary(self):
        for row in self.rows:
            quoted = '"' in row.words or "'" in row.words
            summary = "summary" in row.words.lower() or "recorded" in row.words.lower()
            self.assertTrue(quoted or summary, f"{row.id} neither quotes the owner nor says it is a summary")

    def test_every_october_row_names_its_source(self):
        # A row from the measurement names its lane, date and measured count; a prompt the
        # collected corpus predates is added by hand and names the owner prompt it comes from.
        for row in self.rows:
            if not row.ledger.endswith("2026-10.md"):
                continue
            self.assertTrue(row.source.startswith(("owner prompt history, ", "owner prompt to ")), row.id)
            if row.source.startswith("owner prompt history, "):
                self.assertIn("measured", row.source, row.id)

    def test_every_row_that_is_not_live_names_a_gap(self):
        for row in self.rows:
            if row.state != "live":
                self.assertTrue(len(row.gap) > 12, f"{row.id} has no gap sentence")


if __name__ == "__main__":
    unittest.main()
