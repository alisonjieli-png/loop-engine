"""Pure temporal checks for stage-evidence projection and rebuild.

The functions return a reason string rather than writing storage or raising a
projection-specific exception. The projection remains the adapter and error
authority; this module only compares immutable event positions.
"""
from __future__ import annotations

from .stage_evidence_records import (
    StageOccurrenceIdentity,
    StageRetrievalCandidate,
    StageRetrievalSnapshot,
)


def occurrence_source_error(record, event, events) -> str:
    """Explain why an occurrence is not backed by prior activation/call events."""
    if record.run_id != event.run_id or record.loop_id != event.loop_id:
        return "occurrence run and Loop must match its Run History event"
    loop_init = next((item for item in events
                      if item.event_type == "loop_init"
                      and item.loop_id == record.loop_id), None)
    if loop_init is None:
        return "occurrence Loop has no Run History initialization event"
    if loop_init.sequence_number >= event.sequence_number:
        return "occurrence Loop initialization must precede its evidence event"
    init_detail = loop_init.detail if isinstance(loop_init.detail, dict) else {}
    activation_id = str(init_detail.get("activation_id") or loop_init.loop_id)
    if record.activation_id != activation_id:
        return "occurrence activation does not match its Loop init"
    model_event = next((item for item in events
                        if item.event_type == "model_invocation"
                        and str((item.detail if isinstance(item.detail, dict)
                                 else {}).get("semantic_call_id") or "")
                        == record.semantic_call_id), None)
    if model_event is None:
        return "occurrence semantic call has no model-invocation event"
    if model_event.sequence_number >= event.sequence_number:
        return "occurrence model invocation must precede its evidence event"
    detail = model_event.detail if isinstance(model_event.detail, dict) else {}
    if str(detail.get("owner_loop_id") or "") != record.loop_id:
        return "semantic-call event does not name the occurrence owner Loop"
    return ""


def rebuild_temporal_error(positioned_rows) -> str:
    """Require source and target occurrence evidence before retrieval records."""
    positions = {
        record.occurrence_ref: position
        for (record, _event, _head, _events), position in positioned_rows
        if isinstance(record, StageOccurrenceIdentity)
    }
    for (record, _event, _head, _events), position in positioned_rows:
        if isinstance(record, StageRetrievalCandidate):
            required = (record.source_occurrence_ref,)
        elif isinstance(record, StageRetrievalSnapshot):
            required = (record.occurrence_ref, *(
                candidate.source_occurrence_ref
                for candidate in record.candidates))
        else:
            continue
        if any(positions.get(reference) is None
               or positions[reference] >= position for reference in required):
            return ("rebuild requires occurrence evidence before every "
                    "retrieval record")
    return ""


__all__ = ("occurrence_source_error", "rebuild_temporal_error")
