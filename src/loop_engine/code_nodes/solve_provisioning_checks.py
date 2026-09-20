"""Public solve checks for assignment-folder intelligence provisioning.

Fixture model answers select real Spawned Practitioner work and exact local
resolvers. These checks establish wiring and refusal, not native harness loading
or the quality and independent admission of any catalogue resource.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile

from ..core.adaptive_practitioner_acceptance_checks import _decision, _decision_id, _orientation, _success_answers
from ..core.adaptive_practitioner_bindings_checks import assignment
from ..core.guardrail_intelligence import Guardrail, GuardrailSet
from ..core.practitioner_runtime.provisioning import HarnessAssignmentConfiguration, HarnessProvisioningConfiguration
from ..core.run_history import load_saved_run_bundle
from ..core.spawned_provisioning_checks import fixture_configuration
from ..templates.intake import TaskIntakeRequest, intake_task
from .solution_model_port import FixtureModelExecutionRequest, fixture_model_execution


def public_case(root, configuration, *, writes=False, tasks=None, host=None):
    from .solve_runtime import SolveRequest, solve_task

    observed = []

    class ExactAssignmentResolver:
        resolver_id = "fixture.provisioned_assignment/v1"

        def supports(self, task):
            try:
                return json.loads(task).get("record_type") == "delegated_problem/v1"
            except (ValueError, AttributeError):
                return False

        def execute(self, task):
            observed.append(json.loads(task))
            return {"verified": True, "value": [2, 3]}

    tasks = [assignment("source")] if tasks is None else tasks
    decision = _decision("SPAWN_LOOP", required_capabilities=[], permissions=[], goal="Resolve exact assignments.")
    plan = {"action_id": _decision_id(decision), "how_mode": "delegate", "act_mode": "spawn_practitioners",
            "capability_ref": "", "arguments": {}, "steps": ["resolve assignments"],
            "spawned_tasks": tasks, "rationale": "Use separately governed exact work."}
    verification = json.loads(_success_answers()[-2])
    verification["scores"] = [1.0] * len(tasks)
    answers = tuple(json.dumps(item) for item in (
        _orientation(candidate_capabilities=[]), {"actions": [decision]}, plan, verification,
        {"route": "stop_success", "reason": "The assignments returned."}))
    request = SolveRequest(
        intake_task(TaskIntakeRequest(text="Resolve the root through bounded assignments.")),
        model_execution=fixture_model_execution(FixtureModelExecutionRequest(answers=answers, max_model_calls=len(answers))),
        runs_dir=str(Path(root) / "runs"), workspace_root=str(Path(root) / "workspace"),
        practitioner_mode="hybrid", max_passes=1, quiet_model_io=True,
        allow_workspace_writes=writes, allow_sandbox_commands=writes,
        deterministic_resolvers=(ExactAssignmentResolver(),), harness_provisioning=configuration,
        host_runtime=host)
    outcome = solve_task(request)
    bundle = load_saved_run_bundle(request.runs_dir, outcome.run_id)
    return outcome, observed, bundle


def run_checks():
    checks = []

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed), "note": "public solve; no real provider calls"})

    with tempfile.TemporaryDirectory() as root:
        configuration = fixture_configuration(kind="build")
        outcome, observed, bundle = public_case(root, configuration, writes=True)
        summary = outcome.intelligence["harness_provisioning"]
        folder = Path(root) / "workspace" / "spawned" / "1"
        task = json.loads((folder / "task.json").read_text())
        instructions = (folder / "AGENTS.md").read_text()
        check("public_solve_provisions_the_atomic_assignment_with_exact_configuration",
              len(observed) == 1 and summary["provisioned_assignments"] == 1
              and summary["configuration_digest"] == configuration.content_digest
              and task["node_id"] == "source" and task["kind"] == "build"
              and task["mode"] == "hybrid" and task["effects"] == ["reads_fs", "writes_fs", "spawns_process"]
              and task["output_contract_refs"] and (folder / "CLAUDE.md").is_file())
        check("public_solve_reports_selected_references_without_installing_candidate_bodies",
              {item["identity"] for item in summary["assignments"][0]["offered"]}
              == {"skill.read_source", "tool.write_report"}
              and "skill.unselected" not in instructions and "uninstalled candidate body" not in instructions
              and summary["resource_bodies_installed"] == 0 and summary["native_loading_observed"] is False
              and summary["assignments"][0]["resource_admission_established"] is False)
        check("provisioning_decision_is_bound_into_saved_public_outcome_and_history",
              bundle.history.verify_chain()["intact"]
              and bundle.outcome["intelligence"]["harness_provisioning"] == summary
              and any(event.detail.get("custom_kind") == "spawned_provisioning_decided"
                      for event in bundle.history.event_log))

    with tempfile.TemporaryDirectory() as root:
        outcome, observed, _bundle = public_case(root, None, writes=True)
        summary = outcome.intelligence["harness_provisioning"]
        check("public_default_records_real_absence_without_preparation_files",
              len(observed) == 1 and summary["configured"] is False
              and summary["absence_reason"] == "not_configured"
              and summary["assignments"][0]["reason"] == "not_configured"
              and not (Path(root) / "workspace" / "spawned" / "1" / "task.json").exists())

    with tempfile.TemporaryDirectory() as root:
        outcome, observed, _bundle = public_case(root, fixture_configuration(preparation=False), writes=True)
        summary = outcome.intelligence["harness_provisioning"]
        check("public_solve_refuses_unauthorized_preparation_before_spawned_execution",
              not observed and summary["provisioned_assignments"] == 0
              and summary["assignments"][0]["reason"] == "preparation_writes_not_authorized"
              and not (Path(root) / "workspace" / "spawned" / "1").exists())

    with tempfile.TemporaryDirectory() as root:
        rules = GuardrailSet()
        rules.register(Guardrail("guard.output_contract", "Require output contract", "process", "block",
            "before_provisioning", "proceed without output contract", evidence_required=("output_contract_refs",)))
        outcome, observed, _bundle = public_case(root, fixture_configuration(rules=rules),
                                               tasks=[assignment("source", output=None)])
        summary = outcome.intelligence["harness_provisioning"]
        check("public_guardrail_refusal_prevents_exact_resolver_execution",
              not observed and summary["provisioned_assignments"] == 0
              and summary["assignments"][0]["status"] == "refused"
              and "guard.output_contract" in summary["assignments"][0]["reason"]
              and not (Path(root) / "workspace" / "spawned" / "1" / "task.json").exists())

    with tempfile.TemporaryDirectory() as root:
        configuration = fixture_configuration(kind="build")
        reason = replace(configuration.assignment, kind="reason")
        configuration = replace(configuration, assignment_overrides=(("source", reason),))
        outcome, observed, _bundle = public_case(root, configuration, writes=True,
                                               tasks=[assignment("source"), assignment("writer")])
        first = json.loads((Path(root) / "workspace" / "spawned" / "1" / "task.json").read_text())
        second = json.loads((Path(root) / "workspace" / "spawned" / "2" / "task.json").read_text())
        check("public_exact_assignment_overrides_preserve_both_reason_and_build_choices",
              len(observed) == 2 and first["kind"] == "reason" and first["effects"] == ["reads_fs"]
              and second["kind"] == "build" and second["effects"] == ["reads_fs", "writes_fs", "spawns_process"]
              and outcome.intelligence["harness_provisioning"]["provisioned_assignments"] == 2)

    with tempfile.TemporaryDirectory() as root:
        from ..core.adaptive_host_runtime_checks import _fixture
        outcome, observed, _bundle = public_case(root, fixture_configuration(), host=_fixture(mutating=True).binding)
        summary = outcome.intelligence["harness_provisioning"]
        check("reason_assignment_cannot_claim_to_narrow_an_unrelated_effectful_host_binding",
              not observed and summary["assignments"][0]["status"] == "refused"
              and "read-only host binding" in summary["assignments"][0]["reason"])

    with tempfile.TemporaryDirectory() as root:
        configuration = fixture_configuration()
        configuration = replace(configuration, assignment=replace(configuration.assignment,
            workspace_effects=("reads_fs", "writes_fs"), allow_sandbox_commands=True))
        outcome, observed, _bundle = public_case(root, configuration, writes=True)
        task = json.loads((Path(root) / "workspace" / "spawned" / "1" / "task.json").read_text())
        check("public_reasoning_experiment_preserves_explicit_write_and_command_authority",
              len(observed) == 1 and task["kind"] == "reason"
              and task["effects"] == ["reads_fs", "writes_fs", "spawns_process"]
              and outcome.intelligence["harness_provisioning"]["provisioned_assignments"] == 1)

    with tempfile.TemporaryDirectory() as root:
        configuration = fixture_configuration(kind="build")
        configuration = replace(configuration, assignment=replace(configuration.assignment,
            workspace_effects=("reads_fs",), allow_sandbox_commands=False))
        outcome, observed, _bundle = public_case(root, configuration, writes=True)
        task = json.loads((Path(root) / "workspace" / "spawned" / "1" / "task.json").read_text())
        check("public_build_assignment_can_remain_read_only_without_command_authority",
              len(observed) == 1 and task["kind"] == "build" and task["effects"] == ["reads_fs"]
              and outcome.intelligence["harness_provisioning"]["provisioned_assignments"] == 1)

    with tempfile.TemporaryDirectory() as root:
        configuration = HarnessProvisioningConfiguration.bind(
            assignment=HarnessAssignmentConfiguration("reason"), preparation_writes_authorized=True)
        outcome, observed, _bundle = public_case(root, configuration)
        summary = outcome.intelligence["harness_provisioning"]
        check("public_assignment_only_configuration_names_absent_intelligence",
              len(observed) == 1 and summary["provisioned_assignments"] == 1
              and summary["configuration"]["catalogue_items"] is None
              and summary["assignments"][0]["catalogue_available"] is False
              and summary["assignments"][0]["offered"] == [])
    return checks
