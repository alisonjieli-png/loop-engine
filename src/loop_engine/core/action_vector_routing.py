"""Pure continuation guard for one assessed action outcome vector.

Owns the deterministic rule that a normal terminal route cannot hide a failed
observable process, safe remaining work, or unknown continuation. It consumes
passive vector records and returns a passive route decision. It does not run a
Practitioner, call a model or harness, grant authority, inspect private
reasoning, or decide task acceptance. When the owning Loop has already accepted
and deterministically verified a result, the policy's after-acceptance level
decides whether work the verifier still lists keeps the run going.
"""
from __future__ import annotations

from dataclasses import dataclass

from .outcome_vector import (
    AFTER_ACCEPTANCE_POLICIES,
    DEFAULT_OUTCOME_VECTOR_POLICY,
    OutcomeVectorPolicy,
)


TERMINAL_ROUTES = ("stop_success", "stop_unprofitable")
VECTOR_GUARD_ROUTES = ("continue", "repair", "reframe")
ACTION_ASSESSMENT_RECORD = "action_vector_assessment/v1"
UNAVAILABLE_ASSESSMENT_RECORD = "action_vector_assessment_unavailable/v1"
ROUTING_SIGNAL_NAMES = (
    "observable_process_aligned", "expected_output_satisfied",
    "requested_output_satisfied", "material_progress",
    "continuation_available")
OUTPUT_SIGNAL_NAMES = ("expected_output_satisfied", "requested_output_satisfied")


@dataclass(frozen=True)
class ActionVectorRouteRequest:
    """Proposed route and exact vector evidence at one pass boundary."""

    proposed_route: str
    vector_record: dict | None
    pass_number: int
    policy: OutcomeVectorPolicy = DEFAULT_OUTCOME_VECTOR_POLICY
    acceptance_established: bool = False

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
        if type(self.acceptance_established) is not bool:
            raise TypeError("action vector route acceptance must be a boolean")


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
    failed_output = any(signals[name] is False for name in OUTPUT_SIGNAL_NAMES)
    if process is False and request.policy.require_observable_process_alignment:
        return ActionVectorRouteDecision(
            "reframe",
            "The observable process did not align with its declared checks. "
            "Reframe before treating this response as an exit condition.",
            True, continuation, process, evidence_state)
    if (request.proposed_route == TERMINAL_ROUTES[0]
            and request.acceptance_established and not failed_output
            and request.policy.after_acceptance == AFTER_ACCEPTANCE_POLICIES[0]):
        return ActionVectorRouteDecision(
            request.proposed_route,
            "The owning Loop accepted and verified this result. Work the "
            "verifier still lists is optional under the publish-and-stop "
            "after-acceptance policy.",
            False, continuation, process, evidence_state)
    if (continuation is True
            and request.policy.continue_while_safe_authorized_work_remains):
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
    """Exercise aligned, misaligned, continuing, unknown, accepted, and legacy routes."""
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

    def accepted(record, policy=DEFAULT_OUTCOME_VECTOR_POLICY):
        return guard_action_vector_route(ActionVectorRouteRequest(
            TERMINAL_ROUTES[0], record, 1, policy, acceptance_established=True))

    def refuses_non_boolean_acceptance():
        try:
            ActionVectorRouteRequest(
                TERMINAL_ROUTES[0], None, 1, acceptance_established="yes")
        except TypeError:
            return True
        return False

    continuing_policy = OutcomeVectorPolicy(
        after_acceptance=AFTER_ACCEPTANCE_POLICIES[1])
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
    }, {
        "test": "accepted_verified_result_publishes_and_stops_by_default",
        "passed": accepted(vector(continuation=True)).route == TERMINAL_ROUTES[0]
        and not accepted(vector(continuation=True)).guarded
        and accepted(vector(continuation=None)).route == TERMINAL_ROUTES[0]
        and accepted({"record_type": UNAVAILABLE_ASSESSMENT_RECORD}).route
        == TERMINAL_ROUTES[0],
    }, {
        "test": "continuing_after_acceptance_is_an_explicit_policy_level",
        "passed": accepted(vector(continuation=True), continuing_policy).route
        == "continue",
    }, {
        "test": "acceptance_does_not_hide_a_failed_output_or_misaligned_process",
        "passed": accepted(vector(requested=False, continuation=True)).route
        == "repair"
        and accepted(vector(process=False)).route == "reframe",
    }, {
        "test": "unestablished_acceptance_keeps_the_continuation_guard",
        "passed": route(vector(continuation=True), TERMINAL_ROUTES[0]).route
        == "continue",
    }, {
        "test": "acceptance_flag_must_be_boolean",
        "passed": refuses_non_boolean_acceptance(),
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
