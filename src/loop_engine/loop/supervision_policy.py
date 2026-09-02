"""Supervision policy: the typed, versioned limits a Loop supervises itself by.

Architectural role: one passive record that replaces the module constants the
runtime used for its non-progress guards. The canonical ``Loop`` reads it to
decide when identical failed iterations stop an ``accepted_success`` Loop and
how deep unbounded spawning may go before a typed refusal. The Practitioner
kernel reads it to decide how many non-progressing passes precede each rung of
the escalation ladder (soft reset, cold restart, honest stop). The record is
data: it executes nothing, restarts nothing, and grants no budget. It is
recorded on the owner Loop's init event so a reader of Run History can see
which supervision limits governed the run.

The OTP mapping the owner asked for, stated once: the ladder is a one-for-one
restart strategy (only the stuck Practitioner is reframed or restarted, never
its siblings), ``non_progress_passes_before_escalation`` is the restart
intensity window, ``escalation_ladder`` is the ordered restart strategy, and
``identical_failures_before_stop`` is the let-it-crash boundary for a Loop
that keeps failing identically.

Owns:
    - SupervisionPolicy: the typed limits with one canonical default.
    - DEFAULT_SUPERVISION_POLICY: the values the runtime used before the
      policy existed, so behavior is unchanged unless a caller declares
      otherwise.

Does not own: the guards themselves (loop.recursive_loop, loop.kernel), the
budgets (LoopConfig.max_iterations, max_model_calls, max_depth), or the
reactive scheduler's leases.
"""
from __future__ import annotations

from dataclasses import dataclass


class SupervisionPolicyError(ValueError):
    """A supervision policy declared an invalid limit."""


#: The ordered rungs the Practitioner kernel climbs when consecutive passes
#: make no measurable progress. The last rung must be the honest stop.
ESCALATION_RUNGS = ("soft_reset", "cold_restart", "stop_unprofitable")


@dataclass(frozen=True)
class SupervisionPolicy:
    """Typed non-progress and depth limits for one Loop and its kernel passes."""

    policy_id: str = "loop.supervision"
    version: str = "1.0.0"
    identical_failures_before_stop: int = 3
    non_progress_passes_before_escalation: int = 3
    escalation_ladder: tuple[str, ...] = ESCALATION_RUNGS
    spawn_depth_guard: int = 128

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.version.strip():
            raise SupervisionPolicyError("policy identity must be non-empty")
        for name in ("identical_failures_before_stop",
                     "non_progress_passes_before_escalation",
                     "spawn_depth_guard"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, int)
                    or value < 1):
                raise SupervisionPolicyError(
                    f"{name} must be a positive integer")
        ladder = tuple(self.escalation_ladder)
        if not ladder or ladder[-1] != "stop_unprofitable":
            raise SupervisionPolicyError(
                "escalation_ladder must end with stop_unprofitable")
        if len(set(ladder)) != len(ladder) or any(
                rung not in ESCALATION_RUNGS for rung in ladder):
            raise SupervisionPolicyError(
                f"escalation_ladder must use distinct rungs from "
                f"{ESCALATION_RUNGS}")
        object.__setattr__(self, "escalation_ladder", ladder)

    def rung_for(self, escalation_count: int) -> str:
        """The rung for the n-th consecutive escalation (1-based).

        Escalations beyond the ladder length stop; a ladder is climbed once.
        """
        if escalation_count < 1:
            raise SupervisionPolicyError("escalation_count starts at 1")
        index = min(escalation_count, len(self.escalation_ladder)) - 1
        return self.escalation_ladder[index]

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "identical_failures_before_stop": self.identical_failures_before_stop,
            "non_progress_passes_before_escalation":
                self.non_progress_passes_before_escalation,
            "escalation_ladder": list(self.escalation_ladder),
            "spawn_depth_guard": self.spawn_depth_guard,
        }


#: The limits the runtime enforced as module constants before the policy
#: existed. Declaring a different policy is the only way to change them.
DEFAULT_SUPERVISION_POLICY = SupervisionPolicy()


def self_test() -> dict:
    """Prove validation, ladder order, and that the default matches history."""
    default = DEFAULT_SUPERVISION_POLICY
    custom = SupervisionPolicy(
        policy_id="loop.supervision.strict", version="1.0.0",
        identical_failures_before_stop=1,
        non_progress_passes_before_escalation=2,
        escalation_ladder=("cold_restart", "stop_unprofitable"),
        spawn_depth_guard=8)
    rejected = 0
    for bad in (
            lambda: SupervisionPolicy(identical_failures_before_stop=0),
            lambda: SupervisionPolicy(spawn_depth_guard=True),
            lambda: SupervisionPolicy(escalation_ladder=("soft_reset",)),
            lambda: SupervisionPolicy(
                escalation_ladder=("soft_reset", "soft_reset",
                                   "stop_unprofitable")),
            lambda: SupervisionPolicy(policy_id=" "),
    ):
        try:
            bad()
        except SupervisionPolicyError:
            rejected += 1
    tests = [{
        "test": "default_policy_matches_the_historical_runtime_constants",
        "passed": (default.identical_failures_before_stop == 3
                   and default.non_progress_passes_before_escalation == 3
                   and default.spawn_depth_guard == 128
                   and default.escalation_ladder == ESCALATION_RUNGS),
        "detail": str(default.to_dict()),
    }, {
        "test": "ladder_is_climbed_once_and_ends_in_an_honest_stop",
        "passed": ([default.rung_for(n) for n in (1, 2, 3, 4)]
                   == ["soft_reset", "cold_restart", "stop_unprofitable",
                       "stop_unprofitable"]
                   and [custom.rung_for(n) for n in (1, 2)]
                   == ["cold_restart", "stop_unprofitable"]),
        "detail": "rungs beyond the ladder stop",
    }, {
        "test": "invalid_limits_fail_closed",
        "passed": rejected == 5,
        "detail": f"{rejected}/5 rejected",
    }, {
        "test": "policy_is_passive_data",
        "passed": not any(name in dir(SupervisionPolicy) for name in (
            "run", "execute", "apply", "dispatch", "restart", "supervise")),
        "detail": "no executing methods",
    }]
    return {"module": "loop.supervision_policy",
            "passed": all(item["passed"] for item in tests),
            "tests": tests}
