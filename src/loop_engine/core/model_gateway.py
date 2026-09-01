"""One provider-neutral gateway for every semantic model invocation.

Architectural role: internal model execution service.

The gateway accepts one typed request, resolves provider and model routes,
applies route policy and budgets, gives every physical provider attempt its own
model loop, validates output, and returns one provider-independent result.

Provider adapters expose the same small protocol. Built-in specifications cover
Ollama Cloud, Mistral, and OpenRouter. A custom endpoint adapter can be supplied
without changing the gateway.

This module does not discover credentials, assemble prompts, choose a problem
solving method, or approve spend. Those inputs must be resolved before invoke.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from .model_capabilities import (
    ModelOutputCapability, ModelOutputLimitMismatch, UnknownModelOutputLimit,
    require_declared_maximum,
)
from .model_routes import (LOCALITIES, PURPOSES, ModelRoute, RoutePolicy,
                           RouteRegistry, screen_route)
from .model_response_text import extract_final_answer


class ProviderAdapter(Protocol):
    """The executable contract every model provider adapter implements."""
    DEFAULT_MODEL: str
    def chat_maxout(self, prompt: str, *, model: str = "", system: str = "",
                    temperature: float = 0.7, timeout: float = 900.0,
                    max_attempts: int = 1,
                    max_output_tokens: "int | None" = None,
                    output_capability: "ModelOutputCapability | None" = None): ...

    def verify(self, model: str = ""): ...
    def live_models(self): ...
    def output_capability_for(self, model: str): ...

@dataclass(frozen=True)
class ProviderSpec:
    """A configured provider plus non-secret facts about the connection."""
    provider_id: str
    adapter: object
    adapter_type: str
    credential_ref: str
    locality: str = "cloud"
    tokens_provider_reported: bool = True
    wire_format: str = "provider_native"
    endpoint: str = ""
    capabilities: tuple[str, ...] = ()
    model_output_capability: "ModelOutputCapability | None" = None
    model_output_capability_model: str = ""
    def __post_init__(self):
        if not self.provider_id:
            raise ValueError("ProviderSpec needs provider_id")
        if self.locality not in LOCALITIES:
            raise ValueError(f"provider locality must be one of {LOCALITIES}")
        required = ("chat_maxout", "verify", "live_models",
                    "output_capability_for", "DEFAULT_MODEL")
        missing = [name for name in required if not hasattr(self.adapter, name)]
        if missing:
            raise ValueError(
                f"provider {self.provider_id!r} misses adapter fields {missing}")
        if bool(self.model_output_capability) != bool(
                self.model_output_capability_model):
            raise ValueError(
                "a ProviderSpec model output override needs both the exact "
                "model and a ModelOutputCapability")

    def output_capability_for(self, model: str) -> ModelOutputCapability:
        if (self.model_output_capability is not None
                and model == self.model_output_capability_model):
            return self.model_output_capability
        return self.adapter.output_capability_for(model)

    def describe(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "adapter_type": self.adapter_type,
            "credential_ref": self.credential_ref,
            "locality": self.locality,
            "tokens_provider_reported": self.tokens_provider_reported,
            "wire_format": self.wire_format,
            "endpoint": self.endpoint,
            "capabilities": list(self.capabilities),
            "model_output_capability": (
                self.model_output_capability.summary()
                if self.model_output_capability else None),
            "model_output_capability_model":
                self.model_output_capability_model,
        }


def builtin_provider_specs(
        adapters: "dict[str, object] | None" = None) -> tuple[ProviderSpec, ...]:
    """Built-in providers under the common adapter contract."""
    if adapters is None:
        from . import mistral_client, ollama_client, openrouter_client
        adapters = {
            "ollama_cloud": ollama_client,
            "mistral": mistral_client,
            "openrouter": openrouter_client,
        }
    facts = {
        "ollama_cloud": ("ollama_native", "env:OLLAMA_API_KEY",
                          "https://ollama.com/api/chat"),
        "mistral": ("mistral", "env:MISTRAL_API_KEY",
                    "https://api.mistral.ai/v1/chat/completions"),
        "openrouter": ("openai_compatible", "env:OPENROUTER_API_KEY",
                       "https://openrouter.ai/api/v1/chat/completions"),
    }
    specs = []
    for provider_id, adapter in adapters.items():
        adapter_type, credential_ref, endpoint = facts.get(
            provider_id, ("custom", f"provider:{provider_id}", ""))
        custom = getattr(adapter, "endpoint", None)
        specs.append(ProviderSpec(
            provider_id=provider_id,
            adapter=adapter,
            adapter_type=adapter_type if custom is None else "custom_endpoint",
            credential_ref=credential_ref,
            locality=getattr(custom, "locality", "cloud"),
            tokens_provider_reported=(getattr(
                custom, "counts_as_evidence", True)),
            wire_format=getattr(custom, "wire", "provider_native"),
            endpoint=getattr(custom, "base_url", endpoint),
            capabilities=("chat", "list_models", "verify"),
        ))
    return tuple(specs)


def provider_spec_from_endpoint(endpoint) -> ProviderSpec:
    """Build an isolated provider specification from a CustomEndpoint."""
    from .custom_endpoint import make_adapter
    return ProviderSpec(
        provider_id=endpoint.name,
        adapter=make_adapter(endpoint),
        adapter_type="custom_endpoint",
        credential_ref=f"custom:{endpoint.name}",
        locality=endpoint.locality,
        tokens_provider_reported=endpoint.counts_as_evidence,
        wire_format=endpoint.wire,
        endpoint=endpoint.base_url,
        capabilities=("chat", "list_models", "verify"),
        model_output_capability=endpoint.output_capability,
        model_output_capability_model=(endpoint.model
                                       if endpoint.output_capability else ""),
    )

@dataclass(frozen=True)
class ModelRouteAttemptSpec:
    """One route attempt with its model tier and bounded resources."""

    route_name: str
    thinking_power: str = "medium"
    max_output_tokens: "int | None" = None
    timeout_seconds: "float | None" = None
    def __post_init__(self):
        if not self.route_name:
            raise ValueError("a model route attempt needs route_name")
        if self.thinking_power not in (
                "small", "medium", "high", "max", "specialized"):
            raise ValueError(
                "thinking_power must be small, medium, high, max, or "
                "specialized")
        if self.max_output_tokens is not None and self.max_output_tokens < 1:
            raise ValueError("attempt max_output_tokens must be positive")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("attempt timeout_seconds must be positive")


@dataclass(frozen=True)
class ModelGatewayConfig:
    """Run-scoped provider routing and budget settings."""
    purpose: str = "counted_generation"
    route_names: tuple[str, ...] = ()
    route_plan: tuple[ModelRouteAttemptSpec, ...] = ()
    thinking_power: str = "medium"
    allowed_models: tuple[str, ...] = ()
    allowed_localities: tuple[str, ...] = LOCALITIES
    allow_failover: bool = True
    max_route_attempts: "int | None" = None
    timeout_seconds: float = 900.0
    max_output_tokens: "int | None" = None
    max_total_tokens: "int | None" = None
    allow_power_escalation: bool = False
    max_power_escalations: int = 0
    escalate_on: tuple[str, ...] = ("output_validation_failed",)

    def __post_init__(self):
        if self.purpose not in PURPOSES:
            raise ValueError("unknown model gateway purpose")
        if (self.max_route_attempts is not None
                and self.max_route_attempts < 1):
            raise ValueError(
                "max_route_attempts must be positive when provided")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if (self.max_output_tokens is not None
                and self.max_output_tokens < 1):
            raise ValueError(
                "max_output_tokens must be positive when set")
        if self.max_total_tokens is not None and self.max_total_tokens < 1:
            raise ValueError("max_total_tokens must be positive when set")
        if self.thinking_power not in (
                "small", "medium", "high", "max", "specialized"):
            raise ValueError(
                "thinking_power must be small, medium, high, max, or "
                "specialized")
        if self.max_power_escalations < 0:
            raise ValueError("max_power_escalations cannot be negative")
        if self.route_names and self.route_plan:
            raise ValueError("use route_names or route_plan, not both")
        if any(not isinstance(item, ModelRouteAttemptSpec)
               for item in self.route_plan):
            raise ValueError(
                "route_plan must contain ModelRouteAttemptSpec objects")
        if any(value not in LOCALITIES
               for value in self.allowed_localities):
            raise ValueError(f"allowed_localities accepts {LOCALITIES}")

    @classmethod
    def from_operating_profile(cls, profile, **overrides):
        """Translate the owner-facing reasoning mode into route locality."""
        mode = profile.reasoning_and_model_mode
        localities = {
            "deterministic_only": (),
            "local_only": ("local",),
            "deterministic_first_local_first": (
                "local", "organization", "cloud"),
            "approved_remote": ("organization", "cloud"),
            "best_available": ("local", "organization", "cloud"),
        }[mode]
        timeout = (profile.limits.wall_time_seconds
                   if profile.limits.wall_time_seconds is not None else 900.0)
        overrides.setdefault("timeout_seconds", timeout)
        overrides.setdefault("allowed_localities", localities)
        return cls(**overrides)


@dataclass(frozen=True)
class ModelGatewayRequest:
    prompt: str
    config: ModelGatewayConfig = field(default_factory=ModelGatewayConfig)
    system: str = ""
    temperature: float = 0.7
    output_contract: str = ""
    trace_id: str = ""
    def __post_init__(self):
        if not self.prompt.strip():
            raise ValueError("a model gateway request needs a prompt")


@dataclass(frozen=True)
class GatewayAttempt:
    provider: str
    model: str
    route: str
    loop_id: str
    ok: bool
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    validation_ok: "bool | None" = None
    error_code: str = ""
    error: str = ""
    elapsed_seconds: float = 0.0
    provider_ok: bool = False
    thinking_power: str = "medium"
    maximum_output_tokens: "int | None" = None
    maximum_output_source: str = ""
    expected_model: str = ""
    reasoning_present: bool = False
    response_received: bool = False
    provider_done: "bool | None" = None
    provider_stop_reason: str = ""
    output_limit_reached: bool = False
    usage_diagnostic: "dict | None" = None
    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "route": self.route,
            "thinking_power": self.thinking_power,
            "loop_id": self.loop_id,
            "ok": self.ok,
            "provider_ok": self.provider_ok,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "validation_ok": self.validation_ok,
            "error_code": self.error_code,
            "error": self.error[:200],
            "elapsed_seconds": self.elapsed_seconds,
            "usage_diagnostic": self.usage_diagnostic,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_output_source": self.maximum_output_source,
            "expected_model": self.expected_model,
            "reasoning_present": self.reasoning_present,
            "response_received": self.response_received,
            "provider_done": self.provider_done,
            "provider_stop_reason": self.provider_stop_reason,
            "output_limit_reached": self.output_limit_reached,
        }


@dataclass
class ModelGatewayResult:
    ok: bool = False
    text: str = ""
    provider: str = ""
    model: str = ""
    route: str = ""
    thinking_power: str = ""
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    attempts: list[GatewayAttempt] = field(default_factory=list)
    gateway_loop_id: str = ""
    error_code: str = ""
    error: str = ""
    reasoning_present: bool = False
    @property
    def total_tokens(self) -> "int | None":
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens

    @property
    def accounting_complete(self) -> bool:
        return self.input_tokens is not None and self.output_tokens is not None

    @property
    def provider_responded(self) -> bool:
        return any(attempt.provider_ok or attempt.response_received
                   for attempt in self.attempts)

    def to_dict(self) -> dict:
        return {
            "record_type": "model_gateway_result/v1",
            "ok": self.ok,
            "text": self.text,
            "provider": self.provider,
            "model": self.model,
            "route": self.route,
            "thinking_power": self.thinking_power,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "accounting_complete": self.accounting_complete,
            "provider_responded": self.provider_responded,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "gateway_loop_id": self.gateway_loop_id,
            "error_code": self.error_code,
            "error": self.error[:200],
            "reasoning_present": self.reasoning_present,
        }


def _error_code(error: str) -> str:
    low = str(error).lower()
    # Abrupt TLS termination: the endpoint, a reverse proxy, or an
    # intervening network closed the connection before a complete
    # HTTP/model response arrived. Transport-level, so retryable.
    if any(marker in low for marker in (
            "ssleoferror",
            "eof occurred in violation of protocol",
            "connectionreseterror",
            "connection reset by peer",
            "remotedisconnected",
            "remote end closed connection",
            "connectionaborted",
            "brokenpipeerror")):
        return "provider_unavailable"
    if ("output_limit_reached" in low or "max_tokens" in low
            or "maximum output" in low and "reached" in low):
        return "output_limit_reached"
    if ("no route to host" in low
            or "temporary failure in name resolution" in low
            or "name or service not known" in low
            or "network is unreachable" in low
            or "connection refused" in low):
        return "network_unreachable"
    if "incomplete_response" in low:
        return "incomplete_response"
    if "empty_response" in low:
        return "empty_response"
    if "unknown_model_output_limit" in low:
        return "unknown_model_output_limit"
    if "not the declared model maximum" in low:
        return "model_output_limit_mismatch"
    if "401" in low or "403" in low or "unauthor" in low or "api_key" in low:
        return "authentication_failed"
    if "402" in low or "payment required" in low or "insufficient credit" in low:
        return "payment_required"
    if "404" in low or "model not found" in low:
        return "model_not_found"
    if "429" in low or "rate" in low and "limit" in low:
        return "rate_limited"
    if (any(code in low for code in ("500", "502", "503"))
            or "service unavailable" in low or "high demand" in low):
        return "provider_unavailable"
    if "gateway_timeout" in low or " 524" in low or low.startswith("524") \
            or "504" in low:
        # A proxy cut the connection mid-generation: transport-level and
        # retryable, but a same-request retry may hit the same wall, so the
        # run should also consider a shorter output ceiling or failover.
        return "gateway_timeout"
    if "400" in low or "bad request" in low:
        return "invalid_request"
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if (("not found" in low or "missing" in low)
            and ("key" in low or "credential" in low)):
        return "missing_credential"
    if "validation" in low:
        return "output_validation_failed"
    if "model identity" in low or "model_identity" in low:
        return "model_identity_mismatch"
    return "provider_failed"


_FAILOVER_FORBIDDEN_ERRORS = {
    "authentication_failed", "invalid_request",
    "model_output_limit_mismatch", "model_identity_mismatch",
}


def _gateway_orchestration_config(parent=None):
    """Build the routing loop config without narrowing the owner's tree.

    A starting gateway keeps the historical depth limit of three. A gateway that
    is invoked by an existing Loop inherits that Loop's configured depth, so
    the routing Loop and its spawned provider attempt remain structurally below
    the named spawning Loop.
    """
    from ..loop.recursive_loop import LoopConfig

    max_depth = (parent.config.max_depth if parent is not None
                 else LoopConfig().max_depth)
    return LoopConfig(
        framework="custom", custom_steps=("route",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("non_deterministic",),
        exit_condition="steps_complete", max_depth=max_depth)


class ModelGateway:
    """Resolve and invoke providers through one loop-visible boundary."""

    def __init__(self, *, providers: "Sequence[ProviderSpec] | None" = None,
                 routes: "Sequence[ModelRoute] | None" = None,
                 policy: "RoutePolicy | None" = None):
        specs = tuple(providers or builtin_provider_specs())
        self.providers = {spec.provider_id: spec for spec in specs}
        self.registry = RouteRegistry(routes)
        self.policy = policy or RoutePolicy()

    def _routes(self, config: ModelGatewayConfig
                ) -> list[tuple[ModelRoute, ModelRouteAttemptSpec]]:
        explicit = bool(config.route_plan or config.route_names)
        if config.route_plan:
            selected = [(screen_route(
                self.registry.get(item.route_name), purpose=config.purpose,
                policy=self.policy), item) for item in config.route_plan]
        elif config.route_names:
            selected = [(screen_route(
                self.registry.get(name), purpose=config.purpose,
                policy=self.policy), ModelRouteAttemptSpec(
                    name, config.thinking_power)) for name in config.route_names]
        else:
            routes = self.registry.for_purpose(
                config.purpose, policy=self.policy)
            first_by_provider, remaining, seen = [], [], set()
            for route in routes:
                if route.provider in seen:
                    remaining.append(route)
                else:
                    first_by_provider.append(route)
                    seen.add(route.provider)
            selected = [(route, ModelRouteAttemptSpec(
                route.name, config.thinking_power))
                        for route in first_by_provider + remaining]
        if config.allowed_models:
            selected = [(route, attempt) for route, attempt in selected if any(
                route.model.startswith(model) or model in route.model
                for model in config.allowed_models)]
        selected = [(route, attempt) for route, attempt in selected
                    if route.locality in config.allowed_localities]
        if not explicit:
            locality_order = {value: index for index, value in enumerate(
                config.allowed_localities)}
            selected.sort(key=lambda pair: locality_order[pair[0].locality])
        if not config.allow_failover:
            selected = selected[:1]
        return (selected if config.max_route_attempts is None
                else selected[:config.max_route_attempts])

    def invoke(self, request: ModelGatewayRequest, *,
               validate: "Callable[[str], bool] | None" = None,
               ledger=None, parent=None) -> ModelGatewayResult:
        """Run one route at a time; every provider attempt is a model loop."""
        from ..loop.encapsulate import as_model_loop
        from ..loop.loop_role import (LoopRelationship, LoopRole,
                                     LoopRoleIdentity)
        from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

        routes = self._routes(request.config)
        if not routes:
            return ModelGatewayResult(
                ok=False, error_code="no_eligible_route",
                error="no model route is permitted by this request and policy")

        orchestration_config = _gateway_orchestration_config(parent)
        identity = LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.code_execution")
        relationship = (LoopRelationship.spawned_by(parent.loop_id)
                        if parent is not None
                        else LoopRelationship.starting())
        starting = (parent.spawn(
            "route one model request", orchestration_config,
            identity=identity, relationship=relationship)
                if parent is not None else Loop(
                    "route one model request", orchestration_config,
                    ledger=ledger, identity=identity,
                    relationship=relationship))
        result = ModelGatewayResult(gateway_loop_id=starting.loop_id)
        known_tokens = 0

        def handler(loop, step, context):
            nonlocal known_tokens
            previous_power = ""
            power_escalations = 0
            for route, attempt_spec in routes:
                current_power = attempt_spec.thinking_power
                if previous_power and current_power != previous_power:
                    previous_attempt = (result.attempts[-1]
                                        if result.attempts else None)
                    may_escalate = (
                        request.config.allow_power_escalation
                        and power_escalations
                        < request.config.max_power_escalations
                        and previous_attempt is not None
                        and previous_attempt.error_code
                        in request.config.escalate_on)
                    if not may_escalate:
                        break
                    power_escalations += 1
                    loop.ledger.record(
                        loop_id=loop.loop_id, event="custom",
                        action="model_power_escalation",
                        from_thinking_power=previous_power,
                        to_thinking_power=current_power,
                        trigger=previous_attempt.error_code)
                previous_power = current_power
                spec = self.providers.get(route.provider)
                if spec is None:
                    result.attempts.append(GatewayAttempt(
                        route.provider, route.model, route.name, "", False,
                        error_code="provider_not_configured",
                        error=f"no ProviderSpec for {route.provider!r}",
                        thinking_power=current_power))
                    continue
                started = time.monotonic()
                attempt_timeout = min(
                    request.config.timeout_seconds,
                    attempt_spec.timeout_seconds
                    or request.config.timeout_seconds)
                requested_outputs = tuple(value for value in (
                    request.config.max_output_tokens,
                    attempt_spec.max_output_tokens) if value is not None)
                if len(set(requested_outputs)) > 1:
                    error = (
                        "model_output_limit_mismatch: gateway and route "
                        "declare different output maxima")
                    result.attempts.append(GatewayAttempt(
                        route.provider, route.model, route.name, "", False,
                        error_code="model_output_limit_mismatch", error=error,
                        thinking_power=current_power))
                    continue
                requested_output = (requested_outputs[0]
                                    if requested_outputs else None)
                try:
                    output_capability = spec.output_capability_for(route.model)
                    attempt_output = require_declared_maximum(
                        requested_output, output_capability)
                except (UnknownModelOutputLimit,
                        ModelOutputLimitMismatch) as exc:
                    result.attempts.append(GatewayAttempt(
                        route.provider, route.model, route.name, "", False,
                        error_code=_error_code(str(exc)), error=str(exc),
                        thinking_power=current_power))
                    continue

                def invoke_provider(spec=spec, route=route,
                                    attempt_timeout=attempt_timeout,
                                    attempt_output=attempt_output):
                    value = spec.adapter.chat_maxout(
                        request.prompt, model=route.model,
                        system=request.system,
                        temperature=request.temperature,
                        timeout=attempt_timeout,
                        max_attempts=1,
                        max_output_tokens=attempt_output,
                        output_capability=output_capability)
                    try:
                        value.provider = route.provider
                    except (AttributeError, TypeError):
                        pass
                    return value

                call = as_model_loop(
                    f"{route.provider}:{route.model}",
                    invoke_provider,
                    parent=loop,
                    llm_thinking_power=current_power)
                provider_result = call["value"]
                raw_text = str(getattr(provider_result, "text", "") or "")
                text, embedded_reasoning = extract_final_answer(raw_text)
                reasoning_present = bool(
                    embedded_reasoning
                    or getattr(provider_result, "reasoning_present", False))
                provider_done = getattr(provider_result, "done", None)
                provider_stop_reason = str(
                    getattr(provider_result, "done_reason", "") or "")
                output_limit_reached = bool(getattr(
                    provider_result, "output_limit_reached", False))
                response_received = bool(
                    getattr(provider_result, "response_received", False)
                    or raw_text.strip()
                    or getattr(provider_result, "prompt_tokens", 0)
                    or getattr(provider_result, "eval_tokens", 0)
                    or provider_done is not None)
                transport_ok = bool(getattr(provider_result, "ok", False)
                                    and raw_text.strip())
                reported_model = str(
                    getattr(provider_result, "model", "") or route.model)
                identity_ok = reported_model == route.model
                provider_ok = bool(transport_ok and text.strip() and identity_ok)
                validation_error = ""
                try:
                    validation_ok = (
                        validate(text) if provider_ok and validate is not None
                        else provider_ok)
                except Exception as exc:  # noqa: BLE001
                    validation_ok = False
                    validation_error = (
                        f"output validation raised {type(exc).__name__}")
                raw_in = int(getattr(provider_result, "prompt_tokens", 0) or 0)
                raw_out = int(getattr(provider_result, "eval_tokens", 0) or 0)
                usage_known = bool(raw_in or raw_out)
                input_tokens = raw_in if usage_known else None
                output_tokens = raw_out if usage_known else None
                if usage_known:
                    known_tokens += raw_in + raw_out
                # A real response with no provider-reported usage is an
                # accounting anomaly worth a typed record: the diagnostic
                # carries a clearly-labeled rough estimate, while the
                # accounting fields stay None (unknown, never fabricated).
                usage_diagnostic = None
                if not usage_known and response_received and raw_text.strip():
                    usage_diagnostic = {
                        "record_type": "usage_accounting_unavailable/v1",
                        "reason": (
                            "provider returned a response without token "
                            "usage; accounting remains unknown"),
                        "estimated_output_tokens": max(1, len(raw_text) // 4),
                        "estimate_basis": (
                            "rough characters-over-four diagnostic estimate; "
                            "not provider accounting and never reported as "
                            "usage"),
                    }
                error = str(getattr(provider_result, "error", "") or "")
                if output_limit_reached:
                    error = error or (
                        "output_limit_reached: provider response reached its "
                        "declared output ceiling")
                elif response_received and provider_done is False:
                    error = error or (
                        "incomplete_response: provider response did not finish")
                elif transport_ok and not identity_ok:
                    error = (
                        "model_identity_mismatch: requested exact model "
                        f"{route.model!r}, provider reported {reported_model!r}")
                elif response_received and reasoning_present and not text:
                    error = (
                        "output_validation_failed: response contained no safe "
                        "final answer outside private reasoning")
                if provider_ok and not validation_ok:
                    error = validation_error or "output failed validation"
                attempt = GatewayAttempt(
                    provider=route.provider,
                    model=reported_model,
                    route=route.name,
                    loop_id=call["loop_id"],
                    ok=bool(provider_ok and validation_ok),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    validation_ok=validation_ok if provider_ok else None,
                    error_code="" if provider_ok and validation_ok
                    else _error_code(error),
                    error=error,
                    elapsed_seconds=round(time.monotonic() - started, 6),
                    provider_ok=transport_ok,
                    thinking_power=current_power,
                    maximum_output_tokens=attempt_output,
                    maximum_output_source=output_capability.source,
                    expected_model=route.model,
                    reasoning_present=reasoning_present,
                    response_received=response_received,
                    provider_done=provider_done,
                    provider_stop_reason=provider_stop_reason,
                    output_limit_reached=output_limit_reached,
                    usage_diagnostic=usage_diagnostic,
                )
                result.attempts.append(attempt)
                if (not attempt.ok
                        and attempt.error_code in _FAILOVER_FORBIDDEN_ERRORS):
                    result.error_code = attempt.error_code
                    result.error = attempt.error
                    return StepOutcome(
                        output=f"route:refused:{attempt.error_code}",
                        mode="deterministic", confidence=0.1, failed=True)
                if (request.config.max_total_tokens is not None
                        and known_tokens > request.config.max_total_tokens):
                    result.error_code = "token_budget_exhausted"
                    result.error = (
                        f"{known_tokens} provider-reported tokens exceed "
                        f"the {request.config.max_total_tokens} token budget")
                    return StepOutcome(
                        output="route:token_budget_exhausted",
                        mode="deterministic", confidence=0.1, failed=True)
                if attempt.ok:
                    result.ok = True
                    result.text = text
                    result.provider = attempt.provider
                    result.model = attempt.model
                    result.route = attempt.route
                    result.thinking_power = attempt.thinking_power
                    result.input_tokens = attempt.input_tokens
                    result.output_tokens = attempt.output_tokens
                    result.reasoning_present = reasoning_present
                    return StepOutcome(
                        output=f"route:answered:{attempt.provider}",
                        mode="deterministic", confidence=1.0)
            last = result.attempts[-1] if result.attempts else None
            result.error_code = (last.error_code if last
                                 else "no_provider_attempt")
            result.error = (last.error if last
                            else "no configured provider could be attempted")
            result.thinking_power = last.thinking_power if last else ""
            return StepOutcome(output="route:all_failed", mode="deterministic",
                               confidence=0.1, failed=True)

        starting.run(handler=handler, max_steps=2)
        return result


def invoke_model_gateway(gateway: ModelGateway, request: ModelGatewayRequest,
                         **kwargs) -> ModelGatewayResult:
    """Top-level boundary function for registered gateway invocation."""
    return gateway.invoke(request, **kwargs)


def self_test() -> dict:
    """Offline contract and refusal tests.  No provider is contacted."""
    from .model_capabilities import (
        ModelOutputCapability, UnknownModelOutputLimit)
    from .ollama_client import ChatResult
    from .operating_profile import OperatingProfile

    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    class RefusalBoundary:
        """Non-executable adapter used only to prove pre-call refusal."""

        DEFAULT_MODEL = "unknown-model"

        def __init__(self):
            self.chat_attempted = False

        def output_capability_for(self, model):
            raise UnknownModelOutputLimit(
                "unknown_model_output_limit: no declared maximum")

        def chat_maxout(self, prompt, **kwargs):
            self.chat_attempted = True
            raise AssertionError("the provider boundary must not be reached")

        def verify(self, model=""):
            raise AssertionError("offline tests never verify a provider")

        def live_models(self):
            raise AssertionError("offline tests never query a provider catalog")

    boundary = RefusalBoundary()
    gateway = ModelGateway(
        providers=(ProviderSpec(
            "contract_only", boundary, "non_executable_contract",
            "env:CONTRACT_ONLY_KEY"),),
        routes=(ModelRoute(
            "contract.unknown", "contract_only", "unknown-model"),))
    refused = gateway.invoke(ModelGatewayRequest(
        "prove refusal before provider use",
        ModelGatewayConfig(
            route_names=("contract.unknown",),
            allow_failover=False, max_route_attempts=1)))
    check("unknown_output_capability_refuses_before_provider_use",
          not refused.ok
          and refused.error_code == "unknown_model_output_limit"
          and not boundary.chat_attempted
          and refused.attempts[0].loop_id == "",
          "this is a contract refusal, not a provider integration test")

    mismatch_config = False
    try:
        ModelGatewayConfig(max_output_tokens=0)
    except ValueError:
        mismatch_config = True
    check("invalid_explicit_output_values_are_refused", mismatch_config)

    safe = ProviderSpec(
        "contract_only", boundary, "non_executable_contract",
        "env:SAFE_PROVIDER_KEY")
    check("provider_descriptions_carry_references_not_secret_values",
          safe.describe()["credential_ref"] == "env:SAFE_PROVIDER_KEY")

    deterministic_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="deterministic_only"))
    local_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="local_only"))
    remote_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="approved_remote"))
    check("operating_profile_controls_gateway_route_locality",
          deterministic_config.allowed_localities == ()
          and local_config.allowed_localities == ("local",)
          and remote_config.allowed_localities == ("organization", "cloud"))

    request = ModelGatewayRequest(
        "one typed request",
        ModelGatewayConfig(
            route_plan=(ModelRouteAttemptSpec(
                "contract.unknown", "medium", None, 10.0),),
            max_route_attempts=1))
    check("an_unspecified_output_limit_remains_unspecified_until_capability_resolution",
          request.config.max_output_tokens is None
          and request.config.route_plan[0].max_output_tokens is None)

    class ErrorAdapter:
        DEFAULT_MODEL = "first-model"

        def __init__(self, error: str):
            self.error = error
            self.calls = 0

        @staticmethod
        def output_capability_for(model):
            return ModelOutputCapability(16, "fixture maximum")

        def chat_maxout(self, prompt, **kwargs):
            self.calls += 1
            return ChatResult("", kwargs.get("model", "first-model"),
                              ok=False, error=self.error)

        def verify(self, model=""):
            return {"ok": False}

        def live_models(self):
            return [self.DEFAULT_MODEL]

    class SuccessAdapter(ErrorAdapter):
        DEFAULT_MODEL = "second-model"

        def __init__(self):
            super().__init__("")

        def chat_maxout(self, prompt, **kwargs):
            self.calls += 1
            return ChatResult("accepted", kwargs.get("model", "second-model"),
                              prompt_tokens=1, eval_tokens=1, ok=True,
                              response_received=True, done=True,
                              done_reason="stop")

    class OutputLimitAdapter(ErrorAdapter):
        """A provider returned bytes, but not a complete answer."""

        def __init__(self):
            super().__init__("output_limit_reached")

        def chat_maxout(self, prompt, **kwargs):
            self.calls += 1
            return ChatResult(
                "partial", kwargs.get("model", "first-model"),
                prompt_tokens=2, eval_tokens=16, ok=False,
                error="output_limit_reached: fixture reached its ceiling",
                num_predict_used=16, response_received=True, done=True,
                done_reason="length", output_limit_reached=True)

    auth, auth_fallback = ErrorAdapter("HTTP 401 unauthorized"), SuccessAdapter()
    auth_gateway = ModelGateway(
        providers=(ProviderSpec("first", auth, "fixture", "env:FIRST"),
                   ProviderSpec("second", auth_fallback, "fixture",
                                "env:SECOND")),
        routes=(ModelRoute("first.route", "first", "first-model"),
                ModelRoute("second.route", "second", "second-model")))
    auth_result = auth_gateway.invoke(ModelGatewayRequest(
        "authentication failure must stop",
        ModelGatewayConfig(route_names=("first.route", "second.route"),
                           max_route_attempts=2)))
    check("authentication_failure_does_not_silently_fail_over",
          not auth_result.ok
          and auth_result.error_code == "authentication_failed"
          and auth.calls == 1 and auth_fallback.calls == 0)

    payment, payment_fallback = ErrorAdapter(
        "HTTP 402 insufficient credits"), SuccessAdapter()
    payment_gateway = ModelGateway(
        providers=(ProviderSpec("first", payment, "fixture", "env:FIRST"),
                   ProviderSpec("second", payment_fallback, "fixture",
                                "env:SECOND")),
        routes=(ModelRoute("first.route", "first", "first-model"),
                ModelRoute("second.route", "second", "second-model")))
    payment_result = payment_gateway.invoke(ModelGatewayRequest(
        "payment failure may use another authorized provider",
        ModelGatewayConfig(route_names=("first.route", "second.route"),
                           max_route_attempts=2)))
    check("payment_failure_can_fail_over_to_another_authorized_provider",
          payment_result.ok and payment_result.provider == "second"
          and payment_result.attempts[0].error_code == "payment_required"
          and payment.calls == 1 and payment_fallback.calls == 1)

    limited, limit_fallback = OutputLimitAdapter(), SuccessAdapter()
    limit_gateway = ModelGateway(
        providers=(ProviderSpec("first", limited, "fixture", "env:FIRST"),
                   ProviderSpec("second", limit_fallback, "fixture",
                                "env:SECOND")),
        routes=(ModelRoute("first.route", "first", "first-model"),
                ModelRoute("second.route", "second", "second-model")))
    limit_result = limit_gateway.invoke(ModelGatewayRequest(
        "a truncated response may use another authorized route",
        ModelGatewayConfig(route_names=("first.route", "second.route"),
                           max_route_attempts=2)))
    first_limit = limit_result.attempts[0]
    check("output_limit_is_typed_and_can_fail_over",
          limit_result.ok and limit_result.provider == "second"
          and first_limit.error_code == "output_limit_reached"
          and first_limit.response_received
          and first_limit.provider_stop_reason == "length"
          and first_limit.output_limit_reached
          and limited.calls == 1 and limit_fallback.calls == 1,
          "a partial HTTP 200 is evidence, not a successful model answer")

    check("network_transport_failures_have_specific_codes",
          _error_code("URLError(OSError(113, 'No route to host'))")
          == "network_unreachable"
          and _error_code(
              "URLError(gaierror(-3, 'Temporary failure in name resolution'))")
          == "network_unreachable",
          "routing and DNS failures remain distinct from model rejection")

    # A provider attempt remains below the named spawned model-led Loop even
    # when that Loop is already two levels below a full Practitioner. The
    # routing Loop inherits the declared depth of five. Starting gateway
    # behavior remains compatible at the historical default depth of three.
    from ..loop.recursive_loop import Loop, LoopConfig
    deep = Loop(
        "depth-five practitioner",
        LoopConfig(
            framework="custom", custom_steps=("run",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic", "non_deterministic"),
            max_depth=5))
    stage = deep.spawn(
        "spawned stage",
        LoopConfig(
            framework="custom", custom_steps=("run",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic", "non_deterministic"),
            max_depth=5))
    candidate = stage.spawn(
        "named spawned model-led candidate",
        LoopConfig(
            framework="custom", custom_steps=("invoke",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic", "non_deterministic"),
            max_depth=5))
    nested_config = _gateway_orchestration_config(candidate)
    routing = candidate.spawn("route one model request", nested_config)
    attempt = routing.spawn(
        "provider attempt",
        LoopConfig(
            framework="custom", custom_steps=("invoke",), power="light",
            allowable_modes=("non_deterministic",),
            preferred_modes=("non_deterministic",),
            delegated_modes=("non_deterministic",),
            llm_thinking_power="medium"))
    starting_config = _gateway_orchestration_config(None)
    check("spawned_gateway_inherits_spawning_depth_without_reparenting",
          nested_config.max_depth == 5
          and routing.parent is candidate
          and attempt.parent is routing
          and attempt.depth == 4,
          "practitioner -> spawned stage -> candidate -> route -> attempt")
    check("starting_gateway_has_no_implicit_depth_ceiling",
          starting_config.max_depth is None,
          "starting gateway uses no product-imposed recursion ceiling")

    # Usage accounting: a real response with no provider-reported usage
    # leaves accounting unknown (never zero) and attaches a typed
    # diagnostic with a clearly-labeled estimate.
    class SilentUsageAdapter:
        DEFAULT_MODEL = "silent-usage-model"

        @staticmethod
        def output_capability_for(model=""):
            return ModelOutputCapability(
                4096, "self-test declaration", observed_at="2026-09-01")

        @staticmethod
        def verify(text):
            return bool(text and text.strip())

        @staticmethod
        def live_models():
            return [SilentUsageAdapter.DEFAULT_MODEL]

        @staticmethod
        def chat_maxout(prompt, *, model="", system="", temperature=0.7,
                        timeout=None, api_key=None, backoff=0.9,
                        floor_frac=0.3, max_attempts=1,
                        max_output_tokens=None, output_capability=None):
            del backoff, floor_frac, max_attempts
            return ChatResult(
                text="a real answer with no usage fields",
                model=SilentUsageAdapter.DEFAULT_MODEL, ok=True,
                prompt_tokens=0, eval_tokens=0, response_received=True,
                done=True, done_reason="stop")

    silent_route = ModelRoute(
        "test.silent", "silent_usage", SilentUsageAdapter.DEFAULT_MODEL,
        "cloud", purposes=("counted_generation",))
    silent_gateway = ModelGateway(
        providers=builtin_provider_specs(
            {"silent_usage": SilentUsageAdapter}),
        routes=(silent_route,))
    silent_result = invoke_model_gateway(
        silent_gateway,
        ModelGatewayRequest(prompt="usage diagnostic probe"))
    silent_attempt = silent_result.attempts[0] if silent_result.attempts else None
    check("a_response_without_usage_reports_unknown_not_zero",
          silent_attempt is not None
          and silent_attempt.input_tokens is None
          and silent_attempt.output_tokens is None
          and silent_result.accounting_complete is False)
    check("a_response_without_usage_carries_a_typed_diagnostic",
          silent_attempt is not None
          and silent_attempt.usage_diagnostic is not None
          and silent_attempt.usage_diagnostic.get("record_type")
          == "usage_accounting_unavailable/v1"
          and "estimate" in str(
              silent_attempt.usage_diagnostic.get("estimate_basis"))
          and silent_attempt.usage_diagnostic.get(
              "estimated_output_tokens", 0) >= 1)

    passed = sum(1 for test in results if test["passed"])

    return {
        "record_type": "model_gateway_contract_test/v2",
        "scope": "offline_contract_only",
        "provider_integration_proven": False,
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }
