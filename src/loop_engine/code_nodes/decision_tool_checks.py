"""Direct and real protocol tool checks using an offline provider fixture.

The installed protocol library exchanges messages with the actual decision
tool. Temporary sessions enforce call budgets without external requests. These
checks establish local integration, not Jev quality or native harness loading.
"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from .decision_gateway_checks import fixture
from ..core.decisions.contracts import DecisionProtocolError
from ..core.decisions.contract_checks import fixture_request, report
from .decision_tools import DecisionToolBinding


async def _protocol(check):
    import anyio
    from mcp import ClientSession
    session, _parent, calls, _adapter = fixture(maximum_calls=1)
    binding = DecisionToolBinding(session)
    client_send, server_read = anyio.create_memory_object_stream(0)
    server_send, client_read = anyio.create_memory_object_stream(0)
    async with anyio.create_task_group() as group:
        group.start_soon(binding.run_streams, server_read, server_send)
        async with ClientSession(client_read, client_send) as client:
            initialized = await client.initialize()
            available = await client.list_tools()
            metadata = await client.call_tool("decision_capabilities", {})
            check("official_protocol_client_discovers_without_a_provider_call",
                  initialized.protocolVersion == "2025-11-25" and len(available.tools) == 2
                  and not metadata.isError and not calls)
            output = await client.call_tool("decision_evaluate", fixture_request().to_dict())
            check("harness_tool_uses_the_same_gateway_and_budget",
                  not output.isError and output.structuredContent["answers"]["route"]["choice"] == "inspect"
                  and output.structuredContent["execution"]["runtime_type"] == "Loop" and session.calls_used == 1)
            exhausted = await client.call_tool("decision_evaluate", fixture_request().to_dict())
            check("protocol_repeat_cannot_replenish_model_authority", exhausted.isError and len(calls) == 1)
            injected = await client.call_tool("decision_evaluate", {**fixture_request().to_dict(), "api_key": "PRIVATE_FIXTURE_VALUE"})
            check("protocol_authority_injection_is_refused_without_echo", injected.isError
                  and "PRIVATE_FIXTURE_VALUE" not in str(injected) and len(calls) == 1)
        group.cancel_scope.cancel()


async def _configured_endpoint_protocol(check):
    import anyio
    from mcp import ClientSession
    from ..decision_cli import configured_tool, CONFIGURATION_VERSION
    from ..core.decisions.system_one_checks import loopback_fixture, endpoint_settings, engine_record, FIXTURE_SECRET
    with loopback_fixture() as (endpoint, state), patch.dict("os.environ", {"CIRCUIT_API_KEY": FIXTURE_SECRET}):
        engine = engine_record(endpoint_settings(endpoint))
        binding = configured_tool({"record_type": CONFIGURATION_VERSION, "engines": [engine],
            "route_names": [engine["name"]], "maximum_model_calls": 1, "timeout_seconds": 3})
        client_send, server_read = anyio.create_memory_object_stream(0)
        server_send, client_read = anyio.create_memory_object_stream(0)
        async with anyio.create_task_group() as group:
            group.start_soon(binding.run_streams, server_read, server_send)
            async with ClientSession(client_read, client_send) as client:
                await client.initialize()
                discovery = await client.call_tool("decision_capabilities", {})
                check("configured_circuit_harness_discovery_launches_no_model_or_endpoint",
                      not state["calls"] and discovery.structuredContent["engines"][0]["engine"] == "circuit")
                answer = await client.call_tool("decision_evaluate", fixture_request().to_dict())
                check("configured_circuit_harness_tool_reaches_the_external_endpoint",
                      not answer.isError and answer.structuredContent["route"] == engine["name"]
                      and len(state["calls"]) == 1 and binding.session.calls_used == 1)
                exhausted = await client.call_tool("decision_evaluate", fixture_request().to_dict())
                check("configured_circuit_tool_shares_the_existing_session_ceiling",
                      exhausted.isError and len(state["calls"]) == 1)
            group.cancel_scope.cancel()


def run_checks():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    session, _parent, calls, _adapter = fixture(maximum_calls=1)
    binding = DecisionToolBinding(session)
    meta = binding.describe()
    check("decision_tool_metadata_describes_a_candidate_without_secret_resolution",
          not calls and meta["engines"][0]["protocol"] == "typed_decisions/v1"
          and meta["engines"][0]["provider_qualified"] is False and meta["credentials_returned"] is False)
    value = binding.evaluate(fixture_request().to_dict())
    check("direct_tool_evaluation_is_owned_by_a_classified_Loop",
          value["execution"]["profile"] == "practitioner.solver@1.0.0"
          and value["calls_used"] == 1 and len(calls) == 1)
    try:
        DecisionToolBinding(session, maximum_request_bytes=1).evaluate(fixture_request().to_dict())
        bounded = False
    except DecisionProtocolError:
        bounded = True
    check("tool_byte_limit_refuses_before_another_provider_call", bounded and len(calls) == 1)
    try:
        import mcp
    except ImportError:
        tests.append({"test": "decision_protocol_optional_dependency", "passed": None, "not_tested": True})
        return report(tests)
    asyncio.run(_protocol(check))
    asyncio.run(_configured_endpoint_protocol(check))
    return report(tests)


def cli_checks():
    from ..decision_cli import configured_tool, CONFIGURATION_VERSION
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    configured = {"record_type": CONFIGURATION_VERSION,
        "engines": [{"name": "typesafe", "engine": "jev", "settings": {
            "model": "jev-1.13.0", "credential_ref": "env:TYPESAFE_API_KEY"}}], "route_names": ["typesafe"],
        "maximum_model_calls": 3, "timeout_seconds": 10}
    with patch("loop_engine.core.decisions.credentials.os.environ", {}):
        tool = configured_tool(configured)
        meta = tool.describe()
    check("host_inspection_needs_no_key_or_network", meta["engines"][0]["network_authorized"] is False
          and meta["maximum_calls"] == 3 and meta["calls_used"] == 0)
    registered, _owner, calls, _adapter = fixture()
    selected = configured_tool({"record_type": CONFIGURATION_VERSION, "route_names": ["decision.fixture"],
        "maximum_model_calls": 1, "timeout_seconds": 3, "allow_failover": False},
        installed_gateway=registered.authority.gateway)
    value = selected.evaluate(fixture_request().to_dict())
    check("host_settings_select_existing_registered_routes_without_rebuilding_providers",
          value["route"] == "decision.fixture" and selected.session.calls_used == 1 and len(calls) == 1)
    for name, changed in (("unknown", {**configured, "api_key": "PRIVATE_FIXTURE_VALUE"}),
                          ("no_allowance", {key: value for key, value in configured.items() if key != "maximum_model_calls"}),
                          ("boolean_allowance", {**configured, "maximum_model_calls": True})):
        try:
            configured_tool(changed)
            refused = False
        except DecisionProtocolError:
            refused = True
        check("host_configuration_" + name + "_refuses", refused)
    from ..core.decisions.system_one_checks import loopback_fixture, endpoint_settings, engine_record, FIXTURE_SECRET
    with loopback_fixture() as (endpoint, state):
        circuit = engine_record(endpoint_settings(endpoint))
        configured = {"record_type": CONFIGURATION_VERSION, "engines": [circuit],
            "route_names": [circuit["name"]], "maximum_model_calls": 2, "timeout_seconds": 2}
        with patch.dict("os.environ", {"CIRCUIT_API_KEY": FIXTURE_SECRET}):
            tool = configured_tool(configured)
            value = tool.evaluate(fixture_request().to_dict())
        check("public_configuration_selects_circuit_through_the_actual_gateway",
              value["route"] == circuit["name"] and value["answers"]["route"]["choice"] == "inspect"
              and len(state["calls"]) == 1 and tool.session.calls_used == 1)
        check("unpublished_old_host_configuration_is_refused",
              _configuration_refused({**configured, "record_type": "decision_host_configuration/v1"}))
    from dataclasses import replace
    with loopback_fixture() as (first_endpoint, first_state), loopback_fixture() as (second_endpoint, second_state):
        first = engine_record(endpoint_settings(first_endpoint))
        second = engine_record(replace(endpoint_settings(second_endpoint), engine="system_one",
            model="owner-specialist-1", provenance="custom_trained", provenance_digest="a" * 64,
            credential_ref="env:OTHER_DECISION_KEY"), "specialist")
        first_state["status"] = 503
        second_state["model"] = "owner-specialist-1"
        settings = {"record_type": CONFIGURATION_VERSION, "engines": [first, second],
            "route_names": [first["name"], second["name"]], "maximum_model_calls": 2, "timeout_seconds": 3}
        with patch.dict("os.environ", {"CIRCUIT_API_KEY": FIXTURE_SECRET, "OTHER_DECISION_KEY": FIXTURE_SECRET}):
            blocked = configured_tool(settings)
            try:
                blocked.evaluate(fixture_request().to_dict())
            except Exception:
                pass
            check("configuration_does_not_imply_cross_provider_failover",
                  len(first_state["calls"]) == 1 and not second_state["calls"] and blocked.session.calls_used == 1)
            allowed = configured_tool({**settings, "allow_failover": True})
            answer = allowed.evaluate(fixture_request().to_dict())
            check("configured_fallback_swaps_endpoint_without_changing_the_caller",
                  answer["route"] == "specialist" and answer["model"] == "owner-specialist-1"
                  and allowed.session.calls_used == 2 and len(second_state["calls"]) == 1)
            first_state["status"] = 401
            authenticated = configured_tool({**settings, "allow_failover": True})
            try:
                authenticated.evaluate(fixture_request().to_dict())
            except Exception:
                pass
            check("configured_authentication_failure_does_not_silently_switch_endpoints",
                  authenticated.session.calls_used == 1 and len(second_state["calls"]) == 1)
    return report(tests)


def _configuration_refused(value):
    from ..decision_cli import configured_tool
    try:
        configured_tool(value)
    except DecisionProtocolError:
        return True
    return False
