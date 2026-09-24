"""Tests for scripts/map_categories.py. Effects: writes small synthetic CSV and JSON files inside a temporary directory and starts the script with the running Python interpreter; no network.

Run from the skill folder: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
import copy
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
SCRIPT = PAYLOAD / "scripts" / "map_categories.py"
REFERENCE = PAYLOAD / "references" / "mapping-table.md"
EXAMPLE = PAYLOAD / "examples" / "mapping-table.json"
TABLE = {
    "record_type": "category_mapping_table/v1",
    "columns": ["status"],
    "reviewed_by": "synthetic reviewer",
    "reviewed_on": "2026-09-20",
    "targets_map_to_themselves": True,
    "entries": [{"from": "shipped", "to": "Shipped"}, {"from": "in transit", "to": "In transit"},
                {"from": "shpd", "to": "Shipped"}, {"from": "Caf\N{LATIN SMALL LETTER E WITH ACUTE}", "to": "Cafe"}],
}


def start(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class MapCategoriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="map-categories-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, name: str, text: str) -> str:
        (self.root / name).write_bytes(text.encode("utf-8"))
        return name

    def table(self, document: dict, name: str = "mapping.json") -> str:
        return self.write(name, json.dumps(document))

    def statuses(self, *values: str) -> str:
        lines = ["id,status"] + [f'{number},"{value}"' for number, value in enumerate(values, start=1)]
        return self.write("orders.csv", "\n".join(lines) + "\n")

    def run_map(self, *arguments: str) -> tuple[int, dict]:
        finished = start("--root", str(self.root), *arguments)
        self.assertEqual(finished.stderr, "")
        return finished.returncode, json.loads(finished.stdout)

    def test_known_wrong_typo_is_listed_not_guessed(self) -> None:
        name = self.statuses("shipped", "Shiped", "shiped ", "SHIPED")
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(TABLE))
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"], {"data_rows": 4, "empty": 0, "mapped": 1, "unmapped": 3})
        self.assertEqual(report["unmapped_values"], [{"key": "shiped", "count": 3,
                                                      "spellings": ["Shiped", "shiped ", "SHIPED"],
                                                      "first_data_rows": [2, 3, 4]}])

    def test_case_spacing_and_unicode_forms_are_normalized(self) -> None:
        decomposed = "Cafe\N{COMBINING ACUTE ACCENT}"
        name = self.statuses(" SHIPPED ", "In   Transit", "shpd", decomposed, "")
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(TABLE),
                                    "--output", "orders.mapped.csv")
        self.assertEqual(code, 0)
        self.assertEqual(report["counts"], {"data_rows": 5, "empty": 1, "mapped": 4, "unmapped": 0})
        self.assertEqual(report["target_counts"], {"Cafe": 1, "In transit": 1, "Shipped": 2})
        rows = (self.root / "orders.mapped.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(rows[0], "id,status,status_mapped")
        self.assertEqual([row.rsplit(",", 1)[1] for row in rows[1:]], ["Shipped", "In transit", "Shipped", "Cafe", ""])

    def test_only_letter_case_is_folded(self) -> None:
        table = dict(TABLE, entries=[{"from": "Strasse", "to": "Street"}, {"from": "fine", "to": "Fine"},
                                     {"from": "\N{GREEK CAPITAL LETTER OMICRON}\N{GREEK CAPITAL LETTER DELTA}"
                                              "\N{GREEK CAPITAL LETTER OMICRON}\N{GREEK CAPITAL LETTER SIGMA}",
                                      "to": "Road"}])
        sharp = "Stra\N{LATIN SMALL LETTER SHARP S}e"
        capital_sharp = "STRA\N{LATIN CAPITAL LETTER SHARP S}E"
        ligature = "\N{LATIN SMALL LIGATURE FI}ne"
        final_sigma = ("\N{GREEK SMALL LETTER OMICRON}\N{GREEK SMALL LETTER DELTA}\N{GREEK SMALL LETTER OMICRON}"
                       "\N{GREEK SMALL LETTER FINAL SIGMA}")
        name = self.statuses("STRASSE", sharp, "FINE", ligature, capital_sharp, final_sigma)
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(table))
        self.assertEqual(code, 1)
        self.assertEqual(report["counts"], {"data_rows": 6, "empty": 0, "mapped": 3, "unmapped": 3})
        self.assertEqual(report["target_counts"], {"Fine": 1, "Road": 1, "Street": 1})
        self.assertEqual({entry["key"]: entry["spellings"] for entry in report["unmapped_values"]},
                         {"stra\N{LATIN SMALL LETTER SHARP S}e": [sharp, capital_sharp], ligature: [ligature]})

    def test_targets_map_to_themselves_only_when_declared(self) -> None:
        name = self.statuses("Shipped", "Cafe")
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(TABLE))
        self.assertEqual((code, report["mapped_by"]), (0, {"entry": 1, "target_itself": 1}))
        strict = dict(TABLE, targets_map_to_themselves=False)
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(strict))
        self.assertEqual((code, report["counts"]["unmapped"]), (1, 1))
        self.assertEqual(report["unmapped_values"][0]["key"], "cafe")

    def test_unused_entries_and_input_unchanged(self) -> None:
        name = self.statuses("shipped", "unknown label")
        before = hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", self.table(TABLE),
                                    "--output", "copy.csv")
        self.assertEqual(code, 1)
        self.assertEqual(report["input"]["sha256"], before)
        self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), before)
        self.assertEqual([entry["from"] for entry in report["unused_entries"]],
                         ["in transit", "shpd", "Caf\N{LATIN SMALL LETTER E WITH ACUTE}"])
        copy_bytes = (self.root / "copy.csv").read_bytes()
        self.assertEqual(report["output"]["sha256"], hashlib.sha256(copy_bytes).hexdigest())
        self.assertEqual(copy_bytes.decode("utf-8").splitlines(),
                         ["id,status,status_mapped", "1,shipped,Shipped", "2,unknown label,"])
        self.assertEqual(sum(item["count"] for item in report["unmapped_values"]), report["counts"]["unmapped"])

    def test_table_refusals(self) -> None:
        name = self.statuses("shipped")
        conflicting = copy.deepcopy(TABLE)
        conflicting["entries"].append({"from": "SHIPPED", "to": "Delivered"})
        chained = dict(copy.deepcopy(TABLE), targets_map_to_themselves=False)
        chained["entries"].append({"from": "shipped!", "to": "shpd"})
        colliding = copy.deepcopy(TABLE)
        colliding["entries"].append({"from": "sent", "to": "shipped"})
        cases = {
            "table_conflicting_entries": self.table(conflicting, "conflicting.json"),
            "table_chained_entries": self.table(chained, "chained.json"),
            "table_targets_collide": self.table(colliding, "colliding.json"),
            "table_not_for_this_column": self.table(dict(TABLE, columns=["state"]), "other-column.json"),
            "table_not_reviewed": self.table(dict(TABLE, reviewed_by=" "), "unreviewed.json"),
            "table_empty": self.table(dict(TABLE, entries=[]), "empty.json"),
            "table_invalid": self.table(dict(TABLE, comment="extra key"), "extra-key.json"),
        }
        for reason, mapping in cases.items():
            with self.subTest(reason=reason):
                code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping)
                self.assertEqual((code, report["status"], report["reason"]), (2, "refused", reason))
        for text in ('{"record_type": "category_mapping_table/v1", "record_type": "x"}', "[1, NaN]", "not json"):
            with self.subTest(table=text):
                mapping = self.write("broken.json", text)
                code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping)
                self.assertEqual((code, report["reason"]), (2, "table_invalid"))

    def test_a_mapping_sheet_is_not_a_reviewed_table(self) -> None:
        name = self.statuses("shpd")
        sheet = self.write("status-mapping.csv", "from,to\nshpd,Shipped\n")
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", sheet, "--output", "new.csv")
        self.assertEqual((code, report["reason"]), (2, "table_invalid"))
        self.assertIn("a CSV sheet or a plain list is not read", report["detail"])
        self.assertFalse((self.root / "new.csv").exists())

    def test_table_digest_pins_the_reviewed_bytes(self) -> None:
        name = self.statuses("shpd")
        mapping = self.table(TABLE)
        digest = hashlib.sha256((self.root / mapping).read_bytes()).hexdigest()
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping,
                                    "--table-sha256", digest.upper())
        self.assertEqual((code, report["table"]["sha256"], report["table"]["sha256_pinned"]), (0, digest, True))
        edited = copy.deepcopy(TABLE)
        edited["entries"].append({"from": "lost", "to": "Shipped"})
        self.table(edited)
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping,
                                    "--table-sha256", digest, "--output", "new.csv")
        self.assertEqual((code, report["reason"]), (2, "table_digest_differs"))
        self.assertFalse((self.root / "new.csv").exists())
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping,
                                    "--table-sha256", "abc")
        self.assertEqual((code, report["reason"]), (2, "arguments_invalid"))
        code, report = self.run_map("--input", name, "--column", "status", "--mapping", mapping)
        self.assertEqual((code, report["table"]["sha256_pinned"]), (0, False))

    def test_path_and_output_refusals_write_nothing(self) -> None:
        name = self.statuses("shipped")
        mapping = self.table(TABLE)
        self.write("exists.csv", "already here\n")
        cases = {
            "path_outside_root": ["--input", "../orders.csv", "--column", "status", "--mapping", mapping],
            "column_missing": ["--input", name, "--column", "Status", "--mapping",
                               self.table(dict(TABLE, columns=["status", "Status"]), "both.json")],
            "output_exists": ["--input", name, "--column", "status", "--mapping", mapping, "--output", "exists.csv"],
            "output_column_exists": ["--input", name, "--column", "status", "--mapping", mapping, "--output",
                                     "new.csv", "--output-column", "id"],
            "arguments_invalid": ["--input", name, "--column", "status"],
        }
        for reason, arguments in cases.items():
            with self.subTest(reason=reason):
                code, report = self.run_map(*arguments)
                self.assertEqual((code, report["reason"]), (2, reason))
        self.assertFalse((self.root / "new.csv").exists())
        self.assertEqual((self.root / "exists.csv").read_bytes(), b"already here\n")
        blank = self.write("blank.csv", "id,status\n1,shipped\n\n")
        code, report = self.run_map("--input", blank, "--column", "status", "--mapping", mapping, "--output", "new.csv")
        self.assertEqual((code, report["reason"]), (2, "row_width_differs"))
        self.assertIn("data row 2 is a blank line", report["detail"])
        self.assertFalse((self.root / "new.csv").exists())
        with tempfile.TemporaryDirectory(prefix="map-categories-outside-") as outside:
            target = Path(outside) / "table.json"
            target.write_bytes(json.dumps(TABLE).encode("utf-8"))
            os.symlink(target, self.root / "linked.json")
            code, report = self.run_map("--input", name, "--column", "status", "--mapping", "linked.json")
            self.assertEqual((code, report["reason"]), (2, "path_outside_root"))

    def test_example_table_is_valid(self) -> None:
        mapping = self.write("example.json", EXAMPLE.read_text(encoding="utf-8"))
        name = self.write("example.csv", "example_status\nSHPD\nOn Hold\ncancelled\nIn transit\nlost\n")
        code, report = self.run_map("--input", name, "--column", "example_status", "--mapping", mapping)
        self.assertEqual(code, 1)
        self.assertEqual(report["target_counts"], {"Canceled": 1, "In transit": 1, "Paused": 1, "Shipped": 1})
        self.assertEqual(report["unmapped_values"][0]["key"], "lost")
        code, report = self.run_map("--input", self.statuses("shpd"), "--column", "status", "--mapping", mapping)
        self.assertEqual((code, report["reason"]), (2, "table_not_for_this_column"))

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
