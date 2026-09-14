"""Offline checks for terminal classification and resolution completion.

This module owns test fixtures only. It exercises the static terminal and
best-available-resolution contracts without a model, harness, network call,
workspace effect, database, or orchestration loop.
"""
from __future__ import annotations

from copy import deepcopy


def run_checks() -> dict:
    from .solve_terminal import (
        RESOLUTION_CONTRIBUTION_FIELDS,
        RESOLUTION_METHOD_IDS,
        SOLVE_FAILURE_CODES,
        SolveTerminalCode,
        build_task_resolution_package,
        failure_code_for,
        terminal_with_resolution,
        validate_resolution_input,
    )

    tests = [{
        "test": "a generic exception name does not name a layer never reached",
        "passed": failure_code_for({"failure_code": "RuntimeError"})
        != SolveTerminalCode.VERIFICATION_FAILED.value,
        "detail": failure_code_for({"failure_code": "RuntimeError"}),
    }, {
        "test": "a provider failure is named as one",
        "passed": failure_code_for({"failure_code": "rate_limited"})
        == SolveTerminalCode.PROVIDER_UNAVAILABLE.value,
        "detail": "",
    }, {
        "test": "the failure codes exclude the one success code",
        "passed": (SolveTerminalCode.COMPLETED_VERIFIED.value
                   not in SOLVE_FAILURE_CODES
                   and len(SOLVE_FAILURE_CODES) == len(
                       list(SolveTerminalCode)) - 1),
        "detail": "",
    }, {
        "test": "a_task_level_constraint_returns_a_completed_resolution",
        "passed": (terminal_with_resolution("BLOCKED_MATERIAL_INPUT")
                   == SolveTerminalCode.COMPLETED_PARTIAL.value
                   and terminal_with_resolution("PROVIDER_UNAVAILABLE")
                   == SolveTerminalCode.PROVIDER_UNAVAILABLE.value),
        "detail": "provider outages remain operational failures",
    }]
    package = build_task_resolution_package(
        task="Produce a report.",
        adaptive={
            "orientations": [{
                "ultimate_goal": "Produce a useful report.",
                "task_summary": "Analyze the supplied material.",
                "current_state": "One input is available.",
                "knowns": ["The available input has been read."],
                "unknowns": ["A second input is missing."],
                "assumptions": ["Use a stated provisional value."],
                "safe_defaults": ["Show a low and high scenario."],
                "proposed_next_action": (
                    "Replace the provisional value when observed.")}],
            "action_decisions": [{
                "decision_id": "decision-1",
                "inputs": {
                    "files": {"report.md": "provisional report\n"},
                    "resolution": {
                        "what_can_be_completed": [
                            "A draft can be completed."],
                        "what_cannot_be_completed": [
                            "The live effect cannot run."],
                        "missing_inputs_or_components": [
                            "One approval is missing."],
                        "analysis": [
                            "The available values support a draft."],
                        "assumptions": ["Use a provisional input."],
                        "scenario_analysis": ["Compare low and high cases."],
                        "pro_forma_analysis": [
                            "A pro forma result is available."],
                        "synthetic_material": [
                            "A synthetic example is labeled."],
                        "estimates": ["The estimate is a range."],
                        "analogous_solutions": [
                            "A similar case is adapted."],
                        "first_principles_solutions": [
                            "Constraints derive the approach."],
                        "supplemental_items": [
                            "An input template is included."],
                        "next_actions": ["Obtain the approval."]}}}],
            "verification": [{
                "remaining_gaps": ["Independent review is pending."],
                "operational_failures": []}],
            "recovery_directives": [],
        },
        product={"artifacts": (), "result": None},
        underlying_terminal="CAPABILITY_GAP",
        questions=(), limitations=(), suggested_next="Inspect the package.")
    tests.append({
        "test": "resolution_preserves_analysis_assumptions_gaps_and_candidate_output",
        "passed": (package.fulfillment_status == "provisional_outputs_available"
                   and package.provisional_outputs[0].path == "report.md"
                   and package.provisional_outputs[0].content
                   == "provisional report\n"
                   and "A second input is missing."
                   in package.missing_or_unverified
                   and package.to_dict()["response_complete"] is True
                   and package.pro_forma_analysis
                   == ("A pro forma result is available.",)
                   and package.synthetic_material
                   == ("A synthetic example is labeled.",)
                   and package.first_principles_solutions
                   == ("Constraints derive the approach.",)
                   and "Additional safe methods available" in package.report()),
        "detail": package.fulfillment_status,
    })
    valid_direct = {"resolution": {
        **{name: ["string"] for name in RESOLUTION_CONTRIBUTION_FIELDS},
        "constraint_code": "CAPABILITY_GAP",
        "method_assessments": [{
            "method_id": method_id,
            "disposition": "completed",
            "summary": "The fixture supplies the mapped contribution.",
            "evidence_refs": [],
        } for method_id in RESOLUTION_METHOD_IDS],
    }}
    invalid_direct = {"resolution": {
        **valid_direct["resolution"], "synthetic_material": "not an array"}}
    missing_method = deepcopy(valid_direct)
    missing_method["resolution"]["method_assessments"].pop()
    inconsistent_method = deepcopy(valid_direct)
    inconsistent_method["resolution"]["estimates"] = []

    def refuses(value):
        try:
            validate_resolution_input(value)
        except ValueError:
            return True
        return False

    tests.append({
        "test": "direct_resolution_requires_every_typed_contribution_field",
        "passed": (validate_resolution_input(valid_direct)["analysis"]
                   == ["string"] and refuses(invalid_direct)
                   and refuses(missing_method)
                   and refuses(inconsistent_method)
                   and package.response_complete
                   and len(package.method_assessments)
                   == len(RESOLUTION_METHOD_IDS)),
        "detail": (
            "malformed, incomplete, or falsely completed method coverage is "
            "refused before selection"),
    })
    from .solve_terminal import RESOLUTION_STATUSES

    empty_product = {"artifacts": (), "result": None}
    template_only = build_task_resolution_package(
        task="Invent a new theorem.", adaptive={}, product=empty_product,
        underlying_terminal="CAPABILITY_GAP", questions=(), limitations=(),
        suggested_next=(
            "Configure a supported model route or install a compatible "
            "capability."))
    restated = build_task_resolution_package(
        task="Produce a report.",
        adaptive={"orientations": [{
            "ultimate_goal": "Produce a useful report.",
            "task_summary": "Produce a report.",
            "current_state": "No work has been done.",
            "knowns": ["The task asks for a report."],
            "proposed_next_action": "ASK_USER"}]},
        product=empty_product, underlying_terminal="BLOCKED_MATERIAL_INPUT",
        questions=(), limitations=(),
        suggested_next="Answer the listed material questions.")
    interrupted = build_task_resolution_package(
        task="Produce a report.",
        adaptive={"action_decisions": [{
            "decision_id": "decision-1",
            "inputs": {"resolution": {
                **{name: [] for name in RESOLUTION_CONTRIBUTION_FIELDS},
                "analysis": ["The supplied values support a draft."],
                "next_actions": ["Resume when the provider answers."]}}}]},
        product=empty_product, underlying_terminal="PROVIDER_UNAVAILABLE",
        questions=(), limitations=(), suggested_next="")
    tests.append({
        "test": "runtime_guidance_alone_is_a_constraint_report_not_a_complete_resolution",
        "passed": (template_only.resolution_status == RESOLUTION_STATUSES[1]
                   and template_only.response_complete is False
                   and template_only.to_dict()["resolution_status"]
                   == RESOLUTION_STATUSES[1]
                   and all(item.disposition != "completed"
                           for item in template_only.method_assessments)
                   and template_only.fulfillment_status
                   == "constraint_report_only"),
        "detail": template_only.resolution_status,
    })
    tests.append({
        "test": "a_restated_task_does_not_complete_the_evidence_analysis_method",
        "passed": (restated.resolution_status == RESOLUTION_STATUSES[1]
                   and not any(
                       item.method_id == "available_evidence_analysis"
                       and item.disposition == "completed"
                       for item in restated.method_assessments)
                   and bool(restated.model_analysis)),
        "detail": restated.resolution_status,
    })
    tests.append({
        "test": "an_operational_interruption_is_never_a_complete_resolution",
        "passed": (interrupted.resolution_status == RESOLUTION_STATUSES[2]
                   and interrupted.response_complete is False
                   and any(item.disposition == "completed"
                           for item in interrupted.method_assessments)),
        "detail": interrupted.resolution_status,
    })
    passed = sum(1 for item in tests if item["passed"])
    return {
        "record_type": "solve_terminal_test/v1", "tests": tests,
        "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests)}


__all__ = ("run_checks",)
