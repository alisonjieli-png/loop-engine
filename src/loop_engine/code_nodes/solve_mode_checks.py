"""Checks on how a solve chose the mode it ran in.

Owns: the check that a run which was asked to reason, and could not, says so
in its own record rather than looking like a run nobody asked.

Belongs to: the solve runtime's self-test surface.  Never: runtime behaviour.
A demoted run and a deterministic one produce the same artifacts and the same
terminal code, so nothing else distinguishes them afterwards.
"""
from __future__ import annotations

from .solve_runtime import SolveOutcome


def mode_demotion_is_visible() -> list:
    """A run asked to reason that could not must say so in its own record."""
    silent = SolveOutcome(
        run_id="r", status="COMPLETED_VERIFIED", solved=True, failure_code="",
        result={}, compiled_task={}, intelligence={},
        selected_mode="deterministic", requested_mode="deterministic",
        selected_canvas={}, graph_digest="", verification={}).to_dict()
    demoted = SolveOutcome(
        run_id="r", status="COMPLETED_VERIFIED", solved=True, failure_code="",
        result={}, compiled_task={}, intelligence={},
        selected_mode="deterministic", requested_mode="non_deterministic",
        mode_demoted_because="no model execution was configured",
        selected_canvas={}, graph_digest="", verification={}).to_dict()
    return [{
        "test": "a demoted run is distinguishable from a deterministic one",
        "passed": (silent.get("requested_mode") == "deterministic"
                   and "mode_demoted_because" not in silent
                   and demoted.get("requested_mode") == "non_deterministic"
                   and demoted.get("selected_mode") == "deterministic"
                   and bool(demoted.get("mode_demoted_because"))),
        "detail": "both records name the mode asked for, and only the "
                  "demoted one says why it did not get it",
    }]


def mode_checks() -> list:
    """Every mode check, as one list of test records."""
    return mode_demotion_is_visible()


def self_test() -> dict:
    """Prove the mode checks report rather than assert."""
    tests = mode_checks()
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "solve_mode_check_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
