"""Focused offline checks for the adaptive Practitioner.

The checks exercise one complete typed model-driven pass with two equivalent
task phrasings. Provider behavior is an offline contract fixture only.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from .adaptive_practitioner import run_adaptive_practitioner
from .adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest,
    NextActionDecision, TaskOrientationResult)
from .adaptive_practitioner_orientation import (
    orientation_policy_conflicts, orientation_policy_findings)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest, resolve_stall_with_panel)
from .adaptive_practitioner_supervision import detect_stall
from .independent_verification import IndependentVerificationPolicy
from ..loop.kernel import PractitionerState, ProblemSpec

def run_checks() -> dict:
    """Prove one engine handles paraphrased and unrelated tasks."""
    from .adaptive_practitioner_acceptance_checks import _action_vector
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest, fixture_model_execution)

    orientation = json.dumps({
        "original_task_ref": "replaced_by_runtime",
        "task_summary": "Create the requested output in a bounded project.",
        "ultimate_goal": "Return a verified output artifact.",
        "immediate_goal": "Build and test the artifact.",
        "current_state": "Only the task text is available.",
        "desired_state": "The output exists and its test passes.",
        "inputs": ["user task text"], "outputs": ["verified output file"],
        "operator_bundle": ["generate", "validate"],
        "response_contract": "artifact plus verification evidence",
        "decision_consumer": "the requesting user",
        "explicit_constraints": [], "inferred_constraints": [],
        "non_goals": [], "knowns": ["an output file is required"],
        "unknowns": [], "assumptions": [], "ambiguities": [],
        "delegated_choices": [], "safe_defaults": [],
        "blocking_questions": [], "research_questions": [],
        "subproblems": ["create project", "run test"],
        "dependencies": ["create before test"],
        "parallel_candidates": [],
        "candidate_profiles": ["practitioner.solver"],
        "candidate_capabilities": ["core.generated_project"],
        "verification_obligations": [
            "test command passes", "output file exists"],
        "confidence_profile": {"overall": 0.95},
        "proposed_next_action": "Build the project."})
    decision_value = {
        "action_kind": "BUILD_CAPABILITY",
        "goal": "Build and test the output.",
        "reason": "The requested output needs executable work.",
        "inputs": {}, "expected_output": "A verified output file.",
        "required_capabilities": ["core.generated_project"],
        "permissions": ["workspace_write", "sandbox_command"],
        "budget": {"estimated_cost": 1.0, "risk": 0.1,
                   "reversibility": 1.0},
        "dependencies": [], "scheduling": "sequential",
        "verification": "Run the declared test and inspect the output.",
        "return_destination": "requesting user", "confidence": 0.9,
        "fallback": {"action_kind": "REPAIR"}}
    decision_record = NextActionDecision.from_mapping(decision_value)
    import hashlib
    decision_id = "action:" + hashlib.sha256(json.dumps(
        decision_record.to_dict(), sort_keys=True, separators=(",", ":"),
        default=str).encode()).hexdigest()[:20]
    decision = json.dumps({"actions": [decision_value]})
    how = json.dumps({
        "action_id": decision_id, "how_mode": "generate",
        "act_mode": "run_dag", "capability_ref": "core.generated_project",
        "arguments": {}, "steps": ["create", "run", "test"],
        "spawned_tasks": [], "rationale": "Generate a bounded project."})
    candidate = json.dumps({
        "record_type": "generated_project_candidate/v1",
        "project_id": "adaptive_test", "summary": "A bounded test project.",
        "files": [{"path": "main.py", "purpose": "Create the output.",
                   "acceptance": ["The file runs."]}],
        "commands": [{"argv": ["python", "main.py"],
                      "purpose": "Run the project.", "timeout_seconds": 30}],
        "expected_artifacts": [{"path": "output.txt",
                                "media_type": "text/plain",
                                "minimum_bytes": 1}]})
    generated_file = json.dumps({
        "path": "main.py", "content": "print('done')\n"})
    verification = json.dumps({
        "verdict": "accept", "best_index": 0, "scores": [1.0],
        "notes": "Deterministic checks passed.", "remaining_gaps": [],
        "advisory_findings": [], "new_requirement_proposals": [],
        "action_vector": _action_vector()})
    route = json.dumps({
        "route": "stop_success", "reason": "Requested output is verified."})

    def project_fixture(request, context):
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
            "writes": [], "commands": [{"purpose": "run", "ok": True,
                                           "exit_code": 0, "stdout": "done\n",
                                           "stderr": "", "error_code": ""}],
            "artifacts": [{"path": "output.txt", "media_type": "text/plain",
                           "minimum_bytes": 1, "present": True,
                           "byte_count": 5, "digest": "a" * 64,
                           "error_code": "", "verified": True}],
            "snapshot": {"digest": "b" * 64, "file_count": 2,
                         "total_bytes": 19},
            "deterministic_checks_passed": True,
        }

    tasks = (
        "Create a small verified text artifact from this request.",
        "Crea un artefacto de texto pequeno y verificalo.",
    )
    results = []
    import tempfile
    for index, task in enumerate(tasks):
        with tempfile.TemporaryDirectory() as root:
            execution = fixture_model_execution(FixtureModelExecutionRequest(
                answers=(orientation, decision, how, candidate,
                         generated_file, verification, route),
                max_model_calls=7))
            result = run_adaptive_practitioner(
                AdaptivePractitionerRequest(
                    task, runs_dir=root, max_passes=1,
                    allow_network_reads=False,
                    independent_verification_policy=IndependentVerificationPolicy(
                        required=False)),
                AdaptivePractitionerDependencies(
                    execution, project_executor=project_fixture))
            results.append({
                "test": f"same_practitioner_solves_task_wording_{index + 1}",
                "passed": result["solved"] and result["model_calls"] == 7
                and len(result["loop_details"]) >= 7,
                "detail": result["run_id"],
            })
    with tempfile.TemporaryDirectory() as root:
        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=(orientation, decision, how, candidate,
                     generated_file, verification, route),
            max_model_calls=7))
        inline_pack = run_adaptive_practitioner(
            AdaptivePractitionerRequest(
                "Create the report from the attachment text captured here.",
                mode="non_deterministic", runs_dir=root, max_passes=1,
                source_kind="task_pack", source_refs=(),
                allow_source_materialization_to_model=True,
                allow_network_reads=False,
                independent_verification_policy=IndependentVerificationPolicy(
                    required=False)),
            AdaptivePractitionerDependencies(
                execution, project_executor=project_fixture))
        results.append({
            "test": "inline_task_pack_reaches_project_execution_without_source_selection",
            "passed": (inline_pack["solved"]
                       and len(inline_pack["project_attempts"]) == 1
                       and inline_pack["source_inspections"] == []),
            "detail": inline_pack["run_id"],
        })
    # A request may declare the supervision policy the kernel applies to its
    # passes, so a campaign's ceiling is a configuration level; the outcome
    # names the policy that applied, declared or the repository default.
    from ..loop.supervision_policy import SupervisionPolicy
    from .adaptive_practitioner_validation import AdaptivePractitionerError
    declared_policy = SupervisionPolicy(unaccepted_passes_before_stop=2,
                                        non_progress_passes_before_escalation=2)
    with tempfile.TemporaryDirectory() as root:
        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=(orientation, decision, how, candidate,
                     generated_file, verification, route),
            max_model_calls=7))
        declared_run = run_adaptive_practitioner(
            AdaptivePractitionerRequest(
                tasks[0], runs_dir=root, max_passes=1, allow_network_reads=False,
                supervision=declared_policy,
                independent_verification_policy=IndependentVerificationPolicy(required=False)),
            AdaptivePractitionerDependencies(execution, project_executor=project_fixture))
    refused_policy = False
    try:
        AdaptivePractitionerRequest(tasks[0], supervision="strict")
    except AdaptivePractitionerError:
        refused_policy = True
    results.append({
        "test": "a_request_declares_the_supervision_policy_and_the_outcome_names_it",
        "passed": declared_run["supervision_policy"]["unaccepted_passes_before_stop"] == 2
        and declared_run["supervision_policy"]["policy_id"] == declared_policy.policy_id
        and declared_run["supervision_policy"]["declared"] is True
        and results[0]["passed"]
        and result["supervision_policy"] == {"policy_id": "loop.supervision", "declared": False}
        and AdaptivePractitionerRequest(tasks[0], supervision=declared_policy).source_state_digest
        != AdaptivePractitionerRequest(tasks[0]).source_state_digest
        and refused_policy,
        "detail": str(declared_run.get("supervision_policy"))[:120],
    })
    from . import adaptive_practitioner as implementation
    source = Path(implementation.__file__).read_text(encoding="utf-8").lower()
    results.append({
        "test": "adaptive_practitioner_has_no_example_specific_route",
        "passed": not any(value in source for value in (
            "openml", "iris", "boosted-tree", "target_column=", "kaggle")),
        "detail": "source contains universal contracts and capability refs only",
    })
    meta_orientation = json.loads(orientation)
    meta_orientation.update({
        "immediate_goal": "Return TaskOrientationResult version 1.",
        "unknowns": ["Whether the runtime permits a direct write."],
        "ambiguities": [{
            "subject": "runtime write capability", "state": "UNKNOWN",
            "reason": "The runtime owns the capability registry."}],
        "blocking_questions": [
            "Does the runtime permit a direct workspace write?"],
        "proposed_next_action": "ASK_USER",
    })
    meta_findings = orientation_policy_findings(
        TaskOrientationResult.from_mapping(meta_orientation), "autonomous")
    results.append({
        "test": "orientation_cannot_make_its_protocol_or_runtime_a_user_blocker",
        "passed": (any("immediate goal" in item for item in meta_findings)
                   and any("USER_CLARIFICATION_REQUIRED" in item
                           for item in meta_findings)),
        "detail": str(meta_findings),
    })
    # Repair asks for exactly the fields a conflict names, and a carried
    # orientation withholds only those fields, so the names must be exact.
    meta_conflicts = orientation_policy_conflicts(
        TaskOrientationResult.from_mapping(meta_orientation), "autonomous")
    protocol_obligation = (
        "Validate the TaskOrientationResult against the inline schema.")
    mixed_obligations = json.loads(orientation)
    mixed_obligations["verification_obligations"] = [
        "test command passes", protocol_obligation]
    mixed_conflicts = orientation_policy_conflicts(
        TaskOrientationResult.from_mapping(mixed_obligations), "autonomous")
    results.append({
        "test": "orientation_conflicts_name_their_fields_and_protocol_entries",
        "passed": (
            any(item.fields == ("immediate_goal",) for item in meta_conflicts)
            and all("blocking_questions" in item.fields
                    for item in meta_conflicts
                    if item.fields != ("immediate_goal",))
            and [(item.fields, item.protocol_items)
                 for item in mixed_conflicts] == [
                (("verification_obligations",), (protocol_obligation,))]),
        "detail": str([(item.fields, item.protocol_items)
                       for item in (*meta_conflicts, *mixed_conflicts)]),
    })
    supervised = SimpleNamespace(
        web_results=[], source_inspections=[], project_attempts=[],
        action_history=[], verification_records=[], progress_snapshots=[],
        unchanged_progress_snapshots=0, supervision_findings=[],
        recovery_rounds=0, active_recovery_directive=None)
    state = PractitionerState(ProblemSpec("qualify progress breakout"))
    signals = [detect_stall(supervised, state) for _item in range(2)]
    results.append({
        "test": "unchanged_task_state_triggers_diagnosis_not_terminal_route",
        "passed": signals[0] is None and signals[1] is not None
        and signals[1]["code"] == "RECOVERY_DIAGNOSIS_REQUIRED"
        and bool(supervised.supervision_findings),
        "detail": str([item is not None for item in signals]),
    })
    supervised.web_results.append({"sha256": "new-evidence"})
    signal = detect_stall(supervised, state)
    results.append({
        "test": "new_evidence_clears_exact_repeat_without_a_numeric_cap",
        "passed": signal is None,
        "detail": "novel evidence may continue regardless of attempt count",
    })
    panel_answers = iter((
        {
            "diagnosis_id": "diagnosis-1",
            "root_causes": [{
                "cause": "The same method is repeating.",
                "evidence_refs": ["run:pass-3"], "confidence": 0.9}],
            "failed_strategy": "Repeated research did not change acceptance.",
            "missing_context": [], "invalid_assumptions": [],
            "recommended_change_types": ["mutate", "reframe"],
        },
        {"proposals": [{
            "proposal_id": "proposal-a", "change_kind": "mutate",
            "route": "repair", "directive": "Mutate the failed project.",
            "required_capabilities": ["core.generated_project"],
            "forbidden_action_kinds": ["RESEARCH_SOURCE"],
            "expected_progress": "A second project attempt exists.",
            "risks": ["rebuild risk"],
            "confidence": 0.8,
        }, {
            "proposal_id": "proposal-b", "change_kind": "reframe",
            "route": "reframe", "directive": "Reframe the failed criteria.",
            "required_capabilities": [],
            "forbidden_action_kinds": ["RESEARCH_SOURCE"],
            "expected_progress": "Blocking gaps map to the user contract.",
            "risks": ["criterion drift"],
            "confidence": 0.7,
        }]},
        {
            "selected_proposal_id": "proposal-a", "route": "repair",
            "reason": "The executable mutation best addresses the cause.",
            "directive": "Mutate and rerun the failed project.",
            "required_capabilities": ["core.generated_project"],
            "forbidden_action_kinds": ["RESEARCH_SOURCE"],
            "expected_progress": "A second project attempt exists.",
            "confidence": 0.9,
        },
    ))

    class PanelServices:
        def __init__(self):
            self.steps = []
            self.recovery_directives = []
            self.active_recovery_directive = None
            self.recovery_rounds = 0
            self.unchanged_progress_snapshots = 3
            self.web_results = []

        def model(self, request):
            self.steps.append(request.step_id)
            return next(panel_answers)

        @staticmethod
        def available_capabilities():
            return ({"capability_ref": "core.generated_project"},)

    panel_services = PanelServices()
    directive = resolve_stall_with_panel(RecoveryPanelRequest(
        {"code": "RECOVERY_DIAGNOSIS_REQUIRED"}, {}, 3), panel_services)
    results.append({
        "test": "stall_runs_diagnosis_competing_mutations_and_adjudication",
        "passed": panel_services.steps == [
            "diagnose_stall", "propose_recovery", "adjudicate_recovery"]
        and directive["route"] == "repair"
        and directive["required_capabilities"]
            == ["core.generated_project"],
        "detail": str(panel_services.steps),
    })
    passed = sum(item["passed"] for item in results)
    return {
        "record_type": "adaptive_practitioner_test/v1",
        "tests": results, "passed": passed, "total": len(results),
        "all_passed": passed == len(results),
    }


def complete_checks() -> dict:
    """Run focused task-agnostic adaptive Practitioner checks."""
    from .adaptive_practitioner_acceptance_checks import (
        run_checks as run_acceptance_checks,
    )
    focused = run_checks()
    acceptance = run_acceptance_checks()
    from .practitioner_contract_guards import contract_guard_checks
    tests = [*focused["tests"], *acceptance["tests"],
             *contract_guard_checks()]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "adaptive_practitioner_complete_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
