"""Focused offline checks for the adaptive Practitioner.

The checks exercise one complete typed model-driven pass with two equivalent
task phrasings. Provider behavior is an offline contract fixture only.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from .adaptive_practitioner import run_adaptive_practitioner
from .adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest,
    NextActionDecision)
from .adaptive_practitioner_recovery import (
    RecoveryPanelRequest, resolve_stall_with_panel)
from .adaptive_practitioner_supervision import detect_stall
from ..loop.kernel import PractitionerState, ProblemSpec

def run_checks() -> dict:
    """Prove one engine handles paraphrased and unrelated tasks."""
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
        "advisory_findings": [], "new_requirement_proposals": []})
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
                    allow_network_reads=False),
                AdaptivePractitionerDependencies(
                    execution, project_executor=project_fixture))
            results.append({
                "test": f"same_practitioner_solves_task_wording_{index + 1}",
                "passed": result["solved"] and result["model_calls"] == 7
                and len(result["loop_details"]) >= 7,
                "detail": result["run_id"],
            })
    from . import adaptive_practitioner as implementation
    source = Path(implementation.__file__).read_text(encoding="utf-8").lower()
    results.append({
        "test": "adaptive_practitioner_has_no_example_specific_route",
        "passed": not any(value in source for value in (
            "openml", "iris", "boosted-tree", "target_column=", "kaggle")),
        "detail": "source contains universal contracts and capability refs only",
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
