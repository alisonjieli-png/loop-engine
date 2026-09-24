"""Tests for scripts/check_column_contract.py. Effects: reads package files and starts the script with the current Python; writes nothing."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "check_column_contract.py"
with open(PACKAGE / "examples" / "column-contract.json", encoding="utf-8") as handle:
    CONTRACT = json.load(handle)

HEADER = "customer_id,signup_date,country,plan,monthly_spend,seats,is_active,email\n"
CLEAN = HEADER + (
    "C-0001,2021-03-14,DE,pro,49.00,3,true,ana@example.test\n"
    "C-0002,2019-11-02,US,free,0,1,false,\n"
    "C-0003,2024-07-30,FR,team,310.5,12,true,li@example.test\n"
    "C-0004,2016-01-09,GB,pro,NA,2,true,sam@example.test\n")


def run(*arguments, stdin=None):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=PACKAGE,
                              input=stdin, capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def run_bundle(table, contract=None, *arguments):
    bundle = {"csv": table, "contract": CONTRACT if contract is None else contract}
    return run("--bundle", "-", *arguments, stdin=json.dumps(bundle))


def contract_with(**changes):
    contract = json.loads(json.dumps(CONTRACT))
    contract.update(changes)
    return contract


def rules_of(report):
    return sorted((item.get("row"), item.get("column"), item["rule"]) for item in report["violations"])


class PassingTables(unittest.TestCase):
    def test_clean_table_passes(self):
        status, report = run_bundle(CLEAN)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failed_checks"], [])
        self.assertEqual(report["csv"]["rows"], 4)
        self.assertEqual(report["violations_total"], 0)
        self.assertEqual(report["empty_cells"], {"monthly_spend": 1, "email": 1})

    def test_contract_file_with_table_from_standard_input(self):
        status, report = run("--contract", "examples/column-contract.json", "--bundle", "-",
                             stdin=json.dumps({"csv": CLEAN}))
        self.assertEqual(status, 0, report)
        self.assertEqual(report["contract"]["path"], "examples/column-contract.json")

    def test_tab_delimiter_and_byte_order_mark(self):
        table = "\ufeff" + CLEAN.replace(",", "\t")
        status, report = run_bundle(table, None, "--delimiter", "tab")
        self.assertEqual(status, 0, report)
        self.assertTrue(report["csv"]["byte_order_mark"])


class KnownWrongTables(unittest.TestCase):
    def test_known_wrong_bundle_reports_each_violation_by_row_and_column(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(rules_of(report), [
            (2, "country", "allowed"), (3, "monthly_spend", "type"), (3, "signup_date", "type"),
            (4, "customer_id", "unique"), (4, "email", "trimmed"), (4, "is_active", "type"), (4, "seats", "min")])
        self.assertEqual(report["checks"]["type"], 3)
        self.assertEqual(sorted(report["failed_checks"]), ["allowed", "range", "trimmed", "type", "unique"])
        duplicate = next(item for item in report["violations"] if item["rule"] == "unique")
        self.assertEqual((duplicate["value"], duplicate["first_row"], duplicate["line"]), ("C-0002", 2, 5))

    def test_missing_column_reports_a_letter_case_hint(self):
        status, report = run_bundle(CLEAN.replace("country", "Country", 1))
        self.assertEqual(status, 1)
        missing = [item for item in report["violations"] if item["rule"] == "required_column_missing"]
        self.assertEqual(missing[0]["column"], "country")
        self.assertIn("'Country'", missing[0]["hint"])
        self.assertIn("country", report["contract_columns_not_checked"])
        self.assertEqual(report["checks"]["header"], 2)  # missing country and the extra Country column

    def test_semicolon_file_read_with_commas_gets_a_delimiter_hint(self):
        status, report = run_bundle(CLEAN.replace(",", ";"))
        self.assertEqual(status, 1)
        self.assertIn("--delimiter semicolon", report["violations"][0]["hint"])

    def test_typed_uniqueness_compares_values_not_text(self):
        contract = contract_with(columns=[{"name": "seats", "type": "integer", "unique": True}], extra_columns="allowed")
        table = "seats\n7\n007\n8\n"
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        self.assertEqual(rules_of(report), [(2, "seats", "unique")])

    def test_empty_rules_and_share(self):
        contract = contract_with(columns=[{"name": "a", "type": "string", "empty": "never"},
                                          {"name": "b", "type": "decimal", "max_empty_share": 0.25}],
                                 extra_columns="allowed", empty_values=["", "NA"])
        table = "a,b\nx,NA\n,1\ny,\nz,2\n"
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        self.assertEqual(report["checks"]["empty"], 1)
        self.assertEqual(report["checks"]["empty_share"], 1)
        share = next(item for item in report["violations"] if item["rule"] == "max_empty_share")
        self.assertEqual(share["value_share"], 0.5)

    def test_dates_must_match_the_format_and_range(self):
        contract = contract_with(columns=[{"name": "d", "type": "date", "min": "2020-01-01", "max": "2020-12-31"},
                                          {"name": "t", "type": "datetime", "format": "%d/%m/%Y %H:%M"}],
                                 extra_columns="allowed")
        table = "d,t\n2020-02-29,01/02/2020 10:30\n2020-2-28,1/02/2020 10:30\n2021-01-01,31/02/2020 10:30\n"
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        self.assertEqual(rules_of(report), [(2, "d", "type"), (2, "t", "type"), (3, "d", "max"), (3, "t", "type")])

    def test_extra_columns_order_and_field_count(self):
        contract = contract_with(columns=[{"name": "a", "type": "integer"}, {"name": "b", "type": "integer"}],
                                 extra_columns="not_allowed", column_order="as_listed")
        table = "b,a,c\n1,2,3\n4,5\n"
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        found = {item["rule"] for item in report["violations"]}
        self.assertEqual(found, {"extra_column", "column_order", "field_count"})
        width = next(item for item in report["violations"] if item["rule"] == "field_count")
        self.assertEqual((width["row"], width["expected"], width["found"]), (2, 3, 2))

    def test_quoted_line_breaks_keep_line_numbers_right(self):
        contract = contract_with(columns=[{"name": "note", "type": "string"}, {"name": "n", "type": "integer"}],
                                 extra_columns="allowed")
        table = 'note,n\n"two\nlines",1\nplain,x\n'
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        self.assertEqual((report["violations"][0]["row"], report["violations"][0]["line"]), (2, 4))
        status, report = run_bundle('note,n\n"two\nlines",x\n', contract)
        self.assertEqual((report["violations"][0]["row"], report["violations"][0]["line"]), (1, 2))

    def test_length_bounds_on_text(self):
        contract = contract_with(columns=[{"name": "code", "type": "string", "min_length": 2, "max_length": 3}],
                                 extra_columns="allowed")
        status, report = run_bundle("code\nA\nAB\nABCD\n", contract)
        self.assertEqual(status, 1)
        self.assertEqual(rules_of(report), [(1, "code", "min_length"), (3, "code", "max_length")])
        self.assertEqual(report["checks"]["length"], 2)

    def test_unique_together_skips_rows_with_an_empty_part(self):
        contract = contract_with(columns=[{"name": "shop", "type": "string"}, {"name": "day", "type": "date"}],
                                 extra_columns="allowed", unique_together=[["shop", "day"]])
        table = "shop,day\nS1,2024-01-01\nS1,2024-01-02\nS1,2024-01-01\n,2024-01-01\n,2024-01-01\n"
        status, report = run_bundle(table, contract)
        self.assertEqual(status, 1)
        self.assertEqual(report["checks"]["unique_together"], 1)
        item = next(item for item in report["violations"] if item["rule"] == "unique_together")
        self.assertEqual((item["row"], item["first_row"], item["columns"]), (3, 1, ["shop", "day"]))

    def test_row_count_bounds(self):
        contract = contract_with(columns=[{"name": "n", "type": "integer"}], extra_columns="allowed",
                                 row_count={"min": 2, "max": 3})
        for table, expected in (("n\n1\n", 1), ("n\n1\n2\n", 0), ("n\n1\n2\n3\n", 0), ("n\n1\n2\n3\n4\n", 1)):
            status, report = run_bundle(table, contract)
            self.assertEqual(status, expected, (table, report))
        self.assertEqual(report["violations"][0]["rows"], 4)

    def test_optional_column_may_be_absent_but_is_listed(self):
        contract = contract_with(columns=[{"name": "a", "type": "integer"},
                                          {"name": "b", "type": "integer", "required": False}],
                                 extra_columns="allowed")
        status, report = run_bundle("a\n1\n", contract)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["contract_columns_not_checked"], ["b"])

    def test_repeated_header_name_fails_and_its_rules_do_not_run(self):
        contract = contract_with(columns=[{"name": "a", "type": "integer"}], extra_columns="allowed")
        status, report = run_bundle("a,a\n1,x\n", contract)
        self.assertEqual(status, 1, report)
        self.assertEqual([item["rule"] for item in report["violations"]], ["duplicate_column_name"])
        self.assertEqual(report["contract_columns_not_checked"], ["a"])

    def test_examples_are_bounded_but_counts_stay_complete(self):
        contract = contract_with(columns=[{"name": "n", "type": "integer"}], extra_columns="allowed")
        table = "n\n" + "x\n" * 100
        status, report = run_bundle(table, contract, "--max-examples", "5")
        self.assertEqual(status, 1)
        self.assertEqual(report["violations_total"], 100)
        self.assertEqual(report["violations_shown"], 3)
        self.assertEqual(report["violations_by_column"], {"n": {"type": 100}})

    def test_blank_line_in_a_one_column_table_is_an_empty_value(self):
        contract = contract_with(columns=[{"name": "code", "type": "string", "empty": "never"}], extra_columns="allowed")
        status, report = run_bundle("code\nA1\n\nB2\n", contract)
        self.assertEqual(status, 1, report)
        self.assertEqual(rules_of(report), [(2, "code", "empty")])
        self.assertEqual(report["csv"]["rows"], 3)

    def test_no_values_hides_cell_text(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", "--no-values")
        self.assertEqual(status, 1)
        allowed = next(item for item in report["violations"] if item["rule"] == "allowed")
        self.assertEqual(allowed["value"], {"characters": 7})
        self.assertNotIn("Germany", json.dumps(report))


class RefusedInputs(unittest.TestCase):
    def assert_refused(self, status, report, reason):
        self.assertEqual(status, 2, report)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], reason, report)

    def test_misspelled_contract_key_is_refused(self):
        contract = contract_with(columns=[{"name": "country", "type": "string", "alowed": ["DE"]}])
        status, report = run_bundle(CLEAN, contract)
        self.assert_refused(status, report, "contract_invalid")
        self.assertIn("alowed", report["detail"])

    def test_misspelled_top_level_key_is_refused(self):
        status, report = run_bundle(CLEAN, contract_with(extra_colums="not_allowed"))
        self.assert_refused(status, report, "contract_invalid")
        self.assertIn("extra_colums", report["detail"])

    def test_size_bound_refuses_instead_of_truncating(self):
        status, report = run("--csv", "SKILL.md", "--contract", "examples/column-contract.json", "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")
        status, report = run_bundle(CLEAN, None, "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")

    def test_unknown_type_and_range_on_text_are_refused(self):
        for column in ({"name": "a", "type": "int"}, {"name": "a", "type": "string", "min": 1},
                       {"name": "a", "type": "date", "min": "01/01/2020"},
                       {"name": "a", "type": "string", "allowed": [1, 2]}):
            status, report = run_bundle("a\n1\n", contract_with(columns=[column]))
            self.assert_refused(status, report, "contract_invalid")

    def test_missing_and_escaping_paths_are_refused(self):
        status, report = run("--csv", "examples/none.csv", "--contract", "examples/column-contract.json")
        self.assert_refused(status, report, "input_missing")
        status, report = run("--csv", "../SKILL.md", "--contract", "examples/column-contract.json")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--csv", sys.executable, "--contract", "examples/column-contract.json")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--csv", "examples", "--contract", "examples/column-contract.json")
        self.assert_refused(status, report, "not_a_regular_file")

    @unittest.skipUnless(os.path.islink("/proc/self"), "needs the Linux /proc/self link")
    def test_symbolic_link_that_leaves_the_root_is_refused(self):
        # /proc/self/root is a link to the file system root, so this path leaves --root /proc.
        status, report = run("--root", "/proc", "--csv", "self/root" + str(SCRIPT), "--bundle", "-",
                             stdin=json.dumps({"contract": CONTRACT}))
        self.assert_refused(status, report, "path_leaves_root")

    def test_broken_csv_text_and_arguments_are_refused(self):
        status, report = run_bundle('customer_id\n"C-1\n')
        self.assert_refused(status, report, "malformed_csv")
        status, report = run("--bundle", "-", stdin='{"csv": "a\\n\\ud800\\n", "contract": {}}')
        self.assert_refused(status, report, "contract_invalid")
        status, report = run("--bundle", "-", stdin=json.dumps({"csv": "a\n\ud800\n", "contract": CONTRACT}))
        self.assert_refused(status, report, "not_utf8")
        status, report = run_bundle("")
        self.assert_refused(status, report, "input_empty")
        status, report = run("--csv", "x.csv", "--bundle", "examples/known-wrong-bundle.json")
        self.assert_refused(status, report, "bad_arguments")
        status, report = run("--no-such-flag")
        self.assert_refused(status, report, "bad_arguments")
        status, report = run("--bundle", "-", stdin='{"csv": "a\\n", "contract": {}, "extra": 1}')
        self.assert_refused(status, report, "bundle_invalid")

    def test_compressed_table_is_refused(self):
        status, report = run_bundle("PK\x03\x04 packed table")
        self.assert_refused(status, report, "compressed_input")


class Documentation(unittest.TestCase):
    def test_every_documented_option_is_accepted_by_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        self.assertEqual(finished.returncode, 0)
        for name in ("SKILL.md", "references/contract-format.md", "references/checklist.md"):
            with open(PACKAGE / name, encoding="utf-8") as handle:
                text = handle.read()
            for option in sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", text))):
                self.assertIn(option, finished.stdout, f"{name} mentions {option}")

    def test_the_example_contract_is_valid(self):
        status, report = run_bundle(CLEAN, CONTRACT)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["contract"]["columns"], len(CONTRACT["columns"]))


if __name__ == "__main__":
    unittest.main()
