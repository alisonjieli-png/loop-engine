"""Offline adversarial checks for physical model-call and usage accounting.

These fixtures call no provider and preserve unknown token values.
"""
from __future__ import annotations

import json

from ..code_nodes.solution_model_port import (
    ModelExecution,
    ModelInvocationRequest,
    SolutionModelError,
)
from ..loop.recursive_loop import Loop
from .model_capabilities import ModelOutputCapability, UnknownModelOutputLimit
from .model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    ProviderSpec,
)
from .model_routes import ModelRoute
from .ollama_client import ChatResult


class _Adapter:
    def __init__(self, model: str, *, text: str = "accepted",
                 prompt_tokens=2, output_tokens=1, error: str = ""):
        self.DEFAULT_MODEL = model
        self.model = model
        self.text = text
        self.prompt_tokens = prompt_tokens
        self.output_tokens = output_tokens
        self.error = error
        self.response_received = True
        self.calls = 0

    @staticmethod
    def output_capability_for(model=""):
        return ModelOutputCapability(16, "offline accounting fixture")

    def chat_maxout(self, prompt, **kwargs):
        self.calls += 1
        return ChatResult(
            self.text, self.model, prompt_tokens=self.prompt_tokens,
            eval_tokens=self.output_tokens, ok=not self.error,
            error=self.error, response_received=self.response_received)

    def verify(self, model=""):
        return {"ok": True, "model": model or self.model}

    def live_models(self):
        return [self.model]


def _gateway(*adapters: _Adapter) -> tuple[ModelGateway, tuple[str, ...]]:
    providers = tuple(ProviderSpec(
        f"p{index}", adapter, "offline_fixture", "none")
        for index, adapter in enumerate(adapters))
    routes = tuple(ModelRoute(
        f"r{index}", f"p{index}", adapter.model)
        for index, adapter in enumerate(adapters))
    return ModelGateway(providers=providers, routes=routes), tuple(
        route.name for route in routes)


