"""Tests for scripts/audit_drift.py. Effects: starts the script with the current interpreter and reads the shipped example; writes no file.

Run from the package folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import bisect
import csv
import io
import json
import math
import random
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "audit_drift.py"
EXAMPLE = PACKAGE / "examples" / "drift-pair.json"
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z")


def run_script(*arguments, stdin=None):
    done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(PACKAGE), *arguments],
                          input=stdin, capture_output=True, text=True, timeout=120)
    return done.returncode, json.loads(done.stdout)


def run_pair(train_csv, test_csv, *arguments):
    return run_script("--pair-json", "-", *arguments,
                      stdin=json.dumps({"train_csv": train_csv, "test_csv": test_csv}))


def tied_pair(seed=11):
    """A 0/1 flag moves from 5 to 50 percent ones; an amount moves from 93 to 40 percent zeros; noise stays."""
    rng = random.Random(seed)

    def rows(count, ones, zeros):
        return [f"{1 if rng.random() < ones else 0},{0 if rng.random() < zeros else rng.randint(1, 300)},"
                f"{rng.randint(0, 9)}" for _ in range(count)]

    header = "flag,amount,noise\n"
    return header + "\n".join(rows(5000, 0.05, 0.93)) + "\n", header + "\n".join(rows(2000, 0.5, 0.40)) + "\n"


def decile_edge_psi(train, test):
    """The known-wrong numeric PSI: deduplicated decile edges and bisect_right, so tied values share one bucket."""
    ordered = sorted(train)
    edges = sorted({ordered[(len(ordered) * step) // 10] for step in range(1, 10)})
    total = 0.0
    for bucket in range(len(edges) + 1):
        before = max(sum(1 for v in train if bisect.bisect_right(edges, v) == bucket) / len(train), 0.0001)
        after = max(sum(1 for v in test if bisect.bisect_right(edges, v) == bucket) / len(test), 0.0001)
        total += (after - before) * math.log(after / before)
    return total


def findings_by_column(report):
    return {item["column"]: sorted(finding["kind"] for finding in item["findings"])
            for item in report["flagged_columns"]}


class AuditDrift(unittest.TestCase):
    def test_example_pair_lists_the_planted_drift(self):
        status, report = run_script("--pair-json", "examples/drift-pair.json", "--target", "target", "--id", "id")
        self.assertEqual((status, report["status"]), (1, "findings"))
        self.assertEqual(findings_by_column(report), {
            "price": ["distribution_shift", "outside_train_range"],
            "promo": ["missing_rate_shift"],
            "store_type": ["distribution_shift", "unseen_categories"]})
        self.assertEqual(report["columns_only_in_test"], ["channel"])
        self.assertEqual(report["columns_only_in_train"], [])
        self.assertFalse(report["target_in_test"])
        self.assertEqual(sorted(report["unflagged_columns"]), ["age", "city"])
        self.assertEqual(report["rows"], {"train": 40, "test": 20})
        unseen = [finding for finding in report["flagged_columns"][0]["findings"]
                  if finding["kind"] == "unseen_categories"]
        self.assertEqual(unseen[0]["examples"], ["outlet"])

    def test_known_wrong_header_and_type_check_sees_nothing(self):
        pair = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        tables = [list(csv.reader(io.StringIO(pair[key]))) for key in ("train_csv", "test_csv")]
        shared = [name for name in tables[0][0] if name in tables[1][0]]

        def kinds(table):
            header, rows = table[0], [row for row in table[1:] if row]
            found = {}
            for name in shared:
                values = [row[header.index(name)] for row in rows if row[header.index(name)]]
                found[name] = "number" if all(NUMBER.match(value) for value in values) else "text"
            return found

        self.assertEqual(kinds(tables[0]), kinds(tables[1]))
        status, report = run_script("--pair-json", "examples/drift-pair.json", "--target", "target", "--id", "id")
        self.assertIn("store_type", findings_by_column(report))
        self.assertIn("price", findings_by_column(report))

    def test_known_wrong_tied_numeric_values_still_show_a_large_shift(self):
        train, test = tied_pair()
        columns = [list(zip(*[map(float, line.split(",")) for line in table.splitlines()[1:]])) for table in (train, test)]
        self.assertEqual(decile_edge_psi(columns[0][0], columns[1][0]), 0.0)
        self.assertEqual(decile_edge_psi(columns[0][1], columns[1][1]), 0.0)
        status, report = run_pair(train, test)
        self.assertEqual((status, report["status"]), (1, "findings"))
        found = {item["column"]: {finding["kind"]: finding for finding in item["findings"]}
                 for item in report["flagged_columns"]}
        self.assertEqual(sorted(found), ["amount", "flag"])
        self.assertGreater(found["flag"]["distribution_shift"]["psi"], 1.0)
        self.assertEqual(found["flag"]["distribution_shift"]["buckets"], 2)
        self.assertGreater(found["amount"]["distribution_shift"]["psi"], 0.25)
        self.assertEqual(report["unflagged_columns"], ["noise"])

    def test_identifier_column_is_named_when_not_passed_with_id(self):
        status, report = run_script("--pair-json", "examples/drift-pair.json", "--target", "target")
        self.assertEqual(findings_by_column(report)["id"], ["identifier_like"])
        self.assertNotIn("age", findings_by_column(report))

    def test_same_distribution_passes(self):
        rows = [f"{index},{['a', 'b', 'c'][index % 3]},{index % 10}" for index in range(60)]
        train = "key,group,amount\n" + "\n".join(rows) + "\n"
        status, report = run_pair(train, train, "--id", "key")
        self.assertEqual((status, report["status"]), (0, "pass"), report)
        self.assertEqual(report["flagged_columns"], [])

    def test_target_in_test_and_type_mismatch(self):
        train = "amount,target\n" + "\n".join(f"{index}.5,{index % 2}" for index in range(30)) + "\n"
        test = "amount,target\n" + "\n".join(f'"{index},5",0' for index in range(10)) + "\n"
        status, report = run_pair(train, test, "--target", "target")
        self.assertEqual(status, 1)
        self.assertTrue(report["target_in_test"])
        self.assertIn("type_mismatch", findings_by_column(report)["amount"])

    def test_missing_token_option_replaces_the_default_list(self):
        train = "size\n" + "\n".join(["1", "2", "3", "4"] * 10) + "\n"
        test = "size\n" + "\n".join(["1", "2", "?", "3", "4", "?"] * 5) + "\n"
        status, report = run_pair(train, test, "--missing-token", "?", "--missing-token", "")
        self.assertEqual(findings_by_column(report)["size"], ["missing_rate_shift"])
        self.assertEqual(report["settings"]["missing_tokens"], ["", "?"])

    def test_skipped_unseen_check_is_reported_as_a_note(self):
        values = [f"v{index}" for index in range(50005)]
        train = "code\n" + "\n".join(values + values) + "\n"
        test = "code\n" + "\n".join(f"new{index}" for index in range(10)) + "\n"
        status, report = run_pair(train, test)
        self.assertEqual([note["column"] for note in report["notes"]], ["code"])
        kinds = findings_by_column(report).get("code", [])
        self.assertNotIn("unseen_categories", kinds)
        self.assertNotIn("identifier_like", kinds)

    def test_refusals_are_json_with_exit_code_2(self):
        cases = [
            (["--pair-json", "-"], '{"train": "a"}', "pair_shape"),
            (["--pair-json", "-"], "not json", "pair_not_json"),
            (["--train", "../train.csv", "--test", "test.csv"], None, "path_leaves_root"),
            (["--train", "examples/none.csv", "--test", "examples/none.csv"], None, "input_missing"),
            (["--train", "examples/drift-pair.json"], None, "bad_arguments"),
            (["--pair-json", "examples/drift-pair.json", "--psi-limit", "0"], None, "bad_arguments"),
        ]
        for arguments, stdin, reason in cases:
            status, report = run_script(*arguments, stdin=stdin)
            self.assertEqual((status, report["reason"]), (2, reason), arguments)

    def test_refuses_rows_with_the_wrong_width(self):
        status, report = run_pair("a,b\n1,2\n3\n", "a,b\n1,2\n")
        self.assertEqual((status, report["reason"]), (2, "row_width_mismatch"))


if __name__ == "__main__":
    unittest.main()
