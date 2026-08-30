"""Model-led diagnosis and strategy mutation for stalled work.

Deterministic supervision emits a stall signal. This module asks separate
model steps to diagnose the failure, propose any useful changed strategies,
and adjudicate one recovery directive. The directive is passive data; the
normal Practitioner decision and capability validation path remains
authoritative.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices, ModelStepRequest)
from .adaptive_practitioner_validation import _short_strings, _short_text


RECOVERY_ROUTES = (
    "continue", "retry", "repair", "explore_branch", "reframe",
    "soft_reset", "cold_restart", "stop_unprofitable")
RECOVERY_CHANGE_KINDS = (
    "configure", "modify", "mutate", "compose", "repair", "research",
    "reframe", "delegate")
_ROUTE_BY_CHANGE_KIND = {
    "configure": "repair", "modify": "repair", "mutate": "repair",
    "compose": "repair", "repair": "repair", "research": "continue",
    "reframe": "reframe", "delegate": "explore_branch"}


@dataclass(frozen=True)
class RecoveryPanelRequest:
    """One stall signal plus the safe state visible to the panel."""

    stall_signal: dict
    model_state: dict
    pass_number: int


def _diagnosis_schema() -> str:
    return json.dumps({
        "diagnosis_id": "string",
        "root_causes": [{
            "cause": "string", "evidence_refs": ["string"],
            "confidence": 0.0}],
        "failed_strategy": "string",
        "missing_context": ["string"],
        "invalid_assumptions": ["string"],
        "recommended_change_types": [
            "configure|mutate|compose|research|reframe|delegate"],
    }, separators=(",", ":"))


def _proposal_schema() -> str:
    return json.dumps({"proposals": [{
        "proposal_id": "unique string",
        "change_kind": (
            "configure|modify|mutate|compose|repair|research|reframe|delegate"),
        "directive": "string",
        "required_capabilities": ["registered capability ref"],
        "expected_progress": "string",
        "risks": ["string"],
        "confidence": 0.0,
    }]}, separators=(",", ":"))


def _adjudication_schema() -> str:
    return json.dumps({
        "selected_proposal_id": "string",
        "reason": "string",
        "confidence": 0.0,
    }, separators=(",", ":"))


def _validate_diagnosis(value: dict) -> dict:
    diagnosis_id = _short_text(
        value.get("diagnosis_id"), "diagnosis_id", 120)
    roots = value.get("root_causes")
    if not isinstance(roots, list) or not roots:
        raise AdaptivePractitionerError(
            "recovery diagnosis needs at least one evidenced root cause")
    normalized = []
    for item in roots:
        if not isinstance(item, dict):
            raise AdaptivePractitionerError("root cause must be an object")
        normalized.append({
            "cause": _short_text(item.get("cause"), "root cause"),
            "evidence_refs": list(_short_strings(
                item.get("evidence_refs") or [], "evidence_refs")),
            "confidence": float(item.get("confidence", 0.0)),
        })
    changes = tuple(value.get("recommended_change_types") or ())
    if not changes or any(item not in RECOVERY_CHANGE_KINDS for item in changes):
        raise AdaptivePractitionerError(
            "diagnosis recommended unregistered change types")
    return {
        "diagnosis_id": diagnosis_id,
        "root_causes": normalized,
        "failed_strategy": _short_text(
            value.get("failed_strategy"), "failed_strategy"),
        "missing_context": list(_short_strings(
            value.get("missing_context") or [], "missing_context")),
        "invalid_assumptions": list(_short_strings(
            value.get("invalid_assumptions") or [], "invalid_assumptions")),
        "recommended_change_types": list(changes),
    }


def _validate_proposal(value: dict, services: AdaptiveRunServices) -> dict:
    route = str(value.get("route") or "")
    change_kind = str(value.get("change_kind") or "")
    if change_kind not in RECOVERY_CHANGE_KINDS:
        raise AdaptivePractitionerError("recovery proposal is not registered")
    route = _ROUTE_BY_CHANGE_KIND[change_kind]
    capabilities = tuple(value.get("required_capabilities") or ())
    registered = {item["capability_ref"]
                  for item in services.available_capabilities()}
    if set(capabilities) - registered:
        raise AdaptivePractitionerError(
            "recovery proposal names an unavailable capability")
    return {
        "proposal_id": _short_text(
            value.get("proposal_id"), "proposal_id", 120),
        "change_kind": change_kind,
        "route": route,
        "directive": _short_text(
            value.get("directive"), "recovery directive"),
        "required_capabilities": list(capabilities),
        "forbidden_action_kinds": [],
        "expected_progress": _short_text(
            value.get("expected_progress"), "expected_progress"),
        "risks": list(_short_strings(value.get("risks") or [], "risks")),
        "confidence": float(value.get("confidence", 0.0)),
    }


def _validate_proposals(value: dict, services: AdaptiveRunServices) -> tuple:
    raw = value.get("proposals")
    if not isinstance(raw, list) or not raw:
        raise AdaptivePractitionerError(
            "recovery needs at least one executable changed strategy")
    proposals = tuple(_validate_proposal(item, services)
                      for item in raw if isinstance(item, dict))
    if len(proposals) != len(raw):
        raise AdaptivePractitionerError(
            "every recovery proposal must be an object")
    identities = [item["proposal_id"] for item in proposals]
    if len(identities) != len(set(identities)):
        raise AdaptivePractitionerError("recovery proposal identities repeat")
    signatures = {
        (item["change_kind"], tuple(item["required_capabilities"]),
         item["directive"])
        for item in proposals}
    if len(signatures) != len(proposals):
        raise AdaptivePractitionerError(
            "recovery proposals must contain materially different changes")
    return proposals


def _resolve_validated_step(
        services: AdaptiveRunServices, step_id: str, objective: str,
        state: dict, schema: str, validator):
    """Give one rejected semantic result a bounded typed repair attempt."""
    failure = ""
    rejected = None
    for attempt in (1, 2):
        directive = (objective if attempt == 1 else
                     "Repair the rejected recovery result without changing "
                     "the task, authority, or requested schema.")
        value = services.model(ModelStepRequest(
            step_id, directive,
            {**state, "recovery_validation_failure": failure,
             "rejected_recovery_output": rejected}, schema))
        try:
            return validator(value)
        except (AdaptivePractitionerError, TypeError, ValueError) as exc:
            failure = str(exc)[:500]
            rejected = value
            services.diagnostic("recovery_step_invalid", {
                "step_id": step_id, "attempt": attempt, "error": failure})
    raise AdaptivePractitionerError(
        f"recovery step {step_id} remained invalid after one repair: {failure}")


def resolve_stall_with_panel(
        request: RecoveryPanelRequest,
        services: AdaptiveRunServices) -> dict:
    """Run diagnosis, two competing proposals, and independent adjudication."""
    common = {
        **request.model_state,
        "stall_signal": request.stall_signal,
        "pass_number": request.pass_number,
        "prior_recovery_directives": services.recovery_directives,
    }
    diagnosis = _resolve_validated_step(
        services, "diagnose_stall",
        "Diagnose why governed work stopped making useful progress.",
        common, _diagnosis_schema(), _validate_diagnosis)
    proposal_values = _resolve_validated_step(
        services, "propose_recovery",
        "Propose every useful executable changed strategy from the diagnosis. "
        "Do not repeat the same change under different wording.",
        {**common, "diagnosis": diagnosis}, _proposal_schema(),
        lambda value: _validate_proposals(value, services))
    proposals = {item["proposal_id"]: item for item in proposal_values}

    def validate_adjudication(raw_value):
        selected = _short_text(
            raw_value.get("selected_proposal_id"),
            "selected_proposal_id", 120)
        if selected not in proposals:
            raise AdaptivePractitionerError(
                "recovery adjudication selected an unknown proposal")
        reason = _short_text(
            raw_value.get("reason"), "recovery reason")
        confidence = float(raw_value.get("confidence", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise AdaptivePractitionerError(
                "recovery adjudication confidence must be from zero to one")
        return reason, confidence, selected

    adjudication_reason, adjudication_confidence, selected_id = (
        _resolve_validated_step(
        services, "adjudicate_recovery",
        "Select one recovery directive using evidence, progress, authority, and risk.",
        {**common, "diagnosis": diagnosis,
         "proposals": list(proposal_values)},
        _adjudication_schema(), validate_adjudication))
    adjudicated = proposals[selected_id]
    directive = {
        "record_type": "practitioner_recovery_directive/v1",
        "recovery_round": services.recovery_rounds + 1,
        "stall_signal": request.stall_signal,
        "diagnosis": diagnosis,
        "proposals": list(proposal_values),
        "selected_proposal_id": selected_id,
        "route": adjudicated["route"],
        "reason": adjudication_reason,
        "directive": adjudicated["directive"],
        "required_capabilities": adjudicated["required_capabilities"],
        "forbidden_action_kinds": adjudicated["forbidden_action_kinds"],
        "expected_progress": adjudicated["expected_progress"],
        "confidence": adjudication_confidence,
    }
    services.recovery_rounds += 1
    services.unchanged_progress_snapshots = 0
    services.recovery_directives.append(directive)
    services.active_recovery_directive = directive
    return directive
