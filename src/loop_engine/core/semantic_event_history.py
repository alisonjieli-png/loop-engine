"""Allowlisted model view of prior Loop event structure.

Run History keeps complete control, experiment, packet, diagnostic, and effect
records. A model does not need those raw bodies merely because they precede a
call. This projection exposes a small structural sequence and prevents control
instrumentation, prior assistance, or nested sensitive values from entering a
fresh packet through event history.
"""

from __future__ import annotations

_ALLOWED_EVENT_KINDS = (
    "init",
    "loop.started",
    "iteration_started",
    "run_step",
    "terminal",
    "cancel",
    "fallback",
    "budget_stop",
)
_ALLOWED_FIELDS = (
    "event",
    "loop_id",
    "spawning_loop_id",
    "relationship_kind",
    "role",
    "profile_id",
    "mode",
    "step",
    "iteration",
    "terminal_code",
    "status",
    "failure_code",
    "depth",
    "loop_condition",
    "exit_condition",
)
_SCALAR_TYPES = (str, int, float, bool, type(None))


def semantic_event_history(events) -> tuple[dict, ...]:
    """Return structural event facts only, stopping at the first work packet."""
    projected = []
    for event in tuple(events or ()):
        if not isinstance(event, dict):
            continue
        if event.get("custom_kind") == "llm_work_packet_assembled":
            break
        if event.get("event") not in _ALLOWED_EVENT_KINDS:
            continue
        row = {
            key: event[key] for key in _ALLOWED_FIELDS
            if key in event and isinstance(event[key], _SCALAR_TYPES)
        }
        if row.get("event"):
            projected.append(row)
    return tuple(projected)


def self_test() -> dict[str, object]:
    """Prove instrumentation and nested sensitive bodies never enter."""
    events = ({
        "event": "init", "loop_id": "loop1", "role": "practitioner",
        "goal": "private task body", "ts": 1.0,
    }, {
        "event": "custom", "custom_kind": "public_solve_control_manifest",
        "loop_id": "loop1", "control_manifest": {
            "prior_stage_summary": "must not enter",
            "secret": "must not enter"},
    }, {
        "event": "iteration_started", "loop_id": "loop1", "iteration": 1,
        "step": "orient", "content": {"prior": "must not enter"},
    }, {
        "event": "custom", "custom_kind": "llm_work_packet_assembled",
        "loop_id": "loop1",
    }, {
        "event": "terminal", "loop_id": "loop1",
    })
    projected = semantic_event_history(events)
    body = repr(projected)
    tests = [{
        "test": "structural_events_and_fields_are_preserved",
        "passed": projected == (
            {"event": "init", "loop_id": "loop1", "role": "practitioner"},
            {"event": "iteration_started", "loop_id": "loop1",
             "step": "orient", "iteration": 1}),
    }, {
        "test": "control_prior_and_sensitive_bodies_are_excluded",
        "passed": all(value not in body for value in (
            "prior_stage_summary", "must not enter", "secret", "content")),
    }, {
        "test": "history_stops_at_the_first_model_work_packet",
        "passed": all(item.get("event") != "terminal" for item in projected),
    }]
    passed = sum(bool(item["passed"]) for item in tests)
    return {
        "record_type": "semantic_event_history_checks/v1",
        "provider_calls": 0, "tests": tests,
        "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = ("semantic_event_history", "self_test")
