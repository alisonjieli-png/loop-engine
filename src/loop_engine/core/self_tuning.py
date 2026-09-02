"""Self-tuning: choose a run setting from recorded evidence, with sprouts.

Architectural role: the first consumer of the prompt experiment records. A
run setting that has more than one admitted variant (today: the context
budget policy) is chosen per task region from what earlier runs recorded,
not from a constant. The selector is deterministic for a given seed, region,
and salt, prefers the variant with the best recorded outcome once enough
observations exist, and otherwise explores: with the declared rate it picks a
non-incumbent variant on purpose (a "random sprout") so the evidence keeps
growing. Every choice is a passive ``TuningDecision`` that names the policy,
the seed, the evidence counts per variant, and why the variant was chosen.
Nothing here executes; the solve path reads the decision and records it.

Owns:
    - ExplorationPolicy: rate, seed, and the minimum evidence before
      exploitation.
    - VariantEvidence and TuningDecision: passive records.
    - CONTEXT_BUDGET_VARIANTS: the admitted context budget variants.
    - choose_context_budget(): the deterministic selector.

Does not own: the experiment records (core.prompt_experiment), the budget
policy itself (core.context_budget), or where the decision is applied
(code_nodes.solve_runtime).
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from .context_budget import ContextBudgetPolicy

TUNING_DECISION_SCHEMA_VERSION = "tuning_decision/v1"

#: The admitted context budget variants. The first is the incumbent default.
CONTEXT_BUDGET_VARIANTS = (
    ContextBudgetPolicy(),
    ContextBudgetPolicy(
        policy_id="adaptive_practitioner.context_budget.tight",
        version="1.1.0", text_head_bytes=3_000, text_tail_bytes=600,
        command_output_head_bytes=1_200, command_output_tail_bytes=1_200,
        list_total_bytes=12_000, keep_latest_attempts=2,
        keep_latest_inspections=1),
)


class SelfTuningError(ValueError):
    """A tuning policy, evidence record, or decision was invalid."""


def _variant_key(policy: ContextBudgetPolicy) -> str:
    return f"{policy.policy_id}@{policy.version}"


@dataclass(frozen=True)
class ExplorationPolicy:
    """How often to try a non-incumbent variant, and on what seed."""

    policy_id: str = "self_tuning.epsilon_sprout"
    version: str = "1.0.0"
    exploration_rate: float = 0.1
    seed: int = 20260901
    minimum_observations: int = 5

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.version.strip():
            raise SelfTuningError("exploration policy identity is required")
        if not (0.0 <= float(self.exploration_rate) <= 1.0):
            raise SelfTuningError("exploration_rate must be within [0, 1]")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise SelfTuningError("seed must be an integer")
        if (isinstance(self.minimum_observations, bool)
                or not isinstance(self.minimum_observations, int)
                or self.minimum_observations < 1):
            raise SelfTuningError("minimum_observations must be positive")

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "version": self.version,
                "exploration_rate": self.exploration_rate, "seed": self.seed,
                "minimum_observations": self.minimum_observations}


@dataclass(frozen=True)
class VariantEvidence:
    """What the records say about one variant in one task region."""

    variant_key: str
    calls: int
    ok_calls: int
    input_tokens_total: int
    calls_with_tokens: int

    @property
    def ok_rate(self) -> "float | None":
        return round(self.ok_calls / self.calls, 4) if self.calls else None

    @property
    def mean_input_tokens(self) -> "float | None":
        if not self.calls_with_tokens:
            return None
        return round(self.input_tokens_total / self.calls_with_tokens, 1)

    def to_dict(self) -> dict:
        return {"variant_key": self.variant_key, "calls": self.calls,
                "ok_calls": self.ok_calls, "ok_rate": self.ok_rate,
                "mean_input_tokens": self.mean_input_tokens}


@dataclass(frozen=True)
class TuningDecision:
    """One recorded choice of a variant for one region."""

    setting: str
    region_ref: str
    chosen_variant_key: str
    incumbent_variant_key: str
    explored: bool
    reason: str
    policy: ExplorationPolicy
    draw: float
    evidence: tuple
    advisory: bool = False
    record_type: str = TUNING_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != TUNING_DECISION_SCHEMA_VERSION:
            raise SelfTuningError("unsupported tuning decision schema")
        for name in ("setting", "region_ref", "chosen_variant_key",
                     "incumbent_variant_key", "reason"):
            if not str(getattr(self, name)).strip():
                raise SelfTuningError(f"{name} cannot be empty")
        if not (0.0 <= float(self.draw) < 1.0):
            raise SelfTuningError("draw must be within [0, 1)")
        if not isinstance(self.policy, ExplorationPolicy):
            raise SelfTuningError("policy must be an ExplorationPolicy")
        object.__setattr__(self, "evidence", tuple(self.evidence))

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type, "setting": self.setting,
            "region_ref": self.region_ref,
            "chosen_variant_key": self.chosen_variant_key,
            "incumbent_variant_key": self.incumbent_variant_key,
            "explored": self.explored, "reason": self.reason,
            "policy": self.policy.to_dict(), "draw": self.draw,
            "evidence": [item.to_dict() for item in self.evidence],
            "advisory": self.advisory,
        }


def variant_evidence(records, variants, *, region_ref: str) -> tuple:
    """Aggregate prompt experiment records per variant for one region."""
    keys = [_variant_key(variant) for variant in variants]
    counts = {key: {"calls": 0, "ok": 0, "tokens": 0, "with_tokens": 0}
              for key in keys}
    for record in records:
        if getattr(record, "task_region_ref", None) != region_ref:
            continue
        key = (f"{getattr(record, 'context_policy_id', '')}"
               f"@{getattr(record, 'context_policy_version', '')}")
        if key not in counts:
            continue
        group = counts[key]
        group["calls"] += 1
        group["ok"] += 1 if getattr(record, "ok", False) else 0
        tokens = getattr(record, "input_tokens", None)
        if isinstance(tokens, int):
            group["tokens"] += tokens
            group["with_tokens"] += 1
    return tuple(VariantEvidence(key, g["calls"], g["ok"], g["tokens"],
                                 g["with_tokens"])
                 for key, g in counts.items())


def _draw(policy: ExplorationPolicy, region_ref: str, salt: str) -> float:
    material = json.dumps({"seed": policy.seed, "region": region_ref,
                           "salt": salt}, sort_keys=True)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16)).random()


def choose_context_budget(records, *, region_ref: str, salt: str,
                          policy: "ExplorationPolicy | None" = None,
                          variants=CONTEXT_BUDGET_VARIANTS) -> tuple:
    """Return (chosen ContextBudgetPolicy, TuningDecision).

    Exploit the best-observed variant once every variant has at least
    ``minimum_observations`` recorded calls in this region, ranked by ok rate
    then by lower mean input tokens; otherwise keep the incumbent. Before
    exploiting, a draw below the exploration rate selects a non-incumbent
    variant deterministically from the seed, region, and salt.
    """
    policy = policy or ExplorationPolicy()
    variants = tuple(variants)
    if not variants:
        raise SelfTuningError("at least one variant is required")
    by_key = {_variant_key(variant): variant for variant in variants}
    incumbent = _variant_key(variants[0])
    evidence = variant_evidence(records, variants, region_ref=region_ref)
    draw = _draw(policy, region_ref, salt)
    if len(variants) > 1 and draw < policy.exploration_rate:
        others = [key for key in by_key if key != incumbent]
        chosen = others[int(draw / max(policy.exploration_rate, 1e-9)
                            * len(others)) % len(others)]
        reason = (f"exploration draw {draw:.4f} below rate "
                  f"{policy.exploration_rate}; trying a non-incumbent "
                  "variant on purpose")
        return by_key[chosen], TuningDecision(
            "context_budget", region_ref, chosen, incumbent, True, reason,
            policy, draw, evidence)
    observed = {item.variant_key: item for item in evidence}
    if all(observed[key].calls >= policy.minimum_observations for key in by_key):
        ranked = sorted(
            by_key, key=lambda key: (
                -(observed[key].ok_rate or 0.0),
                observed[key].mean_input_tokens or float("inf")))
        chosen = ranked[0]
        reason = (f"every variant has at least {policy.minimum_observations} "
                  f"recorded calls in this region; {chosen} has the best ok "
                  "rate, then the lowest mean input tokens")
        return by_key[chosen], TuningDecision(
            "context_budget", region_ref, chosen, incumbent, False, reason,
            policy, draw, evidence)
    thin = [key for key in by_key
            if observed[key].calls < policy.minimum_observations]
    reason = (f"insufficient evidence for {thin} (fewer than "
              f"{policy.minimum_observations} recorded calls); keeping the "
              "incumbent")
    return by_key[incumbent], TuningDecision(
        "context_budget", region_ref, incumbent, incumbent, False, reason,
        policy, draw, evidence)


def self_test() -> dict:
    """Prove determinism, exploitation on evidence, and honest thin cases."""
    from .prompt_experiment import PromptExperimentRecord

    def record(region, policy, ok, tokens, index):
        return PromptExperimentRecord(
            f"e{index}", "run", region, "act", 1, "a", "", policy.policy_id,
            policy.version, "", "p", "m", "r", 1000, tokens, 10, ok,
            "" if ok else "provider_failed", "accept")

    default, tight = CONTEXT_BUDGET_VARIANTS
    region = "region.test"
    thin = [record(region, default, True, 30000, i) for i in range(2)]
    rich = ([record(region, default, True, 30000, i) for i in range(6)]
            + [record(region, tight, True, 18000, 10 + i) for i in range(6)])
    exploit_policy = ExplorationPolicy(exploration_rate=0.0)
    chosen_thin, decision_thin = choose_context_budget(
        thin, region_ref=region, salt="s1", policy=exploit_policy)
    chosen_rich, decision_rich = choose_context_budget(
        rich, region_ref=region, salt="s1", policy=exploit_policy)
    again, decision_again = choose_context_budget(
        rich, region_ref=region, salt="s1", policy=exploit_policy)
    always = ExplorationPolicy(exploration_rate=1.0)
    chosen_explore, decision_explore = choose_context_budget(
        rich, region_ref=region, salt="s2", policy=always)
    draws = {choose_context_budget(rich, region_ref=region, salt=f"s{i}")[1].draw
             for i in range(5)}
    rejected = 0
    for bad in (
            lambda: ExplorationPolicy(exploration_rate=1.5),
            lambda: ExplorationPolicy(minimum_observations=0),
            lambda: choose_context_budget([], region_ref=region, salt="x",
                                          variants=()),
    ):
        try:
            bad()
        except SelfTuningError:
            rejected += 1
    tests = [{
        "test": "thin_evidence_keeps_the_incumbent_and_says_why",
        "passed": (chosen_thin is default and not decision_thin.explored
                   and "insufficient evidence" in decision_thin.reason
                   and decision_thin.evidence[0].calls == 2
                   and decision_thin.evidence[1].calls == 0),
        "detail": decision_thin.reason[:100],
    }, {
        "test": "enough_evidence_exploits_the_variant_with_equal_ok_rate_and_fewer_tokens",
        "passed": (chosen_rich is tight and not decision_rich.explored
                   and decision_rich.evidence[1].mean_input_tokens == 18000.0),
        "detail": decision_rich.chosen_variant_key,
    }, {
        "test": "selection_is_deterministic_for_seed_region_and_salt",
        "passed": (again is chosen_rich
                   and decision_again.draw == decision_rich.draw
                   and len(draws) == 5),
        "detail": f"draw={decision_rich.draw:.4f}",
    }, {
        "test": "exploration_rate_one_always_sprouts_a_non_incumbent",
        "passed": (chosen_explore is tight and decision_explore.explored
                   and decision_explore.to_dict()["explored"] is True),
        "detail": decision_explore.reason[:80],
    }, {
        "test": "invalid_policies_and_empty_variants_fail_closed",
        "passed": rejected == 3,
        "detail": f"{rejected}/3 rejected",
    }]
    return {"module": "core.self_tuning",
            "passed": all(item["passed"] for item in tests), "tests": tests}
