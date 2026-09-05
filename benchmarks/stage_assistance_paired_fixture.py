"""Public-solve advisory-versus-fresh offline product-path fixture.
Both arms use the canonical gateway and one frozen task state. Advisory gets
hydrated prior material; fresh gets none. No live provider is contacted.
The fixture proves bounded wiring, not assistance quality or causal benefit."""
from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

if __package__:
    from . import stage_assistance_fixture_material as _fixture_support
else:
    import stage_assistance_fixture_material as _fixture_support
from loop_engine.code_nodes.solution_model_port import (
    FixtureModelExecutionRequest,
    fixture_model_execution,
)
from loop_engine.code_nodes.solve_runtime import (
    SolveRequest,
    solve_task,
    stage_assistance_source_state_digest,
)
from loop_engine.core.adaptive_practitioner import run_adaptive_practitioner
from loop_engine.core.adaptive_practitioner_records import (
    AdaptivePractitionerDependencies,
    AdaptivePractitionerRequest,
    NextActionDecision,
    StageAssistanceRuntimeBinding,
)
from loop_engine.core.context_budget import ContextBudgetPolicy
from loop_engine.core.run_history import RunHistory
from loop_engine.core.stage_evidence_records import StageRetrievalCandidate
from loop_engine.core.stage_store import StageStore
from loop_engine.templates.intake import TaskIntakeRequest, intake_task

TASK = "Create one verified text artifact from the supplied task."
CANDIDATE_REF_PREFIX = "prior-stage:fixture:verified-text-artifact"
EXPERIMENT_REF = "stage-experiment:fixture:advisory-versus-fresh:v1"
TRIAL_REF = (
    "stage-trial:fixture:CONTROL_MANIFEST_PRIOR_TEXT_MUST_NOT_ENTER_PROMPT:v1")


def _decision(mode: str, candidate_ref: str = "") -> dict:
    if mode == "advisory":
        return {
            "disposition": "USE",
            "selected_prior_refs": [candidate_ref],
            "reason": "The compatible prior supports the bounded artifact plan.",
        }
    return {
        "disposition": "START_FRESH",
        "selected_prior_refs": [],
        "reason": "No prior-stage candidate was retrieved or exposed.",
    }


def _answer(value: dict, mode: str, candidate_ref: str = "") -> str:
    return json.dumps({
        **value,
        "stage_assistance_decision": _decision(mode, candidate_ref),
    }, sort_keys=True, separators=(",", ":"))


