"""Validation policy for model-proposed Practitioner orientation.

This module reports internal conflicts and names the record fields that each
conflict concerns. It never rewrites semantic choices, interprets a task,
chooses a solution, or grants authority.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adaptive_practitioner_records import NEXT_ACTION_KINDS, TaskOrientationResult

#: The action kind that asks the user, named once from the action vocabulary.
ASK_USER_ACTION = NEXT_ACTION_KINDS[0]


@dataclass(frozen=True)
class OrientationConflict:
    """One typed-policy conflict and the orientation fields it concerns.

    ``fields`` names every field whose value the conflict involves, including
    the blocking questions whenever the conflict is about asking a person.
    ``protocol_items`` lists the entries of a sequence field that describe the
    orientation step itself rather than the user's task; the other entries of
    that field are not part of the conflict.
    """

    finding: str
    fields: tuple[str, ...]
    protocol_items: tuple[str, ...] = ()


def orientation_policy_findings(
        orientation: TaskOrientationResult,
        interaction_mode: str) -> list[str]:
    """Return typed-policy conflicts in one proposed orientation."""
    return [item.finding for item in orientation_policy_conflicts(
        orientation, interaction_mode)]


def orientation_policy_conflicts(
        orientation: TaskOrientationResult,
        interaction_mode: str) -> list[OrientationConflict]:
    """Return each typed-policy conflict with the fields it concerns."""
    conflicts = []
    states_by_subject: dict[str, set[str]] = {}
    for item in orientation.ambiguities:
        states_by_subject.setdefault(item.subject.strip().lower(), set()).add(
            item.state)
    for subject, states in states_by_subject.items():
        if len(states) > 1:
            conflicts.append(OrientationConflict(
                f"ambiguity subject {subject!r} has competing states",
                ("ambiguities", "blocking_questions")))
    delegated_text = " ".join(orientation.delegated_choices).lower()
    default_text = " ".join(orientation.safe_defaults).lower()
    research_text = " ".join(orientation.research_questions).lower()
    delegated_terms = _orientation_terms(delegated_text)
    default_terms = _orientation_terms(default_text)
    research_terms = _orientation_terms(research_text)
    for item in orientation.ambiguities:
        subject_terms = {
            term for term in item.subject.lower().replace("_", " ").split()
            if len(term) >= 4}
        overlaps = subject_terms & (
            delegated_terms | default_terms | research_terms)
        if item.state == "USER_CLARIFICATION_REQUIRED" and overlaps:
            conflicts.append(OrientationConflict(
                f"{item.subject!r} is both delegated, defaultable, or "
                "researchable and marked "
                "for user clarification",
                ("ambiguities", "delegated_choices", "safe_defaults",
                 "research_questions", "blocking_questions")))
    if (orientation.proposed_next_action == ASK_USER_ACTION
            and not orientation.blocking_questions):
        conflicts.append(OrientationConflict(
            "ASK_USER has no material blocking question",
            ("proposed_next_action", "blocking_questions")))
    user_clarifications = [
        item for item in orientation.ambiguities
        if item.state == "USER_CLARIFICATION_REQUIRED"]
    if orientation.blocking_questions and not user_clarifications:
        conflicts.append(OrientationConflict(
            "blocking questions require a USER_CLARIFICATION_REQUIRED "
            "ambiguity; runtime, capability, research, and authority questions "
            "must be resolved or reported by the Practitioner",
            ("blocking_questions", "ambiguities")))
    if (orientation.proposed_next_action == ASK_USER_ACTION
            and not user_clarifications):
        conflicts.append(OrientationConflict(
            "ASK_USER requires a typed user-clarification ambiguity",
            ("proposed_next_action", "ambiguities", "blocking_questions")))
    if (interaction_mode == "autonomous"
            and orientation.proposed_next_action == ASK_USER_ACTION
            and orientation.delegated_choices):
        conflicts.append(OrientationConflict(
            "autonomous orientation asks despite recorded delegated choices",
            ("proposed_next_action", "delegated_choices",
             "blocking_questions")))
    semantic_step_markers = (
        "taskorientationresult", "orientation result payload",
        "inline schema", "additional prose", "requested schema",
        "current semantic step", "unrequested final solution")
    leaked_obligations = [
        obligation for obligation in orientation.verification_obligations
        if any(marker in obligation.lower().replace(" ", "")
               if marker == "taskorientationresult"
               else marker in obligation.lower()
               for marker in semantic_step_markers)]
    if leaked_obligations:
        conflicts.append(OrientationConflict(
            "verification obligations describe the orientation packet rather "
            "than the user's final task acceptance contract",
            ("verification_obligations",), tuple(leaked_obligations)))
    immediate = orientation.immediate_goal.lower().replace(" ", "")
    if ("taskorientationresult" in immediate
            or "orientationresult" in immediate
            or "returnschema" in immediate):
        conflicts.append(OrientationConflict(
            "the immediate goal describes the orientation protocol rather than "
            "the next useful part of the user's task",
            ("immediate_goal",)))
    return conflicts


def _orientation_terms(value: str) -> set[str]:
    generic = {
        "choice", "field", "meaning", "selected", "selection", "source",
        "specific", "task", "type", "value"}
    return {term.strip(".,:;!?()[]")
            for term in value.lower().replace("_", " ").split()
            if len(term.strip(".,:;!?()[]")) >= 4
            and term.strip(".,:;!?()[]") not in generic}
