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

The answer here is a ladder, not a pick. A stage is given an advisory ordered
list to consider. A route that starts too low can still produce a wrong answer
that passes a weak verifier, so an observed success share never authorizes
routing, escalation, or acceptance by itself.

Evidence comes from prior stages of the same shape and what became of them.
Until each route has enough decided outcomes, the recommendation is `unproven`
and the caller's own default stands. Unknown outcomes remain visible and do not
make one known success look like a body of evidence. These raw rows are not
deduplicated independent samples, and this module makes no IID, calibration,
causal, or statistical-qualification claim.

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
import math
from collections.abc import Mapping
from dataclasses import dataclass, field

MODEL_LADDER_RECORD_TYPE = "model_ladder/v1"

#: What a stage might actually need. Open: a capability nobody listed is
#: recorded under the name a caller gives it, because the unlisted ones are
#: where the next real distinction comes from.
CAPABILITY_CLASSES = (
    "cheap_fast", "general", "strong_reasoning", "long_context",
    "vision", "code", "structured_output",
)

UNPROVEN = "unproven"
BOOTSTRAP_ADVISORY = "bootstrap_advisory_prior_stage_outcomes"


class ModelDemandEvidenceError(ValueError):
    """Model-demand evidence or its bootstrap policy is malformed."""


@dataclass(frozen=True)
class ModelLadderEvidencePolicy:
    """Named bootstrap judgment for advisory ordering only.

    The thresholds are not a confidence bound, calibration result, or
    qualification rule. They prevent thin per-route evidence from looking
    stronger merely because other routes or unknown outcomes add rows.
    """

    policy_id: str = "model_ladder.bootstrap_advisory"
    version: str = "1.0.0"
    minimum_decided_outcomes_per_route: int = 12
    minimum_success_share: float = 0.7

    def __post_init__(self) -> None:
        if (not isinstance(self.policy_id, str)
                or not self.policy_id.strip()
                or self.policy_id != self.policy_id.strip()
                or not isinstance(self.version, str)
                or not self.version.strip()
                or self.version != self.version.strip()):
            raise ModelDemandEvidenceError(
                "model ladder policy identity must be trimmed text")
        minimum = self.minimum_decided_outcomes_per_route
        if (isinstance(minimum, bool) or not isinstance(minimum, int)
                or minimum < 1):
            raise ModelDemandEvidenceError(
                "minimum decided outcomes per route must be positive")
        share = self.minimum_success_share
        if (isinstance(share, bool) or not isinstance(share, (int, float))
                or not math.isfinite(float(share))
                or not 0.0 <= float(share) <= 1.0):
            raise ModelDemandEvidenceError(
                "minimum success share must be finite and between zero and one")
        object.__setattr__(self, "minimum_success_share", float(share))

    def to_dict(self) -> dict:
        return {
            "record_type": "model_ladder_evidence_policy/v1",
            "policy_id": self.policy_id,
            "version": self.version,
            "minimum_decided_outcomes_per_route":
                self.minimum_decided_outcomes_per_route,
            "minimum_success_share": self.minimum_success_share,
            "bootstrap_judgment_only": True,
            "statistically_calibrated": False,
            "grants_authority": False,
        }


DEFAULT_MODEL_LADDER_EVIDENCE_POLICY = ModelLadderEvidencePolicy()

# Private compatibility names for code that imports the historical constants.
_LEAST_EVIDENCE = (
    DEFAULT_MODEL_LADDER_EVIDENCE_POLICY.minimum_decided_outcomes_per_route)
_LEAD_SUCCESS_SHARE = (
    DEFAULT_MODEL_LADDER_EVIDENCE_POLICY.minimum_success_share)


@dataclass(frozen=True)
class RouteEvidence:
    """Raw outcome counts for one route, without an independence claim."""

    route: str
    attempts: int = 0
    helped: int = 0
    unknown: int = 0

    def __post_init__(self) -> None:
        if (not isinstance(self.route, str) or not self.route.strip()
                or self.route != self.route.strip()):
            raise ModelDemandEvidenceError(
                "route evidence needs a trimmed non-empty route")
        for name in ("attempts", "helped", "unknown"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, int)
                    or value < 0):
                raise ModelDemandEvidenceError(
                    f"route {name} must be a non-negative integer")
        if self.unknown > self.attempts or self.helped > self.decided:
            raise ModelDemandEvidenceError(
                "route outcome counts do not reconcile")

    @property
    def decided(self) -> int:
        return self.attempts - self.unknown

    @property
    def failed(self) -> int:
        return self.decided - self.helped

    @property
    def success_share(self) -> float | None:
        return (None if self.decided <= 0
                else round(self.helped / self.decided, 4))

    def bootstrap_eligible(self, policy: ModelLadderEvidencePolicy) -> bool:
        """Whether this route clears one named advisory bootstrap rule."""
        return (
            self.decided >= policy.minimum_decided_outcomes_per_route
            and self.decided > 0
            and self.helped / self.decided >= policy.minimum_success_share
        )

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "attempts": self.attempts,
            "decided": self.decided,
            "helped": self.helped,
            "failed": self.failed,
            "unknown": self.unknown,
            "success_share": self.success_share,
        }


