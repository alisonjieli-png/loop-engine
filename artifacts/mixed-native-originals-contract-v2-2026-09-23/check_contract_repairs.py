"""New contract cases run against a selected old or successor tree, without editing it."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

from jsonschema import Draft202012Validator
from acceptance_cases import REPAIR_CASES

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "mixed-native-originals-2026-09-23"
spec = importlib.util.spec_from_file_location("bounded_old_verifier", OLD / "verify_packages.py")
verifier = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = verifier
spec.loader.exec_module(verifier)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("Use a new report path")
    rows = []
    with tempfile.TemporaryDirectory(prefix="native-contract-regressions-") as directory:
        for identity, cases in REPAIR_CASES.items():
            folder = args.packages / identity
            schema_in = Draft202012Validator(json.loads((folder / "contracts/input.schema.json").read_text()))
            schema_out = Draft202012Validator(json.loads((folder / "contracts/output.schema.json").read_text()))
            for given, expected in cases:
                case = {"input": given, "expected": expected, "expected_exit": 2 if expected is None else 0}
                result = verifier.run_case((folder / "tools" / f"{identity}.py").resolve(), case, Path(directory), schema_out)
                valid = schema_in.is_valid(given)
                rows.append({"identity": identity, "input": given, "input_schema_valid": valid,
                             "result": result, "passed": result["passed"] and (expected is None or valid)})
    report = {"record_type": "native_contract_successor_checks/v1", "checks": rows,
              "passed": all(row["passed"] for row in rows), "provider_calls": 0,
              "approval": False, "execution": "existing minimal Bubblewrap verifier"}
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(rows), "failed": sum(not row["passed"] for row in rows)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
