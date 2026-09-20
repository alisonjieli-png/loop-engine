"""Persistent orientation for one Practitioner pass.

A rejected orientation proposal is a repair task, not the end of the run. The
step first asks again for the whole record with each finding quoted, then asks
only for the fields that the findings name, and finally carries an orientation
forward with every unresolved finding recorded. The declared supervision
policy decides when one repair strategy has stopped producing anything new.
Only an unavailable provider or spent model-call authority ends orientation.

Nothing here interprets the task, grants authority, or marks a carried
orientation as accepted. A carried orientation withholds exactly the fields
whose findings would otherwise aim later steps at the orientation protocol,
define acceptance by that protocol, or pause the run for a question that the
orientation policy did not accept.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Callable

from ..code_nodes.solution_model_port import SolutionModelError
from .adaptive_practitioner_orientation import (
    OrientationConflict, orientation_policy_conflicts)
from .adaptive_practitioner_records import (
    _unnamed_fields, AMBIGUITY_STATES,
    AdaptiveRunServices, ModelResponseRepairStalled, ModelStepRequest,
    TaskOrientationResult)
from .adaptive_practitioner_validation import AdaptivePractitionerError
from .semantic_decision import note_decision

#: The step objective names this step's work. The record's immediate goal
#: names the next useful part of the user's task, so the two stay distinct:
#: a live campaign copied the older objective into the immediate goal on
#: every attempt and every task.
ORIENTATION_OBJECTIVE = (
    "Orient on the user's task and return TaskOrientationResult version 1. "
    "Every field describes the user's task. The immediate goal is the next "
    "useful part of that task, never this orientation step.")
WHOLE_RECORD_REPAIR_OBJECTIVE = (
    "Repair the rejected TaskOrientationResult. Each recorded finding names a "
    "conflict. Change the fields it names so that every field describes the "
    "user's task rather than this orientation step.")
NAMED_FIELD_REPAIR_OBJECTIVE = (
    "Return only the orientation fields listed in orientation_field_repair, "
    "corrected so that each describes the user's task rather than this "
    "orientation step. The runtime keeps every other proposed field.")

#: Ordered repair strategies, each tried until the supervision policy shows
#: that it keeps producing the same rejected result.
ORIENTATION_REPAIR_STRATEGIES = ("whole_record", "named_fields")

#: Fields a carried orientation withholds when a finding names them, and the
#: value later steps receive instead. Every other named field stays as
#: proposed, with its finding recorded.
CARRIED_FIELD_REPLACEMENTS = {
    "immediate_goal": (
        "Unresolved after orientation repair: continue the user's task from "
        "the original task text and the current typed state."),
    "proposed_next_action": (
        "Continue from the original task text and the current typed state."),
    "blocking_questions": (),
}


def orientation_schema_fields() -> dict:
    """The TaskOrientationResult output contract, as a fresh mapping."""
    return {
        "original_task_ref": "sha256:<digest>",
        "task_summary": "string", "ultimate_goal": "string",
        "immediate_goal": "string", "current_state": "string",
        "desired_state": "string", "inputs": ["string"],
        "outputs": ["string"], "operator_bundle": ["string"],
        "response_contract": "string", "decision_consumer": "string",
        "explicit_constraints": ["string"],
        "inferred_constraints": ["string"], "non_goals": ["string"],
        "knowns": ["string"], "unknowns": ["string"],
        "assumptions": ["string"], "ambiguities": [{
            "subject": "string", "state": "|".join(AMBIGUITY_STATES),
            "reason": "string"}],
        "delegated_choices": ["string"], "safe_defaults": ["string"],
        "blocking_questions": ["string"],
        "research_questions": ["string"], "subproblems": ["string"],
        "dependencies": ["string"], "parallel_candidates": ["string"],
        "candidate_profiles": ["string"],
        "candidate_capabilities": ["string"],
        "verification_obligations": ["string"],
        "confidence_profile": {"overall": 0.0},
        "proposed_next_action": "string",
    }


@dataclass(frozen=True)
class OrientationResolutionRequest:
    """What one pass needs to resolve its orientation.

    ``model_state`` builds the model-visible state for each attempt, so an
    attempt never reuses a view assembled before an earlier attempt.
    """

    services: AdaptiveRunServices
    state_version: int
    model_state: Callable[[], dict]


@dataclass(frozen=True)
class _RejectedProposal:
    """The latest structurally valid proposal the policy did not accept."""

    orientation: TaskOrientationResult
    value: dict
    conflicts: tuple[OrientationConflict, ...]


def resolve_orientation(
        request: OrientationResolutionRequest) -> TaskOrientationResult:
    """Return an accepted, reused, or carried orientation for one pass."""
    services = request.services
    policy = services.request.effective_supervision
    failures: list[dict] = []
    repeats: dict[tuple, int] = {}
    seen_outputs: set[str] = set()
    strategy = ORIENTATION_REPAIR_STRATEGIES[0]
    rejected: "_RejectedProposal | None" = None
    attempt = 0
    while attempt < policy.non_accepted_iterations_before_stop:
        attempt += 1
        step = _step_request(request, strategy, attempt, failures, rejected)
        repeated_output = False
        try:
            value = services.model(step)
        except SolutionModelError as exc:
            services.diagnostic("orientation_provider_unavailable", {
                "attempt": attempt,
                "error_code": exc.error_code or "model_gateway_failed"})
            raise
        except ModelResponseRepairStalled as exc:
            # A stalled format repair is one failed attempt, not the end of
            # the run: the next attempt repairs with the stall on record.
            value = None
            findings = [f"{type(exc).__name__}: {str(exc)[:500]}"]
            failure_key = (type(exc).__name__, exc.failure_code)
            services.diagnostic("orientation_repair_stalled", {
                "attempt": attempt, "strategy": strategy,
                "failure_code": exc.failure_code,
                "format_attempts": exc.attempts})
        except AdaptivePractitionerError as exc:
            value = None
            findings = [f"{type(exc).__name__}: {str(exc)[:500]}"]
            failure_key = tuple(findings)
            services.diagnostic("orientation_model_unavailable", {
                "attempt": attempt, "strategy": strategy,
                "error_type": type(exc).__name__})
        else:
            if strategy == "named_fields" and rejected is not None:
                value = _with_named_fields(rejected, value)
            candidate, conflicts, findings = _evaluate(
                services, value, attempt)
            if candidate is not None and not findings:
                services.grade_current_stage(
                    observable_process_aligned=True,
                    expected_output_satisfied=True,
                    material_progress=True)
                if attempt > 1:
                    services.diagnostic("orientation_repaired", {
                        "attempt": attempt, "strategy": strategy})
                return candidate
            services.grade_current_stage(
                observable_process_aligned=False,
                expected_output_satisfied=False,
                material_progress=False)
            if candidate is not None:
                rejected = _RejectedProposal(
                    candidate, value, tuple(conflicts))
            # A byte-identical rejected proposal carries no new information,
            # so repeating the same request is not persistence.
            digest = hashlib.sha256(json.dumps(
                value, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            repeated_output = digest in seen_outputs
            seen_outputs.add(digest)
            failure_key = tuple(sorted(findings))
            services.diagnostic("orientation_invalid", {
                "attempt": attempt, "strategy": strategy,
                "findings": findings, "repeated_output": repeated_output})
        failures.append({
            "attempt": attempt, "strategy": strategy, "findings": findings,
            "rejected_orientation": value})
        repeats[failure_key] = repeats.get(failure_key, 0) + 1
        if (repeated_output or repeats[failure_key]
                >= policy.identical_failures_before_stop):
            following = _next_strategy(strategy, rejected)
            if following is None:
                break
            services.diagnostic("orientation_strategy_changed", {
                "attempt": attempt, "from_strategy": strategy,
                "to_strategy": following, "findings": findings})
            strategy, repeats = following, {}
    return _carry_forward(request, rejected, attempt, failures)


def _step_request(
        request: OrientationResolutionRequest, strategy: str, attempt: int,
        failures: list[dict],
        rejected: "_RejectedProposal | None") -> ModelStepRequest:
    """Build the model request for one attempt under the active strategy."""
    state = {**request.model_state(),
             "orientation_validation_failures": _recorded_failures(failures)}
    schema = orientation_schema_fields()
    if strategy == "named_fields" and rejected is not None:
        named = _named_fields(rejected.conflicts)
        state["orientation_field_repair"] = {
            "fields": list(named),
            "findings": [item.finding for item in rejected.conflicts],
            "rejected_values": {
                name: rejected.value.get(name) for name in named},
        }
        return ModelStepRequest(
            "orient", NAMED_FIELD_REPAIR_OBJECTIVE, state, json.dumps(
                {name: schema[name] for name in named},
                separators=(",", ":")))
    return ModelStepRequest(
        "orient",
        ORIENTATION_OBJECTIVE if attempt == 1
        else WHOLE_RECORD_REPAIR_OBJECTIVE,
        state, json.dumps(schema, separators=(",", ":")))


def _recorded_failures(failures: list[dict]) -> list[dict]:
    """Every finding so far, with the full rejected record only for the latest."""
    return [item if index == len(failures) - 1 else {
        key: value for key, value in item.items()
        if key != "rejected_orientation"}
        for index, item in enumerate(failures)]


def _evaluate(services: AdaptiveRunServices, value: object, attempt: int):
    """Validate one proposal and return the record, conflicts, and findings."""
    if isinstance(value, dict):
        value["original_task_ref"] = (
            "sha256:" + hashlib.sha256(
                services.request.task.encode("utf-8")).hexdigest())
    try:
        candidate = TaskOrientationResult.from_mapping(value)
        # Fields the schema does not name are carried, not refused,
        # so a caller with more to say than the form allows is not
        # answered with a rejection of all of it. They are reported
        # because tolerated-and-invisible is its own kind of loss.
        note_decision(
            services,
            decision_id=f"{services.run_id}.orient.{attempt}",
            decision_kind="interpret_task", owner="llm",
            selected=candidate.immediate_goal[:200],
            # What the task might have meant, in the run's own words.
            alternatives=tuple(
                item.subject for item in candidate.ambiguities)[:8],
            reason_summary=candidate.task_summary[:300],
            assumptions=tuple(candidate.assumptions)[:8],
            uncertainties=tuple(candidate.unknowns)[:8],
            expected_observation=candidate.desired_state[:200])
        unnamed = _unnamed_fields(value, TaskOrientationResult)
        if unnamed:
            services.diagnostic("orientation_carried_unnamed_fields", {
                "attempt": attempt, "fields": unnamed})
        conflicts = orientation_policy_conflicts(
            candidate, services.request.interaction_mode)
    except (AdaptivePractitionerError, ValueError) as exc:
        return None, [], [str(exc)]
    return candidate, conflicts, [item.finding for item in conflicts]


def _named_fields(conflicts) -> tuple[str, ...]:
    """The contract fields that the findings name, in a stable order."""
    schema = orientation_schema_fields()
    return tuple(sorted({
        name for item in conflicts for name in item.fields if name in schema}))


def _with_named_fields(rejected: _RejectedProposal, value: object) -> dict:
    """Apply only the named field replacements to the rejected proposal."""
    replacements = value if isinstance(value, dict) else {}
    return {**rejected.value, **{
        name: replacements[name]
        for name in _named_fields(rejected.conflicts)
        if name in replacements}}


def _next_strategy(
        strategy: str, rejected: "_RejectedProposal | None") -> "str | None":
    """The next repair strategy that applies, or None when all are spent."""
    position = ORIENTATION_REPAIR_STRATEGIES.index(strategy)
    for following in ORIENTATION_REPAIR_STRATEGIES[position + 1:]:
        if following != "named_fields" or (
                rejected is not None and _named_fields(rejected.conflicts)):
            return following
    return None


def _carry_forward(
        request: OrientationResolutionRequest,
        rejected: "_RejectedProposal | None", attempts: int,
        failures: list[dict]) -> TaskOrientationResult:
    """Continue the run with the best orientation available after repair."""
    services = request.services
    accepted = [version for version in services.orientation_by_version
                if version not in services.carried_orientation_by_version]
    if accepted:
        source_version = max(accepted)
        services.diagnostic("orientation_reused", {
            "source_state_version": source_version,
            "target_state_version": request.state_version})
        return replace(
            services.orientation_by_version[source_version],
            current_state=(
                "Latest accepted orientation reused after semantic resolver "
                "failure; typed Practitioner state remains authoritative."),
            proposed_next_action=(
                "Continue from the latest accepted orientation and current "
                "typed state."))
    latest_findings = failures[-1]["findings"] if failures else []
    withheld: dict = {}
    if rejected is not None:
        orientation, withheld = _withhold_named_fields(rejected)
        source = "rejected_proposal"
        latest_findings = [item.finding for item in rejected.conflicts]
    elif services.orientation_by_version:
        orientation = services.orientation_by_version[
            max(services.orientation_by_version)]
        source = "earlier_carried_orientation"
    else:
        orientation = _unresolved_orientation(services, attempts)
        source = "unresolved_orientation"
    record = {"source": source, "attempts": attempts,
              "findings": latest_findings, "withheld": withheld}
    services.carried_orientation_by_version[request.state_version] = record
    services.diagnostic("orientation_carried_forward", {
        "state_version": request.state_version, **record})
    return orientation


def _withhold_named_fields(
        rejected: _RejectedProposal) -> tuple[TaskOrientationResult, dict]:
    """Withhold only what the findings protect later consumers from."""
    orientation = rejected.orientation
    named = {name for item in rejected.conflicts for name in item.fields}
    protocol_items = {
        text for item in rejected.conflicts for text in item.protocol_items}
    changes: dict = {}
    withheld: dict = {}
    if protocol_items:
        withheld["verification_obligations"] = [
            text for text in orientation.verification_obligations
            if text in protocol_items]
        changes["verification_obligations"] = tuple(
            text for text in orientation.verification_obligations
            if text not in protocol_items)
    for name, replacement in CARRIED_FIELD_REPLACEMENTS.items():
        if name in named:
            current = getattr(orientation, name)
            withheld[name] = (list(current) if isinstance(current, tuple)
                              else current)
            changes[name] = replacement
    return replace(orientation, **changes), withheld


def _unresolved_orientation(
        services: AdaptiveRunServices, attempts: int) -> TaskOrientationResult:
    """A labeled orientation for a pass in which no proposal was admitted.

    Every value states that orientation is unresolved and that the original
    task text is authoritative. With no proposed verification obligation,
    acceptance is judged against that text, and the next pass orients again.
    """
    return TaskOrientationResult.from_mapping({
        "original_task_ref": "sha256:" + hashlib.sha256(
            services.request.task.encode("utf-8")).hexdigest(),
        "task_summary": (
            "Orientation is unresolved; the original task text is "
            "authoritative."),
        "ultimate_goal": "Complete the original task as its text states.",
        "immediate_goal": CARRIED_FIELD_REPLACEMENTS["immediate_goal"],
        "current_state": (
            f"No orientation proposal was admitted after {attempts} "
            "attempts; each finding is recorded in Run History."),
        "desired_state": (
            "The original task is complete and its result is verified."),
        "inputs": [], "outputs": [], "operator_bundle": [],
        "response_contract": (
            "The original task text states the response contract."),
        "decision_consumer": (
            "The requester named by the original task text."),
        "explicit_constraints": [], "inferred_constraints": [],
        "non_goals": [], "knowns": [],
        "unknowns": ["The task orientation is unresolved."],
        "assumptions": [], "ambiguities": [], "delegated_choices": [],
        "safe_defaults": [], "blocking_questions": [],
        "research_questions": [], "subproblems": [], "dependencies": [],
        "parallel_candidates": [], "candidate_profiles": [],
        "candidate_capabilities": [], "verification_obligations": [],
        "confidence_profile": {"overall": 0.0},
        "proposed_next_action": CARRIED_FIELD_REPLACEMENTS[
            "proposed_next_action"],
    })
