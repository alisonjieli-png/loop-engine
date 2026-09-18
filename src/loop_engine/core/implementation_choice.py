"""The model-versus-not decision for one operation, recorded with its evidence.

Every operation that could be done by a deterministic resolver, a small
specialist, or a service model gets one typed decision: the candidates, the
evidence that ranked them (verified rates and mean costs from the operation
cost ledger when it has them), the choice, and the reason. The decision is
a record so a later pass can learn from it; it grants nothing.

The default policy prefers the cheapest candidate whose verified rate meets
the threshold, and falls back in order deterministic resolver, small
specialist, service model when no evidence exists. A text conformance
escalation is the first caller: the deterministic pass failed to reach
confidence, so the decision names the model as the next implementation and
records why.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

CANDIDATE_KINDS = ("deterministic_resolver", "small_specialist", "service_model")
DECISION_RECORD_TYPE = "implementation_decision/v1"
JUDGE_KINDS = ("policy", "specialist", "model")


class ImplementationChoiceError(ValueError):
    """A candidate, policy, or decision is invalid."""


@dataclass(frozen=True)
class ImplementationCandidate:
    """One way to perform the operation, with what is known about it."""

    implementation_id: str
    kind: str
    available: bool = True
    verified_rate: "float | None" = None
    mean_total_ms: "float | None" = None
    mean_model_calls: "float | None" = None
    samples: int = 0

    def __post_init__(self):
        if not self.implementation_id:
            raise ImplementationChoiceError("a candidate names its implementation")
        if self.kind not in CANDIDATE_KINDS:
            raise ImplementationChoiceError(f"kind must be one of {CANDIDATE_KINDS}")
        if self.verified_rate is not None and not 0.0 <= self.verified_rate <= 1.0:
            raise ImplementationChoiceError("verified_rate lies in [0, 1]")
        if type(self.samples) is not int or self.samples < 0:
            raise ImplementationChoiceError("samples is a non-negative integer")

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True)
class ImplementationPolicy:
    """How candidates are ranked when evidence exists and when it does not."""

    minimum_verified_rate: float = 0.8
    minimum_samples: int = 3
    fallback_order: tuple[str, ...] = CANDIDATE_KINDS
    version: str = "1.0.0"

    def __post_init__(self):
        if not 0.0 <= self.minimum_verified_rate <= 1.0:
            raise ImplementationChoiceError("minimum_verified_rate lies in [0, 1]")
        if type(self.minimum_samples) is not int or self.minimum_samples < 1:
            raise ImplementationChoiceError("minimum_samples is a positive integer")
        order = tuple(self.fallback_order)
        if sorted(order) != sorted(CANDIDATE_KINDS):
            raise ImplementationChoiceError("fallback_order names every candidate kind once")
        object.__setattr__(self, "fallback_order", order)


@dataclass(frozen=True)
class ImplementationDecision:
    """The recorded choice for one operation."""

    operation_id: str
    candidates: tuple[ImplementationCandidate, ...]
    chosen_id: str
    reason: str
    judge_kind: str = JUDGE_KINDS[0]
    evidence_refs: tuple[str, ...] = ()
    policy_version: str = ""

    def __post_init__(self):
        candidates = tuple(self.candidates)
        if not candidates or any(not isinstance(item, ImplementationCandidate) for item in candidates):
            raise ImplementationChoiceError("a decision lists typed candidates")
        if self.chosen_id not in {item.implementation_id for item in candidates}:
            raise ImplementationChoiceError("the chosen implementation is one of the candidates")
        if self.judge_kind not in JUDGE_KINDS:
            raise ImplementationChoiceError(f"judge_kind must be one of {JUDGE_KINDS}")
        if not self.reason.strip():
            raise ImplementationChoiceError("a decision names its reason")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    @property
    def chosen(self) -> ImplementationCandidate:
        return next(item for item in self.candidates if item.implementation_id == self.chosen_id)

    def to_dict(self) -> dict:
        body = {"record_type": DECISION_RECORD_TYPE, "operation_id": self.operation_id,
                "candidates": [item.to_dict() for item in self.candidates], "chosen_id": self.chosen_id,
                "chosen_kind": self.chosen.kind, "reason": self.reason, "judge_kind": self.judge_kind,
                "evidence_refs": list(self.evidence_refs), "policy_version": self.policy_version}
        body["content_digest"] = hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return body


def candidates_from_ledger(operation_id: str, declared: tuple[ImplementationCandidate, ...],
                           ledger) -> tuple[ImplementationCandidate, ...]:
    """Fill each declared candidate with the ledger's verified rate and mean cost when present."""
    by_id = {item.implementation_id: item for item in ledger.implementations(operation_id)} if ledger else {}
    filled = []
    for candidate in declared:
        cost = by_id.get(candidate.implementation_id)
        if cost is None or cost.records == 0:
            filled.append(candidate)
            continue
        filled.append(ImplementationCandidate(
            candidate.implementation_id, candidate.kind, candidate.available,
            cost.verified / cost.records, cost.mean_total_ms, cost.mean_model_calls, cost.records))
    return tuple(filled)


