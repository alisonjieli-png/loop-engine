"""The canonical event vocabulary — one closed set of families, and the
total projection from runtime kinds into it.

Architectural role: internal event vocabulary service.

Split out of `run_history` on 2026-08-24 when that module crossed the 800-line
cap.  The split is not cosmetic: the VOCABULARY is referenced by the
conformance scanner, the SaaS routes, and the Studio independently of the
append-only history, so it was already a separate concern living in one file.
`run_history` re-exports every name, so no import site changed.

Owns:
    - EVENT_FAMILIES: the closed 59-family vocabulary (§20.2);
    - _CANONICAL_EVENT_MAP: total over every raw kind this package emits;
    - _EVENT_TYPE_FAMILY: the stored bucket -> family binding;
    - to_canonical_events(): the total, lossless projection;
    - canonical_event_coverage(): emitted vs declared-only, never conflated.

Does not own:
    - the RunHistory itself, persistence, or replay (run_history.py).

Key invariants:
    - a projection may only produce a declared family; anything else raises;
    - declaring a family is not claiming it — coverage separates the two.

Verification: exercised by run_history.self_test() and the vocabulary gate.
"""
from __future__ import annotations

#: The CLOSED canonical live-event vocabulary — every family the owner's
#: superseding directive of 2026-08-23 (§20.2) requires, and nothing else.
#: One vocabulary serves the command line, the browser, the event stream,
#: playback, profiling, and export (§3.8: no surface keeps a second semantic
#: event model).  A projection may only ever produce a family in this tuple;
#: producing anything else raises rather than inventing vocabulary.
EVENT_FAMILIES = (
    "run.started", "run.status_changed", "run.completed", "run.failed",
    "loop.initialized", "loop.started", "loop.iteration.started",
    "loop.iteration.completed", "loop.waiting", "loop.paused",
    "loop.resumed", "loop.completed", "loop.failed", "loop.spawn.requested",
    "loop.spawned.started", "loop.spawned.returned",
    "work_item.created", "work_item.selected", "work_item.completed",
    "work_item.deferred",
    "capability.snapshot.created", "capability.search.started",
    "capability.search.completed", "capability.selected",
    "capability.rejected",
    "intelligence.context.retrieved", "intelligence.code.retrieved",
    "intelligence.runtime_history_solution.retrieved", "intelligence.user_feedback.retrieved",
    "runtime_memory.message_written", "runtime_memory.message_read",
    "model.invocation.requested", "model.invocation.started",
    "model.invocation.completed", "model.invocation.failed",
    "tool.invocation.started", "tool.invocation.completed",
    "tool.invocation.failed",
    "solution.candidate.created", "solution.canvas.updated",
    "solution.loop.started", "solution.loop.completed", "solution.finalized",
    "evaluation.started", "evaluation.completed",
    "failure.detected", "recovery.started", "recovery.completed",
    "user_feedback_intelligence.submitted", "user_feedback_intelligence.attached",
    "user_feedback_intelligence.read", "user_feedback_intelligence.accepted",
    "user_feedback_intelligence.deferred", "user_feedback_intelligence.rejected",
    "user_feedback_intelligence.generalized",
    "learning.candidate.staged", "learning.candidate.validated",
    "state.committed", "change.proposed",
)

#: The four persistent intelligence layers, in the family name each retrieval
#: projects into.  An unknown layer raises — it never silently becomes
#: "string".
_INTELLIGENCE_LAYER_FAMILY = {
    "context": "intelligence.context.retrieved",
    "context_intelligence": "intelligence.context.retrieved",
    "code": "intelligence.code.retrieved",
    "code_intelligence": "intelligence.code.retrieved",
    "history": "intelligence.runtime_history_solution.retrieved",
    "runtime_history_solution_intelligence": "intelligence.runtime_history_solution.retrieved",
    "user": "intelligence.user_feedback.retrieved",
    "user_feedback_intelligence": "intelligence.user_feedback.retrieved",
}


#: terminal reasons that mean the loop REACHED its objective.  "success_once"
#: is the accepted-success stop of Article 4 — the most common stop in the
#: system — and an earlier version of this resolver treated everything except
#: "done" as failure, so every accepted-success stop projected as loop.failed.
#: That corrupted the vocabulary on the most-travelled path.
_ACCEPTED_TERMINAL_REASONS = ("done", "success_once")


def _terminal_family(e: dict) -> str:
    """A loop that reached its objective completed; a loop stopped by budget
    exhaustion or cancellation did NOT, so it projects as failed.  The exact
    reason is never lost — it rides in the source event."""
    return ("loop.completed"
            if e.get("reason") in _ACCEPTED_TERMINAL_REASONS
            else "loop.failed")


