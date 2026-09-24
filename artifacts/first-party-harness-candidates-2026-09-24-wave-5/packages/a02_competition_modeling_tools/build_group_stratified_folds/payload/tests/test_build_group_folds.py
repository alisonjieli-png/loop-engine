"""Tests for scripts/build_group_folds.py. Effects: starts the script with the current interpreter; writes only inside temporary folders.

Run from the package folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import bisect
import csv
import hashlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_group_folds.py"


def synthetic_rows(groups=60, seed=3, dominant=0):
    """Customers with one to four visits; about a quarter of the rows have label 1."""
    rng = random.Random(seed)
    lines = ["customer_id,visit,amount,target"]
    for group in range(groups):
        size = 1 + (group * 7) % 4
        if group == 0 and dominant:
            size = dominant
        for visit in range(size):
            label = "1" if (group % 5 == 0 or (group % 7 == 0 and visit == 0)) else "0"
            lines.append(f"c{group:03d},{visit},{rng.randint(1, 99)},{label}")
    return "\n".join(lines) + "\n"


def zero_heavy_sales(seed=7, zero_share=0.93):
    """400 stores by 10 weeks; most weekly sales are 0."""
    rng = random.Random(seed)
    lines = ["store,week,sales"]
    for store in range(400):
        for week in range(10):
            lines.append(f"s{store},{week},{0 if rng.random() < zero_share else rng.randint(1, 500)}")
    return "\n".join(lines) + "\n"


def rare_label_rows(holders, groups=200, rows=5, positive_rows=1):
    """Groups of equal size; label 1 only in the first rows of the holder groups."""
    lines = ["customer_id,target"]
    for group in range(groups):
        for row in range(rows):
            lines.append(f"c{group:03d},{1 if group in holders and row < positive_rows else 0}")
    return "\n".join(lines) + "\n"


class BuildGroupFolds(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_script(self, *arguments):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                              capture_output=True, text=True, timeout=120)
        return done.returncode, json.loads(done.stdout)

    def build(self, output="folds/k5.csv", *extra):
        return self.run_script("--train", "train.csv", "--group", "customer_id", "--label", "target",
                               "--folds", "5", "--seed", "42", "--output", output, *extra)

    def read_folds(self, name):
        with open(self.root / name, encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def failed(self, report):
        return [check["name"] for check in report["checks"] if not check["passed"]]

    def test_list_columns_shows_distinct_counts(self):
        self.write("train.csv", synthetic_rows())
        status, report = self.run_script("--train", "train.csv", "--list-columns")
        self.assertEqual(status, 0)
        columns = {item["name"]: item for item in report["columns"]}
        self.assertEqual(columns["customer_id"]["distinct"], 60)
        self.assertEqual(columns["target"]["distinct"], 2)
        self.assertEqual(report["input"]["rows"], 150)

    def test_positive_case_keeps_groups_together_and_balances_labels(self):
        self.write("train.csv", synthetic_rows())
        status, report = self.build()
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        self.assertEqual(report["warnings"], [])
        rows = self.read_folds("folds/k5.csv")
        self.assertEqual([int(row["row"]) for row in rows], list(range(1, 151)))
        folds_of_group = {}
        for row in rows:
            folds_of_group.setdefault(row["group"], set()).add(row["fold"])
        self.assertTrue(all(len(item) == 1 for item in folds_of_group.values()))
        self.assertEqual(sorted({row["fold"] for row in rows}), ["0", "1", "2", "3", "4"])
        self.assertLessEqual(report["max_label_share_gap"]["value"], 0.05)
        written = (self.root / "folds/k5.csv").read_bytes()
        self.assertEqual(report["output"]["sha256"], hashlib.sha256(written).hexdigest())

    def test_known_wrong_row_level_random_split_mixes_groups(self):
        text = synthetic_rows()
        self.write("train.csv", text)
        records = list(csv.DictReader(io.StringIO(text)))
        rng = random.Random(42)
        naive = {}
        for record in records:
            naive.setdefault(record["customer_id"], set()).add(rng.randrange(5))
        self.assertGreater(sum(1 for item in naive.values() if len(item) > 1), 10)
        status, report = self.build()
        self.assertEqual(status, 0)
        self.assertEqual(report["groups_in_two_folds"], 0)

    def test_same_seed_gives_same_bytes(self):
        self.write("train.csv", synthetic_rows())
        first = self.build("folds/a.csv")[1]["output"]["sha256"]
        second = self.build("folds/b.csv")[1]["output"]["sha256"]
        self.assertEqual(first, second)

    def test_numeric_label_uses_quantile_bins(self):
        lines = ["store,week,sales"] + [f"s{index % 23},{index},{(index * 37) % 101}.5" for index in range(230)]
        self.write("train.csv", "\n".join(lines) + "\n")
        status, report = self.run_script("--train", "train.csv", "--group", "store", "--label", "sales",
                                         "--label-bins", "4", "--folds", "4", "--output", "folds/bins.csv")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["settings"]["label_mode"], "numeric_bins")
        self.assertEqual(report["label_strata"], 4)
        self.assertEqual(sum(item[2] for item in report["label_bin_ranges"]), 230)

    def test_known_wrong_zero_heavy_label_gets_a_zero_bin_and_bins_for_the_rest(self):
        text = zero_heavy_sales()
        self.write("train.csv", text)
        sales = [float(row["sales"]) for row in csv.DictReader(io.StringIO(text))]
        ordered = sorted(sales)
        naive_edges = sorted({ordered[(len(ordered) * step) // 10] for step in range(1, 10)})
        self.assertEqual(len({bisect.bisect_right(naive_edges, value) for value in sales}), 1)
        status, report = self.run_script("--train", "train.csv", "--group", "store", "--label", "sales",
                                         "--label-bins", "10", "--folds", "5", "--output", "folds/sales.csv")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["label_strata"], 10)
        zero_bin = report["label_bin_ranges"][0]
        self.assertEqual(zero_bin, [0.0, 0.0, sales.count(0.0)])
        self.assertGreater(min(item[2] for item in report["label_bin_ranges"][1:]), 20)
        self.assertLessEqual(report["max_label_share_gap"]["value"], 0.05)

    def test_label_with_one_value_fails_and_writes_nothing(self):
        lines = ["store,week,sales"] + [f"s{store},{week},0" for store in range(50) for week in range(4)]
        self.write("flat.csv", "\n".join(lines) + "\n")
        for extra in (["--label-bins", "10"], []):
            status, report = self.run_script("--train", "flat.csv", "--group", "store", "--label", "sales",
                                             "--folds", "5", "--output", "folds/flat.csv", *extra)
            self.assertEqual((status, self.failed(report)), (1, ["at_least_two_label_strata"]))
            self.assertIn("hint", report["checks"][3])
            self.assertFalse(os.path.exists(self.root / "folds/flat.csv"))

    def test_label_held_by_fewer_groups_than_folds_fails_with_a_hint(self):
        self.write("train.csv", rare_label_rows({5, 77, 150}, positive_rows=4))
        status, report = self.build()
        self.assertEqual((status, self.failed(report)), (1, ["each_label_in_every_fold"]))
        missing = report["labels_missing_from_folds"][0]
        self.assertEqual((missing["label"], missing["groups"], len(missing["folds_without"])), ("1", 3, 2))
        self.assertIn("--folds", report["checks"][4]["hint"])
        self.assertFalse(os.path.exists(self.root / "folds/k5.csv"))
        status, report = self.run_script("--train", "train.csv", "--group", "customer_id", "--label", "target",
                                         "--folds", "3", "--output", "folds/k3.csv")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["rarest_label"]["fold_rows"], [4, 4, 4])
        status, report = self.build("folds/allowed.csv", "--allow-missing-labels")
        self.assertEqual(status, 0, report)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("not defined", report["warnings"][0])

    def test_rare_label_in_few_groups_reaches_every_fold(self):
        self.write("train.csv", rare_label_rows({3, 50, 97, 140, 188}))
        for seed in ("0", "42"):
            status, report = self.run_script("--train", "train.csv", "--group", "customer_id", "--label", "target",
                                             "--folds", "5", "--seed", seed, "--output", f"folds/seed{seed}.csv")
            self.assertEqual(status, 0, report)
            self.assertEqual(report["rarest_label"]["fold_rows"], [1, 1, 1, 1, 1])
            self.assertEqual(report["labels_missing_from_folds"], [])

    def test_group_values_with_surrounding_spaces_count_as_one_group(self):
        lines = ["customer_id,target"] + [f"c{index % 20},{index % 2}" for index in range(59)] + ["c0 ,1"]
        self.write("train.csv", "\n".join(lines) + "\n")
        status, report = self.build("folds/spaces.csv", "--max-share-gap", "0.3")
        self.assertEqual(status, 0, report)
        self.assertEqual((report["groups"], report["rows_with_spaces_around_group"]), (20, 1))
        self.assertEqual(len(report["warnings"]), 1)
        rows = self.read_folds("folds/spaces.csv")
        self.assertEqual(rows[-1]["group"], "c0 ")
        self.assertEqual({row["fold"] for row in rows if row["group"].strip() == "c0"}, {rows[0]["fold"]})

    def test_dominant_group_fails_the_check_and_writes_nothing(self):
        self.write("train.csv", synthetic_rows(dominant=400))
        status, report = self.build()
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "check_failed")
        self.assertIn("fold_size_ratio", self.failed(report))
        self.assertFalse(os.path.exists(self.root / "folds/k5.csv"))

    def test_refuses_fewer_groups_than_folds(self):
        self.write("train.csv", synthetic_rows(groups=3))
        status, report = self.build()
        self.assertEqual((status, report["reason"]), (2, "fewer_groups_than_folds"))

    def test_refuses_missing_group_value(self):
        self.write("train.csv", synthetic_rows() + ",9,10,0\n")
        status, report = self.build()
        self.assertEqual((status, report["reason"]), (2, "group_value_missing"))

    def test_refuses_many_classes_without_bins(self):
        lines = ["user,price"] + [f"u{index % 40},{index}" for index in range(400)]
        self.write("train.csv", "\n".join(lines) + "\n")
        status, report = self.run_script("--train", "train.csv", "--group", "user", "--label", "price",
                                         "--output", "folds/x.csv")
        self.assertEqual((status, report["reason"]), (2, "too_many_label_values"))

    def test_refuses_existing_output_and_paths_outside_root(self):
        self.write("train.csv", synthetic_rows())
        self.write("folds/k5.csv", "keep me\n")
        status, report = self.build()
        self.assertEqual((status, report["reason"]), (2, "output_exists"))
        self.assertEqual((self.root / "folds/k5.csv").read_text(encoding="utf-8"), "keep me\n")
        status, report = self.run_script("--train", "../train.csv", "--list-columns")
        self.assertEqual((status, report["reason"]), (2, "path_leaves_root"))
        status, report = self.run_script("--train", "/etc/hostname", "--list-columns")
        self.assertEqual((status, report["reason"]), (2, "path_not_relative"))

    def test_refuses_symbolic_link_input(self):
        self.write("real.csv", synthetic_rows())
        os.symlink(self.root / "real.csv", self.root / "train.csv")
        status, report = self.run_script("--train", "train.csv", "--list-columns")
        self.assertEqual((status, report["reason"]), (2, "path_has_symbolic_link"))

    def test_refuses_bad_arguments_as_json(self):
        self.write("train.csv", synthetic_rows())
        status, report = self.run_script("--train", "train.csv", "--group", "customer_id", "--label", "target",
                                         "--folds", "1", "--output", "folds/x.csv")
        self.assertEqual((status, report["reason"]), (2, "bad_arguments"))
        status, report = self.run_script("--list-columns")
        self.assertEqual((status, report["reason"]), (2, "bad_arguments"))


if __name__ == "__main__":
    unittest.main()