def _answers(mode: str, candidate_refs: tuple[str, ...] = ()) -> tuple[str, ...]:
    orientation = {
        "original_task_ref": "replaced_by_runtime",
        "task_summary": "Create the requested output in a bounded project.",
        "ultimate_goal": "Return a verified output artifact.",
        "immediate_goal": "Build and test the artifact.",
        "current_state": "Only the task text is available.",
        "desired_state": "The output exists and its check passes.",
        "inputs": ["user task text"],
        "outputs": ["verified output file"],
        "operator_bundle": ["generate", "validate"],
        "response_contract": "artifact plus verification evidence",
        "decision_consumer": "the requesting user",
        "explicit_constraints": [],
        "inferred_constraints": [],
        "non_goals": [],
        "knowns": ["an output file is required"],
        "unknowns": [],
        "assumptions": [],
        "ambiguities": [],
        "delegated_choices": [],
        "safe_defaults": [],
        "blocking_questions": [],
        "research_questions": [],
        "subproblems": ["create project", "run check"],
        "dependencies": ["create before checking"],
        "parallel_candidates": [],
        "candidate_profiles": ["practitioner.solver"],
        "candidate_capabilities": ["core.generated_project"],
        "verification_obligations": [
            "test command passes", "output file exists"],
        "confidence_profile": {"overall": 0.95},
        "proposed_next_action": "Build the project.",
    }
    decision_value = {
        "action_kind": "BUILD_CAPABILITY",
        "goal": "Build and test the output.",
        "reason": "The requested output needs executable work.",
        "inputs": {},
        "expected_output": "A verified output file.",
        "required_capabilities": ["core.generated_project"],
        "permissions": ["workspace_write", "sandbox_command"],
        "budget": {"estimated_cost": 1.0, "risk": 0.1,
                   "reversibility": 1.0},
        "dependencies": [],
        "scheduling": "sequential",
        "verification": "Run the declared check and inspect the output.",
        "return_destination": "requesting user",
        "confidence": 0.9,
        "fallback": {"action_kind": "REPAIR"},
    }
    admitted_decision = NextActionDecision.from_mapping(decision_value)
    decision_id = "action:" + hashlib.sha256(json.dumps(
        admitted_decision.to_dict(), sort_keys=True, separators=(",", ":"),
        default=str).encode("utf-8")).hexdigest()[:20]
    how = {
        "action_id": decision_id,
        "how_mode": "generate",
        "act_mode": "run_dag",
        "capability_ref": "core.generated_project",
        "arguments": {},
        "steps": ["create", "run", "test"],
        "spawned_tasks": [],
        "rationale": "Generate a bounded project.",
    }
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "stage_assistance_fixture",
        "summary": "A bounded test project.",
        "files": [{"path": "main.py", "purpose": "Create the output.",
                   "acceptance": ["The file runs."]}],
        "commands": [{"argv": ["python", "main.py"],
                      "purpose": "Run the project.",
                      "timeout_seconds": 30}],
        "expected_artifacts": [{"path": "output.txt",
                                "media_type": "text/plain",
                                "minimum_bytes": 1}],
    }
    generated_file = {"path": "main.py", "content": "print('done')\n"}
    verification = {
        "verdict": "accept",
        "best_index": 0,
        "scores": [1.0],
        "notes": "Deterministic checks passed.",
        "remaining_gaps": [],
        "advisory_findings": [],
        "new_requirement_proposals": [],
    }
    route = {"route": "stop_success",
             "reason": "Requested output is verified."}
    values = (
        orientation,
        {"actions": [decision_value]},
        how,
        candidate,
        generated_file,
        verification,
        route,
    )
    refs = candidate_refs if mode == "advisory" else ("",) * len(values)
    if len(refs) != len(values):
        raise ValueError("the advisory fixture needs one candidate per stage")
    return tuple(_answer(value, mode, ref)
                 for value, ref in zip(values, refs))


def _project_fixture(request, _context):
    path = Path(request.workspace_root)
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("print('done')\n", encoding="utf-8")
    (path / "output.txt").write_text("done\n", encoding="utf-8")
    return {
        "record_type": "generated_project_execution/v1",
        "manifest_digest": request.manifest.digest,
        "workspace": {"workspace_id": "fixture", "backend_kind": "fixture",
                      "root": str(path)},
        "sandbox": {"backend_kind": "fixture", "network_reads": False},
        "writes": [],
        "commands": [{"purpose": "run", "ok": True, "exit_code": 0,
                      "stdout": "done\n", "stderr": "", "error_code": ""}],
        "artifacts": [{"path": "output.txt", "media_type": "text/plain",
                       "minimum_bytes": 1, "present": True,
                       "byte_count": 5, "digest": "a" * 64,
                       "error_code": "", "verified": True}],
        "snapshot": {"digest": "b" * 64, "file_count": 2,
                     "total_bytes": 19},
        "deterministic_checks_passed": True,
    }


def _candidate(semantic_signature: str,
               index: int) -> StageRetrievalCandidate:
    candidate_ref = f"{CANDIDATE_REF_PREFIX}:{index}"
    return StageRetrievalCandidate(
        candidate_ref,
        f"semantic-call:fixture:prior-occurrence:{index}",
        semantic_signature,
        "paired_fixture",
        evidence_refs=("run-history:fixture:prior",),
        material_differences=("different exact task occurrence",),
        contract_compatible=True,
        effect_compatible=True,
        authority_compatible=True,
        privacy_compatible=True,
        outcome_refs=("stage-outcome:fixture:locally-verified",),
    )


def _binding(mode: str, source_state_digest: str,
             candidates: tuple[StageRetrievalCandidate, ...] = ()
             ) -> StageAssistanceRuntimeBinding:
    return StageAssistanceRuntimeBinding(
        mode=mode,
        experiment_ref=EXPERIMENT_REF,
        trial_ref=TRIAL_REF,
        source_state_digest=source_state_digest,
        candidates=(candidates if mode == "advisory" else ()),
        materials=(
            tuple(_fixture_support.fixture_material(item, index)
                  for index, item in enumerate(candidates))
            if mode == "advisory"
            else ()
        ),
        control_manifest=_fixture_support.fixture_control_manifest(
            source_state_digest),
    )


