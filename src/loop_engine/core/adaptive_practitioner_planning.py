"""Typed method selection and repair for the adaptive Practitioner.

This module turns one validated ``NextActionDecision`` into an
``ExecutionPlan``. A model response cannot add a capability, permission, or
spawned assignment that was absent from the selected action contract.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace

from ..code_nodes.solution_model_port import SolutionModelError
from ..loop.kernel import (
    CandidateAction,
    ExecutionPlan,
    PractitionerState,
    ProblemSpec,
    Situation,
)
from .adaptive_practitioner_records import (
    RUN_PARALLEL,
    AdaptivePractitionerError,
    AdaptiveRunServices,
    ModelStepRequest,
)
from .adaptive_practitioner_validation import _short_strings, _short_text
from .model_response_admission import (
    ModelResponseContract, ModelResponseAdmissionPolicy, ModelResponseRepairStalled)
from .option_selection import SELECTION_KEYS
from .adaptive_practitioner_bindings import (
    ASSIGNMENT_KEY, ASSIGNMENT_RECORD_TYPE, BASE_ASSIGNMENT_FIELDS,
    EXTENDED_ASSIGNMENT_FIELDS, SpawnedAssignment, assignment_task_view,
    compile_assignments)

# The two act modes a plan can name: spawn Practitioners, or run directly or as a DAG.
SPAWN_PRACTITIONERS_ACT, DIRECT_OR_DAG_ACT = "spawn_practitioners", "run_direct|run_dag"


@dataclass(frozen=True)
class AdaptivePlanningRequest:
    """State, orientation, and selected action for one method decision."""

    state: PractitionerState
    situation: Situation
    chosen: CandidateAction


_PLAN_FIELDS = frozenset({
    "action_id", "how_mode", "act_mode", "capability_ref", "arguments",
    "steps", "spawned_tasks", "rationale"})
_SPAWNED_FIELDS = frozenset({"objective", "constraints", "success_criteria"})
_PARALLEL_UNAVAILABLE = (
    "RUN_PARALLEL requires an installed concurrent execution contract; "
    "select SPAWN_LOOP for serial governed spawned_tasks, or select an explicitly "
    "registered concurrent host operation")
_TERMINAL_HANDLES = {
    'RETURN_RESULT':'core.finish','STOP':'core.abstain','ASK_USER':'core.ask',
    'ABSTAIN':'core.abstain','REQUEST_AUTHORITY':'core.authority'}
_CAPABILITY_FREE_ACTIONS = frozenset((*_TERMINAL_HANDLES,'SPAWN_LOOP','RUN_PARALLEL'))


def action_needs_execution_capability(action_kind: str) -> bool:
    """Mechanical requirement of this installed planner, not every Loop body.

    Terminal controls and explicit delegation have dedicated implementations.
    Other selected actions require a registered executable capability. The
    parallel action retains its existing explicit unavailable-path refusal.
    """
    return action_kind not in _CAPABILITY_FREE_ACTIONS


def _planning_schema(action_id: str, *, spawning: bool = False) -> str:
    return json.dumps({
        "action_id": action_id,
        "how_mode": (
            "use|configure|compose|modify|mutate|research|generate|delegate"),
        "act_mode": SPAWN_PRACTITIONERS_ACT if spawning else DIRECT_OR_DAG_ACT,
        "capability_ref": "" if spawning else "selected registered capability",
        "arguments": {}, "steps": ["string"],
        "spawned_tasks": ([{
            "record_type": ASSIGNMENT_RECORD_TYPE,
            "task_id": "unique-task-id", "depends_on": [], "inputs": [],
            "objective": "string", "constraints": ["string"],
            "success_criteria": ["string"], "output_contract": None}] if spawning else []),
        "rationale": "string",
    }, separators=(",", ":"))


def _planning_response_contract(action_id, action):
    """Bind a method response to the exact action that requested it."""
    text={'type':'string','minLength':1}
    spawning=action.action_kind=='SPAWN_LOOP'
    properties={
        'action_id':{'const':action_id}, 'how_mode':text,
        'act_mode':({'const':'spawn_practitioners'} if spawning else
                    {'type':'string','minLength':1,'not':{'const':'spawn_practitioners'}}),
        'capability_ref':({'const':''} if spawning else
                          {'enum':list(action.required_capabilities)} if action.required_capabilities else False),
        'arguments':{'type':'object',**({'maxProperties':0} if spawning else {})},
        'steps':{'type':'array','items':text},
        'spawned_tasks':({'type':'array','minItems':1,'items':{'type':'object',
            'required':sorted(_SPAWNED_FIELDS),'properties':{
                'objective':text,'constraints':{'type':'array','items':text},
                'success_criteria':{'type':'array','minItems':1,'items':text}}}}
            if spawning else {'type':'array','maxItems':0}),
        'rationale':text,
        # These channels are advisory telemetry, stripped before the plan
        # parser. Their values must not decide whether the method is valid.
        **{key:{} for key in SELECTION_KEYS}, 'stage_assistance_decision':{},
    }
    return ModelResponseContract('execution_method_response/v1',json.dumps({
        'type':'object','required':sorted(_PLAN_FIELDS),'properties':properties,
        'additionalProperties':False},sort_keys=True),
        policy=ModelResponseAdmissionPolicy(report_required_field_names=True, report_constraint_paths=True))


def _require_fields(value, required, location: str) -> None:
    if type(value) is not dict:
        raise AdaptivePractitionerError(f"{location}: expected_object")
    missing = required - set(value)
    if missing:
        raise AdaptivePractitionerError(
            f"{location}: missing_fields=" + ",".join(sorted(missing)))
    extra = set(value) - required
    if extra:
        raise AdaptivePractitionerError(
            f"{location}: unexpected_fields_count={len(extra)}; use only "
            + ",".join(sorted(required))
            + ". Use the versioned spawned assignment for dependency fields; "
            "parallel scheduling still requires a registered concurrent capability")


def _validate_plan_response(value, request, services) -> ExecutionPlan:
    chosen = request.chosen
    state = request.state
    action = services.action_details[chosen.action]
    if action.action_kind == RUN_PARALLEL:
        raise AdaptivePractitionerError(_PARALLEL_UNAVAILABLE)
    _require_fields(value, _PLAN_FIELDS, "plan")
    if type(value["action_id"]) is not str or value["action_id"] != chosen.action:
        raise AdaptivePractitionerError("how response targets another action")
    capability_ref = value["capability_ref"]
    if type(capability_ref) is not str:
        raise AdaptivePractitionerError("plan.capability_ref: expected_text")
    spawning = action.action_kind == "SPAWN_LOOP"
    act_mode = _short_text(value["act_mode"], "plan.act_mode")
    if spawning and act_mode != SPAWN_PRACTITIONERS_ACT:
        raise AdaptivePractitionerError(
            "SPAWN_LOOP requires act_mode spawn_practitioners")
    if not spawning and act_mode == SPAWN_PRACTITIONERS_ACT:
        raise AdaptivePractitionerError(
            "only a selected SPAWN_LOOP action may use spawn_practitioners; "
            "keep the selected capability in run_direct or run_dag")
    if spawning and capability_ref:
        raise AdaptivePractitionerError(
            "SPAWN_LOOP requires an empty capability_ref; its spawned tasks "
            "select capabilities through their own governed decisions")
    if not spawning and capability_ref not in set(action.required_capabilities):
        raise AdaptivePractitionerError(
            "how selected a capability outside NextActionDecision")
    spawned_values = value["spawned_tasks"]
    if type(spawned_values) is not list:
        raise AdaptivePractitionerError("plan.spawned_tasks: expected_array")
    if spawning and not spawned_values:
        raise AdaptivePractitionerError(
            "SPAWN_LOOP requires at least one spawned task with its own "
            "objective and success_criteria")
    if not spawning and spawned_values:
        raise AdaptivePractitionerError(
            "a capability action requires spawned_tasks []; select "
            "SPAWN_LOOP separately when delegation is needed")
    spawned = []
    for index, item in enumerate(spawned_values):
        location = f"plan.spawned_tasks[{index}]"
        extended = type(item) is dict and bool(set(item) - BASE_ASSIGNMENT_FIELDS)
        _require_fields(item, EXTENDED_ASSIGNMENT_FIELDS if extended else _SPAWNED_FIELDS, location)
        assignment = SpawnedAssignment.from_mapping(item) if extended else None
        criteria = _short_strings(item["success_criteria"], location + ".success_criteria")
        if not criteria:
            raise AdaptivePractitionerError(
                f"{location}.success_criteria: a spawned needs at least one "
                "checkable completion condition")
        spawned.append(ProblemSpec(
            _short_text(item["objective"], location + ".objective"),
            constraints=_short_strings(item["constraints"], location + ".constraints"),
            success_criteria=criteria,
            budget_passes=(
                None if services.request.max_passes is None
                else max(1, services.request.max_passes - 1)),
            depth=state.spec.depth + 1,
            seed_facts=({ASSIGNMENT_KEY: assignment} if assignment is not None else {})))
    if spawned:
        compile_assignments(tuple(spawned), state.spec.objective)
    if type(value["arguments"]) is not dict:
        raise AdaptivePractitionerError("plan.arguments: expected_object")
    if spawning and value["arguments"]:
        raise AdaptivePractitionerError(
            "SPAWN_LOOP requires arguments {}; spawned input bindings are not "
            "supported by this method contract")
    try:
        arguments = json.loads(json.dumps(value["arguments"], allow_nan=False))
    except (TypeError, ValueError):
        raise AdaptivePractitionerError("plan.arguments: expected_strict_json") from None
    steps = _short_strings(value["steps"], "plan.steps")
    plan = ExecutionPlan(
        _short_text(value["how_mode"], "plan.how_mode"), act_mode,
        handle=capability_ref, steps=steps, spawned_loops=tuple(spawned),
        experiment={"arguments": arguments, "action_id": chosen.action},
        rationale=_short_text(value["rationale"], "plan.rationale"))
    # Publish only the fully admitted plan. Rejected modes and spawned records
    # must not overwrite the previous method or mark its canvas selected.
    serialized_spawned = []
    for spec in spawned:
        seed = dict(spec.seed_facts)
        assignment = assignment_task_view(spec)
        if assignment is not None:
            seed[ASSIGNMENT_KEY] = assignment
        serialized_spawned.append(asdict(replace(spec, seed_facts=seed)))
    services.plan_details[chosen.action] = {
        "capability_ref": capability_ref, "arguments": arguments,
        "spawned_tasks": serialized_spawned,
        "steps": list(steps),
    }
    for candidate in services.plan_details.get(
            "current_candidate_canvases", []):
        candidate["selected"] = candidate["candidate_id"] == (
            f"canvas:{chosen.action}")
    return plan


def record_plan_outline(plan, action_id: str, services) -> None:
    """Save the admitted method as a readable outline artifact.

    Auxiliary only: a failed write degrades to a diagnostic, never to
    a failed step — the plan itself was already admitted.
    """
    lines = [f"# Plan outline: {action_id}",
             f"- how: {plan.how_mode} / act: {plan.act_mode}",
             f"- capability: {plan.handle or '(none)'}",
             f"- rationale: {plan.rationale}"]
    steps = list(plan.steps or ())
    if steps:
        lines.append("- steps:")
        lines.extend(f"  {index}. {step}"
                     for index, step in enumerate(steps, start=1))
    spawned = list(plan.spawned_loops or ())
    if spawned:
        lines.append(f"- spawned subproblems: {len(spawned)}")
        for spec in spawned:
            lines.append(f"  - {getattr(spec, 'goal', spec)}")
    try:
        ref = services.artifacts.capture(
            "\n".join(lines) + "\n", media_type="text/plain",
            artifact_kind="plan_outline")
        services.plan_details["plan_outline_ref"] = (
            ref.to_dict() if hasattr(ref, "to_dict") else str(ref))
    except OSError as exc:
        services.publish("practitioner.diagnostic",
                         diagnostic_code="plan_outline_unwritten",
                         error_type=type(exc).__name__)


def build_execution_plan(
        request: AdaptivePlanningRequest,
        services: AdaptiveRunServices) -> ExecutionPlan:
    """Select, validate, and if needed repair one execution method."""
    chosen = request.chosen
    action = services.action_details[chosen.action]
    if action.action_kind == RUN_PARALLEL:
        services.plan_details[chosen.action] = {
            "arguments": {}, "spawned_tasks": [],
            "validation_failure": _PARALLEL_UNAVAILABLE}
        return ExecutionPlan(
            "use", "run_direct", handle="core.invalid",
            experiment={"action_id": chosen.action},
            rationale=_PARALLEL_UNAVAILABLE)
    if action.action_kind in _TERMINAL_HANDLES:
        services.plan_details[chosen.action] = {
            "arguments": {}, "spawned_tasks": []}
        return ExecutionPlan(
            "use", "run_direct",
            handle=_TERMINAL_HANDLES[action.action_kind],
            experiment={"action_id": chosen.action},
            rationale=action.reason)
    if action_needs_execution_capability(action.action_kind) and not action.required_capabilities:
        services.plan_details[chosen.action] = {
            "arguments": {}, "spawned_tasks": [],
            "validation_failure": (
                "selected action did not bind an executable capability")}
        return ExecutionPlan(
            "use", "run_direct", handle="core.invalid",
            experiment={"action_id": chosen.action},
            rationale=(
                "This planner requires a registered execution capability for "
                "the selected action; no method call was dispatched."))
    failure = ""
    for attempt in (1, 2):
        try:
            value = services.model(ModelStepRequest(
                "how", ("Design the method for the selected next action."
                        if attempt == 1 else
                        "Repair the rejected method without changing the "
                        "action."),
                {
                    "state_version": request.state.version,
                    "facts": request.state.facts,
                    "artifact_refs": request.state.artifacts,
                    "failures": list(request.state.failures),
                    "selected_action_id": chosen.action,
                    "selected_action": action.to_dict(),
                    "orientation": request.situation.knowns[
                        "orientation"].to_dict(),
                    "method_validation_failure": failure,
                    **({"dependency_binding_contract": {
                        "scope": "same admitted serial plan only",
                        "legacy_independent_assignments": "objective, constraints, success_criteria remain supported",
                        "inputs": [{"role": "result/v1", "source_task_id": "producer-task-id",
                                    "source_role": "result/v1", "value_contract_ref": "value/v1",
                                    "delivery": "value|reference"}],
                        "output_contract": {"role": "result/v1", "value_contract_ref": "value/v1",
                                            "schema": {}, "result_path": ["value"]},
                        "output_path_origin": "the accepted result envelope, not the full private spawned-task state",
                        "barrier_only_output": None,
                    }} if action.action_kind == "SPAWN_LOOP" else {}),
                }, _planning_schema(
                    chosen.action, spawning=action.action_kind == "SPAWN_LOOP"),
                admission_contract=_planning_response_contract(chosen.action,action)))
            return _validate_plan_response(value, request, services)
        except ModelResponseRepairStalled as exc:
            from .adaptive_practitioner_recovery import recover_step_contract_failure
            recover_step_contract_failure(exc,{
                'state_version':request.state.version,'facts':request.state.facts,
                'artifact_refs':request.state.artifacts,'failures':list(request.state.failures),
                'selected_action_id':chosen.action,'selected_action':action.to_dict(),
                'response_contract':_planning_response_contract(chosen.action,action).to_dict(),
            },services)
            failure = str(exc)[:500]
            break
        except (AdaptivePractitionerError, SolutionModelError,
                TypeError, ValueError) as exc:
            failure = str(exc)[:500]
            services.diagnostic("execution_plan_invalid", {
                "attempt": attempt, "error": failure,
                "selected_action_id": chosen.action})
    services.plan_details[chosen.action] = {
        "capability_ref": "", "arguments": {}, "spawned_tasks": [],
        "steps": [], "validation_failure": failure}
    return ExecutionPlan(
        "use", "run_direct", handle="core.invalid",
        experiment={"action_id": chosen.action},
        rationale=f"method selection remained invalid: {failure}")


def self_test() -> dict:
    """Exercise admission and repair without model calls or effects."""
    from .adaptive_practitioner_planning_checks import run_checks
    return run_checks()
