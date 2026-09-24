"""Tests for scripts/verify_folds.py. Effects: reads package files and starts the script with the current Python; writes nothing."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "verify_folds.py"
EXAMPLE_OPTIONS = ("--id-column", "id", "--group-column", "patient", "--label-column", "target", "--expected-folds", "3")

TRAIN = "id,user,target\nu1,A,1\nu2,A,0\nu3,B,1\nu4,B,0\nu5,C,1\nu6,C,0\n"


def run(*arguments, stdin=None):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], cwd=PACKAGE,
                              input=stdin, capture_output=True, text=True, timeout=120)
    return finished.returncode, json.loads(finished.stdout)


def check(folds, *arguments, train=None):
    bundle = {"folds": folds} if train is None else {"folds": folds, "train": train}
    return run("--bundle", "-", *arguments, stdin=json.dumps(bundle))


class Passing(unittest.TestCase):
    def test_example_group_folds_pass(self):
        status, report = run("--bundle", "examples/group-folds-bundle.json", *EXAMPLE_OPTIONS)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "pass")
        summary = report["summary"]
        self.assertEqual((summary["folds"], summary["groups"], summary["groups_in_two_folds"]), (3, 12, 0))
        self.assertEqual(summary["rows_per_fold"], {"0": 8, "1": 8, "2": 8})
        self.assertEqual(summary["max_label_share_gap"], 0.0)
        self.assertEqual(report["group_column"]["read_from"], "train")

    def test_fold_column_inside_the_training_file(self):
        table = "user,target,fold\nA,1,0\nA,0,0\nB,1,1\nB,0,1\n"
        status, report = check(table, "--group-column", "user", "--label-column", "target")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["match"]["rule"], "position")

    def test_row_number_layout_with_the_training_file(self):
        folds = "row,group,fold\n1,A,0\n2,A,0\n3,B,1\n4,B,1\n5,C,2\n6,C,2\n"
        status, report = check(folds, "--row-column", "row", "--group-column", "user", "--label-column", "target",
                               train=TRAIN)
        self.assertEqual(status, 0, report)
        self.assertEqual(report["match"], {"rule": "row", "column": "row"})

    def test_numeric_label_in_bins(self):
        values = [3.1, 9.4, 1.2, 7.7, 5.5, 2.8, 8.9, 4.4, 6.6, 0.5, 9.9, 3.3]
        table = "user,price,fold\n" + "".join(f"U{index},{value},{index % 2}\n" for index, value in enumerate(values))
        status, report = check(table, "--group-column", "user", "--label-column", "price", "--label-bins", "2",
                               "--label-tolerance", "0.2")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["labels"]["bins"], 2)
        ordered = sorted(values)
        table = "user,price,fold\n" + "".join(f"U{index},{value},{0 if index < 6 else 1}\n"
                                              for index, value in enumerate(ordered))
        status, report = check(table, "--group-column", "user", "--label-column", "price", "--label-bins", "2",
                               "--label-tolerance", "0.2")
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["label_share_gap"])
        self.assertEqual(report["summary"]["max_label_share_gap"], 0.5)


class KnownWrong(unittest.TestCase):
    def test_known_wrong_example_splits_patients_with_perfect_label_shares(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", *EXAMPLE_OPTIONS)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["group_in_two_folds"])
        self.assertEqual(report["summary"]["groups_in_two_folds"], 11)
        self.assertEqual(report["summary"]["max_label_share_gap"], 0.0)
        first = next(item for item in report["violations"] if item["group"] == "P-001")
        self.assertEqual(first["rows_per_fold"], {"0": 1, "1": 1})

    def test_rows_without_fold_twice_listed_and_unknown(self):
        folds = "id,fold\nu1,0\nu2,0\nu2,1\nu3,1\nu3,1\nu4,\nu9,2\n"
        status, report = check(folds, "--id-column", "id", "--group-column", "user", train=TRAIN)
        self.assertEqual(status, 1)
        checks = report["checks"]
        self.assertEqual((checks["row_without_fold"], checks["row_in_two_folds"], checks["row_listed_twice"],
                          checks["unknown_row"]), (3, 1, 1, 1))

    def test_fold_record_with_an_empty_id_is_unknown(self):
        folds = "id,fold\nu1,0\nu2,0\n,1\nu3,1\nu4,1\nu5,2\nu6,2\n"
        status, report = check(folds, "--id-column", "id", "--group-column", "user", train=TRAIN)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["failed_checks"], ["unknown_row"])
        self.assertIn("empty id", report["violations"][0]["reason"])

    def test_row_numbers_with_a_gap_and_without_the_training_file(self):
        folds = "row,group,fold\n1,A,0\n2,A,0\n4,B,1\n"
        status, report = check(folds, "--row-column", "row", "--group-column", "group")
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["row_without_fold"])
        self.assertEqual(report["violations"][0]["row"], 3)

    def test_empty_group_and_a_group_copy_that_differs(self):
        folds = "id,user,fold\nu1,A,0\nu2,B,0\nu3,B,1\nu4,B,1\nu5,C,2\nu6,C,2\n"
        train = TRAIN.replace("u2,A,0", "u2,,0")
        status, report = check(folds, "--id-column", "id", "--group-column", "user", train=train)
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), ["group_copy_differs", "row_without_group"])

    def test_label_share_gap_against_the_declared_tolerance(self):
        table = "user,target,fold\nA,1,0\nB,1,0\nC,1,0\nD,0,0\nE,1,1\nF,0,1\nG,0,1\nH,0,1\n"
        status, report = check(table, "--group-column", "user", "--label-column", "target")
        self.assertEqual(status, 1)
        self.assertEqual(report["failed_checks"], ["label_share_gap"])
        self.assertEqual(report["summary"]["max_label_share_gap"], 0.25)
        status, report = check(table, "--group-column", "user", "--label-column", "target", "--label-tolerance", "0.25")
        self.assertEqual(status, 0, report)

    def test_fold_values_are_exact_text(self):
        table = "user,fold\nA,1\nA,1.0\nB,2\n"
        status, report = check(table, "--group-column", "user", "--expected-folds", "2")
        self.assertEqual(status, 1)
        self.assertEqual(sorted(report["failed_checks"]), ["fold_count", "group_in_two_folds"])

    def test_no_values_hides_group_values(self):
        status, report = run("--bundle", "examples/known-wrong-bundle.json", *EXAMPLE_OPTIONS, "--no-values")
        self.assertEqual(status, 1)
        self.assertNotIn("P-0", json.dumps(report["violations"]))


class Refusals(unittest.TestCase):
    def assert_refused(self, status, report, reason):
        self.assertEqual(status, 2, report)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], reason, report)

    def test_arguments_and_match_rules(self):
        folds = "id,fold\nu1,0\n"
        self.assert_refused(*check(folds, "--group-column", "user", train=TRAIN), "match_rule_missing")
        self.assert_refused(*check(folds, "--id-column", "id", "--row-column", "id", "--group-column", "user"),
                            "bad_arguments")
        self.assert_refused(*check(folds, "--id-column", "id"), "bad_arguments")
        self.assert_refused(*check(folds, "--id-column", "id", "--group-column", "shop", train=TRAIN), "column_missing")
        self.assert_refused(*check(folds, "--group-column", "user", "--label-tolerance", "1.5"), "bad_arguments")
        self.assert_refused(*check(folds, "--group-column", "user", "--label-bins", "4"), "bad_arguments")

    def test_bad_values_are_refused(self):
        self.assert_refused(*check("row,fold\nfirst,0\n", "--row-column", "row", "--group-column", "row"),
                            "row_value_invalid")
        self.assert_refused(*check("row,fold\n0,0\n", "--row-column", "row", "--group-column", "row"),
                            "row_value_invalid")
        self.assert_refused(*check("id,fold\nu1,0\n", "--id-column", "id", "--group-column", "user",
                                   train="id,user\nu1,A\nu1,B\n"), "duplicate_id_in_train")
        self.assert_refused(*check("id,fold\nu1,0\n", "--id-column", "id", "--group-column", "user",
                                   train="id,user\n,A\n"), "empty_id_in_train")
        text_labels = "user,target,fold\nA,red,0\nB,blue,1\n"
        self.assert_refused(*check(text_labels, "--group-column", "user", "--label-column", "target",
                                   "--label-bins", "2"), "label_not_numeric")
        many = "user,target,fold\n" + "".join(f"U{index},{index},{index % 2}\n" for index in range(60))
        self.assert_refused(*check(many, "--group-column", "user", "--label-column", "target"), "too_many_label_values")

    def test_paths_are_confined_to_the_root(self):
        status, report = run("--folds", "../SKILL.md", "--group-column", "user")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--folds", sys.executable, "--group-column", "user")
        self.assert_refused(status, report, "path_leaves_root")
        status, report = run("--folds", "SKILL.md", "--group-column", "user", "--max-bytes", "100")
        self.assert_refused(status, report, "input_too_large")
        status, report = run("--folds", "examples/none.csv", "--group-column", "user")
        self.assert_refused(status, report, "input_missing")

    @unittest.skipUnless(os.path.islink("/proc/self/root"), "needs the Linux /proc/self/root link")
    def test_symbolic_link_that_leaves_the_root_is_refused(self):
        # /proc/self/root is a link to the file system root, so this path leaves --root /proc.
        status, report = run("--root", "/proc", "--folds", "self/root" + str(SCRIPT), "--group-column", "user")
        self.assert_refused(status, report, "path_leaves_root")

    def test_malformed_tables_are_refused(self):
        self.assert_refused(*check('user,fold\n"A,0\n', "--group-column", "user"), "malformed_csv")
        self.assert_refused(*check("user,fold\nA\n", "--group-column", "user"), "ragged_rows")
        self.assert_refused(*check("user,user,fold\nA,A,0\n", "--group-column", "user"), "duplicate_column_name")


class Documentation(unittest.TestCase):
    def test_every_documented_option_is_accepted_by_the_script(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                  timeout=60)
        self.assertEqual(finished.returncode, 0)
        for name in ("SKILL.md", "references/fold-file-format.md", "references/checklist.md"):
            with open(PACKAGE / name, encoding="utf-8") as handle:
                text = handle.read()
            for option in sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]+", text))):
                self.assertIn(option, finished.stdout, f"{name} mentions {option}")

    def test_every_check_name_is_explained(self):
        with open(PACKAGE / "references" / "fold-file-format.md", encoding="utf-8") as handle:
            text = handle.read()
        for name in ("row_without_fold", "row_in_two_folds", "row_listed_twice", "unknown_row", "row_without_group",
                     "group_in_two_folds", "group_copy_differs", "label_copy_differs", "label_share_gap", "fold_count"):
            self.assertIn(f"`{name}`", text)


if __name__ == "__main__":
    unittest.main()
