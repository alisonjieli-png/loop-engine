"""Tests for scripts/verify_change_log.py. Effects: reads package files and starts the script with the current Python; writes nothing."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "verify_change_log.py"
with open(PACKAGE / "examples" / "cleaning-bundle.json", encoding="utf-8") as handle:
    GOOD = json.load(handle)

SOURCE = "id,city,score\nA1,Lyon ,7\nA2,Paris,8\nA3,Nice,9\n"


def run(*arguments, stdin=None):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=PACKAGE,
                              input=stdin, capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def check(source, cleaned, log, *arguments, keys=("id",)):
    options = [item for key in keys for item in ("--key", key)]
    bundle = {"source": source, "cleaned": cleaned, "log": log}
    return run("--bundle", "-", *options, *arguments, stdin=json.dumps(bundle))


def lines(*entries):
    return "".join(json.dumps(entry) + "\n" for entry in entries)


def rules(report):
    return sorted(item["rule"] for item in report["violations"])


class Passing(unittest.TestCase):
    def test_example_cleaning_passes(self):
        status, report = run("--bundle", "examples/cleaning-bundle.json", "--key", "customer_id")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["rows_matched"], 5)
        self.assertEqual(report["summary"]["rows_removed"], 1)
        self.assertEqual(report["summary"]["cells_changed"], 3)
        self.assertEqual(report["log"]["format"], "json_lines")

    def test_row_numbers_json_array_and_order_change(self):
        cleaned = "id,city,score\nA3,Nice,9\nA1,Lyon,7\nA2,Paris,8\n"
        log = json.dumps([{"row": 1, "column": "city", "before": "Lyon ", "after": "Lyon"}])
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["log"]["format"], "json_array")
        self.assertTrue(report["summary"]["row_order_changed"])

    def test_csv_log_with_rows_added_and_removed(self):
        cleaned = "id,city,score\nA1,Lyon,7\nA3,Nice,9\nA4,Metz,6\n"
        log = ("key,row,change,column,before,after,reason\n"
               "A1,,cell,city,Lyon ,Lyon,trim\n"
               ",2,row_removed,,,,duplicate\n"
               "A4,,row_added,,,,late record\n")
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["log"]["format"], "csv")
        self.assertEqual((report["summary"]["rows_removed"], report["summary"]["rows_added"]), (1, 1))

    def test_logged_key_change_moves_the_match(self):
        cleaned = "id,city,score\nA-1,Lyon ,7\nA2,Paris,8\nA3,Nice,9\n"
        status, report = check(SOURCE, cleaned, lines({"key": "A1", "column": "id", "before": "A1", "after": "A-1"}))
        self.assertEqual(status, 0, report)
        status, report = check(SOURCE, cleaned, "")
        self.assertEqual(status, 1)
        self.assertEqual(rules(report), ["row_added_without_log", "row_removed_without_log"])

    def test_composite_key_as_list_and_object(self):
        source = "shop,day,sales\nS1,2024-01-01,5\nS1,2024-01-02,6\nS2,2024-01-01,7\n"
        cleaned = "shop,day,sales\nS1,2024-01-01,5\nS1,2024-01-02,60\nS2,2024-01-01,70\n"
        log = lines({"key": ["S1", "2024-01-02"], "column": "sales", "before": "6", "after": "60"},
                    {"key": {"day": "2024-01-01", "shop": "S2"}, "column": "sales", "before": "7", "after": "70"})
        status, report = check(source, cleaned, log, keys=("shop", "day"))
        self.assertEqual(status, 0, report)

    def test_added_column_with_its_log_entry_and_matching_digest(self):
        cleaned = "id,city,score,city_code\nA1,Lyon ,7,LY\nA2,Paris,8,PA\nA3,Nice,9,NI\n"
        digest = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
        status, report = check(SOURCE, cleaned, lines({"change": "column_added", "column": "city_code"}),
                               "--source-sha256", digest)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["checks"]["source_digest_differs"], 0)


class KnownWrong(unittest.TestCase):
    def test_known_wrong_example_finds_the_unlogged_row_and_cell(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", "--key", "customer_id")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["row_removed_without_log", "cell_changed_without_log"])
        found = {(item["rule"], tuple(item["key"]), item.get("column")) for item in report["violations"]}
        self.assertEqual(found, {("row_removed_without_log", ("C-0042",), None),
                                 ("cell_changed_without_log", ("C-0007",), "phone")})
        cell = next(item for item in report["violations"] if item["rule"] == "cell_changed_without_log")
        self.assertEqual((cell["source_value"], cell["cleaned_value"]), ("N/A", ""))

    def test_log_values_must_match_both_tables(self):
        cleaned = "id,city,score\nA1,Lyon,7\nA2,Paris,8\nA3,Nice,9\n"
        log = lines({"key": "A1", "column": "city", "before": "Lyon", "after": "LYON"})
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 1)
        self.assertEqual(rules(report), ["log_after_mismatch", "log_before_mismatch"])

    def test_repeated_column_and_added_row_entries(self):
        cleaned = "id,city,score,code\nA1,Lyon ,7,x\nA2,Paris,8,y\nA3,Nice,9,z\nA4,Metz,6,w\n"
        log = lines({"change": "column_added", "column": "code"}, {"change": "column_added", "column": "code"},
                    {"change": "row_added", "key": "A4"}, {"change": "row_added", "key": "A4"})
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["duplicate_log_entry"])
        self.assertEqual(report["checks"]["duplicate_log_entry"], 2)
        found = sorted((item.get("column", ""), tuple(item.get("key", ())), item["first_log_entry"], item["log_entry"])
                       for item in report["violations"])
        self.assertEqual(found, [("", ("A4",), 3, 4), ("code", (), 1, 2)])

    def test_claims_about_rows_that_do_not_hold(self):
        cleaned = "id,city,score\nA1,Lyon ,7\nA2,Paris,8\nA3,Nice,9\n"
        log = lines({"change": "row_removed", "key": "A2"}, {"change": "row_added", "key": "A9"},
                    {"change": "row_added", "key": "A3"}, {"row": 7, "column": "city", "before": "x", "after": "y"},
                    {"key": "Z1", "column": "city", "before": "x", "after": "y"},
                    {"key": "A1", "column": "score", "before": "7", "after": "7"},
                    {"key": "A1", "column": "score", "before": "7", "after": "7"})
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), [
            "duplicate_log_entry", "log_added_row_missing", "log_added_row_not_new", "log_removed_row_still_present",
            "log_row_not_in_source"])
        self.assertEqual(report["checks"]["log_row_not_in_source"], 2)
        self.assertEqual(report["warnings"]["log_entries_that_change_nothing"], 1)

    def test_columns_need_log_entries_and_entries_must_be_true(self):
        cleaned = "id,city,region\nA1,Lyon ,R1\nA2,Paris,R2\nA3,Nice,R3\n"
        log = lines({"change": "column_removed", "column": "region"}, {"change": "column_added", "column": "score"},
                    {"key": "A1", "column": "region", "before": "", "after": "R1"})
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), [
            "column_added_without_log", "column_removed_without_log", "log_column_claim_wrong",
            "log_column_not_in_both_tables"])
        self.assertEqual(report["checks"]["log_column_claim_wrong"], 2)

    def test_repeated_and_empty_keys_in_the_cleaned_copy(self):
        cleaned = "id,city,score\nA1,Lyon ,7\nA2,Paris,8\nA2,Paris,8\n,Nice,9\n"
        status, report = check(SOURCE, cleaned, "")
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), ["duplicate_key_in_cleaned", "empty_key_in_cleaned",
                                                           "row_removed_without_log"])

    def test_logged_key_changes_that_collide(self):
        cleaned = "id,city,score\nA2,Lyon ,7\nA3,Nice,9\n"
        log = lines({"key": "A1", "column": "id", "before": "A1", "after": "A2"})
        status, report = check(SOURCE, cleaned, log)
        self.assertEqual(status, 1)
        self.assertIn("logged_keys_collide", report["failed_checks"])

    def test_source_digest_that_differs(self):
        status, report = check(SOURCE, SOURCE.replace("Lyon ", "Lyon"),
                               lines({"row": 1, "column": "city", "before": "Lyon ", "after": "Lyon"}),
                               "--source-sha256", "0" * 64)
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["source_digest_differs"])

    def test_no_values_hides_keys_and_cells(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", "--key", "customer_id", "--no-values")
        self.assertEqual(status, 1)
        text = json.dumps(report["violations"])
        self.assertNotIn("C-0042", text)
        self.assertNotIn("N/A", text)
        self.assertIn('{"characters": 6}', text)


class Refusals(unittest.TestCase):
    def assert_refused(self, status, report, reason):
        self.assertEqual(status, 2, report)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], reason, report)

    def test_source_keys_must_identify_every_row(self):
        self.assert_refused(*check("id,x\nA1,1\nA1,2\n", "id,x\nA1,1\n", ""), "duplicate_key_in_source")
        self.assert_refused(*check("id,x\n,1\n", "id,x\n,1\n", ""), "empty_key_in_source")
        self.assert_refused(*check("code,x\nA1,1\n", "code,x\nA1,1\n", ""), "key_column_missing")

    def test_malformed_logs_are_refused(self):
        cleaned = SOURCE.replace("Lyon ", "Lyon")
        for log in (lines({"key": "A1", "column": "score", "before": 7, "after": "8"}),
                    lines({"key": "A1", "row": 1, "column": "city", "before": "Lyon ", "after": "Lyon"}),
                    lines({"key": "A1", "column": "city", "after": "Lyon"}),
                    lines({"change": "renamed", "key": "A1", "column": "city"}),
                    lines({"change": "row_added", "row": 2}),
                    '{"key": "A1",\n "column": "city"}\n',
                    "note\nsomething\n"):
            status, report = check(SOURCE, cleaned, log)
            self.assertEqual(status, 2, (log, report))
            self.assertIn(report["reason"], ("log_invalid", "json_invalid"), report)

    def test_csv_log_cannot_write_a_key_of_several_columns(self):
        status, report = check("a,b,x\n1,2,3\n", "a,b,x\n1,2,4\n", "key,column,before,after\n1,x,3,4\n",
                               keys=("a", "b"))
        self.assert_refused(status, report, "log_invalid")
        self.assertIn("JSON Lines", report["detail"])
        status, report = check("a,b,x\n1,2,3\n", "a,b,x\n1,2,4\n", "row,column,before,after\n1,x,3,4\n",
                               keys=("a", "b"))
        self.assertEqual(status, 0, report)

    def test_same_file_paths_and_arguments(self):
        status, report = run("--source", "SKILL.md", "--cleaned", "SKILL.md", "--log", "SKILL.md", "--key", "id")
        self.assert_refused(status, report, "same_file")
        status, report = run("--source", "../SKILL.md", "--cleaned", "SKILL.md", "--log", "SKILL.md", "--key", "id")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--source", "examples/none.csv", "--cleaned", "SKILL.md", "--log", "SKILL.md",
                             "--key", "id")
        self.assert_refused(status, report, "input_missing")
        status, report = run("--bundle", "examples/cleaning-bundle.json")
        self.assert_refused(status, report, "bad_arguments")
        status, report = run("--bundle", "examples/cleaning-bundle.json", "--key", "customer_id",
                             "--source-sha256", "abc")
        self.assert_refused(status, report, "bad_arguments")

    @unittest.skipUnless(os.path.islink("/proc/self/root"), "needs the Linux /proc/self/root link")
    def test_symbolic_link_that_leaves_the_root_is_refused(self):
        # /proc/self/root is a link to the file system root, so this path leaves --root /proc.
        status, report = run("--root", "/proc", "--source", "self/root" + str(SCRIPT), "--bundle", "-",
                             "--key", "id", stdin=json.dumps({"cleaned": SOURCE, "log": ""}))
        self.assert_refused(status, report, "path_leaves_root")

    def test_ragged_and_compressed_tables_are_refused(self):
        self.assert_refused(*check(SOURCE, "id,city,score\nA1,Lyon\n", ""), "ragged_rows")
        self.assert_refused(*check(SOURCE, "PK\x03\x04 packed", ""), "compressed_input")

    def test_size_bound_refuses_instead_of_truncating(self):
        status, report = run("--source", "SKILL.md", "--cleaned", "references/log-format.md", "--log",
                             "references/checklist.md", "--key", "id", "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")
        self.assertIn("SKILL.md", report["detail"])


class Documentation(unittest.TestCase):
    def test_every_documented_option_is_accepted_by_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        self.assertEqual(finished.returncode, 0)
        for name in ("SKILL.md", "references/log-format.md", "references/checklist.md"):
            with open(PACKAGE / name, encoding="utf-8") as handle:
                text = handle.read()
            for option in sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]+", text))):
                self.assertIn(option, finished.stdout, f"{name} mentions {option}")

    def test_every_check_name_in_the_format_reference_exists(self):
        with open(PACKAGE / "references" / "log-format.md", encoding="utf-8") as handle:
            text = handle.read()
        status, report = run("--bundle", "examples/cleaning-bundle.json", "--key", "customer_id")
        for name in report["checks"]:
            self.assertIn(f"`{name}`", text, f"references/log-format.md does not explain {name}")


if __name__ == "__main__":
    unittest.main()
