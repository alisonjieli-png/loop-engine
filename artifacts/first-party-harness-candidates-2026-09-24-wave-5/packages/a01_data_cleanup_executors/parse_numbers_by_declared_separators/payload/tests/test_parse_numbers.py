"""Tests for scripts/parse_numbers.py. Effects: writes small synthetic CSV files inside a temporary directory and starts the script with the running Python interpreter; no network.

Run from the skill folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
import csv
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
SCRIPT = PAYLOAD / "scripts" / "parse_numbers.py"
REFERENCE = PAYLOAD / "references" / "marks-and-reasons.md"
US = ("--decimal-mark", "period", "--grouping-mark", "comma")
EUROPE = ("--decimal-mark", "comma", "--grouping-mark", "period")


def start(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class ParseNumbersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="parse-numbers-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def column(self, *values: str) -> str:
        """Write a one-column CSV named amounts.csv and return its name."""
        lines = ["amount"] + ['"' + value.replace('"', '""') + '"' for value in values]
        (self.root / "amounts.csv").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        return "amounts.csv"

    def parse(self, *arguments: str) -> tuple[int, dict]:
        finished = start("--root", str(self.root), *arguments)
        self.assertEqual(finished.stderr, "")
        return finished.returncode, json.loads(finished.stdout)

    def readings(self, *arguments: str) -> dict:
        """Map each value to its parsed number or to its hold reason."""
        code, report = self.parse(*arguments, "--output", "out.csv")
        self.assertIn(code, (0, 1))
        with open(self.root / "out.csv", newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))[1:]
        (self.root / "out.csv").unlink()
        reasons = {entry["value"]: entry["reason"] for entry in report["held_values"]}
        return {raw: number or reasons.get(raw.strip(), "") for raw, number in rows}

    def test_known_wrong_other_convention_is_held_not_stripped(self) -> None:
        name = self.column("1.234,56", "1,234.56")
        code, report = self.parse("--input", name, "--column", "amount", *US)
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"], {"data_rows": 2, "empty": 0, "parsed": 1, "held": 1})
        held = report["held_values"][0]
        self.assertEqual((held["value"], held["reason"], held["other_reading"]),
                         ("1.234,56", "other_convention", "1234.56"))

    def test_known_wrong_mixed_column_holds_values_both_conventions_read(self) -> None:
        name = self.column("1,234.56", "1.234,56", "2,500", "3,000", "12,5")
        code, report = self.parse("--input", name, "--column", "amount", *US, "--output", "out.csv")
        self.assertEqual(code, 1)
        self.assertTrue(report["column_mixes_conventions"])
        self.assertEqual(report["convention_sensitive_parsed"], 0)
        self.assertEqual((report["held_by_reason"]["other_convention"], report["held_by_reason"]["convention_sensitive"]),
                         (2, 2))
        held = {entry["value"]: entry for entry in report["held_values"]}
        self.assertEqual(held["2,500"], {"value": "2,500", "reason": "convention_sensitive", "count": 1,
                                         "first_data_rows": [3], "declared_reading": "2500", "other_reading": "2.500"})
        lines = (self.root / "out.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, ["amount,amount_number", '"1,234.56",1234.56', '"1.234,56",', '"2,500",', '"3,000",',
                                 '"12,5",'])

    def test_declared_european_marks(self) -> None:
        name = self.column("1.234,56", "0,5", "12,50 \N{EURO SIGN}", "1,234.56", "-3,00")
        result = self.readings("--input", name, "--column", "amount", *EUROPE, "--currency", "\N{EURO SIGN}")
        self.assertEqual(result, {"1.234,56": "1234.56", "0,5": "0.5", "12,50 \N{EURO SIGN}": "12.50",
                                  "1,234.56": "other_convention", "-3,00": "-3.00"})

    def test_convention_sensitive_values_are_counted_and_can_be_held(self) -> None:
        name = self.column("1,000", "1.5", "250")
        code, report = self.parse("--input", name, "--column", "amount", *US)
        self.assertEqual((code, report["convention_sensitive_parsed"], report["column_mixes_conventions"]),
                         (0, 1, False))
        code, report = self.parse("--input", name, "--column", "amount", *US, "--hold-convention-sensitive")
        self.assertEqual(code, 1)
        self.assertEqual(report["held_values"], [{"value": "1,000", "reason": "convention_sensitive", "count": 1,
                                                  "first_data_rows": [1], "declared_reading": "1000",
                                                  "other_reading": "1.000"}])

    def test_grouping_styles_and_marks(self) -> None:
        name = self.column("12,34,567", "1,23", "1,234,567")
        result = self.readings("--input", name, "--column", "amount", *US)
        self.assertEqual(result, {"12,34,567": "grouping_mismatch", "1,23": "other_convention",
                                  "1,234,567": "1234567"})
        result = self.readings("--input", name, "--column", "amount", *US, "--group-style", "indian")
        self.assertEqual(result["12,34,567"], "1234567")
        name = self.column("1 234,5", "1\N{NO-BREAK SPACE}234,5", "1.234,5")
        result = self.readings("--input", name, "--column", "amount", "--decimal-mark", "comma",
                               "--grouping-mark", "space")
        self.assertEqual(result, {"1 234,5": "1234.5", "1\N{NO-BREAK SPACE}234,5": "1234.5", "1.234,5": "undeclared_character"})
        name = self.column("1'234.50", "1234.50")
        result = self.readings("--input", name, "--column", "amount", "--decimal-mark", "period",
                               "--grouping-mark", "apostrophe")
        self.assertEqual(result, {"1'234.50": "1234.50", "1234.50": "1234.50"})

    def test_currency_signs_percent_and_parentheses(self) -> None:
        name = self.column("$1,234.50", "-$5", "$-5", "USD 7", "7 usd", "\N{EURO SIGN}5", "$5 USD", "\N{MINUS SIGN}5",
                           "-0.00", "- $5", "$- 5", "1$000")
        result = self.readings("--input", name, "--column", "amount", *US, "--currency", "$", "--currency", "USD")
        self.assertEqual(result, {"$1,234.50": "1234.50", "-$5": "-5", "$-5": "-5", "USD 7": "7", "7 usd": "7",
                                  "\N{EURO SIGN}5": "undeclared_character", "$5 USD": "currency_repeated",
                                  "\N{MINUS SIGN}5": "-5", "-0.00": "0.00", "- $5": "space_after_sign",
                                  "$- 5": "space_after_sign", "1$000": "currency_misplaced"})
        name = self.column("12.5%", "12.5")
        self.assertEqual(self.readings("--input", name, "--column", "amount", *US, "--percent-sign", "divide"),
                         {"12.5%": "0.125", "12.5": "percent_sign_missing"})
        self.assertEqual(self.readings("--input", name, "--column", "amount", *US, "--percent-sign", "strip"),
                         {"12.5%": "12.5", "12.5": "12.5"})
        self.assertEqual(self.readings("--input", name, "--column", "amount", *US),
                         {"12.5%": "percent_sign_not_declared", "12.5": "12.5"})
        name = self.column("(1,234.50)", "-(5)", "(-5)", "$(1,234.50)")
        self.assertEqual(self.readings("--input", name, "--column", "amount", *US, "--negative-parentheses",
                                       "--currency", "$"),
                         {"(1,234.50)": "-1234.50", "-(5)": "parentheses_misplaced", "(-5)": "sign_repeated",
                          "$(1,234.50)": "parentheses_misplaced"})
        self.assertEqual(self.readings("--input", name, "--column", "amount", *US)["(1,234.50)"],
                         "parentheses_not_declared")

    def test_leading_zeros_and_malformed_values(self) -> None:
        name = self.column("007", "5.", "1.2.3", ".5", "1e5", "abc")
        result = self.readings("--input", name, "--column", "amount", *US)
        self.assertEqual(result, {"007": "leading_zero", "5.": "decimal_mark_without_digits",
                                  "1.2.3": "decimal_mark_repeated", ".5": "0.5", "1e5": "undeclared_character",
                                  "abc": "no_digits"})
        result = self.readings("--input", name, "--column", "amount", *US, "--allow-leading-zeros")
        self.assertEqual(result["007"], "7")

    def test_copy_round_trip_and_input_unchanged(self) -> None:
        (self.root / "sales.csv").write_bytes(b'id,amount\n1,"1,234.50"\n2,-7\n3,\n4,"1.234,56"\n')
        before = hashlib.sha256((self.root / "sales.csv").read_bytes()).hexdigest()
        code, report = self.parse("--input", "sales.csv", "--column", "amount", *US, "--output", "sales.out.csv")
        self.assertEqual(code, 1)
        self.assertEqual(report["input"]["sha256"], before)
        self.assertEqual(hashlib.sha256((self.root / "sales.csv").read_bytes()).hexdigest(), before)
        copy_bytes = (self.root / "sales.out.csv").read_bytes()
        self.assertEqual(report["output"]["sha256"], hashlib.sha256(copy_bytes).hexdigest())
        self.assertEqual(copy_bytes.decode("utf-8").splitlines(),
                         ["id,amount,amount_number", '1,"1,234.50",1234.50', "2,-7,-7", "3,,", '4,"1.234,56",'])
        code, again = self.parse("--input", "sales.out.csv", "--column", "amount_number", "--decimal-mark",
                                 "period", "--grouping-mark", "none")
        self.assertEqual((code, again["counts"]["held"], again["counts"]["parsed"]), (0, 0, 2))

    def test_refusals_write_nothing(self) -> None:
        name = self.column("1")
        (self.root / "exists.csv").write_bytes(b"already here\n")
        cases = {
            "marks_conflict": ["--decimal-mark", "comma", "--grouping-mark", "comma"],
            "currency_invalid": [*US, "--currency", "US 1"],
            "path_outside_root": [*US, "--input", "../amounts.csv"],
            "column_missing": [*US, "--column", "Amount"],
            "output_exists": [*US, "--output", "exists.csv"],
            "arguments_invalid": ["--decimal-mark", "dot", "--grouping-mark", "comma"],
        }
        for reason, arguments in cases.items():
            with self.subTest(reason=reason):
                base = ["--input", name, "--column", "amount"]
                code, report = self.parse(*base, *arguments)
                self.assertEqual((code, report["status"], report["reason"]), (2, "refused", reason))
        self.assertEqual((self.root / "exists.csv").read_bytes(), b"already here\n")
        (self.root / "blank.csv").write_bytes(b"id,amount\n1,5\n\n")
        code, report = self.parse("--input", "blank.csv", "--column", "amount", *US, "--output", "never.csv")
        self.assertEqual((code, report["reason"]), (2, "row_width_differs"))
        self.assertIn("data row 2 is a blank line", report["detail"])
        self.assertFalse((self.root / "never.csv").exists())

    def test_symbolic_link_that_leaves_the_root_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="parse-numbers-outside-") as outside:
            target = Path(outside) / "private.csv"
            target.write_bytes(b"amount\n1\n")
            os.symlink(target, self.root / "linked.csv")
            code, report = self.parse("--input", "linked.csv", "--column", "amount", *US)
            self.assertEqual((code, report["reason"]), (2, "path_outside_root"))

    def test_documentation_matches_the_script(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        declared = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in ("HOLD_REASONS", "REFUSAL_REASONS"):
                declared[node.targets[0].id] = set(ast.literal_eval(node.value))
        called = {node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id in ("Refusal", "held")
                  and node.args and isinstance(node.args[0], ast.Constant)}
        self.assertLessEqual(called, declared["REFUSAL_REASONS"] | declared["HOLD_REASONS"])
        reference = REFERENCE.read_text(encoding="utf-8")
        for reason in declared["HOLD_REASONS"] | declared["REFUSAL_REASONS"]:
            self.assertIn(f"`{reason}`", reference)
        help_text = start("--help").stdout
        skill = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        for flag in set(re.findall(r"--[a-z][a-z-]*[a-z]", skill + reference)):
            self.assertIn(flag, help_text)


if __name__ == "__main__":
    unittest.main()
