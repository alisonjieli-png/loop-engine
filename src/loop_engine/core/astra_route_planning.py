"""Offline candidate analysis and quarantined plan code for GPT-6 Astra.

This module evaluates passive records, but executable route qualification is
unconditionally false. Dormant compilation code remains visible for review and
cannot produce a ModelRoute or ProviderSpec plan until the missing one-use
authority, trusted-clock, adapter, and invocation-budget integrations exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .astra_route_authority import (
    ASTRA_CONTEXT_WINDOW_TOKENS,
    ASTRA_CREDENTIAL_REF,
    ASTRA_EXECUTABLE_ROUTE_QUALIFIED,
    ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON,
    ASTRA_MAXIMUM_OUTPUT_TOKENS,
    ASTRA_QUALIFIED_DATA_LOCALITY,
    ASTRA_QUALIFIED_SERVICE_TIER,
    ASTRA_REMAINING_INTEGRATION_REQUIREMENTS,
    ASTRA_ROUTE_NAME,
    AstraAdapterCapabilityPolicy,
    AstraCostExposure,
    AstraReadinessDecision,
    AstraRouteReadinessError,
    AstraRouteReadinessRequest,
    _timestamp,
    conservative_astra_cost_exposure,
)
from .model_gateway import ProviderSpec
from .model_routes import ModelProviderCapabilities, ModelRoute
from .openai_responses_client import (
    API_URL,
    DEFAULT_MODEL,
    MODEL_OUTPUT_CAPABILITIES,
    PROVIDER_CAPABILITIES,
    PROVIDER_ID,
    WIRE_FORMAT,
    OpenAIResponsesAdapter,
)


def _authority_reasons(
    request: AstraRouteReadinessRequest,
    exposure: AstraCostExposure,
) -> list[str]:
    authority = request.authority
    demand = request.demand
    reasons: list[str] = []
    exact_values = (
        (authority.authorized_route_name, ASTRA_ROUTE_NAME, "route_not_authorized"),
        (authority.authorized_provider_id, PROVIDER_ID, "provider_not_authorized"),
        (authority.authorized_model_id, DEFAULT_MODEL, "model_not_authorized"),
    )
    if not authority.model_calls_authorized:
        reasons.append("model_calls_not_authorized")
    if not authority.paid_route_opt_in:
        reasons.append("paid_route_not_authorized")
    if not authority.credential_ref:
        reasons.append("credential_reference_unknown")
    elif authority.credential_ref != ASTRA_CREDENTIAL_REF:
        reasons.append("credential_reference_mismatch")
    for actual, expected, reason in exact_values:
        if actual != expected:
            reasons.append(reason)
    if demand.required_data_locality not in authority.allowed_data_localities:
        reasons.append("data_locality_not_authorized")
    if demand.service_tier not in authority.allowed_service_tiers:
        reasons.append("service_tier_not_authorized")
    limits = (
        (
            authority.maximum_model_calls,
            demand.maximum_model_calls,
            "maximum_model_calls",
        ),
        (
            authority.maximum_input_tokens,
            demand.maximum_input_tokens,
            "maximum_input_tokens",
        ),
        (
            authority.maximum_output_tokens,
            demand.maximum_output_tokens,
            "maximum_output_tokens",
        ),
        (
            authority.maximum_total_tokens,
            demand.maximum_total_tokens,
            "maximum_total_tokens",
        ),
    )
    for authorized, needed, name in limits:
        if authorized is None:
            reasons.append(f"{name}_authority_unknown")
        elif authorized < needed:
            reasons.append(f"{name}_authority_insufficient")
    if authority.maximum_cost_usd is None:
        reasons.append("maximum_cost_authority_unknown")
    elif authority.maximum_cost_usd < exposure.maximum_cost_usd:
        reasons.append("maximum_cost_authority_insufficient")
    return reasons


def _provider_reasons(request: AstraRouteReadinessRequest) -> list[str]:
    readiness = request.provider_readiness
    demand = request.demand
    at = _timestamp(request.evaluated_at, "evaluated_at")
    reasons: list[str] = []
    if not readiness.data_locality:
        reasons.append("provider_data_locality_unknown")
    elif readiness.data_locality != demand.required_data_locality:
        reasons.append("provider_data_locality_mismatch")
    availability = readiness.availability
    if availability is None:
        reasons.append("provider_availability_unknown")
        return reasons
    identities = (
        (availability.route_ref, ASTRA_ROUTE_NAME),
        (availability.provider_id, PROVIDER_ID),
        (availability.exact_model_id, DEFAULT_MODEL),
    )
    if any(actual != expected for actual, expected in identities):
        reasons.append("provider_availability_identity_mismatch")
    if not availability.source_ref:
        reasons.append("provider_availability_source_unknown")
    if not availability.is_fresh(at):
        reasons.append("provider_availability_stale")
    if availability.reachable is not True:
        reasons.append("provider_unreachable")
    if availability.model_loaded is not True:
        reasons.append("model_unavailable")
    if availability.credential_required is not True:
        reasons.append("provider_credential_requirement_mismatch")
    elif availability.credential_available is not True:
        reasons.append("credential_unavailable")
    if availability.context_limit is None:
        reasons.append("provider_context_capacity_unknown")
    elif availability.context_limit < ASTRA_CONTEXT_WINDOW_TOKENS:
        reasons.append("provider_context_capacity_insufficient")
    if availability.maximum_output is None:
        reasons.append("provider_output_capacity_unknown")
    elif availability.maximum_output < ASTRA_MAXIMUM_OUTPUT_TOKENS:
        reasons.append("provider_output_capacity_insufficient")
    return reasons


def _capability_reasons(request: AstraRouteReadinessRequest) -> list[str]:
    demand = request.demand
    capabilities = request.adapter_capabilities
    reasons: list[str] = []
    if demand.required_data_locality != ASTRA_QUALIFIED_DATA_LOCALITY:
        reasons.append("astra_data_locality_not_qualified")
    if demand.service_tier != ASTRA_QUALIFIED_SERVICE_TIER:
        reasons.append("astra_service_tier_not_qualified")
    if set(demand.required_modalities) != {"text"}:
        reasons.append("required_modality_adapter_unqualified")
    if not capabilities.text_input_qualified:
        reasons.append("text_input_adapter_unqualified")
    if not capabilities.text_output_qualified:
        reasons.append("text_output_adapter_unqualified")
    requested = (
        (
            demand.requires_structured_output,
            capabilities.structured_output,
        ),
        (demand.requires_tool_calling, capabilities.tool_calling),
        (
            demand.requires_async_tool_calling,
            capabilities.async_tool_calling,
        ),
    )
    for required, qualification in requested:
        if required and not qualification.adapter_qualified:
            reasons.append(f"{qualification.capability}_adapter_unqualified")
    if not capabilities.explicit_service_tier_qualified:
        reasons.append("service_tier_adapter_unqualified")
    return reasons


def assess_astra_route_readiness(
    request: AstraRouteReadinessRequest,
) -> AstraReadinessDecision:
    """Apply all offline hard gates and preserve every refusal reason."""
    if not isinstance(request, AstraRouteReadinessRequest):
        raise AstraRouteReadinessError("readiness requires AstraRouteReadinessRequest")
    exposure = conservative_astra_cost_exposure(request.demand)
    reasons = (
        [ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON]
        + _authority_reasons(request, exposure)
        + _provider_reasons(request)
        + _capability_reasons(request)
    )
    reasons = list(dict.fromkeys(reasons))
    availability = request.provider_readiness.availability
    effort = request.reasoning_policy.effort_for(request.demand.thinking_power)
    return AstraReadinessDecision(
        request_id=request.request_id,
        request_digest=request.content_digest,
        state="refused",
        refusal_reasons=tuple(reasons),
        reasoning_effort=effort,
        cost_exposure=exposure,
        authority_ref=request.authority.authority_id,
        availability_snapshot_ref=(
            availability.snapshot_id if availability is not None else "unknown"
        ),
        reasoning_policy_ref=(
            f"{request.reasoning_policy.policy_id}@{request.reasoning_policy.version}"
        ),
        adapter_capability_version=request.adapter_capabilities.version,
    )


@dataclass(frozen=True)
class AstraRoutePlan:
    """Explicit existing-contract binding produced only after readiness."""

    request_id: str
    request_digest: str
    demand_id: str
    model_purpose: str
    route: ModelRoute
    provider: ProviderSpec
    reasoning_effort: str
    maximum_model_calls: int
    maximum_input_tokens: int
    maximum_output_tokens: int
    maximum_total_tokens: int
    maximum_cost_exposure_usd: Decimal
    authority_ref: str
    availability_snapshot_ref: str
    capability_policy: AstraAdapterCapabilityPolicy
    registered_by_default: bool = False

    def __post_init__(self) -> None:
        if not ASTRA_EXECUTABLE_ROUTE_QUALIFIED:
            raise AstraRouteReadinessError(
                ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON
                + ": "
                + ", ".join(ASTRA_REMAINING_INTEGRATION_REQUIREMENTS)
            )
        if self.registered_by_default:
            raise AstraRouteReadinessError(
                "an explicit Astra route plan cannot register itself"
            )

    def safe_summary(self) -> dict[str, object]:
        return {
            "record_type": "astra_explicit_route_plan/v1",
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "demand_id": self.demand_id,
            "model_purpose": self.model_purpose,
            "route": self.route.name,
            "provider": self.provider.provider_id,
            "model": self.route.model,
            "credential_ref": self.provider.credential_ref,
            "reasoning_effort": self.reasoning_effort,
            "maximum_model_calls": self.maximum_model_calls,
            "maximum_input_tokens": self.maximum_input_tokens,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_total_tokens": self.maximum_total_tokens,
            "maximum_cost_exposure_usd": str(self.maximum_cost_exposure_usd),
            "authority_ref": self.authority_ref,
            "availability_snapshot_ref": self.availability_snapshot_ref,
            "structured_output_adapter_qualified": (
                self.capability_policy.structured_output.adapter_qualified
            ),
            "tool_calling_adapter_qualified": (
                self.capability_policy.tool_calling.adapter_qualified
            ),
            "async_tool_calling_adapter_qualified": (
                self.capability_policy.async_tool_calling.adapter_qualified
            ),
            "registered_by_default": False,
            "provider_calls_made": 0,
            "credential_reads": 0,
            "executable_route_qualified": ASTRA_EXECUTABLE_ROUTE_QUALIFIED,
        }


def build_explicit_astra_route_plan(
    request: AstraRouteReadinessRequest,
    decision: AstraReadinessDecision,
    adapter: object,
) -> AstraRoutePlan:
    """Refuse compilation while preserving reviewed dormant binding code."""
    if not isinstance(request, AstraRouteReadinessRequest):
        raise AstraRouteReadinessError(
            "route planning requires AstraRouteReadinessRequest"
        )
    if not isinstance(decision, AstraReadinessDecision):
        raise AstraRouteReadinessError("route planning requires AstraReadinessDecision")
    if decision.request_id != request.request_id:
        raise AstraRouteReadinessError(
            "readiness decision does not belong to this request"
        )
    if decision.request_digest != request.content_digest:
        raise AstraRouteReadinessError(
            "readiness decision request digest does not match this request"
        )
    expected_decision = assess_astra_route_readiness(request)
    if decision != expected_decision:
        raise AstraRouteReadinessError(
            "readiness decision does not match the current request facts"
        )
    if type(adapter) is not OpenAIResponsesAdapter:
        raise AstraRouteReadinessError(
            "route planning requires the exact quarantined OpenAIResponsesAdapter"
        )
    if getattr(adapter, "DEFAULT_MODEL", None) != DEFAULT_MODEL:
        raise AstraRouteReadinessError("adapter does not pin the exact Astra model")
    if getattr(adapter, "WIRE_FORMAT", None) != WIRE_FORMAT:
        raise AstraRouteReadinessError(
            "adapter does not implement the Responses wire format"
        )
    if getattr(adapter, "reasoning_effort", None) != decision.reasoning_effort:
        raise AstraRouteReadinessError(
            "adapter reasoning effort does not match the versioned policy"
        )
    if not ASTRA_EXECUTABLE_ROUTE_QUALIFIED:
        raise AstraRouteReadinessError(
            ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON
            + ": "
            + ", ".join(ASTRA_REMAINING_INTEGRATION_REQUIREMENTS)
        )
    if not decision.ready:
        raise AstraRouteReadinessError(
            "a refused Astra readiness decision has no executable plan"
        )
    capability = MODEL_OUTPUT_CAPABILITIES[DEFAULT_MODEL]
    route_capabilities = ModelProviderCapabilities(
        provider=PROVIDER_ID,
        locality="cloud",
        tokens_provider_reported=True,
        supports_structured_output=(
            request.adapter_capabilities.structured_output.adapter_qualified
        ),
        supports_tool_calls=(
            request.adapter_capabilities.tool_calling.adapter_qualified
        ),
        max_context=ASTRA_CONTEXT_WINDOW_TOKENS,
    )
    route = ModelRoute(
        name=ASTRA_ROUTE_NAME,
        provider=PROVIDER_ID,
        model=DEFAULT_MODEL,
        locality="cloud",
        purposes=request.demand.requested_route_purposes,
        capabilities=route_capabilities,
    )
    provider = ProviderSpec(
        provider_id=PROVIDER_ID,
        adapter=adapter,
        adapter_type=WIRE_FORMAT,
        credential_ref=ASTRA_CREDENTIAL_REF,
        locality="cloud",
        tokens_provider_reported=True,
        wire_format=WIRE_FORMAT,
        endpoint=API_URL,
        capabilities=tuple(PROVIDER_CAPABILITIES),
        model_output_capability=capability,
        model_output_capability_model=DEFAULT_MODEL,
    )
    return AstraRoutePlan(
        request_id=request.request_id,
        request_digest=request.content_digest,
        demand_id=request.demand.demand_id,
        model_purpose=request.demand.model_purpose,
        route=route,
        provider=provider,
        reasoning_effort=decision.reasoning_effort,
        maximum_model_calls=request.demand.maximum_model_calls,
        maximum_input_tokens=request.demand.maximum_input_tokens,
        maximum_output_tokens=request.demand.maximum_output_tokens,
        maximum_total_tokens=request.demand.maximum_total_tokens,
        maximum_cost_exposure_usd=decision.cost_exposure.maximum_cost_usd,
        authority_ref=request.authority.authority_id,
        availability_snapshot_ref=decision.availability_snapshot_ref,
        capability_policy=request.adapter_capabilities,
    )
