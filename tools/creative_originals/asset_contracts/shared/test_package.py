"""Tests every asset contract package carries: its card, its files and its fixtures.

The contract card (component.json) names the item's root module (the job identity) and lists fixtures.
Every known-good fixture must pass. Every known-wrong fixture must fail, and must report each failure code
it declares. A tool may not report a failure code its contract does not declare, and every report carries
the fields the contract promises. The command line must print one JSON report and exit 0 on a pass and 1 on
a failure. Replacing the tool's functions with ones that raise makes these tests fail.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
IDENTITY = CARD["job"]["identity"]
CONTRACT_KEYS = {"entry_points", "inputs", "report", "failures_detected", "proves", "does_not_prove", "fixtures"}
FIXTURE_LIMIT = 100 * 1024


def package_argv(argv: list) -> list:
    """The fixture's arguments with package-relative paths made absolute."""
    return [str(ROOT / value) if not value.startswith("-") and (ROOT / value).exists() else value for value in argv]


def tool():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module(IDENTITY)


class CardTests(unittest.TestCase):
    def test_files_match_card(self):
        for row in CARD["files"]:
            with self.subTest(path=row["path"]):
                self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_readme_names_the_item(self):
        first = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(first, "# " + CARD["title"])

    def test_contract_declares_fixtures_and_codes(self):
        self.assertTrue(CONTRACT_KEYS <= set(CONTRACT), sorted(CONTRACT_KEYS - set(CONTRACT)))
        declared = set(CONTRACT["failures_detected"])
        expectations = [row["expect"] for row in CONTRACT["fixtures"]]
        self.assertIn("pass", expectations, "a contract needs a known-good fixture")
        self.assertIn("fail", expectations, "a contract needs a known-wrong fixture")
        for row in CONTRACT["fixtures"]:
            with self.subTest(fixture=row["argv"]):
                self.assertIn(row["expect"], ("pass", "fail"))
                if row["expect"] == "fail":
                    self.assertTrue(row["codes"], "a known-wrong fixture names the codes it must produce")
                    self.assertTrue(set(row["codes"]) <= declared, set(row["codes"]) - declared)
                for value in row["argv"]:
                    path = ROOT / value
                    if value.startswith("fixtures/"):
                        self.assertTrue(path.is_file(), value)
                        self.assertLessEqual(path.stat().st_size, FIXTURE_LIMIT, value)


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = tool()
        cls.reports = [(row, cls.module.run(package_argv(row["argv"]))) for row in CONTRACT["fixtures"]]

    def test_known_good_fixtures_pass(self):
        for row, report in self.reports:
            if row["expect"] == "pass":
                with self.subTest(fixture=row["argv"]):
                    self.assertIs(report["ok"], True, report["failures"])
                    self.assertEqual(report["failures"], [])

    def test_known_wrong_fixtures_fail_with_declared_codes(self):
        for row, report in self.reports:
            if row["expect"] == "fail":
                with self.subTest(fixture=row["argv"]):
                    self.assertIs(report["ok"], False)
                    codes = {failure["code"] for failure in report["failures"]}
                    self.assertTrue(set(row["codes"]) <= codes, f"missing {set(row['codes']) - codes}, got {codes}")

    def test_reports_keep_the_contract(self):
        declared = set(CONTRACT["failures_detected"])
        for row, report in self.reports:
            with self.subTest(fixture=row["argv"]):
                self.assertEqual(report["tool"], IDENTITY)
                self.assertTrue(set(CONTRACT["report"]) <= set(report), set(CONTRACT["report"]) - set(report))
                self.assertTrue({failure["code"] for failure in report["failures"]} <= declared)
                json.dumps(report, allow_nan=False)

    def test_command_line_prints_a_report_and_sets_the_exit_status(self):
        first_pass = next(row for row in CONTRACT["fixtures"] if row["expect"] == "pass")
        first_fail = next(row for row in CONTRACT["fixtures"] if row["expect"] == "fail")
        for row, status in ((first_pass, 0), (first_fail, 1)):
            with self.subTest(fixture=row["argv"]):
                done = subprocess.run([sys.executable, "-E", "-s", "-B", str(ROOT / f"{IDENTITY}.py"),
                                       *package_argv(row["argv"])], cwd=ROOT, capture_output=True, text=True,
                                      timeout=60)
                self.assertEqual(done.returncode, status, done.stderr[-800:])
                self.assertEqual(json.loads(done.stdout)["ok"], status == 0)


if __name__ == "__main__":
    unittest.main()
