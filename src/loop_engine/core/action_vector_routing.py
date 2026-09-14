"""Pure continuation guard for one assessed action outcome vector.

Owns the deterministic rule that a normal terminal route cannot hide a failed
observable process, safe remaining work, or unknown continuation. It consumes
passive vector records and returns a passive route decision. It does not run a
Practitioner, call a model or harness, grant authority, inspect private
reasoning, or decide task acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass

from .outcome_vector import DEFAULT_OUTCOME_VECTOR_POLICY, OutcomeVectorPolicy


TERMINAL_ROUTES = ("stop_success", "stop_unprofitable")
VECTOR_GUARD_ROUTES = ("continue", "repair", "reframe")
ACTION_ASSESSMENT_RECORD = "action_vector_assessment/v1"
UNAVAILABLE_ASSESSMENT_RECORD = "action_vector_assessment_unavailable/v1"
ROUTING_SIGNAL_NAMES = (
    "observable_process_aligned", "expected_output_satisfied",
    "requested_output_satisfied", "material_progress",
    "continuation_available")


@dataclass(frozen=True)
class ActionVectorRouteRequest:
    """Proposed route and exact vector evidence at one pass boundary."""

    proposed_route: str
    vector_record: dict | None
    pass_number: int
    policy: OutcomeVectorPolicy = DEFAULT_OUTCOME_VECTOR_POLICY

    def __post_init__(self) -> None:
        if not isinstance(self.proposed_route, str) or not self.proposed_route:
            raise ValueError("action vector route needs a proposed route")
        if isinstance(self.pass_number, bool) or self.pass_number < 1:
            raise ValueError("action vector route pass number starts at one")
        if self.vector_record is not None and not isinstance(
                self.vector_record, dict):
            raise TypeError("action vector route evidence must be a mapping")
        if not isinstance(self.policy, OutcomeVectorPolicy):
            raise TypeError("action vector route policy must be typed")


@dataclass(frozen=True)
class ActionVectorRouteDecision:
    """Result of the pure route guard, without execution authority."""

    route: str
    reason: str
    guarded: bool
    continuation_available: bool | None
    observable_process_aligned: bool | None
    evidence_state: str

    def to_dict(self) -> dict:
        return {
            "record_type": "action_vector_route_decision/v1",
            "route": self.route,
            "reason": self.reason,
            "guarded": self.guarded,
            "continuation_available": self.continuation_available,
            "observable_process_aligned": self.observable_process_aligned,
            "evidence_state": self.evidence_state,
            "task_accepted": False,
            "authority_granted": False,
        }


def _signals(record: dict | None) -> tuple[dict | None, str]:
    if record is None:
        return None, "legacy_not_recorded"
    record_type = record.get("record_type")
    if record_type == UNAVAILABLE_ASSESSMENT_RECORD:
        return {name: None for name in ROUTING_SIGNAL_NAMES}, "unavailable"
    if record_type != ACTION_ASSESSMENT_RECORD:
        raise ValueError("action vector route received an unsupported assessment")
    values = record.get("outcome_signals")
    if (not isinstance(values, dict)
            or set(values) != set(ROUTING_SIGNAL_NAMES)
            or any(value is not None and type(value) is not bool
                   for value in values.values())):
        raise ValueError("action vector route signals are malformed")
    return values, "observed"


def guard_action_vector_route(
        request: ActionVectorRouteRequest) -> ActionVectorRouteDecision:
    """Return a changed route only when the vector prohibits normal stopping."""
    signals, evidence_state = _signals(request.vector_record)
    if request.proposed_route not in TERMINAL_ROUTES or signals is None:
        return ActionVectorRouteDecision(
            request.proposed_route, "No action-vector route change required.",
            False, None if signals is None else signals[
                "continuation_available"],
            None if signals is None else signals[
                "observable_process_aligned"], evidence_state)

    process = signals["observable_process_aligned"]
    continuation = signals["continuation_available"]
    if process is False and request.policy.require_observable_process_alignment:
        return ActionVectorRouteDecision(
            "reframe",
            "The observable process did not align with its declared checks. "
            "Reframe before treating this response as an exit condition.",
            True, continuation, process, evidence_state)
    if (continuation is True
            and request.policy.continue_while_safe_authorized_work_remains):
        failed_output = any(signals[name] is False for name in (
            "expected_output_satisfied", "requested_output_satisfied"))
        route = "repair" if failed_output else "continue"
        return ActionVectorRouteDecision(
            route,
            "The action vector records safe authorized work that remains. "
            "Publishing or admitting the current response is not an exit condition.",
            True, continuation, process, evidence_state)
    if continuation is None and request.policy.stop_requires_resolved_continuation:
        return ActionVectorRouteDecision(
            "reframe",
            "The action vector could not determine whether safe authorized "
            "work remains. Reframe or gather evidence before stopping.",
            True, continuation, process, evidence_state)
    return ActionVectorRouteDecision(
        request.proposed_route, "The vector reports no safe authorized "
        "continuation at this boundary.", False, continuation, process,
        evidence_state)


def self_test() -> dict:
    """Exercise aligned, misaligned, continuing, unknown, and legacy routes."""
    def vector(*, process=True, expected=True, requested=True,
               progress=True, continuation=False):
        return {
            "record_type": ACTION_ASSESSMENT_RECORD,
            "outcome_signals": {
                "observable_process_aligned": process,
                "expected_output_satisfied": expected,
                "requested_output_satisfied": requested,
                "material_progress": progress,
                "continuation_available": continuation,
            },
        }

    def route(record, proposed="stop_unprofitable"):
        return guard_action_vector_route(
            ActionVectorRouteRequest(proposed, record, 1))

    tests = [{
        "test": "aligned_exhausted_work_preserves_the_terminal_route",
        "passed": route(vector()).route == "stop_unprofitable"
        and not route(vector()).guarded,
    }, {
        "test": "safe_remaining_work_rejects_a_stop",
        "passed": route(vector(continuation=True)).route == "continue",
    }, {
        "test": "failed_output_with_remaining_work_routes_to_repair",
        "passed": route(vector(
            expected=False, requested=False, continuation=True)).route
        == "repair",
    }, {
        "test": "misaligned_process_reframes_even_when_it_claims_no_more_work",
        "passed": route(vector(process=False)).route == "reframe",
    }, {
        "test": "unknown_or_unavailable_continuation_reframes",
        "passed": route(vector(continuation=None)).route == "reframe"
        and route({"record_type": UNAVAILABLE_ASSESSMENT_RECORD}).route
        == "reframe",
    }, {
        "test": "legacy_absence_is_readable_without_invented_vector_evidence",
        "passed": route(None).route == "stop_unprofitable"
        and route(None).evidence_state == "legacy_not_recorded",
    }, {
        "test": "a_nonterminal_route_is_not_rewritten",
        "passed": route(vector(process=False), "retry").route == "retry",
    }]
    return {
        "record_type": "action_vector_routing_test/v1",
        "tests": tests, "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests),
    }


__all__ = (
    "ActionVectorRouteDecision", "ActionVectorRouteRequest",
    "guard_action_vector_route", "self_test")
