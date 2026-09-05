"""Typed verification and routing for the adaptive Practitioner.

Semantic verification remains independent from deterministic artifact checks.
Provider or schema failure becomes a repair verdict instead of false success or
run cancellation. Routing may fall back to a deterministic policy only after a
typed verification result exists.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass

from ..code_nodes.solution_model_port import SolutionModelError
from ..loop.kernel import (
    EvaluationPacket,
    ExecutionPlan,
    PractitionerState,
    ResultPacket,
    RouteDecision,
)
from ..loop.kernel_runtime import current_kernel_owner
from .adaptive_practitioner_records import (
    AdaptivePractitionerError,
    AdaptiveRunServices,
    ModelStepRequest,
)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest,
    resolve_stall_with_panel,
)
from .adaptive_practitioner_source import source_inspection_model_view
from .adaptive_practitioner_supervision import detect_stall
from .adaptive_practitioner_validation import (
    MODEL_ROUTE_VALUES,
    _short_strings,
    _short_text,
)


@dataclass(frozen=True)
class AdaptiveVerificationRequest:
    """Current state, action plan, results, and safe model projection."""

    state: PractitionerState
    plan: ExecutionPlan
    results: tuple[ResultPacket, ...]
    model_state: dict


@dataclass(frozen=True)
class AdaptiveVerificationSubject:
    """Immutable identity of the complete input actually evaluated."""

    run_id: str
    action_id: str
    action_occurrence_ref: str
    plan_digest: str
    result_digests: tuple[str, ...]
    execution_refs: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "record_type": "adaptive_verification_subject/v1",
            "run_id": self.run_id, "action_id": self.action_id,
            "action_occurrence_ref": self.action_occurrence_ref,
            "plan_digest": self.plan_digest,
            "result_digests": list(self.result_digests),
            "execution_refs": list(self.execution_refs),
        }


@dataclass(frozen=True)
class AdaptiveEvaluationBindingRequest:
    """The actual plan, complete result set, and proposed integration verdict."""

    plan: ExecutionPlan
    results: tuple[ResultPacket, ...]
    evaluation: EvaluationPacket


def _verification_subject(services, plan_payload: dict,
                          result_payloads: tuple[dict, ...]
                          ) -> AdaptiveVerificationSubject:
    from .stage_action_lineage import _digest

    experiment = plan_payload.get("experiment", {})
    action_id = str(experiment.get("action_id") or "")
    occurrence = str(experiment.get("action_occurrence_ref") or "")
    plan_digest = _digest(plan_payload)
    result_digests = tuple(_digest(item) for item in result_payloads)
    execution_refs = []
    for result_digest in result_digests:
        matches = [item for item in getattr(
            services, "stage_execution_links", ())
            if item.get("action_occurrence_ref") == occurrence
            and item.get("action_id") == action_id
            and item.get("plan_digest") == plan_digest
            and item.get("result_digest") == result_digest]
        if len(matches) > 1:
            raise AdaptivePractitionerError("verification execution is ambiguous")
        if matches:
            execution_refs.append(matches[0]["execution_ref"])
    if len(execution_refs) != len(set(execution_refs)):
        raise AdaptivePractitionerError("verification repeats an execution member")
    return AdaptiveVerificationSubject(
        str(getattr(services, "run_id", "")), action_id, occurrence,
        plan_digest, result_digests, tuple(execution_refs))


def _append_verification_record(services, record: dict, owner_loop) -> None:
    """Retain the result and anchor its immutable digest in existing history."""
    from .stage_action_lineage import _digest

    services.verification_records.append(record)
    if owner_loop is None:
        return
    try:
        owner_loop.ledger.record(
            loop_id=owner_loop.loop_id, event="custom",
            custom_kind="adaptive_verification_recorded",
            record_type="adaptive_verification_recorded/v1",
            run_id=getattr(services, "run_id", ""),
            verifier_stage_occurrence_id=record["verifier_stage_occurrence_id"],
            evaluation_record_digest=_digest(record))
    except Exception as exc:  # noqa: BLE001
        try:
            services.diagnostic("verification_evidence_degraded", {
                "operation": "record_verification_subject",
                "error_type": type(exc).__name__})
        except Exception:  # noqa: BLE001
            pass


def _require_verification_record(services, record: dict, owner_loop) -> None:
    """Refuse historical, detached, altered, or unrecorded evaluation evidence."""
    from .stage_action_lineage import _digest

    if (not isinstance(record, dict)
            or record.get("record_type") != "adaptive_verification/v2"
            or not isinstance(record.get("subject"), dict)
            or not services.verification_records
            or services.verification_records[-1] is not record
            or owner_loop is None):
        raise ValueError("exact verification requires the current subject-bound record")
    occurrences = [item for item in services.stage_store.observations
                   if item.occurrence_id == record.get("verifier_stage_occurrence_id")]
    if len(occurrences) != 1:
        raise ValueError("verification needs one stored verifier occurrence")
    verifier = occurrences[0]
    if (verifier.run_id != services.run_id
            or verifier.owner_loop_id != owner_loop.loop_id
            or verifier.pass_number != record.get("pass_number")
            or verifier.pass_number != services.active_pass_number
            or verifier.semantic_call_id != record.get("verifier_semantic_call_id")
            or services.stage_arms.get(verifier.occurrence_id, {}).get(
                "cognitive_phase") != "verify"
            or (record.get("semantic_verification_observed") is True
                and verifier.outcome.output_admitted is not True)):
        raise ValueError("verification record has a different verifier identity")
    events = [item for item in owner_loop.ledger.events
              if item.get("event") == "custom"
              and item.get("custom_kind") == "adaptive_verification_recorded"
              and item.get("verifier_stage_occurrence_id") == verifier.occurrence_id]
    if (len(events) != 1 or events[0].get("loop_id") != owner_loop.loop_id
            or events[0].get("run_id") != services.run_id
            or events[0].get("evaluation_record_digest") != _digest(record)):
        raise ValueError("verification record differs from its canonical event")


def _validate_action_verification_record(request, execution: dict,
                                         selected: dict) -> None:
    from .stage_action_lineage import _digest

    record = request.evaluation_record
    _require_verification_record(request.services, record, request.owner_loop)
    expected = AdaptiveVerificationSubject(
        request.services.run_id, selected["action_id"],
        request.action_occurrence_ref, execution["plan_digest"],
        tuple(_digest(item) for item in request.result_payloads),
        (request.execution_ref,))
    if (record["subject"] != expected.to_dict()
            or selected["run_id"] != request.services.run_id
            or selected["owner_loop_id"] != request.owner_loop.loop_id
            or selected["pass_number"] > record["pass_number"]
            or record.get("verdict") != request.verdict
            or record.get("semantic_verification_observed")
            is not request.semantic_verification_observed
            or record.get("deterministic_checks_passed")
            is not request.deterministic_checks_passed):
        raise ValueError("verification evaluated a different action, plan, or result set")


def validate_adaptive_evaluation(
        request: AdaptiveEvaluationBindingRequest,
        services: AdaptiveRunServices, owner_loop=None) -> dict:
    """Validate evidence before integrating the exact evaluated result set."""
    from .stage_action_lineage import _result_payload

    if not isinstance(request, AdaptiveEvaluationBindingRequest):
        raise TypeError("evaluation validation needs its typed binding request")
    record = services.verification_records[-1] if services.verification_records else {}
    _require_verification_record(
        services, record, owner_loop or current_kernel_owner())
    subject = _verification_subject(
        services, asdict(request.plan),
        tuple(_result_payload(item) for item in request.results))
    if (record["subject"] != subject.to_dict()
            or record.get("evaluation") != asdict(request.evaluation)):
        raise ValueError("integration differs from the evaluated subject or verdict")
    return record


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


def selected_project_matches(record, final_attempt: dict) -> bool:
    """A terminal verdict must evaluate the project the product will return."""
    from .stage_action_lineage import _digest

    index = record.evaluation.best_index
    if (not isinstance(index, int) or isinstance(index, bool)
            or not 0 <= index < len(record.results)
            or not isinstance(final_attempt, dict)):
        return False
    selected = record.results[index]
    if selected.errors or not isinstance(selected.result, dict):
        return False
    return _digest(safe_result(selected)["result"]) == _digest(safe_result(
        ResultPacket("emitted project", result=final_attempt))["result"])


def _record_attribution_boundary(services, verdict: str) -> None:
    """Record why a pass verdict is not copied onto its model stages.

    Verification evaluates the action result selected for the pass. The pass
    can also contain orientation, planning, formatting, and routing calls that
    the verdict did not independently test. Until exact consumer links exist,
    their local contribution remains unknown.
    """
    pass_number = int(getattr(services, "active_pass_number", 0) or 0)
    observations = tuple(
        item for item in getattr(
            getattr(services, "stage_store", None), "observations", ())
        if int(getattr(item, "pass_number", 0) or 0) == pass_number)
    payload = {
        "record_type": "stage_attribution_boundary/v1",
        "pass_number": pass_number,
        "verification_verdict": verdict,
        "stage_occurrence_ids": [
            str(getattr(item, "occurrence_id", "")) for item in observations],
        "local_stage_outcomes_changed": False,
        "reason": (
            "the pass verdict evaluates selected action results, not every "
            "semantic model call in the pass"),
    }
    sink = getattr(services, "stage_attribution_events", None)
    if isinstance(sink, list):
        sink.append(payload)
    try:
        owner = current_kernel_owner()
        if owner is not None:
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom",
                custom_kind="stage_attribution_boundary", **payload)
    except Exception as exc:                            # noqa: BLE001
        diagnostic = getattr(services, "diagnostic", None)
        if callable(diagnostic):
            diagnostic("stage_evidence_degraded", {
                "operation": "record_attribution_boundary",
                "error_type": type(exc).__name__,
                "pass_number": pass_number})


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
    semantic_verification_observed = False
    subject = None
    try:
        from .stage_action_lineage import _result_payload

        plan_payload = asdict(request.plan)
        frozen_results = deepcopy(tuple(results))
        model_results = [safe_result(item) for item in frozen_results]
        subject = _verification_subject(
            services, plan_payload,
            tuple(_result_payload(item) for item in frozen_results))
        value = services.model(ModelStepRequest(
            "verify", "Evaluate actual results against the original task.",
            {**request.model_state, "plan": plan_payload,
             "results": model_results,
             "deterministic_checks_passed": deterministic_pass,
             "registered_acceptance_criteria": criteria,
             "verification_scope_rule": (
                 "Every blocking gap must reference one registered acceptance "
                 "criterion. Put optional improvements or new requirements in "
                 "their separate advisory fields; they cannot block." )},
            json.dumps({
                "verdict": (
                    "accept|accept_provisional|repair|research_more|"
                    "try_another|expand_swarm|tune|reset|stop"),
                "best_index": 0, "scores": [0.0], "notes": "string",
                "remaining_gaps": [{
                    "criterion_ref": "criterion:0", "gap": "string"}],
                "advisory_findings": ["string"],
                "new_requirement_proposals": ["string"],
            }, separators=(",", ":"))))
        verdict = str(value.get("verdict"))
        admitted_verdicts = (
            "accept", "accept_provisional", "repair", "research_more",
            "try_another", "expand_swarm", "tune", "reset", "stop")
        if verdict not in admitted_verdicts:
            # Name the value and the set. A closed vocabulary refused without
            # stating itself leaves the next attempt to guess again.
            raise AdaptivePractitionerError(
                f"verification verdict {verdict!r} is not admitted; the "
                f"admitted verdicts are {list(admitted_verdicts)}")
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
                    f"verification gap references criterion "
                    f"{criterion_ref!r}, which is not registered; the "
                    f"registered criteria are {list(criterion_refs)[:24]}")
            gap_assessments.append({
                "criterion_ref": criterion_ref,
                "gap": _short_text(item.get("gap"), "verification gap"),
            })
        gaps = tuple(item["gap"] for item in gap_assessments)
        if verdict == "accept" and gaps:
            raise AdaptivePractitionerError(
                "verification cannot accept with unresolved registered criteria")
        advisory = _short_strings(
            value.get("advisory_findings") or [], "advisory_findings")
        new_requirements = _short_strings(
            value.get("new_requirement_proposals") or [],
            "new_requirement_proposals")
        best_index = value.get("best_index", 0)
        if (not isinstance(best_index, int) or isinstance(best_index, bool)
                or best_index < 0 or best_index >= max(1, len(results))):
            raise AdaptivePractitionerError(
                f"verification best_index {best_index!r} must be an integer "
                f"from zero through {max(0, len(results) - 1)}")
        scores = tuple(float(item) for item in value.get("scores", ()))
        if subject != _verification_subject(
                services, asdict(request.plan),
                tuple(_result_payload(item) for item in results)):
            raise AdaptivePractitionerError("verification inputs changed during evaluation")
        semantic_verification_observed = True
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
    verifier_stage = getattr(services, "_graded_stage", None)
    suffix = (" Remaining: " + "; ".join(gaps)) if gaps else ""
    evaluation = EvaluationPacket(
        verdict, best_index=best_index, scores=scores, notes=notes + suffix)
    record = {
        "record_type": "adaptive_verification/v2", "verdict": verdict,
        "subject": subject.to_dict() if subject is not None else None,
        "evaluation": asdict(evaluation),
        "pass_number": int(getattr(services, "active_pass_number", 0) or 0),
        "verifier_stage_occurrence_id": str(
            getattr(verifier_stage, "occurrence_id", "") or ""),
        "verifier_semantic_call_id": str(
            getattr(verifier_stage, "semantic_call_id", "") or ""),
        "semantic_verification_observed": semantic_verification_observed,
        "deterministic_checks_passed": deterministic_pass, "notes": notes,
        "remaining_gaps": list(gaps),
        "gap_assessments": gap_assessments,
        "advisory_findings": list(advisory),
        "new_requirement_proposals": list(new_requirements),
        "registered_acceptance_criteria": criteria,
    }
    _append_verification_record(services, record, current_kernel_owner())
    _record_attribution_boundary(services, verdict)
    return evaluation


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
            raise AdaptivePractitionerError(
                f"route {selected!r} is not admitted; the admitted routes "
                f"are {list(MODEL_ROUTE_VALUES)}")
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
    if selected == "stop_success":
        try:
            validate_adaptive_evaluation(AdaptiveEvaluationBindingRequest(
                request.record.plan, tuple(request.record.results), evaluation),
                services)
            if not selected_project_matches(
                    request.record, services.project_attempts[-1]):
                raise ValueError("verified result is not the emitted project")
        except (AttributeError, TypeError, ValueError) as exc:
            selected = "repair"
            reason = "Final success requires exact recorded verification of this result."
            services.diagnostic("verification_binding_invalid", {
                "error_type": type(exc).__name__, "reason": str(exc)[:300]})
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
    from .stage_fingerprint import SemanticStageFingerprint
    from .stage_store import StageStore

    diagnostics = []

    def unavailable_model(_request):
        raise SolutionModelError(
            "offline semantic verifier unavailable",
            error_code="provider_unavailable")

    fallback_services = SimpleNamespace(
        orientation_by_version={},
        request=SimpleNamespace(task="verify the requested artifact"),
        model=unavailable_model,
        diagnostic=lambda code, payload: diagnostics.append((code, payload)),
        verification_records=[], active_pass_number=1,
        stage_store=StageStore(), stage_attribution_events=[])
    fallback = verify_adaptive_results(
        AdaptiveVerificationRequest(
            PractitionerState(ProblemSpec("verify the requested artifact")),
            ExecutionPlan("generate", "run_dag"),
            (ResultPacket("fixture", result={"ok": True}),), {}),
        fallback_services)
    tests = [{
        "test": "semantic_failure_cannot_become_deterministic_acceptance",
        "passed": (
            fallback.verdict == "repair"
            and fallback_services.verification_records[-1]["verdict"]
                == "repair"
            and diagnostics[0][0] == "verification_model_unavailable"),
        "detail": "fallback verdict is repair and success still needs accept",
    }]

    stage_store = StageStore()
    for responsibility in ("orient the task", "select one action"):
        stage_store.add(SemanticStageFingerprint(
            semantic_responsibility=responsibility,
            cognitive_phase="verification"), run_id="scope-proof",
            pass_number=1)
    scope_services = SimpleNamespace(
        active_pass_number=1, stage_store=stage_store,
        stage_attribution_events=[], diagnostic=lambda *_args, **_kw: None)
    _record_attribution_boundary(scope_services, "accept")
    tests.append({
        "test": "one_pass_verdict_does_not_label_every_stage",
        "passed": (
            all(item.outcome.local_verification is None
                and item.helped is None for item in stage_store.observations)
            and len(scope_services.stage_attribution_events) == 1
            and scope_services.stage_attribution_events[0][
                "local_stage_outcomes_changed"] is False),
        "detail": "local contribution stays unknown without an exact join",
    })

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