def _intelligence_family(e: dict) -> str:
    layer = str(e.get("layer", "string"))
    fam = _INTELLIGENCE_LAYER_FAMILY.get(layer)
    if fam is None:
        raise ValueError(
            f"intelligence pull declares layer {layer!r}, which is not one of "
            f"the four persistent layers {sorted(set(_INTELLIGENCE_LAYER_FAMILY))}")
    return fam


def _infra_family(e: dict) -> str:
    """A directory search is a capability search; every other infrastructure
    surface is a tool invocation."""
    return ("capability.search.completed"
            if str(e.get("surface", "")).endswith("_search")
            else "tool.invocation.completed")


def _mcp_terminal_family(e: dict) -> str:
    """Map every closed MCP result to an existing canonical family."""
    status = str(e.get("status", ""))
    families = {
        "completed": "tool.invocation.completed",
        "failed": "tool.invocation.failed",
        "approval_required": "loop.paused",
        "refused": "capability.rejected",
        "unavailable": "capability.rejected",
    }
    family = families.get(status)
    if family is None:
        raise ValueError(f"unknown MCP terminal status {status!r}")
    return family


def _skill_terminal_family(e: dict) -> str:
    status = str(e.get("status", ""))
    if status == "completed":
        return "intelligence.context.retrieved"
    if status == "failed":
        return "capability.rejected"
    raise ValueError(f"unknown skill terminal status {status!r}")


#: Raw runtime ledger kind -> canonical family.  A value may be a family name
#: or a resolver that reads the event.  TOTAL over every kind this package
#: emits: the ``unmapped_ledger_event_kind`` conformance detector fails the
#: build on any ``event="..."`` literal missing from this table, so the live
#: vocabulary can never drift away from the canonical one.
_CANONICAL_EVENT_MAP = {
    "init": "loop.initialized",
    # lifecycle + work-item markers real on the live runtime
    "loop.started": "loop.started",
    "work_item.selected": "work_item.selected",
    "work_item.completed": "work_item.completed",
    "evaluation.started": "evaluation.started",
    "evaluation.completed": "evaluation.completed",
    # plan() records the step->mode plan the loop WOULD run: those rows are
    # its work items, created before any of them executes.
    "step": "work_item.created",
    "run_step": "loop.iteration.completed",
    "kernel_run": "loop.iteration.completed",
    "spawn": "loop.spawned.started",
    "spawned_return": "loop.spawned.returned",
    "terminal": _terminal_family,
    "pause": "loop.paused",
    "resume": "loop.resumed",
    "cancel": "run.status_changed",
    "budget_stop": "run.status_changed",
    "model_boundary_deferred": "model.invocation.requested",
    # both escalation kinds record a model surface that was already invoked;
    # WHY it was invoked (hybrid escalation vs model-led) rides in the source.
    "model_escalation": "model.invocation.completed",
    "model_led": "model.invocation.completed",
    "model_invocation_failed": "model.invocation.failed",
    "model.invocation.started": "model.invocation.started",
    "model.invocation.failed": "model.invocation.failed",
    "fallback": "capability.rejected",
    "spec": "state.committed",
    "custom": "state.committed",
    "iteration_started": "loop.iteration.started",
    "tool_invocation_started": "tool.invocation.started",
    "tool_invocation_completed": "tool.invocation.completed",
    "tool_invocation_failed": "tool.invocation.failed",
    "learning_candidate_staged": "learning.candidate.staged",
    "solution_candidate_created": "solution.candidate.created",
    "solution_finalized": "solution.finalized",
    "work_item_deferred": "work_item.deferred",
    "learning_candidate_validated": "learning.candidate.validated",
    "user_feedback_intelligence_generalized": "user_feedback_intelligence.generalized",
    "change.proposed": "change.proposed",
    "run_completed": "run.completed",
    "run_failed": "run.failed",
    "run_started": "run.started",
    "loop_waiting": "loop.waiting",
    "spawned_requested": "loop.spawn.requested",
    "intelligence_pull": _intelligence_family,
    "intelligence.context.retrieved": "intelligence.context.retrieved",
    "intelligence.code.retrieved": "intelligence.code.retrieved",
    "intelligence.runtime_history_solution.retrieved": "intelligence.runtime_history_solution.retrieved",
    "intelligence.user_feedback.retrieved": "intelligence.user_feedback.retrieved",
    "infra_call": _infra_family,
    "runtime_memory.message_written": "runtime_memory.message_written",
    "runtime_memory.message_read": "runtime_memory.message_read",
    "solution.canvas.updated": "solution.canvas.updated",
    "solution.loop.started": "solution.loop.started",
    "capability.search.started": "capability.search.started",
    "capability.search.completed": "capability.search.completed",
    "capability.selected": "capability.selected",
    "capability.snapshot.created": "capability.snapshot.created",
    "failure.detected": "failure.detected",
    "recovery.started": "recovery.started",
    "recovery.completed": "recovery.completed",
    "solution.loop.completed": "solution.loop.completed",
    "user_guidance": "user_feedback_intelligence.read",
    "user_feedback_intelligence.attached": "user_feedback_intelligence.attached",
    "user_feedback_intelligence.submitted": "user_feedback_intelligence.submitted",
    "user_feedback_intelligence.accepted": "user_feedback_intelligence.accepted",
    "user_feedback_intelligence.deferred": "user_feedback_intelligence.deferred",
    "user_feedback_intelligence.rejected": "user_feedback_intelligence.rejected",
    # Safe operational observers reuse existing families. These raw kinds
    # preserve the exact lifecycle identity in RunHistory detail.
    "effect_approval_requested": "loop.paused",
    "effect_approval_decided": "loop.resumed",
    "context_artifact_stored": "state.committed",
    "context_compaction_completed": "state.committed",
    "mcp_call_terminal": _mcp_terminal_family,
    "skill_load_terminal": _skill_terminal_family,
}

