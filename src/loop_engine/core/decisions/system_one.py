"""Host-configured System One endpoints behind the existing decision gateway.

Circuit and compatible services share the same question wire format. Exact
endpoint, model identity, credential, limits and authority are host settings;
model/tool input cannot replace them. Users operate the endpoint. This adapter
does not launch a model server or infer context coverage from a valid answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
import ipaddress
import re
from urllib.parse import urlsplit

from .contracts import DecisionProtocolError, PROVIDER_CAPABILITY, QUESTION_KINDS
from .credentials import environment_credential, validate_reference
from .wire import prepare_payload, invoke_once, MAXIMUM_CHOICES, MAXIMUM_LEVELS
from .http_transport import send_http

CONFIGURATION_VERSION = "system_one_configuration/v1"
CIRCUIT = "circuit"
COMPATIBLE = "system_one"


@dataclass(frozen=True)
class SystemOneConfiguration:
    engine: str
    model: str
    endpoint: str
    credential_ref: str
    locality: str
    provenance: str
    deployment_revision: str | None = None
    provenance_digest: str = ""
    allow_network: bool = False
    allow_model_calls: bool = False
    allow_loopback_http: bool = False
    maximum_choices: int = MAXIMUM_CHOICES
    maximum_levels: int = MAXIMUM_LEVELS
    maximum_request_bytes: int = 262_144
    maximum_response_bytes: int = 1_048_576
    record_type: str = CONFIGURATION_VERSION

    def __post_init__(self):
        if self.record_type != CONFIGURATION_VERSION or self.engine not in (CIRCUIT, COMPATIBLE):
            raise DecisionProtocolError("unsupported_decision_endpoint_profile")
        if (not isinstance(self.model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}", self.model)
                or self.model.lower() in ("fake", "latest", "default")):
            raise DecisionProtocolError("exact_decision_model_required")
        if self.deployment_revision is not None and (not isinstance(self.deployment_revision, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.deployment_revision)):
            raise DecisionProtocolError("deployment_digest_required")
        validate_reference(self.credential_ref)
        from ..model_routes import LOCALITIES
        from ..model_ontology import PROVENANCE_KINDS
        if self.locality not in LOCALITIES:
            raise DecisionProtocolError("declared_endpoint_locality_required")
        if self.provenance not in PROVENANCE_KINDS:
            raise DecisionProtocolError("declared_model_provenance_required")
        if (not isinstance(self.provenance_digest, str) or
                (self.provenance_digest and not re.fullmatch(r"[0-9a-f]{64}", self.provenance_digest))
                or (self.provenance == "custom_trained" and not self.provenance_digest)):
            raise DecisionProtocolError("custom_model_training_digest_required")
        for value in (self.allow_network, self.allow_model_calls, self.allow_loopback_http):
            if type(value) is not bool:
                raise DecisionProtocolError("explicit_endpoint_authority_required")
        for name in ("maximum_choices", "maximum_levels", "maximum_request_bytes", "maximum_response_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise DecisionProtocolError("positive_transport_allowance_required")
        if not 2 <= self.maximum_choices <= MAXIMUM_CHOICES or not 2 <= self.maximum_levels <= MAXIMUM_LEVELS:
            raise DecisionProtocolError("system_one_schema_limit_exceeded")
        if not isinstance(self.endpoint, str):
            raise DecisionProtocolError("exact_system_one_endpoint_required")
        parsed = urlsplit(self.endpoint)
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            loopback = False
        if (parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
                or parsed.path != "/v1/systemone" or not parsed.hostname
                or any(ch.isspace() or ord(ch) < 32 for ch in self.endpoint)):
            raise DecisionProtocolError("exact_system_one_endpoint_required")
        if parsed.scheme != "https":
            if parsed.scheme != "http" or not self.allow_loopback_http or not loopback:
                raise DecisionProtocolError("secure_or_explicit_loopback_endpoint_required")
        if loopback and self.locality != "local":
            raise DecisionProtocolError("loopback_endpoint_must_be_local")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise DecisionProtocolError("invalid_endpoint_port")


@dataclass(frozen=True)
class SystemOneAdapter:
    configuration: SystemOneConfiguration
    secret_resolver: object = field(default=environment_credential, repr=False)
    transport: object = field(default=None, repr=False)
    PROVIDER_CAPABILITIES = (PROVIDER_CAPABILITY,)
    WIRE_FORMAT = "typesafe_systemone"

    def __post_init__(self):
        if not isinstance(self.configuration, SystemOneConfiguration) or not callable(self.secret_resolver):
            raise DecisionProtocolError("typed_system_one_binding_required")
        if self.transport is None:
            object.__setattr__(self, "transport", partial(send_http, endpoint=self.configuration.endpoint))
        elif not callable(self.transport):
            raise DecisionProtocolError("decision_transport_required")

    @property
    def DEFAULT_MODEL(self):
        return self.configuration.model

    def decision_capabilities(self):
        config = self.configuration
        return {"protocol": PROVIDER_CAPABILITY, "kinds": list(QUESTION_KINDS), "engine": config.engine,
                "model": config.model, "deployment_revision": config.deployment_revision,
                "locality": config.locality,
                "provenance": config.provenance, "provenance_authority": "host_configuration",
                "provenance_digest": config.provenance_digest or None,
                "maximum_choices": config.maximum_choices, "maximum_levels": config.maximum_levels,
                "network_authorized": config.allow_network, "model_calls_authorized": config.allow_model_calls,
                "context_policy": "provider_behavior_unqualified", "server_lifecycle": "externally_managed",
                "provider_qualified": False, "generates_text": False}

    def prepare_decisions(self, request, *, model):
        return prepare_payload(request, model=model, configuration=self.configuration,
                               maximum_choices=self.configuration.maximum_choices,
                               maximum_levels=self.configuration.maximum_levels)

    def decide_questions(self, request, *, model, timeout):
        return invoke_once(self, request, model=model, timeout=timeout)


def self_test():
    from .system_one_checks import run_checks
    return run_checks()
