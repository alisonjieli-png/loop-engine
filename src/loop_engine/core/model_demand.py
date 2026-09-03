"""Which model a stage needs, answered from what worked rather than from feel.

Model choice is usually a guess dressed as a judgement. A task is called
medium, so a medium model is used, and nothing about that survives the run to
say whether it was right. Meanwhile the same orientation step runs a thousand
times across a thousand tasks and nobody notices that the cheapest route
answered it correctly every time.

Because work is broken into stages, the question can be asked per stage rather
than per task. Orienting and auditing may want the strongest model available;
writing a file from a settled contract may not. One task can use several
models, each where it earns its cost.

The answer here is a ladder, not a pick. A stage is given an ordered list to
try — cheapest first when the evidence supports it, escalating on failure —
so being wrong costs a retry rather than a wrong answer. A ladder that starts
too low degrades into a slower correct answer; one that starts too high just
overpays, silently, forever.

Evidence comes from prior stages of the same shape and what became of them.
Until there is enough of it the recommendation is `unproven` and the caller's
own default stands: a ladder fitted to four observations is a guess with
provenance, which is worse than an honest guess because it looks like data.

Nothing here selects a route. It reports what the record supports, and says
when the record supports nothing.

Owns:
    - CAPABILITY_CLASSES: what a stage might need, as an open vocabulary.
    - ModelLadder: an ordered attempt list with the evidence behind it.
    - ladder_from_observations(): the recommendation, or an honest refusal.

Does not own: routing (core.model_gateway), the choice (an LLM-led Loop), or
any authority to override an operator's explicit route.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

MODEL_LADDER_RECORD_TYPE = "model_ladder/v1"

#: What a stage might actually need. Open: a capability nobody listed is
#: recorded under the name a caller gives it, because the unlisted ones are
#: where the next real distinction comes from.
CAPABILITY_CLASSES = (
    "cheap_fast", "general", "strong_reasoning", "long_context",
    "vision", "code", "structured_output",
)

#: Observations of one shape below which no ladder is claimed. Chosen to be
#: obviously too small to fit anything to, and stated rather than buried: the
#: number is a judgement about when evidence starts, and it should be argued
#: with rather than trusted.
_LEAST_EVIDENCE = 12

#: A route must have succeeded at least this often to lead a ladder. One
#: success is an anecdote; the bar is deliberately about proportion rather
#: than count so a rarely used route is not promoted by a single good run.
_LEAD_SUCCESS_SHARE = 0.7

UNPROVEN = "unproven"


@dataclass(frozen=True)
class RouteEvidence:
    """What one route did on stages of this shape."""

    route: str
    attempts: int = 0
    helped: int = 0
    unknown: int = 0

    @property
    def success_share(self) -> "float | None":
        decided = self.attempts - self.unknown
        return None if decided <= 0 else round(self.helped / decided, 4)

    def to_dict(self) -> dict:
        return {"route": self.route, "attempts": self.attempts,
                "helped": self.helped, "unknown": self.unknown,
                "success_share": self.success_share}


@dataclass
class ModelLadder:
    """An ordered list of routes to try, and why it is in that order."""

    order: tuple[str, ...] = ()
    basis: str = UNPROVEN
    evidence: tuple[RouteEvidence, ...] = ()
    observations: int = 0

    @property
    def proven(self) -> bool:
        return self.basis != UNPROVEN and bool(self.order)

    def to_dict(self) -> dict:
        return {
            "record_type": MODEL_LADDER_RECORD_TYPE,
            "order": list(self.order), "basis": self.basis,
            "observations": self.observations,
            "evidence": [item.to_dict() for item in self.evidence],
            "reading": _reading(self),
        }


def _reading(ladder: ModelLadder) -> str:
    """What this ladder is worth, in one sentence."""
    if not ladder.observations:
        return ("no stage of this shape has been seen, so nothing is "
                "recommended and the caller's default stands")
    if not ladder.proven:
        return (f"{ladder.observations} observations of this shape is too few "
                f"to fit a ladder to; the caller's default stands")
    lead = ladder.evidence[0] if ladder.evidence else None
    share = lead.success_share if lead else None
    return (f"try {ladder.order[0]!r} first: it succeeded on {share} of "
            f"{lead.attempts} decided attempts at this shape, with "
            f"{len(ladder.order) - 1} route(s) behind it")


def ladder_from_observations(observations, *, cost_order=()) -> ModelLadder:
    """Recommend an order to try routes in, or decline to.

    ``observations`` are prior stages of the same shape, each carrying the
    route used and whether it helped. ``cost_order`` lists routes cheapest
    first; where evidence is equal, the cheaper route leads, because the whole
    point is to stop paying for capability a stage does not need.
    """
    rows = tuple(observations)
    if len(rows) < _LEAST_EVIDENCE:
        return ModelLadder(observations=len(rows))

    counts: dict = {}
    for item in rows:
        route = getattr(item, "model_route", "") or ""
        if not route:
            continue
        entry = counts.setdefault(route, {"attempts": 0, "helped": 0,
                                          "unknown": 0})
        entry["attempts"] += 1
        helped = getattr(item, "helped", None)
        if helped is None:
            entry["unknown"] += 1
        elif helped:
            entry["helped"] += 1

    evidence = tuple(RouteEvidence(route=route, **values)
                     for route, values in counts.items())
    if not evidence:
        return ModelLadder(observations=len(rows))

    cheapness = {route: index for index, route in enumerate(cost_order)}

    def rank(item: RouteEvidence):
        share = item.success_share
        # A route with no decided attempts sorts last: it has not been shown
        # to work, and putting it first would be recommending the unknown.
        return (0 if share is None else 1,
                share or 0.0,
                -cheapness.get(item.route, len(cheapness)))

    ordered = sorted(evidence, key=rank, reverse=True)
    lead = ordered[0]
    if (lead.success_share or 0.0) < _LEAD_SUCCESS_SHARE:
        return ModelLadder(observations=len(rows), evidence=tuple(ordered))

    # Where the evidence ties, prefer the cheaper route. Ties are common
    # early, and this is where the saving actually comes from.
    def final(item: RouteEvidence):
        return (-(item.success_share or 0.0),
                cheapness.get(item.route, len(cheapness)))

    final_order = sorted(ordered, key=final)
    return ModelLadder(
        order=tuple(item.route for item in final_order),
        basis="prior stages of this shape",
        evidence=tuple(final_order), observations=len(rows))


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    from dataclasses import dataclass as _dataclass

    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    @_dataclass
    class Row:
        model_route: str
        helped: "bool | None" = None

    def rows(spec):
        out = []
        for route, helped, count in spec:
            out += [Row(route, helped)] * count
        return out

    check("with no observations nothing is recommended",
          not ladder_from_observations([]).proven
          and "the caller's default stands"
          in ladder_from_observations([]).to_dict()["reading"])

    thin = ladder_from_observations(rows([("cheap", True, 4)]))
    check("a handful of observations is not a ladder",
          not thin.proven and "too few to fit a ladder"
          in thin.to_dict()["reading"],
          "a ladder fitted to four rows looks like data and is a guess")

    # The case worth catching: the cheap route works fine here.
    cheap_works = ladder_from_observations(
        rows([("cheap", True, 14), ("strong", True, 6)]),
        cost_order=("cheap", "general", "strong"))
    check("a shape the cheapest route handles leads with the cheapest route",
          cheap_works.proven and cheap_works.order[0] == "cheap",
          "this is the whole saving: stop paying for capability not needed")
    check("the more expensive route stays on the ladder as a fallback",
          "strong" in cheap_works.order)

    # And the case worth not getting wrong.
    cheap_fails = ladder_from_observations(
        rows([("cheap", False, 12), ("strong", True, 10)]),
        cost_order=("cheap", "general", "strong"))
    check("a shape the cheap route fails does not lead with it",
          cheap_fails.proven and cheap_fails.order[0] == "strong")

    tied = ladder_from_observations(
        rows([("cheap", True, 8), ("strong", True, 8)]),
        cost_order=("cheap", "strong"))
    check("when the evidence ties the cheaper route leads",
          tied.order[0] == "cheap",
          "ties are common early and are where the saving comes from")

    unresolved = ladder_from_observations(
        rows([("cheap", None, 20)]), cost_order=("cheap",))
    check("routes with no known outcome do not earn a recommendation",
          not unresolved.proven,
          "twenty attempts nobody followed up prove nothing")

    weak = ladder_from_observations(
        rows([("cheap", True, 7), ("cheap", False, 8)]),
        cost_order=("cheap",))
    check("a route that mostly fails does not lead a ladder",
          not weak.proven and weak.evidence[0].success_share < 0.5)

    mixed = ladder_from_observations(
        rows([("cheap", True, 10), ("cheap", None, 4), ("strong", True, 4)]),
        cost_order=("cheap", "strong"))
    check("unknown outcomes are excluded from the share, not counted against",
          mixed.evidence[0].success_share == 1.0
          and mixed.evidence[0].unknown == 4)

    check("every capability class is a name, not a gate",
          "vision" in CAPABILITY_CLASSES and "cheap_fast" in CAPABILITY_CLASSES)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "model_demand_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
