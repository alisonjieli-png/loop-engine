"""What a provider failure code means for whoever decides what to do next.

The model gateway classifies provider errors into a closed vocabulary of
codes. A campaign worker, a recovery policy, or a route preference cannot
act on a code alone without knowing what kind of failure it names: an
outage a later retry of the same request may pass, an allowance the
provider will reset on its own schedule, a configuration fault no retry
can change, a fault of the request itself (this cell, not the provider),
a violated contract between the engine and the provider that needs review,
or a code that identifies none of these. Folding every one of them into a
single "provider unavailable" terminal is how a worker re-runs the same
cell without bound against a wrong credential the moment a provider
answers; naming the class beside the code is how it stops. Nothing here
retries, waits, or calls a provider: it is a passive vocabulary.
"""
from __future__ import annotations

from types import MappingProxyType

OUTAGE = "outage"
ALLOWANCE = "allowance"
CONFIGURATION = "configuration"
REQUEST = "request"
CONTRACT = "contract"
UNCLASSIFIED = "unclassified"
FAILURE_CLASSES = (OUTAGE, ALLOWANCE, CONFIGURATION, REQUEST, CONTRACT, UNCLASSIFIED)

WAIT_FOR_RECOVERY = "wait_for_recovery"
WAIT_FOR_ALLOWANCE = "wait_for_allowance"
STOP_ROUTE = "stop_route"
FAIL_CELL = "fail_cell"
DECISIONS = (WAIT_FOR_RECOVERY, WAIT_FOR_ALLOWANCE, STOP_ROUTE, FAIL_CELL)

#: Every code the gateway, the solve terminal, and the Practitioner can
#: report for a provider attempt, with the class each one names. A code
#: absent here is unclassified, never silently an outage.
PROVIDER_FAILURE_CLASSES = MappingProxyType({
    # The provider or the path to it is down; the same request may pass later.
    "network_unreachable": OUTAGE, "provider_unavailable": OUTAGE,
    "gateway_timeout": OUTAGE, "timeout": OUTAGE, "MODEL_PROVIDER_UNAVAILABLE": OUTAGE,
    # The provider refuses by allowance; nothing in the request or the
    # configuration is wrong, and retrying before the allowance changes
    # only spends attempts.
    "rate_limited": ALLOWANCE, "payment_required": ALLOWANCE,
    # The route is misconfigured; no retry of the same configuration can pass.
    "missing_credential": CONFIGURATION, "authentication_failed": CONFIGURATION,
    "model_not_found": CONFIGURATION, "invalid_request": CONFIGURATION,
    "provider_not_configured": CONFIGURATION, "no_eligible_route": CONFIGURATION,
    "unknown_model_output_limit": CONFIGURATION,
    # This request cannot succeed as posed; the cell fails, the campaign goes on.
    "context_window_exceeded": REQUEST, "output_limit_reached": REQUEST,
    "output_validation_failed": REQUEST, "unsupported_tool_call": REQUEST,
    "empty_response": REQUEST, "semantic_response_rejected": REQUEST,
    "response_evaluation_inconclusive": REQUEST,
    # The engine's contract with the provider was violated; review, no retry.
    "provider_attempt_contract_violated": CONTRACT, "model_output_limit_mismatch": CONTRACT,
    "model_identity_mismatch": CONTRACT, "token_accounting_unavailable": CONTRACT,
    # The code says a failure happened and nothing about its kind.
    "provider_failed": UNCLASSIFIED, "model_gateway_failed": UNCLASSIFIED,
    "incomplete_response": UNCLASSIFIED, "SolutionModelError": UNCLASSIFIED,
})


def failure_class(error_code) -> str:
    """The class one code names; an unknown or untyped code is unclassified."""
    if type(error_code) is not str:
        return UNCLASSIFIED
    return PROVIDER_FAILURE_CLASSES.get(error_code, UNCLASSIFIED)


def decide(error_codes, *, attempts_so_far: int = 0, attempt_ceiling: int | None = None) -> dict:
    """The one decision a worker takes after a failed attempt, from every
    code the attempt reported. Precedence: a contract or configuration
    fault stops the route whatever else happened; an allowance refusal
    waits for the allowance; an outage waits for recovery; a request fault
    or an unclassified code fails the cell. When the caller states an
    attempt ceiling, a wait that has already been retried that many times
    fails the cell instead, so no wait is unbounded."""
    codes = tuple(error_codes)
    if any(type(code) is not str for code in codes):
        raise TypeError("error codes must be text")
    if type(attempts_so_far) is not int or isinstance(attempts_so_far, bool) or attempts_so_far < 0:
        raise ValueError("attempts_so_far must be a non-negative integer")
    if attempt_ceiling is not None and (
            type(attempt_ceiling) is not int or isinstance(attempt_ceiling, bool) or attempt_ceiling < 1):
        raise ValueError("attempt_ceiling must be a positive integer when stated")
    classes = tuple(failure_class(code) for code in codes)
    counts = {name: classes.count(name) for name in FAILURE_CLASSES}
    if not codes:
        decision, reason = FAIL_CELL, "no failure code was reported"
    elif CONTRACT in classes or CONFIGURATION in classes:
        decision, reason = STOP_ROUTE, "a configuration or contract fault cannot pass on retry"
    elif ALLOWANCE in classes:
        decision, reason = WAIT_FOR_ALLOWANCE, "the provider refused by allowance"
    elif set(classes) <= {OUTAGE}:
        decision, reason = WAIT_FOR_RECOVERY, "every reported code is an outage"
    else:
        decision, reason = FAIL_CELL, "the request itself failed or the code is unclassified"
    if decision in (WAIT_FOR_RECOVERY, WAIT_FOR_ALLOWANCE) and attempt_ceiling is not None \
            and attempts_so_far >= attempt_ceiling:
        decision, reason = FAIL_CELL, f"waited {attempts_so_far} times, the stated ceiling"
    return {"record_type": "provider_failure_decision/v1", "decision": decision,
            "reason": reason, "codes": list(codes), "classes": list(classes),
            "counts": counts, "attempts_so_far": attempts_so_far,
            "attempt_ceiling": attempt_ceiling}


