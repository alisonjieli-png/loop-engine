"""Tests for scripts/parse_dates.py. Effects: writes small synthetic CSV files inside a temporary directory and starts the script with the running Python interpreter; no network.

Run from the skill folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "parse_dates.py"
REFERENCE = PAYLOAD / "references" / "format-tokens.md"


def start(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class ParseDatesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="parse-dates-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def table(self, name: str, text: str) -> str:
        (self.root / name).write_bytes(text.encode("utf-8"))
        return name

    def parse(self, *arguments: str) -> tuple[int, dict]:
        finished = start("--root", str(self.root), *arguments)
        self.assertEqual(finished.stderr, "")
        return finished.returncode, json.loads(finished.stdout)

    def test_known_wrong_first_format_guess_is_held(self) -> None:
        name = self.table("orders.csv", "id,order_date\n1,03/04/2025\n")
        code, report = self.parse("--input", name, "--column", "order_date", "--format", "DD/MM/YYYY",
                                  "--format", "MM/DD/YYYY")
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "values_held")
        self.assertEqual(report["counts"], {"data_rows": 1, "empty": 0, "parsed": 0, "held": 1})
        held = report["held_values"][0]
        self.assertEqual(held["reason"], "ambiguous")
        self.assertEqual(held["readings"], {"DD/MM/YYYY": "2025-04-03", "MM/DD/YYYY": "2025-03-04"})
        self.assertEqual(held["first_data_rows"], [1])

    def test_single_valid_reading_parses_and_agreeing_readings_parse(self) -> None:
        name = self.table("orders.csv", "id,order_date\n1,12/31/2025\n2,25/12/2025\n3,05/05/2025\n")
        code, report = self.parse("--input", name, "--column", "order_date", "--format", "DD/MM/YYYY",
                                  "--format", "MM/DD/YYYY", "--output", "orders.dates.csv")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "all_parsed")
        self.assertEqual(report["parsed_by_format"], {"DD/MM/YYYY": 2, "MM/DD/YYYY": 1})
        self.assertEqual(report["mixed_conventions"], [])
        lines = (self.root / "orders.dates.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, ["id,order_date,order_date_iso", "1,12/31/2025,2025-12-31",
                                 "2,25/12/2025,2025-12-25", "3,05/05/2025,2025-05-05"])

    def test_mixed_conventions_are_reported(self) -> None:
        name = self.table("orders.csv", "order_date\n25/12/2025\n12/31/2025\n03/04/2025\n")
        code, report = self.parse("--input", name, "--column", "order_date", "--format", "DD/MM/YYYY",
                                  "--format", "MM/DD/YYYY")
        self.assertEqual(code, 1)
        self.assertEqual(report["mixed_conventions"], [{
            "formats": ["DD/MM/YYYY", "MM/DD/YYYY"], "rows_only_first_reads": 1, "rows_only_second_reads": 1,
            "rows_read_differently": 1}])

    def test_invalid_unmatched_empty_and_padded_values(self) -> None:
        name = self.table("events.csv", "day\n2025-02-30\n2024-02-29\nnext tuesday\n\n  2025-01-15  \n")
        code, report = self.parse("--input", name, "--column", "day", "--format", "YYYY-MM-DD")
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"], {"data_rows": 5, "empty": 1, "parsed": 2, "held": 2})
        reasons = {entry["value"]: entry["reason"] for entry in report["held_values"]}
        self.assertEqual(reasons, {"2025-02-30": "invalid_calendar_date",
                                   "next tuesday": "no_declared_format_matches"})
        counts = report["counts"]
        self.assertEqual(counts["parsed"] + counts["held"] + counts["empty"], counts["data_rows"])
        wide = self.table("wide.csv", "id,day\n1,2025-01-15\n\n2,2025-01-16\n")
        code, report = self.parse("--input", wide, "--column", "day", "--format", "YYYY-MM-DD")
        self.assertEqual((code, report["reason"]), (2, "row_width_differs"))
        self.assertIn("data row 2 is a blank line", report["detail"])

    def test_month_names_and_two_digit_years(self) -> None:
        name = self.table("mixed.csv", "day\n3 Apr 2025\n3 APR 2025\n3 Sept 2025\n")
        code, report = self.parse("--input", name, "--column", "day", "--format", "D MON YYYY")
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"]["parsed"], 2)
        self.assertEqual(report["held_values"][0]["value"], "3 Sept 2025")
        long_name = self.table("long.csv", "day\n\"April 3, 2025\"\n")
        code, report = self.parse("--input", long_name, "--column", "day", "--format", "MONTH D, YYYY",
                                  "--output", "long.out.csv")
        self.assertEqual(code, 0)
        self.assertIn("2025-04-03", (self.root / "long.out.csv").read_text(encoding="utf-8"))
        short_name = self.table("short.csv", "day\n03/04/49\n03/04/50\n")
        code, report = self.parse("--input", short_name, "--column", "day", "--format", "DD/MM/YY",
                                  "--two-digit-year-base", "1950", "--output", "short.out.csv")
        self.assertEqual(code, 0)
        text = (self.root / "short.out.csv").read_text(encoding="utf-8")
        self.assertIn("03/04/49,2049-04-03", text)
        self.assertIn("03/04/50,1950-04-03", text)
        code, report = self.parse("--input", short_name, "--column", "day", "--format", "DD/MM/YY")
        self.assertEqual((code, report["reason"]), (2, "two_digit_year_base_missing"))

    def test_declared_range_holds_placeholder_dates(self) -> None:
        name = self.table("people.csv", "joined\n01/01/1900\n14/02/2021\n")
        code, report = self.parse("--input", name, "--column", "joined", "--format", "DD/MM/YYYY",
                                  "--earliest", "2000-01-01", "--latest", "2030-12-31")
        self.assertEqual(code, 1)
        self.assertEqual(report["held_values"], [{"value": "01/01/1900", "reason": "outside_declared_range",
                                                  "count": 1, "first_data_rows": [1], "reading": "1900-01-01"}])

    def test_copy_round_trip_and_input_unchanged(self) -> None:
        name = self.table("orders.csv", "id,order_date,note\n1,14/02/2025,\"a, b\"\n2,03/04/2025,x\n3,,y\n")
        before = hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        code, report = self.parse("--input", name, "--column", "order_date", "--format", "DD/MM/YYYY",
                                  "--format", "MM/DD/YYYY", "--output", "orders.dates.csv")
        self.assertEqual(code, 1)
        self.assertEqual(report["input"]["sha256"], before)
        self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), before)
        copy_bytes = (self.root / "orders.dates.csv").read_bytes()
        self.assertEqual(report["output"]["sha256"], hashlib.sha256(copy_bytes).hexdigest())
        self.assertEqual(copy_bytes.decode("utf-8").splitlines()[1], '1,14/02/2025,"a, b",2025-02-14')
        code, again = self.parse("--input", "orders.dates.csv", "--column", "order_date_iso", "--format",
                                 "YYYY-MM-DD")
        self.assertEqual(code, 0)
        self.assertEqual(again["counts"]["held"], 0)
        self.assertEqual(again["counts"]["parsed"] + again["counts"]["empty"], 3)

    def test_crlf_and_byte_order_mark_are_kept_readable(self) -> None:
        (self.root / "windows.csv").write_bytes(b"\xef\xbb\xbfday\r\n2025-01-15\r\n")
        code, report = self.parse("--input", "windows.csv", "--column", "day", "--format", "YYYY-MM-DD",
                                  "--output", "windows.out.csv")
        self.assertEqual(code, 0)
        self.assertEqual((self.root / "windows.out.csv").read_bytes(), b"day,day_iso\r\n2025-01-15,2025-01-15\r\n")

    def test_refusals_write_nothing(self) -> None:
        self.table("orders.csv", "id,order_date\n1,03/04/2025\n")
        self.table("ragged.csv", "id,order_date\n1,03/04/2025,extra\n")
        self.table("exists.csv", "already here\n")
        (self.root / "latin.csv").write_bytes("day\ncaf\xe9\n".encode("latin-1"))
        cases = {
            "path_outside_root": ["--input", "../orders.csv", "--column", "order_date", "--format", "DD/MM/YYYY"],
            "column_missing": ["--input", "orders.csv", "--column", "Order Date", "--format", "DD/MM/YYYY"],
            "format_invalid": ["--input", "orders.csv", "--column", "order_date", "--format", "%d/%m/%Y"],
            "format_repeated": ["--input", "orders.csv", "--column", "order_date", "--format", "DD/MM/YYYY",
                                "--format", "DD/MM/YYYY"],
            "output_exists": ["--input", "orders.csv", "--column", "order_date", "--format", "DD/MM/YYYY",
                              "--output", "exists.csv"],
            "row_width_differs": ["--input", "ragged.csv", "--column", "order_date", "--format", "DD/MM/YYYY"],
            "input_not_utf8": ["--input", "latin.csv", "--column", "day", "--format", "DD/MM/YYYY"],
            "output_column_exists": ["--input", "orders.csv", "--column", "order_date", "--format", "DD/MM/YYYY",
                                     "--output", "new.csv", "--output-column", "id"],
            "arguments_invalid": ["--input", "orders.csv", "--column", "order_date"],
        }
        for reason, arguments in cases.items():
            with self.subTest(reason=reason):
                code, report = self.parse(*arguments)
                self.assertEqual((code, report["status"], report["reason"]), (2, "refused", reason))
        for text in ("dd/mm/yyyy", "YYYYMD", "DD/MM", "YYYY-MM-DD-DD"):
            with self.subTest(format=text):
                code, report = self.parse("--input", "orders.csv", "--column", "order_date", "--format", text)
                self.assertEqual((code, report["reason"]), (2, "format_invalid"))
        for text, found in (("DD/MM/YYYY MDT", "reads DD, MM, YYYY, M, D;"), ("Day DD/MM/YYYY", "reads D, DD, MM, YYYY;"),
                            ("yyyy-mm-dd", "reads no tokens;")):
            with self.subTest(format=text):
                code, report = self.parse("--input", "orders.csv", "--column", "order_date", "--format", text)
                self.assertEqual((code, report["reason"]), (2, "format_invalid"))
                self.assertIn(found, report["detail"])
        self.assertFalse((self.root / "new.csv").exists())
        self.assertEqual((self.root / "exists.csv").read_text(encoding="utf-8"), "already here\n")

    def test_symbolic_link_that_leaves_the_root_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="parse-dates-outside-") as outside:
            target = Path(outside) / "secret.csv"
            target.write_bytes(b"day\n2025-01-01\n")
            os.symlink(target, self.root / "linked.csv")
            code, report = self.parse("--input", "linked.csv", "--column", "day", "--format", "YYYY-MM-DD")
            self.assertEqual((code, report["reason"]), (2, "path_outside_root"))

    def test_documentation_matches_the_script(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        declared = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in ("HOLD_REASONS", "REFUSAL_REASONS"):
                declared[node.targets[0].id] = set(ast.literal_eval(node.value))
        raised = {node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "Refusal"
                  and node.args and isinstance(node.args[0], ast.Constant)}
        self.assertLessEqual(raised, declared["REFUSAL_REASONS"])
        reference = REFERENCE.read_text(encoding="utf-8")
        for reason in declared["HOLD_REASONS"] | declared["REFUSAL_REASONS"]:
            self.assertIn(f"`{reason}`", reference)
        help_text = start("--help").stdout
        skill = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        for flag in set(re.findall(r"--[a-z][a-z-]*[a-z]", skill + reference)):
            self.assertIn(flag, help_text)


if __name__ == "__main__":
    unittest.main()
