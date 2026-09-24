"""Tests for scripts/flag_outliers.py. Effects: writes small synthetic CSV files inside a temporary directory and starts the script with the running Python interpreter; no network.

Run from the skill folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "flag_outliers.py"
REFERENCE = PAYLOAD / "references" / "method-and-fields.md"
REGIONS = ("region,amount\n" + "".join(f"A,{value}\n" for value in (10, 11, 12, 11, 10, 13))
           + "".join(f"B,{value}\n" for value in (1000, 1010, 990, 1005, 995, 100)))


def start(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class FlagOutliersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="flag-outliers-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, text: str, name: str = "data.csv") -> str:
        (self.root / name).write_bytes(text.encode("utf-8"))
        return name

    def flag(self, *arguments: str) -> tuple[int, dict]:
        finished = start("--root", str(self.root), *arguments)
        self.assertEqual(finished.stderr, "")
        return finished.returncode, json.loads(finished.stdout)

    def test_known_wrong_mean_and_standard_deviation_miss_the_outlier(self) -> None:
        values = [10, 11, 12, 11, 10, 500]
        z_score = (500 - statistics.mean(values)) / statistics.pstdev(values)
        self.assertLess(z_score, 3)
        name = self.write("amount\n" + "".join(f"{value}\n" for value in values))
        code, report = self.flag("--input", name, "--column", "amount", "--multiple", "5")
        self.assertEqual(code, 1)
        self.assertEqual(report["flagged"], [{"column": "amount", "group": None, "data_row": 6, "value": "500",
                                              "median": "11", "mad": "1", "deviation_in_mads": "489.0000",
                                              "direction": "high"}])
        self.assertEqual(report["group_statistics"], [{"column": "amount", "group": None, "values": 6,
                                                       "median": "11", "mad": "1", "flagged": 1}])

    def test_groups_keep_different_scales_apart(self) -> None:
        name = self.write(REGIONS)
        code, report = self.flag("--input", name, "--column", "amount", "--multiple", "5", "--group-by", "region")
        self.assertEqual(code, 1)
        self.assertEqual([(item["group"], item["data_row"], item["direction"], item["median"], item["mad"])
                          for item in report["flagged"]], [({"region": "B"}, 12, "low", "997.5", "7.5")])
        code, pooled = self.flag("--input", name, "--column", "amount", "--multiple", "5")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(item["data_row"] for item in pooled["flagged"]), [7, 8, 9, 10, 11])
        self.assertNotIn(12, [item["data_row"] for item in pooled["flagged"]])

    def test_zero_mad_and_small_groups_are_reported_not_flagged(self) -> None:
        text = "grp,v\n" + "".join(f"X,{value}\n" for value in (5, 5, 5, 5, 5, 9)) + "Y,1\nY,2\nY,3\n"
        name = self.write(text)
        code, report = self.flag("--input", name, "--column", "v", "--multiple", "3", "--group-by", "grp")
        self.assertEqual((code, report["flagged"]), (1, []))
        self.assertEqual(report["groups_not_evaluated"], [
            {"column": "v", "group": {"grp": "X"}, "values": 6, "reason": "mad_is_zero", "median": "5",
             "values_differing_from_median": 1},
            {"column": "v", "group": {"grp": "Y"}, "values": 3, "reason": "too_few_values"}])
        self.assertEqual((report["groups_not_evaluated_complete"], report["not_numeric_values_complete"]),
                         (True, True))
        code, report = self.flag("--input", name, "--column", "v", "--multiple", "3", "--group-by", "grp",
                                 "--min-group-size", "3")
        self.assertEqual(report["groups_not_evaluated_total"], 1)

    def test_group_labels_are_trimmed_but_case_still_counts(self) -> None:
        text = "store,amount\nB,10\nB ,11\n B,12\nB,13\nB ,99\nb,10\nb,11\nb,12\nb,13\nb,14\n"
        name = self.write(text)
        code, report = self.flag("--input", name, "--column", "amount", "--multiple", "5", "--group-by", "store")
        self.assertEqual(code, 1)
        self.assertEqual((report["columns"][0]["groups"], report["group_labels_trimmed"]), (2, 3))
        self.assertEqual([(item["group"], item["data_row"], item["median"], item["mad"]) for item in report["flagged"]],
                         [({"store": "B"}, 5, "12", "1")])
        self.assertEqual(report["groups_not_evaluated"], [])

    def test_capped_lists_say_when_they_are_cut(self) -> None:
        rows = ["grp,v"]
        rows += [f"e{index},{value}" for index in range(201) for value in (1, 2, 3, 4, 5)]
        rows += [f"s{index},{index}" for index in range(201)]
        rows += [f"t,x{index}" for index in range(201)]
        name = self.write("\n".join(rows) + "\n")
        code, report = self.flag("--input", name, "--column", "v", "--multiple", "5", "--group-by", "grp")
        self.assertEqual(code, 1)
        self.assertEqual((report["columns"][0]["groups_evaluated"], report["groups_not_evaluated_total"],
                          report["not_numeric_values_distinct"]), (201, 201, 201))
        self.assertEqual((len(report["group_statistics"]), len(report["groups_not_evaluated"]),
                          len(report["not_numeric_values"])), (200, 200, 200))
        self.assertEqual((report["group_statistics_complete"], report["groups_not_evaluated_complete"],
                          report["not_numeric_values_complete"]), (False, False, False))

    def test_empty_and_unreadable_cells_are_counted(self) -> None:
        name = self.write('amount\n12\n\nn/a\n"1,234"\n13\n12\n11\n14\n')
        code, report = self.flag("--input", name, "--column", "amount", "--multiple", "5")
        self.assertEqual(code, 1)
        summary = report["columns"][0]
        self.assertEqual((summary["numeric"], summary["empty"], summary["not_numeric"]), (5, 1, 2))
        self.assertEqual(summary["numeric"] + summary["empty"] + summary["not_numeric"], report["input"]["data_rows"])
        self.assertEqual(sorted(item["value"] for item in report["not_numeric_values"]), ["1,234", "n/a"])

    def test_copy_adds_flags_and_keeps_every_value(self) -> None:
        text = "id,amount\n1,10\n2,11\n3,12\n4,11\n5,10\n6,500\n7,\n"
        name = self.write(text)
        before = hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        code, report = self.flag("--input", name, "--column", "amount", "--multiple", "5", "--output", "flagged.csv")
        self.assertEqual(code, 1)
        self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), before)
        self.assertEqual(report["input"]["sha256"], before)
        lines = (self.root / "flagged.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "id,amount,amount_outlier")
        self.assertEqual([line.rsplit(",", 1)[0] for line in lines[1:]], text.splitlines()[1:])
        self.assertEqual([line.rsplit(",", 1)[1] for line in lines[1:]],
                         ["within"] * 5 + ["high", "not_evaluated"])
        self.assertEqual(report["output"]["sha256"],
                         hashlib.sha256((self.root / "flagged.csv").read_bytes()).hexdigest())

    def test_refusals_write_nothing(self) -> None:
        name = self.write(REGIONS)
        clash = self.write("amount,amount_outlier\n1,x\n", "clash.csv")
        self.write("already here\n", "exists.csv")
        cases = {
            "arguments_invalid": ["--input", name, "--column", "amount"],
            "min_group_size_invalid": ["--input", name, "--column", "amount", "--multiple", "5",
                                       "--min-group-size", "2"],
            "group_by_invalid": ["--input", name, "--column", "amount", "--multiple", "5", "--group-by", "amount"],
            "column_missing": ["--input", name, "--column", "amount", "--multiple", "5", "--group-by", "Region"],
            "output_exists": ["--input", name, "--column", "amount", "--multiple", "5", "--output", "exists.csv"],
            "output_column_exists": ["--input", clash, "--column", "amount", "--multiple", "5", "--output", "n.csv"],
            "path_outside_root": ["--input", "../data.csv", "--column", "amount", "--multiple", "5"],
        }
        for reason, arguments in cases.items():
            with self.subTest(reason=reason):
                code, report = self.flag(*arguments)
                self.assertEqual((code, report["status"], report["reason"]), (2, "refused", reason))
        for multiple in ("0", "-1", "abc", "1e3", "2000"):
            with self.subTest(multiple=multiple):
                code, report = self.flag("--input", name, "--column", "amount", f"--multiple={multiple}")
                self.assertEqual((code, report["reason"]), (2, "multiple_invalid"))
        self.assertFalse((self.root / "n.csv").exists())
        self.assertEqual((self.root / "exists.csv").read_bytes(), b"already here\n")
        blank = self.write("region,amount\nA,10\n\n", "blank.csv")
        code, report = self.flag("--input", blank, "--column", "amount", "--multiple", "5", "--output", "n.csv")
        self.assertEqual((code, report["reason"]), (2, "row_width_differs"))
        self.assertIn("data row 2 is a blank line", report["detail"])
        self.assertFalse((self.root / "n.csv").exists())
        with tempfile.TemporaryDirectory(prefix="flag-outliers-outside-") as outside:
            (Path(outside) / "other.csv").write_bytes(b"amount\n1\n")
            os.symlink(Path(outside) / "other.csv", self.root / "linked.csv")
            code, report = self.flag("--input", "linked.csv", "--column", "amount", "--multiple", "5")
            self.assertEqual((code, report["reason"]), (2, "path_outside_root"))

    def test_documentation_matches_the_script(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        declared = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in ("GROUP_REASONS", "REFUSAL_REASONS"):
                declared[node.targets[0].id] = set(ast.literal_eval(node.value))
        raised = {node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "Refusal"
                  and node.args and isinstance(node.args[0], ast.Constant)}
        self.assertLessEqual(raised, declared["REFUSAL_REASONS"])
        reference = REFERENCE.read_text(encoding="utf-8")
        for reason in declared["GROUP_REASONS"] | declared["REFUSAL_REASONS"]:
            self.assertIn(f"`{reason}`", reference)
        help_text = start("--help").stdout
        skill = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        for flag in set(re.findall(r"--[a-z][a-z-]*[a-z]", skill + reference)):
            self.assertIn(flag, help_text)


if __name__ == "__main__":
    unittest.main()
