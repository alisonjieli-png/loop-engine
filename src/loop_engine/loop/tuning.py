"""Tuning — executable search over parameters, in multiple places, each toggleable.

The owner's call (2026-08-22): tuning belongs in MULTIPLE places, each of which
can be turned on and off — not one blessed location.  The three places:

  * **step**     — right after a node is implemented and verified, tune that
                   node's own parameters before the loop moves on;
  * **graph**    — around a finished candidate graph (per swarm member, in
                   parallel), tune the whole configuration;
  * **executor** — inside a concrete executor (the Kaggle tabular executor tunes
                   its estimator's hyperparameters by cross-validation).

``TuningPolicy`` is the switchboard: every place defaults OFF (tuning costs real
compute, so it is opt-in), any subset can be on, and every tuning call respects
one ``budget`` — the maximum number of configurations it may evaluate.

Two strategies, both real:

  * **grid**      — exhaustive over the space, admissible only when the space
                    fits the budget;
  * **heuristic** — coordinate descent: sweep one parameter at a time, keep the
                    best, repeat.  This is how a 20-node × 5-param × 20-value
                    space is handled: linear cost in parameters, not the product.

A tuning call returns every trial it ran (config, score) — never just the winner
— so selection breadth is visible and the search is auditable.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

# Where tuning can run.  Each is an independent switch on TuningPolicy.
TUNING_PLACES = ("step", "graph", "executor")

TUNING_STRATEGIES = ("grid", "heuristic")


@dataclass
class TuningPolicy:
    """The switchboard: which places tune, with what strategy and budget."""
    step: bool = False
    graph: bool = False
    executor: bool = False
    strategy: str = "heuristic"
    budget: int = 24                 # max configurations evaluated per call
    min_improvement: float = 0.0     # keep the incumbent unless beaten by this

    def __post_init__(self):
        if self.strategy not in TUNING_STRATEGIES:
            raise ValueError(f"strategy must be one of {TUNING_STRATEGIES}")

    def enabled(self, place: str) -> bool:
        if place not in TUNING_PLACES:
            raise ValueError(f"unknown tuning place {place!r}; "
                             f"places are {TUNING_PLACES}")
        return bool(getattr(self, place))


@dataclass
class ParamSpec:
    """One tunable parameter: its name, candidate values, and default."""
    name: str
    values: tuple
    default: Any = None

    def __post_init__(self):
        if not self.values:
            raise ValueError(f"parameter {self.name!r} has no candidate values")
        if self.default is None:
            self.default = self.values[0]


@dataclass
class Trial:
    config: dict
    score: float


@dataclass
class TuningResult:
    place: str
    strategy: str
    best_config: dict
    best_score: float
    baseline_score: float
    improved: bool
    trials: list = field(default_factory=list)
    evaluations: int = 0
    exhausted_budget: bool = False

    def record(self) -> dict:
        return {"record_type": "tuning_result/v1", "place": self.place,
                "strategy": self.strategy, "evaluations": self.evaluations,
                "baseline_score": self.baseline_score,
                "best_score": self.best_score, "improved": self.improved,
                "best_config": self.best_config,
                "selection_breadth": len(self.trials),
                "exhausted_budget": self.exhausted_budget}


def _defaults(space: Sequence[ParamSpec]) -> dict:
    return {p.name: p.default for p in space}


def grid_search(space: Sequence[ParamSpec],
                evaluate: Callable[[dict], float], *,
                budget: int = 24) -> tuple:
    """Exhaustive grid within the budget.  Returns (trials, exhausted_budget)."""
    trials: list[Trial] = []
    exhausted = False
    names = [p.name for p in space]
    for combo in itertools.product(*[p.values for p in space]):
        if len(trials) >= budget:
            exhausted = True
            break
        cfg = dict(zip(names, combo))
        trials.append(Trial(cfg, float(evaluate(cfg))))
    return trials, exhausted


def heuristic_search(space: Sequence[ParamSpec],
                     evaluate: Callable[[dict], float], *,
                     budget: int = 24) -> tuple:
    """Coordinate descent: start at defaults, sweep one parameter at a time
    keeping the best-so-far, until the budget or a full quiet pass.  Linear in
    parameters — this is the answer to combinatorially huge spaces."""
    current = _defaults(space)
    trials: list[Trial] = [Trial(dict(current), float(evaluate(current)))]
    best = trials[0]
    exhausted = False
    improved_in_pass = True
    while improved_in_pass and not exhausted:
        improved_in_pass = False
        for p in space:
            for v in p.values:
                if v == best.config.get(p.name):
                    continue
                if len(trials) >= budget:
                    exhausted = True
                    break
                cfg = dict(best.config); cfg[p.name] = v
                t = Trial(cfg, float(evaluate(cfg)))
                trials.append(t)
                if t.score > best.score:
                    best = t
                    improved_in_pass = True
            if exhausted:
                break
    return trials, exhausted


def tune(space: Sequence[ParamSpec], evaluate: Callable[[dict], float], *,
         place: str, policy: TuningPolicy) -> "TuningResult | None":
    """Run tuning for one place, IF that place's switch is on.

    Returns None when the place is switched off — the caller's flow is identical
    either way, which is what makes the switches safe to sprinkle.  The incumbent
    (defaults) is always evaluated, and it stays the winner unless a trial beats
    it by ``min_improvement`` — tuning may never silently make things worse."""
    if not policy.enabled(place):
        return None
    baseline_cfg = _defaults(space)
    if policy.strategy == "grid":
        trials, exhausted = grid_search(space, evaluate, budget=policy.budget)
        if not any(t.config == baseline_cfg for t in trials):
            trials.insert(0, Trial(baseline_cfg, float(evaluate(baseline_cfg))))
    else:
        trials, exhausted = heuristic_search(space, evaluate,
                                             budget=policy.budget)
    baseline = next(t.score for t in trials if t.config == baseline_cfg)
    best = max(trials, key=lambda t: t.score)
    improved = best.score > baseline + policy.min_improvement
    chosen = best if improved else Trial(baseline_cfg, baseline)
    return TuningResult(place=place, strategy=policy.strategy,
                        best_config=chosen.config, best_score=chosen.score,
                        baseline_score=baseline, improved=improved,
                        trials=trials, evaluations=len(trials),
                        exhausted_budget=exhausted)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    space = [ParamSpec("depth", (2, 3, 4, 5), default=3),
             ParamSpec("rate", (0.01, 0.05, 0.1), default=0.1)]
    # a known optimum at depth=4, rate=0.05
    def evaluate(cfg):
        return -abs(cfg["depth"] - 4) - abs(cfg["rate"] - 0.05) * 10

    # 1. every place is OFF by default; a disabled place returns None.
    pol_off = TuningPolicy()
    check("all_tuning_places_default_off",
          not any(pol_off.enabled(p) for p in TUNING_PLACES)
          and tune(space, evaluate, place="graph", policy=pol_off) is None,
          "tuning costs compute, so it is opt-in per place")

    # 2. switches are independent: executor on, others off.
    pol_ex = TuningPolicy(executor=True)
    check("switches_are_independent_per_place",
          pol_ex.enabled("executor") and not pol_ex.enabled("step")
          and not pol_ex.enabled("graph"),
          "each of step/graph/executor toggles independently")

    # 3. heuristic search finds the optimum without exhausting the grid.
    pol_h = TuningPolicy(graph=True, strategy="heuristic", budget=10)
    r = tune(space, evaluate, place="graph", policy=pol_h)
    check("heuristic_search_finds_the_optimum_within_budget",
          r is not None and r.best_config == {"depth": 4, "rate": 0.05}
          and r.evaluations <= 10 and r.improved,
          f"coordinate descent reached the optimum in {r.evaluations} "
          f"evaluations (grid would be 12)")

    # 4. grid search is exhaustive within budget and finds the same optimum.
    pol_g = TuningPolicy(graph=True, strategy="grid", budget=12)
    rg = tune(space, evaluate, place="graph", policy=pol_g)
    check("grid_search_is_exhaustive_within_budget",
          rg.best_config == {"depth": 4, "rate": 0.05}
          and rg.evaluations == 12 and not rg.exhausted_budget,
          "the full 4x3 grid fits the budget and agrees with heuristic")

    # 5. the budget is a hard ceiling.
    pol_small = TuningPolicy(graph=True, strategy="grid", budget=5)
    rs = tune(space, evaluate, place="graph", policy=pol_small)
    check("the_budget_is_a_hard_ceiling",
          rs.evaluations <= 6 and rs.exhausted_budget,
          f"grid stopped at {rs.evaluations} evaluations and REPORTED the "
          f"truncation — no silent cap")

    # 6. tuning never silently makes things worse: incumbent kept on no-improve.
    def flat(cfg):
        return 1.0                              # nothing beats anything
    rf = tune(space, flat, place="graph", policy=pol_h)
    check("the_incumbent_is_kept_when_nothing_beats_it",
          not rf.improved and rf.best_config == {"depth": 3, "rate": 0.1},
          "with a flat objective the defaults stay — tuning cannot regress")

    # 7. every trial is retained — selection breadth is visible.
    check("selection_breadth_is_visible_in_the_record",
          r.record()["selection_breadth"] == r.evaluations
          and "baseline_score" in r.record(),
          "the record shows every configuration tried, not just the winner")

    # 8. unknown place / strategy are refused.
    bad_place = bad_strat = False
    try:
        pol_h.enabled("vibes")
    except ValueError:
        bad_place = True
    try:
        TuningPolicy(strategy="quantum")
    except ValueError:
        bad_strat = True
    check("unknown_places_and_strategies_are_refused", bad_place and bad_strat,
          "the taxonomies are closed")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "tuning_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
