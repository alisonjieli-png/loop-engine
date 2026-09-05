"""Reproduce the observed total-token preflight gap without provider traffic.

This is diagnostic evidence of current behavior, not an acceptance test claiming
a hard consumption ceiling. The fake text only supplies a known size.
"""
import json
from types import SimpleNamespace

from loop_engine.core.context_budget import estimate_tokens
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.model_gateway import (
    ModelGateway, ModelGatewayConfig, ModelGatewayRequest, ProviderSpec)
from loop_engine.core.model_routes import ModelProviderCapabilities, ModelRoute


class CountingFixture:
    DEFAULT_MODEL = "offline-budget-fixture"

    def __init__(self):
        self.calls = 0

    def output_capability_for(self, model):
        return ModelOutputCapability(65536, "offline fixture only")

    def chat_maxout(self, prompt, **kwargs):
        self.calls += 1
        assert estimate_tokens(prompt) == 27772
        assert kwargs["max_output_tokens"] == 65536
        return SimpleNamespace(
            text="{}", model=self.DEFAULT_MODEL, ok=True, error="",
            prompt_tokens=34619, eval_tokens=1120, response_received=True,
            done=True, done_reason="stop", reasoning_present=False,
            output_limit_reached=False)

    def verify(self, *args, **kwargs):
        raise AssertionError("no live calls")

    def live_models(self):
        raise AssertionError("no model discovery")


rows = []
for context_limit in (131072, 90000):
    fixture = CountingFixture()
    gateway = ModelGateway(
        providers=(ProviderSpec("offline_probe", fixture, "fixture", "none"),),
        routes=(ModelRoute(
            "offline.probe", "offline_probe", fixture.DEFAULT_MODEL,
            capabilities=ModelProviderCapabilities(
                "offline_probe", "cloud", True, max_context=context_limit)),))
    config = ModelGatewayConfig(
        route_names=("offline.probe",), allow_failover=False,
        max_route_attempts=1, max_output_tokens=65536, max_total_tokens=30130)
    result = gateway.invoke(ModelGatewayRequest("x" * 111087, config))
    rows.append({
        "context_limit": context_limit, "remaining_total_budget": 30130,
        "estimated_input_tokens": 27772, "requested_output_tokens": 65536,
        "fixture_dispatches": fixture.calls, "error_code": result.error_code,
        "fixture_reported_total_tokens": result.total_tokens,
        "live_provider_calls": 0})

assert rows[0]["fixture_dispatches"] == 1
assert rows[0]["error_code"] == "token_budget_exhausted"
assert rows[0]["fixture_reported_total_tokens"] == 35739
assert rows[1]["fixture_dispatches"] == 0
assert rows[1]["error_code"] == "context_window_exceeded"
print(json.dumps({
    "record_type": "budget_preflight_gap_probe/v1", "rows": rows,
    "current_gap_reproduced": True, "hard_total_ceiling_proven": False,
    "live_provider_calls": 0}, sort_keys=True, indent=2))
