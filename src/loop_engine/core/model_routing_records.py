"""Passive evidence records for model-route selection.

These immutable records keep capability, suitability, current availability,
selection input, safe outcomes, and learning candidates separate. They do not
call a provider, run work, or define another intelligence layer.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

from .intelligence_layers import LAYERS
from .model_capabilities import ModelOutputCapability
from .model_routes import LOCALITIES, PURPOSES


MODEL_ROUTING_PORTFOLIO_ID = "core.intelligence_portfolio.model_routing@1"
MODEL_ROUTING_SCHEMA_VERSION = "1.0.0"
ROLES = ("practitioner", "intelligence", "solution")
RUN_MODES = ("deterministic", "hybrid", "non_deterministic")
THINKING_POWER = ("small", "medium", "high", "max", "specialized")
RISK_LEVELS = ("low", "medium", "high", "critical")
ACTIVE_LIFECYCLES = ("reviewed", "active")
CAPABILITY_STATES = ("source_claim", "probed", "reviewed", "verified")
DECISION_STATES = ("no_model_required", "selected", "abstained")


class ModelRoutingError(ValueError):
    """A model-routing record or decision violates its typed contract."""


def _text(value: object, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise ModelRoutingError(f"{name} must be non-empty")
    if "\n" in result or "\r" in result:
        raise ModelRoutingError(f"{name} must be one line")
    return result


def _strings(values: Sequence[object], name: str, *, empty: bool = True
             ) -> tuple[str, ...]:
    result = tuple(str(value).strip() for value in values)
    if (not empty and not result) or any(not value for value in result):
        raise ModelRoutingError(f"{name} must contain non-empty values")
    if len(result) != len(set(result)):
        raise ModelRoutingError(f"{name} must not contain duplicates")
    return result


def _pairs(values: Sequence[Sequence[object]], name: str
           ) -> tuple[tuple[str, float], ...]:
    result: list[tuple[str, float]] = []
    seen: set[str] = set()
    for item in values:
        if len(item) != 2:
            raise ModelRoutingError(f"{name} entries need a name and value")
        key = _text(item[0], f"{name} name")
        value = float(item[1])
        if key in seen or not math.isfinite(value):
            raise ModelRoutingError(f"{name} needs unique finite values")
        seen.add(key)
        result.append((key, value))
    return tuple(result)


def _probability(value: float, name: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ModelRoutingError(f"{name} must be between zero and one")
    return number


def _parse_time(value: str, name: str) -> datetime:
    text = _text(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelRoutingError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_current(valid_from: str, valid_until: str, at: datetime) -> bool:
    if valid_from and at < _parse_time(valid_from, "valid_from"):
        return False
    if valid_until and at >= _parse_time(valid_until, "valid_until"):
        return False
    return True


def _validate_window(valid_from: str, valid_until: str) -> None:
    start = _parse_time(valid_from, "valid_from") if valid_from else None
    end = _parse_time(valid_until, "valid_until") if valid_until else None
    if start is not None and end is not None and end <= start:
        raise ModelRoutingError("valid_until must be later than valid_from")


def _digest_payload(value: object, *, omit: str) -> str:
    payload = asdict(value)  # type: ignore[arg-type]
    payload.pop(omit, None)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _seal(value: object, field_name: str) -> None:
    supplied = str(getattr(value, field_name)).strip()
    computed = _digest_payload(value, omit=field_name)
    if supplied and supplied != computed:
        raise ModelRoutingError(
            f"{field_name} does not match the canonical record content")
    object.__setattr__(value, field_name, computed)


def _safe_dict(value: object) -> dict:
    return asdict(value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ModelRoutingPortfolioDefinition:
    """Reusable query strategy across the four existing intelligence layers."""

    record_id: str = MODEL_ROUTING_PORTFOLIO_ID
    record_version: str = MODEL_ROUTING_SCHEMA_VERSION
    artifact_kind: str = "intelligence_portfolio_definition"
    primary_functions: tuple[str, ...] = (
        "readiness", "deliberation", "execution", "routing",
    )
    secondary_functions: tuple[str, ...] = (
        "implementation", "verification",
    )
    persistent_layers: tuple[str, ...] = LAYERS
    collections: tuple[str, ...] = ("core", "learned", "plugin")
    minimum_governance_status: str = "reviewed"
    require_scope_filter: bool = True
    require_freshness_check: bool = True
    require_counterevidence: bool = True

    def __post_init__(self) -> None:
        if self.record_id != MODEL_ROUTING_PORTFOLIO_ID:
            raise ModelRoutingError("model-routing portfolio identity is fixed")
        if tuple(self.persistent_layers) != tuple(LAYERS):
            raise ModelRoutingError(
                "model-routing intelligence must use the four existing layers")
        object.__setattr__(
            self, "primary_functions",
            _strings(self.primary_functions, "primary_functions", empty=False),
        )
        object.__setattr__(
            self, "secondary_functions",
            _strings(self.secondary_functions, "secondary_functions"),
        )
        object.__setattr__(
            self, "collections",
            _strings(self.collections, "collections", empty=False),
        )

    def to_dict(self) -> dict:
        return _safe_dict(self)


MODEL_ROUTING_PORTFOLIO = ModelRoutingPortfolioDefinition()


@dataclass(frozen=True)
class ModelCapabilityRecord:
    """Reviewed technical facts for one exact provider deployment."""

    record_id: str
    provider_id: str
    route_id: str
    exact_model_id: str
    locality: str
    supported_operators: tuple[str, ...]
    supported_response_topologies: tuple[str, ...]
    version: str = MODEL_ROUTING_SCHEMA_VERSION
    content_digest: str = ""
    catalog_collection: str = "core"
    intelligence_layer: str = "context_intelligence"
    intelligence_functions: tuple[str, ...] = (
        "readiness", "implementation", "execution", "routing",
    )
    model_revision: str = ""
    deployment_digest: str = ""
    serving_runtime: str = ""
    serving_runtime_version: str = ""
    wire_format: str = "provider_native"
    modalities: tuple[str, ...] = ("text",)
    supported_tools: tuple[str, ...] = ()
    structured_output: bool | None = None
    tool_calling: bool | None = None
    streaming: bool | None = None
    context_limit: int | None = None
    maximum_output: int | None = None
    maximum_output_source: str = ""
    reasoning_controls: tuple[str, ...] = ()
    sampling_controls: tuple[str, ...] = ()
    concurrency: int | None = None
    device_requirements: tuple[str, ...] = ()
    quantization: str = ""
    thinking_power: str = "medium"
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    source_refs: tuple[str, ...] = ()
    verification_state: str = "source_claim"
    valid_from: str = ""
    valid_until: str = ""
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("record_id", "provider_id", "route_id", "exact_model_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.locality not in LOCALITIES:
            raise ModelRoutingError(f"locality must be one of {LOCALITIES}")
        if self.intelligence_layer not in LAYERS:
            raise ModelRoutingError("capability records must use an existing layer")
        if self.catalog_collection not in ("core", "learned", "plugin"):
            raise ModelRoutingError(
                "catalog_collection must be core, learned, or plugin")
        if self.thinking_power not in THINKING_POWER:
            raise ModelRoutingError(
                f"thinking_power must be one of {THINKING_POWER}")
        if self.verification_state not in CAPABILITY_STATES:
            raise ModelRoutingError(
                f"verification_state must be one of {CAPABILITY_STATES}")
        for name in (
            "supported_operators", "supported_response_topologies",
            "intelligence_functions", "modalities", "supported_tools",
            "reasoning_controls", "sampling_controls", "device_requirements",
            "source_refs", "provenance",
        ):
            object.__setattr__(
                self, name,
                _strings(getattr(self, name), name,
                         empty=name not in (
                             "supported_operators",
                             "supported_response_topologies",
                             "modalities",
                         )),
            )
        for name in ("context_limit", "maximum_output", "concurrency"):
            number = getattr(self, name)
            if number is not None and number < 1:
                raise ModelRoutingError(f"{name} must be positive when known")
        if bool(self.maximum_output) != bool(self.maximum_output_source.strip()):
            raise ModelRoutingError(
                "maximum_output and maximum_output_source are one fact")
        if self.maximum_output is not None:
            ModelOutputCapability(
                self.maximum_output, self.maximum_output_source)
        if (self.verification_state in ("reviewed", "verified")
                and not self.source_refs):
            raise ModelRoutingError(
                "a reviewed capability needs at least one source reference")
        for name in ("input_cost_per_million", "output_cost_per_million"):
            number = getattr(self, name)
            if number is not None and (not math.isfinite(number) or number < 0):
                raise ModelRoutingError(f"{name} must be non-negative")
        _validate_window(self.valid_from, self.valid_until)
        _seal(self, "content_digest")

    def is_current(self, at: datetime) -> bool:
        return _is_current(self.valid_from, self.valid_until, at)

    def to_dict(self) -> dict:
        return _safe_dict(self)


@dataclass(frozen=True)
class ModelSuitabilityRecord:
    """Reviewed performance evidence for one bounded task population."""

    record_id: str
    route_ref: str
    task_fingerprint_selector: str
    applicable_operators: tuple[str, ...]
    applicable_response_topologies: tuple[str, ...]
    sample_size: int
    trial_count: int
    success_rate: float
    schema_validity: float
    verification_pass_rate: float
    version: str = MODEL_ROUTING_SCHEMA_VERSION
    content_digest: str = ""
    capability_record_digest: str = ""
    model_revision: str = ""
    deployment_digest: str = ""
    applicable_domains: tuple[str, ...] = ()
    applicable_profiles: tuple[str, ...] = ()
    risk_limit: str = "low"
    context_range: tuple[int, int] = (0, 0)
    output_range: tuple[int, int] = (0, 0)
    modality: str = "text"
    benchmark_population_ref: str = ""
    benchmark_version: str = ""
    environment_ref: str = ""
    evaluator_ref: str = ""
    latency_distribution: tuple[float, ...] = ()
    token_distribution: tuple[float, ...] = ()
    cost_distribution: tuple[float, ...] = ()
    retry_rate: float = 0.0
    failure_classes: tuple[str, ...] = ()
    stability: float = 0.0
    calibration: float | None = None
    human_review_rate: float = 0.0
    negative_transfer_evidence: tuple[str, ...] = ()
    counterevidence: tuple[str, ...] = ()
    confidence: float = 0.0
    lifecycle: str = "reviewed"
    review_ref: str = ""
    valid_from: str = ""
    valid_until: str = ""
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("record_id", "route_ref", "task_fingerprint_selector"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "applicable_operators", "applicable_response_topologies",
            "applicable_domains", "applicable_profiles", "failure_classes",
            "negative_transfer_evidence", "counterevidence", "provenance",
        ):
            object.__setattr__(
                self, name,
                _strings(getattr(self, name), name,
                         empty=name not in (
                             "applicable_operators",
                             "applicable_response_topologies",
                         )),
            )
        if self.sample_size < 1 or self.trial_count < self.sample_size:
            raise ModelRoutingError(
                "suitability needs a positive sample and at least as many trials")
        for name in (
            "success_rate", "schema_validity", "verification_pass_rate",
            "retry_rate", "stability", "human_review_rate", "confidence",
        ):
            object.__setattr__(
                self, name, _probability(getattr(self, name), name))
        if self.calibration is not None:
            object.__setattr__(
                self, "calibration", _probability(self.calibration, "calibration"))
        if self.risk_limit not in RISK_LEVELS:
            raise ModelRoutingError(f"risk_limit must be one of {RISK_LEVELS}")
        for name in ("context_range", "output_range"):
            values = tuple(int(value) for value in getattr(self, name))
            if len(values) != 2 or min(values) < 0 or values[1] < values[0]:
                raise ModelRoutingError(f"{name} must be an inclusive range")
            object.__setattr__(self, name, values)
        for name in (
            "latency_distribution", "token_distribution", "cost_distribution",
        ):
            values = tuple(float(value) for value in getattr(self, name))
            if any(not math.isfinite(value) or value < 0 for value in values):
                raise ModelRoutingError(f"{name} must be non-negative and finite")
            object.__setattr__(self, name, values)
        if self.lifecycle not in (*ACTIVE_LIFECYCLES, "candidate", "rejected"):
            raise ModelRoutingError("unknown suitability lifecycle")
        if (self.lifecycle in ACTIVE_LIFECYCLES
                and (not self.benchmark_population_ref.strip()
                     or not self.evaluator_ref.strip()
                     or not self.review_ref.strip()
                     or not self.provenance)):
            raise ModelRoutingError(
                "reviewed suitability needs population, evaluator, review, "
                "and provenance")
        if (self.task_fingerprint_selector.endswith("*")
                and (not self.applicable_domains
                     or not self.negative_transfer_evidence)):
            raise ModelRoutingError(
                "a broad task selector needs domain scope and negative-transfer evidence")
        _validate_window(self.valid_from, self.valid_until)
        _seal(self, "content_digest")

    def applicability(
        self,
        request: "ModelSelectionRequest",
        capability: ModelCapabilityRecord,
        at: datetime,
    ) -> tuple[bool, tuple[str, ...]]:
        """Return explicit scope or staleness reasons, never a fuzzy match."""
        reasons: list[str] = []
        if self.route_ref != capability.route_id:
            reasons.append("route_mismatch")
        if self.lifecycle not in ACTIVE_LIFECYCLES:
            reasons.append("lifecycle_not_active")
        if not _is_current(self.valid_from, self.valid_until, at):
            reasons.append("record_expired_or_not_yet_valid")
        if (self.capability_record_digest
                and self.capability_record_digest != capability.content_digest):
            reasons.append("capability_digest_changed")
        if self.model_revision and self.model_revision != capability.model_revision:
            reasons.append("model_revision_changed")
        if (self.deployment_digest
                and self.deployment_digest != capability.deployment_digest):
            reasons.append("deployment_digest_changed")
        selector = self.task_fingerprint_selector
        selector_match = (selector == request.task_fingerprint
                          or (selector.endswith("*") and request.task_fingerprint.startswith(
                              selector[:-1])))
        if not selector_match:
            reasons.append("task_fingerprint_out_of_scope")
        if request.operator not in self.applicable_operators:
            reasons.append("operator_out_of_scope")
        if request.response_topology not in self.applicable_response_topologies:
            reasons.append("response_topology_out_of_scope")
        if self.applicable_domains and request.domain not in self.applicable_domains:
            reasons.append("domain_out_of_scope")
        if self.applicable_profiles and request.profile not in self.applicable_profiles:
            reasons.append("profile_out_of_scope")
        if RISK_LEVELS.index(request.consequence) > RISK_LEVELS.index(self.risk_limit):
            reasons.append("consequence_exceeds_evidence")
        if set(request.required_modalities) != {self.modality}:
            reasons.append("modality_out_of_scope")
        for name, estimate, limits in (
            ("context", request.input_context_estimate, self.context_range),
            ("output", request.expected_output_estimate, self.output_range),
        ):
            if limits != (0, 0) and not limits[0] <= estimate <= limits[1]:
                reasons.append(f"{name}_estimate_out_of_scope")
        return not reasons, tuple(reasons)

    def to_dict(self) -> dict:
        return _safe_dict(self)


@dataclass(frozen=True)
class ModelRouteAvailabilitySnapshot:
    """Current runtime state. This snapshot is not persistent intelligence."""

    snapshot_id: str
    route_ref: str
    provider_id: str
    exact_model_id: str
    observed_at: str
    expires_at: str
    reachable: bool
    model_loaded: bool
    credential_required: bool
    credential_available: bool
    deployment_digest: str = ""
    context_limit: int | None = None
    maximum_output: int | None = None
    available_concurrency: int | None = None
    queue_depth: int | None = None
    source_ref: str = ""
    content_digest: str = ""

    def __post_init__(self) -> None:
        for name in ("snapshot_id", "route_ref", "provider_id", "exact_model_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        observed = _parse_time(self.observed_at, "observed_at")
        expires = _parse_time(self.expires_at, "expires_at")
        if expires <= observed:
            raise ModelRoutingError("availability must expire after observation")
        for name in (
            "context_limit", "maximum_output", "available_concurrency",
        ):
            number = getattr(self, name)
            if number is not None and number < 1:
                raise ModelRoutingError(f"{name} must be positive when known")
        if self.queue_depth is not None and self.queue_depth < 0:
            raise ModelRoutingError("queue_depth must not be negative")
        _seal(self, "content_digest")

    def is_fresh(self, at: datetime) -> bool:
        return (_parse_time(self.observed_at, "observed_at") <= at
                < _parse_time(self.expires_at, "expires_at"))

    def usable(self, at: datetime) -> bool:
        return bool(
            self.is_fresh(at)
            and self.reachable
            and self.model_loaded
            and (not self.credential_required or self.credential_available)
        )

    def to_dict(self) -> dict:
        return _safe_dict(self)


@dataclass(frozen=True)
class ModelSelectionRequest:
    """One typed need plus hard policy and non-authoritative preferences."""

    request_id: str
    run_id: str
    loop_id: str
    role: str
    profile: str
    run_mode: str
    compiled_task_ref: str
    task_fingerprint: str
    operator: str
    response_topology: str
    output_contract: str
    model_purpose: str
    required_modalities: tuple[str, ...] = ("text",)
    required_tools: tuple[str, ...] = ()
    structured_output_required: bool = False
    input_context_estimate: int = 0
    expected_output_estimate: int = 0
    domain: str = "general"
    novelty: str = "bounded"
    complexity: str = "bounded"
    consequence: str = "low"
    privacy_scope: str = "ordinary"
    data_locality: str = "ordinary"
    latency_target_seconds: float | None = None
    cost_ceiling: float | None = None
    reliability_target: float | None = None
    verification_plan: str = ""
    independent_verifier_available: bool = True
    allowed_routes: tuple[str, ...] = ()
    forbidden_routes: tuple[str, ...] = ()
    allowed_providers: tuple[str, ...] = ()
    forbidden_providers: tuple[str, ...] = ()
    allowed_localities: tuple[str, ...] = LOCALITIES
    preferred_localities: tuple[str, ...] = ()
    preferred_providers: tuple[str, ...] = ()
    preferred_thinking_power: str = ""
    failover_policy: str = "same_tier"
    escalation_policy: str = "configured"
    policy_refs: tuple[str, ...] = ()
    deterministic_sufficient: bool = False
    deterministic_evidence_refs: tuple[str, ...] = ()
    require_suitability_evidence: bool = True
    allow_unmeasured_route_for_experiment: bool = False
    allow_unreviewed_capability_for_experiment: bool = False

    def __post_init__(self) -> None:
        for name in (
            "request_id", "run_id", "loop_id", "profile", "compiled_task_ref",
            "task_fingerprint", "operator", "response_topology",
            "output_contract", "model_purpose", "domain", "novelty",
            "complexity", "privacy_scope", "data_locality",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.role not in ROLES:
            raise ModelRoutingError(f"role must be one of {ROLES}")
        if self.run_mode not in RUN_MODES:
            raise ModelRoutingError(f"run_mode must be one of {RUN_MODES}")
        if self.model_purpose not in PURPOSES:
            raise ModelRoutingError(f"model_purpose must be one of {PURPOSES}")
        if self.consequence not in RISK_LEVELS:
            raise ModelRoutingError(f"consequence must be one of {RISK_LEVELS}")
        if self.preferred_thinking_power and self.preferred_thinking_power not in THINKING_POWER:
            raise ModelRoutingError(
                f"preferred_thinking_power must be one of {THINKING_POWER}")
        if self.failover_policy not in ("none", "same_tier"):
            raise ModelRoutingError("failover_policy must be none or same_tier")
        if self.escalation_policy not in ("none", "configured"):
            raise ModelRoutingError(
                "escalation_policy must be none or configured")
        for name in (
            "required_modalities", "required_tools", "allowed_routes",
            "forbidden_routes", "allowed_providers", "forbidden_providers",
            "allowed_localities", "preferred_localities", "preferred_providers",
            "policy_refs", "deterministic_evidence_refs",
        ):
            object.__setattr__(
                self, name,
                _strings(getattr(self, name), name,
                         empty=name not in (
                             "required_modalities", "allowed_localities",
                         )),
            )
        if any(value not in LOCALITIES for value in self.allowed_localities):
            raise ModelRoutingError(f"allowed_localities must use {LOCALITIES}")
        if any(value not in LOCALITIES for value in self.preferred_localities):
            raise ModelRoutingError(f"preferred_localities must use {LOCALITIES}")
        if set(self.allowed_routes) & set(self.forbidden_routes):
            raise ModelRoutingError("one route cannot be both allowed and forbidden")
        if set(self.allowed_providers) & set(self.forbidden_providers):
            raise ModelRoutingError(
                "one provider cannot be both allowed and forbidden")
        if min(self.input_context_estimate, self.expected_output_estimate) < 0:
            raise ModelRoutingError("token estimates must not be negative")
        for name in ("latency_target_seconds", "cost_ceiling"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ModelRoutingError(f"{name} must be non-negative")
        if self.reliability_target is not None:
            object.__setattr__(
                self, "reliability_target",
                _probability(self.reliability_target, "reliability_target"),
            )
        if self.deterministic_sufficient and not self.deterministic_evidence_refs:
            raise ModelRoutingError(
                "a no-model decision needs deterministic evidence references")
        if (self.consequence in ("high", "critical")
                and (not self.verification_plan
                     or not self.independent_verifier_available)):
            raise ModelRoutingError(
                "high-consequence model work needs an independent verifier")

    def to_dict(self) -> dict:
        return _safe_dict(self)



@dataclass(frozen=True)
class ModelOutcomeEvidence:
    """Safe model-attempt evidence. Raw prompts, output, and reasoning are absent."""

    run_id: str
    loop_id: str
    model_attempt_loop_id: str
    route: str
    provider: str
    exact_model: str
    deployment: str
    task_fingerprint: str
    operator: str
    response_topology: str
    input_digest: str
    output_digest: str
    output_validation: str
    independent_verification: str
    task_success: bool
    failure_class: str
    attempts: int
    input_tokens: int | None
    output_tokens: int | None
    latency_seconds: float
    cost: float | None
    resource_use: tuple[tuple[str, float], ...] = ()
    human_intervention: bool = False
    safe_summary: str = ""
    evidence_refs: tuple[str, ...] = ()
    content_digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "run_id", "loop_id", "model_attempt_loop_id", "route", "provider",
            "exact_model", "task_fingerprint", "operator", "response_topology",
            "input_digest", "output_digest", "output_validation",
            "independent_verification",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.attempts < 1:
            raise ModelRoutingError("outcome attempts must be positive")
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ModelRoutingError(f"{name} must not be negative")
        if self.latency_seconds < 0 or not math.isfinite(self.latency_seconds):
            raise ModelRoutingError("latency_seconds must be non-negative")
        if self.cost is not None and (self.cost < 0 or not math.isfinite(self.cost)):
            raise ModelRoutingError("cost must be non-negative when known")
        object.__setattr__(self, "resource_use", _pairs(
            self.resource_use, "resource_use"))
        object.__setattr__(self, "evidence_refs", _strings(
            self.evidence_refs, "evidence_refs"))
        lowered = self.safe_summary.lower()
        if "<think" in lowered or "</think" in lowered:
            raise ModelRoutingError("safe_summary must not retain thinking blocks")
        _seal(self, "content_digest")

    @property
    def accounting_complete(self) -> bool:
        return self.input_tokens is not None and self.output_tokens is not None

    def to_dict(self) -> dict:
        value = _safe_dict(self)
        value["accounting_complete"] = self.accounting_complete
        return value


@dataclass(frozen=True)
class ModelRoutingLearningCandidate:
    """A scoped routing proposal that cannot approve itself."""

    candidate_id: str
    source_outcomes: tuple[str, ...]
    proposed_task_selector: str
    proposed_route_preference: tuple[str, ...]
    proposed_route_avoidance: tuple[str, ...]
    proposed_escalation_rule: str
    supporting_evidence: tuple[str, ...]
    counterevidence: tuple[str, ...]
    sample_size: int
    uncertainty: str
    scope: tuple[str, ...]
    producer_loop_id: str
    lifecycle: str = "candidate"
    independent_review_required: bool = True
    reviewer_loop_id: str = ""
    rollback: str = ""
    content_digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "candidate_id", "proposed_task_selector", "uncertainty",
            "producer_loop_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "source_outcomes", "proposed_route_preference",
            "proposed_route_avoidance", "supporting_evidence",
            "counterevidence", "scope",
        ):
            object.__setattr__(
                self, name,
                _strings(getattr(self, name), name,
                         empty=name in (
                             "proposed_route_avoidance", "counterevidence",
                         )),
            )
        if self.sample_size < 1:
            raise ModelRoutingError("a routing candidate needs evidence")
        if not self.independent_review_required:
            raise ModelRoutingError("routing candidates require independent review")
        if self.lifecycle not in (
                "candidate", "under_review", "approved", "rejected"):
            raise ModelRoutingError("unknown routing candidate lifecycle")
        if self.lifecycle in ("approved", "rejected"):
            if not self.reviewer_loop_id:
                raise ModelRoutingError("a terminal review needs reviewer_loop_id")
            if self.reviewer_loop_id == self.producer_loop_id:
                raise ModelRoutingError("a producer cannot review its own candidate")
        if self.lifecycle == "approved" and not self.rollback.strip():
            raise ModelRoutingError("an approved routing candidate needs rollback")
        if set(self.proposed_route_preference) & set(
                self.proposed_route_avoidance):
            raise ModelRoutingError(
                "one candidate cannot prefer and avoid the same route")
        _seal(self, "content_digest")

    def to_dict(self) -> dict:
        return _safe_dict(self)
