"""The endpoint handlers behind the hosted service surface.

The core service surface owns authentication, dispatch, and metering and
knows nothing about conformance or evaluation; this module supplies the
handlers it dispatches to, so the dependency runs from code nodes to core
and never the other way. Each handler takes the authenticated tenant, the
parsed request payload, the metering ledger, and the clock, runs the work
through the existing modules, and returns the response record. Metering
decisions live here because they read the shape of the work: a conformed
row that needed no escalation is one avoided model call; an evaluation run
is metered by its wall-clock hours.

``solver_from_spec`` builds the solver a suite is scored with; the
``evaluate`` and ``optimize`` commands and the evaluate endpoint share it.
"""
from __future__ import annotations

from ..core.evaluation_suite import EvaluationSuite, EvaluationSuiteError, evaluate_suite
from ..core.service_api import METERING_UNITS, MeteringRecord, ServiceError

SOLVER_KINDS = ("text_conformance", "recorded")


def solver_from_spec(spec: dict, cell: dict | None = None):
    """A solver callable and its identifier; a cell overrides policy and catalog values."""
    kind = str(spec.get("kind") or "")
    if kind not in SOLVER_KINDS:
        raise EvaluationSuiteError(f"solver kind must be one of {SOLVER_KINDS}")
    cell = dict(cell or {})
    if kind == SOLVER_KINDS[1]:
        outputs = spec.get("outputs")
        if not isinstance(outputs, dict):
            raise EvaluationSuiteError("a recorded solver needs outputs by case identifier")
        return lambda case: outputs[case.case_id], f"recorded@{len(outputs)}"
    from .text_conformance import (CATALOG_SOURCES, ConformancePolicy, ConformanceRule, ExceptionCatalogLayer,
                                   catalog_layer_from_file, load_packaged_catalogs, merge_layers,
                                   run_conformance)
    column = str(spec.get("column") or "value")
    rules = tuple(ConformanceRule.from_dict(item) for item in spec.get("rules") or ())
    policy_record = dict(spec.get("policy") or {})
    catalog_overrides = dict(spec.get("inline_catalogs") or {})
    for name, value in cell.items():
        if name in ("apply_at_or_above", "escalate_below", "escalate_held"):
            policy_record[name] = value
        else:
            catalog_overrides[name] = value
    policy = ConformancePolicy.from_dict(policy_record)
    layers = [load_packaged_catalogs()]
    root = str(spec.get("catalog_root") or ".")
    for item in spec.get("catalog_files") or ():
        layers.append(catalog_layer_from_file(str(item), root))
    if catalog_overrides:
        layers.append(ExceptionCatalogLayer("cell", CATALOG_SOURCES[3], catalog_overrides))
    catalogs = merge_layers(layers)

    def solve(case):
        run = run_conformance([{column: case.input}], rules, policy, catalogs, learn_evidence=False)
        return run.output_rows[0][column]

    return solve, f"text_conformance@{policy.apply_at_or_above}/{policy.escalate_below}"


def conform_handler(tenant, payload: dict, ledger, clock) -> dict:
    """Run conformance rules over rows; meter one avoided model call per row conformed without escalation."""
    from .text_conformance import (ConformancePolicy, ConformanceRule, load_packaged_catalogs, merge_layers,
                                   run_conformance)
    rows = payload.get("rows")
    if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
        raise ServiceError("rows must be a list of objects")
    rules = tuple(ConformanceRule.from_dict(item) for item in payload.get("rules") or ())
    policy = ConformancePolicy.from_dict(payload.get("policy") or {})
    run = run_conformance(rows, rules, policy, merge_layers([load_packaged_catalogs()]))
    escalated_rows = {item.row_ref for item in run.escalations}
    corrected_rows = {item.row_ref for item in run.corrections if item.outcome == "applied"}
    avoided = len(corrected_rows - escalated_rows)
    report = run.report.to_dict()
    if avoided:
        ledger.add(MeteringRecord(tenant.tenant_id, METERING_UNITS[1], float(avoided),
                                  report["content_digest"], clock()))
    return {"record_type": "service_conform_response/v1", "tenant_id": tenant.tenant_id,
            "report": report, "output_rows": list(run.output_rows),
            "corrections": [item.to_dict() for item in run.corrections],
            "escalations": [item.to_dict() for item in run.escalations],
            "decisions": [item.to_dict() for item in run.decisions],
            "metered": {"avoided_model_call": avoided}}


