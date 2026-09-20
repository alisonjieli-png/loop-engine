"""Explicit local decision-engine setup and harness tool process.

Configuration is host-authored and contains credential references only.
Inspection is effect-free. Evaluation and standard-I/O serving use one
allocated model session; restarting requires a new host-authorized session.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .core.decisions.configuration import HOST_CONFIGURATION_VERSION as CONFIGURATION_VERSION


def _read(path):
    from .core.decisions.contracts import strict_json, DecisionProtocolError
    selected = Path(path)
    if not selected.is_absolute() or selected.resolve() != selected or not selected.is_file() or selected.stat().st_size > 262_144:
        raise DecisionProtocolError("confined_host_file_required")
    return strict_json(selected.read_bytes())


def configured_tool(value, *, installed_gateway=None):
    from .core.decisions.contracts import DecisionProtocolError
    from .core.decisions.configuration import configured_gateway
    from .core.model_gateway import ModelGateway, ModelGatewayConfig
    from .code_nodes.decision_tools import DecisionToolBinding
    from .code_nodes.solution_model_port import ModelExecution
    required = {"record_type", "maximum_model_calls", "timeout_seconds", "route_names"}
    allowed = required | {"engines", "allow_failover"}
    if (not isinstance(value, dict) or set(value) - allowed or not required <= set(value)
            or value["record_type"] != CONFIGURATION_VERSION):
        raise DecisionProtocolError("invalid_decision_host_configuration")
    if type(value["maximum_model_calls"]) is not int or value["maximum_model_calls"] < 1:
        raise DecisionProtocolError("explicit_positive_call_allowance_required")
    if installed_gateway is None:
        gateway = configured_gateway(value.get("engines"))
    else:
        if not isinstance(installed_gateway, ModelGateway) or "engines" in value or not value.get("route_names"):
            raise DecisionProtocolError("registered_gateway_needs_explicit_routes_not_another_provider_definition")
        gateway = installed_gateway
    if (not isinstance(value["route_names"], list) or not value["route_names"]
            or len(value["route_names"]) != len(set(value["route_names"]))):
        raise DecisionProtocolError("explicit_unique_decision_routes_required")
    config = ModelGatewayConfig(purpose="decide_label", route_names=value["route_names"],
        allow_failover=value.get("allow_failover", False), timeout_seconds=value["timeout_seconds"])
    gateway._routes(config)
    execution = ModelExecution(gateway, config, max_model_calls=value["maximum_model_calls"])
    return DecisionToolBinding(execution.start_session())


def decision_command(arguments):
    parser = argparse.ArgumentParser(prog="loop-engine decisions", description="Inspect or explicitly use a host-configured typed decision engine.")
    parser.add_argument("command", choices=("inspect", "evaluate", "serve"))
    parser.add_argument("--config", required=True, help="Absolute non-secret host configuration file.")
    parser.add_argument("--request", help="Absolute request file, required for evaluate.")
    values = parser.parse_args(arguments)
    try:
        binding = configured_tool(_read(values.config))
        if values.command == "inspect":
            print(json.dumps(binding.describe(), sort_keys=True))
        elif values.command == "evaluate":
            if not values.request:
                parser.error("evaluate requires --request")
            print(json.dumps(binding.evaluate(_read(values.request)), sort_keys=True))
        else:
            asyncio.run(binding.serve())
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception:
        # Private state and credentials are never exception diagnostics.
        import sys
        print(json.dumps({"record_type": "decision_cli_refusal/v1", "reason": "decision_configuration_or_operation_refused",
            "automatic_retry": False, "provider_qualification": "not_asserted"}), file=sys.stderr)
        return 1


def self_test():
    from .code_nodes.decision_tool_checks import cli_checks
    return cli_checks()
