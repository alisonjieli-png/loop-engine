"""Offline adversarial checks for physical model-call and usage accounting.

These fixtures call no provider and preserve unknown token values.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

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
from .model_routes import ModelProviderCapabilities, ModelRoute
from .model_token_preflight import ProviderTokenBound
from .ollama_client import ChatResult


class _Adapter:
    def __init__(self, model: str, *, text: str = "accepted",
                 prompt_tokens=2, output_tokens=1, error: str = "",
                 maximum_output_tokens=16, maximum_input_tokens=None):
        self.DEFAULT_MODEL = model
        self.model = model
        self.text = text
        self.prompt_tokens = prompt_tokens
        self.output_tokens = output_tokens
        self.error = error
        self.response_received = True
        self.calls = 0
        self.maximum_output_tokens = maximum_output_tokens
        self.maximum_input_tokens = (
            prompt_tokens if type(prompt_tokens) is int and prompt_tokens >= 0
            else 2) if maximum_input_tokens is None else maximum_input_tokens
        self.requested_output_tokens = []

    def output_capability_for(self, model=""):
        return ModelOutputCapability(
            self.maximum_output_tokens, "offline accounting fixture")

    def chat_maxout(self, prompt, **kwargs):
        self.calls += 1
        self.requested_output_tokens.append(kwargs["max_output_tokens"])
        return ChatResult(
            self.text, self.model, prompt_tokens=self.prompt_tokens,
            eval_tokens=self.output_tokens, ok=not self.error,
            error=self.error, response_received=self.response_received)

    def verify(self, model=""):
        return {"ok": True, "model": model or self.model}

    def live_models(self):
        return [self.model]


class _FixtureTokenBounds:
    """Known fixture counts, never an estimator or live-provider qualification."""

    def __init__(self, adapters):
        self.adapters = adapters

    def resolve(self, request):
        adapter = self.adapters[request.provider_id]
        return ProviderTokenBound(
            request.provider_id, request.model_id, request.route_name,
            request.provider_request_digest, adapter.maximum_input_tokens,
            request.maximum_output_tokens,
            "fixture:model_gateway_accounting", "1.0.0")


def _gateway(*adapters: _Adapter, max_context=0
             ) -> tuple[ModelGateway, tuple[str, ...]]:
    providers = tuple(ProviderSpec(
        f"p{index}", adapter, "offline_fixture", "none")
        for index, adapter in enumerate(adapters))
    routes = tuple(ModelRoute(
        f"r{index}", f"p{index}", adapter.model,
        capabilities=ModelProviderCapabilities(
            f"p{index}", "cloud", True, max_context=max_context))
        for index, adapter in enumerate(adapters))
    return ModelGateway(
        providers=providers, routes=routes,
        token_bound_resolver=_FixtureTokenBounds({
            f"p{index}": adapter for index, adapter in enumerate(adapters)})), tuple(
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
            max_total_tokens=32)))
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
            max_total_tokens=32)))
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
            max_total_tokens=32)))
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
            max_total_tokens=32)))
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

    counted = _Adapter("counted", prompt_tokens=2, output_tokens=1,
                       maximum_output_tokens=1)
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

    tests.extend(_reservation_checks())
    tests.extend(_response_boundary_checks())
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_gateway_accounting_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "provider_calls": 0}


def _reservation_checks() -> list[dict]:
    """Regressions for exact-request preflight and single-flight session spend."""
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def failure_code(operation):
        try:
            operation()
        except SolutionModelError as exc:
            return exc.error_code
        return ""

    # Reproduce the physical sizes of saved Case A, not its private prompt.
    fixture = _Adapter(
        "saved-counterexample", prompt_tokens=34619, output_tokens=1120,
        maximum_output_tokens=65536)
    gateway, routes = _gateway(fixture, max_context=131072)
    result = gateway.invoke(ModelGatewayRequest(
        "x" * 111087, ModelGatewayConfig(
            route_names=routes, allow_failover=False, max_route_attempts=1,
            max_output_tokens=65536, max_total_tokens=30130)))
    check("saved_30130_remaining_65536_output_counterexample_has_zero_dispatch",
          not result.ok and fixture.calls == result.physical_model_calls == 0
          and result.error_code == "token_budget_insufficient_preflight"
          and result.attempts[0].maximum_output_tokens == 65536
          and result.attempts[0].reservation_status == "refused")

    fixture = _Adapter("unknown-bound")
    gateway, routes = _gateway(fixture)
    gateway.token_bound_resolver = None
    missing = gateway.invoke(ModelGatewayRequest(
        "no qualified bound", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1, max_total_tokens=32)))
    check("strict_token_budget_without_host_bound_refuses_before_dispatch",
          missing.error_code == "token_bound_unavailable"
          and fixture.calls == missing.physical_model_calls == 0)

    class StaleBound:
        def resolve(self, request):
            return ProviderTokenBound(
                request.provider_id, request.model_id, request.route_name,
                "a" * 64, 2, request.maximum_output_tokens,
                "fixture:stale_bound", "1.0.0")

    gateway.token_bound_resolver = StaleBound()
    stale = gateway.invoke(ModelGatewayRequest(
        "different physical packet", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1, max_total_tokens=32)))
    check("stale_physical_request_bound_refuses_before_dispatch",
          stale.error_code == "token_bound_invalid"
          and fixture.calls == stale.physical_model_calls == 0)

    unknown_output = _Adapter("unknown-output", maximum_output_tokens="unknown")
    gateway, routes = _gateway(unknown_output)
    unknown = gateway.invoke(ModelGatewayRequest(
        "explicit ceiling is not a known provider maximum", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1,
            max_output_tokens=16, max_total_tokens=32)))
    check("strict_budget_refuses_unknown_supported_output_even_with_explicit_ceiling",
          unknown.error_code == "unknown_model_output_limit"
          and unknown_output.calls == unknown.physical_model_calls == 0)

    first = _Adapter("first-route", error="HTTP 503 service unavailable")
    second = _Adapter("second-route")
    gateway, routes = _gateway(first, second)
    failover = gateway.invoke(ModelGatewayRequest(
        "remaining budget must fit the next route", ModelGatewayConfig(
            route_names=routes, max_route_attempts=2, max_total_tokens=20)))
    check("failover_rechecks_remaining_budget_after_failed_physical_usage",
          not failover.ok and first.calls == 1 and second.calls == 0
          and failover.physical_model_calls == 1 and failover.total_tokens == 3
          and failover.error_code == "token_budget_insufficient_preflight"
          and failover.attempts[0].reserved_total_tokens == 18
          and failover.attempts[1].maximum_output_tokens == 16)

    large_maximum = _Adapter("large-output", maximum_output_tokens=32)
    gateway, routes = _gateway(large_maximum, max_context=24)
    no_clamp = gateway.invoke(ModelGatewayRequest(
        "short", ModelGatewayConfig(route_names=routes, max_route_attempts=1)))
    check("context_shortfall_never_silently_reduces_the_provider_maximum",
          no_clamp.error_code == "context_window_exceeded"
          and large_maximum.calls == no_clamp.physical_model_calls == 0
          and no_clamp.attempts[0].maximum_output_tokens == 32)

    exact = _Adapter("exact-fit", maximum_output_tokens=1)
    gateway, routes = _gateway(exact)
    exact_result = gateway.invoke(ModelGatewayRequest(
        "exact fit", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1, max_total_tokens=3)))
    check("exact_bound_fit_dispatches_once_and_preserves_reported_usage",
          exact_result.ok and exact.calls == 1 and exact_result.total_tokens == 3
          and exact.requested_output_tokens == [1]
          and exact_result.attempts[0].reservation_status == "reconciled"
          and exact_result.attempts[0].reserved_total_tokens == 3)

    input_bound = _Adapter("large-input-bound", maximum_input_tokens=8,
                           maximum_output_tokens=1)
    gateway, routes = _gateway(input_bound, max_context=5)
    context_bound = gateway.invoke(ModelGatewayRequest(
        "short", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1, max_total_tokens=20)))
    check("qualified_input_bound_checks_context_even_when_text_estimate_fits",
          context_bound.error_code == "context_window_exceeded"
          and input_bound.calls == context_bound.physical_model_calls == 0)

    class RaisingAdapter(_Adapter):
        def chat_maxout(self, prompt, **kwargs):
            self.calls += 1
            raise RuntimeError("PRIVATE_FIXTURE_PROVIDER_EXCEPTION")

    raising = RaisingAdapter("raising")
    gateway, routes = _gateway(raising)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=1, max_total_tokens=32),
        max_model_calls=1).start_session()
    owner = Loop("offline reservation owner")
    first_error = failure_code(lambda: session.invoke(
        ModelInvocationRequest("raising callback"), owner))
    second_error = failure_code(lambda: session.invoke(
        ModelInvocationRequest("cannot refund raised callback"), owner))
    check("raising_callback_remains_a_physical_call_and_cannot_refund_authority",
          first_error == "token_accounting_unavailable"
          and second_error == "model_call_budget_exhausted"
          and raising.calls == session.calls_used == 1
          and session.total_tokens_used is None and len(session.results) == 1
          and session.results[0].attempts[0].reservation_status == "unresolved"
          and "PRIVATE_FIXTURE" not in json.dumps(session.results[0].to_dict()))

    unused = _Adapter("outer-failure")
    gateway, routes = _gateway(unused)
    outer_entries = []

    def uncertain_gateway(*args, **kwargs):
        outer_entries.append(1)
        raise RuntimeError("PRIVATE_FIXTURE_OUTER_EXCEPTION")

    gateway.invoke = uncertain_gateway
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_total_tokens=32), max_model_calls=2).start_session()
    outer_errors = [failure_code(lambda: session.invoke(
        ModelInvocationRequest("outer failure"), owner)) for _ in range(2)]
    check("outer_gateway_exception_poisons_session_instead_of_refunding",
          outer_errors == ["token_accounting_unavailable"] * 2
          and len(outer_entries) == 1 and unused.calls == 0
          and session.total_tokens_used is None)

    counted = _Adapter("projection", maximum_output_tokens=1)
    gateway, routes = _gateway(counted)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=1, max_total_tokens=3),
        max_model_calls=1).start_session()
    session.invoke(ModelInvocationRequest("one charged call"), owner)
    session.results[0].input_tokens = session.results[0].output_tokens = 0
    session.results.clear()
    projection_error = failure_code(lambda: session.invoke(
        ModelInvocationRequest("projection cannot authorize"), owner))
    check("mutable_results_cannot_refund_private_call_or_token_counters",
          counted.calls == session.calls_used == 1 and session.total_tokens_used == 3
          and projection_error == "model_call_budget_exhausted")
    session.authority = replace(session.authority, max_model_calls=100,
                                config=replace(session.authority.config,
                                               max_total_tokens=300))
    changed_authority = failure_code(lambda: session.invoke(
        ModelInvocationRequest("cannot replace spent authority"), owner))
    check("replacing_session_authority_cannot_replenish_spent_budget",
          changed_authority == "model_authority_changed" and counted.calls == 1)

    allowed = _Adapter("family:allowed")
    outside = _Adapter("family:outside")
    gateway, routes = _gateway(allowed, outside)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, allowed_models=(allowed.model,)),
        max_model_calls=1).start_session()
    outside_error = failure_code(lambda: session.invoke(
        ModelInvocationRequest("cannot broaden model authority", model=outside.model),
        owner))
    check("invocation_model_override_cannot_broaden_session_authority",
          outside_error == "model_not_authorized"
          and allowed.calls == outside.calls == 0)
    exact_models = gateway.invoke(ModelGatewayRequest(
        "family alias is not exact model authority", ModelGatewayConfig(
            route_names=routes, allowed_models=("family",))))
    check("gateway_model_authority_does_not_match_family_aliases",
          exact_models.error_code == "no_eligible_route"
          and allowed.calls == outside.calls == 0)

    class HeldAdapter(_Adapter):
        def __init__(self):
            super().__init__("single-flight", maximum_output_tokens=1)
            self.entered = Event()
            self.release = Event()

        def chat_maxout(self, prompt, **kwargs):
            self.entered.set()
            if not self.release.wait(timeout=5):
                raise RuntimeError("offline single-flight fixture timed out")
            return super().chat_maxout(prompt, **kwargs)

    held = HeldAdapter()
    gateway, routes = _gateway(held)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=1, max_total_tokens=3),
        max_model_calls=1).start_session()

    def concurrent_invoke(label):
        return failure_code(lambda: session.invoke(
            ModelInvocationRequest(label), Loop("offline " + label)))

    with ThreadPoolExecutor(max_workers=2) as workers:
        pending = workers.submit(concurrent_invoke, "first invocation")
        entered = held.entered.wait(timeout=5)
        try:
            overlap = workers.submit(concurrent_invoke, "overlapping invocation")
            overlap_error = overlap.result(timeout=5)
        finally:
            held.release.set()
        pending_error = pending.result(timeout=5)
    check("two_thread_single_flight_prevents_double_spend_of_calls_and_tokens",
          entered and overlap_error == "model_invocation_in_progress"
          and pending_error == "" and held.calls == session.calls_used == 1
          and session.total_tokens_used == 3)

    violated = _Adapter("violated-bound", prompt_tokens=4, output_tokens=1,
                        maximum_input_tokens=2, maximum_output_tokens=1)
    unused = _Adapter("unused-after-violation", maximum_output_tokens=1)
    gateway, routes = _gateway(violated, unused)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=2, max_total_tokens=3),
        max_model_calls=3).start_session()
    violation_error = failure_code(lambda: session.invoke(
        ModelInvocationRequest("violating provider evidence"), owner))
    reported = session.results[0]
    after_violation = failure_code(lambda: session.invoke(
        ModelInvocationRequest("stop after violation"), owner))
    check("bound_violation_halts_and_preserves_actual_usage_without_clamping",
          violation_error == "token_bound_violated" and not reported.ok
          and reported.total_tokens == 5 and not reported.attempts[0].ok
          and reported.attempts[0].error_code == "token_bound_violated"
          and reported.attempts[0].reservation_status == "violated"
          and reported.attempts[0].reserved_total_tokens == 3
          and after_violation == "token_accounting_unavailable"
          and violated.calls == 1 and unused.calls == 0)
    output_violation = _Adapter("output-violation", output_tokens=2,
                               maximum_output_tokens=1)
    gateway, routes = _gateway(output_violation)
    output_result = gateway.invoke(ModelGatewayRequest(
        "provider output bound is independent of its input bound", ModelGatewayConfig(
            route_names=routes, max_route_attempts=1, max_total_tokens=3)))
    check("output_component_bound_violation_preserves_provider_reported_count",
          output_result.error_code == "token_bound_violated"
          and output_result.output_tokens == 2 and output_result.total_tokens == 4
          and output_violation.calls == 1
          and output_result.attempts[0].maximum_output_tokens == 1)
    return tests


def _response_boundary_checks() -> list[dict]:
    """Contradictory responses and cancellation cannot restore authority."""
    tests = []

    class ChangedResponseAdapter(_Adapter):
        def __init__(self, changes):
            super().__init__("contradictory-response")
            self.changes = changes

        def chat_maxout(self, prompt, **kwargs):
            result = super().chat_maxout(prompt, **kwargs)
            for name, value in self.changes.items():
                setattr(result, name, value)
            return result

    for name, changes, expected_code in (
            ("unfinished_response", {"done": False}, "incomplete_response"),
            ("output_limit_signal", {"output_limit_reached": True},
             "output_limit_reached"),
            ("explicit_error", {"error": "output_limit_reached: fixture"},
             "output_limit_reached")):
        adapter = ChangedResponseAdapter(changes)
        gateway, routes = _gateway(adapter)
        result = gateway.invoke(ModelGatewayRequest(
            "contradictory completion fixture", ModelGatewayConfig(
                route_names=routes, allow_failover=False, max_route_attempts=1,
                max_total_tokens=32)))
        attempt = result.attempts[0]
        tests.append({
            "test": name + "_cannot_override_gateway_refusal_with_ok_true",
            "passed": (not result.ok and not attempt.ok
                       and result.error_code == attempt.error_code == expected_code
                       and result.transport_succeeded is True
                       and adapter.calls == result.physical_model_calls == 1
                       and result.total_tokens == 3 and result.text == ""),
        })

    interrupted = _Adapter("cancelled-after-response")
    gateway, routes = _gateway(interrupted)

    def interrupt_after_response(_text):
        raise KeyboardInterrupt("offline post-dispatch cancellation")

    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=1, max_total_tokens=32),
        max_model_calls=1, validator=interrupt_after_response).start_session()
    owner = Loop("offline cancellation accounting owner")
    propagated = False
    try:
        session.invoke(ModelInvocationRequest("cancel after dispatch"), owner)
    except KeyboardInterrupt:
        propagated = True
    retry_code = ""
    try:
        session.invoke(ModelInvocationRequest("cannot retry cancellation"), owner)
    except SolutionModelError as exc:
        retry_code = exc.error_code
    tests.append({
        "test": "post_dispatch_keyboard_interrupt_poisons_accounting_before_unlock",
        "passed": (propagated and interrupted.calls == 1
                   and retry_code == "token_accounting_unavailable"
                   and session.accounting_uncertain
                   and session.total_tokens_used is None and not session.results),
    })

    multiple = ChangedResponseAdapter({"attempts": 2})
    unused = _Adapter("unused-after-multiplicity")
    gateway, routes = _gateway(multiple, unused)
    session = ModelExecution(gateway, ModelGatewayConfig(
        route_names=routes, max_route_attempts=2, max_total_tokens=64),
        max_model_calls=3).start_session()
    errors = []
    for _ in range(2):
        try:
            session.invoke(ModelInvocationRequest("ambiguous physical count"), owner)
        except SolutionModelError as exc:
            errors.append(exc.error_code)
    recorded = session.results[0]
    tests.append({
        "test": "adapter_multi_attempt_claim_halts_failover_and_session_retry",
        "passed": (errors == ["provider_attempt_contract_violated",
                              "token_accounting_unavailable"]
                   and multiple.calls == 1 and unused.calls == 0
                   and not recorded.ok and not recorded.attempts[0].ok
                   and recorded.attempts[0].error_code
                   == "provider_attempt_contract_violated"
                   and session.accounting_uncertain
                   and session.total_tokens_used is None),
    })
    return tests


__all__ = ("self_test",)
