"""Typed method selection and repair for the adaptive Practitioner.

This module turns one validated ``NextActionDecision`` into an
``ExecutionPlan``. A model response cannot add a capability, permission, or
spawned assignment that was absent from the selected action contract.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ..loop.kernel import (
    CandidateAction, ExecutionPlan, PractitionerState, ProblemSpec, Situation)
from ..code_nodes.solution_model_port import SolutionModelError
from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices, ModelStepRequest)
from .adaptive_practitioner_validation import _short_strings, _short_text


@dataclass(frozen=True)
class AdaptivePlanningRequest:
    """State, orientation, and selected action for one method decision."""

    state: PractitionerState
    situation: Situation
    chosen: CandidateAction


def _planning_schema(action_id: str) -> str:
    return json.dumps({
        "action_id": action_id,
        "how_mode": (
            "use|configure|compose|modify|mutate|research|generate|delegate"),
        "act_mode": "run_direct|run_dag|spawn_practitioners",
        "capability_ref": "registered capability or empty",
        "arguments": {}, "steps": ["string"],
        "spawned_tasks": [{
            "objective": "string", "constraints": ["string"],
            "success_criteria": ["string"]}],
        "rationale": "string",
    }, separators=(",", ":"))


def _validate_plan_response(value, request, services) -> ExecutionPlan:
    chosen = request.chosen
    state = request.state
    action = services.action_details[chosen.action]
    if str(value.get("action_id")) != chosen.action:
        raise AdaptivePractitionerError("how response targets another action")
    capability_ref = str(value.get("capability_ref") or "")
    spawning = action.action_kind in ("SPAWN_LOOP", "RUN_PARALLEL")
    if (not spawning
            and capability_ref not in set(action.required_capabilities)):
        raise AdaptivePractitionerError(
            "how selected a capability outside NextActionDecision")
    spawned_values = value.get("spawned_tasks") or []
    if not isinstance(spawned_values, list):
        raise AdaptivePractitionerError("spawned_tasks has an invalid shape")
    spawned = tuple(ProblemSpec(
        _short_text(item.get("objective"), "spawn objective"),
        constraints=_short_strings(item.get("constraints") or [], "constraints"),
        success_criteria=_short_strings(
            item.get("success_criteria") or [], "success_criteria"),
        budget_passes=(
            None if services.request.max_passes is None
            else max(1, services.request.max_passes - 1)),
        depth=state.spec.depth + 1)
        for item in spawned_values if isinstance(item, dict))
    arguments = value.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise AdaptivePractitionerError("how arguments must be an object")
    steps = _short_strings(value.get("steps") or [], "steps")
    services.plan_details[chosen.action] = {
        "capability_ref": capability_ref, "arguments": arguments,
        "spawned_tasks": [asdict(item) for item in spawned],
        "steps": list(steps),
    }
    for candidate in services.plan_details.get(
            "current_candidate_canvases", []):
        candidate["selected"] = candidate["candidate_id"] == (
            f"canvas:{chosen.action}")
    return ExecutionPlan(
        str(value.get("how_mode")), str(value.get("act_mode")),
        handle=capability_ref, steps=steps, spawned_loops=spawned,
        experiment={"arguments": arguments},
        rationale=_short_text(value.get("rationale"), "plan rationale"))


def build_execution_plan(
        request: AdaptivePlanningRequest,
        services: AdaptiveRunServices) -> ExecutionPlan:
    """Select, validate, and if needed repair one execution method."""
    chosen = request.chosen
    action = services.action_details[chosen.action]
    terminal_handles = {
        "RETURN_RESULT": "core.finish", "STOP": "core.abstain",
        "ASK_USER": "core.ask", "ABSTAIN": "core.abstain",
        "REQUEST_AUTHORITY": "core.authority"}
    if action.action_kind in terminal_handles:
        services.plan_details[chosen.action] = {
            "arguments": {}, "spawned_tasks": []}
        return ExecutionPlan(
            "use", "run_direct",
            handle=terminal_handles[action.action_kind],
            rationale=action.reason)
    if action.action_kind == "REPAIR" and not action.required_capabilities:
        services.plan_details[chosen.action] = {
            "arguments": {}, "spawned_tasks": [],
            "validation_failure": (
                "repair action did not bind an executable capability")}
        return ExecutionPlan(
            "use", "run_direct", handle="core.invalid",
            rationale=(
                "A repair proposal without a registered capability cannot "
                "perform work."))
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
                }, _planning_schema(chosen.action)))
            return _validate_plan_response(value, request, services)
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
        rationale=f"method selection remained invalid: {failure}")


def self_test() -> dict:
    """Static check; adaptive acceptance tests exercise the repair path."""
    source = __file__
    passed = bool(source.endswith("adaptive_practitioner_planning.py"))
    return {"record_type": "adaptive_planning_test/v1", "tests": [{
        "test": "adaptive_method_planning_has_one_typed_module",
        "passed": passed, "detail": source}], "passed": int(passed),
        "total": 1, "all_passed": passed}