@dataclass
class ModelLadder:
    """A bootstrap advisory route order and the raw rows behind it."""

    order: tuple[str, ...] = ()
    basis: str = UNPROVEN
    evidence: tuple[RouteEvidence, ...] = ()
    observations: int = 0
    routed_decided_outcomes: int = 0
    routed_unknown_outcomes: int = 0
    unrouted_decided_outcomes: int = 0
    unrouted_unknown_outcomes: int = 0
    policy: ModelLadderEvidencePolicy = field(
        default_factory=ModelLadderEvidencePolicy)

    @property
    def advisory(self) -> bool:
        return self.basis == BOOTSTRAP_ADVISORY and bool(self.order)

    @property
    def proven(self) -> bool:
        """Compatibility alias for an advisory order, not proof."""
        return self.advisory

    @property
    def routed_observations(self) -> int:
        return self.routed_decided_outcomes + self.routed_unknown_outcomes

    @property
    def unrouted_observations(self) -> int:
        return self.unrouted_decided_outcomes + self.unrouted_unknown_outcomes

    def to_dict(self) -> dict:
        evidence = []
        for item in self.evidence:
            evidence.append({
                **item.to_dict(),
                "bootstrap_eligible": item.route in self.order,
            })
        return {
            "record_type": MODEL_LADDER_RECORD_TYPE,
            "order": list(self.order), "basis": self.basis,
            "observations": self.observations,
            "routed_observations": self.routed_observations,
            "routed_decided_outcomes": self.routed_decided_outcomes,
            "routed_unknown_outcomes": self.routed_unknown_outcomes,
            "unrouted_observations": self.unrouted_observations,
            "unrouted_decided_outcomes": self.unrouted_decided_outcomes,
            "unrouted_unknown_outcomes": self.unrouted_unknown_outcomes,
            "evidence_status": (
                "bootstrap_advisory" if self.advisory else UNPROVEN),
            "advisory": self.advisory,
            "evidence_policy": self.policy.to_dict(),
            "evidence": evidence,
            "reading": _reading(self),
            "rows_deduplicated": False,
            "independent_samples_established": False,
            "iid_established": False,
            "calibration_established": False,
            "causal_success_established": False,
            "statistically_qualified": False,
            "automatic_routing_authorized": False,
            "automatic_escalation_authorized": False,
            "verification_authorized": False,
            "grants_authority": False,
        }


def _reading(ladder: ModelLadder) -> str:
    """What this ladder is worth, in one sentence."""
    if not ladder.observations:
        return ("no stage of this shape has been seen, so nothing is "
                "recommended and the caller's default stands")
    if not ladder.advisory:
        return (
            f"{ladder.observations} raw rows include "
            f"{ladder.routed_decided_outcomes} routed decided outcomes and "
            f"{ladder.routed_unknown_outcomes} routed unknown outcomes; no "
            "route clears the named per-route bootstrap rule, so the caller's "
            "default stands"
        )
    lead = next((item for item in ladder.evidence
                 if item.route == ladder.order[0]), None)
    share = lead.success_share if lead else None
    return (
        f"bootstrap advisory only: consider {ladder.order[0]!r} first; it "
        f"succeeded on {share} of {lead.decided} decided outcomes, with "
        f"{lead.unknown} unknown and {len(ladder.order) - 1} other "
        "bootstrap-eligible route(s); the caller retains authority"
    )


def _cost_order(values) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ModelDemandEvidenceError(
            "cost_order must be a sequence of route names")
    try:
        order = tuple(values)
    except TypeError as exc:
        raise ModelDemandEvidenceError(
            "cost_order must be a sequence of route names") from exc
    if (any(not isinstance(route, str) or not route.strip()
            or route != route.strip() for route in order)
            or len(order) != len(set(order))):
        raise ModelDemandEvidenceError(
            "cost_order needs unique trimmed non-empty route names")
    return order