def self_test() -> dict:
    from .model_gateway import _FAILOVER_FORBIDDEN_ERRORS, _error_code
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    messages = ("No route to host", "connection refused", "503 service unavailable",
                "gateway_timeout", "read timed out", "429 rate limit exceeded",
                "402 insufficient credit", "API key not found in environment",
                "401 unauthorized", "404 model not found", "400 bad request",
                "context_window_exceeded", "output_limit_reached", "validation failed",
                "provider_attempt_contract_violated", "model_output_limit_mismatch",
                "model identity mismatch", "token_accounting_unavailable",
                "unsupported_tool_call", "empty_response", "incomplete_response",
                "unknown_model_output_limit", "something else entirely")
    emitted = {_error_code(message) for message in messages}
    check("every_code_the_gateway_emits_for_these_messages_has_a_class",
          all(code in PROVIDER_FAILURE_CLASSES for code in emitted), sorted(emitted))
    check("failover_forbidden_codes_stop_the_route_here_too",
          all(failure_class(code) in (CONFIGURATION, CONTRACT) for code in _FAILOVER_FORBIDDEN_ERRORS))
    check("a_wrong_credential_is_never_an_outage",
          decide(["authentication_failed"])["decision"] == STOP_ROUTE
          and decide(["network_unreachable", "authentication_failed"])["decision"] == STOP_ROUTE
          and decide(["missing_credential"])["decision"] == STOP_ROUTE
          and decide(["model_not_found"])["decision"] == STOP_ROUTE)
    check("an_outage_waits_for_recovery_and_an_allowance_waits_for_its_reset",
          decide(["network_unreachable", "provider_unavailable"])["decision"] == WAIT_FOR_RECOVERY
          and decide(["rate_limited"])["decision"] == WAIT_FOR_ALLOWANCE
          and decide(["network_unreachable", "rate_limited"])["decision"] == WAIT_FOR_ALLOWANCE)
    check("a_request_fault_or_an_unknown_code_fails_the_cell_not_the_campaign",
          decide(["context_window_exceeded"])["decision"] == FAIL_CELL
          and decide(["provider_failed"])["decision"] == FAIL_CELL
          and decide(["network_unreachable", "context_window_exceeded"])["decision"] == FAIL_CELL
          and decide([])["decision"] == FAIL_CELL
          and failure_class("never_seen_before") == UNCLASSIFIED and failure_class(None) == UNCLASSIFIED)
    check("a_stated_ceiling_bounds_every_wait",
          decide(["network_unreachable"], attempts_so_far=3, attempt_ceiling=3)["decision"] == FAIL_CELL
          and decide(["network_unreachable"], attempts_so_far=2, attempt_ceiling=3)["decision"] == WAIT_FOR_RECOVERY
          and decide(["rate_limited"], attempts_so_far=5, attempt_ceiling=5)["decision"] == FAIL_CELL
          and decide(["authentication_failed"], attempts_so_far=0, attempt_ceiling=1)["decision"] == STOP_ROUTE)
    record = decide(["network_unreachable", "timeout"], attempts_so_far=1, attempt_ceiling=4)
    check("the_decision_record_names_codes_classes_counts_and_the_ceiling",
          record["classes"] == [OUTAGE, OUTAGE] and record["counts"][OUTAGE] == 2
          and record["attempt_ceiling"] == 4 and record["record_type"] == "provider_failure_decision/v1")
    for name, operation in (("untyped_codes", lambda: decide([None])),
                            ("negative_attempts", lambda: decide(["timeout"], attempts_so_far=-1)),
                            ("zero_ceiling", lambda: decide(["timeout"], attempt_ceiling=0))):
        try:
            operation()
            check(f"{name}_are_refused", False, "accepted")
        except (TypeError, ValueError):
            check(f"{name}_are_refused", True)
    check("the_vocabulary_is_read_only_and_closed",
          isinstance(PROVIDER_FAILURE_CLASSES, MappingProxyType)
          and set(PROVIDER_FAILURE_CLASSES.values()) <= set(FAILURE_CLASSES))
    return {"module": "core.provider_failure_classes", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
