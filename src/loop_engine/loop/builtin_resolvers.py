"""Builtin resolvers — the session's modules wired in as next-action decision regimes.

The loop is only as good as its resolvers, and the point of this session's work
is that the resolvers already exist.  This module wires the deterministic ones in
as registered regimes so the loop uses them out of the box, and it is the worked
example for adding a regime: each is a small ``(Knowledge) -> NextActionProposal``
function registered under a named category.

Only deterministic backends are registered here (they run with no model and are
self-testable).  Model-backed regimes — the swarm planner (``llm_single`` /
``hybrid``) and the adversarial council (``llm_council``) — are registered by the
caller with a live model client, because their cost and their tokens are real;
this module keeps the model out of the default path so most steps stay free.
"""

from __future__ import annotations

from typing import Any, Callable

from ..strings.knowledge import Knowledge
from ..loop.moves import NextActionProposal, answer, move
from ..loop.registry import ResolverRegistry, DEFAULT_REGISTRY


def plan_recipe_resolver(knowledge: Knowledge) -> NextActionProposal | None:
    """plan_recipe: if a recipe of predefined steps is supplied as blueprints,
    follow the next one.  When the recipe runs out, pass so an open-ended regime
    takes over — exactly the "first ten steps predefined, then open" behaviour."""
    steps = list(knowledge.blueprints)
    done = len([r for r in knowledge.results if r is not None])
    if done < len(steps):
        nxt = steps[done]
        return answer("plan_recipe", "plan_recipe",
                      [move("add_node", str(nxt),
                            mechanism=f"recipe step {done + 1} of {len(steps)}",
                            confidence=0.95)], confidence=0.95)
    return None


def blind_baseline_resolver(knowledge: Knowledge) -> NextActionProposal | None:
    """blind: with almost no context — just that the graph is empty and needs a
    start — propose a safe deterministic baseline.  A diversity lane that never
    reads memory, so it cannot inherit history's bias."""
    if ("empty_graph" in knowledge.open_obligations
            or (not knowledge.fact("has_baseline")
                and not knowledge.fact("has_model"))):
        return answer("blind_baseline", "blind",
                      [move("add_node", "baseline=deterministic_default",
                            mechanism="empty graph; establish a control baseline "
                            "with no memory or model input", confidence=0.72)],
                      confidence=0.72)
    return None


def make_fingerprint_resolver(store: Any) -> Callable[[Knowledge],
                                                      "NextActionProposal | None"]:
    """fingerprint_recall: muscle memory.  Given a ``list_intelligence`` store
    and the knowledge's situation (read from ``frame.extra['situation']``),
    recall the leading previously-accepted move for a matching situation.  This
    is the deterministic, no-model 'this looks like one we've solved' path."""
    def resolve(knowledge: Knowledge) -> "NextActionProposal | None":
        situation = {}
        if isinstance(knowledge.frame.extra, dict):
            situation = knowledge.frame.extra.get("situation", {}) or {}
        try:
            leaders = store.leaders("method", situation, top_n=3)
        except Exception:                                       # noqa: BLE001
            return None
        # Only recall a move that has actually WON before (accepted > 0) — a
        # suggestion that was never accepted is not muscle memory.
        won = [r for r in leaders if r.get("accepted", 0) > 0]
        if not won:
            return None
        moves = [move("add_node", r["display"],
                      mechanism=f"recalled winner ({r['accepted']}x) for a "
                      f"matching situation", support=r["accepted"],
                      confidence=0.85) for r in won[:1]]
        return answer("fingerprint_recall", "fingerprint_recall", moves,
                      confidence=0.85)
    return resolve


def register_builtins(registry: ResolverRegistry = DEFAULT_REGISTRY, *,
                      fingerprint_store: Any = None,
                      replace: bool = True) -> ResolverRegistry:
    """Register the deterministic builtin regimes into a registry.  If a
    ``fingerprint_store`` (a ``list_intelligence.ListIntelligence``) is given, the
    muscle-memory regime is registered too; otherwise it is skipped."""
    registry.register_regime("plan_recipe", "plan_recipe", plan_recipe_resolver,
                             replace=replace)
    registry.register_regime("blind_baseline", "blind", blind_baseline_resolver,
                             replace=replace)
    if fingerprint_store is not None:
        registry.register_regime(
            "fingerprint_recall", "fingerprint_recall",
            make_fingerprint_resolver(fingerprint_store), replace=replace)
    return registry
