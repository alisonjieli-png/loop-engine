"""Which terminal code a finished solve earned, from what it recorded.

Owns: the classification from a run's own failure and diagnostic codes to one
`SolveTerminalCode`, including the rule that a generic exception name defers
to the deepest layer the run actually reached rather than naming a layer it
never got to.

Belongs to: the solve runtime.  Never: deciding whether a run succeeded — it
reads that decision, it does not make it.
"""
from __future__ import annotations

from enum import Enum

from ..core.terminal_layer import deepest_layer_reached


class SolveTerminalCode(str, Enum):
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    COMPLETED_PARTIAL = "COMPLETED_PARTIAL"
    BLOCKED_MATERIAL_INPUT = "BLOCKED_MATERIAL_INPUT"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REPAIR_UNAVAILABLE = "REPAIR_UNAVAILABLE"
    NO_PROGRESS = "NO_PROGRESS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXHAUSTED = "DEADLINE_EXHAUSTED"
    ABSTAINED = "ABSTAINED"
    CANCELLED = "CANCELLED"


SOLVE_FAILURE_CODES = tuple(
    item.value for item in SolveTerminalCode
    if item is not SolveTerminalCode.COMPLETED_VERIFIED)


def failure_code_for(result: dict) -> str:
    code = str(result.get("failure_code") or "")
    if code in ("NO_VERIFIED_CAPABILITY", "EXECUTOR_UNAVAILABLE"):
        return SolveTerminalCode.CAPABILITY_GAP.value
    if code == "CANCELLED":
        return SolveTerminalCode.CANCELLED.value
    if code == "model_call_budget_exhausted":
        return SolveTerminalCode.BUDGET_EXHAUSTED.value
    if code in (
            "SolutionModelError", "MODEL_PROVIDER_UNAVAILABLE",
            "model_gateway_failed", "no_eligible_route",
            "provider_not_configured", "missing_credential",
            "authentication_failed", "payment_required", "model_not_found",
            "rate_limited", "provider_unavailable", "timeout",
            "provider_failed"):
        return SolveTerminalCode.PROVIDER_UNAVAILABLE.value
    if code in ("PermissionError", "PERMISSION_DENIED"):
        return SolveTerminalCode.AUTHORITY_REQUIRED.value
    if code == "OUTPUT_CONTRACT_VIOLATION":
        return SolveTerminalCode.VERIFICATION_FAILED.value
    # A Python exception class name says which module raised, not which layer
    # failed. AdaptivePractitionerError was mapped straight to
    # VERIFICATION_FAILED, so a live run that produced two invalid
    # orientations and never verified anything still reported a verification
    # failure. Generic class names defer to the evidence below.
    if code in ("NO_PROGRESS", "stop_unprofitable"):
        return SolveTerminalCode.NO_PROGRESS.value
    # Only claim verification failed if the run reached verification. A run
    # whose provider never answered has a transport failure, and saying so
    # is the difference between one fix and a week of looking in the wrong
    # subsystem.
    reached = deepest_layer_reached(result)
    if reached == "transport":
        return SolveTerminalCode.PROVIDER_UNAVAILABLE.value
    if reached == "semantic":
        return SolveTerminalCode.NO_PROGRESS.value
    return SolveTerminalCode.VERIFICATION_FAILED.value


def self_test() -> dict:
    """Prove the classification defers to the layer a run actually reached."""
    tests = [{
        "test": "a generic exception name does not name a layer never reached",
        "passed": failure_code_for({"failure_code": "RuntimeError"})
        != SolveTerminalCode.VERIFICATION_FAILED.value,
        "detail": failure_code_for({"failure_code": "RuntimeError"}),
    }, {
        "test": "a provider failure is named as one",
        "passed": failure_code_for({"failure_code": "rate_limited"})
        == SolveTerminalCode.PROVIDER_UNAVAILABLE.value,
        "detail": "",
    }, {
        "test": "the failure codes exclude the one success code",
        "passed": (SolveTerminalCode.COMPLETED_VERIFIED.value
                   not in SOLVE_FAILURE_CODES
                   and len(SOLVE_FAILURE_CODES) == len(
                       list(SolveTerminalCode)) - 1),
        "detail": "",
    }]
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "solve_terminal_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
