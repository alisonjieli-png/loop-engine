"""Opt-in TypeSafe adapter using the shared typed decision wire contract.

The TypeSafe origin is fixed. Exact models, credential references and budgets
remain host configuration. Discovery does not resolve secrets or make calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from .contracts import DecisionProtocolError, PROVIDER_CAPABILITY, QUESTION_KINDS
from .wire import prepare_payload, invoke_once, MAXIMUM_CHOICES, MAXIMUM_LEVELS
from .http_transport import send_http
from .credentials import environment_credential, validate_reference

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_CONTRACT_SOURCE = "https://docs.typesafe.ai/api"
CONFIGURATION_VERSION = "jev_configuration/v1"

@dataclass(frozen=True)
class JevConfiguration:
    model: str
    credential_ref: str = "env:TYPESAFE_API_KEY"
    allow_network: bool = False
    allow_model_calls: bool = False
    maximum_request_bytes: int = 262_144
    maximum_response_bytes: int = 1_048_576
    record_type: str = CONFIGURATION_VERSION

    def __post_init__(self):
        if (self.record_type != CONFIGURATION_VERSION or not isinstance(self.model, str)
                or not re.fullmatch(r"jev-[0-9]+\.[0-9]+\.[0-9]+", self.model)):
            raise DecisionProtocolError("exact_jev_model_required")
        validate_reference(self.credential_ref)
        if type(self.allow_network) is not bool or type(self.allow_model_calls) is not bool:
            raise DecisionProtocolError("explicit_model_and_network_authority_required")
        for name in ("maximum_request_bytes", "maximum_response_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise DecisionProtocolError("positive_transport_allowance_required")



def _send(payload, secret, timeout, response_limit):
    return send_http(payload, secret, timeout, response_limit, endpoint=JEV_ENDPOINT)


@dataclass(frozen=True)
class JevAdapter:
    configuration: JevConfiguration
    secret_resolver: object = field(default=environment_credential, repr=False)
    transport: object = field(default=_send, repr=False)
    PROVIDER_CAPABILITIES = (PROVIDER_CAPABILITY,)
    WIRE_FORMAT = "typesafe_systemone"

    def __post_init__(self):
        if not isinstance(self.configuration, JevConfiguration) or not callable(self.secret_resolver) or not callable(self.transport):
            raise DecisionProtocolError("typed_jev_binding_required")

    @property
    def DEFAULT_MODEL(self):
        return self.configuration.model

    def decision_capabilities(self):
        return {"protocol": PROVIDER_CAPABILITY, "kinds": list(QUESTION_KINDS), "engine": "jev",
                "model": self.configuration.model, "maximum_choices": MAXIMUM_CHOICES,
                "maximum_levels": MAXIMUM_LEVELS, "source": JEV_CONTRACT_SOURCE,
                "network_authorized": self.configuration.allow_network,
                "model_calls_authorized": self.configuration.allow_model_calls,
                "provider_qualified": False, "generates_text": False}

    def prepare_decisions(self, request, *, model):
        return prepare_payload(request, model=model, configuration=self.configuration,
                               maximum_choices=MAXIMUM_CHOICES, maximum_levels=MAXIMUM_LEVELS)

    def decide_questions(self, request, *, model, timeout):
        return invoke_once(self, request, model=model, timeout=timeout)


def self_test():
    from .jev_checks import run_checks
    return run_checks()
