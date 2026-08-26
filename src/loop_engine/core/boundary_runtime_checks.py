"""Runtime evidence for the operational-boundary ontology.

The canonical register stays declarative. This module runs focused offline
checks, captures the Loop initialization events they emit, and compares those
events with the register's claimed role profiles and relationships.
"""
from __future__ import annotations


RUNTIME_PROOF_CASES = (
    ("MCP tool discovery", "mcp",
     "intelligence.code.resolve@1.0.0", ("starting",)),
    ("MCP tool operation", "mcp",
     "intelligence.code.invoke@1.0.0", ("starting",)),
    ("skill instruction load", "skill",
     "intelligence.context.serve@1.0.0", ("starting",)),
    ("skill admission", "skill",
     "practitioner.verifier@1.0.0", ("starting",)),
    ("OpenTelemetry export", "otel",
     "practitioner.code_execution@1.0.0", ("starting",)),
    ("context compaction", "context",
     "intelligence.context.frame@1.0.0", ("starting",)),
    ("durable approval decision", "approval",
     "practitioner.verifier@1.0.0", ("starting", "spawned_by")),
    ("durable approval consumption", "approval",
     "practitioner.verifier@1.0.0", ("starting", "spawned_by")),
    ("workspace file write", "workspace",
     "practitioner.code_execution@1.0.0", ("starting", "spawned_by")),
    ("workspace command", "workspace",
     "practitioner.code_execution@1.0.0", ("starting", "spawned_by")),
    ("spawned checkpoint restore", "delegation", "", ("spawned_by",)),
    ("spawned task join", "delegation", "", ("spawned_by",)),
    ("spawned task state persistence", "state", "", ("spawned_by",)),
    ("spawned saved-state load", "state", "", ("spawned_by",)),
    ("spawned new-attempt restart", "state", "", ("spawned_by",)),
)


def _otel_check():
    from .otel_export import (
        InMemorySpanExporter,
        RawLedgerEvents,
        export_run_history_as_loop,
    )
    source = RawLedgerEvents((
        {"ts": 1.0, "event": "init", "loop_id": "source",
         "relationship_kind": "starting"},
        {"ts": 2.0, "event": "terminal", "loop_id": "source",
         "reason": "done"},
    ))
    result = export_run_history_as_loop(
        source, run_id="boundary-proof",
        exporter=InMemorySpanExporter())
    return {"all_passed": bool(result.loop_id)}


def run_runtime_ontology_proof(ontology) -> tuple[bool, str]:
    """Compare registry claims with actual Loop initialization events."""
    from ..loop import (approval_state_store, delegation_runtime,
                        spawned_task_state_store)
    from ..loop.recursive_loop import LoopLedger
    from . import (
        context_artifacts,
        mcp_adapter,
        skill_registry,
        workspace_operations,
    )

    runners = {
        "mcp": mcp_adapter.self_test,
        "skill": skill_registry.self_test,
        "otel": _otel_check,
        "context": context_artifacts.self_test,
        "approval": approval_state_store.self_test,
        "workspace": workspace_operations.self_test,
        "delegation": delegation_runtime.self_test,
        "state": spawned_task_state_store.self_test,
    }
    original = LoopLedger.record
    captured = {}
    errors = []
    for key, runner in runners.items():
        events = []

        def record(log, _events=events, **fields):
            before = len(log.events)
            value = original(log, **fields)
            _events.extend(log.events[before:])
            return value

        LoopLedger.record = record
        try:
            result = runner()
        finally:
            LoopLedger.record = original
        if not result.get("all_passed", False):
            errors.append(f"{key}: owning offline checks failed")
        captured[key] = [
            event for event in events if event.get("event") == "init"]

    for name, key, profile, required in RUNTIME_PROOF_CASES:
        binding = ontology[name]
        rows = captured[key]
        if profile:
            rows = [
                row for row in rows
                if f"{row.get('profile_id')}@{row.get('profile_version')}"
                == profile
            ]
            profile_ok = binding.profile_ref == profile
        else:
            rows = [
                row for row in rows
                if row.get("relationship_kind") in required
            ]
            profile_ok = all(
                row.get("role") in binding.role_families for row in rows)
        observed = {row.get("relationship_kind") for row in rows}
        if (not rows or not profile_ok
                or not set(required) <= observed
                or not observed <= set(binding.relationship_kinds)):
            errors.append(
                f"{name}: profile={profile or 'dynamic'} "
                f"relationships={sorted(observed)}")

    detail = "; ".join(errors)
    if not detail:
        detail = f"{len(RUNTIME_PROOF_CASES)} runtime claims matched"
    return not errors, detail
