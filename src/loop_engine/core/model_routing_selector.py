"""Deterministic bootstrap selection for configured model routes.

The selector applies typed hard constraints before explainable ranking. It
never invokes an adapter. Selected decisions translate into the existing
ModelGatewayConfig, which keeps ModelGateway as the only invocation boundary.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Sequence

from .model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelRouteAttemptSpec,
    ProviderSpec,
)
from .model_routes import PURPOSES, ModelRoute
from .model_routing_records import (
    DECISION_STATES,
    MODEL_ROUTING_PORTFOLIO,
    MODEL_ROUTING_SCHEMA_VERSION,
    THINKING_POWER,
    ModelCapabilityRecord,
    ModelRouteAvailabilitySnapshot,
    ModelRoutingError,
    ModelRoutingPortfolioDefinition,
    ModelSelectionRequest,
    ModelSuitabilityRecord,
    _pairs,
    _parse_time,
    _safe_dict,
    _seal,
)
from .runtime_settings import RuntimeSettings

@dataclass(frozen=True)
class HardConstraintResult:
    route_id: str
    constraint: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RejectedRoute:
    route_id: str
    provider_id: str
    exact_model_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RouteCandidateAssessment:
    route_id: str
    provider_id: str
    exact_model_id: str
    locality: str
    thinking_power: str
    capability_record_ref: str
    availability_snapshot_ref: str
    suitability_evidence_refs: tuple[str, ...]
    expected_quality: float | None
    expected_latency_seconds: float | None
    expected_cost: float | None
    expected_risk: str
    score_contributions: tuple[tuple[str, float], ...]
    rank_score: float


@dataclass(frozen=True)
class ModelSelectionDecision:
    """Explainable selector output. It contains no provider response."""

    decision_id: str
    request_ref: str
    status: str
    model_purpose: str
    selected_route: str = ""
    selected_provider: str = ""
    selected_model: str = ""
    selected_thinking_power: str = ""
    selected_reasoning_controls: tuple[str, ...] = ()
    candidate_routes: tuple[RouteCandidateAssessment, ...] = ()
    rejected_routes: tuple[RejectedRoute, ...] = ()
    hard_constraint_results: tuple[HardConstraintResult, ...] = ()
    suitability_evidence_refs: tuple[str, ...] = ()
    availability_snapshot_ref: str = ""
    expected_quality: float | None = None
    expected_latency: float | None = None
    expected_cost: float | None = None
    expected_risk: str = ""
    confidence: float = 0.0
    same_tier_failover_plan: tuple[str, ...] = ()
    escalation_plan: tuple[str, ...] = ()
    verifier_requirement: str = ""
    human_gate: str = ""
    policy_version: str = MODEL_ROUTING_SCHEMA_VERSION
    intelligence_portfolio_snapshot_ref: str = ""
    provider_calls_made: int = 0
    decision_digest: str = ""

    def __post_init__(self) -> None:
        if self.status not in DECISION_STATES:
            raise ModelRoutingError(f"status must be one of {DECISION_STATES}")
        if self.model_purpose not in PURPOSES:
            raise ModelRoutingError("decision has an unknown model purpose")
        if self.provider_calls_made != 0:
            raise ModelRoutingError(
                "bootstrap selection must not make a provider call")
        selected = bool(self.selected_route)
        if (self.status == "selected") != selected:
            raise ModelRoutingError(
                "only a selected decision may contain a selected route")
        if selected and not all((
                self.selected_provider, self.selected_model,
                self.selected_thinking_power)):
            raise ModelRoutingError("a selected route needs exact identity")
        _seal(self, "decision_digest")

    @property
    def no_model_required(self) -> bool:
        return self.status == "no_model_required"

    def to_gateway_config(self, *, max_route_attempts: int | None = None
                          ) -> ModelGatewayConfig:
        """Translate a selected decision into the existing gateway contract."""
        if self.status != "selected":
            raise ModelRoutingError(
                "only a selected model decision has a gateway configuration")
        route_names = (self.selected_route, *self.same_tier_failover_plan)
        if max_route_attempts is not None:
            if max_route_attempts < 1:
                raise ModelRoutingError("max_route_attempts must be positive")
            route_names = route_names[:max_route_attempts]
        plan = tuple(ModelRouteAttemptSpec(
            route_name, self.selected_thinking_power) for route_name in route_names)
        return ModelGatewayConfig(
            purpose=self.model_purpose,
            route_plan=plan,
            thinking_power=self.selected_thinking_power,
            allowed_localities=tuple(dict.fromkeys(
                candidate.locality for candidate in self.candidate_routes)),
            allow_failover=len(plan) > 1,
            max_route_attempts=len(plan),
        )

    def to_dict(self) -> dict:
        value = _safe_dict(self)
        value["no_model_required"] = self.no_model_required
        return value



def _estimate_cost(
    capability: ModelCapabilityRecord,
    request: ModelSelectionRequest,
) -> float | None:
    if (capability.input_cost_per_million is None
            or capability.output_cost_per_million is None):
        return None
    return (
        request.input_context_estimate * capability.input_cost_per_million
        + request.expected_output_estimate * capability.output_cost_per_million
    ) / 1_000_000.0


def _weighted(records: Sequence[ModelSuitabilityRecord], name: str
              ) -> float | None:
    if not records:
        return None
    total = sum(record.trial_count for record in records)
    return sum(getattr(record, name) * record.trial_count
               for record in records) / total


def _distribution_median(
    records: Sequence[ModelSuitabilityRecord], name: str,
) -> float | None:
    values = [value for record in records for value in getattr(record, name)]
    return float(median(values)) if values else None


@dataclass(frozen=True)
class ModelRouteCatalog:
    """Passive exact route and provider inputs for deterministic selection."""

    routes: tuple[ModelRoute, ...]
    providers: tuple[ProviderSpec, ...]

    @classmethod
    def from_gateway(cls, gateway: ModelGateway) -> "ModelRouteCatalog":
        """Snapshot configured identities without invoking any provider."""
        if not isinstance(gateway, ModelGateway):
            raise ModelRoutingError("route catalog requires ModelGateway")
        return cls(
            routes=tuple(gateway.registry.all()),
            providers=tuple(gateway.providers.values()),
        )


@dataclass(frozen=True)
class ModelRoutingEvidence:
    """Passive reviewed evidence supplied to one selector instance."""

    capability_records: tuple[ModelCapabilityRecord, ...] = ()
    suitability_records: tuple[ModelSuitabilityRecord, ...] = ()
    availability_snapshots: tuple[ModelRouteAvailabilitySnapshot, ...] = ()


@dataclass(frozen=True)
class ModelSelectorConfig:
    """Passive policy and settings contract for deterministic selection."""

    settings: RuntimeSettings
    portfolio: ModelRoutingPortfolioDefinition = MODEL_ROUTING_PORTFOLIO

    def __post_init__(self) -> None:
        if not isinstance(self.settings, RuntimeSettings):
            raise ModelRoutingError(
                "ModelSelectorConfig.settings must be RuntimeSettings")
        if not isinstance(self.portfolio, ModelRoutingPortfolioDefinition):
            raise ModelRoutingError(
                "ModelSelectorConfig.portfolio has the wrong contract")


class ModelRouteBootstrapSelector:
    """Deterministic, non-recursive hard filter and evidence-aware ranker."""

    def __init__(
        self,
        catalog: ModelRouteCatalog,
        evidence: ModelRoutingEvidence,
        config: ModelSelectorConfig,
    ) -> None:
        if not isinstance(catalog, ModelRouteCatalog):
            raise ModelRoutingError("selector requires ModelRouteCatalog")
        if not isinstance(evidence, ModelRoutingEvidence):
            raise ModelRoutingError("selector requires ModelRoutingEvidence")
        if not isinstance(config, ModelSelectorConfig):
            raise ModelRoutingError("selector requires ModelSelectorConfig")
        self.routes = catalog.routes
        self.providers = self._unique(
            catalog.providers, lambda item: item.provider_id, "provider")
        self.capabilities = self._unique(
            evidence.capability_records,
            lambda item: item.route_id, "capability route")
        self.availability = self._unique(
            evidence.availability_snapshots, lambda item: item.route_ref,
            "availability route",
        )
        self.suitability = evidence.suitability_records
        self.settings = config.settings
        self.portfolio = config.portfolio
        route_names = [route.name for route in self.routes]
        if len(route_names) != len(set(route_names)):
            raise ModelRoutingError("route names must be unique")

    @staticmethod
    def _unique(values: Sequence[object], key, name: str) -> dict:
        result = {}
        for value in values:
            identity = key(value)
            if identity in result:
                raise ModelRoutingError(f"duplicate {name} {identity!r}")
            result[identity] = value
        return result

    @classmethod
    def from_gateway(
        cls,
        gateway: ModelGateway,
        evidence: ModelRoutingEvidence,
        config: ModelSelectorConfig,
    ) -> "ModelRouteBootstrapSelector":
        """Read route data from ``ModelGateway`` without invoking a provider."""
        return cls(
            ModelRouteCatalog.from_gateway(gateway), evidence, config,
        )

    def _thinking_power(self, route_id: str,
                        capability: ModelCapabilityRecord) -> str:
        for tier in self.settings.models.tiers:
            if route_id in tier.routes:
                return tier.name
        return capability.thinking_power

    def _effective_localities(self, request: ModelSelectionRequest) -> tuple[str, ...]:
        operating = ModelGatewayConfig.from_operating_profile(
            self.settings.operating).allowed_localities
        return tuple(value for value in request.allowed_localities
                     if value in operating)

    def _applicable_suitability(
        self,
        route_id: str,
        request: ModelSelectionRequest,
        capability: ModelCapabilityRecord,
        at: datetime,
    ) -> tuple[tuple[ModelSuitabilityRecord, ...], tuple[str, ...]]:
        applicable: list[ModelSuitabilityRecord] = []
        rejected: list[str] = []
        for record in self.suitability:
            if record.route_ref != route_id:
                continue
            ok, reasons = record.applicability(request, capability, at)
            if ok:
                applicable.append(record)
            else:
                rejected.append(f"{record.record_id}:{','.join(reasons)}")
        return tuple(applicable), tuple(rejected)

    def _hard_screen(
        self,
        route: ModelRoute,
        request: ModelSelectionRequest,
        at: datetime,
    ) -> tuple[
        tuple[HardConstraintResult, ...],
        ModelCapabilityRecord | None,
        ModelRouteAvailabilitySnapshot | None,
        tuple[ModelSuitabilityRecord, ...],
    ]:
        results: list[HardConstraintResult] = []

        def check(name: str, passed: bool, detail: str) -> None:
            results.append(HardConstraintResult(route.name, name, passed, detail))

        check(
            "run_mode_allows_model", request.run_mode != "deterministic",
            "deterministic mode cannot invoke a model",
        )
        check(
            "route_allowlist", not request.allowed_routes
            or route.name in request.allowed_routes,
            "route is outside the request allowlist",
        )
        check(
            "route_denylist", route.name not in request.forbidden_routes,
            "route is forbidden by request policy",
        )
        check(
            "purpose", request.model_purpose in route.purposes,
            "route does not declare the requested gateway purpose",
        )
        provider = self.providers.get(route.provider)
        check(
            "provider_configured", provider is not None,
            "no ProviderSpec is configured for this route",
        )
        configured_ids = set(self.settings.models.enabled_provider_ids())
        check(
            "provider_enabled", route.provider in configured_ids,
            "RuntimeSettings does not enable this provider",
        )
        check(
            "provider_allowlist", not request.allowed_providers
            or route.provider in request.allowed_providers,
            "provider is outside the request allowlist",
        )
        check(
            "provider_denylist", route.provider not in request.forbidden_providers,
            "provider is forbidden by request policy",
        )
        localities = self._effective_localities(request)
        check(
            "locality", route.locality in localities,
            "route locality is not permitted by both request and RuntimeSettings",
        )
        check(
            "provider_route_locality_match",
            provider is not None and provider.locality == route.locality,
            "ProviderSpec and ModelRoute locality differ",
        )

        capability = self.capabilities.get(route.name)
        check(
            "capability_record", capability is not None,
            "no reviewed technical capability record exists",
        )
        if capability is not None:
            check(
                "exact_identity",
                capability.provider_id == route.provider
                and capability.exact_model_id == route.model
                and capability.locality == route.locality,
                "capability identity does not match the exact route",
            )
            check(
                "deployment_identity", bool(capability.deployment_digest),
                "the exact deployment identity is unknown",
            )
            reviewed = capability.verification_state in ("reviewed", "verified")
            check(
                "capability_governance",
                reviewed or request.allow_unreviewed_capability_for_experiment,
                "capability is not reviewed; only an explicit experiment may use it",
            )
            check(
                "capability_freshness", capability.is_current(at),
                "capability record is expired or not yet valid",
            )
            check(
                "operator", request.operator in capability.supported_operators,
                "operator is not declared for this deployment",
            )
            check(
                "response_topology",
                request.response_topology
                in capability.supported_response_topologies,
                "response topology is not declared for this deployment",
            )
            check(
                "modalities",
                set(request.required_modalities).issubset(capability.modalities),
                "required modality is not declared",
            )
            tools_ok = (not request.required_tools
                        or (capability.tool_calling is True
                            and set(request.required_tools).issubset(
                                capability.supported_tools)))
            check("tools", tools_ok, "required tool calling is not declared")
            check(
                "structured_output",
                not request.structured_output_required
                or capability.structured_output is True,
                "structured output is required but not declared",
            )
            check(
                "context_limit",
                capability.context_limit is not None
                and capability.context_limit >= request.input_context_estimate,
                "context capability is unknown or too small",
            )
            check(
                "output_limit",
                capability.maximum_output is not None
                and capability.maximum_output >= request.expected_output_estimate,
                "output capability is unknown or too small",
            )
            if (provider is not None
                    and provider.model_output_capability is not None
                    and provider.model_output_capability_model == route.model):
                check(
                    "provider_output_capability_match",
                    provider.model_output_capability.maximum_output_tokens
                    == capability.maximum_output,
                    "ProviderSpec output maximum conflicts with the record",
                )
            estimated_cost = _estimate_cost(capability, request)
            ceiling = request.cost_ceiling
            operating_ceiling = self.settings.operating.limits.model_cost
            if ceiling is None:
                ceiling = operating_ceiling
            elif operating_ceiling is not None:
                ceiling = min(ceiling, operating_ceiling)
            check(
                "cost_ceiling",
                ceiling is None
                or (estimated_cost is not None and estimated_cost <= ceiling),
                "cost is unknown or exceeds the effective hard ceiling",
            )
        availability = self.availability.get(route.name)
        check(
            "availability_snapshot", availability is not None,
            "no current runtime availability snapshot exists",
        )
        if availability is not None:
            check(
                "availability_identity",
                availability.provider_id == route.provider
                and availability.exact_model_id == route.model
                and (capability is None or not availability.deployment_digest
                     or availability.deployment_digest
                     == capability.deployment_digest),
                "availability identity does not match the exact deployment",
            )
            check(
                "availability_freshness", availability.is_fresh(at),
                "availability snapshot is stale",
            )
            check(
                "route_usable", availability.usable(at),
                "endpoint, model, or credential is unavailable",
            )

        applicable: tuple[ModelSuitabilityRecord, ...] = ()
        rejected_evidence: tuple[str, ...] = ()
        if capability is not None:
            applicable, rejected_evidence = self._applicable_suitability(
                route.name, request, capability, at)
        evidence_required = (request.require_suitability_evidence
                             and not request.allow_unmeasured_route_for_experiment)
        check(
            "suitability_scope", bool(applicable) or not evidence_required,
            "no applicable reviewed suitability evidence"
            + (f" ({'; '.join(rejected_evidence)})" if rejected_evidence else ""),
        )
        if request.reliability_target is not None:
            reliability = _weighted(applicable, "verification_pass_rate")
            check(
                "reliability_target",
                reliability is not None and reliability >= request.reliability_target,
                "measured verification reliability is unknown or too low",
            )
        return tuple(results), capability, availability, applicable

    def _rank(
        self,
        route: ModelRoute,
        request: ModelSelectionRequest,
        capability: ModelCapabilityRecord,
        availability: ModelRouteAvailabilitySnapshot,
        suitability: Sequence[ModelSuitabilityRecord],
    ) -> RouteCandidateAssessment:
        success = _weighted(suitability, "success_rate")
        schema = _weighted(suitability, "schema_validity")
        verification = _weighted(suitability, "verification_pass_rate")
        stability = _weighted(suitability, "stability")
        confidence = _weighted(suitability, "confidence")
        latency = _distribution_median(suitability, "latency_distribution")
        observed_cost = _distribution_median(suitability, "cost_distribution")
        estimated_cost = _estimate_cost(capability, request)
        cost = observed_cost if observed_cost is not None else estimated_cost

        quality = success
        latency_fit = 0.5
        if request.latency_target_seconds is not None and latency is not None:
            latency_fit = min(1.0, request.latency_target_seconds
                              / max(latency, 0.000001))
        elif latency is not None:
            latency_fit = 1.0 / (1.0 + latency)
        cost_fit = 0.5
        if request.cost_ceiling is not None and cost is not None:
            cost_fit = max(0.0, 1.0 - cost / max(
                request.cost_ceiling, 0.000001))
        elif cost is not None:
            cost_fit = 1.0 / (1.0 + cost)
        locality_fit = 0.5
        if request.preferred_localities and route.locality in request.preferred_localities:
            locality_fit = 1.0 - (
                request.preferred_localities.index(route.locality)
                / max(1, len(request.preferred_localities)))
        provider_fit = 0.5
        if request.preferred_providers and route.provider in request.preferred_providers:
            provider_fit = 1.0 - (
                request.preferred_providers.index(route.provider)
                / max(1, len(request.preferred_providers)))
        power = self._thinking_power(route.name, capability)
        power_fit = 1.0 if request.preferred_thinking_power == power else 0.5
        counterevidence = sum(len(record.counterevidence) for record in suitability)
        counterevidence_fit = 1.0 / (1.0 + counterevidence)
        contributions = _pairs((
            ("measured_success", 0.0 if success is None else success),
            ("schema_validity", 0.0 if schema is None else schema),
            ("verification_pass_rate", 0.0 if verification is None else verification),
            ("stability", 0.0 if stability is None else stability),
            ("evidence_confidence", 0.0 if confidence is None else confidence),
            ("latency_fit", latency_fit),
            ("cost_fit", cost_fit),
            ("locality_preference", locality_fit),
            ("provider_preference", provider_fit),
            ("thinking_power_fit", power_fit),
            ("counterevidence", counterevidence_fit),
        ), "score_contributions")
        weights = {
            "measured_success": 0.20,
            "schema_validity": 0.12,
            "verification_pass_rate": 0.18,
            "stability": 0.10,
            "evidence_confidence": 0.10,
            "latency_fit": 0.08,
            "cost_fit": 0.07,
            "locality_preference": 0.05,
            "provider_preference": 0.03,
            "thinking_power_fit": 0.03,
            "counterevidence": 0.04,
        }
        score = sum(weights[name] * value for name, value in contributions)
        return RouteCandidateAssessment(
            route_id=route.name,
            provider_id=route.provider,
            exact_model_id=route.model,
            locality=route.locality,
            thinking_power=power,
            capability_record_ref=capability.record_id,
            availability_snapshot_ref=availability.snapshot_id,
            suitability_evidence_refs=tuple(
                record.record_id for record in suitability),
            expected_quality=quality,
            expected_latency_seconds=latency,
            expected_cost=cost,
            expected_risk=request.consequence,
            score_contributions=contributions,
            rank_score=round(score, 9),
        )

    def select(self, request: ModelSelectionRequest, *, as_of: str = ""
               ) -> ModelSelectionDecision:
        """Filter every route before ranking and return a call-free decision."""
        at = (_parse_time(as_of, "as_of") if as_of
              else datetime.now(timezone.utc))
        decision_seed = f"{request.request_id}|{at.isoformat()}"
        decision_id = "model-selection:" + hashlib.sha256(
            decision_seed.encode("utf-8")).hexdigest()[:20]
        if request.deterministic_sufficient:
            snapshot = "deterministic-evidence:" + hashlib.sha256(
                "|".join(request.deterministic_evidence_refs).encode("utf-8")
            ).hexdigest()
            return ModelSelectionDecision(
                decision_id=decision_id,
                request_ref=request.request_id,
                status="no_model_required",
                model_purpose=request.model_purpose,
                verifier_requirement=request.verification_plan,
                intelligence_portfolio_snapshot_ref=snapshot,
            )

        hard_results: list[HardConstraintResult] = []
        rejected: list[RejectedRoute] = []
        candidates: list[RouteCandidateAssessment] = []
        for route in self.routes:
            results, capability, availability, suitability = self._hard_screen(
                route, request, at)
            hard_results.extend(results)
            failed = tuple(result.constraint for result in results
                           if not result.passed)
            if failed or capability is None or availability is None:
                rejected.append(RejectedRoute(
                    route.name, route.provider, route.model, failed))
                continue
            candidates.append(self._rank(
                route, request, capability, availability, suitability))

        candidates.sort(key=lambda item: (-item.rank_score, item.route_id))
        snapshot_payload = {
            "portfolio": self.portfolio.record_id,
            "request": request.request_id,
            "capabilities": [candidate.capability_record_ref
                             for candidate in candidates],
            "suitability": [ref for candidate in candidates
                            for ref in candidate.suitability_evidence_refs],
            "availability": [candidate.availability_snapshot_ref
                             for candidate in candidates],
        }
        snapshot_ref = "model-routing-snapshot:sha256:" + hashlib.sha256(
            json.dumps(snapshot_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if not candidates:
            return ModelSelectionDecision(
                decision_id=decision_id,
                request_ref=request.request_id,
                status="abstained",
                model_purpose=request.model_purpose,
                rejected_routes=tuple(rejected),
                hard_constraint_results=tuple(hard_results),
                verifier_requirement=request.verification_plan,
                human_gate=("required" if request.consequence in (
                    "high", "critical") else ""),
                intelligence_portfolio_snapshot_ref=snapshot_ref,
            )

        selected = candidates[0]
        same_tier = tuple(
            candidate.route_id for candidate in candidates[1:]
            if candidate.thinking_power == selected.thinking_power
        ) if request.failover_policy == "same_tier" else ()
        power_order = {value: index for index, value in enumerate(THINKING_POWER)}
        escalation = tuple(
            candidate.route_id for candidate in candidates[1:]
            if candidate.thinking_power != "specialized"
            and power_order[candidate.thinking_power]
            > power_order[selected.thinking_power]
        ) if request.escalation_policy == "configured" else ()
        confidence = _weighted(
            tuple(record for record in self.suitability
                  if record.record_id in selected.suitability_evidence_refs),
            "confidence",
        )
        capability = self.capabilities[selected.route_id]
        return ModelSelectionDecision(
            decision_id=decision_id,
            request_ref=request.request_id,
            status="selected",
            model_purpose=request.model_purpose,
            selected_route=selected.route_id,
            selected_provider=selected.provider_id,
            selected_model=selected.exact_model_id,
            selected_thinking_power=selected.thinking_power,
            selected_reasoning_controls=capability.reasoning_controls,
            candidate_routes=tuple(candidates),
            rejected_routes=tuple(rejected),
            hard_constraint_results=tuple(hard_results),
            suitability_evidence_refs=selected.suitability_evidence_refs,
            availability_snapshot_ref=selected.availability_snapshot_ref,
            expected_quality=selected.expected_quality,
            expected_latency=selected.expected_latency_seconds,
            expected_cost=selected.expected_cost,
            expected_risk=selected.expected_risk,
            confidence=0.0 if confidence is None else confidence,
            same_tier_failover_plan=same_tier,
            escalation_plan=escalation,
            verifier_requirement=request.verification_plan,
            human_gate=("required" if request.consequence in (
                "high", "critical") else ""),
            intelligence_portfolio_snapshot_ref=snapshot_ref,
        )
