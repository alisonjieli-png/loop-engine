"""Read-only offline probes of current dirty Loop Engine contracts."""
import json
from types import SimpleNamespace

from loop_engine.core.stage_action_lineage_adversarial_checks import (
    _fixture, _select, _execute, _prepare_verifier, _verify,
)
from loop_engine.core.stage_action_lineage import _digest, _result_payload
from loop_engine.core.adaptive_practitioner_verification import (
    AdaptiveVerificationRequest, verify_adaptive_results,
)
from loop_engine.core.adaptive_practitioner import _adaptive_impls
from loop_engine.loop.kernel import (
    ProblemSpec, PractitionerState, ExecutionPlan, ResultPacket,
    EvaluationPacket,
)


def cross_subject_evaluation():
    parts = _fixture()
    services = parts[0]
    selected_a = _select(parts)
    result_a = ResultPacket("build A", result={"subject": "A", "answer": "never evaluated"})
    execution_a, result_a = _execute(parts, selected_a, result=result_a)
    services.active_pass_number = 2
    services.orientation_by_version = {}
    services.request.task = "Evaluate subject B only"
    verifier = _prepare_verifier(parts)
    result_b = ResultPacket("build B", result={"subject": "B", "answer": "accepted"})
    plan_b = ExecutionPlan("use", "run_direct", handle="core.generated_project",
                           experiment={"action_id": "action.B", "action_occurrence_ref": "occurrence.B"})
    model_inputs = []

    def model(request):
        model_inputs.append(request)
        return {"verdict": "accept", "best_index": 0, "scores": [1.0],
                "notes": "Accepted B, which is the only supplied result.",
                "remaining_gaps": [], "advisory_findings": [],
                "new_requirement_proposals": []}

    services.model = model
    evaluation = verify_adaptive_results(AdaptiveVerificationRequest(
        PractitionerState(ProblemSpec("Evaluate B")), plan_b, (result_b,), {}), services)
    genuine_record_for_b = services.verification_records[-1]
    linked = _verify(parts, selected_a, execution_a, result_a, verifier,
                     genuine_record_for_b)
    return {
        "provider_calls": 0,
        "verification_verdict": evaluation.verdict,
        "verified_model_request": vars(model_inputs[0]),
        "result_a_digest": _digest(_result_payload(result_a)),
        "result_b_digest": _digest(_result_payload(result_b)),
        "result_digests_differ": _digest(_result_payload(result_a)) != _digest(_result_payload(result_b)),
        "genuine_evaluation_record_for_b": genuine_record_for_b,
        "credit_linked_to_a": linked,
        "a_local_verification_after_b_evaluation": services.stage_store.observations[0].outcome.local_verification,
    }


def integrate_rejected_result():
    services = SimpleNamespace(verification_records=[{
        "verdict": "repair", "notes": "Result was rejected."}])
    state = PractitionerState(ProblemSpec("retain accepted state"), facts={
        "last_result": {"objective": "previous accepted answer", "result": {"answer": "valid"}}},
        artifacts={"accepted.csv": "accepted.csv"})
    result = ResultPacket("rejected next attempt", result={"answer": "wrong"},
                          artifact_refs=("rejected.csv",), errors=("verification failed",))
    record = SimpleNamespace(results=[result], evaluation=EvaluationPacket("repair"))
    integrated = _adaptive_impls(services)["integrate_commit"](state, record)
    services.verification_records.append({"verdict": "accept", "notes": "New result C passed."})
    accepted_after_repair = _adaptive_impls(services)["integrate_commit"](
        integrated, SimpleNamespace(results=[ResultPacket(
            "new valid result C", result={"answer": "valid C"},
            artifact_refs=("new-accepted.csv",))], evaluation=EvaluationPacket("accept")))
    overflow = SimpleNamespace(results=[result], evaluation=EvaluationPacket("repair", best_index=7))
    error = ""
    try:
        _adaptive_impls(services)["integrate_commit"](state, overflow)
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
    return {
        "rejected_result_overwrites_last_result": integrated.facts["last_result"],
        "rejected_artifact_enters_state_artifacts": "rejected.csv" in integrated.artifacts,
        "artifacts": integrated.artifacts,
        "repair_record_is_preserved": integrated.facts["last_verification"],
        "original_state_unchanged": "rejected.csv" not in state.artifacts,
        "rejected_artifact_remains_after_later_accept": "rejected.csv" in accepted_after_repair.artifacts,
        "later_state_last_verification": accepted_after_repair.facts["last_verification"],
        "out_of_range_best_index": error,
    }


print(json.dumps({"cross_subject_evaluation": cross_subject_evaluation(),
                  "integrate_rejected_result": integrate_rejected_result()},
                 indent=2, default=str))
