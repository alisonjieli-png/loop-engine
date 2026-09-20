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
    AdaptiveRunServices,
    ModelStepRequest,
)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest,
    resolve_stall_with_panel,
)
from .adaptive_practitioner_result import latest_task_result, task_result_succeeded
from .adaptive_practitioner_supervision import detect_stall
from .adaptive_practitioner_validation import AdaptivePractitionerError, MODEL_ROUTE_VALUES, _short_text
from .response_contracts import PRACTITIONER_ROUTE, registered_contract
from ..loop.supervision_policy import BUDGET_PHASES, SupervisionPolicy
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
            registered_contract(PRACTITIONER_ROUTE).contract_json(),
            contract_id=PRACTITIONER_ROUTE))
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
    selected, reason = _budget_phase_route(evidence, selected, reason)
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


def _budget_phase_route(
        evidence: "_RouteEvidence", selected: str, reason: str) -> tuple:
    """Demote exploration routes to consolidation inside a declared phase.

    The supervision policy's declared budget-phase thresholds decide the
    phase from the calls the run's own model session reports. Without a
    declared policy the phase is ``explore`` and no route changes. In
    ``conserve`` the run stops opening new branches and consolidates what
    exists; in ``final_verify`` it presents the best available result for
    verification instead of any new generation. Success and honest stops are
    never demoted, and the demotion is recorded as a diagnostic.
    """
    request, services = evidence.request, evidence.services
    policy = services.services_request_effective_supervision()
    maximum = services.model_authority_max_model_calls()
    explore, conserve = BUDGET_PHASES[0], BUDGET_PHASES[1]
    phase = (policy.budget_phase(services.model_calls_used(), maximum)
             if isinstance(policy, SupervisionPolicy) else explore)
    if phase == explore or selected in (
            "stop_success", "stop_unprofitable"):
        return selected, reason
    if selected in ("explore_branch", "continue", "retry", "soft_reset",
                     "cold_restart"):
        demoted = "repair" if phase == conserve else "reframe"
        services.diagnostic("budget_phase_route_demoted", {
            "phase": phase,
            "model_selected_route": selected,
            "demoted_route": demoted,
            "calls_used": services.model_calls_used(),
            "maximum_calls": maximum,
            "reason": ("The remaining model-call authority is below the "
                       "declared conserve threshold; consolidate existing "
                       "work instead of opening new branches."
                       if phase == conserve else
                       "The remaining model-call authority is below the "
                       "declared final-verification threshold; present the "
                       "best available result for verification.")})
        return demoted, (
            "Budget phase " + phase + " demoted route " + selected +
            " to " + demoted + "; remaining call authority is below the "
            "declared threshold.")
    return selected, reason


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


def _phase_services(services, calls_used: int, maximum_calls: int):
    """Fixture: a run whose declared phase policy and budget are known."""
    from ..loop.supervision_policy import SupervisionPolicy
    services.model_calls_used = lambda: calls_used
    services.model_authority_max_model_calls = lambda: maximum_calls
    services.services_request_effective_supervision = (
        lambda: SupervisionPolicy(budget_phase_thresholds=(0.3, 0.1)))
    return services


def _evidence_for(services, calls_used: int, maximum_calls: int):
    """Fixture: phase-gate evidence with a known budget and phase policy."""
    from types import SimpleNamespace as _Namespace

    from ..loop.kernel import EvaluationPacket, ProblemSpec

    _phase_services(services, calls_used, maximum_calls)
    state = PractitionerState(ProblemSpec("phase gate proof"))
    request = AdaptiveRouteRequest(state, _Namespace(
        evaluation=EvaluationPacket("accept"), pass_number=1), {})
    return _RouteEvidence(request, services, None, True)


def _phase_demoted_diagnostics(services, calls_used: int,
                               maximum_calls: int) -> bool:
    """Fixture: the demotion of a phase route is recorded, not silent."""
    from types import SimpleNamespace as _Namespace

    from ..loop.kernel import EvaluationPacket, ProblemSpec

    recorded = []
    services.diagnostic = lambda code, payload: recorded.append((code, payload))
    _phase_services(services, calls_used, maximum_calls)
    state = PractitionerState(ProblemSpec("phase diagnostic proof"))
    record = _Namespace(
        evaluation=EvaluationPacket("accept"), pass_number=1)
    route_adaptive_result(
        AdaptiveRouteRequest(state, record, {}), services)
    return (bool(recorded)
            and recorded[0][0] == "budget_phase_route_demoted"
            and recorded[0][1]["phase"] == "conserve")


def self_test() -> dict:
    """Test adaptive route integration without executing a task or provider."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from ..loop.kernel import EvaluationPacket, ProblemSpec
    from ..loop.supervision_policy import (
        DEFAULT_SUPERVISION_POLICY, SupervisionPolicy)

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
            supervision_findings=[], diagnostic=lambda *_args, **_kw: None,
            model_calls_used=lambda: None,
            model_authority_max_model_calls=lambda: None,
            services_request_effective_supervision=lambda: (
                DEFAULT_SUPERVISION_POLICY))

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
    }, {
        # The declared budget phase demotes exploration routes but never a
        # verified success or an honest stop, and a default policy with no
        # declared thresholds changes nothing.
        "test": "undeclared_budget_phase_leaves_every_route_unchanged",
        "passed": route_adaptive_result(
            AdaptiveRouteRequest(state, accepted_record, {}),
            services_for("explore_branch", "accept"))[0].route
        == "explore_branch",
    }, {
        "test": "conserve_phase_demotes_exploration_to_consolidation",
        "passed": route_adaptive_result(
            AdaptiveRouteRequest(state, accepted_record, {}),
            _phase_services(services_for("explore_branch", "accept"), 70, 100)
        )[0].route == "repair",
    }, {
        "test": "final_verify_phase_presents_existing_work_for_verification",
        "passed": route_adaptive_result(
            AdaptiveRouteRequest(state, accepted_record, {}),
            _phase_services(services_for("continue", "accept"), 92, 100)
        )[0].route == "reframe",
    }, {
        "test": "budget_phase_never_demotes_success_or_honest_stops",
        "passed": all(
            _budget_phase_route(_evidence_for(
                services_for("stop_success", "accept"), 92, 100),
                "stop_success", "verified")[0] == "stop_success"
            and _budget_phase_route(_evidence_for(
                services_for("stop_unprofitable", "repair"), 92, 100),
                "stop_unprofitable", "honest stop")[0] == "stop_unprofitable"
            for _ in (0,)),
        "detail": "the phase gate leaves stop routes to the guard and binding",
    }, {
        "test": "phase_demotion_is_recorded_as_a_diagnostic",
        "passed": _phase_demoted_diagnostics(services_for(
            "explore_branch", "accept"), 70, 100),
    }]
    captured = []
    capturing = services_for("continue", "accept")
    inner_model = capturing.model
    capturing.model = lambda request: (captured.append(request), inner_model(request))[1]
    route_adaptive_result(AdaptiveRouteRequest(state, accepted_record, {}), capturing)
    tests.append({
        "test": "the_route_step_names_its_registered_contract",
        "passed": bool(captured) and captured[0].contract_id == PRACTITIONER_ROUTE
        and captured[0].output_contract
        == registered_contract(PRACTITIONER_ROUTE).contract_json(),
        "detail": "the packet names practitioner.route and shows its registered JSON",
    })
    return {
        "record_type": "adaptive_practitioner_routing_test/v1",
        "tests": tests, "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests)}


__all__ = ("AdaptiveRouteRequest", "route_adaptive_result", "self_test")
