"""Explicit decision-engine settings compiled into the existing ModelGateway.

This is a bounded factory for shipped adapters, not dynamic plugin loading or
a parallel provider registry. Ordered route names and failover authority stay
separate. Each provider retains its own credential and deployment binding.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .contracts import DecisionProtocolError, PROVIDER_CAPABILITY
from .jev import JevAdapter, JevConfiguration, JEV_ENDPOINT
from .system_one import SystemOneAdapter, SystemOneConfiguration, CIRCUIT, COMPATIBLE

HOST_CONFIGURATION_VERSION = "decision_host_configuration/v2"
JEV = "jev"
ADAPTER_FACTORIES = {
    JEV: (JevConfiguration, JevAdapter),
    CIRCUIT: (SystemOneConfiguration, SystemOneAdapter),
    COMPATIBLE: (SystemOneConfiguration, SystemOneAdapter),
}


@dataclass(frozen=True)
class ConfiguredDecisionEngine:
    name: str
    adapter: object
    endpoint: str


def configured_engines(values):
    if not isinstance(values, list) or not values:
        raise DecisionProtocolError("explicit_decision_engines_required")
    engines, names = [], set()
    for value in values:
        if not isinstance(value, dict) or set(value) != {"name", "engine", "settings"}:
            raise DecisionProtocolError("invalid_decision_engine_configuration")
        name, kind, settings = value["name"], value["engine"], value["settings"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", name) or name in names:
            raise DecisionProtocolError("unique_decision_engine_name_required")
        if kind not in ADAPTER_FACTORIES or not isinstance(settings, dict):
            raise DecisionProtocolError("unsupported_decision_engine")
        if "engine" in settings:
            raise DecisionProtocolError("engine_identity_must_have_one_owner")
        configuration, factory = ADAPTER_FACTORIES[kind]
        try:
            config = configuration(**(settings if kind == JEV else {**settings, "engine": kind}))
            adapter = factory(config)
        except (TypeError, ValueError) as error:
            raise DecisionProtocolError("decision_engine_settings_refused") from error
        engines.append(ConfiguredDecisionEngine(name, adapter, JEV_ENDPOINT if kind == JEV else config.endpoint))
        names.add(name)
    # Never reuse a credential reference across different provider origins.
    from urllib.parse import urlsplit
    origins = {}
    for engine in engines:
        parsed = urlsplit(engine.endpoint)
        origin = (parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        ref = engine.adapter.configuration.credential_ref
        if ref in origins and origins[ref] != origin:
            raise DecisionProtocolError("credential_reference_crosses_provider_origin")
        origins[ref] = origin
    return tuple(engines)


def configured_gateway(values):
    from ..model_gateway import ModelGateway, ProviderSpec
    from ..model_routes import ModelRoute
    from ..model_ontology import ModelProfile
    providers, routes = [], []
    for engine in configured_engines(values):
        adapter = engine.adapter
        locality = getattr(adapter.configuration, "locality", "cloud")
        routes.append(ModelRoute(engine.name, engine.name, adapter.DEFAULT_MODEL, locality=locality, purposes=("decide_label",),
            profile=ModelProfile("judgment", placement="local_endpoint" if locality == "local" else "remote_endpoint",
                                 size_class="local_service" if locality == "local" else "remote_service",
                                 provenance=getattr(adapter.configuration, "provenance", "vendor_foundation"),
                                 provenance_digest=getattr(adapter.configuration, "provenance_digest", ""),
                                 output_kinds=("label", "probability", "score"))))
        providers.append(ProviderSpec(engine.name, adapter, adapter.WIRE_FORMAT, adapter.configuration.credential_ref,
            locality=locality, wire_format=adapter.WIRE_FORMAT, endpoint=engine.endpoint, capabilities=(PROVIDER_CAPABILITY,)))
    return ModelGateway(providers=tuple(providers), routes=tuple(routes))