def ladder_from_observations(
        observations, *, cost_order=(),
        policy: ModelLadderEvidencePolicy | None = None) -> ModelLadder:
    """Recommend an order to try routes in, or decline to.

    ``observations`` are prior stages of the same shape, each carrying the
    route used and whether it helped. ``cost_order`` lists routes cheapest
    first; where evidence is equal, the cheaper route leads, because the whole
    point is to stop paying for capability a stage does not need.
    """
    if isinstance(observations, (str, bytes, Mapping)):
        raise ModelDemandEvidenceError(
            "observations must be a sequence of stage records")
    try:
        rows = tuple(observations)
    except TypeError as exc:
        raise ModelDemandEvidenceError(
            "observations must be a sequence of stage records") from exc
    selected_policy = policy or DEFAULT_MODEL_LADDER_EVIDENCE_POLICY
    if not isinstance(selected_policy, ModelLadderEvidencePolicy):
        raise ModelDemandEvidenceError(
            "policy must be a ModelLadderEvidencePolicy")
    cost_routes = _cost_order(cost_order)

    counts: dict = {}
    unrouted_decided = 0
    unrouted_unknown = 0
    for item in rows:
        route = getattr(item, "model_route", "")
        if (not isinstance(route, str)
                or route != route.strip()):
            raise ModelDemandEvidenceError(
                "model_route must be trimmed text")
        helped = getattr(item, "helped", None)
        if helped is not None and helped is not True and helped is not False:
            raise ModelDemandEvidenceError(
                "helped must be exactly True, False, or None")
        if not route:
            if helped is None:
                unrouted_unknown += 1
            else:
                unrouted_decided += 1
            continue
        entry = counts.setdefault(route, {"attempts": 0, "helped": 0,
                                          "unknown": 0})
        entry["attempts"] += 1
        if helped is None:
            entry["unknown"] += 1
        elif helped is True:
            entry["helped"] += 1

    raw_evidence = tuple(RouteEvidence(route=route, **values)
                         for route, values in counts.items())
    cheapness = {route: index for index, route in enumerate(cost_routes)}

    def rank(item: RouteEvidence):
        eligible = item.bootstrap_eligible(selected_policy)
        exact_share = (item.helped / item.decided
                       if item.decided else -1.0)
        return (
            0 if eligible else 1,
            -exact_share,
            cheapness.get(item.route, len(cheapness)),
            item.route,
        )

    evidence = tuple(sorted(raw_evidence, key=rank))
    order = tuple(item.route for item in evidence
                  if item.bootstrap_eligible(selected_policy))
    return ModelLadder(
        order=order,
        basis=BOOTSTRAP_ADVISORY if order else UNPROVEN,
        evidence=evidence,
        observations=len(rows),
        routed_decided_outcomes=sum(item.decided for item in evidence),
        routed_unknown_outcomes=sum(item.unknown for item in evidence),
        unrouted_decided_outcomes=unrouted_decided,
        unrouted_unknown_outcomes=unrouted_unknown,
        policy=selected_policy,
    )


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    from dataclasses import dataclass as _dataclass

    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    @_dataclass
    class Row:
        model_route: str
        helped: bool | None = None

    def rows(spec):
        out = []
        for route, helped, count in spec:
            out += [Row(route, helped)] * count
        return out

    def refused(operation):
        try:
            operation()
        except (TypeError, ValueError):
            return True
        return False

    check("with no observations nothing is recommended",
          not ladder_from_observations([]).proven
          and "the caller's default stands"
          in ladder_from_observations([]).to_dict()["reading"])

    thin = ladder_from_observations(rows([("cheap", True, 4)]))
    check("a handful of observations is not a ladder",
          not thin.proven and "no route clears"
          in thin.to_dict()["reading"],
          "a ladder fitted to four rows looks like data and is a guess")

    unknown_heavy = ladder_from_observations(rows([
        ("cheap", True, 1), ("cheap", None, 11)]))
    check("one_success_and_eleven_unknowns_do_not_recommend_a_route",
          not unknown_heavy.advisory
          and unknown_heavy.evidence[0].decided == 1
          and unknown_heavy.evidence[0].unknown == 11
          and unknown_heavy.routed_decided_outcomes == 1
          and unknown_heavy.routed_unknown_outcomes == 11)

    # The case worth catching: the cheap route works on enough decided rows.
    cheap_works = ladder_from_observations(
        rows([("cheap", True, 14), ("strong", True, 12)]),
        cost_order=("cheap", "general", "strong"))
    check("a shape the cheapest route handles leads with the cheapest route",
          cheap_works.advisory and cheap_works.order[0] == "cheap",
          "this is the whole saving: stop paying for capability not needed")
    check("the more expensive route stays on the ladder as a fallback",
          "strong" in cheap_works.order)

    # And the case worth not getting wrong.
    cheap_fails = ladder_from_observations(
        rows([("cheap", False, 12), ("strong", True, 12)]),
        cost_order=("cheap", "general", "strong"))
    check("a shape the cheap route fails does not lead with it",
          cheap_fails.advisory and cheap_fails.order == ("strong",))

    thin_cheap = ladder_from_observations(
        rows([("cheap", True, 1), ("strong", True, 12)]),
        cost_order=("cheap", "strong"))
    check("one_sample_route_cannot_lead_over_sufficient_other_route_evidence",
          thin_cheap.order == ("strong",)
          and any(item.route == "cheap" and item.decided == 1
                  for item in thin_cheap.evidence))

    fragmented = ladder_from_observations([
        Row(f"route-{index}", True) for index in range(12)])
    check("many_rows_split_across_thin_routes_do_not_form_a_ladder",
          not fragmented.advisory and fragmented.routed_decided_outcomes == 12)

    boundary = ladder_from_observations(rows([("cheap", True, 12)]))
    below_boundary = ladder_from_observations(rows([("cheap", True, 11)]))
    check("minimum_decided_outcome_boundary_is_exact",
          boundary.order == ("cheap",) and not below_boundary.order)

    at_share = ladder_from_observations(rows([
        ("cheap", True, 14), ("cheap", False, 6)]))
    below_share = ladder_from_observations(rows([
        ("cheap", True, 13), ("cheap", False, 7)]))
    check("minimum_success_share_boundary_is_exact",
          at_share.order == ("cheap",) and not below_share.order
          and at_share.evidence[0].success_share == 0.7)

    tied = ladder_from_observations(
        rows([("cheap", True, 12), ("strong", True, 12)]),
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
        rows([("cheap", True, 12), ("cheap", None, 4), ("strong", True, 4)]),
        cost_order=("cheap", "strong"))
    check("unknown outcomes are excluded from the share, not counted against",
          mixed.evidence[0].success_share == 1.0
          and mixed.evidence[0].unknown == 4
          and mixed.routed_unknown_outcomes == 4)

    unrouted = ladder_from_observations([
        Row("", True), Row("", False), Row("", None),
        *rows([("cheap", True, 12)]),
    ])
    check("unrouted_decided_and_unknown_rows_are_counted_separately",
          unrouted.observations == 15
          and unrouted.routed_decided_outcomes == 12
          and unrouted.routed_unknown_outcomes == 0
          and unrouted.unrouted_decided_outcomes == 2
          and unrouted.unrouted_unknown_outcomes == 1)

    class MissingOutcome:
        model_route = "cheap"

    missing = ladder_from_observations([MissingOutcome()] * 12)
    check("missing_outcomes_remain_unknown",
          not missing.advisory
          and missing.routed_unknown_outcomes == 12
          and missing.routed_decided_outcomes == 0)

    check("truthy_non_boolean_outcome_labels_are_refused",
          all(refused(lambda value=value: ladder_from_observations(
              [Row("cheap", value)])) for value in (1, 0, "yes", [], object())))

    check("caller_cost_order_is_strict_and_cannot_invent_routes",
          refused(lambda: ladder_from_observations([], cost_order="cheap"))
          and refused(lambda: ladder_from_observations(
              [], cost_order=("cheap", "cheap")))
          and refused(lambda: ladder_from_observations(
              [], cost_order=("",)))
          and "unobserved" not in ladder_from_observations(
              rows([("cheap", True, 12)]),
              cost_order=("unobserved", "cheap")).order)

    serialized = cheap_works.to_dict()
    check("bootstrap_advisory_carries_no_statistical_or_runtime_authority",
          serialized["evidence_status"] == "bootstrap_advisory"
          and serialized["advisory"]
          and serialized["rows_deduplicated"] is False
          and serialized["independent_samples_established"] is False
          and serialized["iid_established"] is False
          and serialized["calibration_established"] is False
          and serialized["causal_success_established"] is False
          and serialized["statistically_qualified"] is False
          and serialized["automatic_routing_authorized"] is False
          and serialized["automatic_escalation_authorized"] is False
          and serialized["verification_authorized"] is False
          and serialized["grants_authority"] is False
          and "bootstrap advisory only" in serialized["reading"])

    check("every capability class is a name, not a gate",
          "vision" in CAPABILITY_CLASSES and "cheap_fast" in CAPABILITY_CLASSES)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "model_demand_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