#: The RunHistory's stored ``event_type`` is a COARSER storage bucket than the
#: canonical family (18 buckets over 59 families).  Binding every bucket to a
#: family here is what keeps it a projection of the one vocabulary instead of
#: a second semantic model: the suite asserts this table is total over
#: EVENT_TYPES and lands inside EVENT_FAMILIES.
_EVENT_TYPE_FAMILY = {
    "run_started": "run.started",
    "loop_init": "loop.initialized",
    "loop_spawn": "loop.spawned.started",
    "iteration": "loop.iteration.completed",
    "capability_search": "capability.search.completed",
    "context_retrieval": "intelligence.context.retrieved",
    "code_execution": "tool.invocation.completed",
    "model_invocation": "model.invocation.completed",
    "fallback": "capability.rejected",
    "model_boundary_deferred": "model.invocation.requested",
    "budget_stop": "run.status_changed",
    "evaluation": "evaluation.completed",
    "terminal": "loop.completed",
    "cancel": "run.status_changed",
    "solution_built": "solution.candidate.created",
    "solution_run": "solution.loop.completed",
    "learning": "learning.candidate.staged",
    "custom": "state.committed",
}


def family_of(event_type: str) -> str:
    """The canonical family a stored RunHistory event_type belongs to."""
    fam = _EVENT_TYPE_FAMILY.get(event_type)
    if fam is None:
        raise ValueError(f"event_type {event_type!r} has no canonical family")
    return fam


def to_canonical_events(ledger_events: list) -> list:
    """Project raw ledger events into the canonical live-event vocabulary.
    Every input event yields exactly one output event (len(out) == len(in))
    and the whole source event rides along, so the projection is total and
    lossless.  A kind this package does not own passes through as "x.<kind>"
    (a plugin's private event stays visible instead of vanishing); a kind it
    DOES own can never take that path — the conformance detector fails the
    build first.  Producing a family outside EVENT_FAMILIES raises."""
    out = []
    for e in ledger_events:
        kind = e.get("event", "custom")
        fam = _CANONICAL_EVENT_MAP.get(kind)
        if callable(fam):
            fam = fam(e)
        if fam is None:
            fam = f"x.{kind}"
        elif fam not in EVENT_FAMILIES:
            raise ValueError(f"{kind!r} projects to {fam!r}, which is not a "
                             "declared canonical event family")
        out.append({"type": fam, "source": e})
    return out


def canonical_event_coverage(ledger_events: "list | None" = None) -> dict:
    """The HONEST state of the canonical vocabulary: which families some raw
    runtime kind can actually produce, which are declared but have no emitter
    yet, and — when a run's events are supplied — which that run observed.
    Nothing here claims a family is live because it appears in EVENT_FAMILIES.
    """
    reachable = set()
    for fam in _CANONICAL_EVENT_MAP.values():
        if callable(fam):
            continue
        reachable.add(fam)
    # resolver-backed kinds reach every family their resolver can return
    reachable.update(_INTELLIGENCE_LAYER_FAMILY.values())
    reachable.update({"loop.completed", "loop.failed",
                      "capability.search.completed",
                      "tool.invocation.completed", "tool.invocation.failed",
                      "loop.paused", "capability.rejected"})
    reachable &= set(EVENT_FAMILIES)
    observed = set()
    if ledger_events is not None:
        observed = {c["type"] for c in to_canonical_events(ledger_events)}
    return {"record_type": "canonical_event_coverage/v1",
            "declared": len(EVENT_FAMILIES),
            "emitted_by_some_runtime_kind": sorted(reachable),
            "declared_without_an_emitter":
                sorted(set(EVENT_FAMILIES) - reachable),
            "observed_in_this_run": sorted(observed),
            "raw_kinds_mapped": len(_CANONICAL_EVENT_MAP)}
