"""Validation policy for model-proposed Practitioner orientation.

This module reports internal conflicts. It never rewrites semantic choices,
interprets a task, chooses a solution, or grants authority.
"""
from __future__ import annotations

from .adaptive_practitioner_records import TaskOrientationResult


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
            findings.append(
                f"{item.subject!r} is both delegated, defaultable, or "
                "researchable and marked "
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
