"""Deliberation strategies — pipelines that decide what is *really* next.

A single "what is next?" call to a model tends to return the generic default —
load, EDA, transform, preprocess, train a tree model, verify — because that is
what dominates training data.  It will not, on its own, reach cell tracking,
principled noise handling, or an advanced nearest-neighbour method.  To get the
real answer you often run a *pipeline* of deliberation.  This module gives those
pipelines a typed home, each as a composite strategy that produces a
``WhatIsNextAnswer`` and can be registered as a resolver:

- **blueprint-then-refine** — first ask for a high-level blueprint, then
  recursively expand each step into sub-steps and alternatives to a chosen
  depth, then read the first step's *refined alternatives* off the detailed plan.
  Forcing depth is what surfaces the non-obvious options a shallow ask skips.

- **fan-out-and-test** — a step is rarely one move.  "Load the data" may have
  five viable ways; the honest answer is *try all five, measure which works best
  and fastest, keep the winner and the runners-up, then move on*.  This strategy
  turns a step into a batch of `run_tests` moves plus a follow-up
  `control.promote`, rather than committing to one guess.

- **multi-context probe** — ask the same decision across deliberately different
  context levels (blind, task-only, memory-informed, research-grounded).  The
  blind and research lanes propose different, often more advanced, methods than
  the single generic call; the strategy unions them and surfaces the ones that
  are NOT in the generic-default set first, so an advanced method is not buried
  under the obvious ones.

These take injected functions (propose/refine/generate/ask), so they are
testable with stubs and pluggable with a real model client — the model stays out
of this module, exactly like the model-backed regimes.  A strategy ORDERS what to
try; the fold oracle still decides what worked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..strings.knowledge import Knowledge
from ..loop.moves import move, answer, WhatIsNextAnswer, family_of

# The generic-default vocabulary a shallow "what next?" tends to return.  Used
# only to FLAG which probed answers are non-default (advanced) — never to filter
# them out.
GENERIC_DEFAULT_TERMS = frozenset({
    "load", "load_data", "eda", "explore", "transform", "preprocess",
    "clean", "feature_engineering", "train", "model", "tree", "tree_model",
    "random_forest", "xgboost", "gradient_boosting", "verify", "evaluate",
    "baseline"})


def _is_advanced(term: str) -> bool:
    t = term.strip().lower().replace(" ", "_").replace("-", "_")
    return not any(d in t for d in GENERIC_DEFAULT_TERMS)


@dataclass
class DeliberationResult:
    strategy: str
    answer: WhatIsNextAnswer
    blueprint: tuple = ()
    considered: tuple[str, ...] = ()
    advanced_surfaced: tuple[str, ...] = ()
    rounds: int = 0

    def to_dict(self) -> dict:
        return {"record_type": "deliberation_result/v1", "strategy": self.strategy,
                "answer": self.answer.to_dict(),
                "blueprint": list(self.blueprint),
                "considered": list(self.considered),
                "advanced_surfaced": list(self.advanced_surfaced),
                "rounds": self.rounds,
                "the_rule": ("a deliberation pipeline surfaces what is REALLY "
                             "next — depth, fan-out, and varied context beat a "
                             "single generic call; the fold oracle still decides "
                             "what worked")}


def blueprint_then_refine(
        knowledge: Knowledge,
        propose_blueprint: Callable[[Knowledge], Sequence[str]],
        refine_step: Callable[[str, int], Sequence[str]], *,
        depth: int = 2, first_step_alternatives: int = 3) -> DeliberationResult:
    """Blueprint first, then recursively refine, then read the first step's
    alternatives.  ``propose_blueprint`` returns the high-level steps;
    ``refine_step(step, depth)`` returns sub-steps/alternatives for a step."""
    top = list(propose_blueprint(knowledge))
    # Recursively expand into a nested plan to `depth`.
    def expand(step: str, d: int) -> dict:
        if d <= 0:
            return {"step": step, "children": []}
        kids = list(refine_step(step, d))
        return {"step": step, "children": [expand(k, d - 1) for k in kids]}
    blueprint = [expand(s, depth) for s in top]
    rounds = depth + 1

    # The first step's refined alternatives become the moves to try.
    first_children = blueprint[0]["children"] if blueprint else []
    alternatives = [c["step"] for c in first_children][:first_step_alternatives]
    if not alternatives and top:
        alternatives = [top[0]]
    moves = [move("move.constructive.instantiate", alt,
                  mechanism=f"refined alternative for first step {top[0]!r}"
                  if top else "", confidence=0.75)
             for alt in alternatives]
    considered = tuple(c["step"] for node in blueprint for c in node["children"])
    advanced = tuple(a for a in considered if _is_advanced(a))
    return DeliberationResult(
        strategy="blueprint_then_refine",
        answer=answer("blueprint_then_refine", "hybrid", moves,
                      confidence=0.75, detail=f"depth {depth} blueprint"),
        blueprint=tuple(blueprint), considered=considered,
        advanced_surfaced=advanced, rounds=rounds)


def fan_out_and_test(
        knowledge: Knowledge,
        generate_candidates: Callable[[Knowledge], Sequence[str]], *,
        step_label: str = "current_step", keep_runners_up: int = 2
        ) -> DeliberationResult:
    """A step becomes 'try all N candidates, keep the best + runners-up'.  Emits
    a batch of ``run_tests`` moves plus a ``control.promote`` follow-up, rather
    than committing to one guess."""
    candidates = list(generate_candidates(knowledge))
    moves = [move("run_tests", f"{step_label}:{c}",
                  mechanism=f"one of {len(candidates)} ways to do "
                  f"'{step_label}' — measure which works best and fastest",
                  confidence=0.7) for c in candidates]
    if candidates:
        moves.append(move("move.control.promote",
                          f"{step_label}:keep_best_plus_{keep_runners_up}_runners_up",
                          mechanism="after the batch, keep the winner and the "
                          f"top {keep_runners_up} runners-up; then move on",
                          confidence=0.8))
    advanced = tuple(c for c in candidates if _is_advanced(c))
    return DeliberationResult(
        strategy="fan_out_and_test",
        answer=answer("fan_out_and_test", "test_driven", moves,
                      confidence=0.75,
                      detail=f"{len(candidates)} candidates for {step_label}"),
        considered=tuple(candidates), advanced_surfaced=advanced, rounds=1)


def multi_context_probe(
        knowledge: Knowledge,
        ask_at_context: Callable[[Knowledge, str], Sequence[str]],
        context_levels: Sequence[str] = ("blind", "task_only",
                                         "memory_informed", "research_grounded"),
        *, top: int = 8) -> DeliberationResult:
    """Ask the same decision across context levels and union the answers,
    surfacing NON-default (advanced) methods first so they are not buried under
    the obvious ones.  ``ask_at_context(knowledge, level)`` returns proposed
    methods for that context level."""
    seen: dict[str, dict] = {}
    for level in context_levels:
        try:
            proposed = list(ask_at_context(knowledge, level)) or []
        except Exception:                                       # noqa: BLE001
            proposed = []
        for term in proposed:
            key = term.strip().lower()
            row = seen.setdefault(key, {"display": term, "levels": [],
                                        "advanced": _is_advanced(term)})
            if level not in row["levels"]:
                row["levels"].append(level)
    # Rank: advanced first, then by how many independent context lanes proposed
    # it (breadth of support), then name.
    rows = sorted(seen.values(),
                  key=lambda r: (0 if r["advanced"] else 1, -len(r["levels"]),
                                 r["display"].lower()))
    moves = [move("move.constructive.instantiate", r["display"],
                  mechanism=("advanced method surfaced by "
                             + ", ".join(r["levels"]) if r["advanced"]
                             else "proposed by " + ", ".join(r["levels"])),
                  support=len(r["levels"]),
                  confidence=0.6 + 0.05 * len(r["levels"]))
             for r in rows[:top]]
    advanced = tuple(r["display"] for r in rows if r["advanced"])
    return DeliberationResult(
        strategy="multi_context_probe",
        answer=answer("multi_context_probe", "llm_council", moves,
                      confidence=0.7,
                      detail=f"probed {len(context_levels)} context levels"),
        considered=tuple(r["display"] for r in rows),
        advanced_surfaced=advanced, rounds=len(context_levels))


def as_resolver(name: str, strategy_fn: Callable[[Knowledge], DeliberationResult],
                *, category: str = "hybrid"):
    """Wrap a bound deliberation strategy as a what-is-next resolver (returns the
    strategy's answer, or None if it produced no moves)."""
    def resolve(knowledge: Knowledge):
        result = strategy_fn(knowledge)
        return result.answer if result.answer.moves.items else None
    resolve.__name__ = name
    return resolve


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    k = Knowledge(goal="predict churn")

    # blueprint_then_refine: high-level plan, refined to depth, first step's
    # alternatives become the moves.
    def propose_bp(_k):
        return ["load_data", "model"]
    def refine(step, d):
        return {"load_data": ["read_csv", "memory_map_parquet", "streaming_loader"],
                "model": ["advanced_knn", "gradient_boosting"]}.get(step, [])
    bp = blueprint_then_refine(k, propose_bp, refine, depth=2,
                               first_step_alternatives=3)
    check("blueprint_then_refine_reads_first_step_alternatives_from_the_plan",
          bp.rounds == 3 and len(bp.blueprint) == 2
          and [m.action_key for m in bp.answer.moves.items]
          == ["read_csv", "memory_map_parquet", "streaming_loader"]
          and all(family_of(m.action_kind) == "constructive"
                  for m in bp.answer.moves.items),
          "a depth-2 blueprint expands load_data into three loaders; the "
          "answer's moves are those refined alternatives, not the generic "
          "top-level step")

    # fan_out_and_test: five loaders -> five run_tests + a promote follow-up.
    def five_loaders(_k):
        return ["read_csv", "pyarrow", "polars", "duckdb", "streaming"]
    fo = fan_out_and_test(k, five_loaders, step_label="load_data",
                          keep_runners_up=2)
    kinds = [m.action_kind for m in fo.answer.moves.items]
    check("fan_out_and_test_tries_all_candidates_then_promotes_best_and_runners_up",
          kinds.count("run_tests") == 5
          and any(x == "move.control.promote" for x in kinds)
          and "runners_up" in fo.answer.moves.items[-1].action_key,
          "five ways to load the data become five run_tests moves plus a "
          "control.promote that keeps the winner and two runners-up — 'try all "
          "five, then move on', not one guess")

    # multi_context_probe: advanced methods surface above the generic default.
    def ask(_k, level):
        return {"task_only": ["tree_model", "eda"],
                "blind": ["baseline", "advanced_knn"],
                "memory_informed": ["gradient_boosting"],
                "research_grounded": ["cell_tracking", "noise_robust_knn"],
                }.get(level, [])
    mc = multi_context_probe(k, ask)
    top_keys = [m.action_key for m in mc.answer.moves.items]
    check("multi_context_probe_surfaces_advanced_methods_above_the_default",
          "cell_tracking" in mc.advanced_surfaced
          and "advanced_knn" in mc.advanced_surfaced
          and top_keys[0] in ("advanced_knn", "cell_tracking", "noise_robust_knn")
          and "tree_model" not in top_keys[:2],
          "probing blind/task/memory/research context levels surfaces "
          "cell_tracking and advanced_knn (which a single generic call misses) "
          "and ranks them above the default tree_model")

    # determinism + resolver wrapping.
    fo2 = fan_out_and_test(k, five_loaders, step_label="load_data",
                           keep_runners_up=2)
    resolver = as_resolver("fanout", lambda kn: fan_out_and_test(
        kn, five_loaders, step_label="load_data"))
    r_ans = resolver(k)
    check("strategies_are_deterministic_and_wrap_as_resolvers",
          fo2.to_dict() == fo.to_dict() and r_ans is not None
          and r_ans.category == "test_driven",
          "the same inputs produce the identical deliberation result, and a "
          "strategy wraps cleanly as a what-is-next resolver")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "deliberation_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
