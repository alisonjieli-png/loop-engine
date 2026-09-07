"""Offline regressions for selected-action and spawned-plan admission.

These fixtures test method shape, rejected delegation, and admission atomicity.
They perform no provider calls or host effects.
"""
from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

from ..loop.kernel import CandidateAction, PractitionerState, ProblemSpec, Situation
from .adaptive_practitioner_planning import (
    AdaptivePlanningRequest, _planning_schema, _validate_plan_response,
    build_execution_plan)
from .adaptive_practitioner_records import NextActionDecision


def _request() -> AdaptivePlanningRequest:
    return AdaptivePlanningRequest(
        PractitionerState(ProblemSpec("Complete the parent task", depth=7)),
        Situation("oriented", knowns={"orientation": SimpleNamespace(
            to_dict=lambda: {"immediate_goal": "Complete the selected action"})}),
        CandidateAction("selected"))


def _services(action_kind="GENERATE_CODE", *, answers=(), max_passes=None):
    capability_refs = ([] if action_kind in ("SPAWN_LOOP", "RUN_PARALLEL")
                       else ["core.generated_project"])
    action = NextActionDecision.from_mapping({
        "action_kind": action_kind,
        "goal": "Perform the selected responsibility",
        "reason": "The result contributes to the task",
        "inputs": {}, "expected_output": "Checked result",
        "required_capabilities": capability_refs,
        "permissions": [], "budget": {}, "dependencies": [],
        "scheduling": "sequential", "verification": "Check the result",
        "return_destination": "parent", "confidence": 0.8,
        "fallback": {}})
    responses = iter(deepcopy(answers))
    requests, diagnostics = [], []

    def model(request):
        requests.append(request)
        return next(responses)

    return SimpleNamespace(
        action_details={"selected": action},
        request=SimpleNamespace(max_passes=max_passes),
        plan_details={
            "selected": {"incumbent": "preserve until admission"},
            "current_candidate_canvases": [
                {"candidate_id": "canvas:selected", "selected": False}]},
        model=model, model_requests=requests, diagnostics=diagnostics,
        diagnostic=lambda name, value: diagnostics.append((name, value)))


def _spawned(**changes):
    return {"objective": "Inspect one bounded question",
            "constraints": [], "success_criteria": ["Return supported findings"],
            **changes}


def _plan(*, spawning=False, **changes):
    return {
        "action_id": "selected", "how_mode": "delegate" if spawning else "generate",
        "act_mode": "spawn_practitioners" if spawning else "run_dag",
        "capability_ref": "" if spawning else "core.generated_project",
        "arguments": {}, "steps": ["Perform the selected responsibility"],
        "spawned_tasks": [_spawned()] if spawning else [],
        "rationale": "Use the admitted action contract", **changes}