def evaluate_handler(tenant, payload: dict, ledger, clock) -> dict:
    """Score a suite with a solver specification; meter the wall-clock hours."""
    suite = EvaluationSuite.from_dict(payload.get("suite") or {})
    solver, solver_id = solver_from_spec(payload.get("solver") or {})
    started = clock()
    report = evaluate_suite(suite, solver, solver_id=solver_id).to_dict()
    hours = max(0.0, clock() - started) / 3600.0
    ledger.add(MeteringRecord(tenant.tenant_id, METERING_UNITS[2], hours, report["content_digest"], clock()))
    return {"record_type": "service_evaluate_response/v1", "tenant_id": tenant.tenant_id,
            "report": report, "metered": {"optimize_hour": round(hours, 9)}}


def default_handlers() -> dict:
    """The handlers the service dispatches to, keyed by endpoint."""
    return {"conform": conform_handler, "evaluate": evaluate_handler}


def self_test() -> dict:
    """The real handlers run through the service surface, meter honestly, and refuse bad payloads."""
    import json
    from ..core.service_api import ServiceApplication, new_tenant
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    tenant, key = new_tenant("acme", "tenant:acme")
    ticks = iter(range(100))
    application = ServiceApplication((tenant,), handlers=default_handlers(), clock=lambda: 1000.0 + next(ticks))
    payload = {"rows": [{"name": "ACME CORPORATION", "email": "A@Example.com"},
                        {"name": "AA CAREERS", "email": "ok@example.org"},
                        {"name": "ACME INC", "email": "bad@"}],
               "rules": [{"rule_id": "case", "operation": "case_normalize", "columns": ["name"]},
                         {"rule_id": "suffix", "operation": "suffix_canonicalize", "columns": ["name"]},
                         {"rule_id": "email", "operation": "email_normalize", "columns": ["email"]}]}
    status, body = application.handle("POST", "/v1/conform", key, json.dumps(payload).encode("utf-8"))
    usage = application.ledger.usage("acme")
    check("the_conform_endpoint_runs_the_rules_and_meters_avoided_model_calls_without_bodies",
          status == 200 and body["output_rows"][0]["name"] == "Acme Corp"
          and body["output_rows"][2]["name"] == "Acme Inc" and len(body["escalations"]) == 1
          and len(body["decisions"]) == 1 and body["metered"]["avoided_model_call"] == 1
          and usage["totals"]["avoided_model_call"] == 1.0
          and all("ACME" not in json.dumps(item.to_dict()) for item in application.ledger.records)
          and application.handle("POST", "/v1/conform", key, json.dumps({"rows": "x"}).encode("utf-8"))[0] == 422)
    suite = {"record_type": "evaluation_suite/v1", "suite_id": "s", "version": "1.0.0",
             "cases": [{"case_id": "c1", "input": "ACME CORP", "expected": "Acme Corp"},
                       {"case_id": "c2", "input": "AA CAREERS", "expected": "AA Careers"}]}
    solver = {"kind": "text_conformance", "column": "name",
              "rules": [{"rule_id": "case", "operation": "case_normalize", "columns": ["name"]},
                        {"rule_id": "suffix", "operation": "suffix_canonicalize", "columns": ["name"]}]}
    status, body = application.handle("POST", "/v1/evaluate", key,
                                      json.dumps({"suite": suite, "solver": solver}).encode("utf-8"))
    check("the_evaluate_endpoint_scores_a_suite_and_meters_optimize_hours",
          status == 200 and body["report"]["passed"] == 1 and body["report"]["denominator"] == 2
          and body["metered"]["optimize_hour"] > 0
          and application.ledger.usage("acme")["totals"]["optimize_hour"] > 0
          and application.handle("POST", "/v1/evaluate", key, b"{}")[0] == 422)
    recorded, recorded_id = solver_from_spec({"kind": "recorded", "outputs": {"c1": "x"}})
    cell_solver, cell_id = solver_from_spec({**solver, "policy": {"apply_at_or_above": 0.9}},
                                            {"apply_at_or_above": 0.7, "short_token_confidence": 0.9})
    check("solvers_are_built_from_specifications_and_cells_override_policy_and_catalog_values",
          recorded_id == "recorded@1" and cell_id == "text_conformance@0.7/0.6"
          and cell_solver(type("Case", (), {"input": "AA CAREERS", "case_id": "c"})()) == "AA Careers")
    passed = sum(item["passed"] for item in results)
    return {"record_type": "service_endpoints_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