def self_test() -> dict:
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    refused = _Adapter("refused", text="partial", prompt_tokens=10,
                       output_tokens=1,
                       error="output_limit_reached: fixture")
    accepted = _Adapter("accepted", prompt_tokens=2, output_tokens=3)
    gateway, routes = _gateway(refused, accepted)
    aggregate = gateway.invoke(ModelGatewayRequest(
        "aggregate failover", ModelGatewayConfig(
            route_names=routes, max_route_attempts=2)))
    check("gateway_aggregates_failed_and_winning_physical_usage",
          aggregate.ok and aggregate.physical_model_calls == 2
          and aggregate.input_tokens == 12
          and aggregate.output_tokens == 4
          and aggregate.total_tokens == 16)

    partial = _Adapter("partial", prompt_tokens=None, output_tokens=3)
    gateway, routes = _gateway(partial)
    incomplete = gateway.invoke(ModelGatewayRequest(
        "partial usage", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1)))
    check("partial_usage_preserves_unknown_instead_of_zero",
          incomplete.ok and incomplete.input_tokens is None
          and incomplete.output_tokens == 3
          and not incomplete.accounting_complete)
    bounded = gateway.invoke(ModelGatewayRequest(
        "partial usage under budget", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_total_tokens=10)))
    check("exact_token_budget_refuses_incomplete_usage",
          not bounded.ok
          and bounded.error_code == "token_accounting_unavailable")

    secret = "sk-fixture-do-not-persist"
    failed_unknown = _Adapter(
        "failed-unknown", text="", prompt_tokens=None, output_tokens=None,
        error=("HTTP 503 service unavailable; Authorization: Bearer "
               f"{secret}; body=private"))
    failed_unknown.response_received = False
    gateway, routes = _gateway(failed_unknown)
    blocked = gateway.invoke(ModelGatewayRequest(
        "transport failure without accounting", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_total_tokens=10)))
    blocked_attempt = blocked.attempts[0]
    blocked_record = blocked.to_dict()
    check("transport_failure_survives_missing_usage_accounting_block",
          not blocked.ok
          and blocked.error_code == "token_accounting_unavailable"
          and blocked_attempt.error_code == "token_accounting_unavailable"
          and blocked.transport_error_code == "provider_unavailable"
          and blocked_attempt.transport_error_code == "provider_unavailable"
          and blocked.transport_error == blocked_attempt.transport_error
          and blocked.transport_succeeded is False
          and blocked_attempt.transport_succeeded is False
          and blocked_attempt.response_received is False
          and blocked_record["transport_error_code"]
          == "provider_unavailable"
          and blocked_record["attempts"][0]["transport_error_code"]
          == "provider_unavailable"
          and blocked.input_tokens is None
          and blocked.output_tokens is None)

    accepted_unknown = _Adapter(
        "accepted-unknown", prompt_tokens=None, output_tokens=None)
    gateway, routes = _gateway(accepted_unknown)
    accepted_blocked = gateway.invoke(ModelGatewayRequest(
        "successful response without accounting", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_total_tokens=10)))
    accepted_attempt = accepted_blocked.attempts[0]
    check("successful_response_missing_usage_has_no_transport_failure",
          not accepted_blocked.ok
          and accepted_blocked.error_code == "token_accounting_unavailable"
          and not accepted_blocked.transport_error_code
          and not accepted_blocked.transport_error
          and not accepted_attempt.transport_error_code
          and not accepted_attempt.transport_error
          and accepted_blocked.transport_succeeded is True
          and accepted_attempt.transport_succeeded is True
          and accepted_attempt.response_received is True)

    failed_known = _Adapter(
        "failed-known", text="", prompt_tokens=4, output_tokens=1,
        error=("HTTP 503 service unavailable; Authorization: Bearer "
               f"{secret}; body=private"))
    gateway, routes = _gateway(failed_known)
    known_failure = gateway.invoke(ModelGatewayRequest(
        "transport failure with accounting", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_total_tokens=10)))
    known_attempt = known_failure.attempts[0]
    check("known_usage_preserves_public_transport_failure",
          not known_failure.ok
          and known_failure.error_code == "provider_unavailable"
          and known_attempt.error_code == "provider_unavailable"
          and known_failure.transport_error_code == "provider_unavailable"
          and known_failure.transport_succeeded is False
          and known_attempt.transport_succeeded is False
          and known_attempt.response_received is True
          and known_failure.input_tokens == 4
          and known_failure.output_tokens == 1)

    recovered_failure = _Adapter(
        "recovered-failure", text="", prompt_tokens=2, output_tokens=1,
        error="HTTP 503 service unavailable")
    recovered_answer = _Adapter(
        "recovered-answer", prompt_tokens=3, output_tokens=2)
    gateway, routes = _gateway(recovered_failure, recovered_answer)
    recovered = gateway.invoke(ModelGatewayRequest(
        "transport diagnostic propagation", ModelGatewayConfig(
            route_names=routes, max_route_attempts=2)))
    recovered_record = recovered.to_dict()
    check("prior_transport_diagnostic_stays_on_attempt_after_recovery",
          recovered.ok
          and recovered.error_code == ""
          and recovered.transport_succeeded is True
          and not recovered.transport_error_code
          and recovered_record["transport_succeeded"] is True
          and not recovered_record["transport_error_code"]
          and recovered_record["attempts"][0]["transport_error_code"]
          == "provider_unavailable"
          and recovered_record["attempts"][0]["transport_succeeded"] is False
          and recovered_record["attempts"][1]["transport_succeeded"] is True
          and not recovered_record["attempts"][1]["transport_error_code"])

    serialized_blocked = json.dumps(
        blocked.to_dict(), sort_keys=True, ensure_ascii=False)
    serialized_known_failure = json.dumps(
        known_failure.to_dict(), sort_keys=True, ensure_ascii=False)
    check("saved_transport_diagnostic_does_not_persist_provider_secret",
          secret not in serialized_blocked
          and secret not in serialized_known_failure
          and "Authorization" not in serialized_blocked
          and "Authorization" not in serialized_known_failure
          and "body=private" not in serialized_blocked
          and "body=private" not in serialized_known_failure
          and blocked_attempt.transport_error
          == "provider attempt failed with classified code provider_unavailable")

    failed = _Adapter("first", text="", error="HTTP 402 payment required")
    unused = _Adapter("second")
    gateway, routes = _gateway(failed, unused)
    session = ModelExecution(
        gateway, ModelGatewayConfig(
            route_names=routes, max_route_attempts=2),
        max_model_calls=1).start_session()
    owner = Loop("offline accounting owner")
    call_refused = False
    try:
        session.invoke(ModelInvocationRequest("one physical call"), owner)
    except SolutionModelError:
        call_refused = True
    check("session_call_ceiling_caps_physical_failover_attempts",
          call_refused and failed.calls == 1 and unused.calls == 0
          and session.calls_used == 1)

    counted = _Adapter("counted", prompt_tokens=2, output_tokens=1)
    gateway, routes = _gateway(counted)
    session = ModelExecution(
        gateway, ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_total_tokens=6), max_model_calls=3).start_session()
    session.invoke(ModelInvocationRequest("first three"), owner)
    session.invoke(ModelInvocationRequest("second three"), owner)
    budget_refused = False
    try:
        session.invoke(ModelInvocationRequest("past six"), owner)
    except SolutionModelError as exc:
        budget_refused = exc.error_code == "token_budget_exhausted"
    check("session_token_ceiling_is_cumulative_across_semantic_calls",
          budget_refused and session.total_tokens_used == 6
          and session.calls_used == 2)

    class _Preflight(_Adapter):
        @staticmethod
        def output_capability_for(model=""):
            raise UnknownModelOutputLimit("unknown_model_output_limit: fixture")

    gateway, routes = _gateway(_Preflight("preflight"))
    preflight = gateway.invoke(ModelGatewayRequest(
        "preflight", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1)))
    check("effect_free_preflight_is_not_a_physical_model_call",
          not preflight.ok and preflight.physical_model_calls == 0
          and preflight.attempts[0].loop_id == "")

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_gateway_accounting_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "provider_calls": 0}


__all__ = ("self_test",)
