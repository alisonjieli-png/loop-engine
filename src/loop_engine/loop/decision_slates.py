"""Decision slates — the shared, typed vocabulary every deliberation emits.

A decision cell must never return one blurred answer. It returns separate
ranked slates that it never conflates:

- **TRY** — actions worth testing next, best first;
- **DO_NOT_TRY** — actions to skip now, each with the condition that would
  bring it back (never a permanent blacklist);
- **NEED_INFORMATION** — observations or research that would change the ranking;
- **CONTRADICTION** — unresolved disagreements and their cause;
- **CAPABILITY_GAP** — a needed capability nothing in the registry supplies;
- **EXPERIMENT** — the cheapest test that discriminates among proposals;
- **ABSTAIN** — why no valid recommendation was possible.

This module is that shared contract, and nothing more: small, pure, and
self-testing, so the next-move planner and the adversarial council both speak
one language and an SDK (or a human) can read either one.  Two disciplines are
built into the types themselves, because they are the ones a swarm most easily
violates:

1. **A proposal is never a promotion.**  A slate ORDERS; the fold oracle
   decides.  Every rendered slate says so.
2. **A negative item is never permanent.**  Each carries a ``disposition`` —
   invalid, not_now, dominated, already_tried, or unknown — and, unless it is a
   hard prohibition, a ``reconsider_when`` condition.  A method rejected today
   because the split was unverified must be reachable again once the split is
   verified.

Run: ``python -m loop_engine.loop.decision_slates --self-test``.
Architectural role: Practitioner Loop.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Sequence

# The slate kinds, matching the specification's DecisionCell output contract.
SLATE_KINDS = ("try", "do_not_try", "need_information", "contradiction",
               "capability_gap", "experiment", "abstain")

# Why a negative item is negative — kept distinct because the four have very
# different lifetimes: an INVALID move never comes back, an ALREADY_TRIED one
# comes back if the graph changes, a NOT_NOW one comes back when its condition
# holds, a DOMINATED one comes back if its dominator is refuted.
NEGATIVE_DISPOSITIONS = ("invalid", "not_now", "dominated", "already_tried",
                         "unknown")


@dataclass(frozen=True)
class Proposal:
    """One typed thing to try or avoid, with its reasons and its falsifier.

    ``mechanism`` is the claim about WHY this would change the outcome — the
    thing an oracle can later confirm or refute.  ``support`` is a 0..1 measure
    of how much of the independent swarm endorsed it (agreement, not
    performance).  ``falsification_test`` names the cheapest check that would
    settle it — the spec requires every proposal to carry one.
    """
    action_kind: str                     # e.g. "swap_filling", "add_node"
    action_key: str                      # canonical id, e.g. "estimator=hgb"
    mechanism: str = ""
    support: float = 0.0
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    reasons_against: tuple[str, ...] = field(default_factory=tuple)
    falsification_test: str = ""
    # Negative-slate only:
    disposition: str = ""                # one of NEGATIVE_DISPOSITIONS
    reconsider_when: str = ""            # empty ⇒ hard prohibition
    hard: bool = False

    def to_dict(self) -> dict:
        out = {k: (list(v) if isinstance(v, tuple) else v)
               for k, v in asdict(self).items()}
        # Drop the negative-only fields when they are unused, so a TRY item
        # renders clean.
        if not self.disposition and not self.reconsider_when and not self.hard:
            for key in ("disposition", "reconsider_when", "hard"):
                out.pop(key, None)
        return out


_THE_RULE = ("this slate ORDERS what to consider; it never removes a move from "
             "the search and never claims a move will win — the fold oracle "
             "decides, and a blind/random lane always runs alongside")


@dataclass
class Slate:
    """A ranked, typed list of proposals of one kind, plus its honest header."""
    kind: str
    items: list[Proposal] = field(default_factory=list)
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in SLATE_KINDS:
            raise ValueError(f"unknown slate kind {self.kind!r}; "
                             f"expected one of {SLATE_KINDS}")
        for item in self.items:
            if self.kind == "do_not_try" and item.disposition \
                    and item.disposition not in NEGATIVE_DISPOSITIONS:
                raise ValueError(
                    f"negative item {item.action_key!r} has unknown "
                    f"disposition {item.disposition!r}")

    def top(self, n: int) -> list[Proposal]:
        return self.items[:max(0, n)]

    def to_dict(self) -> dict:
        return {"record_type": "decision_slate/v1", "kind": self.kind,
                "count": len(self.items),
                "items": [p.to_dict() for p in self.items],
                "note": self.note or _THE_RULE}


def slate_set_to_dict(slates: Mapping[str, Slate]) -> dict:
    """Render a whole set of slates from one decision, keyed by kind."""
    return {"record_type": "decision_slate_set/v1",
            "the_rule": _THE_RULE,
            "slates": {kind: slate.to_dict() for kind, slate in slates.items()}}


def merge_negative(*slates: Slate) -> Slate:
    """Union several DO_NOT_TRY slates, keeping the STRONGEST objection per
    action (a hard prohibition beats a soft one; an invalid disposition beats a
    not_now).  Used to fold the council's vetoes into the planner's avoid-list.
    """
    strength = {"invalid": 4, "already_tried": 3, "dominated": 2,
                "not_now": 1, "unknown": 0, "": 0}
    best: dict[str, Proposal] = {}
    for slate in slates:
        if slate.kind != "do_not_try":
            raise ValueError("merge_negative only accepts do_not_try slates")
        for item in slate.items:
            key = f"{item.action_kind}:{item.action_key}"
            prior = best.get(key)
            if prior is None:
                best[key] = item
                continue
            # Keep the harder / higher-disposition objection; union reasons.
            keep = item if (item.hard, strength.get(item.disposition, 0)) \
                > (prior.hard, strength.get(prior.disposition, 0)) else prior
            other = prior if keep is item else item
            merged_reasons = tuple(dict.fromkeys(
                keep.reasons_against + other.reasons_against))
            best[key] = Proposal(
                action_kind=keep.action_kind, action_key=keep.action_key,
                mechanism=keep.mechanism, support=keep.support,
                confidence=keep.confidence, reasons=keep.reasons,
                reasons_against=merged_reasons,
                falsification_test=keep.falsification_test,
                disposition=keep.disposition,
                reconsider_when=keep.reconsider_when, hard=keep.hard)
    ordered = sorted(best.values(),
                     key=lambda p: (-int(p.hard),
                                    -strength.get(p.disposition, 0),
                                    p.action_key))
    return Slate(kind="do_not_try", items=ordered)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # A TRY slate renders without the negative-only fields.
    try_item = Proposal("swap_filling", "estimator=hgb",
                        mechanism="gradient boosting fits the tabular shape",
                        support=0.7, confidence=0.8,
                        reasons=("won on 3 similar tasks",),
                        falsification_test="5-fold CV vs the incumbent")
    rendered = try_item.to_dict()
    check("try_item_renders_without_negative_fields",
          "disposition" not in rendered and rendered["mechanism"]
          and rendered["falsification_test"],
          "a positive proposal carries its mechanism and falsification test and "
          "does not show the negative-only disposition/reconsider fields")

    # An unknown slate kind is refused.
    refused = False
    try:
        Slate(kind="whatever")
    except ValueError:
        refused = True
    check("unknown_slate_kind_is_refused",
          refused, "constructing a slate with a kind outside the typed set "
          "raises rather than silently accepting an untyped bucket")

    # A negative item keeps its disposition and reconsider condition.
    neg = Proposal("swap_filling", "target_encoding=global",
                   reasons_against=("split not yet verified",),
                   disposition="not_now",
                   reconsider_when="temporal split proven leakage-free")
    neg_slate = Slate(kind="do_not_try", items=[neg])
    neg_rendered = neg_slate.to_dict()["items"][0]
    check("negative_item_carries_reconsider_condition_not_a_blacklist",
          neg_rendered["disposition"] == "not_now"
          and "leakage-free" in neg_rendered["reconsider_when"]
          and not neg_rendered["hard"],
          "a DO_NOT_TRY item states WHY (not_now) and the exact condition that "
          "brings it back — it is a soft, reversible objection, not a permanent "
          "blacklist")

    # A bad negative disposition is refused.
    bad_neg = False
    try:
        Slate(kind="do_not_try",
              items=[Proposal("x", "y", disposition="forbidden")])
    except ValueError:
        bad_neg = True
    check("bad_negative_disposition_is_refused",
          bad_neg, "a negative item with a disposition outside the typed set "
          "is refused, so the four distinct lifetimes stay legible")

    # merge_negative keeps the strongest objection and unions reasons.
    a = Slate("do_not_try", [Proposal("add_node", "n1", disposition="not_now",
                                      reasons_against=("premature",),
                                      reconsider_when="baseline exists")])
    b = Slate("do_not_try", [Proposal("add_node", "n1", disposition="invalid",
                                      hard=True,
                                      reasons_against=("violates leakage gate",))])
    merged = merge_negative(a, b)
    item = merged.items[0]
    check("merge_negative_keeps_strongest_objection_and_unions_reasons",
          len(merged.items) == 1 and item.hard and item.disposition == "invalid"
          and "violates leakage gate" in item.reasons_against
          and "premature" in item.reasons_against,
          "folding a soft not_now and a hard invalid objection to the same move "
          "keeps the hard invalid one and unions both reasons — the council's "
          "veto dominates the planner's mild caution")

    # A slate set renders with the one honest rule at the top.
    sset = slate_set_to_dict({"try": Slate("try", [try_item]),
                              "do_not_try": neg_slate})
    check("slate_set_states_the_ordering_rule_once",
          "the fold oracle decides" in sset["the_rule"]
          and set(sset["slates"]) == {"try", "do_not_try"},
          "a full decision renders its TRY and DO_NOT_TRY slates under one "
          "header stating it orders and the oracle decides")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "decision_slates_self_test", "tests": results,
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
