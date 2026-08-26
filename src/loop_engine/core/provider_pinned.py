"""Typed convenience path for one provider-pinned model call.

This companion to ``model_gateway`` serves comparison arms and legacy call
sites that must name one provider and model. It creates a one-route gateway,
so it cannot silently cross providers or introduce another invocation system.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model_gateway import (ModelGateway, ModelGatewayConfig,
                            ModelGatewayRequest, ModelGatewayResult,
                            builtin_provider_specs)
from .model_routes import ModelRoute, RoutePolicy


@dataclass(frozen=True)
class ProviderPinnedRequest:
    """One provider-pinned call expressed as a typed request object."""

    prompt: str
    provider: str
    model: str
    purpose: str = "counted_generation"
    system: str = ""
    temperature: float = 0.7
    timeout_seconds: float = 900.0
    max_output_tokens: "int | None" = None
    thinking_power: str = "medium"

    def __post_init__(self):
        if not self.prompt.strip() or not self.provider or not self.model:
            raise ValueError(
                "ProviderPinnedRequest needs prompt, provider, and model")
        if (self.timeout_seconds <= 0
                or (self.max_output_tokens is not None
                    and self.max_output_tokens < 1)):
            raise ValueError("provider-pinned limits must be positive")
        if self.thinking_power not in (
                "small", "medium", "high", "max", "specialized"):
            raise ValueError(
                "thinking_power must be small, medium, high, max, or "
                "specialized")


def invoke_provider_model(request: ProviderPinnedRequest, *, validate=None,
                          ledger=None, parent=None) -> ModelGatewayResult:
    """Invoke exactly one provider and model through ``ModelGateway``."""
    from .provider_failover import PROVIDERS

    adapter = PROVIDERS.get(request.provider)
    if adapter is None:
        return ModelGatewayResult(
            ok=False, error_code="provider_not_configured",
            error=f"no configured provider {request.provider!r}")
    specs = builtin_provider_specs({request.provider: adapter})
    locality = specs[0].locality
    route_name = (f"direct.{request.provider}.{request.model}"
                  .replace("/", ".").replace(":", "."))
    route = ModelRoute(
        route_name, request.provider, request.model, locality=locality,
        purposes=(request.purpose,))
    gateway = ModelGateway(
        providers=specs, routes=(route,),
        policy=RoutePolicy(allow_local_counted_generation=locality == "local"))
    return gateway.invoke(
        ModelGatewayRequest(
            request.prompt,
            ModelGatewayConfig(
                purpose=request.purpose, route_names=(route_name,),
                allow_failover=False, max_route_attempts=1,
                timeout_seconds=request.timeout_seconds,
                max_output_tokens=request.max_output_tokens,
                thinking_power=request.thinking_power),
            system=request.system, temperature=request.temperature),
        validate=validate, ledger=ledger, parent=parent)
