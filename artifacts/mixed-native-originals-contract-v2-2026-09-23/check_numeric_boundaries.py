"""Exact numeric literals and selected-column boundaries, in the existing sandbox."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator
import verify_packages as verifier

HERE = Path(__file__).resolve().parent
PACKAGES = HERE / "prepared/packages"


def probe(script, raw, expected, directory):
    source = directory / "input.json"
    runner = directory / "runner.py"
    source.write_text(raw)
    runner.write_text(verifier.RUNNER)
    result = verifier.run_command(verifier.command(script.resolve(), source, runner),
        timeout_seconds=4, maximum_output_bytes=65537, environment={"PATH": "/usr/bin:/bin"})
    try:
        observed = json.loads(result.stdout)
    except ValueError:
        observed = None
    expected_code = 2 if expected is None else 0
    return {"expected_exit": expected_code, "actual_exit": result.exit_code, "output": observed,
            "timed_out": result.timed_out, "passed": result.exit_code == expected_code
                and observed == (expected if expected is not None else {"error": "invalid_input"})
                and not result.timed_out and not result.truncated}


def main():
    path = HERE / "numeric-boundaries-and-guard-controls.json"
    if path.exists():
        raise ValueError("Use a new evidence path")
    schedule = PACKAGES / "schedule_dag_earliest_times/tools/schedule_dag_earliest_times.py"
    rows = []
    with tempfile.TemporaryDirectory(prefix="native-number-boundaries-") as temp:
        directory = Path(temp)
        cases = [("1.0", 1), ("1e0", 1), ("true", None), ("1.5", None),
                 ("1e1000000000", None), ("0e1000000000", None), ("1e-1000000000", None),
                 ("1.0000000000000001", None), ("1000000000.0", 1000000000),
                 ("1000000001.0", None), ("1e309", None)]
        for literal, duration in cases:
            raw = '{"tasks":[{"id":"a","duration":' + literal + ',"depends_on":[]}]}'
            expected = None if duration is None else {"duration": duration, "schedule": [{"id": "a", "start": 0, "finish": duration}]}
            rows.append({"literal": literal, **probe(schedule, raw, expected, directory)})
        original = schedule.read_text()
        before, after = 'if exact == exact.to_integral_value():', 'if number.is_integer():'
        assert original.count(before) == 1
        mutant = directory / "rounding-mutant.py"
        mutant.write_text(original.replace(before, after, 1))
        raw = '{"tasks":[{"id":"a","duration":1.0000000000000001,"depends_on":[]}]}'
        rounding = probe(mutant, raw, None, directory)
        original_fd = PACKAGES / "audit_functional_dependency_rows/tools/audit_functional_dependency_rows.py"
        raw = json.dumps({"determinants": ["a"], "dependents": ["b"], "rows": [{"a": "x", "b": {"nested": True}}]})
        fd_source = original_fd.read_text()
        before = 'need(all(type(row[key]) in (str, int, bool, type(None)) for key in columns))'
        assert fd_source.count(before) == 1
        mutant_fd = directory / "scalar-guard-mutant.py"
        mutant_fd.write_text(fd_source.replace(before, 'pass', 1))
        selected_guard = probe(mutant_fd, raw, None, directory)
        rational = PACKAGES / "evaluate_bounded_rational_expression/tools/evaluate_bounded_rational_expression.py"
        rows.append({"case": "rational_grammar_still_refuses_floating_literal",
                     **probe(rational, json.dumps({"expression": "1.0 + 1"}), None, directory)})
    report = {"record_type": "native_numeric_boundary_controls/v1", "checks": rows,
              "guards": [{"name": "decimal_classification_before_binary_rounding", "detected": not rounding["passed"], "mutant": rounding},
                         {"name": "selected_columns_still_require_scalars", "detected": not selected_guard["passed"], "mutant": selected_guard}],
              "script_sha256": hashlib.sha256(schedule.read_bytes()).hexdigest(),
              "provider_calls": 0, "approval": False,
              "passed": all(row["passed"] for row in rows) and not rounding["passed"] and not selected_guard["passed"]}
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(rows), "guard_removals_detected": sum(x["detected"] for x in report["guards"])}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