def choose_implementation(operation_id: str, candidates, *, policy: ImplementationPolicy | None = None,
                          ledger=None, evidence_refs: tuple[str, ...] = ()) -> ImplementationDecision:
    """Pick the cheapest evidenced candidate that meets the verified rate, else fall back in order."""
    policy = policy or ImplementationPolicy()
    filled = candidates_from_ledger(operation_id, tuple(candidates), ledger)
    if not filled:
        raise ImplementationChoiceError("an operation needs at least one candidate")
    available = [item for item in filled if item.available]
    if not available:
        raise ImplementationChoiceError("no candidate is available")
    evidenced = [item for item in available
                 if item.samples >= policy.minimum_samples and item.verified_rate is not None
                 and item.verified_rate >= policy.minimum_verified_rate and item.mean_total_ms is not None]
    if evidenced:
        best = min(evidenced, key=lambda item: (item.mean_total_ms, item.mean_model_calls or 0.0,
                                                item.implementation_id))
        return ImplementationDecision(
            operation_id, filled, best.implementation_id,
            f"{best.implementation_id} has verified rate {best.verified_rate:.2f} over {best.samples} "
            f"samples and the lowest mean time {best.mean_total_ms:.0f} ms", JUDGE_KINDS[0],
            evidence_refs, policy.version)
    rank = {kind: index for index, kind in enumerate(policy.fallback_order)}
    fallback = min(available, key=lambda item: (rank[item.kind], item.implementation_id))
    return ImplementationDecision(
        operation_id, filled, fallback.implementation_id,
        f"no candidate has {policy.minimum_samples} verified samples at rate {policy.minimum_verified_rate:.2f}; "
        f"fallback order chose {fallback.kind}", JUDGE_KINDS[0], evidence_refs, policy.version)


def decision_for_escalation(operation_id: str, deterministic_id: str, model_id: str,
                            confidence: float, threshold: float) -> ImplementationDecision:
    """The decision a low-confidence deterministic result produces: the model is next."""
    deterministic = ImplementationCandidate(deterministic_id, CANDIDATE_KINDS[0], True)
    model = ImplementationCandidate(model_id, CANDIDATE_KINDS[2], True)
    return ImplementationDecision(
        operation_id, (deterministic, model), model_id,
        f"{deterministic_id} reached confidence {confidence:.2f}, below the escalation threshold "
        f"{threshold:.2f}; the service model is the next implementation", JUDGE_KINDS[0])


