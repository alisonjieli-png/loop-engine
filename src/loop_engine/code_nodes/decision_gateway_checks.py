"""The real gateway and session with explicit offline provider fixtures.

Application-layer checks exercise the lower provider boundary through the
shared model session. They retain refusal and accounting cases without making
an external model request or treating typed output as independent acceptance.
"""
from __future__ import annotations

from dataclasses import replace
import json

from ..core.decisions.contracts import PROVIDER_CAPABILITY, DecisionProtocolError, DecisionProviderResult
from ..core.decisions.contract_checks import fixture_request, fixture_answers, report
from ..core.decisions.jev import JevAdapter, JevConfiguration
from ..core.decisions.jev_checks import provider_body
from ..core.model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
from ..core.model_routes import ModelRoute
from ..core.model_ontology import ModelProfile


def fixture(*, maximum_calls=2, allow_network=True, transport=None):
    from ..code_nodes.solution_model_port import ModelExecution
    from ..loop.recursive_loop import Loop, LoopConfig
    calls = []
    def respond(*args):
        calls.append(args)
        return provider_body()
    adapter = JevAdapter(JevConfiguration("jev-1.13.0", allow_network=allow_network, allow_model_calls=allow_network),
                         lambda _ref: "LOCAL_DECISION_FIXTURE_SECRET", transport or respond)
    route = ModelRoute("decision.fixture", "decision_fixture", "jev-1.13.0", purposes=("decide_label",),
                       profile=ModelProfile("judgment", output_kinds=("label", "probability", "score")))
    spec = ProviderSpec(route.provider, adapter, "typed_decision", adapter.configuration.credential_ref,
                        capabilities=(PROVIDER_CAPABILITY,))
    gateway = ModelGateway(providers=(spec,), routes=(route,))
    config = ModelGatewayConfig(purpose="decide_label", route_names=(route.name,), timeout_seconds=5)
    session = ModelExecution(gateway, config, max_model_calls=maximum_calls).start_session()
    parent = Loop("offline decision integration", LoopConfig(framework="custom", custom_steps=("choose",),
        allowable_modes=("hybrid", "non_deterministic"), preferred_modes=("hybrid",), delegated_modes=("non_deterministic",)))
    return session, parent, calls, adapter


