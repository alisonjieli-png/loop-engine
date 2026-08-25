"""One provider-neutral gateway for every semantic model invocation.

Architectural role: Static Architecture model execution boundary.

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

from .model_routes import (ModelRoute, RoutePolicy, RouteRegistry,
                           screen_route)


class ProviderAdapter(Protocol):
    """The executable contract every model provider adapter implements."""
    DEFAULT_MODEL: str

    def chat_maxout(self, prompt: str, *, model: str = "", system: str = "",
                    temperature: float = 0.7, timeout: float = 900.0,
                    max_attempts: int = 1,
                    max_output_tokens: "int | None" = None): ...

    def verify(self, model: str = ""): ...

    def live_models(self): ...


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

    def __post_init__(self):
        if not self.provider_id:
            raise ValueError("ProviderSpec needs provider_id")
        if self.locality not in ("cloud", "local"):
            raise ValueError("provider locality must be cloud or local")
        required = ("chat_maxout", "verify", "live_models", "DEFAULT_MODEL")
        missing = [name for name in required if not hasattr(self.adapter, name)]
        if missing:
            raise ValueError(
                f"provider {self.provider_id!r} misses adapter fields {missing}")

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
    allowed_localities: tuple[str, ...] = ("cloud", "local")
    allow_failover: bool = True
    max_route_attempts: int = 3
    timeout_seconds: float = 900.0
    max_output_tokens: int = 4096
    max_total_tokens: "int | None" = None
    allow_power_escalation: bool = False
    max_power_escalations: int = 0
    escalate_on: tuple[str, ...] = ("output_validation_failed",)

    def __post_init__(self):
        if self.purpose not in (
                "counted_generation", "decide_label", "embedding"):
            raise ValueError("unknown model gateway purpose")
        if self.max_route_attempts < 1:
            raise ValueError("max_route_attempts must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
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
        if any(value not in ("cloud", "local")
               for value in self.allowed_localities):
            raise ValueError("allowed_localities accepts cloud and local")

    @classmethod
    def from_operating_profile(cls, profile, **overrides):
        """Translate the owner-facing reasoning mode into route locality."""
        mode = profile.reasoning_and_model_mode
        localities = {
            "deterministic_only": (),
            "local_only": ("local",),
            "deterministic_first_local_first": ("local", "cloud"),
            "approved_remote": ("cloud",),
            "best_available": ("cloud", "local"),
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
        return any(attempt.provider_ok for attempt in self.attempts)

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
        }


def _error_code(error: str) -> str:
    low = str(error).lower()
    if "401" in low or "403" in low or "unauthor" in low or "api_key" in low:
        return "authentication_failed"
    if "429" in low or "rate" in low and "limit" in low:
        return "rate_limited"
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if (("not found" in low or "missing" in low)
            and ("key" in low or "credential" in low)):
        return "missing_credential"
    if "validation" in low:
        return "output_validation_failed"
    return "provider_failed"


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
        return selected[:config.max_route_attempts]

    def invoke(self, request: ModelGatewayRequest, *,
               validate: "Callable[[str], bool] | None" = None,
               ledger=None, parent=None) -> ModelGatewayResult:
        """Run one route at a time; every provider attempt is a model loop."""
        from ..loop.encapsulate import as_model_loop
        from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

        routes = self._routes(request.config)
        if not routes:
            return ModelGatewayResult(
                ok=False, error_code="no_eligible_route",
                error="no model route is permitted by this request and policy")

        orchestration_config = LoopConfig(
            framework="custom", custom_steps=("route",), power="light",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("non_deterministic",),
            stop_condition="run_to_completion")
        root = (parent.spawn("route one model request", orchestration_config)
                if parent is not None else Loop(
                    "route one model request", orchestration_config,
                    ledger=ledger))
        result = ModelGatewayResult(gateway_loop_id=root.loop_id)
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
                attempt_output = min(
                    request.config.max_output_tokens,
                    attempt_spec.max_output_tokens
                    or request.config.max_output_tokens)

                def invoke_provider(spec=spec, route=route,
                                    attempt_timeout=attempt_timeout,
                                    attempt_output=attempt_output):
                    value = spec.adapter.chat_maxout(
                        request.prompt, model=route.model,
                        system=request.system,
                        temperature=request.temperature,
                        timeout=attempt_timeout,
                        max_attempts=1,
                        max_output_tokens=attempt_output)
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
                text = str(getattr(provider_result, "text", "") or "")
                provider_ok = bool(getattr(provider_result, "ok", False)
                                   and text.strip())
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
                error = str(getattr(provider_result, "error", "") or "")
                if provider_ok and not validation_ok:
                    error = validation_error or "output failed validation"
                attempt = GatewayAttempt(
                    provider=route.provider,
                    model=str(getattr(provider_result, "model", route.model)),
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
                    provider_ok=provider_ok,
                    thinking_power=current_power,
                )
                result.attempts.append(attempt)
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

        root.run(handler=handler, max_steps=2)
        return result


def invoke_model_gateway(gateway: ModelGateway, request: ModelGatewayRequest,
                         **kwargs) -> ModelGatewayResult:
    """Top-level boundary function for registered gateway invocation."""
    return gateway.invoke(request, **kwargs)


def self_test() -> dict:
    """Offline contract tests. No provider or network is contacted."""
    from .ollama_client import ChatResult
    from ..loop.recursive_loop import LoopLedger

    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    class StubAdapter:
        DEFAULT_MODEL = "stub"

        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = []

        def chat_maxout(self, prompt, **kwargs):
            self.calls.append({"prompt": prompt, **kwargs})
            return self.responses.pop(0)

        def verify(self, model=""):
            return {"ok": True, "model": model or self.DEFAULT_MODEL}

        def live_models(self):
            return [self.DEFAULT_MODEL]

    ollama = StubAdapter([ChatResult(
        "", "ollama-model", ok=False, error="HTTP 429 rate limit")])
    mistral = StubAdapter([ChatResult(
        "valid answer", "mistral-model", prompt_tokens=11, eval_tokens=7)])
    openrouter = StubAdapter([ChatResult(
        "unused", "openrouter-model", prompt_tokens=9, eval_tokens=3)])
    providers = (
        ProviderSpec("ollama_cloud", ollama, "fixture", "fixture:ollama"),
        ProviderSpec("mistral", mistral, "fixture", "fixture:mistral"),
        ProviderSpec("openrouter", openrouter, "fixture", "fixture:openrouter"),
    )
    routes = (
        ModelRoute("test.ollama", "ollama_cloud", "ollama-model"),
        ModelRoute("test.mistral", "mistral", "mistral-model"),
        ModelRoute("test.openrouter", "openrouter", "openrouter-model"),
    )
    ledger = LoopLedger()
    gateway = ModelGateway(providers=providers, routes=routes)
    response = gateway.invoke(ModelGatewayRequest(
        "solve the fixture",
        ModelGatewayConfig(route_names=(
            "test.ollama", "test.mistral", "test.openrouter"))),
        validate=lambda text: text.startswith("valid"), ledger=ledger)
    check("provider_failover_is_ordered_and_each_attempt_is_a_loop",
          response.ok and response.provider == "mistral"
          and [attempt.provider for attempt in response.attempts]
          == ["ollama_cloud", "mistral"]
          and len({attempt.loop_id for attempt in response.attempts}) == 2
          and not openrouter.calls and len(ledger.loops()) == 3,
          "gateway root plus two provider-attempt loops")
    check("split_usage_and_failure_reason_survive_failover",
          response.input_tokens == 11 and response.output_tokens == 7
          and response.total_tokens == 18 and response.accounting_complete
          and response.attempts[0].error_code == "rate_limited")

    only = StubAdapter([ChatResult(
        "wrong shape", "mistral-model", prompt_tokens=4, eval_tokens=2)])
    failed = ModelGateway(
        providers=(ProviderSpec("mistral", only, "fixture", "fixture:m"),),
        routes=(ModelRoute("only", "mistral", "mistral-model"),)
    ).invoke(ModelGatewayRequest(
        "return json", ModelGatewayConfig(route_names=("only",))),
        validate=lambda text: text.startswith("{"))
    check("validation_failure_remains_a_model_failure",
          not failed.ok and failed.error_code == "output_validation_failed"
          and failed.attempts[0].validation_ok is False)

    raising_validator_adapter = StubAdapter([ChatResult(
        "not json", "mistral-model", prompt_tokens=4, eval_tokens=2)])
    raising_validator = ModelGateway(
        providers=(ProviderSpec(
            "mistral", raising_validator_adapter, "fixture", "fixture:m"),),
        routes=(ModelRoute("raise", "mistral", "mistral-model"),)
    ).invoke(ModelGatewayRequest(
        "return json", ModelGatewayConfig(route_names=("raise",))),
        validate=lambda text: json.loads(text))
    check("a_validator_exception_becomes_a_typed_validation_failure",
          not raising_validator.ok
          and raising_validator.error_code == "output_validation_failed"
          and "JSONDecodeError" in raising_validator.error)

    pinned_adapter = StubAdapter([ChatResult(
        "pinned", "openrouter-model", prompt_tokens=3, eval_tokens=1)])
    pinned = ModelGateway(
        providers=(ProviderSpec("openrouter", pinned_adapter, "fixture",
                                "fixture:o"),),
        routes=(ModelRoute("pinned.openrouter", "openrouter",
                           "openrouter-model"),)
    ).invoke(ModelGatewayRequest(
        "one provider",
        ModelGatewayConfig(route_names=("pinned.openrouter",),
                           allow_failover=False)))
    check("a_provider_comparison_can_pin_one_route",
          pinned.ok and pinned.provider == "openrouter"
          and len(pinned.attempts) == 1)

    no_usage_adapter = StubAdapter([ChatResult("answer", "m", ok=True)])
    no_usage = ModelGateway(
        providers=(ProviderSpec("mistral", no_usage_adapter, "fixture",
                                "fixture:m"),),
        routes=(ModelRoute("unknown.usage", "mistral", "m"),)
    ).invoke(ModelGatewayRequest(
        "usage", ModelGatewayConfig(route_names=("unknown.usage",))))
    check("missing_provider_usage_remains_unknown_not_zero",
          no_usage.ok and no_usage.input_tokens is None
          and no_usage.output_tokens is None
          and no_usage.total_tokens is None
          and not no_usage.accounting_complete)

    secret_text = "fixture-secret-value"
    safe = ProviderSpec("safe", no_usage_adapter, "fixture",
                        "env:SAFE_PROVIDER_KEY")
    check("provider_descriptions_carry_references_not_secret_values",
          secret_text not in str(safe.describe())
          and safe.describe()["credential_ref"] == "env:SAFE_PROVIDER_KEY")

    from .operating_profile import OperatingProfile
    deterministic_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="deterministic_only"))
    local_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="local_only"))
    remote_config = ModelGatewayConfig.from_operating_profile(
        OperatingProfile(reasoning_and_model_mode="approved_remote"))
    check("operating_profile_controls_gateway_route_locality",
          deterministic_config.allowed_localities == ()
          and local_config.allowed_localities == ("local",)
          and remote_config.allowed_localities == ("cloud",))

    tier_adapter = StubAdapter([
        ChatResult("", "small-model", ok=False, error="request timeout"),
        ChatResult("strong answer", "high-model",
                   prompt_tokens=8, eval_tokens=5)])
    tier_gateway = ModelGateway(
        providers=(ProviderSpec(
            "mistral", tier_adapter, "fixture", "fixture:m"),),
        routes=(ModelRoute("tier.small", "mistral", "small-model"),
                ModelRoute("tier.high", "mistral", "high-model")))
    tier_ledger = LoopLedger()
    tier_result = tier_gateway.invoke(ModelGatewayRequest(
        "escalate only after a typed failure",
        ModelGatewayConfig(
            route_plan=(
                ModelRouteAttemptSpec("tier.small", "small", 64, 10.0),
                ModelRouteAttemptSpec("tier.high", "high", 128, 20.0)),
            allow_power_escalation=True, max_power_escalations=1,
            escalate_on=("timeout",))),
        ledger=tier_ledger)
    check("thinking_power_escalates_only_under_a_bounded_typed_plan",
          tier_result.ok and tier_result.thinking_power == "high"
          and [attempt.thinking_power for attempt in tier_result.attempts]
          == ["small", "high"]
          and [call["max_output_tokens"] for call in tier_adapter.calls]
          == [64, 128]
          and any(event.get("llm_thinking_power") == "high"
                  for event in tier_ledger.events
                  if event.get("event") == "init"))

    auth_adapter = StubAdapter([
        ChatResult("", "small-model", ok=False, error="HTTP 401 rejected"),
        ChatResult("must not run", "high-model")])
    auth_result = ModelGateway(
        providers=(ProviderSpec(
            "mistral", auth_adapter, "fixture", "fixture:m"),),
        routes=(ModelRoute("auth.small", "mistral", "small-model"),
                ModelRoute("auth.high", "mistral", "high-model"))
    ).invoke(ModelGatewayRequest(
        "do not spend a stronger call on a bad credential",
        ModelGatewayConfig(
            route_plan=(
                ModelRouteAttemptSpec("auth.small", "small"),
                ModelRouteAttemptSpec("auth.high", "high")),
            allow_power_escalation=True, max_power_escalations=1)))
    check("authentication_failure_does_not_trigger_power_escalation",
          not auth_result.ok and len(auth_adapter.calls) == 1
          and auth_result.error_code == "authentication_failed")

    passed = sum(1 for test in results if test["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
