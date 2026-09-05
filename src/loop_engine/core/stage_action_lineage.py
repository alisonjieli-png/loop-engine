"""Exact lineage from one semantic decision stage through verified action.

These helpers append immutable Run History facts and update only the stage that
produced the selected action. They do not infer credit for other stages, select
an action, execute a capability, verify a result, or grant authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .outcome_vector import observe as observe_outcome
from .stage_store import StageObservation


def _digest(value: object) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _event(services, owner_loop, kind: str, payload: dict) -> None:
    owner_loop.ledger.record(
        loop_id=owner_loop.loop_id,
        event="custom",
        custom_kind=kind,
        **payload,
    )


def _degraded(request: object, operation: str, exc: Exception) -> None:
    record = {
        "record_type": "stage_action_lineage_degraded/v1",
        "operation": operation,
        "error_type": type(exc).__name__,
        "error": str(exc)[:300],
    }
    sink = getattr(request.services, "stage_evidence_degradations", None)
    if isinstance(sink, list):
        sink.append(record)
    try:
        request.services.diagnostic("stage_action_lineage_degraded", record)
    except Exception:  # noqa: BLE001
        return


def _stored_stage(services, observation: StageObservation, owner_loop,
                  *, cognitive_phase: str) -> StageObservation:
    """Resolve and validate one exact current-run stage occurrence."""
    if not isinstance(observation, StageObservation):
        raise ValueError("stage lineage needs one StageObservation")
    matches = tuple(
        item for item in services.stage_store.observations
        if item.occurrence_id == observation.occurrence_id)
    if len(matches) != 1:
        raise ValueError("stage lineage needs one stored occurrence")
    current = matches[0]
    identity = (
        "run_id", "occurrence_id", "semantic_call_id", "owner_loop_id",
        "pass_number", "digest", "responsibility",
    )
    if any(getattr(current, name) != getattr(observation, name)
           for name in identity):
        raise ValueError("supplied stage identity differs from the stored row")
    active_pass = int(getattr(services, "active_pass_number", 0) or 0)
    if (not current.semantic_call_id
            or current.run_id != services.run_id
            or current.owner_loop_id != owner_loop.loop_id
            or current.pass_number != active_pass):
        raise ValueError("stage is outside the active run, owner, or pass")
    facts = services.stage_arms.get(current.occurrence_id)
    if not isinstance(facts, dict) or facts.get(
            "cognitive_phase") != cognitive_phase:
        raise ValueError(
            f"stage is not the active {cognitive_phase} responsibility")
    graded = getattr(services, "_graded_stage", None)
    if getattr(graded, "occurrence_id", "") != current.occurrence_id:
        raise ValueError("stage is not the current graded occurrence")
    return current


def _action_occurrence_ref(services, stage: StageObservation,
                           action_id: str, payload_digest: str) -> str:
    return "action-occurrence:sha256:" + _digest({
        "run_id": services.run_id,
        "pass_number": stage.pass_number,
        "stage_occurrence_id": stage.occurrence_id,
        "semantic_call_id": stage.semantic_call_id,
        "action_id": action_id,
        "action_payload_digest": payload_digest,
    })


def _selected_link(services, action_occurrence_ref: str) -> dict:
    links = tuple(
        item for item in services.stage_action_links
        if item.get("action_occurrence_ref") == action_occurrence_ref)
    if len(links) != 1:
        raise ValueError("action needs one exact selected-action occurrence")
    return links[0]


def _execution_link(services, execution_ref: str) -> dict:
    links = tuple(
        item for item in services.stage_execution_links
        if item.get("execution_ref") == execution_ref)
    if len(links) != 1:
        raise ValueError("verification needs one exact execution occurrence")
    return links[0]


def _result_payload(result: object) -> dict:
    return {
        "objective": getattr(result, "objective", ""),
        "result": getattr(result, "result", None),
        "claims": list(getattr(result, "claims", ())),
        "evidence_refs": list(getattr(result, "evidence_refs", ())),
        "artifact_refs": list(getattr(result, "artifact_refs", ())),
        "confidence": getattr(result, "confidence", None),
        "assumptions": list(getattr(result, "assumptions", ())),
        "metrics": getattr(result, "metrics", None),
        "cost": getattr(result, "cost", None),
        "errors": list(getattr(result, "errors", ())),
        "limitations": list(getattr(result, "limitations", ())),
        "suggested_next": list(getattr(result, "suggested_next", ())),
        "lineage": list(getattr(result, "lineage", ())),
    }


@dataclass(frozen=True)
class SelectedActionLineageRequest:
    services: object
    owner_loop: object
    stage_observation: StageObservation
    action_id: str
    action_payload: dict


def record_selected_action(request: SelectedActionLineageRequest) -> dict:
    """Bind a selected action to the exact semantic stage that proposed it."""
    if not isinstance(request, SelectedActionLineageRequest):
        raise ValueError("selected action lineage needs its typed request")
    observation = request.stage_observation
    if not request.action_id or not isinstance(request.action_payload, dict):
        raise ValueError("selected action lineage identity is incomplete")
    observation = _stored_stage(
        request.services, observation, request.owner_loop,
        cognitive_phase="decide_next")
    payload_digest = _digest(request.action_payload)
    if request.action_id != "action:" + payload_digest[:20]:
        raise ValueError("action ID does not match its admitted payload")
    admitted = request.services.action_details.get(request.action_id)
    if admitted is None or getattr(admitted, "to_dict", lambda: None)() \
            != request.action_payload:
        raise ValueError("action payload differs from the admitted decision")
    stage_facts = request.services.stage_arms.get(observation.occurrence_id, {})
    decisions = tuple(
        item for item in request.services.stage_assistance_decisions
        if item.get("stage_occurrence_id") == observation.occurrence_id
    )
    mode = request.services.request.stage_assistance.mode
    if mode in ("advisory", "fresh") and len(decisions) != 1:
        raise ValueError(
            "an active experiment needs one assistance decision for the stage")
    if mode in ("advisory", "fresh"):
        decision = decisions[0]
        exposure = stage_facts.get("active_exposure")
        if (not isinstance(exposure, dict)
                or decision.get("assigned_arm") != mode
                or decision.get("experiment_ref")
                != stage_facts.get("experiment_ref")
                or decision.get("trial_ref") != stage_facts.get("trial_ref")
                or decision.get("exposure_ref") != exposure.get("exposure_ref")
                or decision.get("packet_digest") != exposure.get("packet_digest")
                or decision.get("prompt_digest") != exposure.get("prompt_digest")
                or decision.get("gateway_request_digest")
                != exposure.get("gateway_request_digest")
                or decision.get("control_manifest_ref")
                != stage_facts.get("control_manifest_ref")
                or decision.get("control_manifest_digest")
                != stage_facts.get("control_manifest_digest")):
            raise ValueError(
                "assistance decision differs from its exact stage exposure")
    action_occurrence_ref = _action_occurrence_ref(
        request.services, observation, request.action_id, payload_digest)
    if any(item.get("action_occurrence_ref") == action_occurrence_ref
           or item.get("stage_occurrence_id") == observation.occurrence_id
           for item in request.services.stage_action_links):
        raise ValueError("selected action occurrence is already recorded")
    record = {
        "record_type": "stage_selected_action_lineage/v1",
        "stage_occurrence_id": observation.occurrence_id,
        "semantic_call_id": observation.semantic_call_id,
        "run_id": observation.run_id,
        "owner_loop_id": observation.owner_loop_id,
        "pass_number": observation.pass_number,
        "action_id": request.action_id,
        "action_occurrence_ref": action_occurrence_ref,
        "action_payload_digest": payload_digest,
        "experiment_ref": stage_facts.get("experiment_ref", ""),
        "trial_ref": stage_facts.get("trial_ref", ""),
        "control_manifest_ref": stage_facts.get("control_manifest_ref", ""),
        "control_manifest_digest": stage_facts.get(
            "control_manifest_digest", ""),
        "assistance_decision_digest": _digest(decisions[-1]) if decisions else "",
        "attribution_method": "EXACT_SELECTED_ACTION_IDENTITY",
    }
    _event(request.services, request.owner_loop, "stage_selected_action_linked", record)
    request.services.stage_action_links.append(record)
    return record


def try_record_selected_action(request: SelectedActionLineageRequest) -> dict | None:
    try:
        return record_selected_action(request)
    except Exception as exc:  # noqa: BLE001
        _degraded(request, "link_selected_action", exc)
        return None


def _try_selected(services, stage, action_id: str, payload: dict) -> dict | None:
    from ..loop.kernel_runtime import current_kernel_owner

    return try_record_selected_action(SelectedActionLineageRequest(
        services, current_kernel_owner(), stage, action_id, payload))


def source_stage_fields(stage: object) -> dict[str, str]:
    return {
        "source_stage_occurrence_id": str(getattr(stage, "occurrence_id", "")),
        "source_semantic_call_id": str(getattr(stage, "semantic_call_id", "")),
    }


@dataclass(frozen=True)
class ActionExecutionLineageRequest:
    services: object
    owner_loop: object
    action_occurrence_ref: str
    action_id: str
    capability_ref: str
    plan_payload: dict
    result: object


def record_action_execution(request: ActionExecutionLineageRequest) -> dict:
    """Record the observed result of the exact selected action."""
    if not isinstance(request, ActionExecutionLineageRequest):
        raise ValueError("action execution lineage needs its typed request")
    if (not request.action_occurrence_ref or not request.action_id
            or not request.capability_ref or not isinstance(
                request.plan_payload, dict)):
        raise ValueError("action execution lineage identity is incomplete")
    selected = _selected_link(
        request.services, request.action_occurrence_ref)
    if (selected["action_id"] != request.action_id
            or selected["run_id"] != request.services.run_id
            or selected["owner_loop_id"] != request.owner_loop.loop_id
            or selected["pass_number"] != int(getattr(
                request.services, "active_pass_number", 0) or 0)):
        raise ValueError("execution differs from its selected action identity")
    if request.plan_payload.get("handle") != request.capability_ref:
        raise ValueError("execution capability differs from its plan")
    experiment = request.plan_payload.get("experiment")
    if (not isinstance(experiment, dict)
            or experiment.get("action_id") != request.action_id
            or experiment.get("action_occurrence_ref")
            != request.action_occurrence_ref):
        raise ValueError("execution plan is not bound to the selected action")
    plan_details = request.services.plan_details.get(request.action_id)
    if (not isinstance(plan_details, dict)
            or plan_details.get("capability_ref") != request.capability_ref
            or plan_details.get("arguments", {})
            != experiment.get("arguments", {})):
        raise ValueError("execution plan differs from the admitted method")
    if any(item.get("action_occurrence_ref") == request.action_occurrence_ref
           for item in request.services.stage_execution_links):
        raise ValueError("action execution occurrence is already recorded")
    result_payload = _result_payload(request.result)
    result_digest = _digest(result_payload)
    plan_digest = _digest(request.plan_payload)
    execution_ref = "action-execution:sha256:" + _digest({
        "action_occurrence_ref": request.action_occurrence_ref,
        "plan_digest": plan_digest,
        "result_digest": result_digest,
    })
    record = {
        "record_type": "stage_action_execution_lineage/v1",
        "stage_occurrence_id": selected["stage_occurrence_id"],
        "action_occurrence_ref": request.action_occurrence_ref,
        "execution_ref": execution_ref,
        "action_id": request.action_id,
        "capability_ref": request.capability_ref,
        "plan_digest": plan_digest,
        "result_digest": result_digest,
        "execution_succeeded": (
            result_payload["result"] is not None
            and not bool(result_payload["errors"])),
        "downstream_use": True,
        "attribution_method": "DIRECT_DOWNSTREAM_CONSUMPTION",
    }
    _event(
        request.services,
        request.owner_loop,
        "stage_action_execution_linked",
        record,
    )
    source = next(item for item in request.services.stage_store.observations
                  if item.occurrence_id == selected["stage_occurrence_id"])
    request.services.stage_store.observe(source, downstream_use=True)
    request.services.stage_execution_links.append(record)
    return record


def try_record_action_execution(request: ActionExecutionLineageRequest) -> dict | None:
    try:
        return record_action_execution(request)
    except Exception as exc:  # noqa: BLE001
        _degraded(request, "link_action_execution", exc)
        return None


def _try_execution(services, owner_loop, plan, result) -> None:
    from dataclasses import asdict

    try_record_action_execution(ActionExecutionLineageRequest(
        services, owner_loop,
        str(plan.experiment.get("action_occurrence_ref") or ""),
        str(plan.experiment.get("action_id") or ""), plan.handle,
        asdict(plan), result))


@dataclass(frozen=True)
class ActionVerificationLineageRequest:
    services: object
    owner_loop: object
    action_occurrence_ref: str
    execution_ref: str
    verifier_stage_occurrence_id: str
    result_payloads: tuple[dict, ...]
    evaluation_record: dict
    verdict: str
    deterministic_checks_passed: bool
    semantic_verification_observed: bool


def record_action_verification(
    request: ActionVerificationLineageRequest,
) -> dict:
    """Apply exact downstream verification only to the action-producing stage."""
    if not isinstance(request, ActionVerificationLineageRequest):
        raise ValueError("action verification lineage needs its typed request")
    if not isinstance(request.deterministic_checks_passed, bool) \
            or not isinstance(request.semantic_verification_observed, bool):
        raise TypeError("verification observation flags must be booleans")
    execution = _execution_link(request.services, request.execution_ref)
    if execution["action_occurrence_ref"] != request.action_occurrence_ref:
        raise ValueError("verification and execution occurrences differ")
    selected = _selected_link(request.services, request.action_occurrence_ref)
    if execution["stage_occurrence_id"] != selected["stage_occurrence_id"]:
        raise ValueError("execution and selected stage occurrences differ")
    source = next((item for item in request.services.stage_store.observations
                   if item.occurrence_id == selected["stage_occurrence_id"]), None)
    if source is None:
        raise ValueError("action verification source stage is unavailable")
    verifier = next((item for item in request.services.stage_store.observations
                     if item.occurrence_id
                     == request.verifier_stage_occurrence_id), None)
    if verifier is None or verifier.occurrence_id == source.occurrence_id:
        raise ValueError("verification needs a distinct stored verifier stage")
    verifier = _stored_stage(
        request.services, verifier, request.owner_loop,
        cognitive_phase="verify")
    if request.semantic_verification_observed \
            and verifier.outcome.output_admitted is not True:
        raise ValueError("observed semantic verification was not admitted")
    from .adaptive_practitioner_verification import _validate_action_verification_record

    _validate_action_verification_record(request, execution, selected)
    if (not request.result_payloads
            or len(request.result_payloads) != 1
            or _digest(request.result_payloads[0]) != execution["result_digest"]):
        raise ValueError("verified result differs from the executed result")
    if any(item.get("execution_ref") == request.execution_ref
           for item in request.services.stage_outcome_links):
        raise ValueError("action verification occurrence is already recorded")
    local_verification = None
    if (not execution["execution_succeeded"]
            or not request.deterministic_checks_passed):
        local_verification = False
    elif request.semantic_verification_observed:
        if request.verdict == "accept":
            local_verification = True
        elif request.verdict == "repair":
            local_verification = False
    predicted = observe_outcome(
        source.outcome, **({"local_verification": local_verification}
                           if local_verification is not None else {}))
    evaluation_digest = _digest(request.evaluation_record)
    verification_ref = "action-verification:sha256:" + _digest({
        "execution_ref": request.execution_ref,
        "verifier_stage_occurrence_id": verifier.occurrence_id,
        "evaluation_record_digest": evaluation_digest,
    })
    record = {
        "record_type": "stage_action_verification_lineage/v1",
        "stage_occurrence_id": source.occurrence_id,
        "stage_observation_ref": source.observation_ref,
        "action_occurrence_ref": request.action_occurrence_ref,
        "execution_ref": request.execution_ref,
        "verification_ref": verification_ref,
        "action_id": selected["action_id"],
        "execution_result_digest": execution["result_digest"],
        "verifier_stage_occurrence_id": verifier.occurrence_id,
        "verifier_semantic_call_id": verifier.semantic_call_id,
        "verification_verdict": request.verdict,
        "deterministic_checks_passed": request.deterministic_checks_passed,
        "semantic_verification_observed": (
            request.semantic_verification_observed),
        "evaluation_record_digest": evaluation_digest,
        "local_verification": local_verification,
        "outcome_after_verification": predicted.to_dict(),
        "attribution_method": (
            "DIRECT_LOCAL_VERIFIER"
            if local_verification is not None else "UNKNOWN"),
        "attribution_confidence": None,
        "verifier_independence": "same_practitioner_model_path",
    }
    _event(request.services, request.owner_loop, "stage_action_outcome_linked", record)
    if local_verification is not None:
        request.services.stage_store.observe(
            source, local_verification=local_verification)
    request.services.stage_outcome_links.append(record)
    return record


def try_record_action_verification(
    request: ActionVerificationLineageRequest,
) -> dict | None:
    try:
        return record_action_verification(request)
    except Exception as exc:  # noqa: BLE001
        _degraded(request, "link_action_verification", exc)
        return None


def _try_verification(services, plan, results, evaluation) -> None:
    from ..loop.kernel_runtime import current_kernel_owner

    deterministic_pass = bool(
        results and not any(item.errors for item in results)
        and all(item.result is not None for item in results))
    verification_record = (
        services.verification_records[-1]
        if services.verification_records else {})
    action_occurrence_ref = str(
        plan.experiment.get("action_occurrence_ref") or "")
    executions = tuple(
        item for item in services.stage_execution_links
        if item.get("action_occurrence_ref") == action_occurrence_ref)
    try_record_action_verification(ActionVerificationLineageRequest(
        services, current_kernel_owner(),
        action_occurrence_ref,
        str(executions[-1].get("execution_ref") if len(executions) == 1 else ""),
        str(getattr(services._graded_stage, "occurrence_id", "")),
        tuple(_result_payload(item) for item in results),
        verification_record, evaluation.verdict, deterministic_pass,
        bool(verification_record.get("semantic_verification_observed"))))


def stage_lineage_summary(services: object) -> dict:
    """Project passive stage and action-lineage records for a product result."""
    return {
        "stages": services.stage_store.to_dict(),
        "stage_arms": dict(services.stage_arms),
        "stage_assistance_decisions": list(services.stage_assistance_decisions),
        "stage_action_links": list(services.stage_action_links),
        "stage_execution_links": list(services.stage_execution_links),
        "stage_outcome_links": list(services.stage_outcome_links),
        "stage_attribution_events": list(services.stage_attribution_events),
        "stage_evidence_degradations": list(services.stage_evidence_degradations),
    }


def self_test() -> dict[str, object]:
    """Exercise exact occurrence joins and adversarial refusal offline."""
    from dataclasses import replace
    from types import SimpleNamespace
    from ..loop.kernel import ResultPacket
    from .adaptive_practitioner_verification import (
        AdaptiveVerificationSubject, _append_verification_record)
    from .stage_fingerprint import SemanticStageFingerprint
    from .stage_store import StageStore
    def fixture(*, mode="advisory", event_failure=False):
        store, events, diagnostics = StageStore(), [], []
        def record(**value):
            if event_failure:
                raise RuntimeError("event sink unavailable")
            events.append(value)
        owner = SimpleNamespace(
            loop_id="loop.owner",
            ledger=SimpleNamespace(record=record, events=events))
        source = store.add(SemanticStageFingerprint(
            semantic_responsibility="select one action",
            cognitive_phase="decide_next"),
            run_id="lineage-fixture", occurrence_id="occurrence.decision",
            semantic_call_id="semantic-call.decision",
            owner_loop_id=owner.loop_id, pass_number=1,
            output_admitted=True)
        unrelated = store.add(SemanticStageFingerprint(
            semantic_responsibility="orient task", cognitive_phase="orient"),
            run_id="lineage-fixture", occurrence_id="occurrence.orientation",
            semantic_call_id="semantic-call.orientation",
            owner_loop_id=owner.loop_id, pass_number=1,
            output_admitted=True)
        exposure = {
            "exposure_ref": "exposure.fixture",
            "packet_digest": "a" * 64,
            "prompt_digest": "b" * 64,
            "gateway_request_digest": "c" * 64,
        }
        facts = {
            "cognitive_phase": "decide_next",
            "experiment_ref": "experiment.fixture",
            "trial_ref": "trial.fixture",
            "active_exposure": exposure,
        }
        decision = {
            "stage_occurrence_id": source.occurrence_id,
            "assigned_arm": mode,
            "experiment_ref": facts["experiment_ref"],
            "trial_ref": facts["trial_ref"],
            **exposure,
            "disposition": "USE",
        }
        payload = {"action_kind": "BUILD", "goal": "build"}
        action_id = "action:" + _digest(payload)[:20]
        admitted = SimpleNamespace(to_dict=lambda: dict(payload))
        services = SimpleNamespace(
            run_id="lineage-fixture", active_pass_number=1,
            request=SimpleNamespace(
                stage_assistance=SimpleNamespace(mode=mode)),
            stage_store=store, _graded_stage=source,
            stage_arms={source.occurrence_id: facts,
                        unrelated.occurrence_id: {
                            "cognitive_phase": "orient"}},
            stage_assistance_decisions=([] if mode == "shadow" else [decision]),
            action_details={action_id: admitted},
            plan_details={action_id: {
                "capability_ref": "core.generated_project",
                "arguments": {"path": "out"}}},
            verification_records=[], stage_action_links=[],
            stage_execution_links=[], stage_outcome_links=[],
            stage_attribution_events=[], stage_evidence_degradations=[],
            diagnostic=lambda code, detail: diagnostics.append((code, detail)))
        return (services, owner, source, unrelated, payload, action_id,
                events, diagnostics)
    def select(parts):
        services, owner, source, _, payload, action_id, _, _ = parts
        return record_selected_action(SelectedActionLineageRequest(
            services, owner, source, action_id, payload))
    def execute(parts, selected, *, result=None):
        services, owner, _, _, _, action_id, _, _ = parts
        result = result or ResultPacket(
            "build", result={"ok": True}, artifact_refs=("out",))
        plan = {
            "how_mode": "use", "act_mode": "run_direct",
            "handle": "core.generated_project", "steps": [],
            "resources": [], "spawned_loops": [],
            "experiment": {
                "action_id": action_id,
                "action_occurrence_ref": selected["action_occurrence_ref"],
                "arguments": {"path": "out"}},
            "rationale": "fixture",
        }
        return record_action_execution(ActionExecutionLineageRequest(
            services, owner, selected["action_occurrence_ref"], action_id,
            "core.generated_project", plan, result)), result, plan
    def verify(parts, selected, executed, result, *, verdict="accept",
               observed=True, deterministic=True):
        services, owner, _, _, _, _, _, _ = parts
        verifier = services.stage_store.add(SemanticStageFingerprint(
            semantic_responsibility="verify result", cognitive_phase="verify"),
            run_id=services.run_id, occurrence_id="occurrence.verifier",
            semantic_call_id="semantic-call.verifier",
            owner_loop_id=owner.loop_id, pass_number=services.active_pass_number,
            output_admitted=observed)
        services.stage_arms[verifier.occurrence_id] = {
            "cognitive_phase": "verify"}
        services._graded_stage = verifier
        evaluation = {
            "record_type": "adaptive_verification/v2", "verdict": verdict,
            "subject": AdaptiveVerificationSubject(
                services.run_id, selected["action_id"],
                selected["action_occurrence_ref"], executed["plan_digest"],
                (executed["result_digest"],), (executed["execution_ref"],)).to_dict(),
            "pass_number": services.active_pass_number,
            "verifier_stage_occurrence_id": verifier.occurrence_id,
            "verifier_semantic_call_id": verifier.semantic_call_id,
            "semantic_verification_observed": observed,
            "deterministic_checks_passed": deterministic,
        }
        _append_verification_record(services, evaluation, owner)
        return record_action_verification(ActionVerificationLineageRequest(
            services, owner, selected["action_occurrence_ref"],
            executed["execution_ref"], verifier.occurrence_id,
            (_result_payload(result),), evaluation, verdict, deterministic,
            observed))

    def refuses(callable_):
        try:
            callable_()
        except (TypeError, ValueError):
            return True
        return False

    happy = fixture()
    selected = select(happy)
    executed, result, _ = execute(happy, selected)
    verified = verify(happy, selected, executed, result)
    services, _, source, unrelated, payload, action_id, events, _ = happy
    updated = next(item for item in services.stage_store.observations
                   if item.occurrence_id == source.occurrence_id)
    untouched = next(item for item in services.stage_store.observations
                     if item.occurrence_id == unrelated.occurrence_id)
    tests = [{
        "test": "exact_occurrence_refs_join_selection_execution_verification",
        "passed": bool(selected["action_occurrence_ref"]
                       and executed["execution_ref"]
                       and verified["verification_ref"])
        and verified["execution_ref"] == executed["execution_ref"],
    }, {
        "test": "only_action_source_gets_direct_local_credit",
        "passed": updated.outcome.downstream_use is True
        and updated.outcome.local_verification is True
        and untouched.outcome.local_verification is None,
    }, {
        "test": "attribution_scope_and_unknown_confidence_are_explicit",
        "passed": verified["attribution_method"] == "DIRECT_LOCAL_VERIFIER"
        and verified["attribution_confidence"] is None
        and executed["attribution_method"] == "DIRECT_DOWNSTREAM_CONSUMPTION",
    }, {
        "test": "events_follow_selection_execution_verification_order",
        "passed": [item["custom_kind"] for item in events[-4:]] == [
            "stage_selected_action_linked", "stage_action_execution_linked",
            "adaptive_verification_recorded",
            "stage_action_outcome_linked"],
    }]

    forged = fixture()
    forged_stage = replace(forged[2], semantic_call_id="forged")
    forged[0]._graded_stage = forged_stage
    tests.append({
        "test": "forged_semantic_call_is_refused",
        "passed": refuses(lambda: record_selected_action(
            SelectedActionLineageRequest(
                forged[0], forged[1], forged_stage, forged[5], forged[4]))),
    })
    wrong_phase = fixture(mode="shadow")
    wrong_phase[0]._graded_stage = wrong_phase[3]
    tests.append({
        "test": "non_decision_stage_is_refused",
        "passed": refuses(lambda: record_selected_action(
            SelectedActionLineageRequest(
                wrong_phase[0], wrong_phase[1], wrong_phase[3],
                wrong_phase[5], wrong_phase[4]))),
    })
    missing_decision = fixture()
    missing_decision[0].stage_assistance_decisions.clear()
    tests.append({
        "test": "active_arm_without_exact_assistance_decision_is_refused",
        "passed": refuses(lambda: select(missing_decision)),
    })
    wrong_exposure = fixture()
    wrong_exposure[0].stage_assistance_decisions[0]["packet_digest"] = "d" * 64
    tests.append({
        "test": "assistance_decision_with_wrong_exposure_is_refused",
        "passed": refuses(lambda: select(wrong_exposure)),
    })
    wrong_payload = fixture(mode="shadow")
    tests.append({
        "test": "action_payload_mismatch_is_refused",
        "passed": refuses(lambda: record_selected_action(
            SelectedActionLineageRequest(
                wrong_payload[0], wrong_payload[1], wrong_payload[2],
                wrong_payload[5], {**wrong_payload[4], "goal": "other"}))),
    })
    duplicate = fixture(mode="shadow")
    duplicate_selected = select(duplicate)
    tests.append({
        "test": "duplicate_selection_is_refused",
        "passed": refuses(lambda: select(duplicate)),
    })
    tests.append({
        "test": "duplicate_execution_is_refused",
        "passed": (execute(duplicate, duplicate_selected) is not None
                   and refuses(lambda: execute(duplicate, duplicate_selected))),
    })
    null_run = fixture(mode="shadow")
    null_selected = select(null_run)
    null_execution, _, _ = execute(
        null_run, null_selected,
        result=ResultPacket("build", result=None, errors=()))
    tests.append({
        "test": "null_result_is_not_successful_execution",
        "passed": null_execution["execution_succeeded"] is False,
    })
    changed = fixture(mode="shadow")
    changed_selected = select(changed)
    changed_execution, changed_result, _ = execute(changed, changed_selected)
    original_payload = _result_payload(changed_result)
    changed_result.result = {"ok": False}
    tests.append({
        "test": "changed_result_is_refused_by_verification",
        "passed": refuses(lambda: verify(
            changed, changed_selected, changed_execution, changed_result)),
    })
    changed_result.result = original_payload["result"]
    provisional = fixture(mode="shadow")
    provisional_selected = select(provisional)
    provisional_execution, provisional_result, _ = execute(
        provisional, provisional_selected)
    provisional_link = verify(
        provisional, provisional_selected, provisional_execution,
        provisional_result, verdict="accept_provisional")
    provisional_source = provisional[0].stage_store.observations[0]
    tests.append({
        "test": "provisional_semantic_verdict_keeps_local_credit_unknown",
        "passed": provisional_link["local_verification"] is None
        and provisional_source.outcome.local_verification is None,
    })
    unavailable = fixture(mode="shadow")
    unavailable_selected = select(unavailable)
    unavailable_execution, unavailable_result, _ = execute(
        unavailable, unavailable_selected)
    unavailable_link = verify(
        unavailable, unavailable_selected, unavailable_execution,
        unavailable_result, verdict="repair", observed=False)
    tests.append({
        "test": "unavailable_semantic_verifier_keeps_credit_unknown",
        "passed": unavailable_link["local_verification"] is None,
    })
    repair = fixture(mode="shadow")
    repair_selected = select(repair)
    repair_execution, repair_result, _ = execute(repair, repair_selected)
    repair_link = verify(
        repair, repair_selected, repair_execution, repair_result,
        verdict="repair")
    tests.append({
        "test": "observed_repair_verdict_records_negative_local_check",
        "passed": repair_link["local_verification"] is False,
    })
    event_failure = fixture(mode="shadow", event_failure=True)
    failed_selection = try_record_selected_action(SelectedActionLineageRequest(
        event_failure[0], event_failure[1], event_failure[2],
        event_failure[5], event_failure[4]))
    tests.append({
        "test": "failed_canonical_selection_event_leaves_no_projection_link",
        "passed": failed_selection is None
        and not event_failure[0].stage_action_links,
    })
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "stage_action_lineage_checks/v1",
        "provider_calls": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = (
    "ActionExecutionLineageRequest",
    "ActionVerificationLineageRequest",
    "SelectedActionLineageRequest",
    "record_action_execution",
    "record_action_verification",
    "record_selected_action",
    "stage_lineage_summary",
    "source_stage_fields",
    "self_test",
    "try_record_action_execution",
    "try_record_action_verification",
    "try_record_selected_action",
)
