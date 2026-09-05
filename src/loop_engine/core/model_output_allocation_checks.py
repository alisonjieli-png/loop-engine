"""Offline wire regressions for explicit model output allocations.

These checks exercise the real Ollama, Mistral and OpenRouter request builders
through ModelGateway, but intercept HTTP locally and prohibit sockets. Keys
are synthetic placeholders. ProviderSpec pins one fixture capability snapshot;
live catalog lookup is prohibited, not represented as qualified integration.
Token bounds describe fixture counts, not a tokenizer or provider guarantee.
This verification module owns no operational runtime or allocation authority.
"""
from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import patch

from . import mistral_client, ollama_client, openrouter_client
from .model_capabilities import ModelOutputAllocation, ModelOutputCapability
from .model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    ProviderSpec,
)
from .model_routes import ModelProviderCapabilities, ModelRoute
from .model_token_preflight import ProviderTokenBound


class _Response:
    """Local response bytes with both tested provider response envelopes."""

    def __init__(self, model):
        self.body = {
            "model": model,
            "message": {"content": "offline fixture answer"},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 7,
            "eval_count": 3,
            "choices": [{"message": {"content": "offline fixture answer"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode("utf-8")


class _FixtureBounds:
    """Exact synthetic input count; no text-length estimate or network work."""

    def resolve(self, request):
        return ProviderTokenBound(
            request.provider_id, request.model_id, request.route_name,
            request.provider_request_digest, 7, request.maximum_output_tokens,
            "fixture:native_output_allocation_wire", "1.0.0")


def self_test() -> dict:
    """Check all three wire builders with no live credentials or sockets."""
    tests = []
    intercepted_dispatches = 0

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def prohibited(*args, **kwargs):
        raise AssertionError("network and live capability lookup are prohibited")

    for provider, module in (("ollama_cloud", ollama_client),
                             ("mistral", mistral_client),
                             ("openrouter", openrouter_client)):
        model = "allocation-fixture-model"
        route = "fixture." + provider
        capability = ModelOutputCapability(
            1024, "offline native wire fixture capacity", observed_at="fixture-revision-1")
        captured = []

        def intercept(request, captured=captured, **kwargs):
            # Inspect only the synthetic body, never authorization headers.
            payload = json.loads(request.data)
            captured.append(payload)
            return _Response(payload["model"])

        with ExitStack() as stack:
            stack.enter_context(patch("urllib.request.urlopen", side_effect=intercept))
            for socket_operation in ("socket", "create_connection", "getaddrinfo"):
                stack.enter_context(patch("socket." + socket_operation,
                                          side_effect=prohibited))
            stack.enter_context(patch.object(
                module, "load_api_key", return_value="offline-key-placeholder"))
            stack.enter_context(patch.object(
                module, "output_capability_for", side_effect=prohibited))
            gateway = ModelGateway(
                providers=(ProviderSpec(
                    provider, module, "offline_fixture", "none",
                    model_output_capability=capability,
                    model_output_capability_model=model),),
                routes=(ModelRoute(
                    route, provider, model,
                    capabilities=ModelProviderCapabilities(
                        provider, "cloud", True, max_context=4096)),),
                token_bound_resolver=_FixtureBounds())

            def allocation(tokens, *, capability=capability, provider=provider,
                           model=model, route=route):
                return ModelOutputAllocation(
                    capability, provider, model, route, tokens,
                    "loop:fixture-allocation-decision",
                    "Offline explicit allocation decision for this response.")

            def invoke(selected=None, scalar=None, *, gateway=gateway, route=route):
                output = selected.requested_tokens if selected is not None else 1024
                return gateway.invoke(ModelGatewayRequest(
                    "offline exact physical packet",
                    ModelGatewayConfig(
                        route_names=(route,), allow_failover=False,
                        max_route_attempts=1, max_total_tokens=output + 7,
                        max_output_tokens=scalar, output_allocation=selected),
                    system="offline system"))

            def wire_output(payload, *, provider=provider):
                return (payload["options"]["num_predict"] if provider == "ollama_cloud"
                        else payload["max_tokens"])

            for tokens in (None, 32, 128):
                selected = allocation(tokens) if tokens is not None else None
                expected = tokens if tokens is not None else 1024
                before = len(captured)
                result = invoke(selected)
                succeeded = result.ok and len(captured) == before + 1
                check(provider + "_wire_" + str(tokens or "full_default"),
                      succeeded and result.physical_model_calls == 1
                      and wire_output(captured[-1]) == expected
                      and captured[-1]["model"] == model
                      and result.total_tokens == 10
                      and result.attempts[0].maximum_output_tokens == expected
                      and result.attempts[0].reserved_total_tokens == expected + 7
                      and result.attempts[0].reservation_status == "reconciled")

            selected = allocation(32)
            mismatches = (
                ("provider", {"provider_id": "different-provider"}, "no_eligible_route"),
                ("model", {"model_id": "different-model"}, "no_eligible_route"),
                ("route", {"route_name": "different-route"}, "no_eligible_route"),
                ("source", {"capability": replace(
                    capability, source="different observation")}, "model_output_limit_mismatch"),
                ("capacity", {"capability": replace(
                    capability, maximum_output_tokens=2048)}, "model_output_limit_mismatch"),
            )
            for name, changes, error_code in mismatches:
                before = len(captured)
                result = invoke(replace(selected, **changes))
                check(provider + "_allocation_mismatch_" + name,
                      not result.ok and result.error_code == error_code
                      and result.physical_model_calls == 0 and len(captured) == before)

            for scalar, expected_ok in ((32, True), (1024, True), (64, False)):
                before = len(captured)
                result = invoke(selected, scalar)
                if expected_ok:
                    passed = (result.ok and len(captured) == before + 1
                              and wire_output(captured[-1]) == 32
                              and result.attempts[0].reserved_total_tokens == 39)
                else:
                    passed = (not result.ok and len(captured) == before
                              and result.physical_model_calls == 0
                              and result.error_code == "model_output_limit_mismatch")
                check(provider + "_scalar_with_allocation_" + str(scalar), passed)
        intercepted_dispatches += len(captured)

    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "model_output_allocation_wire_self_test/v1",
        "scope": "offline_native_request_builders_only",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
        "intercepted_http_dispatches": intercepted_dispatches,
        "provider_calls": 0,
        "provider_integration_proven": False,
        "live_catalog_qualification": "not_tested",
    }
