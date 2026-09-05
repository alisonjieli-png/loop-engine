"""Passive authority and readiness records for an explicit GPT-6 Astra route.

Architectural role: internal model-routing policy and request records.

This module performs no provider discovery, credential lookup, network access,
model call, route registration, or spending. It retains candidate paid-model
authority, availability, demand, and pricing analysis. Executable route
qualification is unconditionally false until one-use authority, trusted-clock
availability, exact adapter qualification, and invocation-budget enforcement
are integrated through existing runtime boundaries.

The model facts and prices are from the official OpenAI GPT-6 Astra model page
observed on 2026-09-04. The Responses compatibility facts are from the
official current model guidance observed on the same date.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from .astra_route_record_identity import (
    AstraRouteRecordError as AstraRouteReadinessError,
)
from .astra_route_record_identity import (
    adapter_capability_binding,
    authority_binding,
    authority_safe_summary,
    capability_qualification_binding,
    content_digest,
    cost_exposure_dict,
    demand_binding,
    issuer_reference,
    provider_readiness_binding,
    request_binding,
    thinking_policy_binding,
)
from .astra_route_record_identity import (
    money as _money,
)
from .astra_route_record_identity import (
    non_secret_reference as _non_secret_reference,
)
from .astra_route_record_identity import (
    one_line as _one_line,
)
from .astra_route_record_identity import (
    optional_limit as _optional_limit,
)
from .astra_route_record_identity import (
    positive_limit as _positive_limit,
)
from .astra_route_record_identity import (
    require_digest as _require_digest,
)
from .astra_route_record_identity import (
    strings as _strings,
)
from .astra_route_record_identity import (
    timestamp as _timestamp,
)
from .model_routing_records import (
    THINKING_POWER,
    ModelRouteAvailabilitySnapshot,
)
from .openai_responses_client import SUPPORTED_REASONING_EFFORTS

ASTRA_AUTHORITY_SCHEMA_VERSION = "1.0.0"
ASTRA_EXECUTABLE_ROUTE_QUALIFIED = False
ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON = "astra_executable_route_not_qualified"
ASTRA_REMAINING_INTEGRATION_REQUIREMENTS = (
    "one_use_spending_and_effect_authority",
    "trusted_clock_provider_availability",
    "exact_adapter_and_credential_qualification",
    "invocation_budget_enforcement",
)
ASTRA_ROUTE_NAME = "cloud.openai.gpt-6-astra.explicit"
ASTRA_CREDENTIAL_REF = "env:OPENAI_API_KEY"
ASTRA_CONTEXT_WINDOW_TOKENS = 1_050_000
# Derived allowance: context window minus the required 128,000-token maximum
# output request. OpenAI documents the two source values, not 922,000 as a
# separate model input maximum.
ASTRA_MAXIMUM_INPUT_TOKENS = 922_000
ASTRA_MAXIMUM_OUTPUT_TOKENS = 128_000
ASTRA_LONG_CONTEXT_THRESHOLD = 272_000
ASTRA_QUALIFIED_DATA_LOCALITY = "global"
ASTRA_QUALIFIED_SERVICE_TIER = "standard"
ASTRA_ROUTE_PURPOSES = (
    "counted_generation",
    "generation",
    "reasoning",
    "code",
)
ASTRA_MODEL_DOCUMENTATION_URL = (
    "https://developers.openai.com/api/docs/models/gpt-6-astra"
)
ASTRA_MODEL_GUIDANCE_URL = "https://developers.openai.com/api/docs/guides/latest-model"
RESPONSES_SERVICE_TIERS = ("standard", "flex", "fast")
PRICING_WORKFLOWS = ("standard", "batch", "flex", "fast")
# Compatibility name for route-demand validation. Batch is intentionally not a
# Responses service tier; its nominal price remains in PRICING_WORKFLOWS.
SERVICE_TIERS = RESPONSES_SERVICE_TIERS
READINESS_STATES = ("ready", "refused")
_MONEY_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class ThinkingPowerReasoningPolicy:
    """Versioned data mapping Loop thinking power to provider effort values."""

    policy_id: str
    version: str
    mappings: tuple[tuple[str, str], ...]
    supported_efforts: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            _non_secret_reference(self.policy_id, "policy_id"),
        )
        object.__setattr__(self, "version", _one_line(self.version, "version"))
        efforts = _strings(self.supported_efforts, "supported_efforts")
        if set(efforts) != set(SUPPORTED_REASONING_EFFORTS):
            raise AstraRouteReadinessError(
                "supported_efforts must preserve the exact Astra effort set"
            )
        object.__setattr__(self, "supported_efforts", efforts)
        normalized: list[tuple[str, str]] = []
        for item in self.mappings:
            if len(item) != 2:
                raise AstraRouteReadinessError(
                    "thinking-power mappings need a source and destination"
                )
            thinking = _one_line(item[0], "thinking_power")
            effort = _one_line(item[1], "reasoning_effort")
            if effort not in efforts:
                raise AstraRouteReadinessError(
                    f"unsupported reasoning effort {effort!r}"
                )
            normalized.append((thinking, effort))
        keys = tuple(item[0] for item in normalized)
        if len(keys) != len(set(keys)) or set(keys) != set(THINKING_POWER):
            raise AstraRouteReadinessError(
                "the mapping must define every canonical thinking-power value once"
            )
        object.__setattr__(self, "mappings", tuple(normalized))

    def effort_for(self, thinking_power: str) -> str:
        """Resolve through policy data without inspecting a model name."""
        values = dict(self.mappings)
        if thinking_power not in values:
            raise AstraRouteReadinessError(
                f"thinking_power must be one of {THINKING_POWER}"
            )
        return values[thinking_power]

    def binding_dict(self) -> dict[str, object]:
        return thinking_policy_binding(self)


ASTRA_REASONING_POLICY = ThinkingPowerReasoningPolicy(
    policy_id="openai.astra.thinking-power-reasoning@1",
    version=ASTRA_AUTHORITY_SCHEMA_VERSION,
    mappings=(
        ("small", "low"),
        ("medium", "medium"),
        ("high", "high"),
        ("max", "max"),
        ("specialized", "xhigh"),
    ),
    supported_efforts=SUPPORTED_REASONING_EFFORTS,
)


@dataclass(frozen=True)
class AdapterCapabilityQualification:
    """Separate model declaration from this adapter's qualification state."""

    capability: str
    model_declared: bool
    adapter_qualified: bool = False
    qualification_ref: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability", _one_line(self.capability, "capability"))
        for name in ("model_declared", "adapter_qualified"):
            if not isinstance(getattr(self, name), bool):
                raise AstraRouteReadinessError(f"{name} must be boolean")
        ref = _non_secret_reference(
            self.qualification_ref,
            "qualification_ref",
            allow_empty=True,
        )
        object.__setattr__(self, "qualification_ref", ref)
        if self.adapter_qualified and not self.model_declared:
            raise AstraRouteReadinessError(
                "an adapter cannot qualify an undeclared model capability"
            )
        if self.adapter_qualified != bool(ref):
            raise AstraRouteReadinessError(
                "adapter qualification and its evidence reference are one fact"
            )

    def binding_dict(self) -> dict[str, object]:
        return capability_qualification_binding(self)


