"""Passive contracts for reactive Loop activation and output serving.

These objects configure the canonical ``Loop`` runtime.  They do not execute,
schedule, persist, rank, or publish work by themselves.  Candidate payloads
use exact ``LoopValueRef`` identities so storage placement stays independent
from activation, evaluation, portfolio, and emission decisions.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum



_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ReactiveContractError(ValueError):
    """A reactive policy, candidate, evaluation, or portfolio is invalid."""


class TriggerKind(str, Enum):
    EXPLICIT_REQUEST = "explicit_request"
    PUSH_EVENT = "push_event"
    SCHEDULE = "schedule"
    POLL_DUE = "poll_due"
    SPAWNED_RESULT = "spawned_result"
    INFORMATION_CHANGED = "information_changed"
    CONFIDENCE_CHANGED = "confidence_changed"
    VERIFICATION_EXPIRED = "verification_expired"
    MANUAL_REFRESH = "manual_refresh"


class PersistenceMode(str, Enum):
    EPHEMERAL = "ephemeral"
    CHECKPOINTED = "checkpointed"
    DURABLE_SERIES = "durable_series"


class InputOrdering(str, Enum):
    FIFO = "fifo"
    PRIORITY_AGING = "priority_aging"
    EARLIEST_DEADLINE = "earliest_deadline"
    WEIGHTED_FAIR = "weighted_fair"
    INFORMATION_GAIN = "information_gain"
    SEEDED_RANDOM = "seeded_random"


class ExplorationStrategy(str, Enum):
    SINGLE = "single"
    BASELINE_CHALLENGERS = "baseline_challengers"
    SEEDED_RANDOM = "seeded_random"
    SUCCESSIVE_HALVING = "successive_halving"
    UPPER_CONFIDENCE = "upper_confidence"
    THOMPSON = "thompson"
    NOVELTY = "novelty"


class OutputCardinality(str, Enum):
    SINGLE = "single"
    LIST = "list"
    STREAM = "stream"
    PORTFOLIO = "portfolio"


class OutputUpdateSemantics(str, Enum):
    IMMUTABLE = "immutable"
    APPEND = "append"
    SUPERSEDE = "supersede"
    RETRACT = "retract"


class CandidateVerdict(str, Enum):
    PROVISIONAL = "provisional"
    ELIGIBLE = "eligible"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class PortfolioView(str, Enum):
    TOP_K = "top_k"
    VERIFIED_TOP_K = "verified_top_k"
    PARETO = "pareto"
    ALL_ATTEMPTED = "all_attempted"


class MetricDirection(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class EmissionTrigger(str, Enum):
    EVERY_CANDIDATE = "every_candidate"
    VERIFIED_CANDIDATE = "verified_candidate"
    LEADER_CHANGED = "leader_changed"
    MATERIAL_IMPROVEMENT = "material_improvement"
    PARETO_ENTRY = "pareto_entry"
    RETRACTION = "retraction"
    DEADLINE = "deadline"
    PERIODIC_DIGEST = "periodic_digest"
    SUBSCRIBER_REQUEST = "subscriber_request"


def _enum(value, kind, label: str):
    try:
        return value if isinstance(value, kind) else kind(value)
    except (TypeError, ValueError) as exc:
        raise ReactiveContractError(f"{label} is not registered") from exc


def _names(label: str, values) -> tuple[str, ...]:
    normalized = tuple(values or ())
    if (any(not isinstance(item, str) or not item.strip()
            for item in normalized)
            or len(normalized) != len(set(normalized))):
        raise ReactiveContractError(
            f"{label} must contain unique non-empty strings")
    return normalized


def _identity(label: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ReactiveContractError(f"{label} is invalid")
    return value


def _digest(label: str, value: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ReactiveContractError(f"{label} must be a SHA-256 digest")
    return value


def _timestamp(label: str, value: str, *, optional: bool = False) -> str:
    if optional and not value:
        return value
    if not isinstance(value, str) or not value:
        raise ReactiveContractError(f"{label} is required")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReactiveContractError(f"{label} must use ISO-8601") from exc
    return value


def _bounded_score(label: str, value: float) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not 0.0 <= float(value) <= 1.0):
        raise ReactiveContractError(f"{label} must be between zero and one")
    return float(value)


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _jsonable(getattr(value, item.name))
                for item in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ActivationPolicy:
    """What may wake a Loop series and how trigger storms are bounded."""

    accepted_triggers: tuple[TriggerKind | str, ...] = (
        TriggerKind.EXPLICIT_REQUEST,)
    reactivation_enabled: bool = False
    debounce_seconds: float = 0.0
    cooldown_seconds: float = 0.0
    minimum_information_delta: float = 0.0
    coalesce_by_subject: bool = True

    def __post_init__(self) -> None:
        triggers = tuple(_enum(item, TriggerKind, "trigger kind")
                         for item in self.accepted_triggers)
        if not triggers or len(triggers) != len(set(triggers)):
            raise ReactiveContractError(
                "activation policy needs unique trigger kinds")
        if any(not isinstance(value, bool) for value in (
                self.reactivation_enabled, self.coalesce_by_subject)):
            raise ReactiveContractError("activation flags must be booleans")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool)
               or value < 0 for value in (
                   self.debounce_seconds, self.cooldown_seconds,
                   self.minimum_information_delta)):
            raise ReactiveContractError(
                "activation thresholds must be non-negative numbers")
        if (not self.reactivation_enabled
                and set(triggers) != {TriggerKind.EXPLICIT_REQUEST}):
            raise ReactiveContractError(
                "disabled reactivation accepts explicit requests only")
        object.__setattr__(self, "accepted_triggers", triggers)


@dataclass(frozen=True)
class AdmissionPolicy:
    """Requirements a trigger must satisfy before becoming work."""

    maximum_pending_inputs: int
    require_new_input_digest: bool = True
    require_observable_delta: bool = True
    deduplicate: bool = True

    def __post_init__(self) -> None:
        if any(not isinstance(value, bool) for value in (
                self.require_new_input_digest, self.require_observable_delta,
                self.deduplicate)):
            raise ReactiveContractError("admission flags must be booleans")
        if not self.deduplicate:
            raise ReactiveContractError(
                "reactive admission requires deduplication")
        if (not isinstance(self.maximum_pending_inputs, int)
                or isinstance(self.maximum_pending_inputs, bool)
                or self.maximum_pending_inputs < 1):
            raise ReactiveContractError(
                "maximum_pending_inputs must be a positive integer")


@dataclass(frozen=True)
class InputSchedulingPolicy:
    """How admitted inputs are ordered, separate from answer ranking."""

    ordering: InputOrdering | str = InputOrdering.FIFO
    priority_aging_per_second: float = 0.0
    random_seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "ordering", _enum(self.ordering, InputOrdering,
                                    "input ordering"))
        if (not isinstance(self.priority_aging_per_second, (int, float))
                or isinstance(self.priority_aging_per_second, bool)
                or self.priority_aging_per_second < 0):
            raise ReactiveContractError(
                "priority aging must be a non-negative number")
        if (self.ordering is InputOrdering.SEEDED_RANDOM
                and not isinstance(self.random_seed, int)):
            raise ReactiveContractError(
                "seeded random input scheduling requires an integer seed")


@dataclass(frozen=True)
class ExplorationPolicy:
    """How candidate-producing settings are varied within a hard budget."""

    strategy: ExplorationStrategy | str = ExplorationStrategy.SINGLE
    maximum_variants: int = 1
    random_seed: int | None = None
    settings_axes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "strategy", _enum(self.strategy, ExplorationStrategy,
                                    "exploration strategy"))
        if (not isinstance(self.maximum_variants, int)
                or isinstance(self.maximum_variants, bool)
                or self.maximum_variants < 1):
            raise ReactiveContractError(
                "maximum_variants must be a positive integer")
        object.__setattr__(
            self, "settings_axes", _names("settings_axes", self.settings_axes))
        if (self.strategy in {
                ExplorationStrategy.SEEDED_RANDOM,
                ExplorationStrategy.THOMPSON}
                and not isinstance(self.random_seed, int)):
            raise ReactiveContractError(
                "stochastic exploration requires an integer seed")
        if self.strategy is ExplorationStrategy.SINGLE \
                and self.maximum_variants != 1:
            raise ReactiveContractError(
                "single exploration permits exactly one variant")


@dataclass(frozen=True)
class OutputPortDefinition:
    """Typed output publication semantics for one Loop port."""

    port_id: str
    semantic_type: str
    output_contract_ref: str
    cardinality: OutputCardinality | str = OutputCardinality.SINGLE
    update_semantics: OutputUpdateSemantics | str = (
        OutputUpdateSemantics.IMMUTABLE)
    access_policy_ref: str = "core.policy.output.owner_only"

    def __post_init__(self) -> None:
        _identity("port_id", self.port_id)
        for label, value in (
                ("semantic_type", self.semantic_type),
                ("output_contract_ref", self.output_contract_ref),
                ("access_policy_ref", self.access_policy_ref)):
            if not isinstance(value, str) or not value.strip():
                raise ReactiveContractError(f"{label} is required")
        object.__setattr__(
            self, "cardinality", _enum(
                self.cardinality, OutputCardinality, "output cardinality"))
        object.__setattr__(
            self, "update_semantics", _enum(
                self.update_semantics, OutputUpdateSemantics,
                "output update semantics"))


@dataclass(frozen=True)
class RankingDimension:
    """One measurable portfolio dimension and its declared orientation."""

    name: str
    direction: MetricDirection | str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ReactiveContractError("ranking dimension needs a name")
        object.__setattr__(
            self, "direction", _enum(
                self.direction, MetricDirection, "metric direction"))
        if (not isinstance(self.weight, (int, float))
                or isinstance(self.weight, bool) or self.weight <= 0):
            raise ReactiveContractError(
                "ranking dimension weight must be positive")


@dataclass(frozen=True)
class PortfolioPolicy:
    """One versioned view over immutable candidates and evaluations."""

    policy_id: str
    version: str
    view: PortfolioView | str
    dimensions: tuple[RankingDimension, ...]
    maximum_results: int

    def __post_init__(self) -> None:
        _identity("portfolio policy ID", self.policy_id)
        if not _SEMVER.fullmatch(self.version):
            raise ReactiveContractError(
                "portfolio policy version must use MAJOR.MINOR.PATCH")
        object.__setattr__(
            self, "view", _enum(self.view, PortfolioView, "portfolio view"))
        dimensions = tuple(self.dimensions)
        if (not dimensions
                or any(not isinstance(item, RankingDimension)
                       for item in dimensions)
                or len({item.name for item in dimensions}) != len(dimensions)):
            raise ReactiveContractError(
                "portfolio dimensions must be unique typed records")
        if (not isinstance(self.maximum_results, int)
                or isinstance(self.maximum_results, bool)
                or self.maximum_results < 1):
            raise ReactiveContractError(
                "portfolio maximum_results must be positive")
        object.__setattr__(self, "dimensions", dimensions)

    @property
    def content_digest(self) -> str:
        body = {
            "policy_id": self.policy_id, "version": self.version,
            "view": self.view.value,
            "dimensions": [{"name": item.name,
                            "direction": item.direction.value,
                            "weight": item.weight}
                           for item in self.dimensions],
            "maximum_results": self.maximum_results,
        }
        encoded = json.dumps(
            body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EmissionPolicy:
    """What portfolio change is material enough to publish."""

    triggers: tuple[EmissionTrigger | str, ...] = (
        EmissionTrigger.LEADER_CHANGED,)
    minimum_score_improvement: float = 0.0
    require_verified: bool = True

    def __post_init__(self) -> None:
        triggers = tuple(_enum(item, EmissionTrigger, "emission trigger")
                         for item in self.triggers)
        if not triggers or len(triggers) != len(set(triggers)):
            raise ReactiveContractError(
                "emission policy needs unique trigger kinds")
        _bounded_score(
            "minimum_score_improvement", self.minimum_score_improvement)
        if not isinstance(self.require_verified, bool):
            raise ReactiveContractError("require_verified must be a boolean")
        object.__setattr__(self, "triggers", triggers)


@dataclass(frozen=True)
class ServingPolicy:
    """Read-only portfolio views available without waking the producer."""

    maximum_results: int
    permitted_views: tuple[PortfolioView | str, ...] = (
        PortfolioView.VERIFIED_TOP_K,)
    pull_reactivates_producer: bool = False

    def __post_init__(self) -> None:
        views = tuple(_enum(item, PortfolioView, "serving view")
                      for item in self.permitted_views)
        if not views or len(views) != len(set(views)):
            raise ReactiveContractError(
                "serving policy needs unique portfolio views")
        if (not isinstance(self.maximum_results, int)
                or isinstance(self.maximum_results, bool)
                or self.maximum_results < 1):
            raise ReactiveContractError(
                "serving maximum_results must be positive")
        if self.pull_reactivates_producer:
            raise ReactiveContractError(
                "portfolio reads cannot silently reactivate the producer")
        object.__setattr__(self, "permitted_views", views)


@dataclass(frozen=True)
class RetentionPolicy:
    """Bounded candidate and portfolio retention."""

    maximum_candidates: int
    maximum_portfolio_versions: int
    retain_attempted_candidates: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.retain_attempted_candidates, bool):
            raise ReactiveContractError(
                "retain_attempted_candidates must be a boolean")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1
               for value in (self.maximum_candidates,
                             self.maximum_portfolio_versions)):
            raise ReactiveContractError(
                "retention limits must be positive integers")


@dataclass(frozen=True)
class ReactiveLivenessPolicy:
    """Hard protections for bounded activation and feedback behavior."""

    maximum_activation_seconds: float
    maximum_zero_change_activations: int = 2
    suspend_when_idle: bool = True
    reject_unchanged_self_trigger: bool = True

    def __post_init__(self) -> None:
        if (not isinstance(self.maximum_activation_seconds, (int, float))
                or isinstance(self.maximum_activation_seconds, bool)
                or self.maximum_activation_seconds <= 0):
            raise ReactiveContractError(
                "maximum_activation_seconds must be positive")
        if (not isinstance(self.maximum_zero_change_activations, int)
                or isinstance(self.maximum_zero_change_activations, bool)
                or self.maximum_zero_change_activations < 1):
            raise ReactiveContractError(
                "zero-change activation limit must be positive")
        if any(not isinstance(value, bool) for value in (
                self.suspend_when_idle,
                self.reject_unchanged_self_trigger)):
            raise ReactiveContractError("liveness flags must be booleans")


@dataclass(frozen=True)
class ReactiveLoopProfile:
    """Complete passive reactive capability surface for one Loop definition."""

    profile_id: str
    version: str
    activation: ActivationPolicy
    admission: AdmissionPolicy
    input_scheduling: InputSchedulingPolicy
    persistence: PersistenceMode | str
    exploration: ExplorationPolicy
    output_ports: tuple[OutputPortDefinition, ...]
    portfolio: PortfolioPolicy
    emission: EmissionPolicy
    serving: ServingPolicy
    retention: RetentionPolicy
    liveness: ReactiveLivenessPolicy

    def __post_init__(self) -> None:
        _identity("reactive profile ID", self.profile_id)
        if not _SEMVER.fullmatch(self.version):
            raise ReactiveContractError(
                "reactive profile version must use MAJOR.MINOR.PATCH")
        typed = (
            (self.activation, ActivationPolicy),
            (self.admission, AdmissionPolicy),
            (self.input_scheduling, InputSchedulingPolicy),
            (self.exploration, ExplorationPolicy),
            (self.portfolio, PortfolioPolicy),
            (self.emission, EmissionPolicy),
            (self.serving, ServingPolicy),
            (self.retention, RetentionPolicy),
            (self.liveness, ReactiveLivenessPolicy),
        )
        if any(not isinstance(value, kind) for value, kind in typed):
            raise ReactiveContractError(
                "reactive profile contains an untyped policy")
        object.__setattr__(
            self, "persistence", _enum(
                self.persistence, PersistenceMode, "persistence mode"))
        ports = tuple(self.output_ports)
        if (not ports
                or any(not isinstance(port, OutputPortDefinition)
                       for port in ports)
                or len({port.port_id for port in ports}) != len(ports)):
            raise ReactiveContractError(
                "reactive profile needs unique typed output ports")
        object.__setattr__(self, "output_ports", ports)
        if (self.persistence is PersistenceMode.DURABLE_SERIES
                and not self.activation.reactivation_enabled):
            raise ReactiveContractError(
                "durable series persistence requires reactivation")

    def to_dict(self) -> dict:
        return {
            "record_type": "reactive_loop_profile/v1",
            **{item.name: _jsonable(getattr(self, item.name))
               for item in fields(self)},
        }

    @property
    def content_digest(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


__all__ = (
    "ActivationPolicy", "AdmissionPolicy", "CandidateVerdict",
    "EmissionPolicy", "EmissionTrigger", "ExplorationPolicy",
    "ExplorationStrategy", "InputOrdering", "InputSchedulingPolicy",
    "MetricDirection", "OutputCardinality", "OutputPortDefinition",
    "OutputUpdateSemantics", "PersistenceMode",
    "PortfolioPolicy", "PortfolioView", "RankingDimension",
    "ReactiveContractError", "ReactiveLivenessPolicy",
    "ReactiveLoopProfile", "RetentionPolicy", "ServingPolicy",
    "TriggerKind",
)
