"""Independent-process local launch checks and removed-guard controls.

Uses temporary records, loopback sockets and injected provider fixtures only.
Mutants change in-memory functions, never source files. The retained report
binds the complete package identity and does not assert provider qualification.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from architecture_audit_evidence import source_identity


def main():
    from loop_engine import decision_cli
    from loop_engine.core.decisions import contracts, jev, system_one, contract_checks
    from loop_engine.core import retrieval_backends, node_provisioning, spawned_provisioning
    from loop_engine.core.service_runtime import http_checks
    from loop_engine.core.service_runtime.http import ServiceHttpApplication
    from loop_engine.code_nodes import decision_tools, decision_gateway_checks
    from loop_engine.code_nodes.solution_model_port import ModelExecutionSession
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    before = source_identity(root)
    reports = {module.__name__: module.self_test() for module in (
        contracts, jev, system_one, decision_tools, decision_cli, retrieval_backends,
        node_provisioning, spawned_provisioning, http_checks)}
    from loop_engine.core.adaptive_practitioner_scope_checks import run_checks as scope_checks
    reports["loop_engine.core.adaptive_practitioner_scope_checks"] = scope_checks()
    from loop_engine.code_nodes.solve_provisioning_checks import run_checks as public_provisioning_checks
    reports["loop_engine.code_nodes.solve_provisioning_checks"] = {"tests": public_provisioning_checks()}
    mutants = []
    def rejected(name, result, required):
        failed = {row.get("test", row.get("name")) for row in result["tests"] if row.get("passed") is False}
        mutants.append({"name": name, "detected": bool(set(required) <= failed), "failed_checks": sorted(failed)})
    # The owning checks import this function by value. Mutate the reference
    # they actually invoke, not an unused name on the defining module.
    with patch.object(contract_checks, "admit_answers", lambda _request, answers: answers):
        rejected("remove_answer_admission", contracts.self_test(), ("answer_missing_refuses", "choice_winner_refuses"))
    original = jev.JevAdapter.prepare_decisions
    def unauthorized(self, request, *, model):
        mutated = replace(self, configuration=replace(self.configuration, allow_network=True, allow_model_calls=True))
        return original(mutated, request, model=model)
    with patch.object(jev.JevAdapter, "prepare_decisions", unauthorized):
        rejected("remove_provider_authority_guard", jev.self_test(),
                 ("discovery_and_disabled_provider_resolve_no_secret_and_send_nothing",))
    with patch.object(ModelExecutionSession, "calls_used", property(lambda self: 0)):
        rejected("remove_cumulative_call_accounting", decision_gateway_checks.run_checks(),
                 ("repeated_tool_calls_do_not_reset_the_session_budget",))
    original_binding = retrieval_backends.RetrievalBackendBinding.instantiate
    def unscoped(self, records, *, authority_effects=()):
        return original_binding(self, records, authority_effects=self.handshake.effects)
    with patch.object(retrieval_backends.RetrievalBackendBinding, "instantiate", unscoped):
        rejected("remove_retrieval_backend_effect_guard", retrieval_backends.self_test(),
                 ("effect_authority_is_checked_before_factory_execution",))
    with TemporaryDirectory(prefix="launch-revocation-control-") as temporary:
        cases = []
        with patch.object(ServiceHttpApplication, "_verify_search_snapshot", lambda *args: None):
            http_checks._retrieval_snapshot_checks(lambda name, ok: cases.append({"test": name, "passed": bool(ok)}), Path(temporary))
        rejected("remove_metadata_completion_authorization", {"tests": cases},
                 ("retrieval_completion_refuses_in_flight_revoke", "retrieval_completion_refuses_in_flight_replace",
                  "retrieval_completion_refuses_in_flight_entitlement"))
    after = source_identity(root)
    checks = [row for report in reports.values() for row in report["tests"]]
    result = {"record_type": "launch_slice_verification/v1", "scope": "local integration and removed-guard controls",
              "source_before": before, "source_after": after, "source_unchanged": before == after,
              "external_provider_calls": 0, "provider_qualified": False, "reports": reports,
              "passed": sum(row.get("passed") is True for row in checks), "total": len(checks),
              "mutants": mutants, "mutants_detected": sum(row["detected"] for row in mutants)}
    result["all_passed"] = (before == after and all(row.get("passed") is True for row in checks)
                            and all(row["detected"] for row in mutants))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({key: result[key] for key in ("passed", "total", "mutants_detected", "source_unchanged", "all_passed")}))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