@dataclass(frozen=True)
class AstraAdapterCapabilityPolicy:
    """Capabilities exposed by the current narrow Responses adapter."""

    version: str
    structured_output: AdapterCapabilityQualification
    tool_calling: AdapterCapabilityQualification
    async_tool_calling: AdapterCapabilityQualification
    text_input_qualified: bool = True
    text_output_qualified: bool = True
    explicit_service_tier_qualified: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "version", _one_line(self.version, "capability policy version")
        )
        expected = {
            "structured_output": self.structured_output,
            "tool_calling": self.tool_calling,
            "async_tool_calling": self.async_tool_calling,
        }
        for name, record in expected.items():
            if record.capability != name:
                raise AstraRouteReadinessError(
                    f"{name} qualification has the wrong capability name"
                )
        for name in (
            "text_input_qualified",
            "text_output_qualified",
            "explicit_service_tier_qualified",
        ):
            if not isinstance(getattr(self, name), bool):
                raise AstraRouteReadinessError(f"{name} must be boolean")

    def binding_dict(self) -> dict[str, object]:
        return adapter_capability_binding(self)


ASTRA_ADAPTER_CAPABILITIES = AstraAdapterCapabilityPolicy(
    version=ASTRA_AUTHORITY_SCHEMA_VERSION,
    structured_output=AdapterCapabilityQualification(
        "structured_output", model_declared=True
    ),
    tool_calling=AdapterCapabilityQualification("tool_calling", model_declared=True),
    async_tool_calling=AdapterCapabilityQualification(
        "async_tool_calling", model_declared=True
    ),
    explicit_service_tier_qualified=True,
)


