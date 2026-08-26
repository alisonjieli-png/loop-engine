"""Generation campaigns and the bounded expansion engine.

A campaign declares the target contract, seeds, variation space,
constraints, search strategy, evaluation and verification profiles,
budgets, writeback policy, and stop conditions. Expansion is bounded:
the full Cartesian product is never materialized unless it is small.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dimensions import ConditionalRule, VariationDimension
from .fragments import GenerationError, SeedArtifact
from .seeds import SEED_SOURCES

#: Search strategies a campaign may bind.
SEARCH_STRATEGIES = (
    "exact_enumeration", "pairwise", "stratified_sampling", "beam_search",
    "successive_halving", "evolutionary", "novelty_search",
    "ablation_search", "pareto_search", "adaptive",
)

#: Writeback modes.
WRITEBACK_MODES = ("dry_run", "shadow", "candidate", "reviewed", "active")

#: Candidate lifecycle states.
CANDIDATE_STATES = (
    "proposed", "compiled", "validated", "evaluated", "ranked",
    "reviewed", "promoted", "rejected", "revoked",
)


@dataclass(frozen=True)
class WritebackPolicy:
    """Where generated candidates may be written."""

    mode: str = "candidate"
    allowed_namespaces: tuple[str, ...] = ("candidate",)
    allowed_file_roots: tuple[str, ...] = ()
    may_write_learned: bool = False
    may_write_core: bool = False
    may_promote: bool = False
    append_only: bool = True
    maximum_artifacts: int = 1000
    maximum_total_bytes: int = 10_000_000

    def __post_init__(self) -> None:
        if self.mode not in WRITEBACK_MODES:
            raise GenerationError(
                f"writeback mode must be one of {WRITEBACK_MODES}")
        if self.maximum_artifacts < 1 or self.maximum_total_bytes < 1:
            raise GenerationError("writeback limits must be positive")


@dataclass(frozen=True)
class GenerationBudget:
    """Hard ceilings for one generation campaign."""

    candidate_limit: int = 128
    model_call_limit: int = 0
    cost_limit: float = 0.0
    time_limit_seconds: float = 300.0
    iteration_limit: int = 10

    def __post_init__(self) -> None:
        if self.candidate_limit < 1:
            raise GenerationError("candidate_limit must be positive")
        if self.model_call_limit < 0 or self.cost_limit < 0:
            raise GenerationError("budgets cannot be negative")


@dataclass(frozen=True)
class GenerationCampaign:
    """One bounded campaign definition."""

    campaign_id: str
    version: str
    target_artifact_kind: str
    seeds: tuple[SeedArtifact, ...] = ()
    dimensions: tuple[VariationDimension, ...] = ()
    conditional_rules: object = ()
    search_strategy: str = "exact_enumeration"
    objectives: dict = field(default_factory=dict)
    writeback: WritebackPolicy = field(default_factory=WritebackPolicy)
    budget: GenerationBudget = field(default_factory=GenerationBudget)
    stop_conditions: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.search_strategy not in SEARCH_STRATEGIES:
            raise GenerationError(
                f"search_strategy must be one of {SEARCH_STRATEGIES}")
        if not self.campaign_id or not self.version:
            raise GenerationError("campaign needs id and version")
        if self.writeback.may_promote:
            raise GenerationError(
                "a generation campaign may not promote its own output; "
                "promotion requires an independent governed review")


def expand_variation_space(campaign: GenerationCampaign) -> tuple[dict, ...]:
    """Expand the campaign's variation space into candidate configs.

    Bounded by the campaign budget. Conditional rules prune
    incompatible combinations deterministically.
    """
    import itertools

    axis_values = []
    for dimension in campaign.dimensions:
        axis_values.append((dimension.dimension_id, dimension.expand()))
    if not axis_values:
        return ()
    combinations = itertools.product(*(values for _, values in axis_values))
    configs = []
    for combo in combinations:
        config = dict(zip((d for d, _ in axis_values), combo))
        config = dict(config)
        config.update(campaign.context)
        pruned = False
        rules = campaign.conditional_rules
        if isinstance(rules, ConditionalRule):
            rules = (rules,)
        for rule in rules:
            if not rule.matches(config):
                continue
            for key, allowed in rule.require.items():
                if config.get(key) not in allowed:
                    pruned = True
                    break
            if not pruned:
                for key in rule.prohibit:
                    if config.get(key):
                        pruned = True
                        break
            if pruned:
                break
        if pruned:
            continue
        configs.append(config)
        if len(configs) >= campaign.budget.candidate_limit:
            break
    return tuple(configs)


def self_test() -> dict:
    """Prove campaigns validate and expansion is bounded and pruned."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    campaign = GenerationCampaign(
        campaign_id="camp-1", version="1.0.0",
        target_artifact_kind="prompt_block",
        seeds=(SeedArtifact("s1", "core_default", "prompt_block", {}),),
        dimensions=(VariationDimension(
            "reasoning", "categorical",
            values=("direct", "plan_then_execute")),
            VariationDimension("example_count", "integer_range",
                               minimum=0, maximum=1)),
        conditional_rules=(ConditionalRule(
            "high_risk", {"reasoning": "plan_then_execute"},
            require={"example_count": (1,)})),
        budget=GenerationBudget(candidate_limit=10))
    configs = expand_variation_space(campaign)
    check("variation_space_expands",
          len(configs) == 3
          and ("direct", 0) in [(c["reasoning"], c["example_count"])
                                for c in configs])
    check("conditional_rules_prune_combinations",
          all(not (c["reasoning"] == "plan_then_execute"
                   and c["example_count"] != 1) for c in configs))

    bounded = GenerationCampaign(
        campaign_id="camp-2", version="1.0.0",
        target_artifact_kind="string",
        dimensions=(VariationDimension("x", "integer_range",
                                       minimum=0, maximum=100000),),
        budget=GenerationBudget(candidate_limit=5))
    check("expansion_respects_candidate_limit",
          len(expand_variation_space(bounded)) == 5)

    try:
        GenerationCampaign(
            campaign_id="camp-3", version="1.0.0",
            target_artifact_kind="string",
            writeback=WritebackPolicy(may_promote=True))
        check("self_promotion_is_refused", False)
    except GenerationError:
        check("self_promotion_is_refused", True)

    try:
        GenerationCampaign(
            campaign_id="camp-4", version="1.0.0",
            target_artifact_kind="string",
            search_strategy="bogus")
        check("unknown_search_strategy_is_refused", False)
    except GenerationError:
        check("unknown_search_strategy_is_refused", True)
    return {"tests": results}