def self_test() -> dict:
    """Evidence picks the cheapest verified candidate; without evidence the fallback order decides."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except ImplementationChoiceError:
            return True
        return False

    from .operation_cost_records import OperationCostLedger, OperationCostRecord
    ledger = OperationCostLedger()
    for run in range(4):
        ledger.add(OperationCostRecord("conform.name", "resolver:text_conformance", f"run-{run}", "verified",
                                       (("setup", 1), ("execution", 5), ("verification", 2), ("recovery", 0)),
                                       model_calls=0))
        ledger.add(OperationCostRecord("conform.name", "model:cloud", f"run-{run}", "verified",
                                       (("setup", 50), ("execution", 4000), ("verification", 200), ("recovery", 0)),
                                       model_calls=2, input_tokens=1800))
    declared = (ImplementationCandidate("resolver:text_conformance", "deterministic_resolver"),
                ImplementationCandidate("model:cloud", "service_model"))
    decision = choose_implementation("conform.name", declared, ledger=ledger, evidence_refs=("ledger:conform.name",))
    check("with_evidence_the_cheapest_verified_candidate_wins",
          decision.chosen_id == "resolver:text_conformance" and decision.chosen.verified_rate == 1.0
          and decision.chosen.samples == 4 and "lowest mean time" in decision.reason
          and decision.to_dict()["chosen_kind"] == "deterministic_resolver"
          and decision.evidence_refs == ("ledger:conform.name",))
    bare = choose_implementation("conform.name", declared)
    check("without_evidence_the_fallback_order_decides_and_says_so",
          bare.chosen_id == "resolver:text_conformance" and "fallback order" in bare.reason
          and choose_implementation("conform.name", declared,
                                    policy=ImplementationPolicy(fallback_order=("service_model", "small_specialist",
                                                                                "deterministic_resolver"))).chosen_id
          == "model:cloud")
    failing = OperationCostLedger()
    for run in range(4):
        failing.add(OperationCostRecord("conform.name", "resolver:text_conformance", f"run-{run}",
                                        "verified" if run == 0 else "failed",
                                        (("setup", 1), ("execution", 5), ("verification", 2), ("recovery", 0))))
        failing.add(OperationCostRecord("conform.name", "model:cloud", f"run-{run}", "verified",
                                        (("setup", 50), ("execution", 4000), ("verification", 200), ("recovery", 0)),
                                        model_calls=2))
    low_rate = choose_implementation("conform.name", declared, ledger=failing)
    check("a_candidate_below_the_verified_rate_is_passed_over_for_an_evidenced_one",
          low_rate.chosen_id == "model:cloud"
          and next(item for item in low_rate.candidates
                   if item.implementation_id == "resolver:text_conformance").verified_rate == 0.25
          and next(item for item in low_rate.candidates
                   if item.implementation_id == "resolver:text_conformance").mean_total_ms == 8.0)
    unavailable = (ImplementationCandidate("resolver:text_conformance", "deterministic_resolver", available=False),
                   ImplementationCandidate("model:cloud", "service_model"))
    check("unavailable_candidates_are_never_chosen_and_empty_sets_are_refused",
          choose_implementation("conform.name", unavailable).chosen_id == "model:cloud"
          and refuses(lambda: choose_implementation("conform.name", ()))
          and refuses(lambda: choose_implementation("conform.name", (
              ImplementationCandidate("x", "service_model", available=False),))))
    escalation = decision_for_escalation("conform.name", "resolver:text_conformance", "model:cloud", 0.35, 0.6)
    check("an_escalation_records_the_model_as_the_next_implementation_with_the_confidence",
          escalation.chosen_id == "model:cloud" and "0.35" in escalation.reason and "0.60" in escalation.reason
          and escalation.judge_kind == "policy")
    check("invalid_candidates_policies_and_decisions_are_refused",
          refuses(lambda: ImplementationCandidate("", "service_model"))
          and refuses(lambda: ImplementationCandidate("x", "oracle"))
          and refuses(lambda: ImplementationCandidate("x", "service_model", verified_rate=2.0))
          and refuses(lambda: ImplementationPolicy(minimum_verified_rate=1.5))
          and refuses(lambda: ImplementationPolicy(fallback_order=("service_model",)))
          and refuses(lambda: ImplementationDecision("op", declared, "missing", "r"))
          and refuses(lambda: ImplementationDecision("op", declared, "model:cloud", ""))
          and refuses(lambda: ImplementationDecision("op", declared, "model:cloud", "r", judge_kind="oracle")))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "implementation_choice_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
