"""Ask strategies for rigorous next-action selection.

Owner thesis (2026-08-22): once the solver DAG is universal, building pipelines
stops being the competitive advantage.  The advantage is **asking the right
questions in the right ways** — thousands of questions and personas, and many
METHODS of asking: ask directly; ask for the entire solution then drill to the
immediate next step; build a high-level blueprint, then more detail, then more
detail, then choose the most discrete next step; challenge a candidate with "are
you sure, or is there an intermediary step we're missing?"; ask cold with no
context; ask with masked or rephrased context.  Each method is a **strategy**: a
named, tiered recipe that renders one or more ``AskSpec``s through the strict
LLM-call DAG (never its own ad-hoc calls).

Strategies are tiered like store records — core ships, experimental is off by
default, gated needs a grant (the trade-secret industry sets) — and they are
REMIXABLE: ``remix`` derives new variants deterministically (persona x context
policy x emphasis), which is the generate-new-questions loop in its simplest
honest form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..strings.knowledge import Knowledge
from ..core.model_call import AskSpec, execute_ask, AskResult
from ..core.store_serve import TIERS

# A strategy is simple (one AskSpec) or compound (a scripted multi-ask flow).
STRATEGY_SHAPES = ("single", "compound")


@dataclass
class StrategySpec:
    name: str
    shape: str
    tier: str = "core"
    description: str = ""
    # single: build(knowledge, question) -> AskSpec
    build: "Callable[[Knowledge, str], AskSpec] | None" = None
    # compound: run(knowledge, question, ask) -> dict  (ask = execute_ask-like)
    run: "Callable[..., dict] | None" = None

    def __post_init__(self):
        if self.shape not in STRATEGY_SHAPES:
            raise ValueError(f"shape must be one of {STRATEGY_SHAPES}")
        if self.tier not in TIERS:
            raise ValueError(f"tier must be one of {TIERS}")
        if self.shape == "single" and self.build is None:
            raise ValueError("a single strategy needs build()")
        if self.shape == "compound" and self.run is None:
            raise ValueError("a compound strategy needs run()")


# -- core single strategies ---------------------------------------------------


def _direct_next(k: Knowledge, q: str) -> AskSpec:
    return AskSpec(question=q or "What is the single best next move?",
                   knowledge=k, context_policy="fully_informed")


def _full_solution_first_step(k: Knowledge, q: str) -> AskSpec:
    return AskSpec(
        question=("Lay out the ENTIRE solution to this task end to end, "
                  "numbered. Then, on a final line starting 'NEXT:', name the "
                  "single most discrete immediate next step."),
        knowledge=k, context_policy="fully_informed",
        output_contract="numbered steps, then one line 'NEXT: <step>'")


def _cold_ask(k: Knowledge, q: str) -> AskSpec:
    # deliberately NO knowledge: what does a fresh mind propose?
    return AskSpec(question=(q or "What is the single best next move?")
                   + f"\nTask: {k.goal}", knowledge=None)


def _masked_ask(k: Knowledge, q: str) -> AskSpec:
    return AskSpec(question=q or "What is the single best next move?",
                   knowledge=k, context_policy="memory_blind")


# -- core compound strategies -------------------------------------------------


def _are_you_sure(k: Knowledge, question: str, ask=execute_ask, *,
                  candidate: str = "", **_kw) -> dict:
    """Challenge a candidate: sure it is next, or is a step missing before it?"""
    spec = AskSpec(
        question=(f"The proposed next step is: {candidate or question}.\n"
                  "Are you SURE this action should run next, or is there an "
                  "intermediary step we are missing? If a step is missing, name "
                  "it on a line starting 'INTERMEDIARY:'. If not, reply "
                  "'CONFIRMED'."),
        knowledge=k, context_policy="fully_informed")
    res = ask(spec)
    text = res.text if res.ok else ""
    missing = ""
    for line in text.splitlines():
        if line.strip().upper().startswith("INTERMEDIARY:"):
            missing = line.split(":", 1)[1].strip()
    return {"strategy": "are_you_sure_intermediary", "confirmed": not missing,
            "intermediary": missing, "asks": 1,
            "tokens": res.total_tokens, "raw": text[:400]}


def _blueprint_progressive_detail(k: Knowledge, question: str,
                                  ask=execute_ask, *, detail_rounds: int = 2,
                                  **_kw) -> dict:
    """Blueprint -> more detail -> more detail -> the most discrete next step.

    Each round is one AskSpec through the strict call DAG; the final round must
    commit to exactly one discrete step.  The transcript of rounds is returned —
    the drill-down is auditable, not a single opaque answer."""
    rounds: list = []
    tokens = 0
    r1 = ask(AskSpec(
        question=("Develop a HIGH-LEVEL blueprint of ALL the steps to solve "
                  "this task, numbered, one line each."),
        knowledge=k, context_policy="fully_informed"))
    tokens += r1.total_tokens
    rounds.append({"round": "blueprint", "text": (r1.text or "")[:800]})
    current = r1.text or ""
    for i in range(max(0, detail_rounds)):
        ri = ask(AskSpec(
            question=("Here is the current plan:\n" + current[:4000]
                      + "\n\nGo into MORE DETAIL: expand each step into its "
                      "sub-steps, keeping the numbering."),
            knowledge=k, context_policy="graph_only"))
        tokens += ri.total_tokens
        current = ri.text or current
        rounds.append({"round": f"detail_{i + 1}", "text": (ri.text or "")[:800]})
    rf = ask(AskSpec(
        question=("Here is the detailed plan:\n" + current[:4000]
                  + "\n\nChoose the MOST DISCRETE immediate next step — the "
                  "smallest atomic action. Reply with one line starting "
                  "'NEXT:'."),
        knowledge=k, context_policy="goal_only",
        output_contract="one line 'NEXT: <step>'"))
    tokens += rf.total_tokens
    nxt = ""
    for line in (rf.text or "").splitlines():
        if line.strip().upper().startswith("NEXT:"):
            nxt = line.split(":", 1)[1].strip()
    rounds.append({"round": "choose", "text": (rf.text or "")[:400]})
    return {"strategy": "blueprint_progressive_detail", "next_step": nxt,
            "asks": 2 + max(0, detail_rounds), "tokens": tokens,
            "rounds": rounds}


# -- the registry -------------------------------------------------------------


def core_strategies() -> dict:
    return {
        "direct_next": StrategySpec(
            "direct_next", "single", "core",
            "ask the question straight, full context", build=_direct_next),
        "full_solution_first_step": StrategySpec(
            "full_solution_first_step", "single", "core",
            "entire solution end to end, then drill to the immediate next step",
            build=_full_solution_first_step),
        "blueprint_progressive_detail": StrategySpec(
            "blueprint_progressive_detail", "compound", "core",
            "blueprint -> more detail -> more detail -> most discrete next step",
            run=_blueprint_progressive_detail),
        "are_you_sure_intermediary": StrategySpec(
            "are_you_sure_intermediary", "compound", "core",
            "challenge a candidate: is an intermediary step missing?",
            run=_are_you_sure),
        "cold_ask": StrategySpec(
            "cold_ask", "single", "experimental",
            "no context at all — what does a fresh mind propose?",
            build=_cold_ask),
        "masked_memory": StrategySpec(
            "masked_memory", "single", "experimental",
            "memory-blind context — break the anchor on history",
            build=_masked_ask),
    }


class StrategyRegistry:
    """Named, tiered, remixable ways of asking.  Core is always on;
    experimental/gated follow the same switchboard as the stores."""

    def __init__(self, strategies: dict | None = None):
        self._all = dict(strategies or core_strategies())
        self._enabled_tiers: set = {"core"}

    def enable_tier(self, tier: str, *, grant: str = "") -> None:
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}")
        if tier == "gated" and not grant:
            raise PermissionError("the gated tier needs an explicit grant")
        self._enabled_tiers.add(tier)

    def available(self) -> tuple:
        return tuple(sorted(n for n, s in self._all.items()
                            if s.tier in self._enabled_tiers))

    def get(self, name: str) -> StrategySpec:
        s = self._all.get(name)
        if s is None or s.tier not in self._enabled_tiers:
            raise KeyError(f"strategy {name!r} is unknown or its tier is off")
        return s

    def register(self, spec: StrategySpec) -> None:
        self._all[spec.name] = spec

    def remix(self, base_name: str, *, persona: str = "",
              context_policy: str = "", seed: int = 0) -> StrategySpec:
        """Derive a NEW single strategy from a base by swapping the persona
        and/or context policy — deterministic (seeded by the arguments, never a
        clock), registered as experimental until it earns its keep."""
        base = self.get(base_name)
        if base.shape != "single":
            raise ValueError("remix currently derives from single strategies")
        name = f"{base_name}__remix_{seed}"

        def build(k: Knowledge, q: str) -> AskSpec:
            spec = base.build(k, q)
            if persona:
                spec.persona = persona
            if context_policy:
                spec = AskSpec(question=spec.question, knowledge=spec.knowledge,
                               context_policy=context_policy,
                               persona=spec.persona,
                               output_contract=spec.output_contract,
                               details=spec.details, models=spec.models)
            return spec
        new = StrategySpec(name, "single", "experimental",
                           f"remix of {base_name} (persona={persona!r}, "
                           f"policy={context_policy!r})", build=build)
        self.register(new)
        return new


def run_strategy(registry: StrategyRegistry, name: str, knowledge: Knowledge,
                 question: str = "", *, ask=execute_ask, **kw) -> dict:
    """Execute one strategy through the strict LLM-call DAG (injectable for
    tests).  Single strategies return the AskResult record; compound ones
    return their own scripted transcript."""
    spec = registry.get(name)
    if spec.shape == "single":
        res: AskResult = ask(spec.build(knowledge, question))
        return {"strategy": name, "ok": res.ok, "text": res.text,
                "tokens": res.total_tokens, "asks": 1,
                "record": res.record()}
    return spec.run(knowledge, question, ask, **kw)


# ---------------------------------------------------------------------------
# Self-test — offline: injected stub ask, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    k = Knowledge(goal="win the tabular competition", graph_summary="2 nodes",
                  facts={"modality": "tabular"})
    reg = StrategyRegistry()

    # a scripted stub ask: answers depend on the question, offline.
    def stub(spec: AskSpec):
        q = spec.question
        if "HIGH-LEVEL blueprint" in q:
            text = "1. load data\n2. baseline\n3. features\n4. model\n5. submit"
        elif "MORE DETAIL" in q:
            text = "1. load data\n 1a. read csv\n2. baseline\n 2a. majority"
        elif "MOST DISCRETE" in q:
            text = "NEXT: read the train csv and profile dtypes"
        elif "Are you SURE" in q:
            text = "INTERMEDIARY: audit leakage before adding the model"
        else:
            text = "the answer"
        return AskResult(ok=True, text=text, model_used="stub",
                         models_tried=["stub"], total_tokens=7,
                         context_policy=spec.context_policy)

    # 1. core strategies available; experimental off by default.
    avail = reg.available()
    check("core_strategies_ship_and_experimental_is_off_by_default",
          "direct_next" in avail and "blueprint_progressive_detail" in avail
          and "cold_ask" not in avail,
          f"available: {avail}")

    # 2. blueprint -> detail -> detail -> most discrete step, auditable rounds.
    out = run_strategy(reg, "blueprint_progressive_detail", k, ask=stub,
                       detail_rounds=2)
    check("blueprint_drilldown_runs_rounds_and_commits_to_one_discrete_step",
          out["next_step"] == "read the train csv and profile dtypes"
          and out["asks"] == 4
          and [r["round"] for r in out["rounds"]]
          == ["blueprint", "detail_1", "detail_2", "choose"],
          f"4 asks, rounds {[r['round'] for r in out['rounds']]}")

    # 3. are-you-sure finds the missing intermediary step.
    out2 = run_strategy(reg, "are_you_sure_intermediary", k, ask=stub,
                        candidate="add estimator=xgboost")
    check("are_you_sure_surfaces_a_missing_intermediary_step",
          not out2["confirmed"]
          and out2["intermediary"] == "audit leakage before adding the model",
          "the challenge strategy caught the missing leakage audit")

    # 4. the same question renders under DIFFERENT context per strategy.
    s_full = reg.get("direct_next").build(k, "")
    reg.enable_tier("experimental")
    s_cold = reg.get("cold_ask").build(k, "")
    s_mask = reg.get("masked_memory").build(k, "")
    check("strategies_vary_the_context_shown_for_the_same_question",
          s_full.context_policy == "fully_informed"
          and s_cold.knowledge is None
          and s_mask.context_policy == "memory_blind",
          "full / cold / masked are one field apart — the call DAG does the rest")

    # 5. remix derives a NEW registered strategy deterministically.
    new = reg.remix("direct_next", persona="a contrarian ablation engineer",
                    context_policy="graph_only", seed=7)
    spec7 = reg.get(new.name).build(k, "")
    check("remix_derives_new_strategies_deterministically",
          new.name == "direct_next__remix_7"
          and spec7.persona == "a contrarian ablation engineer"
          and spec7.context_policy == "graph_only"
          and new.tier == "experimental",
          "a remixed way-of-asking registers as experimental until it earns "
          "its keep")

    # 6. a strategy on a disabled tier is not reachable.
    reg2 = StrategyRegistry()
    blocked = False
    try:
        reg2.get("cold_ask")
    except KeyError:
        blocked = True
    check("a_strategy_on_a_disabled_tier_is_unreachable", blocked,
          "tier gates apply to ways-of-asking exactly as to records")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "ask_strategies_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
