"""Adversarial offline checks for exact stage-to-action outcome lineage.

These tests attack identity, pass, plan, event-order, result, evaluator, and
duplicate-join boundaries. They make no provider or model-quality claim.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from ..loop.kernel import (
    EvaluationPacket, ExecutionPlan, PractitionerState, ProblemSpec, ResultPacket)
from .adaptive_practitioner_verification import (
    AdaptiveEvaluationBindingRequest, AdaptiveVerificationRequest,
    AdaptiveRouteRequest, AdaptiveVerificationSubject, _append_verification_record,
    route_adaptive_result, validate_adaptive_evaluation, verify_adaptive_results)
from .stage_action_lineage import (
    ActionExecutionLineageRequest,
    ActionVerificationLineageRequest,
    SelectedActionLineageRequest,
    _digest,
    _result_payload,
    record_action_execution,
    record_action_verification,
    record_selected_action,
    try_record_action_execution,
    try_record_action_verification,
)
from .stage_fingerprint import SemanticStageFingerprint
from .stage_store import StageStore


def _fixture():
    store, events, diagnostics = StageStore(), [], []
    owner = SimpleNamespace(
        loop_id="loop.owner",
        ledger=SimpleNamespace(record=lambda **value: events.append(value),
                               events=events))
    source = store.add(SemanticStageFingerprint(
        semantic_responsibility="select action", cognitive_phase="decide_next"),
        run_id="lineage-adversarial", occurrence_id="occurrence.decision.1",
        semantic_call_id="semantic.decision.1", owner_loop_id=owner.loop_id,
        pass_number=1, output_admitted=True)
    payload = {"action_kind": "BUILD", "goal": "build"}
    action_id = "action:" + _digest(payload)[:20]
    services = SimpleNamespace(
        run_id="lineage-adversarial", active_pass_number=1,
        request=SimpleNamespace(
            stage_assistance=SimpleNamespace(mode="shadow")),
        stage_store=store, _graded_stage=source,
        stage_arms={source.occurrence_id: {
            "cognitive_phase": "decide_next"}},
        stage_assistance_decisions=[],
        action_details={action_id: SimpleNamespace(
            to_dict=lambda: dict(payload))},
        plan_details={action_id: {
            "capability_ref": "core.generated_project",
            "arguments": {"path": "out"}}},
        verification_records=[], stage_action_links=[],
        stage_execution_links=[], stage_outcome_links=[],
        stage_attribution_events=[], stage_evidence_degradations=[],
        diagnostic=lambda code, detail: diagnostics.append((code, detail)))
    return services, owner, source, payload, action_id, events, diagnostics


def _select(parts, source=None):
    services, owner, initial, payload, action_id, _, _ = parts
    return record_selected_action(SelectedActionLineageRequest(
        services, owner, source or initial, action_id, payload))


def _plan(selected, action_id, *, capability="core.generated_project",
          arguments=None):
    return {
        "how_mode": "use", "act_mode": "run_direct", "handle": capability,
        "steps": [], "resources": [], "spawned_loops": [],
        "experiment": {
            "action_id": action_id,
            "action_occurrence_ref": selected["action_occurrence_ref"],
            "arguments": {"path": "out"} if arguments is None else arguments,
        },
        "rationale": "adversarial fixture",
    }


def _execute(parts, selected, result=None, plan=None):
    services, owner, _, _, action_id, _, _ = parts
    result = result or ResultPacket("build", result={"ok": True})
    plan = plan or _plan(selected, action_id)
    record = record_action_execution(ActionExecutionLineageRequest(
        services, owner, selected["action_occurrence_ref"], action_id,
        plan["handle"], plan, result))
    return record, result


def _prepare_verifier(parts, *, phase="verify", admitted=True):
    services, owner, _, _, _, _, _ = parts
    suffix = str(len(services.stage_store.observations))
    verifier = services.stage_store.add(SemanticStageFingerprint(
        semantic_responsibility="verify result", cognitive_phase=phase),
        run_id=services.run_id, occurrence_id=f"occurrence.verifier.{suffix}",
        semantic_call_id=f"semantic.verifier.{suffix}",
        owner_loop_id=owner.loop_id, pass_number=services.active_pass_number,
        output_admitted=admitted)
    services.stage_arms[verifier.occurrence_id] = {"cognitive_phase": phase}
    services._graded_stage = verifier
    return verifier


def _evaluation(parts, verifier, *, verdict="accept", observed=True,
                deterministic=True):
    services = parts[0]
    execution = services.stage_execution_links[-1]
    record = {
        "record_type": "adaptive_verification/v2", "verdict": verdict,
        "subject": AdaptiveVerificationSubject(
            services.run_id, execution["action_id"],
            execution["action_occurrence_ref"], execution["plan_digest"],
            (execution["result_digest"],), (execution["execution_ref"],)).to_dict(),
        "pass_number": services.active_pass_number,
        "verifier_stage_occurrence_id": verifier.occurrence_id,
        "verifier_semantic_call_id": verifier.semantic_call_id,
        "semantic_verification_observed": observed,
        "deterministic_checks_passed": deterministic,
    }
    _append_verification_record(services, record, parts[1])
    return record


def _verify(parts, selected, execution, result, verifier, evaluation, **flags):
    services, owner = parts[:2]
    return record_action_verification(ActionVerificationLineageRequest(
        services, owner, selected["action_occurrence_ref"],
        execution["execution_ref"], verifier.occurrence_id,
        (_result_payload(result),), evaluation,
        flags.get("verdict", evaluation["verdict"]),
        flags.get("deterministic", evaluation["deterministic_checks_passed"]),
        flags.get("observed", evaluation["semantic_verification_observed"])))


def _refuses(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError):
        return True
    return False


def _actual_evaluation(parts, plan, results, *, best_index=0, verdict="accept",
                       during_call=None, response_changes=None):
    """Exercise the real producer, including its canonical event append."""
    from unittest.mock import patch

    from . import adaptive_practitioner_verification as verification

    services, owner = parts[:2]
    services.orientation_by_version = {}
    services.request.task = "verify the supplied result set"
    verifier = _prepare_verifier(parts)
    seen = []

    def model(request):
        seen.append(request.state)
        if during_call is not None:
            during_call()
        return {
            "verdict": verdict, "best_index": best_index, "scores": [1.0],
            "notes": "Checked exactly the supplied plan and results.",
            "remaining_gaps": [], "advisory_findings": [],
            "new_requirement_proposals": [],
            **(response_changes or {}),
        }

    services.model = model
    with patch.object(verification, "current_kernel_owner", return_value=owner):
        evaluated = verify_adaptive_results(AdaptiveVerificationRequest(
            PractitionerState(ProblemSpec(services.request.task)),
            plan, tuple(results), {}), services)
    return evaluated, services.verification_records[-1], verifier, seen


def _route_with_evidence(parts, plan, result, evaluation, *, requested="stop_success",
                         final_attempt=None):
    from unittest.mock import patch

    from . import adaptive_practitioner_verification as verification

    services, owner = parts[:2]
    services.model = lambda _request: {"route": requested, "reason": "fixture route"}
    services.project_attempts = [
        result.result if final_attempt is None else final_attempt]
    services.web_results, services.source_inspections = [], []
    services.action_history, services.progress_snapshots = [], []
    services.unchanged_progress_snapshots = 0
    services.active_recovery_directive = None
    record = SimpleNamespace(plan=plan, results=(result,), evaluation=evaluation,
                             pass_number=services.active_pass_number)
    with patch.object(verification, "current_kernel_owner", return_value=owner):
        route, _ = route_adaptive_result(AdaptiveRouteRequest(
            PractitionerState(ProblemSpec("exact verified completion")), record, {}),
            services)
    return route


def _subject_binding_checks() -> list[dict]:
    tests = []

    def check(name, ok):
        tests.append({"test": name, "passed": bool(ok)})

    mismatch = _fixture()
    selected_a = _select(mismatch)
    execution_a, result_a = _execute(
        mismatch, selected_a, ResultPacket("A", result={"answer": "A"}))
    mismatch[0].active_pass_number = 2
    plan_a = ExecutionPlan(**_plan(selected_a, mismatch[4]))
    plan_b = replace(plan_a, experiment={"action_id": "action.B",
                                         "action_occurrence_ref": "occurrence.B"})
    result_b = ResultPacket("B", result={"answer": "B"})
    evaluated_b, record_b, verifier_b, seen = _actual_evaluation(
        mismatch, plan_b, (result_b,))
    check("genuine_B_evaluation_cannot_grant_A_credit",
          evaluated_b.verdict == "accept"
          and seen[0]["results"][0]["objective"] == "B"
          and _refuses(lambda: _verify(mismatch, selected_a, execution_a,
                                      result_a, verifier_b, record_b))
          and mismatch[0].stage_store.observations[0].outcome.local_verification is None)

    # Replacing even the genuine record's subject cannot change its issued digest.
    record_b["subject"] = AdaptiveVerificationSubject(
        mismatch[0].run_id, selected_a["action_id"],
        selected_a["action_occurrence_ref"], execution_a["plan_digest"],
        (execution_a["result_digest"],), (execution_a["execution_ref"],)).to_dict()
    check("grafted_subject_on_genuine_record_is_refused",
          _refuses(lambda: _verify(mismatch, selected_a, execution_a,
                                  result_a, verifier_b, record_b)))

    delayed = _fixture()
    selected = _select(delayed)
    execution, result = _execute(delayed, selected, ResultPacket(
        "verified project", result={"manifest_digest": "fixture",
                                    "deterministic_checks_passed": True}))
    plan = ExecutionPlan(**_plan(selected, delayed[4]))
    delayed[0].active_pass_number = 2
    evaluated, record, verifier, _ = _actual_evaluation(delayed, plan, (result,))
    binding = AdaptiveEvaluationBindingRequest(plan, (result,), evaluated)
    check("integration_accepts_exact_delayed_evaluation",
          validate_adaptive_evaluation(binding, delayed[0], delayed[1]) is record)
    linked = _verify(delayed, selected, execution, result, verifier, record)
    check("later_verifier_can_check_the_same_exact_old_subject",
          linked["local_verification"] is True
          and linked["execution_ref"] == execution["execution_ref"])
    check("stop_success_requires_and_accepts_exact_verification_evidence",
          _route_with_evidence(delayed, plan, result, evaluated).route == "stop_success")
    check("integration_refuses_a_different_EvaluationPacket",
          _refuses(lambda: validate_adaptive_evaluation(
              replace(binding, evaluation=EvaluationPacket("accept", notes="forged")),
              delayed[0], delayed[1])))
    changed_plan = replace(plan, rationale="different method")
    check("integration_refuses_changed_plan",
          _refuses(lambda: validate_adaptive_evaluation(
              replace(binding, plan=changed_plan), delayed[0], delayed[1])))

    source_result = ResultPacket("later source read", result={"source": "new data"})
    source_plan = replace(plan, handle="core.source.inspect", experiment={})
    source_evaluation, _, _, _ = _actual_evaluation(delayed, source_plan, (source_result,))
    check("accepted_source_result_cannot_finalize_an_earlier_project",
          _route_with_evidence(delayed, source_plan, source_result, source_evaluation,
                               final_attempt=result.result).route == "repair")
    returned = ResultPacket("return verified project", result=result.result)
    return_plan = replace(plan, handle="core.finish", experiment={})
    return_evaluation, _, _, _ = _actual_evaluation(delayed, return_plan, (returned,))
    check("explicit_return_of_the_same_verified_project_can_finish",
          _route_with_evidence(delayed, return_plan, returned, return_evaluation,
                               final_attempt=result.result).route == "stop_success")

    changed = _fixture()
    selected = _select(changed)
    execution, result = _execute(changed, selected)
    changed_plan = ExecutionPlan(**_plan(selected, changed[4]))
    changed_plan.rationale = "a plan that did not execute"
    _, record, verifier, _ = _actual_evaluation(changed, changed_plan, (result,))
    check("genuine_verdict_for_changed_plan_cannot_credit_old_execution",
          _refuses(lambda: _verify(changed, selected, execution, result,
                                  verifier, record)))

    ordered = _fixture()
    selected = _select(ordered)
    execution, first = _execute(ordered, selected)
    second = ResultPacket("another result", result={"answer": "other"})
    plan = ExecutionPlan(**_plan(selected, ordered[4]))
    evaluated, record, verifier, _ = _actual_evaluation(
        ordered, plan, (first, second))
    binding = AdaptiveEvaluationBindingRequest(plan, (first, second), evaluated)
    check("complete_ordered_result_set_is_bound",
          len(record["subject"]["result_digests"]) == 2
          and validate_adaptive_evaluation(binding, ordered[0], ordered[1]) is record
          and _refuses(lambda: validate_adaptive_evaluation(
              replace(binding, results=(second, first)), ordered[0], ordered[1])))
    check("bundle_evaluation_cannot_credit_only_one_supplied_member",
          _refuses(lambda: _verify(ordered, selected, execution, first,
                                  verifier, record)))
    check("integration_refuses_duplicate_result_member",
          _refuses(lambda: validate_adaptive_evaluation(
              replace(binding, results=(first, first)), ordered[0], ordered[1])))
    ordered[0].stage_execution_links.append(dict(execution))
    check("duplicate_execution_member_is_ambiguous",
          _refuses(lambda: validate_adaptive_evaluation(
              binding, ordered[0], ordered[1])))

    legacy = _fixture()
    selected = _select(legacy)
    execution, result = _execute(legacy, selected)
    verifier = _prepare_verifier(legacy)
    record = _evaluation(legacy, verifier)
    record.pop("subject")
    record["record_type"] = "adaptive_verification/v1"
    check("historical_v1_without_subject_cannot_create_exact_credit",
          _refuses(lambda: _verify(legacy, selected, execution, result,
                                  verifier, record)))

    missing = _fixture()
    selected = _select(missing)
    execution, result = _execute(missing, selected)
    verifier = _prepare_verifier(missing)
    record = _evaluation(missing, verifier)
    missing[5][:] = [item for item in missing[5]
                     if item.get("custom_kind") != "adaptive_verification_recorded"]
    check("subject_without_canonical_event_cannot_create_credit",
          _refuses(lambda: _verify(missing, selected, execution, result,
                                  verifier, record)))

    for requested in ("stop_success", "invalid-route-for-fallback"):
        absent = _fixture()
        selected = _select(absent)
        _, result = _execute(absent, selected, ResultPacket(
            "verified project", result={"manifest_digest": "fixture",
                                        "deterministic_checks_passed": True}))
        plan = ExecutionPlan(**_plan(selected, absent[4]))
        evaluated, _, _, _ = _actual_evaluation(absent, plan, (result,))
        absent[5][:] = [item for item in absent[5]
                        if item.get("custom_kind") != "adaptive_verification_recorded"]
        check(f"{requested}_cannot_finalize_without_verification_event",
              _route_with_evidence(absent, plan, result, evaluated,
                                   requested=requested).route == "repair")

    for channel in ("remaining_gaps", "advisory_findings", "new_requirement_proposals"):
        scoped = _fixture()
        selected = _select(scoped)
        _, result = _execute(scoped, selected)
        plan = ExecutionPlan(**_plan(selected, scoped[4]))
        change = ([{"criterion_ref": "criterion:0", "gap": "output not checked"}]
                  if channel == "remaining_gaps" else ["Optional additional work"])
        evaluated, record, _, _ = _actual_evaluation(
            scoped, plan, (result,), response_changes={channel: change})
        check(f"verification_scope_{channel}_preserves_completion_contract",
              (evaluated.verdict == "repair"
               and record["semantic_verification_observed"] is False)
              if channel == "remaining_gaps" else
              (evaluated.verdict == "accept"
               and record["semantic_verification_observed"] is True))

    mutable = _fixture()
    selected = _select(mutable)
    execution, result = _execute(mutable, selected)
    plan = ExecutionPlan(**_plan(selected, mutable[4]))
    original_plan_digest = _digest(_plan(selected, mutable[4]))

    def mutate_inputs():
        plan.experiment["arguments"]["path"] = "changed"
        result.result["ok"] = False

    evaluated, record, _, seen = _actual_evaluation(
        mutable, plan, (result,), during_call=mutate_inputs)
    check("verifier_input_snapshot_has_no_mutable_plan_or_result_alias",
          seen[0]["plan"]["experiment"]["arguments"]["path"] == "out"
          and seen[0]["results"][0]["result"] == {"ok": True}
          and record["subject"]["plan_digest"] == original_plan_digest
          and record["subject"]["result_digests"] == [execution["result_digest"]]
          and evaluated.verdict == "repair"
          and record["semantic_verification_observed"] is False)

    for index in (True, -1, 1, 7, "0", 0.5, None):
        invalid = _fixture()
        selected = _select(invalid)
        _, result = _execute(invalid, selected)
        plan = ExecutionPlan(**_plan(selected, invalid[4]))
        evaluated, record, _, _ = _actual_evaluation(
            invalid, plan, (result,), best_index=index)
        check(f"invalid_best_index_{type(index).__name__}_{index!r}_is_repaired",
              evaluated.verdict == "repair" and evaluated.best_index == 0
              and record["semantic_verification_observed"] is False)
    return tests


def self_test() -> dict[str, object]:
    """Refuse cross-pass, forged, duplicate, and non-canonical joins."""
    tests = []

    foreign = _fixture()
    foreign_stage = replace(foreign[2], run_id="foreign")
    foreign[0]._graded_stage = foreign_stage
    tests.append({"test": "foreign_run_stage_is_refused", "passed": _refuses(
        lambda: _select(foreign, foreign_stage))})
    wrong_owner = _fixture()
    wrong_owner_stage = replace(wrong_owner[2], owner_loop_id="other")
    wrong_owner[0]._graded_stage = wrong_owner_stage
    tests.append({"test": "foreign_owner_stage_is_refused", "passed": _refuses(
        lambda: _select(wrong_owner, wrong_owner_stage))})
    stale_pass = _fixture()
    stale_pass[0].active_pass_number = 2
    tests.append({"test": "stale_pass_stage_is_refused", "passed": _refuses(
        lambda: _select(stale_pass))})

    repeat = _fixture()
    first = _select(repeat)
    first_execution, _ = _execute(repeat, first)
    repeat[0].active_pass_number = 2
    second_stage = repeat[0].stage_store.add(SemanticStageFingerprint(
        semantic_responsibility="select action", cognitive_phase="decide_next"),
        run_id=repeat[0].run_id, occurrence_id="occurrence.decision.2",
        semantic_call_id="semantic.decision.2",
        owner_loop_id=repeat[1].loop_id, pass_number=2,
        output_admitted=True)
    repeat[0].stage_arms[second_stage.occurrence_id] = {
        "cognitive_phase": "decide_next"}
    repeat[0]._graded_stage = second_stage
    second = _select(repeat, second_stage)
    second_execution, _ = _execute(repeat, second)
    tests.append({
        "test": "same_action_on_second_pass_has_disjoint_exact_lineage",
        "passed": first["action_occurrence_ref"]
        != second["action_occurrence_ref"]
        and first_execution["execution_ref"]
        != second_execution["execution_ref"]
        and len(repeat[0].stage_execution_links) == 2,
    })

    wrong_plan = _fixture()
    selected = _select(wrong_plan)
    bad = _plan(selected, wrong_plan[4], arguments={"path": "other"})
    tests.append({"test": "plan_arguments_outside_admitted_method_are_refused",
                  "passed": _refuses(
                      lambda: _execute(wrong_plan, selected, plan=bad))})
    no_event = _fixture()
    selected = _select(no_event)
    no_event[1].ledger.record = lambda **value: (_ for _ in ()).throw(
        RuntimeError("event sink unavailable"))
    failed_execution = try_record_action_execution(
        ActionExecutionLineageRequest(
            no_event[0], no_event[1], selected["action_occurrence_ref"],
            no_event[4], "core.generated_project",
            _plan(selected, no_event[4]), ResultPacket("build", result={})))
    source = no_event[0].stage_store.observations[0]
    tests.append({
        "test": "failed_execution_event_cannot_create_use_or_projection",
        "passed": failed_execution is None
        and not no_event[0].stage_execution_links
        and source.outcome.downstream_use is None,
    })

    absent_verifier = _fixture()
    selected = _select(absent_verifier)
    execution, result = _execute(absent_verifier, selected)
    fake_evaluation = {
        "verdict": "accept", "pass_number": 1,
        "verifier_stage_occurrence_id": "missing",
        "verifier_semantic_call_id": "missing",
        "semantic_verification_observed": True,
        "deterministic_checks_passed": True,
    }
    absent_verifier[0].verification_records.append(fake_evaluation)
    tests.append({"test": "nonexistent_verifier_is_refused", "passed": _refuses(
        lambda: record_action_verification(ActionVerificationLineageRequest(
            absent_verifier[0], absent_verifier[1],
            selected["action_occurrence_ref"], execution["execution_ref"],
            "missing", (_result_payload(result),), fake_evaluation,
            "accept", True, True)))})

    nonverify = _fixture()
    selected = _select(nonverify)
    execution, result = _execute(nonverify, selected)
    verifier = _prepare_verifier(nonverify, phase="orient")
    evaluation = _evaluation(nonverify, verifier)
    tests.append({"test": "non_verify_stage_cannot_be_the_verifier",
                  "passed": _refuses(lambda: _verify(
                      nonverify, selected, execution, result,
                      verifier, evaluation))})
    forged_evaluation = _fixture()
    selected = _select(forged_evaluation)
    execution, result = _execute(forged_evaluation, selected)
    verifier = _prepare_verifier(forged_evaluation)
    evaluation = _evaluation(forged_evaluation, verifier)
    detached = dict(evaluation)
    tests.append({"test": "detached_evaluation_record_is_refused",
                  "passed": _refuses(lambda: _verify(
                      forged_evaluation, selected, execution, result,
                      verifier, detached))})
    tests.append({"test": "truthy_text_is_not_a_verification_boolean",
                  "passed": _refuses(lambda: _verify(
                      forged_evaluation, selected, execution, result,
                      verifier, evaluation, deterministic="yes"))})

    no_outcome_event = _fixture()
    selected = _select(no_outcome_event)
    execution, result = _execute(no_outcome_event, selected)
    verifier = _prepare_verifier(no_outcome_event)
    evaluation = _evaluation(no_outcome_event, verifier)
    no_outcome_event[1].ledger.record = lambda **value: (
        _ for _ in ()).throw(RuntimeError("event sink unavailable"))
    failed_verification = try_record_action_verification(
        ActionVerificationLineageRequest(
            no_outcome_event[0], no_outcome_event[1],
            selected["action_occurrence_ref"], execution["execution_ref"],
            verifier.occurrence_id, (_result_payload(result),), evaluation,
            "accept", True, True))
    source = no_outcome_event[0].stage_store.observations[0]
    tests.append({
        "test": "failed_outcome_event_cannot_create_local_credit",
        "passed": failed_verification is None
        and not no_outcome_event[0].stage_outcome_links
        and source.outcome.local_verification is None,
    })

    duplicate = _fixture()
    selected = _select(duplicate)
    execution, result = _execute(duplicate, selected)
    verifier = _prepare_verifier(duplicate)
    evaluation = _evaluation(duplicate, verifier)
    first_verification = _verify(
        duplicate, selected, execution, result, verifier, evaluation)
    tests.append({"test": "duplicate_verification_is_refused", "passed": bool(
        first_verification) and _refuses(lambda: _verify(
            duplicate, selected, execution, result, verifier, evaluation))})

    tests.extend(_subject_binding_checks())
    passed = sum(bool(item["passed"]) for item in tests)
    return {
        "record_type": "stage_action_lineage_adversarial_checks/v1",
        "provider_calls": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = ("self_test",)
