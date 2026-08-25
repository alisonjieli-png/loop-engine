"""Arbiter — a proposal is not a decision (v3 §12–13).

Resolvers and deliberation strategies produce *proposals*.  Turning proposals
into a decision is a separate, authority-bearing step, and it is deliberately
two-phase:

1. **Hard gates exclude first.**  Authority, compilability, budget, a sealed
   evaluator boundary, capability availability — these are not negative utility
   terms to be traded off.  A proposal that fails one is removed before any
   scoring, with the reason recorded.  A brilliant-but-unauthorized move never
   competes on utility.

2. **Then multi-objective utility, kept multi-objective.**  Among the survivors,
   value is a vector — expected goal progress, information value, option value,
   reuse, diversity, reversibility, minus cost, latency, risk, fragility.  A
   weighted scalar is only one projection; the Pareto frontier is preserved so a
   cheap high-information probe is not hidden behind a costly high-score move.

The result is a ``NextMoveDecision`` that selects zero, one, or several
complementary moves and **retains the rejected ones with their reasons** —
rejected is not deleted; it is decision evidence.  The arbiter never claims a
move worked: it orders and authorizes what to try; the fold oracle decides
outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Mapping, Sequence

from .decision_slates import Proposal

# The hard gates that EXCLUDE a candidate before scoring.  All must pass.
HARD_GATES = ("authority_ok", "compiles", "within_budget", "sealed_safe",
              "capabilities_available")

# The multi-objective utility terms: benefits minus costs.
BENEFIT_TERMS = ("goal_progress", "information_value", "option_value",
                 "reuse_value", "diversity_value", "reversibility_value")
COST_TERMS = ("compute_cost", "latency_cost", "operational_risk",
              "epistemic_risk", "irreversibility_penalty")

DEFAULT_WEIGHTS = {
    "goal_progress": 1.0, "information_value": 1.0, "option_value": 0.6,
    "reuse_value": 0.5, "diversity_value": 0.4, "reversibility_value": 0.3,
    "compute_cost": 1.0, "latency_cost": 0.5, "operational_risk": 0.8,
    "epistemic_risk": 0.6, "irreversibility_penalty": 1.0}

# Policy weight overlays — a projection, not the whole truth.
POLICY_WEIGHTS = {
    "value_weighted": {},
    "information_first": {"information_value": 3.0, "option_value": 1.2},
    "cost_first": {"compute_cost": 3.0, "latency_cost": 1.5},
    "risk_averse": {"operational_risk": 3.0, "irreversibility_penalty": 3.0},
}


@dataclass(frozen=True)
class Candidate:
    """A proposed move plus its hard-gate verdicts and its objective estimates."""
    move: Proposal
    gates: dict = field(default_factory=dict)      # gate -> bool
    estimates: dict = field(default_factory=dict)  # objective term -> float

    def gate_failures(self) -> list[str]:
        return [g for g in HARD_GATES if not self.gates.get(g, True)]

    def utility(self, weights: Mapping[str, float]) -> float:
        score = 0.0
        for term in BENEFIT_TERMS:
            score += weights.get(term, 0.0) * float(self.estimates.get(term, 0.0))
        for term in COST_TERMS:
            score -= weights.get(term, 0.0) * float(self.estimates.get(term, 0.0))
        return score

    def objective_vector(self) -> dict:
        """Benefits positive, costs negated — for Pareto dominance."""
        vec = {t: float(self.estimates.get(t, 0.0)) for t in BENEFIT_TERMS}
        vec.update({t: -float(self.estimates.get(t, 0.0)) for t in COST_TERMS})
        return vec


def _dominates(a: Candidate, b: Candidate) -> bool:
    """a Pareto-dominates b if a is >= on every objective and > on at least one."""
    va, vb = a.objective_vector(), b.objective_vector()
    ge_all = all(va[k] >= vb[k] for k in va)
    gt_any = any(va[k] > vb[k] for k in va)
    return ge_all and gt_any


def pareto_front(candidates: Sequence[Candidate]) -> list[Candidate]:
    """The non-dominated candidates."""
    front: list[Candidate] = []
    for c in candidates:
        if not any(_dominates(o, c) for o in candidates if o is not c):
            front.append(c)
    return front


@dataclass
class NextMoveDecision:
    selected: list[Candidate] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)      # {move_key, reason}
    gate_excluded: list[dict] = field(default_factory=list)  # {move_key, gates}
    policy: str = "value_weighted"
    note: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "next_move_decision/v1", "policy": self.policy,
                "selected": [{"move": c.move.action_key,
                              "kind": c.move.action_kind,
                              "utility": round(c.utility(DEFAULT_WEIGHTS), 4)}
                             for c in self.selected],
                "rejected": self.rejected, "gate_excluded": self.gate_excluded,
                "note": self.note,
                "the_rule": ("hard gates EXCLUDE before utility; value is "
                             "multi-objective and rejected proposals are "
                             "retained as decision evidence; the arbiter "
                             "authorizes what to try, the oracle decides what "
                             "worked")}


def arbitrate(candidates: Sequence[Candidate], *,
              policy: str = "value_weighted", select: int = 1,
              keep_pareto: bool = True) -> NextMoveDecision:
    """Gate, score, and select.  ``select`` is how many top moves to authorize;
    with ``keep_pareto`` the selection is drawn from the Pareto frontier so a
    complementary cheap/high-information move can be chosen alongside the top."""
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(POLICY_WEIGHTS.get(policy, {}))

    decision = NextMoveDecision(policy=policy)
    survivors: list[Candidate] = []
    for c in candidates:
        failures = c.gate_failures()
        if failures:
            decision.gate_excluded.append(
                {"move": c.move.action_key, "failed_gates": failures})
        else:
            survivors.append(c)

    if not survivors:
        decision.note = "no candidate passed the hard gates"
        return decision

    ranked = sorted(survivors, key=lambda c: (-c.utility(weights),
                                              c.move.action_key))
    pool = pareto_front(survivors) if keep_pareto else survivors
    # Selection: highest utility first, but only from the Pareto pool so a
    # dominated move is never selected over the frontier.
    pool_ranked = sorted(pool, key=lambda c: (-c.utility(weights),
                                              c.move.action_key))
    chosen = pool_ranked[:max(1, select)]
    decision.selected = chosen
    chosen_keys = {c.move.action_key for c in chosen}
    for c in ranked:
        if c.move.action_key not in chosen_keys:
            reason = ("dominated / lower utility under policy "
                      f"{policy}" if c in pool
                      else "Pareto-dominated by a selected move")
            decision.rejected.append({"move": c.move.action_key,
                                      "reason": reason})
    decision.note = (f"{len(survivors)} of {len(candidates)} passed gates; "
                     f"selected {len(chosen)} from the Pareto frontier")
    return decision


# ---------------------------------------------------------------------------
# Self-test — deterministic.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    def cand(key, kind="add_node", gates=None, **est):
        return Candidate(move=Proposal(action_kind=kind, action_key=key),
                         gates=gates or {g: True for g in HARD_GATES},
                         estimates=est)

    # 1. A hard-gate failure EXCLUDES a candidate before any scoring — even a
    #    high-utility one.
    unauthorized = cand("deploy_now", goal_progress=0.9,
                        gates={g: True for g in HARD_GATES} | {"authority_ok": False})
    modest = cand("run_probe", kind="run_tests", information_value=0.6,
                  compute_cost=0.1)
    d1 = arbitrate([unauthorized, modest])
    check("a_hard_gate_failure_excludes_before_utility",
          d1.selected[0].move.action_key == "run_probe"
          and any(g["move"] == "deploy_now"
                  and "authority_ok" in g["failed_gates"]
                  for g in d1.gate_excluded),
          "the unauthorized high-goal move is excluded by the authority gate "
          "before scoring; the modest probe is selected — a hard gate is not a "
          "utility penalty")

    # 2. A cheap high-information probe survives on the Pareto frontier next to a
    #    costly high-goal move, under the information-first policy.
    probe = cand("leakage_probe", kind="run_tests", information_value=0.9,
                 compute_cost=0.1)
    big = cand("train_deep_net", goal_progress=0.7, compute_cost=8.0)
    d2 = arbitrate([probe, big], policy="information_first")
    check("information_first_policy_prefers_the_high_information_probe",
          d2.selected[0].move.action_key == "leakage_probe",
          "under the information-first policy the cheap high-information probe "
          "outranks the costly high-goal train — the objective is a vector, and "
          "the weight projection changes the choice")

    # 3. Rejected proposals are retained with reasons (decision evidence).
    d3 = arbitrate([probe, big], policy="value_weighted", select=1)
    check("rejected_proposals_are_retained_with_reasons",
          len(d3.rejected) == 1 and d3.rejected[0].get("reason"),
          "the unselected move stays on the decision with a reason — rejected "
          "is decision evidence, not deleted")

    # 4. Multiple complementary moves can be selected from the frontier.
    d4 = arbitrate([probe, big, modest], select=2, keep_pareto=True)
    check("multiple_complementary_moves_can_be_selected",
          len(d4.selected) == 2,
          "the arbiter can authorize two complementary moves at once, not only "
          "a single winner")

    # 5. Pareto dominance: a strictly-worse move is never selected.
    dominated = cand("worse", goal_progress=0.1, compute_cost=5.0)
    dominator = cand("better", goal_progress=0.9, compute_cost=0.1)
    front = pareto_front([dominated, dominator])
    check("pareto_front_excludes_a_strictly_dominated_move",
          dominator in front and dominated not in front,
          "a move worse on every objective is Pareto-dominated and drops off "
          "the frontier")

    # 6. Determinism + all-gated-out.
    d6a = arbitrate([probe, big], policy="information_first")
    all_gated = arbitrate([unauthorized])
    check("arbiter_is_deterministic_and_reports_all_gated_out",
          d6a.to_dict() == d2.to_dict() and not all_gated.selected
          and "no candidate passed" in all_gated.note,
          "the same candidates and policy always produce the identical "
          "decision; when everything fails a gate the decision selects nothing "
          "and says so")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "arbiter_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