@dataclass(frozen=True)
class AstraPricingSpec:
    """Source-backed token pricing used for a conservative exposure bound."""

    version: str = ASTRA_AUTHORITY_SCHEMA_VERSION
    input_per_million_usd: Decimal = Decimal(10)
    cached_input_per_million_usd: Decimal = Decimal(1)
    cache_write_per_million_usd: Decimal = Decimal("12.5")
    output_per_million_usd: Decimal = Decimal(50)
    long_context_threshold_tokens: int = ASTRA_LONG_CONTEXT_THRESHOLD
    long_input_and_cache_multiplier: Decimal = Decimal(2)
    long_output_multiplier: Decimal = Decimal("1.5")
    service_tier_multipliers: tuple[tuple[str, Decimal], ...] = (
        ("standard", Decimal(1)),
        ("batch", Decimal("0.5")),
        ("flex", Decimal("0.5")),
        ("fast", Decimal(2)),
    )
    source_ref: str = ASTRA_MODEL_DOCUMENTATION_URL
    observed_at: str = "2026-09-04"

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", _one_line(self.version, "pricing version"))
        object.__setattr__(
            self,
            "source_ref",
            _non_secret_reference(self.source_ref, "pricing source_ref"),
        )
        object.__setattr__(
            self, "observed_at", _one_line(self.observed_at, "pricing observed_at")
        )
        for name in (
            "input_per_million_usd",
            "cached_input_per_million_usd",
            "cache_write_per_million_usd",
            "output_per_million_usd",
            "long_input_and_cache_multiplier",
            "long_output_multiplier",
        ):
            value = _money(getattr(self, name), name)
            if value is None or value <= 0:
                raise AstraRouteReadinessError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        _positive_limit(
            self.long_context_threshold_tokens,
            "long_context_threshold_tokens",
        )
        tiers: list[tuple[str, Decimal]] = []
        for name, raw_multiplier in self.service_tier_multipliers:
            tier = _one_line(name, "service tier")
            multiplier = _money(raw_multiplier, "service tier multiplier")
            if multiplier is None or multiplier <= 0:
                raise AstraRouteReadinessError(
                    "service tier multipliers must be positive"
                )
            tiers.append((tier, multiplier))
        names = tuple(item[0] for item in tiers)
        if len(names) != len(set(names)) or set(names) != set(PRICING_WORKFLOWS):
            raise AstraRouteReadinessError(
                "pricing must define every Astra pricing workflow once"
            )
        object.__setattr__(self, "service_tier_multipliers", tuple(tiers))

    def tier_multiplier(self, service_tier: str) -> Decimal:
        try:
            return dict(self.service_tier_multipliers)[service_tier]
        except KeyError as exc:
            raise AstraRouteReadinessError(
                f"pricing workflow must be one of {PRICING_WORKFLOWS}"
            ) from exc


ASTRA_PRICING = AstraPricingSpec()


