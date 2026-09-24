"""Tests for scripts/validate_submission.py. Effects: reads package files and starts the script with the current Python; writes nothing."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "validate_submission.py"
with open(PACKAGE / "examples" / "submission-bundle.json", encoding="utf-8") as handle:
    GOOD = json.load(handle)
SAMPLE = GOOD["sample"]
SUBMISSION = GOOD["submission"]
CLASSES_SAMPLE = "id,low,medium,high\n1,0.33,0.33,0.34\n2,0.33,0.33,0.34\n3,0.33,0.33,0.34\n"


def run(*arguments, stdin=None):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=PACKAGE,
                              input=stdin, capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def check(submission, sample, *arguments):
    return run("--bundle", "-", *arguments, stdin=json.dumps({"submission": submission, "sample": sample}))


def rules(report):
    return sorted({item["rule"] for item in report["violations"]})


class Passing(unittest.TestCase):
    def test_example_submission_passes(self):
        status, report = run("--bundle", "examples/submission-bundle.json", "--task", "probability")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["failed_checks"], [])
        self.assertEqual((report["id_column"], report["prediction_columns"]), ("id", ["target"]))
        self.assertEqual(report["submission"]["rows"], 12)
        self.assertEqual(report["warnings"], [])
        self.assertIn("not attempted", report["upload"])

    def test_each_task_type_accepts_a_valid_file(self):
        cases = (
            ("id,low,medium,high\n1,0.2,0.3,0.5\n2,0.1,0.1,0.8\n3,1,0,0\n", CLASSES_SAMPLE,
             ("--task", "class_probabilities")),
            ("id,need\n1,Low\n2,High\n", "id,need\n1,Low\n2,Low\n", ("--task", "label", "--labels", "Low", "High")),
            ("id,y\n1,3.5\n2,1e2\n", "id,y\n1,0\n2,0\n", ("--task", "number", "--min", "0", "--max", "100")),
            ("id,answer\n1,blue\n2,red\n", "id,answer\n1,x\n2,x\n", ("--task", "text")),
        )
        for submission, sample, arguments in cases:
            status, report = check(submission, sample, *arguments)
            self.assertEqual(status, 0, (arguments, report))

    def test_other_row_order_is_a_warning_unless_the_order_is_required(self):
        submission = "id,target\n" + "".join(reversed(SUBMISSION.splitlines(keepends=True)[1:]))
        status, report = check(submission, SAMPLE, "--task", "probability")
        self.assertEqual(status, 0, report)
        self.assertTrue(any("sample order" in warning for warning in report["warnings"]))
        status, report = check(submission, SAMPLE, "--task", "probability", "--require-same-order")
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["row_order"])

    def test_id_column_that_is_not_first(self):
        sample = "target,key\n0.5,a\n0.5,b\n"
        status, report = check("target,key\n0.1,b\n0.9,a\n", sample, "--task", "probability", "--id-column", "key")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["prediction_columns"], ["target"])


class KnownWrong(unittest.TestCase):
    def test_known_wrong_example_index_column_and_float_ids(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", "--task", "probability")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["failed_checks"], ["header", "missing_id", "extra_id"])
        self.assertEqual((report["checks"]["missing_id"], report["checks"]["extra_id"]), (12, 12))
        self.assertEqual(report["violations_total"], 25)
        self.assertEqual(len(report["hints"]), 2)
        self.assertIn("row index", report["hints"][0])
        self.assertIn("17.0 against 17", report["hints"][1])

    def test_header_without_the_header_line(self):
        submission = "".join(SUBMISSION.splitlines(keepends=True)[1:])
        status, report = check(submission, SAMPLE, "--task", "probability")
        self.assertEqual(status, 1)
        self.assertIn("header", report["failed_checks"])
        self.assertIn("row_count", report["failed_checks"])
        self.assertTrue(report["hints"][0].startswith("the first line holds data"))

    def test_header_order_and_letter_case_hints(self):
        status, report = check("target,id\n0.1,1001\n", "id,target\n1001,0.5\n", "--task", "probability")
        self.assertEqual(status, 1)
        self.assertIn("another order", report["hints"][0])
        status, report = check("ID,Target\n1001,0.1\n", "id,target\n1001,0.5\n", "--task", "probability")
        self.assertEqual(status, 1)
        self.assertIn("letter case", report["hints"][0])

    def test_ids_rows_and_fields(self):
        submission = "id,target\n1001,0.1\n1001,0.2\n1003,0.3\n9999,0.4\n1005,0.5,7\n"
        sample = "id,target\n1001,0.5\n1002,0.5\n1003,0.5\n1004,0.5\n1005,0.5\n"
        status, report = check(submission, sample, "--task", "probability")
        self.assertEqual(status, 1)
        checks = report["checks"]
        self.assertEqual((checks["duplicate_id"], checks["extra_id"], checks["field_count"], checks["row_count"]),
                         (1, 1, 1, 0))
        self.assertEqual(checks["missing_id"], 3)
        duplicate = next(item for item in report["violations"] if item["rule"] == "duplicate_id")
        self.assertEqual((duplicate["id"], duplicate["row"], duplicate["first_row"]), ("1001", 2, 1))

    def test_probability_values(self):
        submission = "id,target\n1,0.2\n2,1.5\n3,\n4,NaN\n5,0.5 \n6,-0.1\n"
        sample = "id,target\n1,0.5\n2,0.5\n3,0.5\n4,0.5\n5,0.5\n6,0.5\n"
        status, report = check(submission, sample, "--task", "probability")
        self.assertEqual(status, 1)
        checks = report["checks"]
        self.assertEqual((checks["out_of_range"], checks["missing_value"], checks["not_a_number"]), (2, 2, 1))

    def test_class_probabilities_must_add_up_to_one(self):
        submission = "id,low,medium,high\n1,0.2,0.3,0.5\n2,0.5,0.6,0.1\n3,0.3,0.3,0.3995\n"
        status, report = check(submission, CLASSES_SAMPLE, "--task", "class_probabilities")
        self.assertEqual(status, 1)
        self.assertEqual(report["checks"]["row_sum"], 1)
        failed = next(item for item in report["violations"] if item["rule"] == "row_sum")
        self.assertEqual(failed["row"], 2)
        status, report = check(submission, CLASSES_SAMPLE, "--task", "class_probabilities", "--sum-tolerance", "0.2")
        self.assertEqual(status, 0, report)

    def test_labels_must_be_exact(self):
        submission = "id,need\n1,Low\n2,low\n3,\n4, High\n5,NA\n"
        sample = "id,need\n1,Low\n2,Low\n3,Low\n4,Low\n5,Low\n"
        status, report = check(submission, sample, "--task", "label", "--labels", "Low", "High")
        self.assertEqual(status, 1)
        self.assertEqual((report["checks"]["not_allowed_label"], report["checks"]["missing_value"]), (2, 2))
        status, report = check(submission.replace(",NA", ",High"), sample, "--task", "label", "--labels", "Low",
                               "High", "low", " High")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["missing_value"])

    def test_number_range_and_text_values(self):
        status, report = check("id,y\n1,-1\n2,101\n3,1,000\n", "id,y\n1,0\n2,0\n3,0\n", "--task", "number",
                               "--min", "0", "--max", "100")
        self.assertEqual(status, 1)
        self.assertEqual((report["checks"]["out_of_range"], report["checks"]["field_count"]), (2, 1))
        status, report = check("id,answer\n1, \n2,NA\n", "id,answer\n1,x\n2,x\n", "--task", "text")
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["missing_value"])
        self.assertTrue(any("NA or null" in warning for warning in report["warnings"]))

    def test_warnings_for_hard_labels_and_placeholder_values(self):
        status, report = check("id,target\n1,0\n2,1\n3,1\n", "id,target\n1,0.5\n2,0.5\n3,0.5\n", "--task", "probability")
        self.assertEqual(status, 0, report)
        self.assertTrue(any("0 or 1" in warning for warning in report["warnings"]))
        status, report = check("id,target\n1,0.5\n2,0.5\n", "id,target\n1,0.5\n2,0.5\n", "--task", "probability")
        self.assertEqual(status, 0, report)
        self.assertTrue(any("placeholders" in warning for warning in report["warnings"]))
        self.assertTrue(any("same value" in warning for warning in report["warnings"]))

    def test_byte_order_mark_and_blank_lines_are_warnings(self):
        status, report = check("\ufeff" + SUBMISSION + "\n", SAMPLE, "--task", "probability")
        self.assertEqual(status, 0, report)
        self.assertEqual(len(report["warnings"]), 2)


class Refusals(unittest.TestCase):
    def assert_refused(self, status, report, reason):
        self.assertEqual(status, 2, report)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], reason, report)

    def test_arguments(self):
        for arguments in ((), ("--task", "label"), ("--task", "probability", "--labels", "a"),
                          ("--task", "probability", "--min", "0"), ("--task", "number", "--min", "5", "--max", "1"),
                          ("--task", "label", "--labels", "a", "a"), ("--task", "label", "--labels", "a", " "),
                          ("--task", "guess"),
                          ("--task", "class_probabilities", "--sum-tolerance", "1"),
                          ("--task", "probability", "--max-examples", "0"), ("--no-such-flag",)):
            status, report = check(SUBMISSION, SAMPLE, *arguments)
            self.assert_refused(status, report, "bad_arguments")

    def test_sample_that_cannot_be_the_authority(self):
        cases = (("id,id\n1,2\n", "sample_header_repeats"), ("id,target\n1,0.5\n1,0.5\n", "sample_ids_repeat"),
                 ("id\n1\n", "no_prediction_columns"), ("id,target\n", "sample_has_no_rows"),
                 ("id,target\n1,0.5,9\n", "sample_ragged"))
        for sample, reason in cases:
            self.assert_refused(*check(SUBMISSION, sample, "--task", "probability"), reason)
        self.assert_refused(*check(SUBMISSION, SAMPLE, "--task", "probability", "--id-column", "row_id"),
                            "id_column_missing")

    def test_unreadable_inputs(self):
        self.assert_refused(*check("PK\x03\x04 packed", SAMPLE, "--task", "probability"), "compressed_input")
        self.assert_refused(*check('id,target\n"1001,0.5\n', SAMPLE, "--task", "probability"), "malformed_csv")
        self.assert_refused(*check("", SAMPLE, "--task", "probability"), "header_missing")
        status, report = run("--bundle", "-", "--task", "probability",
                             stdin=json.dumps({"submission": "a\n\ud800\n", "sample": SAMPLE}))
        self.assert_refused(status, report, "not_utf8")
        status, report = run("--bundle", "-", "--task", "probability",
                             stdin=json.dumps({"submission": SUBMISSION, "sample": SAMPLE, "test": ""}))
        self.assert_refused(status, report, "bundle_invalid")
        status, report = run("--bundle", "-", "--task", "probability", stdin='{"submission": "a", "submission": "b"}')
        self.assert_refused(status, report, "json_invalid")

    def test_paths_are_confined_to_the_root(self):
        status, report = run("--submission", "examples/none.csv", "--sample", "SKILL.md", "--task", "text")
        self.assert_refused(status, report, "input_missing")
        status, report = run("--submission", "../SKILL.md", "--sample", "SKILL.md", "--task", "text")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--submission", sys.executable, "--sample", "SKILL.md", "--task", "text")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--submission", "examples", "--sample", "SKILL.md", "--task", "text")
        self.assert_refused(status, report, "not_a_regular_file")
        status, report = run("--submission", "x.csv", "--bundle", "examples/submission-bundle.json", "--task", "text")
        self.assert_refused(status, report, "bad_arguments")

    @unittest.skipUnless(os.path.islink("/proc/self/root"), "needs the Linux /proc/self/root link")
    def test_symbolic_link_that_leaves_the_root_is_refused(self):
        # /proc/self/root is a link to the file system root, so this path leaves --root /proc.
        status, report = run("--root", "/proc", "--submission", "self/root" + str(SCRIPT), "--bundle", "-",
                             "--task", "text", stdin=json.dumps({"sample": SAMPLE}))
        self.assert_refused(status, report, "path_leaves_root")

    def test_size_bound_refuses_instead_of_truncating(self):
        status, report = run("--bundle", "examples/submission-bundle.json", "--task", "probability",
                             "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")
        status, report = run("--submission", "SKILL.md", "--sample", "SKILL.md", "--task", "text", "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")
        self.assertIn("SKILL.md", report["detail"])


class Documentation(unittest.TestCase):
    def test_every_documented_option_is_accepted_by_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        self.assertEqual(finished.returncode, 0)
        for name in ("SKILL.md", "references/task-types.md", "references/checklist.md"):
            with open(PACKAGE / name, encoding="utf-8") as handle:
                text = handle.read()
            for option in sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]+", text))):
                self.assertIn(option, finished.stdout, f"{name} mentions {option}")

    def test_every_check_name_is_explained(self):
        with open(PACKAGE / "references" / "task-types.md", encoding="utf-8") as handle:
            text = handle.read()
        runs = (("--task", "probability", "--require-same-order"), ("--task", "class_probabilities"),
                ("--task", "label", "--labels", "a"), ("--task", "number", "--min", "0"), ("--task", "text"))
        for arguments in runs:
            _status, report = check(SUBMISSION, SAMPLE, *arguments)
            for name in report["checks"]:
                self.assertIn(f"`{name}`", text, f"references/task-types.md does not explain {name}")

    def test_task_types_in_the_documents_match_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        with open(PACKAGE / "references" / "task-types.md", encoding="utf-8") as handle:
            documented = set(re.findall(r"^\| `([a-z_]+)` \| ", handle.read(), re.MULTILINE))
        listed = set(re.search(r"--task \{([a-z_,]+)\}", finished.stdout).group(1).split(","))
        self.assertTrue(listed <= documented, (listed, documented))


if __name__ == "__main__":
    unittest.main()
