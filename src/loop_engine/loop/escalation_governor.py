"""Escalation governor — resolve each decision at the cheapest arm that suffices.

This is what lets loop_engine run a swarm at every open decision without paying for a
model at every step, and it is the structural difference from a model-driven
agent framework.  A model-driven loop (AWS Strands and similar) calls a model on
every turn: the model decides the next tool, then the next, then the next.
loop_engine instead treats each open decision as a *waterfall of arms ordered by
cost* and resolves it at the cheapest arm that answers confidently enough —
usually with no model call at all:

    level 0  cached exact rule / solved-route replay        (no model)
    level 1  deterministic memory: pheromone + analogy priors (no model)
    level 2  archived-list leaders / retrieval                (no model)
    level 3  a small hosted model, labelling only             (cheap)
    level 4  one strong model                                  (frontier)
    level 5  an independent panel                              (frontier × N)
    level 6  the adversarial council                           (frontier × N)
    level 7  research-on-the-fly                               (expensive)
    level 8  an experiment / a fold-oracle probe               (compute)
    level 9  human authority                                   (scarce)

The governor walks the arms cheapest-first and stops at the first arm that
resolves the decision with enough confidence — early exit is success, exactly as
the information-first waterfall requires.  It escalates to a costlier arm ONLY
when the cheaper arm abstained or was under-confident AND the expected value of
the information the next arm would add exceeds that arm's cost.  It stops when
the budget cannot afford the next arm.  Every resolution carries the receipt that
makes the cost claim checkable: which arms ran, which one resolved, how many
model calls were made, and — the number that beats a model-every-step loop — how
many model calls were AVOIDED.

Three disciplines keep this honest and keep it from becoming destiny:

- **The oracle still decides truth.**  A confident cheap answer resolves a
  *decision about what to try*; it never marks an arrangement accepted.  Levels
  8 (probe) and the fold oracle downstream are where performance is established.
- **A protected exploration floor.**  On a deterministic minority of decisions
  the governor escalates PAST a confident cheap answer to gather unbiased data,
  so the cheap arm's priors are continually re-checked against costlier arms and
  the expensive arms never fall out of use.  This is recorded as exploration.
- **Confidence is agreement/among-arms, not performance.**  The threshold is on
  how sure the arm is about the decision, never a claim the move will win.

Run: ``python -m loop_engine.loop.escalation_governor --self-test``.
Architectural role: Practitioner Loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

# Cost tiers, cheapest first.  The number is an ordinal, not a price; a price
# snapshot lives in the resolver's declared cost.
LEVEL_NAMES = {
    0: "cached_rule", 1: "deterministic_memory", 2: "retrieval_leaders",
    3: "small_model", 4: "strong_model", 5: "independent_panel",
    6: "adversarial_council", 7: "research", 8: "experiment_probe",
    9: "human_authority"}

# Which levels actually spend model tokens — used to count calls made/avoided.
MODEL_LEVELS = frozenset({3, 4, 5, 6, 7})


@dataclass(frozen=True)
class Resolution:
    """What one arm returned for one decision."""
    resolved: bool                 # did this arm produce a usable answer?
    answer: Any = None
    confidence: float = 0.0        # 0..1 the arm's confidence in the answer
    abstained: bool = False        # arm declined (thin memory, no match, …)
    detail: str = ""


@dataclass(frozen=True)
class Arm:
    """One rung of the waterfall.

    ``resolve`` is a pure function ``(decision, context) -> Resolution``.
    ``cost`` is the arm's declared cost in whatever unit the caller budgets in
    (tokens, dollars, seconds); ``model_calls`` is how many model calls running
    this arm costs (0 for the deterministic rungs).
    """
    name: str
    level: int
    cost: float
    resolve: Callable[[Mapping[str, Any], Mapping[str, Any]], Resolution]
    model_calls: int = 0


@dataclass
class GovernorResult:
    resolved: bool
    answer: Any
    resolving_arm: str
    resolving_level: int
    arms_run: list[str]
    model_calls_made: int
    model_calls_avoided: int
    cost_spent: float
    cost_avoided: float
    exploration: bool
    trace: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "record_type": "escalation_governor_result/v1",
            "resolved": self.resolved, "answer": self.answer,
            "resolving_arm": self.resolving_arm,
            "resolving_level": self.resolving_level,
            "resolving_level_name": LEVEL_NAMES.get(self.resolving_level, "?"),
            "arms_run": self.arms_run,
            "model_calls_made": self.model_calls_made,
            "model_calls_avoided": self.model_calls_avoided,
            "cost_spent": round(self.cost_spent, 4),
            "cost_avoided": round(self.cost_avoided, 4),
            "exploration_escalation": self.exploration,
            "trace": self.trace,
            "the_rule": ("resolved at the cheapest arm whose confidence cleared "
                         "the bar; escalation is paid for only when its expected "
                         "information beats its cost — the fold oracle still "
                         "decides truth downstream"),
        }


def _exploration_draw(decision_id: str, rate: float, salt: str) -> bool:
    """A deterministic, reproducible exploration decision (no RNG, because the
    engine forbids Math.random-style nondeterminism in replayable paths).  Maps
    a hash of the decision id to [0,1) and compares to the rate."""
    if rate <= 0.0:
        return False
    digest = hashlib.sha256(f"{salt}:{decision_id}".encode()).hexdigest()
    draw = int(digest[:8], 16) / 0xFFFFFFFF
    return draw < rate


def resolve_decision(decision: Mapping[str, Any], arms: Sequence[Arm], *,
                     confidence_bar: float = 0.75,
                     budget: float | None = None,
                     impact: float = 1.0,
                     exploration_rate: float = 0.0,
                     exploration_salt: str = "explore",
                     context: Mapping[str, Any] | None = None) -> GovernorResult:
    """Walk the arms cheapest-first and resolve at the first that suffices.

    An arm's answer is accepted when it resolves with ``confidence >=
    confidence_bar``.  Otherwise the governor considers the next arm and pays for
    it only when the expected value of information — ``impact`` times the
    confidence headroom the next arm could plausibly add — exceeds the next arm's
    cost, and the budget can afford it.  On a deterministic exploration minority
    the governor escalates one rung past a confident answer to keep the priors
    honest.
    """
    ctx = dict(context or {})
    decision_id = str(decision.get("id", decision.get("key", "decision")))
    ladder = sorted(arms, key=lambda a: (a.level, a.cost))
    total_ladder_cost = sum(a.cost for a in ladder)
    total_model_calls = sum(a.model_calls for a in ladder)

    explore = _exploration_draw(decision_id, exploration_rate, exploration_salt)
    arms_run: list[str] = []
    trace: list[dict] = []
    cost_spent = 0.0
    model_calls_made = 0
    best: tuple[Arm, Resolution] | None = None

    for i, arm in enumerate(ladder):
        # Budget gate: cannot afford this arm → stop escalating.
        if budget is not None and cost_spent + arm.cost > budget:
            trace.append({"arm": arm.name, "action": "skipped_over_budget",
                          "would_cost": arm.cost,
                          "remaining": round(budget - cost_spent, 4)})
            break

        res = arm.resolve(decision, ctx)
        arms_run.append(arm.name)
        cost_spent += arm.cost
        model_calls_made += arm.model_calls
        trace.append({"arm": arm.name, "level": arm.level,
                      "resolved": res.resolved,
                      "confidence": round(res.confidence, 3),
                      "abstained": res.abstained, "detail": res.detail})

        if res.resolved and (best is None or res.confidence > best[1].confidence):
            best = (arm, res)

        # Sufficient confidence → stop, unless this is an exploration draw and a
        # costlier arm still remains (escalate exactly one more rung).
        if res.resolved and res.confidence >= confidence_bar:
            if explore and i + 1 < len(ladder):
                explore = False   # spend the one exploration escalation, once
                trace[-1]["note"] = ("confident, but exploring one rung further "
                                     "to keep the priors honest")
                continue
            break

        # Under-confident or abstained → decide whether to pay for the next arm.
        if i + 1 < len(ladder):
            nxt = ladder[i + 1]
            headroom = max(0.0, confidence_bar - res.confidence)
            voi = impact * headroom
            if voi < nxt.cost:
                trace.append({"arm": nxt.name, "action": "not_escalated",
                              "value_of_information": round(voi, 4),
                              "cost": nxt.cost,
                              "reason": "expected information below cost"})
                break

    resolving_arm, resolving_level, answer, resolved = "", -1, None, False
    if best is not None:
        resolving_arm = best[0].name
        resolving_level = best[0].level
        answer = best[1].answer
        resolved = True

    return GovernorResult(
        resolved=resolved, answer=answer, resolving_arm=resolving_arm,
        resolving_level=resolving_level, arms_run=arms_run,
        model_calls_made=model_calls_made,
        model_calls_avoided=max(0, total_model_calls - model_calls_made),
        cost_spent=cost_spent,
        cost_avoided=max(0.0, total_ladder_cost - cost_spent),
        exploration=_exploration_draw(decision_id, exploration_rate,
                                      exploration_salt),
        trace=trace)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # Arms: a deterministic memory arm (free) that may abstain, a small model
    # (cheap), a strong model (dear), a panel (dearest).
    def mem(dec, ctx):
        hit = ctx.get("memory", {}).get(dec["key"])
        if hit is None:
            return Resolution(False, abstained=True, detail="no memory match")
        return Resolution(True, answer=hit["answer"],
                          confidence=hit["confidence"], detail="memory hit")

    def small(dec, ctx):
        return Resolution(True, answer="small:" + dec["key"], confidence=0.6,
                          detail="small model guess")

    def strong(dec, ctx):
        return Resolution(True, answer="strong:" + dec["key"], confidence=0.9,
                          detail="strong model answer")

    def panel(dec, ctx):
        return Resolution(True, answer="panel:" + dec["key"], confidence=0.97,
                          detail="independent panel")

    ladder = [
        Arm("deterministic_memory", 1, 0.0, mem, model_calls=0),
        Arm("small_model", 3, 1.0, small, model_calls=1),
        Arm("strong_model", 4, 8.0, strong, model_calls=1),
        Arm("independent_panel", 5, 40.0, panel, model_calls=5)]

    # 1. A confident memory hit resolves at level 1 with ZERO model calls, and
    #    the receipt shows the model calls it avoided.
    ctx_hit = {"memory": {"d1": {"answer": "cached", "confidence": 0.9}}}
    r1 = resolve_decision({"id": "d1", "key": "d1"}, ladder,
                          confidence_bar=0.75, context=ctx_hit)
    check("a_confident_memory_hit_resolves_with_zero_model_calls",
          r1.resolved and r1.resolving_level == 1 and r1.model_calls_made == 0
          and r1.model_calls_avoided == 7 and r1.answer == "cached"
          and r1.arms_run == ["deterministic_memory"],
          "a confident deterministic-memory hit resolves the decision at the "
          "cheapest rung, makes no model call, and the receipt shows all 7 "
          "would-be model calls avoided — the structural win over a "
          "model-every-step loop")

    # 2. Memory misses → escalate to the small model, which suffices only if the
    #    bar is low; with a high bar it escalates once more to the strong model.
    ctx_miss = {"memory": {}}
    # impact 40: the strong model's information (40 × (0.85−0.6) = 10) now
    # exceeds its cost (8), so paying for it is justified — a genuinely
    # high-impact decision.
    r2 = resolve_decision({"id": "d2", "key": "d2"}, ladder,
                          confidence_bar=0.85, impact=40.0, context=ctx_miss)
    check("a_memory_miss_escalates_only_as_far_as_the_bar_requires",
          r2.resolving_arm == "strong_model" and r2.model_calls_made == 2
          and "deterministic_memory" in r2.arms_run
          and "small_model" in r2.arms_run
          and "independent_panel" not in r2.arms_run,
          "memory abstains, the small model (0.6) is under the 0.85 bar, and for "
          "this high-impact decision the strong model's information beats its "
          "cost, so the governor pays for it (0.9 clears the bar) and STOPS "
          "there — it never pays for the panel")

    # 3. Value-of-information gate: when impact is low, an under-confident cheap
    #    answer is NOT escalated because the next arm costs more than the info.
    r3 = resolve_decision({"id": "d3", "key": "d3"}, ladder,
                          confidence_bar=0.85, impact=1.0, context=ctx_miss)
    # memory abstains (headroom vs small: voi = 1.0*(0.85-0)=0.85 >= 1.0? no) →
    # actually memory abstains with confidence 0; voi to small = 1.0*0.85=0.85 <
    # small.cost 1.0 → not escalated. So nothing resolves.
    check("low_impact_decisions_do_not_escalate_when_info_is_below_cost",
          not r3.resolved and "small_model" not in r3.arms_run
          and any(t.get("action") == "not_escalated" for t in r3.trace),
          "for a low-impact decision the expected information from the small "
          "model (0.85) is below its cost (1.0), so the governor declines to "
          "escalate and leaves the decision unresolved rather than overspending")

    # 4. Budget gate: a tight budget stops escalation before the expensive arm.
    r4 = resolve_decision({"id": "d4", "key": "d4"}, ladder,
                          confidence_bar=0.99, impact=100.0, budget=5.0,
                          context=ctx_miss)
    check("a_tight_budget_stops_escalation_before_the_dear_arms",
          "strong_model" not in r4.arms_run
          and "independent_panel" not in r4.arms_run
          and any(t.get("action") == "skipped_over_budget" for t in r4.trace),
          "with a budget of 5 the governor runs memory (0) and the small model "
          "(1) but cannot afford the strong model (8), so it stops and records "
          "the over-budget skip rather than overspending")

    # 5. Exploration floor: on a drawn decision, escalate one rung past a
    #    confident cheap answer to keep the priors honest.
    # Find a decision id that draws exploration at rate 1.0 (always draws).
    r5 = resolve_decision({"id": "d5", "key": "d5"}, ladder,
                          confidence_bar=0.75, exploration_rate=1.0,
                          context={"memory": {"d5": {"answer": "cached",
                                                     "confidence": 0.9}}})
    check("the_exploration_floor_escalates_past_a_confident_cheap_answer",
          r5.resolved and len(r5.arms_run) >= 2
          and r5.arms_run[0] == "deterministic_memory"
          and any("exploring one rung" in (t.get("note") or "")
                  for t in r5.trace),
          "on an exploration draw the governor takes the confident memory answer "
          "but still runs the next rung, so the cheap prior is continually "
          "re-checked against a costlier arm and never becomes destiny")

    # 6. Determinism.
    r6a = resolve_decision({"id": "d2", "key": "d2"}, ladder,
                           confidence_bar=0.85, impact=40.0, context=ctx_miss)
    check("the_governor_is_deterministic",
          r6a.to_dict()["trace"] == r2.to_dict()["trace"]
          and r6a.answer == r2.answer,
          "the same decision, ladder, and context always produce the identical "
          "escalation trace and answer — replayable, as the engine requires")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "escalation_governor_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
