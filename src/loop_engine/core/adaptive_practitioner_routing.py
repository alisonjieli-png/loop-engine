"""Adaptive Practitioner routing after subject-bound verification.

Owns the orchestration join among the model-proposed route, the pure action
vector continuation guard, exact final-acceptance binding, and stalled-work
recovery. It does not evaluate action results, execute recovery, define vector
semantics, call capabilities, or grant authority.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ..code_nodes.solution_model_port import SolutionModelError
from .model_response_admission import ModelResponseRepairStalled
from ..loop.kernel import PractitionerState, RouteDecision
from ..loop.kernel_runtime import current_kernel_owner
from .action_vector_routing import (
    ActionVectorRouteRequest,
    guard_action_vector_route,
)
from .adaptive_host_verification import require_host_checks
from .adaptive_practitioner_records import (
    AdaptivePractitionerError,
    AdaptiveRunServices,
    ModelStepRequest,
)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest,
    resolve_stall_with_panel,
)
from .adaptive_practitioner_result import latest_task_result, task_result_succeeded
from .adaptive_practitioner_supervision import detect_stall
from .adaptive_practitioner_validation import MODEL_ROUTE_VALUES, _short_text
from .adaptive_practitioner_verification import (
    AdaptiveEvaluationBindingRequest,
    selected_project_matches,
    validate_adaptive_evaluation,
)
from .independent_evidence import ACCEPT


@dataclass(frozen=True)
class AdaptiveRouteRequest:
    """Integrated state, pass record, and safe model projection."""

    state: PractitionerState
    record: object
    model_state: dict


@dataclass(frozen=True)
class _RouteEvidence:
    """The verification evidence every proposed route is checked against."""

    request: AdaptiveRouteRequest
    services: AdaptiveRunServices
    final_result: object
    deterministic_pass: bool


def route_adaptive_result(
        request: AdaptiveRouteRequest,
        services: AdaptiveRunServices) -> tuple:
    """Choose continuation or success after verification, with safe fallback."""
    evaluation = request.record.evaluation
    final_result = latest_task_result(services)
    deterministic_pass = task_result_succeeded(final_result)
    route_semantic_observed = False
    model_selected_route = ""
    try:
        value = services.model(ModelStepRequest(
            "route", "Choose the next pass or finish the verified task.",
            {**request.model_state, "evaluation": asdict(evaluation),
             "deterministic_project_passed": deterministic_pass,
             "pass_number": request.record.pass_number},
            json.dumps({"route": "|".join(MODEL_ROUTE_VALUES),
                        "reason": "string"}, separators=(",", ":"))))
        selected = str(value.get("route"))
        if selected not in MODEL_ROUTE_VALUES:
            raise AdaptivePractitionerError(
                f"route {selected!r} is not admitted; the admitted routes "
                f"are {list(MODEL_ROUTE_VALUES)}")
        reason = _short_text(value.get("reason"), "route reason")
        route_semantic_observed = True
        model_selected_route = selected
    except (AdaptivePractitionerError, SolutionModelError, ModelResponseRepairStalled,
            TypeError, ValueError) as exc:
        services.diagnostic("route_model_unavailable", {
            "error_type": type(exc).__name__,
            "verification_verdict": evaluation.verdict})
        selected = ("stop_success" if evaluation.verdict == ACCEPT
                    and deterministic_pass else "repair")
        reason = (
            "Deterministic route policy used after semantic route failure; "
            "final success still requires accepted verification.")
    evidence = _RouteEvidence(request, services, final_result, deterministic_pass)
    selected, reason, continuation = _guarded_route(evidence, selected, reason)
    stall = (None if selected in ("stop_success", "stop_unprofitable")
             else detect_stall(services, request.state))
    if stall is not None:
        try:
            directive = resolve_stall_with_panel(
                RecoveryPanelRequest(
                    stall, request.model_state, request.record.pass_number),
                services)
            selected = directive["route"]
            reason = directive["reason"]
        except (AdaptivePractitionerError, SolutionModelError, ModelResponseRepairStalled,
                TypeError, ValueError) as exc:
            services.diagnostic("recovery_panel_unavailable", {
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "recovery_round": services.recovery_rounds + 1})
            selected = "reframe"
            reason = (
                "Recovery panel was unavailable. Reframe with the preserved "
                "stall signal and attempt history; do not claim success.")
        # The panel's directive passes the same guard and binding as the
        # model's route. A directive that skipped them could stop a run that
        # the action vector records as having safe authorized work left, or
        # publish success without the exact verification binding.
        selected, reason, panel_continuation = _guarded_route(
            evidence, selected, reason)
        if isinstance(panel_continuation, bool):
            continuation = panel_continuation
    failures = request.state.failures
    grade = getattr(services, "grade_current_stage", None)
    if route_semantic_observed and callable(grade):
        aligned = selected == model_selected_route
        grade(
            observable_process_aligned=aligned,
            expected_output_satisfied=aligned,
            material_progress=aligned,
            **({"continuation_available": continuation}
               if isinstance(continuation, bool) else {}))
    if selected in ("repair", "retry", "reframe"):
        failures = failures + (reason,)
    return RouteDecision(selected, reason), request.state.derive(
        failures=failures, last_route=selected)


def _guarded_route(
        evidence: _RouteEvidence, selected: str, reason: str) -> tuple:
    """Apply the action vector guard and final acceptance binding to a route."""
    request, services = evidence.request, evidence.services
    evaluation = request.record.evaluation
    verification_record = (
        services.verification_records[-1]
        if services.verification_records else {})
    vector_record = verification_record.get("action_vector")
    # Acceptance here is the owning Loop's accepted verdict plus passing
    # deterministic checks; the exact evaluation binding is still validated
    # below before any success is published.
    acceptance_established = bool(
        evaluation.verdict == ACCEPT and evidence.deterministic_pass)
    try:
        vector_route = guard_action_vector_route(ActionVectorRouteRequest(
            selected, vector_record if isinstance(vector_record, dict) else None,
            request.record.pass_number,
            acceptance_established=acceptance_established))
    except (TypeError, ValueError) as exc:
        services.diagnostic("action_vector_route_invalid", {
            "error_type": type(exc).__name__})
        vector_route = guard_action_vector_route(ActionVectorRouteRequest(
            selected, {"record_type":
                       "action_vector_assessment_unavailable/v1"},
            request.record.pass_number,
            acceptance_established=acceptance_established))
    if vector_route.guarded:
        selected, reason = vector_route.route, vector_route.reason
        services.supervision_findings.append(vector_route.to_dict())
    if selected == "stop_success" and (
            evaluation.verdict != ACCEPT or not evidence.deterministic_pass):
        selected = "repair"
    if selected == "stop_success":
        try:
            validate_adaptive_evaluation(AdaptiveEvaluationBindingRequest(
                request.record.plan, tuple(request.record.results), evaluation),
                services)
            if not selected_project_matches(
                    request.record, evidence.final_result):
                raise ValueError("verified result is not the emitted task result")
            require_host_checks(
                services.verification_records[-1], request.record.results,
                services, current_kernel_owner(), task_complete=True)
        except (AttributeError, TypeError, ValueError) as exc:
            selected = "repair"
            reason = (
                "Final success requires exact recorded verification of this result.")
            services.diagnostic("verification_binding_invalid", {
                "error_type": type(exc).__name__, "reason": str(exc)[:300]})
    return selected, reason, vector_route.continuation_available


def self_test() -> dict:
    """Test adaptive route integration without executing a task or provider."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from ..loop.kernel import EvaluationPacket, ProblemSpec

    def services_for(route, verdict):
        return SimpleNamespace(
            model=lambda _request: {
                "route": route, "reason": "model-selected route"},
            project_attempts=[{"manifest_digest": "m",
                               "deterministic_checks_passed": True}],
            progress_snapshots=[], unchanged_progress_snapshots=0,
            source_inspections=[], web_results=[], action_history=[],
            verification_records=[{"verdict": verdict}],
            active_recovery_directive=None, recovery_rounds=0,
            supervision_findings=[], diagnostic=lambda *_args, **_kw: None)

    state = PractitionerState(ProblemSpec("route selection proof"))
    accepted_record = SimpleNamespace(
        evaluation=EvaluationPacket("accept"), pass_number=1)
    continued, _state = route_adaptive_result(
        AdaptiveRouteRequest(state, accepted_record, {}),
        services_for("continue", "accept"))
    repair_record = SimpleNamespace(
        evaluation=EvaluationPacket("repair"), pass_number=1)
    reframed, _state = route_adaptive_result(
        AdaptiveRouteRequest(state, repair_record, {}),
        services_for("reframe", "repair"))
    continuing_services = services_for("stop_unprofitable", "repair")
    continuing_services.verification_records[-1]["action_vector"] = {
        "record_type": "action_vector_assessment/v1",
        "outcome_signals": {
            "observable_process_aligned": True,
            "expected_output_satisfied": False,
            "requested_output_satisfied": False,
            "material_progress": True,
            "continuation_available": True}}
    guarded, _state = route_adaptive_result(
        AdaptiveRouteRequest(state, repair_record, {}), continuing_services)
    accepted_services = services_for("stop_success", "accept")
    accepted_services.verification_records[-1]["action_vector"] = {
        "record_type": "action_vector_assessment/v1",
        "outcome_signals": {
            "observable_process_aligned": True,
            "expected_output_satisfied": True,
            "requested_output_satisfied": True,
            "material_progress": True,
            "continuation_available": True}}
    route_adaptive_result(
        AdaptiveRouteRequest(state, accepted_record, {}), accepted_services)
    # A stalled pass hands its route to the recovery panel. The panel's stop
    # must meet the same guard: overridden while safe authorized work
    # remains, and left standing when the vector records none.
    panel_outcomes = {}
    for continuation in (True, False):
        stalled_services = services_for("repair", "repair")
        stalled_services.verification_records[-1]["action_vector"] = {
            "record_type": "action_vector_assessment/v1",
            "outcome_signals": {
                "observable_process_aligned": True,
                "expected_output_satisfied": False,
                "requested_output_satisfied": False,
                "material_progress": True,
                "continuation_available": continuation}}
        with patch(f"{__name__}.detect_stall",
                   return_value={"stall_id": "stall.route_test"}), \
                patch(f"{__name__}.resolve_stall_with_panel", return_value={
                    "route": "stop_unprofitable",
                    "reason": "The panel proposed an honest stop."}):
            decision, _state = route_adaptive_result(
                AdaptiveRouteRequest(state, repair_record, {}),
                stalled_services)
        panel_outcomes[continuation] = (
            decision.route, stalled_services.supervision_findings)
    tests = [{
        "test": "accepted_result_can_follow_model_selected_continue_route",
        "passed": continued.route == "continue",
    }, {
        "test": "repair_verdict_preserves_model_selected_reframe_route",
        "passed": reframed.route == "reframe",
    }, {
        "test": "adaptive_route_applies_the_pure_vector_guard",
        "passed": (guarded.route == "repair"
                   and continuing_services.supervision_findings[-1][
                       "record_type"] == "action_vector_route_decision/v1"),
    }, {
        "test": "accepted_verified_result_is_not_rewritten_by_the_continuation_guard",
        "passed": not any(
            item.get("record_type") == "action_vector_route_decision/v1"
            for item in accepted_services.supervision_findings),
    }, {
        "test": "recovery_panel_stop_meets_the_vector_guard_while_work_remains",
        "passed": (panel_outcomes[True][0] == "repair"
                   and panel_outcomes[True][1][-1]["record_type"]
                   == "action_vector_route_decision/v1"),
    }, {
        "test": "recovery_panel_stop_stands_when_no_safe_authorized_work_remains",
        "passed": panel_outcomes[False][0] == "stop_unprofitable",
    }]
    return {
        "record_type": "adaptive_practitioner_routing_test/v1",
        "tests": tests, "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests)}


__all__ = ("AdaptiveRouteRequest", "route_adaptive_result", "self_test")