@dataclass(frozen=True)
class AstraModelDemand:
    """Exact maximum physical demand for one bounded Astra route plan."""

    demand_id: str
    model_purpose: str
    thinking_power: str
    maximum_model_calls: int
    maximum_input_tokens_per_call: int
    maximum_output_tokens_per_call: int
    service_tier: str
    required_data_locality: str
    required_modalities: tuple[str, ...] = ("text",)
    requires_structured_output: bool = False
    requires_tool_calling: bool = False
    requires_async_tool_calling: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "demand_id",
            _non_secret_reference(self.demand_id, "demand_id"),
        )
        object.__setattr__(
            self, "model_purpose", _one_line(self.model_purpose, "model_purpose")
        )
        if self.model_purpose not in ASTRA_ROUTE_PURPOSES:
            raise AstraRouteReadinessError(
                f"model_purpose must be one of {ASTRA_ROUTE_PURPOSES}"
            )
        if self.thinking_power not in THINKING_POWER:
            raise AstraRouteReadinessError(
                f"thinking_power must be one of {THINKING_POWER}"
            )
        _positive_limit(self.maximum_model_calls, "maximum_model_calls")
        _positive_limit(
            self.maximum_input_tokens_per_call,
            "maximum_input_tokens_per_call",
        )
        _positive_limit(
            self.maximum_output_tokens_per_call,
            "maximum_output_tokens_per_call",
        )
        if self.maximum_input_tokens_per_call > ASTRA_MAXIMUM_INPUT_TOKENS:
            raise AstraRouteReadinessError(
                "maximum input exceeds the exact Astra input bound"
            )
        if self.maximum_output_tokens_per_call != ASTRA_MAXIMUM_OUTPUT_TOKENS:
            raise AstraRouteReadinessError(
                "the current adapter must request Astra's exact output maximum"
            )
        if (
            self.maximum_input_tokens_per_call + self.maximum_output_tokens_per_call
            > ASTRA_CONTEXT_WINDOW_TOKENS
        ):
            raise AstraRouteReadinessError(
                "input and output ceilings exceed the context window"
            )
        if self.service_tier not in SERVICE_TIERS:
            raise AstraRouteReadinessError(
                "service_tier must be a Responses request workflow from "
                f"{SERVICE_TIERS}; Batch uses the separate Batch API"
            )
        object.__setattr__(
            self,
            "required_data_locality",
            _one_line(self.required_data_locality, "required_data_locality"),
        )
        object.__setattr__(
            self,
            "required_modalities",
            _strings(self.required_modalities, "required_modalities"),
        )
        if not self.required_modalities:
            raise AstraRouteReadinessError("required_modalities must be non-empty")
        for name in (
            "requires_structured_output",
            "requires_tool_calling",
            "requires_async_tool_calling",
        ):
            if not isinstance(getattr(self, name), bool):
                raise AstraRouteReadinessError(f"{name} must be boolean")

    @property
    def requested_route_purposes(self) -> tuple[str, ...]:
        """Return the one purpose this demand may ever compile."""
        return (self.model_purpose,)

    @property
    def maximum_input_tokens(self) -> int:
        return self.maximum_model_calls * self.maximum_input_tokens_per_call

    @property
    def maximum_output_tokens(self) -> int:
        return self.maximum_model_calls * self.maximum_output_tokens_per_call

    @property
    def maximum_total_tokens(self) -> int:
        return self.maximum_input_tokens + self.maximum_output_tokens

    def binding_dict(self) -> dict[str, object]:
        return demand_binding(self)


@dataclass(frozen=True)
class PaidModelRouteAuthority:
    """Candidate paid-route envelope; it cannot grant execution authority."""

    authority_id: str
    issuer_ref: str
    model_calls_authorized: bool
    paid_route_opt_in: bool
    credential_ref: str
    authorized_route_name: str
    authorized_provider_id: str
    authorized_model_id: str
    allowed_data_localities: tuple[str, ...]
    allowed_service_tiers: tuple[str, ...]
    maximum_model_calls: int | None
    maximum_input_tokens: int | None
    maximum_output_tokens: int | None
    maximum_total_tokens: int | None
    maximum_cost_usd: Decimal | str | float | int | None
    version: str = ASTRA_AUTHORITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "authority_id",
            "authorized_route_name",
            "authorized_provider_id",
            "authorized_model_id",
        ):
            object.__setattr__(
                self,
                name,
                _non_secret_reference(getattr(self, name), name),
            )
        issuer_ref = issuer_reference(self.issuer_ref)
        object.__setattr__(self, "issuer_ref", issuer_ref)
        object.__setattr__(self, "version", _one_line(self.version, "version"))
        for name in ("model_calls_authorized", "paid_route_opt_in"):
            if not isinstance(getattr(self, name), bool):
                raise AstraRouteReadinessError(f"{name} must be boolean")
        credential_ref = _non_secret_reference(
            self.credential_ref,
            "credential_ref",
        )
        if credential_ref != ASTRA_CREDENTIAL_REF:
            raise AstraRouteReadinessError(
                f"credential_ref must be exactly {ASTRA_CREDENTIAL_REF!r}"
            )
        object.__setattr__(self, "credential_ref", credential_ref)
        for name in ("allowed_data_localities", "allowed_service_tiers"):
            object.__setattr__(self, name, _strings(getattr(self, name), name))
        if any(tier not in SERVICE_TIERS for tier in self.allowed_service_tiers):
            raise AstraRouteReadinessError(
                f"allowed_service_tiers must use {SERVICE_TIERS}"
            )
        for name in (
            "maximum_model_calls",
            "maximum_input_tokens",
            "maximum_output_tokens",
            "maximum_total_tokens",
        ):
            object.__setattr__(self, name, _optional_limit(getattr(self, name), name))
        object.__setattr__(
            self, "maximum_cost_usd", _money(self.maximum_cost_usd, "maximum_cost_usd")
        )

    def safe_summary(self) -> dict[str, object]:
        """Describe authority without resolving or exposing a credential."""
        return authority_safe_summary(self)

    def binding_dict(self) -> dict[str, object]:
        """Return every authority field for request identity, not display."""
        return authority_binding(self)