def _run_arm(
    mode: str,
    root: Path,
    candidates: tuple[StageRetrievalCandidate, ...] = (),
    *,
    answers: tuple[str, ...] | None = None,
    context_budget: ContextBudgetPolicy | None = None,
) -> tuple[dict, list[dict], str]:
    progress: list[dict] = []
    prior_fragments = (
        CANDIDATE_REF_PREFIX,
        "prior_stage_summary",
        "response_program_candidate",
        "semantic-call:fixture:prior-occurrence",
    )
    execution = fixture_model_execution(
        FixtureModelExecutionRequest(
            answers=(
                answers
                if answers is not None
                else _answers(
                    mode, tuple(item.candidate_ref for item in candidates)
                )
            ),
            max_model_calls=7,
            required_prompt_fragments=(
                prior_fragments if mode == "advisory" else ()
            ),
            forbidden_prompt_fragments=((_fixture_support.CONTROL_HISTORY_PROBE,)
                + (prior_fragments if mode == "fresh" else ())),
        )
    )
    base_request = SolveRequest(
        intake_task(TaskIntakeRequest(text=TASK)),
        model_execution=execution,
        runs_dir=str(root),
        max_passes=1,
        allow_network_reads=False,
        allow_workspace_writes=True,
        allow_sandbox_commands=True,
        quiet_model_io=False,
        context_budget=(context_budget or ContextBudgetPolicy()),
        project_executor=_project_fixture,
        progress=progress.append,
    )
    source_state_digest = stage_assistance_source_state_digest(base_request)
    outcome = solve_task(
        replace(
            base_request,
            stage_assistance=_binding(mode, source_state_digest, candidates),
        )
    )
    result = outcome.to_dict()
    stage = outcome.intelligence["stage_assistance"]
    result.update(
        {
            "prior_stages_loaded": stage["prior_stages_loaded"],
            "stage_arms": stage["stage_arms"],
            "stages": stage["stages"],
            "stage_assistance_decisions": stage["decisions"],
            "stage_action_links": stage["action_links"],
            "stage_execution_links": stage["execution_links"],
            "stage_outcome_links": stage["outcome_links"],
            "stage_attribution_events": stage["attribution_boundaries"],
            "stage_evidence_degradations": stage["degradations"],
        }
    )
    return result, progress, source_state_digest


def _stage_events(history: RunHistory, kind: str) -> list:
    return [event for event in history.event_log
            if event.event_type == "custom"
            and event.detail.get("custom_kind") == kind]