def run_checks() -> dict:
    """No provider, filesystem, shell, or host effect is performed."""
    checks = []

    def check(name, passed, detail=""):
        checks.append({"test": name, "passed": bool(passed), "detail": detail})

    request = _request()
    direct = _plan(act_mode="run_direct")
    direct_services = _services(answers=(direct,))
    direct_plan = build_execution_plan(request, direct_services)
    check("simple_capability_keeps_one_method_decision_without_spawned_tasks",
          direct_plan.act_mode == "run_direct" and not direct_plan.spawned_loops
          and len(direct_services.model_requests) == 1)

    dag = _validate_plan_response(_plan(), request, _services())
    check("registered_capability_run_dag_remains_admitted",
          dag.act_mode == "run_dag" and dag.handle == "core.generated_project"
          and not dag.spawned_loops)

    spawn = _validate_plan_response(_plan(spawning=True), request,
                                   _services("SPAWN_LOOP"))
    check("spawn_plan_keeps_spawned_goal_criteria_and_unlimited_declared_budget",
          spawn.act_mode == "spawn_practitioners" and not spawn.handle
          and len(spawn.spawned_loops) == 1
          and spawn.spawned_loops[0].objective == _spawned()["objective"]
          and spawn.spawned_loops[0].success_criteria
          == tuple(_spawned()["success_criteria"])
          and spawn.spawned_loops[0].budget_passes is None
          and spawn.spawned_loops[0].depth == request.state.spec.depth + 1)

    serial = _validate_plan_response(_plan(spawning=True, spawned_tasks=[
        _spawned(objective="First independent responsibility"),
        _spawned(objective="Second independent responsibility")]), request,
        _services("SPAWN_LOOP", max_passes=4))
    check("serial_spawned_tasks_preserve_order_and_existing_bounded_pass_authority",
          [spawned.objective for spawned in serial.spawned_loops]
          == ["First independent responsibility", "Second independent responsibility"]
          and all(spawned.budget_passes == 3 for spawned in serial.spawned_loops))

    direct_schema = json.loads(_planning_schema("selected"))
    spawn_schema = json.loads(_planning_schema("selected", spawning=True))
    check("method_schema_shows_only_the_selected_action_execution_shapes",
          direct_schema["spawned_tasks"] == []
          and "spawn_practitioners" not in direct_schema["act_mode"]
          and spawn_schema["act_mode"] == "spawn_practitioners"
          and spawn_schema["capability_ref"] == "")

    malformed = [
        ("capability_cannot_switch_to_spawning", "GENERATE_CODE",
         _plan(act_mode="spawn_practitioners", spawned_tasks=[_spawned()]),
         "only a selected SPAWN_LOOP"),
        ("capability_cannot_hide_ignored_spawned_tasks", "GENERATE_CODE",
         _plan(spawned_tasks=[_spawned()]), "spawned_tasks []"),
        ("spawn_cannot_switch_to_direct_execution", "SPAWN_LOOP",
         _plan(spawning=True, act_mode="run_direct"), "requires act_mode"),
        ("spawn_cannot_select_an_unbound_capability", "SPAWN_LOOP",
         _plan(spawning=True, capability_ref="unregistered"), "empty capability_ref"),
        ("spawn_cannot_discard_capability_arguments", "SPAWN_LOOP",
         _plan(spawning=True, arguments={"input": "unbound"}), "requires arguments {}"),
        ("spawn_cannot_be_empty", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[]), "at least one spawned"),
        ("malformed_spawned_cannot_be_silently_removed", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(), 17]), "spawned_tasks[1]"),
        ("null_spawned_array_is_not_empty", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=None), "expected_array"),
        ("false_spawned_array_is_not_empty", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=False), "expected_array"),
        ("spawned_dependencies_cannot_be_discarded", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(depends_on=["prior"])]),
         "not supported"),
        ("spawned_identity_cannot_be_discarded", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(task_id="spawned")]),
         "unexpected_fields"),
        ("spawned_input_bindings_cannot_be_discarded", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(inputs={"data": "ref"})]),
         "input-binding"),
        ("spawned_permission_fields_cannot_grant_authority", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(permissions=["network_write"])]),
         "unexpected_fields"),
        ("spawned_requires_checkable_completion", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(success_criteria=[])]),
         "completion condition"),
        ("null_spawned_constraints_are_not_empty", "SPAWN_LOOP",
         _plan(spawning=True, spawned_tasks=[_spawned(constraints=None)]), "constraints"),
        ("plan_dependency_fields_cannot_be_discarded", "GENERATE_CODE",
         _plan(dependencies=["prior"]), "unexpected_fields"),
        ("method_cannot_select_outside_action_capabilities", "GENERATE_CODE",
         _plan(capability_ref="unregistered"), "outside NextActionDecision"),
        ("method_capability_is_not_coerced", "GENERATE_CODE",
         _plan(capability_ref=None), "expected_text"),
        ("method_must_target_the_selected_action", "GENERATE_CODE",
         _plan(action_id="other"), "another action"),
        ("null_arguments_are_not_empty", "GENERATE_CODE",
         _plan(arguments=None), "expected_object"),
        ("non_json_arguments_are_refused", "GENERATE_CODE",
         _plan(arguments={"number": float("nan")}), "expected_strict_json"),
        ("invalid_how_mode_cannot_publish_a_plan", "GENERATE_CODE",
         _plan(how_mode="invalid"), "how_mode"),
        ("invalid_act_mode_cannot_publish_a_plan", "GENERATE_CODE",
         _plan(act_mode="invalid"), "act_mode"),
        ("null_steps_are_not_empty", "GENERATE_CODE",
         _plan(steps=None), "plan.steps"),
        ("non_object_plan_is_refused", "GENERATE_CODE", [], "expected_object"),
        ("unsupported_parallel_plan_is_refused", "RUN_PARALLEL",
         _plan(spawning=True), "concurrent execution contract"),
    ]
    missing = _plan()
    del missing["spawned_tasks"]
    malformed.append(("missing_plan_fields_are_refused", "GENERATE_CODE",
                      missing, "missing_fields=spawned_tasks"))
    for name, kind, value, expected in malformed:
        services = _services(kind)
        before = deepcopy(services.plan_details)
        try:
            _validate_plan_response(value, request, services)
            error = ""
        except (TypeError, ValueError) as exc:
            error = str(exc)
        check(name, bool(error) and expected in error
              and services.plan_details == before, error)

    original = _plan(arguments={"query": {"limit": 2}})
    independent = _validate_plan_response(original, request, _services())
    original["arguments"]["query"]["limit"] = 100
    check("caller_argument_mutation_cannot_change_the_admitted_method",
          independent.experiment["arguments"]["query"]["limit"] == 2)

    bad_spawn = _plan(spawning=True, spawned_tasks=[_spawned(), "malformed"])
    repaired_services = _services("SPAWN_LOOP", answers=(bad_spawn, _plan(spawning=True)))
    repaired = build_execution_plan(request, repaired_services)
    check("spawned_shape_failure_gets_targeted_repair_before_admission",
          len(repaired.spawned_loops) == 1
          and len(repaired_services.model_requests) == 2
          and "spawned_tasks[1]" in repaired_services.model_requests[1].state[
              "method_validation_failure"]
          and len(repaired_services.diagnostics) == 1)

    exhausted_services = _services("SPAWN_LOOP", answers=(bad_spawn, bad_spawn))
    exhausted = build_execution_plan(request, exhausted_services)
    check("exhausted_shape_repair_returns_no_executable_spawned",
          exhausted.handle == "core.invalid" and not exhausted.spawned_loops
          and len(exhausted_services.model_requests) == 2
          and "spawned_tasks[1]" in exhausted.rationale)

    parallel_services = _services("RUN_PARALLEL")
    parallel = build_execution_plan(request, parallel_services)
    check("unavailable_parallel_execution_refuses_before_any_method_call",
          parallel.handle == "core.invalid" and not parallel.spawned_loops
          and not parallel_services.model_requests
          and "registered concurrent host operation" in parallel.rationale)

    terminal_services = _services("RETURN_RESULT")
    terminal = build_execution_plan(request, terminal_services)
    check("terminal_result_still_requires_no_method_model_call",
          terminal.handle == "core.finish" and not terminal.spawned_loops
          and not terminal_services.model_requests)

    passed = sum(item["passed"] for item in checks)
    return {"record_type": "adaptive_planning_test/v1", "tests": checks,
            "passed": passed, "total": len(checks),
            "all_passed": passed == len(checks)}
