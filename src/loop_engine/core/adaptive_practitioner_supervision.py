"""Deterministic progress and breakout laws for the adaptive Practitioner.

The semantic resolver may propose research, repair, or continuation. These
pure controls decide whether the proposal represents executable work and
whether repeated passes have changed the governed task state.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PractitionerSupervisionPolicy:
    """Define when governed diagnosis is required without deciding the route."""

    maximum_research_actions_after_project: int = 3
    maximum_unchanged_progress_snapshots: int = 3


DEFAULT_SUPERVISION_POLICY = PractitionerSupervisionPolicy()


def _research_after_latest_intervention(services) -> int:
    if not services.project_attempts:
        return 0
    evidence_at_project = int(
        services.project_attempts[-1].get("context_evidence_count", 0))
    baseline = max(evidence_at_project, services.recovery_evidence_baseline)
    return max(0, len(services.web_results) - baseline)


def supervision_context(services, state) -> dict:
    """Return the bounded control state exposed to semantic decisions."""
    policy = DEFAULT_SUPERVISION_POLICY
    research_used = _research_after_latest_intervention(services)
    return {
        "record_type": "practitioner_supervision_context/v1",
        "research_actions_after_latest_project": research_used,
        "research_actions_remaining_after_project": max(
            0, policy.maximum_research_actions_after_project - research_used),
        "project_attempts": len(services.project_attempts),
        "verified_project_attempts": sum(
            bool(item.get("deterministic_checks_passed"))
            for item in services.project_attempts),
        "artifact_refs": sorted(str(key) for key in state.artifacts),
        "unchanged_progress_snapshots": services.unchanged_progress_snapshots,
        "recovery_rounds": services.recovery_rounds,
        "active_recovery_directive": (
            services.active_recovery_directive),
    }


def validate_progressing_action(decision, services) -> None:
    """Reject non-executable or explicitly repeated post-diagnosis actions."""
    capabilities = set(decision.required_capabilities)
    if (decision.action_kind == "REPAIR" and services.project_attempts
            and not capabilities):
        raise ValueError(
            "A repair after an executable attempt must bind a registered "
            "capability or stop honestly.")
    if services.active_recovery_directive:
        directive = services.active_recovery_directive
        forbidden = set(directive.get("forbidden_action_kinds", ()))
        if decision.action_kind in forbidden:
            raise ValueError(
                "The selected recovery directive forbids repeating this "
                "action kind without new evidence.")


def _progress_snapshot(services, state) -> tuple:
    unique_evidence = tuple(sorted({
        str(item.get("sha256") or "") for item in services.web_results
        if item.get("sha256")}))
    projects = tuple(
        (str(item.get("manifest_digest") or ""),
         bool(item.get("deterministic_checks_passed")))
        for item in services.project_attempts)
    return (
        unique_evidence,
        projects,
        tuple(sorted(str(key) for key in state.artifacts)),
    )


def detect_stall(services, state) -> dict | None:
    """Return a typed stall signal; never choose a repair or terminal route."""
    snapshot = _progress_snapshot(services, state)
    previous = (
        services.progress_snapshots[-1]
        if services.progress_snapshots else None)
    services.progress_snapshots.append(snapshot)
    if snapshot == previous:
        services.unchanged_progress_snapshots += 1
    else:
        services.unchanged_progress_snapshots = 0
        services.active_recovery_directive = None
    policy = DEFAULT_SUPERVISION_POLICY
    reasons = []
    if (services.unchanged_progress_snapshots
            >= policy.maximum_unchanged_progress_snapshots):
        reasons.append("governed task state did not measurably change")
    research_used = _research_after_latest_intervention(services)
    if (services.project_attempts and research_used
            >= policy.maximum_research_actions_after_project):
        reasons.append("post-project research repeated without resolution")
    if not reasons:
        return None
    finding = {
        "record_type": "practitioner_stall_signal/v1",
        "code": "RECOVERY_DIAGNOSIS_REQUIRED",
        "unchanged_snapshots": services.unchanged_progress_snapshots,
        "research_actions_since_intervention": research_used,
        "reasons": reasons,
        "progress_snapshot": {
            "unique_evidence": len(snapshot[0]),
            "project_attempts": len(snapshot[1]),
            "artifact_refs": len(snapshot[2]),
        },
    }
    services.supervision_findings.append(finding)
    return finding