def run_fixture(root: str) -> dict:
    """Run both public solve arms and return exact offline evidence."""
    target = Path(root).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    calibration, _calibration_progress, calibration_state = _run_arm(
        "fresh", target)
    calibration_history = RunHistory.load(
        str(target), calibration["run_id"])
    calibration_occurrences = _stage_events(
        calibration_history, "stage_occurrence_opened")
    candidates = tuple(
        _candidate(str(event.detail["semantic_stage_signature"]), index)
        for index, event in enumerate(calibration_occurrences))
    materials = tuple(_fixture_support.fixture_material(item, index)
                      for index, item in enumerate(candidates))
    advisory, advisory_progress, advisory_state = _run_arm(
        "advisory", target, candidates)
    # The comparison fresh arm now runs against a nonempty prior-stage store.
    # Its zero-query record therefore proves isolation rather than absence.
    fresh, fresh_progress, fresh_state = _run_arm("fresh", target)
    fresh_history = RunHistory.load(str(target), fresh["run_id"])
    if len({calibration_state, advisory_state, fresh_state}) != 1:
        raise RuntimeError("paired arms did not start from one frozen state")
    histories = {
        "advisory": RunHistory.load(str(target), advisory["run_id"]),
        "fresh": fresh_history,
    }
    store = StageStore(path=str(target / "stages.jsonl"))
    stored_rows = store.load()
    by_run = {
        mode: [item for item in store.observations
               if item.run_id == result["run_id"]]
        for mode, result in (("advisory", advisory), ("fresh", fresh))
    }
    progress = {"advisory": advisory_progress, "fresh": fresh_progress}
    prompts = {
        mode: [str(event.get("prompt_text") or "")
               for event in events
               if event.get("event_type") == "model.step.started"]
        for mode, events in progress.items()
    }
    exposure = {mode: _stage_events(history, "stage_assistance_exposure")
                for mode, history in histories.items()}
    decisions = {mode: _stage_events(history, "stage_assistance_decision")
                 for mode, history in histories.items()}
    occurrences = {mode: _stage_events(history, "stage_occurrence_opened")
                   for mode, history in histories.items()}
    local_outcomes = {
        mode: _stage_events(history, "stage_local_outcome_observed")
        for mode, history in histories.items()}
    attribution_boundaries = {
        mode: _stage_events(history, "stage_attribution_boundary")
        for mode, history in histories.items()}
    return {
        "record_type": "stage_assistance_public_solve_fixture/v2",
        "evidence_class": "offline_public_solve_mechanism_only_injected_provider",
        "limitations": [
            "injected responses do not establish live model quality",
            "equal fixture outcomes do not establish assistance benefit",
            "six of seven semantic stages retain unknown local contribution",
            "one separate fresh calibration run identifies stage signatures",
            "the request-wide trial label is not a canonical per-stage trial",
            "no causal assistance effect or canonical paired outcome is claimed",
            "full non-treatment variable and provider request freezing is unproven",
            "retrieval candidates are injected rather than queried from Run History",
        ],
        "source_state_digest": advisory_state,
        "candidate_refs": [item.candidate_ref for item in candidates],
        "candidate_records": [item.to_dict() for item in candidates],
        "material_records": [item.to_dict() for item in materials],
        "calibration": {
            "run_id": calibration["run_id"],
            "model_calls": int(calibration["model_calls"]),
            "stage_occurrences": len(calibration_occurrences),
            "run_history_intact": calibration_history.verify_chain()["intact"],
            "included_in_pair": False,
        },
        "arms": {
            mode: {
                "run_id": result["run_id"],
                "solved": bool(result["solved"]),
                "model_calls": int(result["model_calls"]),
                "prior_stages_loaded": int(result["prior_stages_loaded"]),
                "run_history_events": len(histories[mode].event_log),
                "run_history_intact": histories[mode].verify_chain()["intact"],
                "public_product_outcome_bound": bool(
                    result["run_history"].get("product_outcome_bound")
                ),
                "stage_occurrences": len(occurrences[mode]),
                "exposure_records": len(exposure[mode]),
                "assistance_decisions": len(decisions[mode]),
                "local_outcome_records": len(local_outcomes[mode]),
                "attribution_boundary_records": len(
                    attribution_boundaries[mode]),
                **_fixture_support.fixture_lineage_summary(result),
                "prompt_count": len(prompts[mode]),
                "candidate_ref_present_in_prompt": any(
                    CANDIDATE_REF_PREFIX in prompt for prompt in prompts[mode]),
                "prior_material_body_present_in_prompt": any(
                    "prior_stage_summary" in prompt
                    and "response_program_candidate" in prompt
                    and "known_local_outcome" in prompt
                    for prompt in prompts[mode]
                ),
                "source_occurrence_ref_present_in_prompt": any(
                    "semantic-call:fixture:prior-occurrence" in prompt
                    for prompt in prompts[mode]
                ),
                "stage_prior_context_present": any(
                    event.detail.get("stage_prior_context_present")
                    for event in exposure[mode]),
                "stage_prior_prompt_material_present": any(
                    event.detail.get("stage_prior_prompt_material_present")
                    for event in exposure[mode]
                ),
                "baseline_template_ids": sorted({
                    template_id for event in exposure[mode]
                    for template_id in event.detail.get(
                        "baseline_template_ids", ())}),
                "retrieval_performed": any(
                    event.detail.get("retrieval_performed")
                    for event in exposure[mode]),
                "exposed_prior_refs": sorted({
                    ref for event in exposure[mode]
                    for ref in event.detail.get("exposed_prior_refs", ())}),
                "exposed_material_refs": sorted({
                    ref for event in exposure[mode]
                    for ref in event.detail.get("exposed_material_refs", ())}),
                "exposed_material_digests": sorted({
                    ref for event in exposure[mode]
                    for ref in event.detail.get("exposed_material_digests", ())}),
                "exposure_refs": sorted({
                    str(event.detail.get("exposure_ref") or "")
                    for event in exposure[mode]
                    if event.detail.get("exposure_ref")}),
                "decision_exposure_refs": sorted({
                    str(event.detail.get("exposure_ref") or "")
                    for event in decisions[mode]
                    if event.detail.get("exposure_ref")}),
                "decision_packet_digests": sorted({
                    str(event.detail.get("packet_digest") or "")
                    for event in decisions[mode]
                    if event.detail.get("packet_digest")}),
                "exposure_packet_digests": sorted({
                    str(event.detail.get("packet_digest") or "")
                    for event in exposure[mode]
                    if event.detail.get("packet_digest")}),
                "decision_gateway_request_digests": sorted({
                    str(event.detail.get("gateway_request_digest") or "")
                    for event in decisions[mode]
                    if event.detail.get("gateway_request_digest")}),
                "exposure_gateway_request_digests": sorted({
                    str(event.detail.get("gateway_request_digest") or "")
                    for event in exposure[mode]
                    if event.detail.get("gateway_request_digest")}),
                "decision_provider_request_digests": sorted({
                    ref for event in decisions[mode]
                    for ref in event.detail.get("provider_request_digests", ())}),
                "exposure_provider_request_digests": sorted({
                    ref for event in exposure[mode]
                    for ref in event.detail.get("provider_request_digests", ())}),
                "admitted_response_digests": sorted({
                    str(event.detail.get("admitted_response_digest") or "")
                    for event in decisions[mode]
                    if event.detail.get("admitted_response_digest")}),
                "semantic_payload_digests": sorted({
                    str(event.detail.get("semantic_payload_digest") or "")
                    for event in decisions[mode]
                    if event.detail.get("semantic_payload_digest")}),
                "decision_dispositions": sorted({
                    str(event.detail.get("disposition") or "")
                    for event in decisions[mode]}),
                "source_state_digests": sorted({
                    str(event.detail.get("source_state_digest") or "")
                    for event in _stage_events(
                        histories[mode], "stage_retrieval_snapshot")}),
                "semantic_signatures": sorted({
                    str(event.detail.get("semantic_stage_signature") or "")
                    for event in occurrences[mode]}),
                "stage_credit_known": sum(
                    item.helped is not None for item in by_run[mode]),
                "routes": sorted({item.model_route for item in by_run[mode]}),
                "semantic_call_ids": sorted({
                    item.semantic_call_id for item in by_run[mode]}),
                "physical_attempt_loop_ids": sorted({
                    loop_id for item in by_run[mode]
                    for loop_id in item.model_attempt_loop_ids}),
                "semantic_call_correlation_complete": ({
                    item.semantic_call_id for item in by_run[mode]
                }.issubset({
                    str(event.detail.get("semantic_call_id") or "")
                    for event in histories[mode].event_log
                    if event.event_type == "model_invocation"})),
                "physical_attempts": sum(item.model_calls
                                         for item in by_run[mode]),
                "elapsed_seconds_known": all(
                    item.elapsed_seconds is not None
                    and item.elapsed_seconds >= 0
                    for item in by_run[mode]),
                "input_tokens": sum(item.input_tokens or 0
                                    for item in by_run[mode]),
                "output_tokens": sum(item.output_tokens or 0
                                     for item in by_run[mode]),
                "usage_complete": all(
                    item.input_tokens is not None
                    and item.output_tokens is not None
                    for item in by_run[mode]),
            }
            for mode, result in (("advisory", advisory), ("fresh", fresh))
        },
        "denominators": {
            "frozen_task_states": 1,
            "product_runs_total": 3,
            "calibration_runs": 1,
            "independent_arms": 2,
            "paired_logical_semantic_calls": sum(
                len(occurrences[mode]) for mode in histories),
            "logical_semantic_calls_total": (
                len(calibration_occurrences)
                + sum(len(occurrences[mode]) for mode in histories)),
            "paired_offline_fixture_physical_attempts": sum(
                sum(item.model_calls for item in by_run[mode])
                for mode in histories),
            "offline_fixture_physical_attempts_total": (
                int(calibration["model_calls"])
                + sum(sum(item.model_calls for item in by_run[mode])
                      for mode in histories)),
            "live_provider_calls": 0,
            "stored_stage_rows": stored_rows,
        },
        "occurrence_ids_disjoint": not (
            {event.detail.get("stage_occurrence_id")
             for event in occurrences["advisory"]}
            & {event.detail.get("stage_occurrence_id")
               for event in occurrences["fresh"]}),
    }


