"""STEP 9 — Choose what happens next (continue / branch / reset / close / finish).

CONTRACT   PractitionerState + PassRecord  ->  RouteDecision + new state
REQUIRED   yes (you always route — this is where reset/branch/close live)
WAYS       continue · repair · reset ladder (soft->cold) · branch · distill ·
           escalate · close checkpoint · finish
EXTEND     provide a `route` impl to emit richer routes; call closure.audit_run
           before finishing (a run may NOT succeed while work is orphaned).

Routing is BETWEEN passes: each pass is acyclic; node 9 commits a new versioned
state and launches the next pass.  Reset escalates repair -> soft_reset ->
cold_restart; a cold restart keeps only the spec + the failure log.
plan_skip_next_pass sets which OPTIONAL nodes the next pass skips.
"""
from ...loop.kernel import (RouteDecision, ROUTES, RESET_MODES, default_route,
                     plan_skip_next_pass)
from ...code_nodes.closure import audit_run, ClosureVerdict
from ...loop.practitioner_loop import detect_logjam, logjam_reset

__all__ = ["RouteDecision", "ROUTES", "RESET_MODES", "default_route",
           "plan_skip_next_pass", "audit_run", "ClosureVerdict",
           "detect_logjam", "logjam_reset"]