@dataclass(frozen=True)
class AstraProviderReadiness:
    """Bind canonical availability to a separately sourced data locality."""

    availability: ModelRouteAvailabilitySnapshot | None
    data_locality: str = ""
    data_locality_source_ref: str = ""

    def __post_init__(self) -> None:
        if self.availability is not None and not isinstance(
            self.availability, ModelRouteAvailabilitySnapshot
        ):
            raise AstraRouteReadinessError(
                "availability must use ModelRouteAvailabilitySnapshot"
            )
        if self.availability is not None:
            for name in (
                "snapshot_id",
                "route_ref",
                "provider_id",
                "exact_model_id",
                "source_ref",
            ):
                value = getattr(self.availability, name)
                if value:
                    _non_secret_reference(value, f"availability.{name}")
        locality = _non_secret_reference(
            self.data_locality,
            "data_locality",
            allow_empty=True,
        )
        source = _non_secret_reference(
            self.data_locality_source_ref,
            "data_locality_source_ref",
            allow_empty=True,
        )
        if bool(locality) != bool(source):
            raise AstraRouteReadinessError(
                "data locality and its source reference are one fact"
            )
        object.__setattr__(self, "data_locality", locality)
        object.__setattr__(self, "data_locality_source_ref", source)

    def binding_dict(self) -> dict[str, object]:
        return provider_readiness_binding(self)


@dataclass(frozen=True)
class AstraRouteReadinessRequest:
    """One passive request to evaluate an exact route before execution."""

    request_id: str
    demand: AstraModelDemand
    authority: PaidModelRouteAuthority
    provider_readiness: AstraProviderReadiness
    evaluated_at: str
    reasoning_policy: ThinkingPowerReasoningPolicy = ASTRA_REASONING_POLICY
    adapter_capabilities: AstraAdapterCapabilityPolicy = ASTRA_ADAPTER_CAPABILITIES

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _non_secret_reference(self.request_id, "request_id"),
        )
        if not isinstance(self.demand, AstraModelDemand):
            raise AstraRouteReadinessError("demand must use AstraModelDemand")
        if not isinstance(self.authority, PaidModelRouteAuthority):
            raise AstraRouteReadinessError("authority must use PaidModelRouteAuthority")
        if not isinstance(self.provider_readiness, AstraProviderReadiness):
            raise AstraRouteReadinessError(
                "provider_readiness must use AstraProviderReadiness"
            )
        if not isinstance(self.reasoning_policy, ThinkingPowerReasoningPolicy):
            raise AstraRouteReadinessError("reasoning_policy has the wrong contract")
        if not isinstance(self.adapter_capabilities, AstraAdapterCapabilityPolicy):
            raise AstraRouteReadinessError(
                "adapter_capabilities has the wrong contract"
            )
        evaluated_at = _timestamp(self.evaluated_at, "evaluated_at")
        object.__setattr__(
            self,
            "evaluated_at",
            evaluated_at.isoformat().replace("+00:00", "Z"),
        )

    def binding_dict(self) -> dict[str, object]:
        """Return the complete canonical input to one readiness decision."""
        return request_binding(self, ASTRA_AUTHORITY_SCHEMA_VERSION)

    @property
    def content_digest(self) -> str:
        return content_digest(self.binding_dict())


@dataclass(frozen=True)
class AstraCostExposure:
    """Conservative maximum token charge for the requested call envelope."""

    maximum_model_calls: int
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_total_tokens: int
    input_rate_per_million_usd: Decimal
    output_rate_per_million_usd: Decimal
    service_tier: str
    service_tier_multiplier: Decimal
    long_context_surcharge_applied: bool
    maximum_cost_usd: Decimal
    method: str = (
        "all input uses the higher uncached-or-cache-write rate; all output "
        "may reach the declared maximum; discounts are not assumed"
    )

    def to_dict(self) -> dict[str, object]:
        return cost_exposure_dict(self)


