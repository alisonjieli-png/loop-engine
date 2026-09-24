"""Reviewer engine ``model_gateway``: one hosted model through the repository's model gateway.

The engine never opens its own model connection. It builds one ``ModelRoute``
for its installation's exact model, asks the repository's ``ModelGateway`` for
one attempt with no failover, and passes a typed ``ModelOutputAllocation`` that
the panel policy declares within the model's source-backed capacity. The
gateway gives the attempt its own model Loop, classifies failures and keeps
provider-reported usage exactly: a count the provider did not report stays
unknown.

The route is built through the model policy of ``core.model_routes``: a model
that policy forbids is refused before any provider call, and the refusal is
recorded as the engine's availability. The provider declares its credential as
an environment variable (``credential_ref`` of its ``ProviderSpec``). The engine
checks only that the variable holds a value, keeps and records nothing of it,
and is unavailable without it, so the adapter never falls back to any other
place a key could be read from. The adapter reads the value from the environment and sends it only
in the request header.

``listed_model_versions`` reads the provider's model listing, which names each
model's short digest and modification time. It is a listing, not a model call,
and it reads the key from the same environment variable only.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from loop_engine.core import ollama_client
from loop_engine.core.model_capabilities import ModelOutputAllocation, UnknownModelOutputLimit
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, ModelGatewayRequest, builtin_provider_specs
from loop_engine.core.model_routes import PURPOSES, ModelProviderCapabilities, ModelRoute, RouteViolation, screen_route

from ..configuration import thawed
from ..verdicts import ANSWER_FORMATS, JSON_ONLY
from ..records import VERDICT_RECORD, identifier, positive_integer, positive_number, read_part, refuse, text_field
from . import (
    ANSWERED, AUTHENTICATION_UNAVAILABLE, CONTEXT_WINDOW_EXCEEDED, ENGINE_UNAVAILABLE, MODEL_IDENTITY_MISMATCH,
    MODEL_NOT_FOUND, OUTPUT_LIMIT_REACHED, PROVIDER_FAILED, PROVIDER_REPORTED, PROVIDER_UNAVAILABLE, RATE_LIMITED,
    REFUSED_BY_ROUTE_POLICY, TIMEOUT, USAGE_LIMIT_REACHED, USAGE_UNKNOWN, Availability, ReviewerAttempt, Usage,
    failed,
)

SETTINGS_FIELDS = ("provider_id", "route_name", "purpose", "timeout_seconds", "maximum_context_tokens")
#: Optional settings: an output allocation for this installation within the model's capacity (otherwise the
#: panel policy's), and the answer format its model uses (otherwise ``json_only``).
OPTIONAL_FIELDS = ("output_allocation_tokens", "answer_format")
LOCALITY = "cloud"
ALLOCATION_DECISION = "candidate_review_panel_policy/v1#output_allocation_tokens"
ALLOCATION_REASON = ("A review answer is one short JSON object. The panel policy declares this allocation "
                     "within the model's source-backed output capacity, so the token ceiling can hold.")
#: The gateway's failure codes, grouped into the reviewer edge's closed outcomes.
OUTCOME_FOR_ERROR = {
    "rate_limited": RATE_LIMITED,
    "usage_limit_reached": USAGE_LIMIT_REACHED, "payment_required": USAGE_LIMIT_REACHED,
    "provider_unavailable": PROVIDER_UNAVAILABLE, "gateway_timeout": PROVIDER_UNAVAILABLE,
    "network_unreachable": PROVIDER_UNAVAILABLE,
    "timeout": TIMEOUT,
    "authentication_failed": AUTHENTICATION_UNAVAILABLE, "missing_credential": AUTHENTICATION_UNAVAILABLE,
    "model_not_found": MODEL_NOT_FOUND,
    "context_window_exceeded": CONTEXT_WINDOW_EXCEEDED,
    "output_limit_reached": OUTPUT_LIMIT_REACHED,
    "model_identity_mismatch": MODEL_IDENTITY_MISMATCH,
}
LISTING_RECORD = "ollama_model_versions/v1"
LISTING_LIMIT_BYTES = 4 * 1024 * 1024
LISTING_PROVIDER = "ollama_cloud"
ENVIRONMENT_PREFIX = "env:"


def credential_variable(spec) -> str:
    """The environment variable a provider declares for its credential, or empty when it declares none."""
    reference = str(getattr(spec, "credential_ref", "") or "")
    return reference[len(ENVIRONMENT_PREFIX):] if reference.startswith(ENVIRONMENT_PREFIX) else ""


def credential_missing(spec) -> str:
    """Why the declared credential cannot be used, or empty when its variable holds a value.

    Only presence is checked: the value is not kept, returned or written anywhere."""
    name = credential_variable(spec)
    if not name:
        return f"the provider {spec.provider_id} declares no credential in the environment"
    if name not in os.environ or not os.environ[name].strip():
        return f"the provider credential variable {name} is not set in the environment"
    return ""


class GatewayReviewer:
    """One installation of a hosted model, reached only through the model gateway."""

    def __init__(self, installation, policy, context) -> None:
        raw = thawed(installation.settings)
        optional = {name: raw.pop(name) for name in OPTIONAL_FIELDS if name in raw}
        settings = read_part(raw, installation.installation_id, SETTINGS_FIELDS)
        self.output_allocation_tokens = (positive_integer(optional["output_allocation_tokens"],
                                                          "output_allocation_tokens")
                                         if "output_allocation_tokens" in optional else None)
        self.answer_format = optional.get("answer_format", JSON_ONLY)
        if self.answer_format not in ANSWER_FORMATS:
            refuse("installation_setting_invalid", f"answer_format is one of {list(ANSWER_FORMATS)}")
        self.installation, self.policy, self.context = installation, policy, context
        self.provider_id = identifier(settings["provider_id"], "provider_id")
        self.route_name = text_field(settings["route_name"], "route_name", limit=200)
        if settings["purpose"] not in PURPOSES:
            refuse("installation_setting_invalid", f"purpose is one of {list(PURPOSES)}")
        self.purpose = settings["purpose"]
        self.timeout_seconds = positive_number(settings["timeout_seconds"], "timeout_seconds")
        self.maximum_context = positive_integer(settings["maximum_context_tokens"], "maximum_context_tokens")
        self.route, self.route_refusal = None, ""
        try:
            route = ModelRoute(self.route_name, self.provider_id, installation.model, LOCALITY,
                               purposes=(self.purpose,),
                               capabilities=ModelProviderCapabilities(self.provider_id, LOCALITY,
                                                                      tokens_provider_reported=True,
                                                                      max_context=self.maximum_context))
            self.route = screen_route(route, purpose=self.purpose)
        except (ValueError, RouteViolation) as error:
            self.route_refusal = str(error)[:300]
        adapters = context.provider_adapters
        specs = builtin_provider_specs(dict(adapters)) if adapters is not None else builtin_provider_specs()
        self.spec = next((spec for spec in specs if spec.provider_id == self.provider_id), None)

    @property
    def route_or_command(self) -> str:
        return f"{self.provider_id}:{self.route_name}"

    def availability(self) -> Availability:
        if self.route is None:
            return Availability(False, "the model policy refuses this route: " + self.route_refusal, "", {},
                                REFUSED_BY_ROUTE_POLICY)
        if self.spec is None:
            return Availability(False, f"the provider {self.provider_id} is not configured", "", {},
                                ENGINE_UNAVAILABLE)
        missing = credential_missing(self.spec)
        if missing:
            return Availability(False, missing, "", {}, AUTHENTICATION_UNAVAILABLE)
        listing = self.context.model_listing
        if listing is None or self.installation.model not in listing:
            return Availability(False, "the provider's model listing does not name this model", "", {},
                                ENGINE_UNAVAILABLE)
        try:
            capability = self.spec.output_capability_for(self.installation.model)
        except UnknownModelOutputLimit:
            return Availability(False, "the model's output capacity has no source-backed record", "", {},
                                ENGINE_UNAVAILABLE)
        allocation = self.output_allocation_tokens or self.policy.output_allocation_tokens
        if capability.declared_maximum is None or capability.declared_maximum < allocation:
            return Availability(False, "the declared output allocation exceeds the model's capacity", "", {},
                                ENGINE_UNAVAILABLE)
        return Availability(True, "", f"model_gateway/{self.spec.adapter_type}", dict(listing[self.installation.model]))

    def review(self, prompt, allowance) -> ReviewerAttempt:
        if self.route is None:
            return failed(REFUSED_BY_ROUTE_POLICY, self.route_or_command, self.route_refusal)
        if self.spec is None:
            return failed(ENGINE_UNAVAILABLE, self.route_or_command, "the provider is not configured")
        missing = credential_missing(self.spec)
        if missing:
            return failed(AUTHENTICATION_UNAVAILABLE, self.route_or_command, missing)
        return invoke_once(self.spec, self.route, self.installation.model, self.purpose, prompt, allowance,
                           min(allowance.timeout_seconds, self.timeout_seconds), self.route_or_command)


def invoke_once(spec, route, model: str, purpose: str, prompt, allowance, timeout_seconds: float,
                route_or_command: str) -> ReviewerAttempt:
    """One gateway attempt on one route with no failover, read into the reviewer edge's attempt.

    The output allocation is typed and bound to the model's source-backed capacity; usage is what the
    provider reported, and a count it did not report stays unknown."""
    try:
        capability = spec.output_capability_for(model)
        allocation = ModelOutputAllocation(capability, spec.provider_id, model, route.name,
                                           allowance.max_output_tokens, ALLOCATION_DECISION, ALLOCATION_REASON)
    except (UnknownModelOutputLimit, ValueError) as error:
        return failed(ENGINE_UNAVAILABLE, route_or_command, type(error).__name__)
    gateway = ModelGateway(providers=(spec,), routes=(route,))
    config = ModelGatewayConfig(purpose=purpose, route_names=(route.name,), allow_failover=False,
                                max_route_attempts=1, timeout_seconds=timeout_seconds, output_allocation=allocation)
    request = ModelGatewayRequest(prompt=prompt.user, config=config, system=prompt.system,
                                  temperature=allowance.temperature, output_contract=VERDICT_RECORD)
    started = time.monotonic()
    result = gateway.invoke(request)
    elapsed = round(time.monotonic() - started, 3)
    physical = result.physical_provider_attempts
    last = physical[-1] if physical else (result.attempts[-1] if result.attempts else None)
    usage = Usage(last.input_tokens if last else None, last.output_tokens if last else None,
                  source=PROVIDER_REPORTED if last is not None and last.input_tokens is not None
                  and last.output_tokens is not None else USAGE_UNKNOWN)
    calls = result.physical_model_calls
    retry_after = last.retry_after_seconds if last else None
    reported = last.model if last else ""
    if result.ok:
        return ReviewerAttempt(ANSWERED, result.text, usage, calls, elapsed, None, reported,
                               route_or_command, "", "the gateway's count of physical provider requests")
    outcome = OUTCOME_FOR_ERROR.get(result.error_code, PROVIDER_FAILED)
    return failed(outcome, route_or_command, result.error_code, physical_model_calls=calls,
                  elapsed_seconds=elapsed, usage=usage, retry_after_seconds=retry_after, reported_model=reported)


def listed_model_versions(timeout: float = 30.0) -> dict:
    """The provider's served models with each one's short digest and modification time.

    A listing, not a model call. The key is read only from the environment
    variable the provider declares, and sent only in the request header; it
    never enters the record. Models the route policy forbids are named as
    withheld.
    """
    record = {"record_type": LISTING_RECORD, "ok": False, "http_status": None, "models": {}, "withheld": [],
              "error": ""}
    spec = next((item for item in builtin_provider_specs() if item.provider_id == LISTING_PROVIDER), None)
    missing = credential_missing(spec) if spec is not None else f"the provider {LISTING_PROVIDER} is not configured"
    if missing:
        record["error"] = missing
        return record
    key = os.environ[credential_variable(spec)].strip()
    request = urllib.request.Request(ollama_client.CATALOG_ENDPOINT, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(LISTING_LIMIT_BYTES + 1)
            record["http_status"] = response.status
    except urllib.error.HTTPError as error:
        record.update(http_status=error.code, error=f"the listing was refused with status {error.code}")
        return record
    except (urllib.error.URLError, OSError) as error:
        record["error"] = f"the listing could not be read: {type(error).__name__}"
        return record
    if len(raw) > LISTING_LIMIT_BYTES:
        record["error"] = "the listing is larger than this reader accepts"
        return record
    try:
        rows = json.loads(raw.decode("utf-8")).get("models") or []
    except (ValueError, AttributeError):
        record["error"] = "the listing is not a JSON object with models"
        return record
    for row in rows:
        if type(row) is not dict or not row.get("name"):
            continue
        name = str(row["name"])
        if any(name.startswith(forbidden) for forbidden in ollama_client.FORBIDDEN_MODELS):
            record["withheld"].append(name)
            continue
        record["models"][name] = {"digest": str(row.get("digest") or ""), "modified_at": str(row.get("modified_at")
                                                                                           or "")}
    record["ok"] = True
    return record
