"""Tests for scripts/target_encode_oof.py. Effects: starts the script with the current interpreter; writes only inside temporary folders.

Run from the package folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "target_encode_oof.py"
SMALL_TRAIN = "city,device,target,fold\nA,x,1,0\nA,y,0,1\nB,x,1,0\nB,y,1,1\nA,x,1,1\nC,y,0,0\n"
SMALL_TEST = "city,device\nA,x\nC,y\nD,z\n"


def larger_rows(flip_fold=None):
    """200 synthetic rows in 5 folds; many categories hold one or two rows."""
    lines = ["user,target,fold"]
    for index in range(200):
        fold = index % 5
        target = (index * 7 + index // 3) % 2
        if fold == flip_fold:
            target = 1 - target
        lines.append(f"u{(index * 13) % 120},{target},{fold}")
    return "\n".join(lines) + "\n"


class TargetEncodeOutOfFold(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_script(self, *arguments):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                              capture_output=True, text=True, timeout=120)
        return done.returncode, json.loads(done.stdout)

    def column(self, name, column):
        with open(self.root / name, encoding="utf-8", newline="") as handle:
            return [float(row[column]) for row in csv.DictReader(handle)]

    def encode_small(self, smoothing, output="out/train.csv", *extra):
        self.write("train.csv", SMALL_TRAIN)
        return self.run_script("--train", "train.csv", "--target", "target", "--column", "city",
                               "--fold-column", "fold", "--smoothing", smoothing, "--output-train", output, *extra)

    def test_hand_computed_values_without_smoothing(self):
        self.write("test.csv", SMALL_TEST)
        status, report = self.encode_small("0", "out/train.csv", "--test", "test.csv", "--output-test", "out/test.csv")
        self.assertEqual(status, 0, report)
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        expected = [0.5, 1.0, 1.0, 1.0, 1.0, 2 / 3]
        for got, want in zip(self.column("out/train.csv", "city_te"), expected):
            self.assertAlmostEqual(got, want, places=12)
        for got, want in zip(self.column("out/test.csv", "city_te"), [2 / 3, 0.0, 4 / 6]):
            self.assertAlmostEqual(got, want, places=12)
        summary = report["columns"][0]
        self.assertEqual((summary["test_rows_unseen"], summary["single_row_categories"]), (1, 1))

    def test_smoothing_pulls_rare_values_toward_the_other_folds_mean(self):
        status, report = self.encode_small("2")
        self.assertEqual(status, 0, report)
        values = self.column("out/train.csv", "city_te")
        self.assertAlmostEqual(values[0], 7 / 12, places=12)
        self.assertAlmostEqual(values[5], 2 / 3, places=12)

    def test_known_wrong_full_data_mean_copies_the_label_but_out_of_fold_does_not(self):
        self.write("train.csv", larger_rows())
        self.write("flipped.csv", larger_rows(flip_fold=0))
        for name, output in (("train.csv", "out/a.csv"), ("flipped.csv", "out/b.csv")):
            status, report = self.run_script("--train", name, "--target", "target", "--column", "user",
                                             "--fold-column", "fold", "--output-train", output)
            self.assertEqual(status, 0, report)
        before, after = self.column("out/a.csv", "user_te"), self.column("out/b.csv", "user_te")
        fold_zero = [position for position in range(200) if position % 5 == 0]
        self.assertEqual([before[p] for p in fold_zero], [after[p] for p in fold_zero])
        with open(self.root / "train.csv", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        sums, counts = defaultdict(float), defaultdict(int)
        for row in rows:
            sums[row["user"]] += float(row["target"])
            counts[row["user"]] += 1
        single = [p for p in fold_zero if counts[rows[p]["user"]] == 1]
        self.assertTrue(single)
        for position in single:
            self.assertEqual(sums[rows[position]["user"]] / counts[rows[position]["user"]],
                             float(rows[position]["target"]))

    def test_fold_file_gives_the_same_values_as_the_fold_column(self):
        status, _report = self.encode_small("5", "out/by_column.csv")
        self.assertEqual(status, 0)
        self.write("folds.csv", "row,group,fold\n1,g1,0\n2,g2,1\n3,g3,0\n4,g4,1\n5,g5,1\n6,g6,0\n")
        status, report = self.run_script("--train", "train.csv", "--target", "target", "--column", "city",
                                         "--fold-file", "folds.csv", "--smoothing", "5",
                                         "--output-train", "out/by_file.csv")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["settings"]["fold_source"]["kind"], "fold_file")
        self.assertEqual(self.column("out/by_column.csv", "city_te"), self.column("out/by_file.csv", "city_te"))

    def test_refusals(self):
        self.write("train.csv", SMALL_TRAIN)
        self.write("one_fold.csv", SMALL_TRAIN.replace(",1\n", ",0\n"))
        self.write("words.csv", SMALL_TRAIN.replace("A,x,1,0", "A,x,yes,0"))
        self.write("blank.csv", SMALL_TRAIN.replace("A,x,1,0", "A,x,,0"))
        self.write("short_folds.csv", "row,fold\n1,0\n2,1\n3,0\n4,1\n5,1\n")
        self.write("twice_folds.csv", "row,fold\n1,0\n1,1\n3,0\n4,1\n5,1\n6,0\n")
        self.write("out/taken.csv", "keep me\n")
        base = ["--target", "target", "--column", "city", "--output-train", "out/new.csv"]
        cases = [
            (["--train", "train.csv", *base], "bad_arguments"),
            (["--train", "train.csv", *base, "--fold-column", "fold", "--fold-file", "short_folds.csv"],
             "bad_arguments"),
            (["--train", "one_fold.csv", *base, "--fold-column", "fold"], "fewer_than_two_folds"),
            (["--train", "words.csv", *base, "--fold-column", "fold"], "target_not_numeric"),
            (["--train", "blank.csv", *base, "--fold-column", "fold"], "target_value_missing"),
            (["--train", "train.csv", *base, "--fold-file", "short_folds.csv"], "fold_file_rows_mismatch"),
            (["--train", "train.csv", *base, "--fold-file", "twice_folds.csv"], "fold_file_rows_mismatch"),
            (["--train", "train.csv", *base, "--fold-column", "fold", "--test", "train.csv"], "bad_arguments"),
            (["--train", "train.csv", "--target", "target", "--column", "target", "--fold-column", "fold",
              "--output-train", "out/new.csv"], "bad_arguments"),
            (["--train", "train.csv", "--target", "target", "--column", "city", "--fold-column", "fold",
              "--output-train", "out/taken.csv"], "output_exists"),
            (["--train", "../train.csv", "--list-columns"], "path_leaves_root"),
        ]
        for arguments, reason in cases:
            status, report = self.run_script(*arguments)
            self.assertEqual((status, report.get("reason")), (2, reason), arguments)
        self.assertFalse(os.path.exists(self.root / "out/new.csv"))
        self.assertEqual((self.root / "out/taken.csv").read_text(encoding="utf-8"), "keep me\n")

    def test_refuses_more_than_100_folds(self):
        lines = ["city,target,fold"] + [f"c{index % 30},{index % 2},{index % 300}" for index in range(3000)]
        self.write("many.csv", "\n".join(lines) + "\n")
        status, report = self.run_script("--train", "many.csv", "--target", "target", "--column", "city",
                                         "--fold-column", "fold", "--output-train", "out/many.csv")
        self.assertEqual((status, report["reason"]), (2, "too_many_folds"))
        self.assertFalse(os.path.exists(self.root / "out/many.csv"))

    def test_known_wrong_fold_file_for_other_rows_is_caught_by_the_group_check(self):
        self.write("train.csv", "customer,city,target\nk1,A,1\nk2,A,0\nk3,B,1\nk4,B,1\nk5,A,1\nk6,C,0\n")
        self.write("folds.csv", "row,group,fold\n1,k1,0\n2,k2,1\n3,k3,0\n4,k4,1\n5,k5,1\n6,k6,0\n")
        self.write("other.csv", "row,group,fold\n1,k2,1\n2,k1,0\n3,k3,0\n4,k4,1\n5,k5,1\n6,k6,0\n")
        base = ["--train", "train.csv", "--target", "target", "--column", "city"]
        status, report = self.run_script(*base, "--fold-file", "other.csv", "--output-train", "out/silent.csv")
        self.assertEqual(status, 0, report)
        status, report = self.run_script(*base, "--fold-file", "other.csv", "--check-group-column", "customer",
                                         "--output-train", "out/checked.csv")
        self.assertEqual((status, report["reason"]), (2, "fold_file_group_mismatch"))
        self.assertFalse(os.path.exists(self.root / "out/checked.csv"))
        status, report = self.run_script(*base, "--fold-file", "folds.csv", "--check-group-column", "customer",
                                         "--output-train", "out/good.csv")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["settings"]["fold_source"]["group_column_checked"], "customer")
        status, report = self.run_script(*base, "--fold-column", "customer", "--check-group-column", "customer",
                                         "--output-train", "out/bad.csv")
        self.assertEqual((status, report["reason"]), (2, "bad_arguments"))

    def test_list_columns(self):
        self.write("train.csv", SMALL_TRAIN)
        status, report = self.run_script("--train", "train.csv", "--list-columns")
        self.assertEqual(status, 0)
        self.assertEqual([item["name"] for item in report["columns"]], ["city", "device", "target", "fold"])


if __name__ == "__main__":
    unittest.main()
