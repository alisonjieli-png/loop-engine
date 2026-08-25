"""Route bridge — translate a What-Is-Next decision into engine route priors.

The expert loop decides what to try; the arrangement-search engine decides what
wins.  This module is the adapter between them: it turns a decision's TRY and
DO_NOT_TRY slates into the *priors* the engine already consumes — a bias over
which slot fillings to try first, which to avoid, and any ordering hint — so the
loop can warm-start and steer a route without ever authoring the arrangement
itself.

It lives here, non-pinned, so building it does not touch the pinned route or the
drift-guarded engine.  The actual wiring — the route importing this and reading
the prior bundle — is a one-line change on the route in a deliberate re-pin
cycle; the bridge that change depends on is ready now.  The bridge only biases
ORDER: it never removes a filling from the engine's search, and it emits a plain
dict the engine can merge with its own pheromone and analogy priors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .decision_slates import Slate, Proposal


def _parse_slot_filling(action_key: str) -> "tuple[str, str] | None":
    """A constructive move key like 'estimator=hgb' names a slot filling; an
    action like 'run_tests:leakage' does not.  Returns (slot, filling) or None."""
    if "=" in action_key:
        slot, _, filling = action_key.partition("=")
        slot, filling = slot.strip(), filling.strip()
        if slot and filling:
            return slot, filling
    return None


@dataclass
class RoutePriors:
    """A bias the engine can merge with its own priors.  Order only — never a
    filter."""
    filling_priors: dict = field(default_factory=dict)   # "slot=filling" -> weight
    avoid: dict = field(default_factory=dict)            # "slot=filling" -> reason
    actions: list = field(default_factory=list)          # non-graph moves (tests, research)
    ordering_hints: list = field(default_factory=list)   # (before_key, after_key)

    def to_engine_dict(self) -> dict:
        return {"record_type": "route_priors/v1",
                "filling_priors": dict(self.filling_priors),
                "avoid": dict(self.avoid), "actions": list(self.actions),
                "ordering_hints": [list(h) for h in self.ordering_hints],
                "the_rule": ("priors bias the ORDER the engine tries fillings; "
                             "they never remove a filling from the search, and "
                             "the fold oracle still decides what wins")}


def priors_from_slate(try_slate: Slate, *, avoid_slate: Slate | None = None,
                      weight_scale: float = 1.0) -> RoutePriors:
    """Build route priors from a decision's TRY (and optional DO_NOT_TRY) slate.
    A constructive move becomes a filling prior weighted by the move's support/
    confidence; a non-graph move (test, research) is recorded as an action to run
    first, not a graph edit; a hard/invalid avoid becomes an avoid entry."""
    priors = RoutePriors()
    for p in try_slate.items:
        sf = _parse_slot_filling(p.action_key)
        base = max(p.support, p.confidence, 0.0) * weight_scale
        if sf:
            key = f"{sf[0]}={sf[1]}"
            priors.filling_priors[key] = priors.filling_priors.get(key, 0.0) + base
        else:
            priors.actions.append({"kind": p.action_kind, "key": p.action_key,
                                   "weight": round(base, 4)})
    if avoid_slate is not None:
        for p in avoid_slate.items:
            sf = _parse_slot_filling(p.action_key)
            key = f"{sf[0]}={sf[1]}" if sf else p.action_key
            # Only a HARD/invalid avoid biases the engine; a soft 'not now' is
            # advisory and does not suppress ordering.
            if p.hard or p.disposition in ("invalid", "already_tried"):
                priors.avoid[key] = (p.reasons_against[0]
                                     if p.reasons_against else p.disposition)
    return priors


def merge_priors(*bundles: RoutePriors) -> RoutePriors:
    """Combine several prior bundles — summing filling weights, unioning avoids
    and actions.  Used to fold whats_next priors with pheromone/analogy priors."""
    out = RoutePriors()
    for b in bundles:
        for k, w in b.filling_priors.items():
            out.filling_priors[k] = out.filling_priors.get(k, 0.0) + w
        for k, r in b.avoid.items():
            out.avoid.setdefault(k, r)
        out.actions.extend(b.actions)
        out.ordering_hints.extend(b.ordering_hints)
    return out


def bridge_from_decision(decision: Mapping[str, Any]) -> RoutePriors:
    """Build priors directly from an arbiter NextMoveDecision dict (its selected
    moves become filling priors; its rejected/gate-excluded become avoids)."""
    priors = RoutePriors()
    for sel in decision.get("selected", ()):
        key = sel.get("move", "")
        sf = _parse_slot_filling(key)
        w = float(sel.get("utility", 1.0))
        if sf:
            k = f"{sf[0]}={sf[1]}"
            priors.filling_priors[k] = priors.filling_priors.get(k, 0.0) + w
        else:
            priors.actions.append({"kind": sel.get("kind", ""), "key": key,
                                   "weight": w})
    for g in decision.get("gate_excluded", ()):
        key = g.get("move", "")
        sf = _parse_slot_filling(key)
        priors.avoid[f"{sf[0]}={sf[1]}" if sf else key] = "gate_excluded"
    return priors


# ---------------------------------------------------------------------------
# Self-test — deterministic, no engine, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    try_slate = Slate("try", [
        Proposal("move.constructive.add", "estimator=hgb", support=0.7),
        Proposal("move.constructive.add", "estimator=lightgbm", support=0.5),
        Proposal("run_tests", "leakage_audit", confidence=0.9)])
    avoid_slate = Slate("do_not_try", [
        Proposal("move.constructive.add", "estimator=deepnet",
                 disposition="invalid", hard=True,
                 reasons_against=("not installed",))])

    priors = priors_from_slate(try_slate, avoid_slate=avoid_slate)
    check("constructive_moves_become_weighted_filling_priors",
          priors.filling_priors.get("estimator=hgb") == 0.7
          and priors.filling_priors.get("estimator=lightgbm") == 0.5,
          "the two estimator moves become filling priors weighted by their "
          "support — a warm-start bias the engine can merge")

    check("non_graph_moves_become_actions_not_fillings",
          any(a["key"] == "leakage_audit" for a in priors.actions)
          and "leakage_audit" not in priors.filling_priors,
          "a run_tests move is recorded as an action to run first, NOT a graph "
          "filling — the loop's information action is not mistaken for a node")

    check("a_hard_avoid_biases_the_engine_a_soft_one_does_not",
          "estimator=deepnet" in priors.avoid,
          "the hard/invalid avoid (deepnet not installed) becomes an avoid "
          "entry; a soft 'not now' would not suppress ordering")

    engine = priors.to_engine_dict()
    check("the_bridge_emits_a_plain_engine_dict_that_only_biases_order",
          engine["filling_priors"]["estimator=hgb"] == 0.7
          and "never remove a filling" in engine["the_rule"],
          "the bridge emits a plain dict the engine can merge, stating it biases "
          "order and never removes a filling from the search")

    # Merge with a pheromone-style prior bundle.
    pher = RoutePriors(filling_priors={"estimator=hgb": 0.3,
                                       "scaler=standard": 0.4})
    merged = merge_priors(priors, pher)
    check("priors_merge_by_summing_filling_weights",
          abs(merged.filling_priors["estimator=hgb"] - 1.0) < 1e-9
          and merged.filling_priors["scaler=standard"] == 0.4,
          "merging the whats_next priors with a pheromone bundle sums the hgb "
          "weight (0.7+0.3) and keeps the scaler prior — one bundle for the "
          "engine")

    # From an arbiter decision dict.
    dec_priors = bridge_from_decision({
        "selected": [{"move": "estimator=catboost", "utility": 0.8}],
        "gate_excluded": [{"move": "estimator=forbidden"}]})
    check("priors_build_from_an_arbiter_decision_dict",
          dec_priors.filling_priors.get("estimator=catboost") == 0.8
          and "estimator=forbidden" in dec_priors.avoid,
          "an arbiter decision's selected move becomes a filling prior and its "
          "gate-excluded move an avoid — the bridge consumes the decision plane "
          "directly")

    # Determinism.
    check("the_bridge_is_deterministic",
          priors_from_slate(try_slate, avoid_slate=avoid_slate).to_engine_dict()
          == engine,
          "the same slates always produce the identical prior bundle")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "route_bridge_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
