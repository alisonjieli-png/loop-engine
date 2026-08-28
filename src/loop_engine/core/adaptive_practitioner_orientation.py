"""Deterministic orientation policy for the adaptive Practitioner.

This module resolves only model-internal ambiguity classification conflicts.
It does not interpret a task, choose a domain solution, or grant authority.
"""
from __future__ import annotations

from dataclasses import replace

from .adaptive_practitioner_records import (
    AmbiguityDisposition, TaskOrientationResult)


def orientation_policy_findings(
        orientation: TaskOrientationResult,
        interaction_mode: str) -> list[str]:
    """Return typed-policy conflicts in one proposed orientation."""
    findings = []
    states_by_subject: dict[str, set[str]] = {}
    for item in orientation.ambiguities:
        states_by_subject.setdefault(item.subject.strip().lower(), set()).add(
            item.state)
    for subject, states in states_by_subject.items():
        if len(states) > 1:
            findings.append(
                f"ambiguity subject {subject!r} has competing states")
    delegated_text = " ".join(
        (*orientation.delegated_choices, *orientation.safe_defaults)).lower()
    delegated_terms = {
        term for term in delegated_text.replace("_", " ").split()
        if len(term) >= 4}
    for item in orientation.ambiguities:
        subject_terms = {
            term for term in item.subject.lower().replace("_", " ").split()
            if len(term) >= 4}
        if (item.state == "USER_CLARIFICATION_REQUIRED"
                and subject_terms & delegated_terms):
            findings.append(
                f"{item.subject!r} is both delegated/defaultable and marked "
                "for user clarification")
    if (orientation.proposed_next_action == "ASK_USER"
            and not orientation.blocking_questions):
        findings.append("ASK_USER has no material blocking question")
    if (interaction_mode == "autonomous"
            and orientation.proposed_next_action == "ASK_USER"
            and orientation.delegated_choices):
        findings.append(
            "autonomous orientation asks despite recorded delegated choices")
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
        findings.append(
            "verification obligations describe the orientation packet rather "
            "than the user's final task acceptance contract")
    return findings


def _orientation_terms(value: str) -> set[str]:
    generic = {
        "choice", "field", "meaning", "selected", "selection", "source",
        "specific", "task", "type", "value"}
    return {term.strip(".,:;!?()[]")
            for term in value.lower().replace("_", " ").split()
            if len(term.strip(".,:;!?()[]")) >= 4
            and term.strip(".,:;!?()[]") not in generic}


def normalize_orientation_choices(
        orientation: TaskOrientationResult) -> tuple:
    """Resolve delegated, derived, defaultable, and research classifications."""
    delegated = tuple(orientation.delegated_choices)
    defaults = tuple(orientation.safe_defaults)
    research = tuple(orientation.research_questions)
    normalized = []
    changes = []
    removed_subjects = []
    for item in orientation.ambiguities:
        terms = _orientation_terms(item.subject)
        subject_text = item.subject.lower().replace("_", " ").strip()
        delegated_match = any(
            subject_text in value.lower().replace("_", " ")
            or value.lower().replace("_", " ").strip() in subject_text
            or bool(terms & _orientation_terms(value)) for value in delegated)
        default_matches = [value for value in defaults
                           if terms & _orientation_terms(value)]
        reason_terms = _orientation_terms(item.reason)
        depends_on_choice = (
            ("depend" in item.reason.lower()
             or "derived" in item.reason.lower()) and bool(delegated))
        research_match = any(
            (terms | reason_terms) & _orientation_terms(value)
            for value in research)
        normalizable = item.state in (
            "UNKNOWN", "AMBIGUOUS", "USER_CLARIFICATION_REQUIRED")
        if normalizable and (
                delegated_match or default_matches or depends_on_choice
                or research_match):
            derived = depends_on_choice or any(
                "deriv" in value.lower() or "determin" in value.lower()
                for value in default_matches)
            state = ("DERIVED_VALUE" if derived else
                     "DELEGATED_CHOICE" if delegated_match else
                     "RESEARCH_REQUIRED" if research_match else
                     "DEFAULTABLE_CHOICE")
            normalized.append(AmbiguityDisposition(
                item.subject, state,
                "Normalized from conflicting clarification state under the "
                "accepted delegated/default policy."))
            removed_subjects.append((subject_text, terms))
            changes.append({"subject": item.subject, "state": state})
        else:
            normalized.append(item)
    questions = tuple(
        question for question in orientation.blocking_questions
        if not any(
            (subject and subject in question.lower().replace("_", " "))
            or bool(_orientation_terms(question) & terms)
            for subject, terms in removed_subjects))
    proposed = orientation.proposed_next_action
    if proposed == "ASK_USER" and not questions:
        proposed = "Continue with the normalized delegated or derived choice."
    return replace(
        orientation, ambiguities=tuple(normalized),
        blocking_questions=questions,
        proposed_next_action=proposed), tuple(changes)
