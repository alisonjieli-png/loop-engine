"""Static source templates for the standalone text-conformance export.

Owns the versioned, immutable source bundle used by the export builder.
These are source resources, not executable graph vertices or authority.
The export component owns rendering, validation, effects, and verification.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportSourceTemplates:
    """The related source bodies move together as one immutable configuration."""

    solution: str
    entry_point: str
    tests: str
    version: str = "1.0.0"


_SOLUTION_SOURCE = '''"""Standalone text conformance solution exported from Loop Engine."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import operations

HERE = Path(__file__).resolve().parent


def load_configuration() -> tuple[list, dict, dict]:
    rules = json.loads((HERE / "rules.json").read_text("utf-8"))
    return rules["rules"], rules["policy"], json.loads((HERE / "catalogs.json").read_text("utf-8"))


def conform_rows(rows, rules, policy, catalogs, *, learn_evidence: bool = True):
    """Two passes: learn column evidence, then apply the rules row by row."""
    rows = list(rows)
    columns = sorted({column for rule in rules for column in rule["columns"]})
    evidence = operations.learn_column_evidence(rows, columns) if learn_evidence else {}
    for index, row in enumerate(rows):
        output, corrections = operations.apply_rules_to_row(row, rules, catalogs, policy, evidence)
        yield str(row.get("row_ref") or index), output, corrections


def run(input_path: str, output_dir: str, *, learn_evidence: bool = True) -> dict:
    rules, policy, catalogs = load_configuration()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    corrections_all = []
    with open(input_path, "r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    with open(out / "conformed.csv", "w", encoding="utf-8", newline="") as target, \\
            open(out / "corrections.jsonl", "w", encoding="utf-8") as corrections_file, \\
            open(out / "escalations.jsonl", "w", encoding="utf-8") as escalations_file:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for row_ref, output, corrections in conform_rows(rows, rules, policy, catalogs,
                                                         learn_evidence=learn_evidence):
            writer.writerow({key: output.get(key, "") for key in fieldnames})
            for item in corrections:
                record = {"row_ref": row_ref, **item}
                corrections_file.write(json.dumps(record, sort_keys=True) + "\\n")
                corrections_all.append(record)
                if item["outcome"] == "escalated" or (policy.get("escalate_held") and item["outcome"] == "held"):
                    escalations_file.write(json.dumps(record, sort_keys=True) + "\\n")
    report = {"record_type": "conformance_report/v1", "rows": len(rows),
              **operations.summarize(corrections_all, rules)}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", "utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Conform text columns with a confidence per correction.")
    parser.add_argument("--input", required=True, help="CSV file to conform")
    parser.add_argument("--output-dir", required=True, help="directory for conformed.csv, corrections.jsonl, escalations.jsonl, report.json")
    parser.add_argument("--no-column-evidence", action="store_true", help="skip the first pass that learns casings from the column")
    args = parser.parse_args(argv)
    report = run(args.input, args.output_dir, learn_evidence=not args.no_column_evidence)
    print(json.dumps(report["overall"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_MAIN_SOURCE = '''from .solution import main

if __name__ == "__main__":
    raise SystemExit(main())
'''

_TEST_SOURCE = '''import json
import tempfile
import unittest
from pathlib import Path

from {package} import operations, solution


class ConformanceTest(unittest.TestCase):
    def test_rules_apply_hold_and_escalate(self):
        rules, policy, catalogs = solution.load_configuration()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "in.csv"
            source.write_text("{header}\\n{row_confident}\\n{row_low}\\n", "utf-8")
            report = solution.run(str(source), folder)
            self.assertEqual(report["rows"], 2)
            self.assertGreaterEqual(report["overall"]["applied"], 1)
            lines = (Path(folder) / "conformed.csv").read_text("utf-8").splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue((Path(folder) / "report.json").is_file())

    def test_operations_are_deterministic(self):
        rules, policy, catalogs = solution.load_configuration()
        first = operations.apply_operation("case_normalize", "ACME CORPORATION", {{}}, catalogs)
        second = operations.apply_operation("case_normalize", "ACME CORPORATION", {{}}, catalogs)
        self.assertEqual(first, second)
        self.assertTrue(first["changed"])


if __name__ == "__main__":
    unittest.main()
'''



TEXT_CONFORMANCE_TEMPLATES = ExportSourceTemplates(
    solution=_SOLUTION_SOURCE, entry_point=_MAIN_SOURCE, tests=_TEST_SOURCE)

