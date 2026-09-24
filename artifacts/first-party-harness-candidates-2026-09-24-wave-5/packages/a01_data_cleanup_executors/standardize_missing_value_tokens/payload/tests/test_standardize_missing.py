"""Tests for scripts/standardize_missing.py. Effects: writes small synthetic CSV files inside a temporary directory and starts the script with the running Python interpreter; no network.

Run from the skill folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
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
SCRIPT = PAYLOAD / "scripts" / "standardize_missing.py"
REFERENCE = PAYLOAD / "references" / "tokens-and-counts.md"
SURVEY = ("id,score,active,country,note\n"
          "1,0,false,NA,n/a\n"
          "2,n/a,true,DE,\n"
          "3,12,null,NA,  N/A \n"
          "4,N/A,false,FR,   \n")


def start(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class StandardizeMissingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="standardize-missing-")
        self.root = Path(self.temporary.name)
        (self.root / "survey.csv").write_bytes(SURVEY.encode("utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(self, *arguments: str) -> tuple[int, dict]:
        finished = start("--root", str(self.root), "--input", "survey.csv", *arguments)
        self.assertEqual(finished.stderr, "")
        return finished.returncode, json.loads(finished.stdout)

    def copy_rows(self, name: str) -> list[str]:
        return (self.root / name).read_text(encoding="utf-8").splitlines()

    def test_known_wrong_real_values_survive(self) -> None:
        code, report = self.run_tool("--column", "score", "--column", "active", "--token", "n/a", "--token", "null",
                                     "--output", "out.csv")
        self.assertEqual(code, 1)
        self.assertEqual(self.copy_rows("out.csv"), ["id,score,active,country,note", "1,0,false,NA,n/a",
                                                     "2,,true,DE,", "3,12,,NA,  N/A ", "4,N/A,false,FR,   "])
        score, active = report["columns"]
        self.assertEqual((score["blanked"], score["kept"], score["blanked_by_token"]), (1, 3, {"n/a": 1, "null": 0}))
        self.assertEqual((active["blanked"], active["kept"]), (1, 3))
        self.assertEqual(report["undeclared_lookalikes"], [{"column": "score", "value": "N/A", "count": 1,
                                                            "first_data_rows": [4]}])
        for token in ("0", "false", "FALSE", "-999", "1900-01-01"):
            with self.subTest(token=token):
                code, report = self.run_tool("--column", "score", "--token", token)
                self.assertEqual((code, report["reason"]), (2, "token_looks_like_a_value"))

    def test_ignore_case_and_whitespace_cells(self) -> None:
        code, report = self.run_tool("--column", "note", "--token", "n/a", "--ignore-case", "--output", "a.csv")
        self.assertEqual(code, 1)
        self.assertEqual(report["columns"][0]["whitespace_kept"], 1)
        self.assertEqual([row.rsplit(",", 1)[1] for row in self.copy_rows("a.csv")[1:]], ["", "", "", "   "])
        code, report = self.run_tool("--column", "note", "--token", "n/a", "--ignore-case",
                                     "--blank-whitespace-cells", "--output", "b.csv")
        self.assertEqual((code, report["status"]), (0, "done"))
        note = report["columns"][0]
        self.assertEqual((note["blanked"], note["whitespace_blanked"], note["already_empty"], note["cells"]),
                         (2, 1, 1, 4))

    def test_token_must_match_the_whole_cell(self) -> None:
        (self.root / "survey.csv").write_bytes(b"status\nn/a pending\nn/a\n-5\n")
        code, report = self.run_tool("--column", "status", "--token", "n/a", "--token=-", "--output", "out.csv")
        self.assertEqual((code, report["totals"]["blanked"], report["totals"]["kept"]), (0, 1, 2))
        self.assertEqual(self.copy_rows("out.csv"), ["status", "n/a pending", '""', "-5"])

    def test_value_like_tokens_need_a_second_declaration(self) -> None:
        (self.root / "survey.csv").write_bytes(b"temperature,balance\n-999,-999\n21.5,10\n")
        code, report = self.run_tool("--column", "temperature", "--token", "-999", "--allow-value-token", "-999",
                                     "--output", "out.csv")
        self.assertEqual(code, 0)
        self.assertEqual(self.copy_rows("out.csv"), ["temperature,balance", ",-999", "21.5,10"])
        code, report = self.run_tool("--column", "temperature", "--token", "n/a", "--allow-value-token", "-999")
        self.assertEqual((code, report["reason"]), (2, "allow_value_token_not_declared"))

    def test_all_columns_copy_is_idempotent_and_input_unchanged(self) -> None:
        before = hashlib.sha256((self.root / "survey.csv").read_bytes()).hexdigest()
        code, report = self.run_tool("--all-columns", "--token", "n/a", "--token", "null", "--token=-",
                                     "--ignore-case", "--blank-whitespace-cells", "--output", "clean.csv")
        self.assertEqual(code, 1)
        self.assertEqual(report["undeclared_lookalikes"], [{"column": "country", "value": "NA", "count": 2,
                                                            "first_data_rows": [1, 3]}])
        self.assertEqual(report["input"]["sha256"], before)
        self.assertEqual(hashlib.sha256((self.root / "survey.csv").read_bytes()).hexdigest(), before)
        self.assertEqual(report["totals"]["blanked"], 5)
        totals = report["totals"]
        self.assertEqual(totals["blanked"] + totals["whitespace_blanked"] + totals["whitespace_kept"]
                         + totals["already_empty"] + totals["kept"], totals["cells"])
        copy_bytes = (self.root / "clean.csv").read_bytes()
        self.assertEqual(report["output"]["sha256"], hashlib.sha256(copy_bytes).hexdigest())
        finished = start("--root", str(self.root), "--input", "clean.csv", "--all-columns", "--token", "n/a",
                         "--token", "null", "--token=-", "--ignore-case", "--blank-whitespace-cells")
        again = json.loads(finished.stdout)
        self.assertEqual((finished.returncode, again["totals"]["blanked"], again["totals"]["whitespace_blanked"]),
                         (1, 0, 0))
        self.assertIn("1,0,false,NA,", copy_bytes.decode("utf-8"))

    def test_a_declared_token_applies_to_every_cleaned_column(self) -> None:
        code, report = self.run_tool("--column", "id", "--token", "NA", "--output", "id.csv")
        self.assertEqual((code, report["totals"]["blanked"]), (0, 0))
        self.assertEqual([row.split(",")[3] for row in self.copy_rows("id.csv")[1:]], ["NA", "DE", "NA", "FR"])
        code, report = self.run_tool("--all-columns", "--token", "NA", "--output", "every.csv")
        self.assertEqual(code, 1)
        country = next(item for item in report["columns"] if item["column"] == "country")
        self.assertEqual((country["blanked"], country["blanked_by_token"]), (2, {"NA": 2}))
        self.assertEqual([row.split(",")[3] for row in self.copy_rows("every.csv")[1:]], ["", "DE", "", "FR"])

    def test_refusals_write_nothing(self) -> None:
        (self.root / "exists.csv").write_bytes(b"already here\n")
        cases = {
            "columns_not_declared": ["--token", "n/a"],
            "arguments_invalid": ["--column", "score", "--all-columns", "--token", "n/a"],
            "token_invalid": ["--column", "score", "--token", "   "],
            "token_repeated": ["--column", "score", "--token", "N/A", "--token", "n/a", "--ignore-case"],
            "column_missing": ["--column", "Score", "--token", "n/a"],
            "output_exists": ["--column", "score", "--token", "n/a", "--output", "exists.csv"],
        }
        for reason, arguments in cases.items():
            with self.subTest(reason=reason):
                code, report = self.run_tool(*arguments)
                self.assertEqual((code, report["status"], report["reason"]), (2, "refused", reason))
        finished = start("--root", str(self.root), "--input", "../survey.csv", "--column", "score", "--token", "n/a")
        self.assertEqual((finished.returncode, json.loads(finished.stdout)["reason"]), (2, "path_outside_root"))
        self.assertEqual((self.root / "exists.csv").read_bytes(), b"already here\n")
        (self.root / "blank.csv").write_bytes(b"id,score\n1,n/a\n\n")
        finished = start("--root", str(self.root), "--input", "blank.csv", "--column", "score", "--token", "n/a",
                         "--output", "never.csv")
        report = json.loads(finished.stdout)
        self.assertEqual((finished.returncode, report["reason"]), (2, "row_width_differs"))
        self.assertIn("data row 2 is a blank line", report["detail"])
        self.assertFalse((self.root / "never.csv").exists())
        with tempfile.TemporaryDirectory(prefix="standardize-missing-outside-") as outside:
            (Path(outside) / "other.csv").write_bytes(b"a\nn/a\n")
            os.symlink(Path(outside) / "other.csv", self.root / "linked.csv")
            finished = start("--root", str(self.root), "--input", "linked.csv", "--column", "a", "--token", "n/a")
            self.assertEqual(json.loads(finished.stdout)["reason"], "path_outside_root")

    def test_documentation_matches_the_script(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        declared = set()
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id == "REFUSAL_REASONS":
                declared = set(ast.literal_eval(node.value))
        raised = {node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "Refusal"
                  and node.args and isinstance(node.args[0], ast.Constant)}
        self.assertLessEqual(raised, declared)
        reference = REFERENCE.read_text(encoding="utf-8")
        for reason in declared:
            self.assertIn(f"`{reason}`", reference)
        help_text = start("--help").stdout
        skill = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        for flag in set(re.findall(r"--[a-z][a-z-]*[a-z]", skill + reference)):
            self.assertIn(flag, help_text)


if __name__ == "__main__":
    unittest.main()
