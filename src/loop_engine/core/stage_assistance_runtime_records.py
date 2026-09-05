"""Passive validation for product-path stage-assistance plumbing.

These helpers validate exact physical exposure correlation, solver decision
shape, and cheap frozen-source facts. They do not emit events, call a model,
retrieve candidates, execute an action, or grant authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .stage_evidence_records import STAGE_ASSISTANCE_DISPOSITIONS, START_FRESH


class StageAssistanceRuntimeRecordError(ValueError):
    """A product-path assistance record is malformed or mismatched."""


def source_ref_states(refs) -> tuple[dict, ...]:
    """Return cheap current identities for local frozen-comparison inputs."""
    states = []
    for ref in refs:
        if str(ref).startswith(("http://", "https://")):
            states.append({"ref": str(ref), "kind": "remote_reference"})
            continue
        path = Path(str(ref)).expanduser().resolve()
        try:
            stat = path.stat()
            states.append({
                "ref": str(ref), "resolved_path": str(path),
                "kind": "directory" if path.is_dir() else "file",
                "size": int(stat.st_size),
                "modified_ns": int(stat.st_mtime_ns),
            })
        except OSError as exc:
            states.append({
                "ref": str(ref), "resolved_path": str(path),
                "kind": "unavailable", "error_type": type(exc).__name__,
            })
    return tuple(states)


def physical_exposure(
        observation, snapshot: dict, *, packet_digest: str, gateway_result,
        format_attempt: int, transport_attempt: int) -> dict | None:
    """Build exact exposure correlation after at least one physical attempt."""
    physical = tuple(
        attempt for attempt in tuple(
            getattr(gateway_result, "attempts", ()) or ())
        if str(getattr(attempt, "loop_id", "") or ""))
    if not physical:
        return None
    semantic_call_id = str(
        getattr(observation, "semantic_call_id", "") or "")
    owner_loop_id = str(getattr(observation, "owner_loop_id", "") or "")
    if (str(getattr(gateway_result, "semantic_call_id", "") or "")
            != semantic_call_id
            or str(getattr(gateway_result, "owner_loop_id", "") or "")
            != owner_loop_id
            or any(
                str(getattr(item, "semantic_call_id", "") or "")
                != semantic_call_id
                or str(getattr(item, "owner_loop_id", "") or "")
                != owner_loop_id for item in physical)):
        raise StageAssistanceRuntimeRecordError(
            "physical exposure identity differs from the stage occurrence")
    physical_ids = tuple(str(item.loop_id) for item in physical)
    prompt_digest = str(snapshot.get("prompt_digest") or "")
    prompt_assembly_id = str(snapshot.get("assembly_id") or "")
    gateway_prompt_digest = str(
        getattr(gateway_result, "prompt_digest", "") or ""
    )
    gateway_request_digest = str(
        getattr(gateway_result, "request_digest", "") or ""
    )
    provider_request_digests = tuple(
        str(getattr(item, "provider_request_digest", "") or "")
        for item in physical
    )
    if (
        gateway_prompt_digest != prompt_digest
        or any(
            str(getattr(item, "prompt_digest", "") or "") != prompt_digest
            for item in physical
        )
        or len(gateway_request_digest) != 64
        or any(len(item) != 64 for item in provider_request_digests)
    ):
        raise StageAssistanceRuntimeRecordError(
            "gateway request digests do not match the rendered prompt"
        )
    material = json.dumps({
        "stage_occurrence_id": observation.occurrence_id,
        "semantic_call_id": semantic_call_id,
        "packet_digest": packet_digest,
        "prompt_digest": prompt_digest,
        "prompt_assembly_id": prompt_assembly_id,
        "gateway_request_digest": gateway_request_digest,
        "provider_request_digests": provider_request_digests,
        "physical_attempt_loop_ids": physical_ids,
    }, sort_keys=True, separators=(",", ":"))
    return {
        "exposure_ref": "stage-exposure:sha256:" + hashlib.sha256(
            material.encode("utf-8")).hexdigest(),
        "packet_digest": packet_digest, "prompt_digest": prompt_digest,
        "prompt_assembly_id": prompt_assembly_id,
        "gateway_request_digest": gateway_request_digest,
        "provider_request_digests": provider_request_digests,
        "format_attempt": format_attempt,
        "transport_attempt": transport_attempt,
        "physical_attempt_loop_ids": physical_ids,
    }


def validate_decision(raw_decision: object, *, mode: str, exposed_refs,
                      exposure: object) -> dict:
    """Validate one exact active-arm decision against its physical exposure."""
    if not isinstance(raw_decision, dict):
        raise StageAssistanceRuntimeRecordError(
            "stage_assistance_decision must be an object")
    expected_fields = {"disposition", "selected_prior_refs", "reason"}
    if set(raw_decision) != expected_fields:
        raise StageAssistanceRuntimeRecordError(
            "stage_assistance_decision fields do not match its schema")
    disposition = raw_decision.get("disposition")
    if disposition not in STAGE_ASSISTANCE_DISPOSITIONS:
        raise StageAssistanceRuntimeRecordError(
            "stage assistance disposition is not admitted")
    raw_selected = raw_decision.get("selected_prior_refs")
    if not isinstance(raw_selected, list) or any(
            not isinstance(item, str) for item in raw_selected):
        raise StageAssistanceRuntimeRecordError(
            "selected_prior_refs must be a JSON list of text")
    selected = tuple(raw_selected)
    if (len(selected) != len(set(selected))
            or any(not item for item in selected)):
        raise StageAssistanceRuntimeRecordError(
            "selected prior refs must be unique non-empty text")
    if not set(selected).issubset(tuple(exposed_refs or ())):
        raise StageAssistanceRuntimeRecordError(
            "the model selected a prior it was not exposed to")
    if mode == "fresh" and (disposition != START_FRESH or selected):
        raise StageAssistanceRuntimeRecordError(
            "a fresh arm permits only START_FRESH with no selected refs")
    if disposition in ("USE", "MODIFY") and len(selected) != 1:
        raise StageAssistanceRuntimeRecordError(
            f"{disposition} needs exactly one selected prior ref")
    if disposition == "COMBINE" and len(selected) < 2:
        raise StageAssistanceRuntimeRecordError(
            "COMBINE needs at least two selected prior refs")
    if disposition in ("IGNORE", "RETRIEVE_DEEPER", START_FRESH) and selected:
        raise StageAssistanceRuntimeRecordError(
            f"{disposition} cannot select prior refs")
    reason = raw_decision.get("reason")
    if (not isinstance(reason, str) or not reason.strip()
            or reason != reason.strip()):
        raise StageAssistanceRuntimeRecordError(
            "a stage assistance decision needs trimmed reason text")
    if (not isinstance(exposure, dict) or not exposure.get("exposure_ref")
            or not exposure.get("physical_attempt_loop_ids")):
        raise StageAssistanceRuntimeRecordError(
            "a stage assistance decision needs an actual physical exposure")
    return {"disposition": disposition, "selected_prior_refs": selected,
            "reason": reason, "exposure": exposure}


__all__ = (
    "StageAssistanceRuntimeRecordError", "physical_exposure",
    "source_ref_states", "validate_decision")