def self_test() -> dict:
    """Run adversarial paired-isolation checks with no live provider."""
    with tempfile.TemporaryDirectory(prefix="stage_assistance_pair_") as root:
        report = run_fixture(root)
        candidates = tuple(StageRetrievalCandidate.from_dict(item)
                           for item in report["candidate_records"])
        refs = tuple(item.candidate_ref for item in candidates)
        missing_answers = []
        for answer in _answers("advisory", refs):
            value = json.loads(answer)
            value.pop("stage_assistance_decision", None)
            missing_answers.append(json.dumps(
                value, sort_keys=True, separators=(",", ":")))
        missing, _progress, _state = _run_arm(
            "advisory", Path(root), candidates,
            answers=tuple(missing_answers))
        missing_history = RunHistory.load(root, missing["run_id"])
        missing_decision_events = _stage_events(
            missing_history, "stage_assistance_decision_missing")
        valid_missing_decisions = _stage_events(
            missing_history, "stage_assistance_decision")
        invalid_answers = []
        for answer in _answers("advisory", refs):
            value = json.loads(answer)
            value["stage_assistance_decision"]["selected_prior_refs"] = (
                value["stage_assistance_decision"]["selected_prior_refs"][0])
            invalid_answers.append(json.dumps(
                value, sort_keys=True, separators=(",", ":")))
        invalid, _progress, _state = _run_arm(
            "advisory", Path(root), candidates,
            answers=tuple(invalid_answers))
        invalid_history = RunHistory.load(root, invalid["run_id"])
        rejected_decision_events = _stage_events(
            invalid_history, "stage_assistance_decision_rejected")
        preflight, _progress, _state = _run_arm(
            "advisory", Path(root), candidates,
            context_budget=ContextBudgetPolicy(
                packet_estimated_tokens_max=1))
        preflight_history = RunHistory.load(root, preflight["run_id"])
        preflight_exposures = _stage_events(
            preflight_history, "stage_assistance_exposure")
        caller_prior = {}
        copied_request = AdaptivePractitionerRequest(
            TASK, runs_dir=root, max_passes=1,
            allow_network_reads=False,
            prior_region_evidence=caller_prior)
        copied_digest = copied_request.source_state_digest
        caller_prior["late_prior"] = "must not enter the frozen request"
        external_mutation_detached = (
            copied_request.source_state_digest == copied_digest
            and "late_prior" not in copied_request.prior_region_evidence)
        source_probe = Path(root) / "frozen-source-probe.txt"
        source_probe.write_text("arm-a", encoding="utf-8")
        source_request = AdaptivePractitionerRequest(
            TASK, source_refs=(str(source_probe),))
        source_digest = source_request.source_state_digest
        source_probe.write_text("arm-b-changed", encoding="utf-8")
        source_change_detected = (
            source_request.source_state_digest != source_digest)
        drift_request = replace(
            copied_request,
            stage_assistance=_binding(
                "advisory", copied_request.source_state_digest, candidates))
        drift_request.prior_region_evidence["late_prior"] = "changed"
        drift_execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=_answers("advisory", refs), max_model_calls=7))
        drift = run_adaptive_practitioner(
            drift_request, AdaptivePractitionerDependencies(
                drift_execution, project_executor=_project_fixture))
    advisory = report["arms"]["advisory"]
    fresh = report["arms"]["fresh"]

    def refused(action) -> bool:
        try:
            action()
        except ValueError:
            return True
        return False

    unchecked = StageRetrievalCandidate(
        "prior-stage:unchecked", "semantic-call:unchecked",
        "semantic-stage:unchecked", "fixture",
        contract_compatible=True, effect_compatible=None,
        authority_compatible=True, privacy_compatible=True)
    base = AdaptivePractitionerRequest(
        TASK, max_passes=1, allow_network_reads=False)
    checks = [
        ("both_arms_share_one_source_state_and_control_manifest",
         report["denominators"]["frozen_task_states"] == 1
         and advisory["control_manifest_ref"]
         == fresh["control_manifest_ref"]
         and advisory["control_set_digest"] == fresh["control_set_digest"]
         and advisory["control_evidence_class"] == "mechanism_only"
         and len(advisory["control_blocking_unknowns"]) == 6),
        ("arms_use_independent_occurrence_ids",
         report["occurrence_ids_disjoint"]),
        ("advisory_refuses_unknown_hard_compatibility",
         refused(lambda: _binding(
             "advisory", base.source_state_digest, (unchecked,)))),
        ("advisory_refuses_reference_only_or_mismatched_hydration",
         refused(lambda: replace(_binding(
             "advisory", base.source_state_digest, (candidates[0],)),
             materials=()))
         and refused(lambda: replace(_binding(
             "advisory", base.source_state_digest, (candidates[0],)),
             materials=(replace(_fixture_support.fixture_material(
                 candidates[0], 0),
                 semantic_signature="stage:sha256:mismatched"),)))),
        ("fresh_refuses_candidates_and_mismatched_state",
         refused(lambda: replace(_binding(
             "fresh", base.source_state_digest),
             candidates=(_candidate("stage:test", 99),)))
         and refused(lambda: replace(_binding(
             "fresh", base.source_state_digest),
             materials=(_fixture_support.fixture_material(candidates[0], 0),)))
         and refused(lambda: replace(
             base, stage_assistance=_binding("fresh", "f" * 64)))),
        ("both_arms_traverse_the_public_solve_path",
         advisory["solved"] and fresh["solved"]
         and advisory["stage_occurrences"] == 7
         and fresh["stage_occurrences"] == 7
         and advisory["public_product_outcome_bound"]
         and fresh["public_product_outcome_bound"]),
        ("comparison_fresh_arm_skips_a_nonempty_prior_store",
         fresh["prior_stages_loaded"] >= 14
         and not fresh["retrieval_performed"]),
        ("advisory_prompt_contains_hydrated_prior_material_not_only_its_ref",
         advisory["candidate_ref_present_in_prompt"]
         and advisory["prior_material_body_present_in_prompt"]
         and advisory["source_occurrence_ref_present_in_prompt"]
         and advisory["stage_prior_context_present"]
         and advisory["stage_prior_prompt_material_present"]
         and advisory["exposed_prior_refs"] == report["candidate_refs"]
         and advisory["exposed_material_refs"]
             == sorted(item["material_ref"] for item in report["material_records"])
         and advisory["exposed_material_digests"]
             == sorted(item["content_digest"] for item in report["material_records"])
         and len(report["candidate_refs"]) == 7),
        ("fresh_prompt_context_template_and_retrieval_are_prior_clean",
         not fresh["candidate_ref_present_in_prompt"]
         and not fresh["prior_material_body_present_in_prompt"]
         and not fresh["source_occurrence_ref_present_in_prompt"]
         and not fresh["stage_prior_context_present"]
         and not fresh["stage_prior_prompt_material_present"]
         and not fresh["retrieval_performed"]
         and fresh["exposed_prior_refs"] == []
         and fresh["exposed_material_refs"] == []
         and fresh["exposed_material_digests"] == []
         and fresh["baseline_template_ids"]
         == advisory["baseline_template_ids"]),
        ("paired_arms_share_state_and_semantic_regions",
         advisory["source_state_digests"] == [report["source_state_digest"]]
         and fresh["source_state_digests"] == [report["source_state_digest"]]
         and advisory["semantic_signatures"]
         == fresh["semantic_signatures"]),
        ("model_assistance_dispositions_are_recorded_per_arm",
         advisory["decision_dispositions"] == ["USE"]
         and fresh["decision_dispositions"] == ["START_FRESH"]
         and advisory["assistance_decisions"] == 7
         and fresh["assistance_decisions"] == 7),
        ("every_decision_binds_the_exact_physical_exposure_and_packet",
         advisory["decision_exposure_refs"] == advisory["exposure_refs"]
         and fresh["decision_exposure_refs"] == fresh["exposure_refs"]
         and advisory["decision_packet_digests"]
             == advisory["exposure_packet_digests"]
         and fresh["decision_packet_digests"]
             == fresh["exposure_packet_digests"]
         and advisory["decision_gateway_request_digests"]
             == advisory["exposure_gateway_request_digests"]
         and fresh["decision_gateway_request_digests"]
             == fresh["exposure_gateway_request_digests"]
         and advisory["decision_provider_request_digests"]
             == advisory["exposure_provider_request_digests"]
         and fresh["decision_provider_request_digests"]
             == fresh["exposure_provider_request_digests"]
         and len(advisory["admitted_response_digests"]) == 7
         and len(fresh["admitted_response_digests"]) == 7
         and len(advisory["semantic_payload_digests"]) == 7
         and len(fresh["semantic_payload_digests"]) == 7),
        ("missing_active_decisions_cannot_reach_downstream_success",
         not missing["solved"] and missing_decision_events
         and not valid_missing_decisions),
        ("ill_typed_active_decisions_cannot_reach_downstream_success",
         not invalid["solved"] and rejected_decision_events
         and not _stage_events(invalid_history, "stage_assistance_decision")),
        ("no_physical_attempt_means_no_exposure_record",
         not preflight["solved"] and preflight["model_calls"] == 0
         and not preflight_exposures),
        ("caller_owned_control_mappings_are_detached_on_construction",
         external_mutation_detached),
        ("ordinary_local_source_replacement_changes_the_frozen_digest",
         source_change_detected),
        ("execution_refuses_a_frozen_binding_changed_after_validation",
         not drift["solved"] and drift["model_calls"] == 0
         and "frozen state changed" in str(drift.get("failure", ""))),
        ("only_the_exact_action_producing_stage_receives_direct_local_credit",
         _fixture_support.fixture_lineage_is_complete(advisory)
         and _fixture_support.fixture_lineage_is_complete(fresh)),
        ("pass_verdicts_record_an_attribution_boundary",
         advisory["attribution_boundary_records"] == 1
         and fresh["attribution_boundary_records"] == 1),
        ("real_fixture_route_attempt_and_usage_values_are_joined",
         advisory["routes"] == ["fixture.route"]
         and fresh["routes"] == ["fixture.route"]
         and advisory["physical_attempts"] == 7
         and fresh["physical_attempts"] == 7
         and len(advisory["semantic_call_ids"]) == 7
         and len(fresh["semantic_call_ids"]) == 7
         and len(advisory["physical_attempt_loop_ids"]) == 7
         and len(fresh["physical_attempt_loop_ids"]) == 7
         and advisory["semantic_call_correlation_complete"]
         and fresh["semantic_call_correlation_complete"]
         and advisory["elapsed_seconds_known"]
         and fresh["elapsed_seconds_known"]
         and advisory["input_tokens"] == 14
         and advisory["output_tokens"] == 21
         and fresh["input_tokens"] == 14
         and fresh["output_tokens"] == 21
         and advisory["usage_complete"] and fresh["usage_complete"]),
        ("run_histories_are_intact",
         advisory["run_history_intact"] and fresh["run_history_intact"]
         and report["calibration"]["run_history_intact"]),
        ("denominators_are_exact",
         report["denominators"] == {
             "frozen_task_states": 1,
             "product_runs_total": 3,
             "calibration_runs": 1,
             "independent_arms": 2,
             "paired_logical_semantic_calls": 14,
             "logical_semantic_calls_total": 21,
             "paired_offline_fixture_physical_attempts": 14,
             "offline_fixture_physical_attempts_total": 21,
             "live_provider_calls": 0,
             "stored_stage_rows": 21,
         }),
    ]
    tests = [{"test": name, "passed": bool(passed)}
             for name, passed in checks]
    return {
        "record_type": "stage_assistance_product_plumbing_fixture_test/v1",
        "tests": tests,
        "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests),
        "report": report,
    }


if __name__ == "__main__":
    result = self_test()
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)
