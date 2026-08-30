"""Deterministic progress and breakout laws for the adaptive Practitioner.

The semantic resolver may propose research, repair, or continuation. These
pure controls decide whether the proposal represents executable work and
whether repeated passes have changed the governed task state.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class PractitionerSupervisionPolicy:
    """Require real progress without imposing a numerical work ceiling."""

    require_executable_repair_delta: bool = True
    diagnose_identical_state_action_failure: bool = True


DEFAULT_SUPERVISION_POLICY = PractitionerSupervisionPolicy()


def supervision_context(services, state) -> dict:
    """Return exact progress facts without deciding how much work is enough."""
    latest = _progress_snapshot(services, state)
    repeated = bool(services.progress_snapshots
                    and services.progress_snapshots[-1] == latest)
    return {
        "record_type": "practitioner_supervision_context/v1",
        "project_attempts": len(services.project_attempts),
        "verified_project_attempts": sum(
            bool(item.get("deterministic_checks_passed"))
            for item in services.project_attempts),
        "artifact_refs": sorted(str(key) for key in state.artifacts),
        "identical_state_action_failure_repeated": repeated,
        "progress_fingerprint": _snapshot_digest(latest),
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
    unique_web_evidence = tuple(sorted({
        str(item.get("sha256") or "") for item in services.web_results
        if item.get("sha256")}))
    unique_source_evidence = tuple(sorted({
        str(item.get("digest") or "")
        for inspection in services.source_inspections
        for item in inspection.get("selected", ())
        if item.get("digest")}))
    projects = tuple(sorted({
        (str(item.get("manifest_digest") or ""),
         bool(item.get("deterministic_checks_passed")))
        for item in services.project_attempts}))
    action = services.action_history[-1] if services.action_history else {}
    action_fingerprint = hashlib.sha256(json.dumps(
        action, sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest() if action else ""
    verification = (
        services.verification_records[-1]
        if services.verification_records else {})
    verification_fingerprint = hashlib.sha256(json.dumps(
        verification, sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest() if verification else ""
    return (
        unique_web_evidence,
        unique_source_evidence,
        projects,
        tuple(sorted(str(key) for key in state.artifacts)),
        action_fingerprint,
        verification_fingerprint,
        tuple(state.failures[-1:]),
    )


def _snapshot_digest(snapshot: tuple) -> str:
    return hashlib.sha256(json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), default=str
    ).encode()).hexdigest()


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
    if (not DEFAULT_SUPERVISION_POLICY.
            diagnose_identical_state_action_failure
            or snapshot != previous):
        return None
    reasons = [
        "the same state, action, evidence, and failure repeated without an "
        "executable delta"]
    finding = {
        "record_type": "practitioner_stall_signal/v1",
        "code": "RECOVERY_DIAGNOSIS_REQUIRED",
        "unchanged_snapshots": services.unchanged_progress_snapshots,
        "reasons": reasons,
        "progress_fingerprint": _snapshot_digest(snapshot),
        "progress_snapshot": {
            "unique_web_evidence": len(snapshot[0]),
            "unique_source_evidence": len(snapshot[1]),
            "project_attempts": len(snapshot[2]),
            "artifact_refs": len(snapshot[3]),
        },
    }
    services.supervision_findings.append(finding)
    return finding