def conservative_astra_cost_exposure(
    demand: AstraModelDemand,
    pricing: AstraPricingSpec = ASTRA_PRICING,
) -> AstraCostExposure:
    """Price the maximum physical demand without assuming cache discounts."""
    if not isinstance(demand, AstraModelDemand):
        raise AstraRouteReadinessError("cost exposure requires AstraModelDemand")
    if not isinstance(pricing, AstraPricingSpec):
        raise AstraRouteReadinessError("cost exposure requires AstraPricingSpec")
    long_context = (
        demand.maximum_input_tokens_per_call > pricing.long_context_threshold_tokens
    )
    base_input_rate = max(
        pricing.input_per_million_usd,
        pricing.cached_input_per_million_usd,
        pricing.cache_write_per_million_usd,
    )
    long_input = pricing.long_input_and_cache_multiplier if long_context else Decimal(1)
    long_output = pricing.long_output_multiplier if long_context else Decimal(1)
    tier = pricing.tier_multiplier(demand.service_tier)
    input_rate = base_input_rate * long_input * tier
    output_rate = pricing.output_per_million_usd * long_output * tier
    raw = (
        Decimal(demand.maximum_input_tokens) * input_rate
        + Decimal(demand.maximum_output_tokens) * output_rate
    ) / Decimal(1_000_000)
    maximum_cost = raw.quantize(_MONEY_QUANTUM, rounding=ROUND_CEILING)
    return AstraCostExposure(
        maximum_model_calls=demand.maximum_model_calls,
        maximum_input_tokens=demand.maximum_input_tokens,
        maximum_output_tokens=demand.maximum_output_tokens,
        maximum_total_tokens=demand.maximum_total_tokens,
        input_rate_per_million_usd=input_rate,
        output_rate_per_million_usd=output_rate,
        service_tier=demand.service_tier,
        service_tier_multiplier=tier,
        long_context_surcharge_applied=long_context,
        maximum_cost_usd=maximum_cost,
    )


@dataclass(frozen=True)
class AstraReadinessDecision:
    """Fail-closed offline result. It grants no execution authority."""

    request_id: str
    request_digest: str
    state: str
    refusal_reasons: tuple[str, ...]
    reasoning_effort: str
    cost_exposure: AstraCostExposure
    authority_ref: str
    availability_snapshot_ref: str
    reasoning_policy_ref: str
    adapter_capability_version: str
    provider_calls_made: int = 0
    credential_reads: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _non_secret_reference(self.request_id, "request_id"),
        )
        object.__setattr__(
            self,
            "request_digest",
            _require_digest(self.request_digest, "request_digest"),
        )
        if self.state not in READINESS_STATES:
            raise AstraRouteReadinessError(f"state must be one of {READINESS_STATES}")
        object.__setattr__(
            self, "refusal_reasons", _strings(self.refusal_reasons, "refusal_reasons")
        )
        if (self.state == "ready") == bool(self.refusal_reasons):
            raise AstraRouteReadinessError(
                "ready decisions have no reasons; refused decisions need reasons"
            )
        if not ASTRA_EXECUTABLE_ROUTE_QUALIFIED and (
            self.state != "refused"
            or ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON not in self.refusal_reasons
        ):
            raise AstraRouteReadinessError(
                "the quarantined Astra route must remain refused with its "
                "integration reason"
            )
        if self.reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
            raise AstraRouteReadinessError(
                "decision has an unsupported reasoning effort"
            )
        if not isinstance(self.cost_exposure, AstraCostExposure):
            raise AstraRouteReadinessError(
                "decision cost_exposure has the wrong contract"
            )
        for name in (
            "authority_ref",
            "availability_snapshot_ref",
            "reasoning_policy_ref",
        ):
            object.__setattr__(
                self,
                name,
                _non_secret_reference(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "adapter_capability_version",
            _one_line(
                self.adapter_capability_version,
                "adapter_capability_version",
            ),
        )
        if self.provider_calls_made != 0 or self.credential_reads != 0:
            raise AstraRouteReadinessError(
                "offline readiness cannot call providers or read credentials"
            )

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "astra_route_readiness_decision/v1",
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "state": self.state,
            "refusal_reasons": list(self.refusal_reasons),
            "reasoning_effort": self.reasoning_effort,
            "cost_exposure": self.cost_exposure.to_dict(),
            "authority_ref": self.authority_ref,
            "availability_snapshot_ref": self.availability_snapshot_ref,
            "reasoning_policy_ref": self.reasoning_policy_ref,
            "adapter_capability_version": self.adapter_capability_version,
            "provider_calls_made": self.provider_calls_made,
            "credential_reads": self.credential_reads,
            "executable_route_qualified": ASTRA_EXECUTABLE_ROUTE_QUALIFIED,
            "remaining_integration_requirements": list(
                ASTRA_REMAINING_INTEGRATION_REQUIREMENTS
            ),
            "execution_authorized": False,
        }
