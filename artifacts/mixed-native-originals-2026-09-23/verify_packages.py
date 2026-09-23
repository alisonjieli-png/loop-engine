"""Bounded original-tool fixtures in a minimal no-network Bubblewrap instance."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from loop_engine.core.library_ingestion.processes import run_command
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
RUNNER = '''import resource, runpy, sys
resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
sys.argv = ["/package/tool.py"]
with open("/input.json", "r", encoding="utf-8") as stream:
    sys.stdin = stream
    runpy.run_path("/package/tool.py", run_name="__main__")
'''
ALLOWED_IMPORTS = {"json", "math", "re", "sys", "graphlib", "itertools", "fractions", "ast"}
MUTANTS = {
    "schedule_dag_earliest_times": ('start = max((finishes[parent]', 'start = min((finishes[parent]'),
    "cover_pairwise_configuration_values": ('uncovered -= coverage[best]', 'uncovered.clear()'),
    "compare_primitive_object_contracts": ('add("changed_type", field)', 'pass'),
    "pack_first_fit_decreasing_batches": ('target = next((bucket for bucket in bins if bucket["used"] + item["size"] <= value["capacity"]), None)', 'target = None'),
    "audit_functional_dependency_rows": ('if len(group["dependent_variants"]) > 1]', 'if False]'),
    "find_strongly_connected_components": ('len(group) > 1 or (group[0], group[0]) in edge_set', 'len(group) > 1'),
    "simulate_exact_token_bucket": ('previous) * value["refill_per_second"], 1000)', 'previous) * value["refill_per_second"], 1)'),
    "audit_boolean_rule_coverage": ('elif len(decisions) > 1:', 'elif False:'),
    "decode_u16_length_prefixed_frames": ('need(size <= 1024 and offset + size <= len(data))', 'need(size <= 1024)'),
    "evaluate_bounded_rational_expression": ('result = left + right', 'result = left - right'),
    "resolve_literal_named_template": ('need(names_used == set(value["variables"]))', 'need(names_used <= set(value["variables"]))'),
    "project_json_pointer_values": ('encoded.replace("~1", "/").replace("~0", "~")', 'encoded.replace("~0", "~").replace("~1", "/")'),
}


def command(script, input_path, runner):
    args = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--dir", "/work",
            "--ro-bind", str(script), "/package/tool.py", "--ro-bind", str(input_path), "/input.json",
            "--ro-bind", str(runner), "/runner.py", "--chdir", "/work",
            "--setenv", "HOME", "/tmp", "--setenv", "PATH", "/usr/bin:/bin",
            "--", "/usr/bin/python3", "-I", "-S", "-B", "/runner.py"]
    return tuple(args)


def run_case(script, case, directory, validator):
    input_path, runner = directory / "input.json", directory / "runner.py"
    input_path.write_text(json.dumps(case["input"]))
    runner.write_text(RUNNER)
    result = run_command(command(script, input_path, runner), timeout_seconds=4,
                         maximum_output_bytes=65537, environment={"PATH": "/usr/bin:/bin"})
    expected = case["expected"] if case["expected"] is not None else {"error": "invalid_input"}
    try:
        output = json.loads(result.stdout)
    except (UnicodeError, ValueError):
        output = None
    schema_ok = case["expected_exit"] != 0 or (output is not None and validator.is_valid(output))
    return {"expected_exit": case["expected_exit"], "actual_exit": result.exit_code,
            "output": output, "schema_valid": schema_ok, "timed_out": result.timed_out,
            "truncated": result.truncated, "stderr": result.stderr_tail,
            "passed": result.exit_code == case["expected_exit"] and output == expected
                      and schema_ok and not result.timed_out and not result.truncated}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--packages", type=Path, default=HERE / "authored")
    parser.add_argument("--mutants", action="store_true")
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("Use a new report path")
    inventory_path = args.packages.parent / "items.json"
    inventory = json.loads(inventory_path.read_text()) if inventory_path.is_file() else {"items": []}
    bindings = {row["reference"]["identity"]: row["reference"]["digest"] for row in inventory["items"]}
    rows, mutants = [], []
    with tempfile.TemporaryDirectory(prefix="baltor-original-tool-checks-") as temp:
        directory = Path(temp)
        for folder in sorted(args.packages.iterdir()):
            identity = folder.name
            script = folder / "tools" / f"{identity}.py"
            source = script.read_text()
            syntax = ast.parse(source)
            imports = [node.module.split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
                       for node in ast.walk(syntax) if isinstance(node, (ast.Import, ast.ImportFrom))
                       for alias in (node.names if isinstance(node, ast.Import) else [None])]
            if not set(imports) <= ALLOWED_IMPORTS:
                raise ValueError("Unexpected candidate dependency")
            input_schema = json.loads((folder / "contracts/input.schema.json").read_text())
            output_schema = json.loads((folder / "contracts/output.schema.json").read_text())
            Draft202012Validator.check_schema(input_schema)
            Draft202012Validator.check_schema(output_schema)
            validator = Draft202012Validator(output_schema)
            input_validator = Draft202012Validator(input_schema)
            cases = json.loads((folder / "verification/cases.json").read_text())
            checks = [run_case(script.resolve(), case, directory, validator) for case in cases]
            for case, check in zip(cases, checks):
                check["input_schema_valid"] = input_validator.is_valid(case["input"])
                if case["expected_exit"] == 0 and not check["input_schema_valid"]:
                    check["passed"] = False
            rows.append({"identity": identity, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                         "package_digest": bindings.get(identity),
                         "payload_digests": {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                                             for path in sorted(folder.rglob("*")) if path.is_file()},
                         "imports": imports, "checks": checks, "passed": all(row["passed"] for row in checks)})
            if args.mutants:
                before, after = MUTANTS[identity]
                if source.count(before) != 1:
                    raise ValueError("Mutant anchor must be exact and unique")
                mutant = directory / "mutant.py"
                mutant.write_text(source.replace(before, after, 1))
                checks = [run_case(mutant.resolve(), case, directory, validator) for case in cases]
                mutants.append({"identity": identity, "mutation": {"before": before, "after": after},
                                "detected": any(not row["passed"] for row in checks), "checks": checks})
    passed = all(row["passed"] for row in rows) and all(row["detected"] for row in mutants)
    report = {"record_type": "original_native_method_verification/v1", "passed": passed,
              "sandbox": {"engine": "bubblewrap", "network": "unshare-all", "home_mounted": False,
                          "mounted_inputs": ["read-only /usr", "one candidate script", "synthetic input", "trusted resource-limit runner"],
                          "cpu_seconds": 2, "address_space_bytes": 268435456, "wall_timeout_seconds": 4,
                          "environment": "clearenv, HOME=/tmp, PATH=/usr/bin:/bin", "execution": "python3 -I -S -B"},
              "packages": rows, "mutants": mutants, "model_calls": 0,
              "independent_approval": False, "native_harness_loading_proven": False}
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": passed, "packages": len(rows), "cases": sum(len(row["checks"]) for row in rows),
                      "mutants_detected": sum(row["detected"] for row in mutants)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
