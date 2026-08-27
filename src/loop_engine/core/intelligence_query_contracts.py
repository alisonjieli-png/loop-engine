"""Independent policy, strategy, profile, definition, and snapshot contracts.

These passive objects keep permission, search behavior, ranking preference,
reusable portfolio configuration, and one invocation's selected records from
collapsing into an ambiguous query object. Intelligence-role LoopNodes execute
the work that consumes them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .intelligence_layers import LAYERS

SOURCE_COLLECTIONS = ("core", "learned", "plugin")
FUNCTIONAL_DOMAINS = (
    "ask", "horizon", "readiness", "deliberation", "implementation",
    "execution", "verification", "integration", "routing",
)
SEARCH_CHANNELS = (
    "exact", "lexical", "ngram", "semantic", "graph", "historical",
)


class IntelligenceQueryContractError(ValueError):
    """One intelligence-query semantic dimension is invalid."""


def _closed(label: str, values: tuple[str, ...], allowed: tuple[str, ...]) \
        -> tuple[str, ...]:
    result = tuple(values)
    unknown = sorted(set(result) - set(allowed))
    if unknown or len(result) != len(set(result)):
        raise IntelligenceQueryContractError(
            f"{label} contains unknown or duplicate values: {unknown}")
    return result


@dataclass(frozen=True)
class IntelligenceAccessPolicy:
    """Hard visibility and materialization limits; never ranking preference."""

    allowed_layers: tuple[str, ...] = LAYERS
    allowed_collections: tuple[str, ...] = SOURCE_COLLECTIONS
    allowed_scopes: tuple[str, ...] = ("project",)
    allowed_lifecycles: tuple[str, ...] = ("active",)
    maximum_references: int = 20
    allow_body_materialization: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_layers", _closed(
            "allowed_layers", self.allowed_layers, LAYERS))
        object.__setattr__(self, "allowed_collections", _closed(
            "allowed_collections", self.allowed_collections,
            SOURCE_COLLECTIONS))
        if not self.allowed_scopes or any(not value for value
                                          in self.allowed_scopes):
            raise IntelligenceQueryContractError(
                "allowed_scopes must contain explicit non-empty scopes")
        if not self.allowed_lifecycles or any(not value for value
                                              in self.allowed_lifecycles):
            raise IntelligenceQueryContractError(
                "allowed_lifecycles must be explicit")
        if self.maximum_references < 1:
            raise IntelligenceQueryContractError(
                "maximum_references must be positive")


@dataclass(frozen=True)
class IntelligenceSeekingStrategy:
    """Search expansion and stopping behavior within an access policy."""

    strategy_id: str
    version: str = "1.0.0"
    channels: tuple[str, ...] = ("exact", "lexical")
    maximum_queries: int = 4
    maximum_expansion_depth: int = 2
    stop_when_sufficient: bool = True

    def __post_init__(self) -> None:
        if not self.strategy_id.strip() or not self.version.strip():
            raise IntelligenceQueryContractError(
                "strategy needs an ID and version")
        object.__setattr__(self, "channels", _closed(
            "channels", self.channels, SEARCH_CHANNELS))
        if self.maximum_queries < 1 or self.maximum_expansion_depth < 0:
            raise IntelligenceQueryContractError(
                "strategy budgets must be bounded")


@dataclass(frozen=True)
class IntelligenceQueryProfile:
    """Soft ranking preferences that cannot expand policy visibility."""

    profile_id: str
    version: str = "1.0.0"
    functional_domains: tuple[str, ...] = ()
    preferred_layers: tuple[str, ...] = ()
    ranking_weights: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.version.strip():
            raise IntelligenceQueryContractError(
                "query profile needs an ID and version")
        object.__setattr__(self, "functional_domains", _closed(
            "functional_domains", self.functional_domains,
            FUNCTIONAL_DOMAINS))
        object.__setattr__(self, "preferred_layers", _closed(
            "preferred_layers", self.preferred_layers, LAYERS))
        keys = [key for key, _value in self.ranking_weights]
        if len(keys) != len(set(keys)) or any(
                not key or value < 0 for key, value in self.ranking_weights):
            raise IntelligenceQueryContractError(
                "ranking weights need unique names and non-negative values")


@dataclass(frozen=True)
class IntelligencePortfolioDefinition:
    """Reusable combination of policy, strategy, and ranking profile."""

    portfolio_id: str
    version: str
    access_policy: IntelligenceAccessPolicy
    seeking_strategy: IntelligenceSeekingStrategy
    query_profile: IntelligenceQueryProfile

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip() or not self.version.strip():
            raise IntelligenceQueryContractError(
                "portfolio definition needs an ID and version")
        preferred = set(self.query_profile.preferred_layers)
        allowed = set(self.access_policy.allowed_layers)
        if not preferred <= allowed:
            raise IntelligenceQueryContractError(
                "ranking preference cannot broaden access policy")


@dataclass(frozen=True)
class IntelligencePortfolioSnapshot:
    """Exact considered, rejected, ranked, and selected records for one use."""

    portfolio_id: str
    portfolio_version: str
    query: str
    records_considered: tuple[str, ...] = ()
    records_selected: tuple[str, ...] = ()
    records_rejected: tuple[tuple[str, str], ...] = ()
    ranking: tuple[tuple[str, float], ...] = ()
    materializations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip() or not self.portfolio_version.strip():
            raise IntelligenceQueryContractError(
                "snapshot needs an exact portfolio identity")
        if not self.query.strip():
            raise IntelligenceQueryContractError("snapshot query is required")
        considered = set(self.records_considered)
        selected = set(self.records_selected)
        rejected = {record for record, _reason in self.records_rejected}
        if not selected <= considered or not rejected <= considered:
            raise IntelligenceQueryContractError(
                "selected and rejected records must have been considered")
        if selected & rejected:
            raise IntelligenceQueryContractError(
                "one record cannot be selected and rejected")


def self_test() -> dict:
    """Prove the five semantic dimensions remain independent."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    policy = IntelligenceAccessPolicy(
        allowed_layers=("context_intelligence",), maximum_references=2)
    strategy = IntelligenceSeekingStrategy(
        "core.strategy.exact_then_lexical")
    profile = IntelligenceQueryProfile(
        "core.profile.context", functional_domains=("readiness",),
        preferred_layers=("context_intelligence",))
    definition = IntelligencePortfolioDefinition(
        "core.portfolio.context", "1.0.0", policy, strategy, profile)
    check("policy_strategy_profile_are_distinct_types",
          len({type(policy), type(strategy), type(profile)}) == 3)
    check("portfolio_definition_composes_without_granting_access",
          definition.access_policy is policy
          and definition.query_profile is profile)
    try:
        IntelligencePortfolioDefinition(
            "bad", "1.0.0", policy, strategy,
            IntelligenceQueryProfile(
                "bad.profile", preferred_layers=("code_intelligence",)))
    except IntelligenceQueryContractError:
        check("preference_cannot_broaden_policy", True)
    else:
        check("preference_cannot_broaden_policy", False)
    empty = IntelligencePortfolioSnapshot(
        definition.portfolio_id, definition.version, "unseen question",
        reason="no applicable active intelligence")
    check("honest_empty_snapshot_is_valid",
          not empty.records_selected and bool(empty.reason))
    try:
        IntelligencePortfolioSnapshot(
            definition.portfolio_id, definition.version, "question",
            records_selected=("never-considered",))
    except IntelligenceQueryContractError:
        check("snapshot_cannot_select_unconsidered_record", True)
    else:
        check("snapshot_cannot_select_unconsidered_record", False)
    return {"tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests), "all_passed": all(
                item["passed"] for item in tests)}


__all__ = (
    "FUNCTIONAL_DOMAINS", "IntelligenceAccessPolicy",
    "IntelligencePortfolioDefinition", "IntelligencePortfolioSnapshot",
    "IntelligenceQueryContractError", "IntelligenceQueryProfile",
    "IntelligenceSeekingStrategy", "SEARCH_CHANNELS", "SOURCE_COLLECTIONS",
)
