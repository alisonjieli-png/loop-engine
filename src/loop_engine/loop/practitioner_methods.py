"""Practitioner methods — the checklist and the weighted if-then bundle.

Distil what an engineer actually brings and much of it is a *checklist* and a set
of *heuristics*: "do we have categorical variables? are they nominal? can they be
converted? will that explode the dimensionality?"  Most of that is deterministic
and cheap; some is a bundle of weighted measurements; a little is genuinely
open-ended.  This module gives the two deterministic ends of that spectrum a
home as resolvers, so the loop follows an expert's checklist and weighted rules
with no model — and escalates to deliberation only for what the checklist and
rules cannot settle.

- **checklist_resolver** walks a checklist in order and proposes the remedy for
  the first unsatisfied item — the mechanical "follow the checklist until the
  steps are compatible."  When every item is satisfied it passes, yielding to an
  open regime for the judgement calls a checklist cannot capture.

- **weighted_heuristic_resolver** evaluates a bundle of weighted if-then rules
  and proposes the move whose firing rules accumulate the most weight above a
  threshold — the "twenty weighted measurements" an expert balances at once.

Both are `deterministic`/`hybrid` category resolvers (no model), and both read
the same ``Knowledge.facts``.  Checklists and rule bundles are per-method and
per-domain data (a linear-regression checklist here; a well-drilling or
disease-detection one is another checklist), so the system gets sharper about a
field by adding checklists, exactly as it does by adding packs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..strings.knowledge import Knowledge
from ..loop.moves import move, answer


@dataclass(frozen=True)
class Check:
    """One checklist item: a satisfied?-predicate and the remedy if it is not."""
    id: str
    description: str
    predicate: Callable[[Knowledge], bool]
    remedy_kind: str
    remedy_key: str
    facet: str = ""


Checklist = Sequence[Check]


def checklist_resolver(name: str, checklist: Checklist, *,
                       category: str = "plan_recipe"):
    """A resolver that walks a checklist and proposes the remedy for the first
    unsatisfied item; passes (returns None) when the whole checklist is
    satisfied, so an open regime handles what the checklist cannot."""
    def resolve(knowledge: Knowledge):
        for chk in checklist:
            try:
                ok = chk.predicate(knowledge)
            except Exception:                                   # noqa: BLE001
                ok = False
            if not ok:
                return answer(name, category,
                              [move(chk.remedy_kind, chk.remedy_key,
                                    mechanism=chk.description, confidence=0.9)],
                              0.9, detail=f"checklist item {chk.id}")
        return None
    resolve.__name__ = name
    return resolve


def checklist_status(checklist: Checklist, knowledge: Knowledge) -> dict:
    """Report which checklist items are satisfied and which remain — the
    'coverage' an operator reads to see the checklist being worked."""
    rows = []
    for chk in checklist:
        try:
            ok = bool(chk.predicate(knowledge))
        except Exception:                                       # noqa: BLE001
            ok = False
        rows.append({"id": chk.id, "satisfied": ok, "facet": chk.facet,
                     "description": chk.description})
    remaining = [r["id"] for r in rows if not r["satisfied"]]
    return {"record_type": "checklist_status/v1", "items": rows,
            "satisfied": len(rows) - len(remaining), "total": len(rows),
            "remaining": remaining, "complete": not remaining}


def linear_regression_checklist() -> tuple[Check, ...]:
    """The atomic checklist an expert runs for a linear-regression task (the
    owner's worked example).  Order matters: verify the target, then encoding,
    then dimensionality, then scaling, then collinearity."""
    return (
        Check("target_numeric", "the target must be numeric for regression",
              lambda k: bool(k.fact("target_numeric")),
              "run_tests", "verify_target_is_numeric", "target"),
        Check("categoricals_encoded",
              "categorical variables must be encoded",
              lambda k: not k.fact("has_categorical")
              or bool(k.fact("categoricals_encoded")),
              "add_node", "encoder=onehot_or_target", "encoding"),
        Check("dimensionality_controlled",
              "high-cardinality categoricals must not explode dimensionality",
              lambda k: not k.fact("high_cardinality")
              or bool(k.fact("dimensionality_controlled")),
              "add_node", "encoder=hashing_or_target", "dimensionality"),
        Check("features_scaled", "features must be scaled for a linear model",
              lambda k: bool(k.fact("features_scaled")),
              "add_node", "scaler=standard", "scaling"),
        Check("collinearity_checked", "multicollinearity should be checked",
              lambda k: bool(k.fact("collinearity_checked")),
              "run_tests", "vif_check", "collinearity"),
    )


@dataclass(frozen=True)
class WeightedRule:
    """One weighted if-then measurement: a condition, a weight, and the move it
    argues for."""
    condition: Callable[[Knowledge], bool]
    weight: float
    move_kind: str
    move_key: str
    reason: str = ""


def weighted_heuristic_resolver(name: str, rules: Sequence[WeightedRule], *,
                                threshold: float = 1.0,
                                category: str = "hybrid"):
    """A resolver over a bundle of weighted if-then rules: firing rules add their
    weight to the move they argue for, and the top-weighted move is proposed if
    it clears the threshold.  This is the 'twenty weighted measurements' an
    expert balances to decide one move."""
    def resolve(knowledge: Knowledge):
        scores: dict[tuple[str, str], list] = {}
        for r in rules:
            try:
                fires = r.condition(knowledge)
            except Exception:                                   # noqa: BLE001
                fires = False
            if fires:
                s = scores.setdefault((r.move_kind, r.move_key), [0.0, []])
                s[0] += r.weight
                if r.reason:
                    s[1].append(r.reason)
        if not scores:
            return None
        (kind, key), (score, reasons) = max(
            scores.items(), key=lambda kv: (kv[1][0], kv[0]))
        if score < threshold:
            return None
        conf = min(1.0, score / (threshold * 2.0))
        return answer(name, category,
                      [move(kind, key, mechanism="; ".join(reasons),
                            support=score, confidence=conf)], conf,
                      detail=f"weighted score {score:.2f} >= {threshold}")
    resolve.__name__ = name
    return resolve


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    cl = linear_regression_checklist()
    walk = checklist_resolver("lr_checklist", cl)

    # Nothing done yet -> the first unsatisfied item (verify target) is proposed.
    k0 = Knowledge(goal="regress price", facts={})
    a0 = walk(k0)
    check("the_checklist_proposes_the_first_unsatisfied_item",
          a0 is not None
          and a0.moves.items[0].action_key == "verify_target_is_numeric",
          "with nothing done, the checklist walker proposes verifying the target "
          "is numeric — the first unsatisfied item, in order")

    # Target verified, categoricals present but unencoded -> next item fires.
    k1 = Knowledge(goal="regress price",
                   facts={"target_numeric": True, "has_categorical": True})
    a1 = walk(k1)
    check("the_checklist_advances_to_the_next_unsatisfied_item",
          a1.moves.items[0].action_key == "encoder=onehot_or_target",
          "once the target is verified, the walker advances to 'encode the "
          "categoricals' — the checklist is worked in order until compatible")

    # Everything satisfied -> the checklist passes to an open regime.
    done = {"target_numeric": True, "has_categorical": True,
            "categoricals_encoded": True, "high_cardinality": False,
            "features_scaled": True, "collinearity_checked": True}
    a_done = walk(Knowledge(goal="x", facts=done))
    status = checklist_status(cl, Knowledge(goal="x", facts=done))
    check("a_complete_checklist_passes_and_reports_coverage",
          a_done is None and status["complete"]
          and status["satisfied"] == status["total"],
          "when every checklist item is satisfied the walker passes (yields to "
          "open deliberation) and the status reports full coverage")

    # Weighted heuristic bundle: firing rules accumulate weight; top move wins.
    rules = [
        WeightedRule(lambda k: k.fact("imbalanced"), 0.6, "add_node",
                     "class_weight=balanced", "target is imbalanced"),
        WeightedRule(lambda k: k.fact("small_data"), 0.5, "add_node",
                     "class_weight=balanced", "small data favours weighting"),
        WeightedRule(lambda k: k.fact("many_features"), 0.7, "add_node",
                     "feature_selection=l1", "high feature count"),
    ]
    wr = weighted_heuristic_resolver("imbalance_bundle", rules, threshold=1.0)
    # imbalanced + small_data both argue for class_weight (0.6+0.5=1.1 >= 1.0).
    a_w = wr(Knowledge(goal="x", facts={"imbalanced": True, "small_data": True}))
    check("weighted_rules_accumulate_and_the_top_move_clears_the_threshold",
          a_w is not None
          and a_w.moves.items[0].action_key == "class_weight=balanced"
          and abs(a_w.moves.items[0].support - 1.1) < 1e-9,
          "two firing rules both argue for class-weight; their weights sum to "
          "1.1 which clears the 1.0 threshold, so class-weight is proposed — the "
          "twenty-weighted-measurements pattern")

    # Below threshold -> the bundle abstains (defers to deliberation).
    a_low = wr(Knowledge(goal="x", facts={"imbalanced": True}))  # only 0.6
    check("a_weighted_bundle_below_threshold_abstains",
          a_low is None,
          "a single 0.6-weight rule does not clear the 1.0 threshold, so the "
          "bundle abstains and defers the call — not every measurement forces a "
          "move")

    # Determinism.
    check("practitioner_methods_are_deterministic",
          walk(k1).to_dict() == a1.to_dict()
          and wr(Knowledge(goal="x", facts={"imbalanced": True,
                                            "small_data": True})).to_dict()
          == a_w.to_dict(),
          "the same knowledge always yields the identical checklist and "
          "weighted-heuristic answer")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "practitioner_methods_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
