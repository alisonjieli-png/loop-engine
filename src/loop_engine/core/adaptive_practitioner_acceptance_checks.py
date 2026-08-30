"""Anti-overfitting and completion checks for the adaptive Practitioner.

Task strings and scripted model outputs are test data. They are deliberately
kept outside the generic solver modules scanned by this suite.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from .adaptive_practitioner import run_adaptive_practitioner
from .adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest,
    NextActionDecision)


def _orientation(**changes) -> dict:
    value = {
        "original_task_ref": "replaced_by_runtime",
        "task_summary": "Create and verify the requested result.",
        "ultimate_goal": "Return the requested verified result.",
        "immediate_goal": "Build and test the result.",
        "current_state": "Only the task text is available.",
        "desired_state": "The requested result exists and passes verification.",
        "inputs": ["user task text"], "outputs": ["verified result artifact"],
        "operator_bundle": ["generate", "validate"],
        "response_contract": "artifact plus verification evidence",
        "decision_consumer": "requesting user",
        "explicit_constraints": [], "inferred_constraints": [],
        "non_goals": [], "knowns": ["a verified result is required"],
        "unknowns": [], "assumptions": [], "ambiguities": [],
        "delegated_choices": [], "safe_defaults": [],
        "blocking_questions": [], "research_questions": [],
        "subproblems": ["construct result", "verify result"],
        "dependencies": ["construct before verify"],
        "parallel_candidates": [],
        "candidate_profiles": ["practitioner.solver"],
        "candidate_capabilities": ["core.generated_project"],
        "verification_obligations": [
            "execution command passes", "expected artifact exists"],
        "confidence_profile": {"overall": 0.95},
        "proposed_next_action": "Build the project.",
    }
    value.update(changes)
    return value


def _decision(action_kind="BUILD_CAPABILITY", **changes) -> dict:
    capability = ([] if action_kind in (
        "ASK_USER", "REQUEST_AUTHORITY", "RETURN_RESULT", "ABSTAIN", "STOP")
        else ["core.generated_project"])
    permissions = ([] if not capability
                   else ["workspace_write", "sandbox_command"])
    value = {
        "action_kind": action_kind,
        "goal": "Produce the next verified result.",
        "reason": "The acceptance contract still requires an output.",
        "inputs": {}, "expected_output": "A verified result.",
        "required_capabilities": capability,
        "permissions": permissions,
        "budget": {"estimated_cost": 1.0, "risk": 0.1,
                   "reversibility": 1.0},
        "dependencies": [], "scheduling": "sequential",
        "verification": "Run tests and inspect expected artifacts.",
        "return_destination": "requesting user", "confidence": 0.9,
        "fallback": {"action_kind": "REPAIR"},
    }
    value.update(changes)
    return value


def _decision_id(value: dict) -> str:
    record = NextActionDecision.from_mapping(value)
    return "action:" + hashlib.sha256(json.dumps(
        record.to_dict(), sort_keys=True, separators=(",", ":"),
        default=str).encode()).hexdigest()[:20]


def _success_answers(orientation=None, decision=None) -> tuple[str, ...]:
    orientation = orientation or _orientation()
    decision = decision or _decision()
    action_id = _decision_id(decision)
    how = {
        "action_id": action_id, "how_mode": "generate",
        "act_mode": "run_dag", "capability_ref": "core.generated_project",
        "arguments": {}, "steps": ["create", "run", "test"],
        "spawned_tasks": [], "rationale": "Generate a bounded project.",
    }
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "acceptance_test",
        "summary": "A bounded acceptance-test project.",
        "files": [{"path": "main.py", "purpose": "Create the output.",
                   "acceptance": ["The file runs."]}],
        "commands": [{"argv": ["python", "main.py"],
                      "purpose": "Run the project.", "timeout_seconds": 30}],
        "expected_artifacts": [{"path": "main.py",
                                "media_type": "text/x-python",
                                "minimum_bytes": 1}],
    }
    verification = {
        "verdict": "accept", "best_index": 0, "scores": [1.0],
        "notes": "Deterministic checks passed.", "remaining_gaps": [],
        "advisory_findings": [], "new_requirement_proposals": [],
    }
    route = {"route": "stop_success", "reason": "Result is verified."}
    return tuple(json.dumps(item) for item in (
        orientation, {"actions": [decision]}, how, candidate,
        {"path": "main.py", "content": "print('done')\n"},
        verification, route))


def _gap_answers(task_kind="unknown") -> tuple[str, ...]:
    orientation = _orientation(
        task_summary=f"Orient an unseen {task_kind} task.",
        candidate_capabilities=[],
        unknowns=["no compatible execution capability is registered"],
        proposed_next_action="Return an honest capability gap.")
    decision = _decision(
        "ABSTAIN", goal="Return a capability gap.",
        reason="No verified capability can produce the requested result.",
        expected_output="A typed capability gap.")
    verification = {
        "verdict": "stop", "best_index": 0, "scores": [0.0],
        "notes": "No artifact was produced.",
        "remaining_gaps": [{
            "criterion_ref": "criterion:0",
            "gap": "execution capability unavailable"}],
        "advisory_findings": [], "new_requirement_proposals": [],
    }
    route = {"route": "stop_unprofitable",
             "reason": "No verified capability is available."}
    return tuple(json.dumps(item) for item in (
        orientation, {"actions": [decision]}, verification, route))


def _project_fixture(request, context):
    path = Path(request.workspace_root)
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.py").write_text("print('done')\n", encoding="utf-8")
    return {
        "record_type": "generated_project_execution/v1",
        "manifest_digest": request.manifest.digest,
        "workspace": {"workspace_id": "fixture", "backend_kind": "fixture",
                      "root": str(path)},
        "sandbox": {"backend_kind": "fixture", "network_reads": False},
        "writes": [], "commands": [{
            "purpose": "run", "ok": True, "exit_code": 0,
            "stdout": "done\n", "stderr": "", "error_code": ""}],
        "artifacts": [{
            "path": "main.py", "media_type": "text/x-python",
            "minimum_bytes": 1, "present": True, "byte_count": 14,
            "digest": "a" * 64, "error_code": "", "verified": True}],
        "snapshot": {"digest": "b" * 64, "file_count": 1,
                     "total_bytes": 14},
        "deterministic_checks_passed": True,
    }


def _run(task: str, answers: tuple[str, ...], root: str,
         mode="hybrid", interaction_mode="autonomous") -> dict:
    execution = fixture_model_execution(FixtureModelExecutionRequest(
        answers=answers, max_model_calls=len(answers)))
    return run_adaptive_practitioner(
        AdaptivePractitionerRequest(
            task, mode=mode, runs_dir=root, max_passes=1,
            interaction_mode=interaction_mode,
            allow_network_reads=False),
        AdaptivePractitionerDependencies(
            execution, project_executor=_project_fixture))


def _paraphrases() -> tuple[str, ...]:
    verbs = ("Create", "Build", "Produce", "Make", "Generate",
             "Construct", "Prepare", "Develop", "Assemble", "Deliver")
    endings = (
        "a tested text artifact.",
        "a text artifact and verify it.",
        "one verified text output.",
        "a text result whose test passes.",
        "a working text artifact with evidence.",
    )
    return tuple(f"{verb} {ending[0].lower() + ending[1:]}"
                 for verb in verbs for ending in endings)


def _hardcoding_scan() -> tuple[bool, str]:
    root = Path(__file__).parent
    generic = tuple(root / name for name in (
        "adaptive_practitioner.py", "adaptive_practitioner_records.py",
        "adaptive_practitioner_capabilities.py", "generated_project.py",
        "practitioner_context.py", "web_fetch.py", "web_search.py")) + (
            root.parent / "code_nodes" / "solve_runtime.py",)
    prohibited = (
        "download an authorized public dataset",
        "linear model", "boosted-tree", "target_column=", "openml", "iris",
        "kaggle", "ken burns", "pose-rig", "pdf and html reports")
    findings = []
    for path in generic:
        text = path.read_text(encoding="utf-8").split(
            "def self_test()", 1)[0].lower()
        findings.extend(f"{path.name}:{term}"
                        for term in prohibited if term in text)
    return not findings, ", ".join(findings)


def run_checks() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory() as root:
        paraphrases = _paraphrases()
        results = [_run(task, _success_answers(), root) for task in paraphrases]
        check("fifty_paraphrases_use_one_core_solver",
              len(paraphrases) == 50 and len(set(paraphrases)) == 50
              and all(item["solved"] for item in results)
              and all(item["model_calls"] == 7 for item in results),
              f"{sum(item['solved'] for item in results)}/50 solved")

    multilingual = (
        "Crea un artefacto de texto verificado.",
        "Creez un artefact texte verifie.",
        "Erstelle ein gepruftes Textartefakt.",
        "Crie um artefato de texto verificado.",
        "Maak een geverifieerd tekstbestand.",
    )
    with tempfile.TemporaryDirectory() as root:
        results = [_run(task, _success_answers(), root)
                   for task in multilingual]
        check("multilingual_tasks_use_the_same_solver",
              all(item["solved"] for item in results),
              f"{sum(item['solved'] for item in results)}/5 solved")

    cross_domain = (
        "Inspect an unfamiliar repository and produce a verified repair.",
        "Transform an image and verify the output visually.",
        "Edit a video and verify playback and timing.",
        "Standardize an address file and report unresolved records.",
        "Build and test an adapter for an unfamiliar API.",
        "Research an unfamiliar regulation and produce a sourced report.",
    )
    with tempfile.TemporaryDirectory() as root:
        results = [_run(task, _gap_answers("cross-domain"), root)
                   for task in cross_domain]
        check("noun_substitution_and_cross_domain_tasks_return_honest_gaps",
              all(not item["solved"] for item in results)
              and all(item["final_route"] == "stop_unprofitable"
                      for item in results),
              f"{len(results)} typed capability gaps")

    class ExactResolver:
        resolver_id = "test.exact_verified"

        @staticmethod
        def supports(task):
            return task == "Apply the registered exact transformation."

        @staticmethod
        def execute(task):
            return {"verified": True, "value": task.upper()}

    with tempfile.TemporaryDirectory() as root:
        deterministic = run_adaptive_practitioner(
            AdaptivePractitionerRequest(
                "Apply the registered exact transformation.",
                mode="deterministic", runs_dir=root),
            AdaptivePractitionerDependencies(
                deterministic_resolvers=(ExactResolver(),)))
        check("deterministic_exact_capability_uses_zero_model_calls",
              deterministic["solved"]
              and deterministic["model_calls"] == 0
              and deterministic["run_history"]["chain_intact"],
              deterministic["deterministic_attempt"]["status"])

    with tempfile.TemporaryDirectory() as root:
        hybrid = _run(
            "Build an unfamiliar verified artifact.",
            _success_answers(), root, mode="hybrid")
        block_ids = [block["block_id"]
                     for snap in hybrid["context_snapshots"]
                     for block in snap["blocks"]]
        check("hybrid_passes_complete_deterministic_trace_to_model",
              hybrid["solved"]
              and hybrid["deterministic_attempt"]["status"]
                  == "NO_VERIFIED_CAPABILITY"
              and "deterministic_attempt" in block_ids,
              hybrid["deterministic_attempt"]["recommended_escalation"])
        first_snapshot = hybrid["context_snapshots"][0]
        roles = {item.get("role") for item in hybrid["loop_details"]}
        check("governed_semantic_prompt_assembly_uses_one_loop",
              bool(first_snapshot.get("packet_artifact_ref"))
              and bool(first_snapshot.get("intelligence_loop_id"))
              and bool(first_snapshot.get("assembly_loop_id"))
              and not first_snapshot.get("primitive_loop_ids")
              and first_snapshot["prompt_assembly"]["ordered_block_refs"][0]
                  == "authority_and_policy"
              and {"practitioner", "intelligence"} <= roles
              and '"prompt":' not in json.dumps(hybrid),
              first_snapshot["packet_digest"])

    with tempfile.TemporaryDirectory() as root:
        repaired = _run(
            "Build a verified artifact after a malformed model response.",
            ("not valid JSON", *_success_answers()), root, mode="hybrid")
        check("invalid_model_json_is_repaired_through_the_same_typed_step",
              repaired["solved"] and repaired["model_calls"] == 8,
              repaired.get("failure", "format repair succeeded"))

    leaked_orientation = _orientation(
        verification_obligations=[
            "Validate the TaskOrientationResult against the inline schema.",
            "Emit no additional prose outside the requested schema."])
    horizon_answers = (
        json.dumps(leaked_orientation), *_success_answers())
    with tempfile.TemporaryDirectory() as root:
        horizon_repair = _run(
            "Build a verified artifact without losing the task horizon.",
            horizon_answers, root, mode="hybrid")
        check("orientation_packet_contract_cannot_replace_task_acceptance",
              horizon_repair["solved"]
              and horizon_repair["model_calls"] == 8,
              horizon_repair.get("failure", "orientation repaired"))

    method_answers = list(_success_answers())
    valid_how = json.loads(method_answers[2])
    method_answers.insert(2, json.dumps({
        **valid_how, "capability_ref": "core.web.get"}))
    with tempfile.TemporaryDirectory() as root:
        method_repair = _run(
            "Build a verified artifact after an invalid method selection.",
            tuple(method_answers), root, mode="hybrid")
        check("method_outside_the_selected_action_is_repaired_before_use",
              method_repair["solved"]
              and method_repair["model_calls"] == 8,
              method_repair.get("failure", "method repair succeeded"))

    decision_answers = list(_success_answers())
    invalid_decision = json.loads(decision_answers[1])
    invalid_decision["actions"][0]["scheduling"] = ""
    decision_answers.insert(1, json.dumps(invalid_decision))
    with tempfile.TemporaryDirectory() as root:
        decision_repair = _run(
            "Build a verified artifact after an invalid action decision.",
            tuple(decision_answers), root, mode="hybrid")
        check("invalid_next_action_is_repaired_before_planning",
              decision_repair["solved"]
              and decision_repair["model_calls"] == 8,
              decision_repair.get("failure", "decision repair succeeded"))

    executable_repair = _decision("REPAIR")
    with tempfile.TemporaryDirectory() as root:
        repaired_project = _run(
            "Repair a failed artifact through the registered capability.",
            _success_answers(decision=executable_repair), root, mode="hybrid")
        check("repair_with_registered_capability_executes_real_work",
              repaired_project["solved"]
              and bool(repaired_project["project_attempts"]),
              repaired_project.get("final_route", ""))

    invalid_candidate_answers = tuple(json.dumps(item) for item in (
        _orientation(), {"actions": [_decision()]},
        {"action_id": _decision_id(_decision()), "how_mode": "generate",
         "act_mode": "run_dag", "capability_ref": "core.generated_project",
         "arguments": {}, "steps": ["build"], "spawned_tasks": [],
         "rationale": "Build through the registered capability."},
        {"record_type": "invalid"}, {"record_type": "still_invalid"},
        {"verdict": "repair", "best_index": 0, "scores": [0.0],
         "notes": "The project candidate is invalid.",
         "remaining_gaps": [{"criterion_ref": "criterion:0",
                              "gap": "valid project candidate"}],
         "advisory_findings": [], "new_requirement_proposals": []},
        {"route": "repair", "reason": "Repair the typed candidate."}))
    with tempfile.TemporaryDirectory() as root:
        invalid_candidate = _run(
            "Build a verified artifact after an invalid project candidate.",
            invalid_candidate_answers, root, mode="hybrid")
        check("invalid_project_candidate_becomes_a_repairable_action_result",
              not invalid_candidate["solved"]
              and not invalid_candidate.get("failure_code")
              and invalid_candidate["final_route"] == "repair",
              "run reached verification and routing")

    with tempfile.TemporaryDirectory() as root:
        led = _run(
            "Build an unseen verified artifact.",
            _success_answers(), root, mode="non_deterministic")
        check("llm_led_starts_with_orientation_and_completes_full_loop",
              led["solved"]
              and led["deterministic_attempt"]["status"] == "SKIPPED_LLM_LED"
              and len(led["orientations"]) == 1
              and bool(led["selected_solution_canvas"]),
              f"{led['passes']} pass, {led['model_calls']} model calls")

    low_confidence_build = _decision(confidence=0.1)
    high_confidence_stop = _decision(
        "ABSTAIN", confidence=0.99,
        goal="Stop without producing the requested artifact.",
        reason="One possible candidate is to stop.")
    selected_answers = list(_success_answers(
        decision=low_confidence_build))
    selected_answers[1] = json.dumps({
        "actions": [high_confidence_stop, low_confidence_build],
        "selected_action_index": 1})
    with tempfile.TemporaryDirectory() as root:
        selected = _run(
            "Compare possible actions, select one, and build the artifact.",
            tuple(selected_answers), root, mode="non_deterministic")
        selected_canvases = [item for item in
                             selected["candidate_solution_canvases"]
                             if item.get("selected")]
        check("model_explicitly_selects_among_actions_without_local_rescoring",
              selected["solved"] and len(selected_canvases) == 1
              and selected_canvases[0]["action_kind"] == "BUILD_CAPABILITY"
              and [item["confidence"]
                   for item in selected["action_decisions"]] == [0.99, 0.1],
              "the selected index wins even when another candidate has a "
              "larger advisory confidence")

    with tempfile.TemporaryDirectory() as root:
        source_root = Path(root) / "source"
        source_root.mkdir()
        source_body = (
            "def normalize(value):\n"
            "    return value.upper()  # defect: expected casefold\n")
        (source_root / "unseen_module.py").write_text(
            source_body, encoding="utf-8")
        inspect_decision = _decision(
            "RESEARCH_SOURCE",
            goal="Inspect the supplied implementation before changing it.",
            required_capabilities=["core.source.inspect"],
            permissions=["source_read"],
            expected_output="Selected source content and its digest.")
        inspect_how = {
            "action_id": _decision_id(inspect_decision),
            "how_mode": "research", "act_mode": "run_dag",
            "capability_ref": "core.source.inspect",
            "arguments": {"query": "normalize casefold",
                          "include_contents": True},
            "steps": ["inspect supplied source"], "spawned_tasks": [],
            "rationale": "Read the exact implementation before proposing a fix.",
        }
        build_decision = _decision(
            "REPAIR", goal="Build and verify the source-informed repair.")
        build_how = {
            "action_id": _decision_id(build_decision),
            "how_mode": "modify", "act_mode": "run_dag",
            "capability_ref": "core.generated_project", "arguments": {},
            "steps": ["build repair", "verify repair"],
            "spawned_tasks": [],
            "rationale": "Use the selected source content to build the repair.",
        }
        candidate = {
            "record_type": "generated_project_candidate/v1",
            "project_id": "source_informed_repair",
            "summary": "Repair the supplied implementation.",
            "files": [{"path": "repair.py", "purpose": "Apply the repair.",
                       "acceptance": ["The selected source is read."]}],
            "commands": [{"argv": ["python", "repair.py"],
                          "purpose": "Run the repair.",
                          "timeout_seconds": 30}],
            "expected_artifacts": [{"path": "repair.py",
                                    "media_type": "text/x-python",
                                    "minimum_bytes": 1}],
        }
        repair_content = (
            "from pathlib import Path\n"
            "source = Path('inputs/source/unseen_module.py').read_text()\n"
            "assert 'return value.upper()' in source\n"
            "print('repair uses selected source')\n")
        inspect_verification = {
            "verdict": "research_more", "best_index": 0,
            "scores": [1.0], "notes": "The source is now available.",
            "remaining_gaps": [{"criterion_ref": "criterion:0",
                                 "gap": "the repair has not been built"}],
            "advisory_findings": [], "new_requirement_proposals": [],
        }
        accept_verification = {
            "verdict": "accept", "best_index": 0, "scores": [1.0],
            "notes": "The source-informed repair passed.",
            "remaining_gaps": [], "advisory_findings": [],
            "new_requirement_proposals": [],
        }
        answers = tuple(json.dumps(item) for item in (
            _orientation(
                current_state="A supplied implementation must be inspected.",
                unknowns=["exact defect in supplied source"],
                candidate_capabilities=["core.source.inspect",
                                        "core.generated_project"]),
            {"actions": [inspect_decision]}, inspect_how,
            inspect_verification,
            {"route": "continue", "reason": "Inspect before editing."},
            _orientation(
                current_state="Selected source content is available.",
                knowns=["the implementation uppercases instead of casefolding"],
                unknowns=[], candidate_capabilities=["core.generated_project"]),
            {"actions": [build_decision]}, build_how, candidate,
            {"path": "repair.py", "content": repair_content},
            accept_verification,
            {"route": "stop_success", "reason": "Repair is verified."},
        ))
        observed_inputs = []

        def source_project_fixture(request, context):
            observed_inputs.extend(request.input_artifacts)
            result = _project_fixture(request, context)
            result["input_use_validation"] = {
                "passed": bool(request.input_artifacts),
                "supplied_paths": [item.path
                                   for item in request.input_artifacts],
            }
            return result

        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=answers, max_model_calls=len(answers)))
        source_led = run_adaptive_practitioner(
            AdaptivePractitionerRequest(
                "Repair the supplied unfamiliar module after inspecting it.",
                mode="non_deterministic", runs_dir=root, max_passes=2,
                source_kind="repository", source_refs=(str(source_root),),
                allow_source_materialization_to_model=True,
                allow_network_reads=False),
            AdaptivePractitionerDependencies(
                execution, project_executor=source_project_fixture))
        selected = source_led["source_inspections"][0]["selected"]
        check("model_can_inspect_unseen_source_then_choose_a_different_action",
              source_led["solved"] and source_led["passes"] == 2
              and selected[0]["content"] == source_body
              and observed_inputs
              and observed_inputs[0].content == source_body.encode("utf-8")
              and [item["action_kind"]
                   for item in source_led["action_decisions"]]
                  == ["RESEARCH_SOURCE", "REPAIR"],
              f"{source_led['passes']} passes; "
              f"{len(selected)} selected source; "
              f"{len(observed_inputs)} executed input")

    incomplete_decision = _decision(
        "RETURN_RESULT", goal="Return without building.",
        reason="Attempt premature completion.",
        expected_output="A claim without an artifact.")
    incomplete_answers = tuple(json.dumps(item) for item in (
        _orientation(), {"actions": [incomplete_decision]},
        {"verdict": "repair", "best_index": 0, "scores": [0.0],
         "notes": "The requested artifact is missing.",
         "remaining_gaps": [{"criterion_ref": "criterion:0",
                              "gap": "artifact not built"}],
         "advisory_findings": [], "new_requirement_proposals": []},
        {"route": "repair", "reason": "Artifact remains missing."}))
    with tempfile.TemporaryDirectory() as root:
        incomplete = _run(
            "Build a real artifact, not a plan.", incomplete_answers, root)
        check("ready_planned_or_returned_without_artifact_is_not_completion",
              not incomplete["solved"]
              and incomplete["status"] == "NOT_YET_PROVEN",
              incomplete["final_route"])

    permission_decision = _decision(
        permissions=["deployment"],
        required_capabilities=["core.generated_project"])
    with tempfile.TemporaryDirectory() as root:
        blocked = _run(
            "Build something that requests unavailable authority.",
            (json.dumps(_orientation()),
             json.dumps({"actions": [permission_decision]})), root)
        check("permission_uncertainty_blocks_before_execution",
              not blocked["solved"]
              and blocked["failure_code"] == "PermissionError"
              and blocked["run_history"]["chain_intact"],
              blocked.get("failure", ""))

    blocking_orientation = _orientation(
        unknowns=["required destination"],
        ambiguities=[{
            "subject": "required destination",
            "state": "USER_CLARIFICATION_REQUIRED",
            "reason": "The intended result changes materially."}],
        blocking_questions=["Which destination is required?"])
    ask_decision = _decision(
        "ASK_USER", goal="Ask the material question.",
        reason="The intended result depends on the answer.",
        expected_output="A user answer.")
    ask_answers = tuple(json.dumps(item) for item in (
        blocking_orientation, {"actions": [ask_decision]},
        {"verdict": "stop", "best_index": 0, "scores": [0.0],
         "notes": "Input is still missing.",
         "remaining_gaps": [{"criterion_ref": "criterion:0",
                              "gap": "required destination"}],
         "advisory_findings": [], "new_requirement_proposals": []},
        {"route": "stop_unprofitable", "reason": "Material input is missing."}))
    with tempfile.TemporaryDirectory() as root:
        asked = _run(
            "Send the finished result to the required destination.",
            ask_answers, root, interaction_mode="ask_when_material")
        autonomous = _run(
            "Send the finished result to the required destination.",
            ask_answers, root, interaction_mode="autonomous")
        check("material_clarification_asks_and_autonomous_run_abstains",
              not asked["solved"] and not autonomous["solved"],
              "both paths terminate without invented input")

    delegated_orientation = _orientation(
        ambiguities=[{
            "subject": "implementation detail", "state": "DELEGATED_CHOICE",
            "reason": "Any verified implementation is acceptable."}],
        delegated_choices=["implementation detail"])
    with tempfile.TemporaryDirectory() as root:
        delegated = _run(
            "Choose any implementation and return a verified artifact.",
            _success_answers(orientation=delegated_orientation), root)
        check("delegated_choice_proceeds_without_user_interruption",
              delegated["solved"], delegated["final_route"])

    advisory_answers = list(_success_answers())
    advisory_verification = json.loads(advisory_answers[5])
    advisory_verification["advisory_findings"] = [
        "A larger evaluation could improve confidence."]
    advisory_verification["new_requirement_proposals"] = [
        "Consider another optional report format."]
    advisory_answers[5] = json.dumps(advisory_verification)
    with tempfile.TemporaryDirectory() as root:
        advisory = _run(
            "Build and verify the requested artifact.",
            tuple(advisory_answers), root)
        check("advisory_improvement_does_not_redefine_completion",
              advisory["solved"]
              and advisory["verification"][0]["advisory_findings"],
              advisory.get("final_route", ""))

    conflicting_orientation = _orientation(
        ambiguities=[{
            "subject": "implementation detail",
            "state": "USER_CLARIFICATION_REQUIRED",
            "reason": "The model incorrectly asked despite delegation."}],
        delegated_choices=["implementation detail"],
        blocking_questions=["Which implementation detail should be used?"],
        proposed_next_action="ASK_USER")
    with tempfile.TemporaryDirectory() as root:
        normalized = _run(
            "Choose any implementation and return a verified artifact.",
            _success_answers(orientation=conflicting_orientation), root)
        dispositions = normalized["orientations"][0]["ambiguities"]
        check("delegated_choice_conflict_is_normalized_without_another_model_call",
              normalized["solved"]
              and dispositions[0]["state"] == "DELEGATED_CHOICE"
              and not normalized["orientations"][0]["blocking_questions"],
              dispositions[0]["state"])

    open_choice_orientation = _orientation(
        ambiguities=[
            {"subject": "source choice", "state": "UNKNOWN",
             "reason": "No source was named."},
            {"subject": "derived field", "state": "UNKNOWN",
             "reason": "This depends on the selected source."},
            {"subject": "source authorization", "state": "AMBIGUOUS",
             "reason": "The source license must be researched."}],
        delegated_choices=["source choice"],
        research_questions=["What source license applies?"],
        blocking_questions=[
            "Which source choice should be used?",
            "What is the derived field?",
            "What source authorization applies?"])
    with tempfile.TemporaryDirectory() as root:
        classified = _run(
            "Choose an acceptable source and build a verified artifact.",
            _success_answers(orientation=open_choice_orientation), root)
        states = [item["state"]
                  for item in classified["orientations"][0]["ambiguities"]]
        check("open_choices_dependencies_and_research_do_not_block_autonomy",
              classified["solved"]
              and states == [
                  "DELEGATED_CHOICE", "DERIVED_VALUE", "RESEARCH_REQUIRED"]
              and not classified["orientations"][0]["blocking_questions"],
              str(states))

    clean, detail = _hardcoding_scan()
    check("generic_solver_source_contains_no_acceptance_example_leakage",
          clean, detail or "no prohibited source phrases")

    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "adaptive_practitioner_acceptance_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
