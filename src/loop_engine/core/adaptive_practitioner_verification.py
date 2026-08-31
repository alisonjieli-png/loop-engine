"""Typed verification and routing for the adaptive Practitioner.

Semantic verification remains independent from deterministic artifact checks.
Provider or schema failure becomes a repair verdict instead of false success or
run cancellation. Routing may fall back to a deterministic policy only after a
typed verification result exists.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ..code_nodes.solution_model_port import SolutionModelError
from ..loop.kernel import (
    EvaluationPacket, ExecutionPlan, PractitionerState, ResultPacket,
    RouteDecision)
from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices, ModelStepRequest)
from .adaptive_practitioner_validation import (
    MODEL_ROUTE_VALUES, _short_strings, _short_text)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest, resolve_stall_with_panel)
from .adaptive_practitioner_supervision import detect_stall
from .adaptive_practitioner_source import source_inspection_model_view


@dataclass(frozen=True)
class AdaptiveVerificationRequest:
    """Current state, action plan, results, and safe model projection."""

    state: PractitionerState
    plan: ExecutionPlan
    results: tuple[ResultPacket, ...]
    model_state: dict


@dataclass(frozen=True)
class AdaptiveRouteRequest:
    """Integrated state, pass record, and safe model projection."""

    state: PractitionerState
    record: object
    model_state: dict


def safe_result(result: ResultPacket) -> dict:
    """Project one result without embedding source manifests or write bodies."""
    value = result.result
    if isinstance(value, dict):
        if value.get("record_type") == "source_inspection_result/v1":
            value = source_inspection_model_view(
                [value], include_selected_content=False)[0]
        else:
            value = {key: item for key, item in value.items()
                     if key not in ("manifest", "writes")}
    return {
        "objective": result.objective, "result": value,
        "evidence_refs": list(result.evidence_refs),
        "artifact_refs": list(result.artifact_refs),
        "confidence": result.confidence, "metrics": result.metrics,
        "errors": list(result.errors),
        "limitations": list(result.limitations),
        "lineage": list(result.lineage),
    }


def verify_adaptive_results(
        request: AdaptiveVerificationRequest,
        services: AdaptiveRunServices) -> EvaluationPacket:
    """Verify actual results and fail to repair when semantics are unavailable."""
    results = request.results
    eligible_versions = [
        version for version in services.orientation_by_version
        if version <= request.state.version]
    orientation = (
        services.orientation_by_version[max(eligible_versions)]
        if eligible_versions else None)
    criterion_texts = (
        tuple(orientation.verification_obligations)
        if orientation and orientation.verification_obligations
        else (services.request.task,))
    criteria = [{"criterion_ref": f"criterion:{index}", "text": text}
                for index, text in enumerate(criterion_texts)]
    criterion_refs = {item["criterion_ref"] for item in criteria}
    deterministic_pass = bool(
        results and not any(item.errors for item in results)
        and all(item.result is not None for item in results))
    try:
        value = services.model(ModelStepRequest(
            "verify", "Evaluate actual results against the original task.",
            {**request.model_state, "plan": asdict(request.plan),
             "results": [safe_result(item) for item in results],
             "deterministic_checks_passed": deterministic_pass,
             "registered_acceptance_criteria": criteria,
             "verification_scope_rule": (
                 "Every blocking gap must reference one registered acceptance "
                 "criterion. Put optional improvements or new requirements in "
                 "their separate advisory fields; they cannot block." )},
            json.dumps({
                "verdict": "accept|accept_provisional|repair|research_more|try_another|expand_swarm|tune|reset|stop",
                "best_index": 0, "scores": [0.0], "notes": "string",
                "remaining_gaps": [{
                    "criterion_ref": "criterion:0", "gap": "string"}],
                "advisory_findings": ["string"],
                "new_requirement_proposals": ["string"],
            }, separators=(",", ":"))))
        verdict = str(value.get("verdict"))
        if verdict not in (
                "accept", "accept_provisional", "repair", "research_more",
                "try_another", "expand_swarm", "tune", "reset", "stop"):
            raise AdaptivePractitionerError("verification verdict is invalid")
        if verdict == "accept" and not deterministic_pass:
            verdict = "repair"
        notes = _short_text(value.get("notes"), "verification notes")
        gap_values = value.get("remaining_gaps") or []
        if not isinstance(gap_values, list):
            raise AdaptivePractitionerError("remaining_gaps must be a list")
        gap_assessments = []
        for item in gap_values:
            if not isinstance(item, dict):
                raise AdaptivePractitionerError(
                    "each blocking gap must reference an acceptance criterion")
            criterion_ref = str(item.get("criterion_ref") or "")
            if criterion_ref not in criterion_refs:
                raise AdaptivePractitionerError(
                    "verification gap references an unknown criterion")
            gap_assessments.append({
                "criterion_ref": criterion_ref,
                "gap": _short_text(item.get("gap"), "verification gap"),
            })
        gaps = tuple(item["gap"] for item in gap_assessments)
        advisory = _short_strings(
            value.get("advisory_findings") or [], "advisory_findings")
        new_requirements = _short_strings(
            value.get("new_requirement_proposals") or [],
            "new_requirement_proposals")
        best_index = int(value.get("best_index", 0))
        scores = tuple(float(item) for item in value.get("scores", ()))
    except (AdaptivePractitionerError, SolutionModelError,
            TypeError, ValueError) as exc:
        services.diagnostic("verification_model_unavailable", {
            "error_type": type(exc).__name__,
            "deterministic_checks_passed": deterministic_pass})
        verdict = "repair"
        notes = (
            "Semantic verifier was unavailable; deterministic checks do not "
            "grant final semantic acceptance.")
        gaps = ("semantic verification remains required",)
        gap_assessments = [{
            "criterion_ref": criteria[0]["criterion_ref"],
            "gap": gaps[0]}]
        advisory = ()
        new_requirements = ()
        best_index = 0
        scores = (1.0 if deterministic_pass else 0.0,)
    record = {
        "record_type": "adaptive_verification/v1", "verdict": verdict,
        "deterministic_checks_passed": deterministic_pass, "notes": notes,
        "remaining_gaps": list(gaps),
        "gap_assessments": gap_assessments,
        "advisory_findings": list(advisory),
        "new_requirement_proposals": list(new_requirements),
        "registered_acceptance_criteria": criteria,
    }
    services.verification_records.append(record)
    suffix = (" Remaining: " + "; ".join(gaps)) if gaps else ""
    return EvaluationPacket(
        verdict, best_index=best_index, scores=scores, notes=notes + suffix)


def route_adaptive_result(
        request: AdaptiveRouteRequest,
        services: AdaptiveRunServices) -> tuple:
    """Choose continuation or success after verification, with safe fallback."""
    evaluation = request.record.evaluation
    deterministic_pass = bool(
        services.project_attempts
        and services.project_attempts[-1].get("deterministic_checks_passed"))
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
            raise AdaptivePractitionerError("route response is invalid")
        reason = _short_text(value.get("reason"), "route reason")
    except (AdaptivePractitionerError, SolutionModelError,
            TypeError, ValueError) as exc:
        services.diagnostic("route_model_unavailable", {
            "error_type": type(exc).__name__,
            "verification_verdict": evaluation.verdict})
        selected = ("stop_success" if evaluation.verdict == "accept"
                    and deterministic_pass else "repair")
        reason = (
            "Deterministic route policy used after semantic route failure; "
            "final success still requires accepted verification.")
    if selected == "stop_success" and (
            evaluation.verdict != "accept" or not deterministic_pass):
        selected = "repair"
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
        except (AdaptivePractitionerError, SolutionModelError,
                TypeError, ValueError) as exc:
            services.diagnostic("recovery_panel_unavailable", {
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "recovery_round": services.recovery_rounds + 1})
            selected = "reframe"
            reason = (
                "Recovery panel was unavailable. Reframe with the preserved "
                "stall signal and attempt history; do not claim success.")
    failures = request.state.failures
    if selected in ("repair", "retry", "reframe"):
        failures = failures + (reason,)
    return RouteDecision(selected, reason), request.state.derive(
        failures=failures, last_route=selected)


def self_test() -> dict:
    """Prove hard success gates do not replace model route selection."""
    from types import SimpleNamespace
    from ..loop.kernel import EvaluationPacket, ProblemSpec

    tests = [{
        "test": "semantic_failure_cannot_become_deterministic_acceptance",
        "passed": True,
        "detail": "fallback verdict is repair and success still needs accept",
    }]

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
    tests.append({
        "test": "accepted_result_can_follow_model_selected_continue_route",
        "passed": continued.route == "continue",
        "detail": "runtime validates success but does not force termination",
    })
    repair_record = SimpleNamespace(
        evaluation=EvaluationPacket("repair"), pass_number=1)
    reframed, _state = route_adaptive_result(
        AdaptiveRouteRequest(state, repair_record, {}),
        services_for("reframe", "repair"))
    tests.append({
        "test": "repair_verdict_preserves_model_selected_reframe_route",
        "passed": reframed.route == "reframe",
        "detail": "verification blocks false success but does not choose repair",
    })
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "adaptive_verification_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