def run_checks():
    from ..code_nodes.solution_model_port import SolutionModelError, ModelInvocationPort
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    session, parent, calls, adapter = fixture(maximum_calls=1)
    request = fixture_request()
    value = session.invoke_decisions(request, parent)
    check("structured_decision_uses_gateway_canonical_Loop_and_session_accounting",
          value["answers"]["route"]["choice"] == "inspect" and value["task_accepted"] is False
          and session.calls_used == 1 and session.total_tokens_used == 60
          and len(calls) == 1 and session.results[0].physical_provider_attempts)
    try:
        session.invoke_decisions(request, parent)
        refused = False
    except SolutionModelError as error:
        refused = error.error_code == "model_call_budget_exhausted"
    check("repeated_tool_calls_do_not_reset_the_session_budget", refused and len(calls) == 1)
    # The ledger records counts and digests; it does not need the supplied state.
    events = json.dumps(parent.ledger.events, default=lambda item: vars(item))
    check("history_does_not_record_state_or_provider_credentials",
          "fixture only" not in events and "LOCAL_DECISION_FIXTURE_SECRET" not in events)
    disabled, owner, sends, _adapter = fixture(allow_network=False)
    try:
        disabled.invoke_decisions(request, owner)
        blocked = False
    except SolutionModelError:
        blocked = True
    check("disabled_network_never_reaches_the_provider", blocked and not sends and disabled.calls_used == 0)
    session, parent, calls, adapter = fixture()
    bounded = session.authority.gateway.invoke_decisions(request, parent=parent,
        config=replace(session.authority.config, max_total_tokens=100))
    check("unknown_typed_output_capacity_does_not_bypass_a_hard_token_ceiling",
          not bounded.ok and bounded.error_code == "typed_decision_token_bound_unavailable" and not calls)
    separated = session.authority.gateway.invoke_decisions(request, parent=parent,
        config=replace(session.authority.config, excluded_routes=("decision.fixture",)))
    check("decision_route_exclusions_are_preserved", not separated.ok and separated.error_code == "no_eligible_route" and not calls)
    try:
        session.authority.gateway.invoke_decisions(request, config=session.authority.config)
        owner_required = False
    except DecisionProtocolError:
        owner_required = True
    check("direct_invocation_requires_its_owning_Loop", owner_required and not calls)
    unknown, owner, _calls, _adapter = fixture(transport=lambda *args: {**provider_body(), "usage": {}})
    unknown.invoke_decisions(request, owner)
    check("missing_provider_usage_stays_unknown_in_the_shared_session", unknown.calls_used == 1 and unknown.total_tokens_used is None)
    session._invocation_lock.acquire()
    try:
        try:
            session.invoke_decisions(request, parent)
            serialized = False
        except SolutionModelError as error:
            serialized = error.error_code == "model_invocation_in_progress"
    finally:
        session._invocation_lock.release()
    check("occupied_sessions_refuse_instead_of_oversubscribing_authority", serialized and not calls)
    from .solution_model_port import ModelExecution
    class AlternateProvider:
        DEFAULT_MODEL = "custom-decision-fixture"
        def __init__(self):
            self.calls = 0
        def decision_capabilities(self):
            return {"protocol": PROVIDER_CAPABILITY, "kinds": ["choice", "score", "boolean_probability"]}
        def prepare_decisions(self, request, *, model):
            if model != self.DEFAULT_MODEL:
                raise DecisionProtocolError("unknown_model")
        def decide_questions(self, request, *, model, timeout):
            self.calls += 1
            return DecisionProviderResult(True, model, fixture_answers(), 12, 8,
                                          physical_requests=1, response_received=True)
    alternate = AlternateProvider()
    alternative_route = ModelRoute("alternative.route", "alternative", alternate.DEFAULT_MODEL,
        purposes=("decide_label",), profile=ModelProfile("judgment", output_kinds=("label", "probability")))
    first, owner, sent, first_adapter = fixture(transport=lambda *args: {**provider_body(), "answers": {}})
    gateway = first.authority.gateway
    gateway.providers["alternative"] = ProviderSpec("alternative", alternate, "host_registered", "",
                                                   capabilities=(PROVIDER_CAPABILITY,))
    gateway.registry.add(alternative_route)
    default = replace(first.authority.config, route_names=("decision.fixture", "alternative.route"))
    refused_result = gateway.invoke_decisions(request, config=default, parent=owner)
    check("listing_an_alternative_is_not_fallback_authority", not refused_result.ok and alternate.calls == 0)
    permitted = ModelExecution(gateway, replace(default, allow_failover=True), max_model_calls=2).start_session()
    switched = permitted.invoke_decisions(request, owner)
    check("a_different_registered_engine_uses_the_same_call_contract",
          switched["provider"] == "alternative" and alternate.calls == 1 and permitted.calls_used == 2
          and permitted.total_tokens_used == 80)
    def denied(*args):
        raise DecisionProtocolError("authentication_failed")
    auth, owner, _sent, _adapter = fixture(transport=denied)
    auth.authority.gateway.providers["alternative"] = gateway.providers["alternative"]
    auth.authority.gateway.registry.add(alternative_route)
    stopped = auth.authority.gateway.invoke_decisions(request, config=replace(default, allow_failover=True), parent=owner)
    check("authentication_failure_does_not_silently_change_provider",
          not stopped.ok and stopped.error_code == "authentication_failed" and alternate.calls == 1)
    from ..loop.recursive_loop import Loop, LoopConfig
    from ..loop.loop_role import LoopRole, LoopRoleIdentity
    solution_session, _owner, sends, _adapter = fixture(maximum_calls=1)
    solution = Loop("Use a typed decision inside a Solution", LoopConfig(
        framework="custom", custom_steps=("choose",), allowable_modes=("hybrid",),
        preferred_modes=("hybrid",), delegated_modes=("non_deterministic",)),
        identity=LoopRoleIdentity(LoopRole.SOLUTION, "solution.atomic_component"))
    port = ModelInvocationPort(solution_session, "hybrid", solution)
    result = port.decide(request)
    check("Solution_model_port_supports_the_same_direct_typed_decision",
          result["answers"]["needed"]["probability"] == .7 and port.calls_used == 1 and len(sends) == 1
          and solution_session.results[-1].owner_loop_id == solution.loop_id)
    return report(tests)
