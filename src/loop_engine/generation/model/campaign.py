"""Generation campaigns and explicitly governed expansion.

A campaign declares the target contract, seeds, variation space,
constraints, search strategy, evaluation and verification profiles,
optional owner budgets, writeback policy, and stop conditions. The product does
not invent campaign ceilings or a search strategy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dimensions import ConditionalRule, VariationDimension
from .fragments import GenerationError, SeedArtifact

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
    maximum_artifacts: "int | None" = None
    maximum_total_bytes: "int | None" = None

    def __post_init__(self) -> None:
        if self.mode not in WRITEBACK_MODES:
            raise GenerationError(
                f"writeback mode must be one of {WRITEBACK_MODES}")
        if any(value is not None and value < 1 for value in (
                self.maximum_artifacts, self.maximum_total_bytes)):
            raise GenerationError(
                "writeback limits must be positive when provided")


@dataclass(frozen=True)
class GenerationBudget:
    """Optional owner-supplied ceilings for one generation campaign."""

    candidate_limit: "int | None" = None
    model_call_limit: "int | None" = None
    cost_limit: "float | None" = None
    time_limit_seconds: "float | None" = None
    iteration_limit: "int | None" = None

    def __post_init__(self) -> None:
        if self.candidate_limit is not None and self.candidate_limit < 1:
            raise GenerationError(
                "candidate_limit must be positive when provided")
        if any(value is not None and value < 0 for value in (
                self.model_call_limit, self.cost_limit,
                self.time_limit_seconds, self.iteration_limit)):
            raise GenerationError("provided budgets cannot be negative")


@dataclass(frozen=True)
class GenerationCampaign:
    """One bounded campaign definition."""

    campaign_id: str
    version: str
    target_artifact_kind: str
    seeds: tuple[SeedArtifact, ...] = ()
    dimensions: tuple[VariationDimension, ...] = ()
    conditional_rules: object = ()
    search_strategy: str = ""
    objectives: dict = field(default_factory=dict)
    writeback: WritebackPolicy = field(default_factory=WritebackPolicy)
    budget: GenerationBudget = field(default_factory=GenerationBudget)
    stop_conditions: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.search_strategy and self.search_strategy not in SEARCH_STRATEGIES:
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

    The campaign must explicitly select the installed exact-enumeration
    strategy. Conditional rules prune incompatible combinations.
    """
    import itertools

    if campaign.search_strategy != "exact_enumeration":
        raise GenerationError(
            "expansion requires an explicit model-selected installed strategy; "
            "this executor currently installs exact_enumeration")
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
        if (campaign.budget.candidate_limit is not None
                and len(configs) >= campaign.budget.candidate_limit):
            break
    return tuple(configs)


def self_test() -> dict:
    """Prove campaigns validate and expansion is bounded and pruned."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    open_campaign = GenerationCampaign(
        campaign_id="camp-open", version="1.0.0",
        target_artifact_kind="prompt_block")
    check("campaign_has_no_implicit_strategy_or_resource_ceiling",
          not open_campaign.search_strategy
          and open_campaign.budget.candidate_limit is None
          and open_campaign.budget.model_call_limit is None
          and open_campaign.budget.iteration_limit is None,
          "model or owner must provide strategy and optional limits")
    try:
        expand_variation_space(open_campaign)
        check("unselected_search_strategy_cannot_execute", False)
    except GenerationError:
        check("unselected_search_strategy_cannot_execute", True)

    campaign = GenerationCampaign(
        campaign_id="camp-1", version="1.0.0",
        target_artifact_kind="prompt_block",
        search_strategy="exact_enumeration",
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
        search_strategy="exact_enumeration",
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
