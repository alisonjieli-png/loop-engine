"""Focused checks for the failed first frozen verification attempt.

All mutations are in memory, and recipe/surface checks use temporary folders.
The diagnostic preserves distinct source-nomenclature and public-language gates.
"""
from copy import deepcopy
import inspect
import json
import textwrap
from unittest.mock import patch

from loop_engine import _conformance_scan as scanner, _conformance_test
from loop_engine import conformance_report
from loop_engine._self_test import _module_test_records
from loop_engine.code_nodes import data_quality_surfaces
from loop_engine.core import harness_remaining_recipe_checks


def records(name, function):
    return _module_test_records(name, function())


def mutated(function, module, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(before) != 1:
        raise RuntimeError("mutation target must occur exactly once")
    namespace = dict(vars(module))
    exec(compile(source.replace(before, after), "<runtime-regression-mutant>", "exec"), namespace)
    return namespace[function.__name__]


if __name__ == "__main__":
    suites = {}
    for name, module in (("core.harness_remaining_recipe_checks", harness_remaining_recipe_checks),
                         ("code_nodes.data_quality_surfaces", data_quality_surfaces)):
        tests = records(name, module.self_test)
        suites[name] = {"passed": sum(item["passed"] is True for item in tests),
                        "total": len(tests),
                        "failed": [item["test"] for item in tests if not item["passed"]]}
    results = []
    old_recipe_shape = mutated(harness_remaining_recipe_checks.self_test,
        harness_remaining_recipe_checks,
        '    return {"record_type": "harness_remaining_recipe_checks/v1", "tests": tests,\n'
        '            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}',
        '    return results')
    try:
        records("core.harness_remaining_recipe_checks", old_recipe_shape)
    except ValueError as error:
        results.append({"mutant": "restore_unstructured_recipe_results", "detected": True,
                        "error": str(error)})
    else:
        results.append({"mutant": "restore_unstructured_recipe_results", "detected": False})
    old_request = mutated(data_quality_surfaces.self_test, data_quality_surfaces,
        '    request = SolveRequest(intake_task(TaskIntakeRequest(text="Inspect declared family surfaces.")),\n'
        '                           practitioner_mode="deterministic")',
        '    request = SimpleNamespace(model_execution=None, progress=None, reuse_observation_port=None,\n'
        '                              project_executor=None, extension_snapshot={}, host_runtime=None)')
    try:
        records("code_nodes.data_quality_surfaces", old_request)
    except AttributeError as error:
        results.append({"mutant": "restore_incomplete_request_fixture", "detected": True,
                        "error": str(error)})
    else:
        results.append({"mutant": "restore_incomplete_request_fixture", "detected": False})
    with patch.object(harness_remaining_recipe_checks, "extract_remaining_output", return_value=""):
        wrong_output = records("core.harness_remaining_recipe_checks", harness_remaining_recipe_checks.self_test)
    results.append({"mutant": "extract_no_candidate_output", "detected": any(not item["passed"] for item in wrong_output),
                    "failed_checks": [item["test"] for item in wrong_output if not item["passed"]]})
    policy_before = deepcopy(scanner._rules())
    findings_before = scanner.scan_retired_source_nomenclature(scanner._HERE, scanner._rules())
    prior_tests = _conformance_test.self_test()["tests"]
    findings_after = scanner.scan_retired_source_nomenclature(scanner._HERE, scanner._rules())
    print(json.dumps({"record_type": "runtime_regression_probe/v1", "provider_calls": 0,
        "suites": suites, "mutants": results,
        "preceding_conformance_tests": {"passed": sum(item["passed"] is True for item in prior_tests),
                                         "total": len(prior_tests)},
        "policy_unchanged": policy_before == scanner._rules(),
        "findings_unchanged": findings_before == findings_after,
        "all_source_term_findings": findings_before,
        "public_decision_spine_findings": conformance_report._public_retired_nomenclature()}, indent=2))
    raise SystemExit(0 if all(item["passed"] == item["total"] for item in suites.values())
                     and all(item["detected"] for item in results)
                     and policy_before == scanner._rules()
                     and findings_before == findings_after else 1)
