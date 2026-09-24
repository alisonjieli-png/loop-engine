"""Tests for scripts/build_time_splits.py. Effects: starts the script with the current interpreter; writes only inside temporary folders.

Run from the package folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import csv
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_time_splits.py"
START = date(2024, 1, 1)


def hourly_rows(hours, start=datetime(2024, 1, 1)):
    """One synthetic row per hour."""
    lines = ["ts,y"] + [f"{(start + timedelta(hours=hour)).isoformat()},{hour % 5}" for hour in hours]
    return "\n".join(lines) + "\n"


def daily_rows(days=60, per_day=2, start=START):
    """Two synthetic sales rows per day, listed newest first so input order is not time order."""
    lines = ["store,date,sales"]
    for offset in reversed(range(days)):
        for store in range(per_day):
            lines.append(f"s{store},{(start + timedelta(days=offset)).isoformat()},{(offset * 13 + store) % 50}")
    return "\n".join(lines) + "\n"


class BuildTimeSplits(unittest.TestCase):
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

    def split(self, *extra, output="splits/out.csv"):
        return self.run_script("--train", "train.csv", "--time", "date", "--output", output, *extra)

    def dates_by_part(self, output, column):
        with open(self.root / "train.csv", encoding="utf-8", newline="") as handle:
            dates = [date.fromisoformat(row["date"]) for row in csv.DictReader(handle)]
        with open(self.root / output, encoding="utf-8", newline="") as handle:
            parts = [row[column] for row in csv.DictReader(handle)]
        found = {}
        for day, part in zip(dates, parts):
            found.setdefault(part, []).append(day)
        return found

    def test_list_columns(self):
        self.write("train.csv", daily_rows())
        status, report = self.run_script("--train", "train.csv", "--list-columns")
        self.assertEqual(status, 0)
        self.assertEqual({item["name"]: item["distinct"] for item in report["columns"]}["date"], 60)

    def test_positive_case_every_split_respects_the_gap(self):
        self.write("train.csv", daily_rows())
        status, report = self.split("--gap", "7", "--splits", "3")
        self.assertEqual(status, 0, report)
        self.assertTrue(all(check["passed"] for check in report["checks"]))
        previous_last = None
        for number in (1, 2, 3):
            parts = self.dates_by_part("splits/out.csv", f"split_{number}")
            self.assertGreaterEqual(min(parts["validation"]) - max(parts["train"]), timedelta(days=7))
            self.assertIn("gap", parts)
            if previous_last is not None:
                self.assertGreater(min(parts["validation"]), previous_last)
            previous_last = max(parts["validation"])
            self.assertEqual(report["splits"][number - 1]["gap_observed"], 7.0)

    def test_known_wrong_random_split_validates_on_the_past(self):
        self.write("train.csv", daily_rows())
        days = [START + timedelta(days=offset) for offset in range(60) for _store in range(2)]
        rng = random.Random(1)
        fold = [rng.randrange(4) for _ in days]
        valid = [day for day, number in zip(days, fold) if number == 0]
        train = [day for day, number in zip(days, fold) if number != 0]
        self.assertLess(min(valid), max(train))
        status, report = self.split("--gap", "0", "--splits", "3")
        self.assertEqual(status, 0)
        for number in (1, 2, 3):
            parts = self.dates_by_part("splits/out.csv", f"split_{number}")
            self.assertGreater(min(parts["validation"]), max(parts["train"]))

    def test_warns_when_the_gap_is_shorter_than_before_the_test(self):
        self.write("train.csv", daily_rows())
        self.write("test.csv", daily_rows(days=14, start=START + timedelta(days=67)))
        status, report = self.split("--gap", "0", "--test", "test.csv")
        self.assertEqual(status, 0)
        self.assertEqual(report["test_period"]["gap_after_training"], 8.0)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertEqual(report["suggested_gap"]["arguments"], ["--gap", "8", "--gap-unit", "days"])
        self.assertIn("--gap 8 --gap-unit days", report["warnings"][0])
        status, report = self.split("--gap", "8", "--test", "test.csv", output="splits/gap8.csv")
        self.assertEqual((status, report["warnings"], report["suggested_gap"]), (0, [], None))

    def test_known_wrong_hourly_gap_rounded_in_days_never_clears_but_suggested_gap_does(self):
        self.write("train.csv", hourly_rows(range(200)))
        self.write("test.csv", hourly_rows(range(201, 230)))
        self.assertLess(round(2 / 24, 6) * 86400, 7200)
        status, report = self.run_script("--train", "train.csv", "--time", "ts", "--splits", "3", "--gap", "0",
                                         "--test", "test.csv", "--output", "splits/first.csv")
        self.assertEqual(status, 0, report)
        suggestion = report["suggested_gap"]
        self.assertEqual(suggestion["arguments"], ["--gap", "2", "--gap-unit", "hours"])
        status, report = self.run_script("--train", "train.csv", "--time", "ts", "--splits", "3",
                                         *suggestion["arguments"], "--test", "test.csv",
                                         "--output", "splits/second.csv")
        self.assertEqual((status, report["warnings"], report["suggested_gap"]), (0, [], None))
        self.assertEqual(report["settings"]["gap_unit"], "hours")
        self.assertEqual([item["gap_observed"] for item in report["splits"]], [2, 2, 2])
        self.assertEqual(report["test_period"]["gap_after_training"], 2)
        self.assertTrue(all(check["passed"] for check in report["checks"]))

    def test_numeric_time_and_sliding_window(self):
        lines = ["day,value"] + [f"{day},{day % 7}" for day in range(1, 101)]
        self.write("train.csv", "\n".join(lines) + "\n")
        status, report = self.run_script("--train", "train.csv", "--time", "day", "--time-kind", "number",
                                         "--gap", "5", "--splits", "4", "--train-blocks", "1",
                                         "--output", "splits/numbers.csv")
        self.assertEqual(status, 0, report)
        with open(self.root / "splits/numbers.csv", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        split_two = [int(row["row"]) for row in rows if row["split_2"] == "train"]
        self.assertTrue(split_two)
        self.assertGreater(min(split_two), 20)
        self.assertEqual(rows[0]["split_2"], "unused")

    def test_gap_too_large_fails_and_writes_nothing(self):
        self.write("train.csv", daily_rows())
        status, report = self.split("--gap", "40", "--splits", "3")
        self.assertEqual((status, report["status"]), (1, "check_failed"))
        self.assertFalse(os.path.exists(self.root / "splits/out.csv"))

    def test_refuses_times_that_do_not_parse(self):
        self.write("train.csv", daily_rows() + "s9,2024-02-30,1\n")
        status, report = self.split("--gap", "1")
        self.assertEqual((status, report["reason"]), (2, "time_not_parsed"))
        self.write("other.csv", "date,x\n03/01/2024,1\n04/01/2024,2\n")
        status, report = self.run_script("--train", "other.csv", "--time", "date", "--gap", "0",
                                         "--output", "splits/other.csv")
        self.assertEqual((status, report["reason"]), (2, "time_not_parsed"))

    def test_refuses_mixed_zone_offsets(self):
        self.write("train.csv", "date,x\n2024-01-01T00:00:00Z,1\n2024-01-02T00:00:00,2\n2024-01-03T00:00:00Z,3\n")
        status, report = self.split("--gap", "0", "--splits", "1")
        self.assertEqual((status, report["reason"]), (2, "time_zone_mixed"))

    def test_refuses_gap_unit_with_numeric_times(self):
        self.write("train.csv", "day,value\n1,2\n2,3\n3,4\n4,5\n")
        status, report = self.run_script("--train", "train.csv", "--time", "day", "--time-kind", "number",
                                         "--gap", "1", "--gap-unit", "days", "--output", "splits/x.csv")
        self.assertEqual((status, report["reason"]), (2, "bad_arguments"))

    def test_refuses_too_few_distinct_times_and_missing_gap(self):
        self.write("train.csv", "date,x\n2024-01-01,1\n2024-01-01,2\n2024-01-02,3\n")
        status, report = self.split("--gap", "0", "--splits", "3")
        self.assertEqual((status, report["reason"]), (2, "too_few_distinct_times"))
        status, report = self.split()
        self.assertEqual((status, report["reason"]), (2, "bad_arguments"))

    def test_refuses_existing_output_and_paths_outside_root(self):
        self.write("train.csv", daily_rows())
        self.write("splits/out.csv", "keep me\n")
        status, report = self.split("--gap", "1")
        self.assertEqual((status, report["reason"]), (2, "output_exists"))
        status, report = self.run_script("--train", "../train.csv", "--list-columns")
        self.assertEqual((status, report["reason"]), (2, "path_leaves_root"))


if __name__ == "__main__":
    unittest.main()
