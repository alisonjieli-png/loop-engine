"""Post-completion reuse observation for the adaptive Practitioner.

This helper extracts only verified generated-project references. A configured
``ReuseObservationPort`` performs the Loop-owned observation and placement.
Observer failure is recorded on the result and cannot invalidate source work.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .reusable_capability_harvest import (
    ReuseObservationPort, ReuseObservationRequest)


def observe_generated_project_reuse(
        owner, services, history: dict, solved: bool) -> dict | None:
    """Submit one verified generated project to an optional reuse sink."""
    port = services.dependencies.reuse_observation_port
    if port is None:
        return None
    if not isinstance(port, ReuseObservationPort):
        return {
            "record_type": "reuse_observation_status/v1",
            "status": "failed",
            "failure_class": "INVALID_REUSE_OBSERVATION_PORT",
        }
    if not solved or not services.project_attempts:
        return {
            "record_type": "reuse_observation_status/v1",
            "status": "not_observed",
            "reason": "source result is not a verified generated project",
        }
    attempt = services.project_attempts[-1]
    manifest_digest = str(attempt.get("manifest_digest") or "")
    manifest = attempt.get("manifest") or {}
    artifact_ref = str(
        attempt.get("workspace_path")
        or attempt.get("workspace", {}).get("workspace_id") or "")
    if (not attempt.get("deterministic_checks_passed")
            or len(manifest_digest) != 64 or not artifact_ref):
        return {
            "record_type": "reuse_observation_status/v1",
            "status": "not_observed",
            "reason": "verified artifact identity is incomplete",
        }
    definition = owner.definition_ref
    definition_ref = (
        f"{definition.definition_id}@{definition.version}"
        f"#{definition.content_digest}")
    head_digest = str(history.get("head_digest") or "")
    operation_family = "generated_project." + str(
        manifest.get("project_id") or "unclassified")
    request = ReuseObservationRequest(
        services.run_id, services.run_id, owner.loop_id,
        f"{owner.identity.profile_id}@{owner.identity.profile_version}",
        definition_ref, f"adaptive-result:{services.run_id}",
        f"run-history:{services.run_id}:{head_digest}", artifact_ref,
        manifest_digest, "python_project", operation_family,
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        True, True, port.dispatch)
    try:
        opportunity = port.submit(request)
    except Exception as exc:
        return {
            "record_type": "reuse_observation_status/v1",
            "status": "failed",
            "failure_class": type(exc).__name__,
            "detail": str(exc)[:500],
        }
    return {
        "record_type": "reuse_observation_status/v1",
        "status": "observed",
        "dispatch": port.dispatch.value,
        "opportunity": opportunity.to_dict(),
    }


__all__ = ("observe_generated_project_reuse",)
