"""Terminal result and Run History projection for adaptive Practitioner runs.

This module projects accepted, failed, interrupted, and exact deterministic
outcomes. Its integration helper keeps local accepted results separate from
unverified attempts. It does not decide task semantics or execute tools.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

from ..loop.kernel import PassRecord, PractitionerState
from ..loop.recursive_loop import Loop, StepOutcome
from .adaptive_practitioner_records import (
    ADAPTIVE_PRACTITIONER_RECORD_TYPE,
    AdaptivePractitionerError,
    AdaptiveRunServices,
)
from .adaptive_practitioner_source import saved_source_inspections


def integrate_adaptive_state(
        state: PractitionerState, record: PassRecord,
        services: AdaptiveRunServices) -> PractitionerState:
    """Apply only subject-bound local acceptance inside the owning Loop.

    This is a run-state projection, not persistent Intelligence promotion or
    a semantic-runtime effect authorization. Old unclassified artifacts are
    not retroactively considered verified. Exact artifact bytes still need
    their existing artifact-store and time-of-use checks.
    """
    from .adaptive_practitioner_verification import (
        AdaptiveEvaluationBindingRequest,
        safe_result,
        validate_adaptive_evaluation,
    )
    from .stage_action_lineage import _digest

    facts, artifacts = deepcopy(state.facts), dict(state.artifacts)
    affected = _reported_artifact_refs(record.results)
    dispositions = dict(facts.get("artifact_dispositions") or {})
    for ref in affected:
        artifacts.pop(ref, None)
        dispositions[ref] = {"status": "UNVERIFIED", "state_version": state.version,
                             "verification_bound": False}
    facts["artifact_dispositions"] = dispositions
    incumbent = facts.get("accepted_incumbent")
    if incumbent and affected.intersection(incumbent.get("artifact_refs", ())):
        incumbent["status"] = "INVALIDATED_BY_OVERLAPPING_ATTEMPT"
        facts.pop("last_result", None)
    evaluation = record.evaluation
    index = getattr(evaluation, "best_index", None)
    index_valid = (isinstance(index, int) and not isinstance(index, bool)
                   and 0 <= index < len(record.results))
    verification = {}
    binding_error = ""
    try:
        verification = validate_adaptive_evaluation(
            AdaptiveEvaluationBindingRequest(
                record.plan, tuple(record.results), evaluation), services)
    except (ValueError, TypeError, AttributeError) as exc:
        binding_error = type(exc).__name__
        diagnostic = getattr(services, "diagnostic", None)
        if callable(diagnostic):
            diagnostic("adaptive_state_verification_unbound", {
                "error_type": binding_error, "state_version": state.version})
    if not index_valid:
        facts["last_attempt"] = {
            "record_type": "adaptive_attempt_state/v1", "status": "UNVERIFIED",
            "reason": "no valid selected result", "state_version": state.version,
            "verification_bound": bool(verification),
        }
        return state.derive(facts=facts, artifacts=artifacts)

    latest = record.results[index]
    result = deepcopy(safe_result(latest))
    accepted = bool(
        verification and evaluation.verdict == "accept" and not latest.errors
        and verification.get("semantic_verification_observed") is True
        and verification.get("deterministic_checks_passed") is True)
    status = ("ACCEPTED_LOCAL" if accepted else "UNVERIFIED"
              if not verification else "PROVISIONAL"
              if evaluation.verdict == "accept_provisional" else "REJECTED")
    result_digest = _digest(result)
    verification_digest = _digest(verification) if verification else None
    attempt = {
        "record_type": "adaptive_attempt_state/v1", "status": status,
        "state_version": state.version, "projected_result_digest": result_digest,
        "verification_record_digest": verification_digest,
        "verification_bound": bool(verification),
        "binding_error": binding_error,
        "persistent_promotion_authorized": False,
    }
    if accepted:
        attempt["result_ref"] = "facts.last_result"
    else:
        attempt["result"] = result
    facts["last_attempt"] = attempt
    facts["last_verification"] = deepcopy(verification)
    selected_refs = {str(ref) for ref in latest.artifact_refs}
    for ref in selected_refs:
        dispositions[ref] = {
            "status": status, "projected_result_digest": result_digest,
            "state_version": state.version,
            "verification_bound": bool(verification),
        }
        if accepted:
            artifacts[ref] = ref
        else:
            # A string address is not an immutable artifact identity. A new
            # unverified use of the same address cannot preserve old trust.
            artifacts.pop(ref, None)
    if accepted:
        facts["last_result"] = deepcopy(result)
        facts["accepted_incumbent"] = {
            **deepcopy(attempt), "artifact_refs": sorted(selected_refs),
            "verification_subject": deepcopy(verification.get("subject", {})),
        }
    facts["artifact_dispositions"] = dispositions
    return state.derive(facts=facts, artifacts=artifacts)


def _reported_artifact_refs(results) -> set[str]:
    """Include failed and unselected execution outputs before admitting any."""
    refs = {str(ref) for result in results for ref in result.artifact_refs}
    for result in results:
        payload = result.result
        if (isinstance(payload, dict)
                and payload.get("record_type") == "generated_project_execution/v1"):
            for key in ("artifacts", "writes"):
                for item in payload.get(key, ()):
                    if isinstance(item, dict) and isinstance(item.get("path"), str):
                        refs.add(item["path"])
    return refs


def has_bound_accepted_incumbent(run: dict, final_attempt: dict) -> bool:
    """Require current integrated acceptance before public success projection."""
    from ..loop.kernel import ResultPacket
    from .adaptive_practitioner_verification import safe_result
    from .stage_action_lineage import _digest

    facts = run.get("facts", {})
    incumbent, attempt = facts.get("accepted_incumbent", {}), facts.get("last_attempt", {})
    emitted = safe_result(ResultPacket("emitted project", result=final_attempt))["result"]
    return bool(incumbent.get("status") == attempt.get("status") == "ACCEPTED_LOCAL"
                and incumbent.get("verification_bound") is True
                and attempt.get("verification_bound") is True
                and incumbent.get("verification_record_digest")
                == attempt.get("verification_record_digest")
                and incumbent.get("projected_result_digest")
                == attempt.get("projected_result_digest") == _digest(facts.get("last_result"))
                and _digest(facts.get("last_result", {}).get("result")) == _digest(emitted))


def loop_details(events: list[dict]) -> list[dict]:
    """Project Loop identities, steps, and terminal reasons."""
    terminal = {item.get("loop_id"): item for item in events
                if item.get("event") == "terminal"}
    steps: dict[str, list[dict]] = {}
    for item in events:
        if item.get("event") == "run_step":
            steps.setdefault(str(item.get("loop_id")), []).append({
                "step": item.get("step"), "mode": item.get("mode"),
                "output": item.get("output"),
                "accepted": item.get("accepted"),
            })
    return [{
        "loop_id": item.get("loop_id"), "goal": item.get("goal"),
        "role": item.get("role"), "profile_id": item.get("profile_id"),
        "relationship": item.get("relationship_kind"),
        "input_roles": list(item.get("input_roles") or ()),
        "output_roles": list(item.get("output_roles") or ()),
        "loop_condition": item.get("loop_condition"),
        "exit_condition": item.get("exit_condition"),
        "steps": steps.get(str(item.get("loop_id")), []),
        "terminal_reason": (terminal.get(item.get("loop_id")) or {}).get(
            "reason", ""),
    } for item in events if item.get("event") == "init"]


def save_adaptive_result(history: dict, output: dict) -> None:
    """Write the internal adaptive result only when persistence is enabled."""
    if not history.get("path"):
        return
    result_path = Path(history["path"]) / "adaptive-result.json"
    result_path.write_text(json.dumps(
        output, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    output["result_path"] = str(result_path)


def safe_model_usage(services: AdaptiveRunServices) -> list[dict]:
    """Remove model text while preserving exact provider accounting."""
    if services.model_session is None:
        return []
    rows = []
    for result in services.model_session.results:
        value = result.to_dict()
        value.pop("text", None)
        rows.append(value)
    return rows


def finish_deterministic_attempt(
        owner: Loop, services: AdaptiveRunServices,
        history_builder: Callable[[], dict]) -> dict:
    """Terminate and save an explicitly selected exact reuse run."""
    trace = services.deterministic_attempt
    if trace is None:
        raise AdaptivePractitionerError(
            "deterministic attempt trace is missing")
    resolved = trace.status == "COMPLETED"
    result_value = dict(trace.outputs).get("result") if resolved else None

    def handler(_active, step, _context):
        if step == "act":
            return StepOutcome(
                "deterministic:executed" if resolved
                else "deterministic:no_verified_capability",
                "deterministic", 1.0 if resolved else 0.0,
                failed=not resolved)
        if step == "verify":
            return StepOutcome(
                "verify:passed" if resolved else "verify:not_satisfied",
                "deterministic", 1.0 if resolved else 0.0,
                failed=not resolved)
        return StepOutcome(
            f"{step}:trace_preserved", "deterministic",
            1.0 if resolved else 0.5)

    owner.run(handler=handler, max_steps=len(owner.steps()) + 1)
    history = history_builder()
    output = {
        "record_type": ADAPTIVE_PRACTITIONER_RECORD_TYPE,
        "run_id": services.run_id,
        "status": "VERIFIED_WORKING" if resolved else "NOT_YET_PROVEN",
        "solved": resolved,
        "failure_code": "" if resolved else trace.status,
        "result": result_value, "original_task": services.request.task,
        "task_feedback": [item.to_dict()
                          for item in services.request.feedback],
        "mode": services.request.mode,
        "deterministic_attempt": trace.to_dict(), "passes": 1,
        "final_route": "stop_success" if resolved else "stop_unprofitable",
        "failures": [] if resolved else list(trace.errors),
        "model_calls": 0, "loop_details": loop_details(owner.ledger.events),
        "run_history": history,
    }
    save_adaptive_result(history, output)
    return output


def failed_adaptive_output(
        owner: Loop, services: AdaptiveRunServices,
        failure_code: str, failure: str,
        history_builder: Callable[[], dict]) -> dict:
    """Persist one failed or interrupted run through canonical history."""
    history = history_builder()
    output = {
        "record_type": ADAPTIVE_PRACTITIONER_RECORD_TYPE,
        "run_id": services.run_id, "status": "NOT_YET_PROVEN",
        "solved": False, "failure_code": failure_code,
        "failure": failure[:1000], "original_task": services.request.task,
        "mode": services.request.mode,
        "task_feedback": [item.to_dict()
                          for item in services.request.feedback],
        "deterministic_attempt": services.deterministic_attempt.to_dict(),
        "model_calls": services.model_session.calls_used,
        "model_usage": safe_model_usage(services),
        "option_selection": services.selection_tally.to_dict(),
        "semantic_autonomy": services.semantic_decisions.to_dict(),
        "semantic_decisions": [item.to_dict()
                               for item in services.semantic_decisions
                               .decisions],
        "orientations": [item.to_dict()
                         for item in services.orientation_by_version.values()],
        "action_decisions": services.action_history,
        "context_snapshots": services.context_snapshots,
        "candidate_solution_canvases": services.candidate_canvases,
        "selected_solution_canvas": services.plan_details.get(
            "active_canvas", {}),
        "web_search_candidates": services.web_search_results,
        "web_evidence": services.web_results,
        "source_inspections": saved_source_inspections(
            services.source_inspections),
        "project_attempts": services.project_attempts,
        "verification": services.verification_records,
        "supervision": services.supervision_findings,
        "recovery_directives": services.recovery_directives,
        "generated_file_checkpoints":
            services.generated_file_checkpoint_summaries(),
        "loop_details": loop_details(owner.ledger.events),
        "run_history": history,
    }
    save_adaptive_result(history, output)
    return output


def self_test() -> dict:
    """Prove the Loop detail projection preserves steps and termination."""
    value = loop_details([
        {"event": "init", "loop_id": "loop1", "goal": "test",
         "role": "practitioner", "profile_id": "practitioner.solver",
         "relationship_kind": "starting", "input_roles": (),
         "output_roles": ("result",), "loop_condition": "steps_remain",
         "exit_condition": "steps_complete"},
        {"event": "run_step", "loop_id": "loop1", "step": "act",
         "mode": "deterministic", "output": "done", "accepted": True},
        {"event": "terminal", "loop_id": "loop1", "reason": "done"},
    ])
    passed = (len(value) == 1 and value[0]["steps"][0]["step"] == "act"
              and value[0]["terminal_reason"] == "done")
    tests = [{"test": "adaptive_result_preserves_loop_detail",
              "passed": passed, "detail": str(value)}]
    tests.extend(_integration_checks())
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "adaptive_result_projection_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def _integration_checks() -> list[dict]:
    """Isolate state projection; product checks exercise real issued verdicts."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from ..loop.kernel import EvaluationPacket, ExecutionPlan, ProblemSpec, ResultPacket

    checks = []
    source = PractitionerState(ProblemSpec("retain verified work"))
    services = SimpleNamespace()
    plan = ExecutionPlan("use", "run_direct")

    def record(verdict, ref, *, index=0, errors=()):
        return PassRecord(1, 0, plan=plan, results=[ResultPacket(
            ref, result={"value": ref}, artifact_refs=(ref,), errors=errors)],
            evaluation=EvaluationPacket(verdict, best_index=index))

    binding = {
        "record_type": "adaptive_verification/v2",
        "semantic_verification_observed": True,
        "deterministic_checks_passed": True,
    }
    boundary = ("loop_engine.core.adaptive_practitioner_verification."
                "validate_adaptive_evaluation")
    with patch(boundary, return_value=binding):
        accepted = integrate_adaptive_state(source, record("accept", "a"), services)
        rejected = integrate_adaptive_state(accepted, record("repair", "b"), services)
        checks.append({"test": "rejected_result_cannot_replace_accepted_incumbent",
            "passed": rejected.facts["last_result"]["result"] == {"value": "a"}
            and rejected.facts["last_attempt"]["status"] == "REJECTED"
            and "a" in rejected.artifacts and "b" not in rejected.artifacts})
        later = integrate_adaptive_state(rejected, record("accept", "c"), services)
        checks.append({"test": "later_accept_does_not_launder_rejected_artifact",
            "passed": "b" not in later.artifacts
            and later.facts["artifact_dispositions"]["b"]["status"] == "REJECTED"
            and later.facts["last_result"]["result"] == {"value": "c"}})
        provisional = integrate_adaptive_state(
            accepted, record("accept_provisional", "p"), services)
        checks.append({"test": "provisional_result_is_not_an_accepted_artifact",
            "passed": "p" not in provisional.artifacts
            and provisional.facts["last_attempt"]["status"] == "PROVISIONAL"})
        collision = integrate_adaptive_state(accepted, record("repair", "a"), services)
        checks.append({"test": "reused_mutable_address_invalidates_prior_incumbent",
            "passed": "a" not in collision.artifacts
            and "last_result" not in collision.facts
            and collision.facts["accepted_incumbent"]["status"]
            == "INVALIDATED_BY_OVERLAPPING_ATTEMPT"})
        failed_write = record("repair", "")
        failed_write.results = [ResultPacket("failed overwrite", result={
            "record_type": "generated_project_execution/v1",
            "artifacts": [{"path": "a", "verified": False}],
            "writes": [], "deterministic_checks_passed": False}, errors=("failed",))]
        failed_state = integrate_adaptive_state(accepted, failed_write, services)
        checks.append({"test": "failed_reported_artifact_invalidates_even_without_accepted_refs",
            "passed": "a" not in failed_state.artifacts
            and failed_state.facts["accepted_incumbent"]["status"]
            == "INVALIDATED_BY_OVERLAPPING_ATTEMPT"})
        failed_write.evaluation = EvaluationPacket("repair", best_index=7)
        invalid_index = integrate_adaptive_state(accepted, failed_write, services)
        checks.append({"test": "invalid_result_selection_cannot_skip_write_invalidation",
            "passed": "a" not in invalid_index.artifacts and "last_result" not in invalid_index.facts})
        unselected_write = record("repair", "b")
        unselected_write.results.extend(failed_write.results)
        unselected_state = integrate_adaptive_state(accepted, unselected_write, services)
        checks.append({"test": "unselected_executed_results_still_invalidate_mutable_addresses",
            "passed": "a" not in unselected_state.artifacts})
        checks.append({"test": "integration_does_not_mutate_prior_state_or_evidence",
            "passed": source.facts == {} and source.artifacts == {}
            and accepted.facts["accepted_incumbent"]["status"] == "ACCEPTED_LOCAL"
            and "status" not in binding})
        bad_indices = [True, -1, 7, "0", None]
        checks.append({"test": "invalid_selected_index_preserves_incumbent_without_indexing",
            "passed": all(integrate_adaptive_state(
                accepted, record("accept", "x", index=i), services
            ).facts["last_attempt"]["status"] == "UNVERIFIED" for i in bad_indices)})
        errored = integrate_adaptive_state(
            accepted, record("accept", "x", errors=("failed",)), services)
        checks.append({"test": "errored_result_cannot_enter_accepted_state",
            "passed": "x" not in errored.artifacts
            and errored.facts["last_result"]["result"] == {"value": "a"}})
    with patch(boundary, side_effect=ValueError("wrong subject")):
        unbound = integrate_adaptive_state(accepted, record("accept", "x"), services)
    checks.append({"test": "unbound_verdict_cannot_grant_local_acceptance",
        "passed": "x" not in unbound.artifacts
        and unbound.facts["last_attempt"]["status"] == "UNVERIFIED"
        and unbound.facts["last_result"]["result"] == {"value": "a"}})
    from tempfile import TemporaryDirectory

    from .adaptive_practitioner_acceptance_checks import _run, _success_answers

    integrated_states = []

    def capture(state, record, services):
        value = integrate_adaptive_state(state, record, services)
        integrated_states.append(value)
        return value

    with TemporaryDirectory() as root, patch(
            "loop_engine.core.adaptive_practitioner.integrate_adaptive_state",
            side_effect=capture):
        product = _run("Create a verified result.", _success_answers(), root)
    checks.append({"test": "product_path_binds_verifier_before_accepting_incumbent",
        "passed": product["solved"] and len(integrated_states) == 1
        and integrated_states[0].facts.get("accepted_incumbent", {}).get("status")
        == "ACCEPTED_LOCAL"
        and integrated_states[0].facts["last_attempt"]["verification_bound"]})
    from .stage_action_lineage import _digest
    unicode_answers = list(_success_answers())
    verifier_answer = json.loads(unicode_answers[-2])
    verifier_answer["notes"] = "Vérification réussie."
    unicode_answers[-2] = json.dumps(verifier_answer)
    with TemporaryDirectory() as root:
        unicode_result = _run("Create a verified result.", tuple(unicode_answers), root)
    checks.append({"test": "state_verification_reference_uses_canonical_unicode_digest",
        "passed": unicode_result["solved"]
        and unicode_result["state_evidence"]["accepted_incumbent"]["verification_record_digest"]
        == _digest(unicode_result["verification"][-1])})
    from ..loop.recursive_loop import LoopLedger
    original_record = LoopLedger.record

    def drop_verification_anchor(ledger, **values):
        if values.get("custom_kind") != "adaptive_verification_recorded":
            return original_record(ledger, **values)
        return None

    with TemporaryDirectory() as root, patch.object(
            LoopLedger, "record", drop_verification_anchor):
        no_anchor = _run("Create a verified result.", _success_answers(), root)
    checks.append({"test": "missing_verifier_anchor_cannot_report_product_success",
        "passed": not no_anchor["solved"]
        and no_anchor["state_evidence"]["last_attempt"]["status"] == "UNVERIFIED"})
    return checks


__all__ = (
    "failed_adaptive_output", "finish_deterministic_attempt",
    "has_bound_accepted_incumbent", "integrate_adaptive_state", "loop_details", "safe_model_usage",
    "save_adaptive_result",
)
