"""Offline-ready OpenAI Responses adapter for the exact GPT-6 Astra route.

Architectural role: internal model provider adapter.

This module implements the existing ``ProviderAdapter`` protocol for one
source-backed model contract. It does not register a route, inspect whether a
credential exists at import time, select a model, approve paid use, execute a
tool call, or claim live provider integration.

The current contract is intentionally narrow:

* endpoint: OpenAI Responses API;
* model: ``gpt-6-astra``;
* maximum output: 128,000 tokens;
* reasoning effort: low, medium, high, xhigh, or max;
* processing: explicit Standard tier (``service_tier="default"``);
* text input and text output only;
* no tool definitions and no tool-call execution.

The model and capacity facts are from the official OpenAI model page observed
on 2026-09-04. The request compatibility rules are from the official current
model guidance observed on the same date. Offline fixtures prove only request
construction, refusal behavior, response normalization, and compatibility
with ``ModelGateway``. A separately authorized live probe is still required.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from .model_capabilities import (
    ModelOutputCapability,
    ModelOutputLimitMismatch,
    UnknownModelOutputLimit,
    require_declared_maximum,
)

PROVIDER_ID = "openai"
API_URL = "https://api.openai.com/v1/responses"
MODELS_URL = "https://api.openai.com/v1/models"
DEFAULT_MODEL = "gpt-6-astra"
DEFAULT_REASONING_EFFORT = "high"
SUPPORTED_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
STANDARD_SERVICE_TIER = "default"
CONTEXT_WINDOW_TOKENS = 1_050_000
WIRE_FORMAT = "openai_responses"
PROVIDER_CAPABILITIES = (
    "responses",
    "text_input",
    "text_output",
    "provider_reported_usage",
    "verify",
    "list_models",
)
MODEL_DOCUMENTATION_URL = "https://developers.openai.com/api/docs/models/gpt-6-astra"
MODEL_GUIDANCE_URL = "https://developers.openai.com/api/docs/guides/latest-model"

MODEL_OUTPUT_CAPABILITIES = {
    DEFAULT_MODEL: ModelOutputCapability(
        128_000,
        f"OpenAI GPT-6 Astra model documentation {MODEL_DOCUMENTATION_URL}, "
        "observed 2026-09-04",
        endpoint=API_URL,
        observed_at="2026-09-04",
    ),
}
MODEL_MAX_OUTPUT = {
    name: capability.maximum_output_tokens
    for name, capability in MODEL_OUTPUT_CAPABILITIES.items()
}


class OpenAIResponsesError(ValueError):
    """The local Responses request or response contract is invalid."""


class OpenAIResponsesHTTPError(OSError):
    """The physical Responses HTTP exchange failed."""

    def __init__(self, status_code: int, error_code: str = "") -> None:
        self.status_code = int(status_code)
        candidate = str(error_code or "unclassified")
        self.error_code = (
            candidate
            if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", candidate)
            else "unclassified"
        )
        super().__init__(
            f"HTTP {self.status_code}: provider_error_code={self.error_code}"
        )


@dataclass(frozen=True)
class OpenAIResponsesCall:
    """One exact text-only Astra request before transport binding."""

    prompt: str
    model: str = DEFAULT_MODEL
    system: str = ""
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    max_output_tokens: int | None = None
    store: bool = False
    service_tier: str = STANDARD_SERVICE_TIER

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise OpenAIResponsesError("an Astra call needs a prompt")
        if self.model != DEFAULT_MODEL:
            raise UnknownModelOutputLimit(
                "unknown_model_output_limit: the offline-ready OpenAI "
                f"Responses adapter supports only {DEFAULT_MODEL!r}, not "
                f"{self.model!r}"
            )
        if self.reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
            raise OpenAIResponsesError(
                "GPT-6 Astra reasoning effort must be low, medium, high, xhigh, or max"
            )
        if not isinstance(self.store, bool):
            raise OpenAIResponsesError("store must be boolean")
        if self.service_tier != STANDARD_SERVICE_TIER:
            raise OpenAIResponsesError(
                "the quarantined Astra adapter supports only explicit "
                "Standard processing with service_tier='default'"
            )


@dataclass(frozen=True)
class OpenAIResponsesHTTPRequest:
    """Transport request. Its safe summary never exposes header values."""

    method: str
    endpoint: str
    headers: Mapping[str, str] = field(repr=False)
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.method not in {"GET", "POST"}:
            raise OpenAIResponsesError("Responses HTTP method is unsupported")
        if self.endpoint not in {API_URL, MODELS_URL}:
            raise OpenAIResponsesError("OpenAI endpoint is not admitted")
        if not isinstance(self.headers, Mapping) or not isinstance(
            self.payload, Mapping
        ):
            raise OpenAIResponsesError("HTTP headers and payload must be mappings")

    def safe_summary(self) -> dict:
        payload = dict(self.payload)

        def private_text(name: str) -> dict:
            value = str(payload.get(name, "") or "")
            return {
                "present": bool(value),
                "characters": len(value),
                "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()
                if value
                else "",
            }

        return {
            "method": self.method,
            "endpoint": self.endpoint,
            "header_names": sorted(self.headers),
            "payload_fields": sorted(payload),
            "model": str(payload.get("model", "") or ""),
            "max_output_tokens": payload.get("max_output_tokens"),
            "reasoning": dict(_mapping(payload.get("reasoning"))),
            "service_tier": payload.get("service_tier"),
            "store": payload.get("store"),
            "input": private_text("input"),
            "instructions": private_text("instructions"),
            "private_text_recorded": False,
        }


@dataclass(frozen=True)
class OpenAIResponsesHTTPResponse:
    """One decoded provider response returned by a transport."""

    status_code: int
    body: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.status_code, int) or isinstance(self.status_code, bool):
            raise OpenAIResponsesError("HTTP status code must be an integer")
        if not isinstance(self.body, Mapping):
            raise OpenAIResponsesError("Responses body must be an object")


class OpenAIResponsesTransport(Protocol):
    """Physical transport behind the provider adapter."""

    def send(
        self, request: OpenAIResponsesHTTPRequest, *, timeout: float
    ) -> OpenAIResponsesHTTPResponse: ...


@dataclass(frozen=True)
class OpenAIResponsesUsage:
    """Provider-reported token fields, including supported detail fields."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    provider_fields: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "reasoning_output_tokens": self.reasoning_output_tokens,
            "provider_fields": dict(self.provider_fields),
        }


@dataclass(frozen=True)
class OpenAIResponsesStatus:
    """Provider response identity and terminal status fields."""

    response_id: str = ""
    status: str = ""
    incomplete_details: Mapping[str, object] = field(default_factory=dict)
    service_tier: str = ""
    error: Mapping[str, object] = field(default_factory=dict)

    @property
    def incomplete_reason(self) -> str:
        return str(self.incomplete_details.get("reason", "") or "")

    def to_dict(self) -> dict:
        return {
            "response_id": self.response_id,
            "status": self.status,
            "incomplete_details": dict(self.incomplete_details),
            "service_tier": self.service_tier,
            "error": dict(self.error),
        }


@dataclass(frozen=True)
class OpenAIResponsesResult:
    """Provider-neutral fields plus exact Responses usage and status data."""

    text: str
    model: str
    ok: bool
    error: str = ""
    usage: OpenAIResponsesUsage = field(default_factory=OpenAIResponsesUsage)
    response_status: OpenAIResponsesStatus = field(
        default_factory=OpenAIResponsesStatus
    )
    num_predict_used: int = 0
    response_received: bool = False
    done: bool | None = None
    done_reason: str = ""
    reasoning_present: bool = False
    output_limit_reached: bool = False
    unsupported_output_types: tuple[str, ...] = ()
    provider: str = PROVIDER_ID
    attempts: int = 1

    @property
    def prompt_tokens(self) -> int | None:
        return self.usage.input_tokens

    @property
    def eval_tokens(self) -> int | None:
        return self.usage.output_tokens

    @property
    def total_tokens(self) -> int | None:
        return self.usage.total_tokens

    @property
    def provider_status(self) -> str:
        return self.response_status.status

    @property
    def provider_response_id(self) -> str:
        return self.response_status.response_id

    @property
    def provider_service_tier(self) -> str:
        return self.response_status.service_tier

    @property
    def provider_incomplete_details(self) -> Mapping[str, object]:
        return self.response_status.incomplete_details

    @property
    def provider_usage(self) -> Mapping[str, object]:
        return self.usage.provider_fields

    def to_dict(self) -> dict:
        return {
            "record_type": "openai_responses_result/v1",
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "ok": self.ok,
            "error": self.error,
            "usage": self.usage.to_dict(),
            "response_status": self.response_status.to_dict(),
            "num_predict_used": self.num_predict_used,
            "response_received": self.response_received,
            "done": self.done,
            "done_reason": self.done_reason,
            "reasoning_present": self.reasoning_present,
            "output_limit_reached": self.output_limit_reached,
            "unsupported_output_types": list(self.unsupported_output_types),
        }


class UrllibOpenAIResponsesTransport:
    """Dependency-free HTTPS transport used only after route authorization."""

    def send(
        self, request: OpenAIResponsesHTTPRequest, *, timeout: float
    ) -> OpenAIResponsesHTTPResponse:
        encoded = json.dumps(request.payload).encode("utf-8")
        wire_request = urllib.request.Request(
            request.endpoint,
            data=(None if request.method == "GET" else encoded),
            method=request.method,
            headers=dict(request.headers),
        )
        try:
            with urllib.request.urlopen(wire_request, timeout=timeout) as reply:
                status_code = int(getattr(reply, "status", 200))
                body = json.loads(reply.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_code = "unclassified"
            try:
                error_body = json.loads(exc.read()[:4096].decode("utf-8", "replace"))
                candidate = _mapping(_mapping(error_body).get("error"))
                error_code = str(
                    candidate.get("code") or candidate.get("type") or "unclassified"
                )
            except (OSError, UnicodeDecodeError, ValueError):
                pass
            raise OpenAIResponsesHTTPError(exc.code, error_code) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise OpenAIResponsesHTTPError(0, type(exc).__name__) from exc
        return OpenAIResponsesHTTPResponse(status_code, body)


def output_capability_for(model: str) -> ModelOutputCapability:
    """Return the official exact Astra output maximum or fail closed."""
    if model != DEFAULT_MODEL:
        raise UnknownModelOutputLimit(
            "unknown_model_output_limit: no exact OpenAI Responses "
            f"capability for model={model!r}, endpoint={API_URL!r}"
        )
    return MODEL_OUTPUT_CAPABILITIES[DEFAULT_MODEL]


def _token(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _json_copy(value: Mapping[str, object]) -> Mapping[str, object]:
    """Detach provider JSON from a mutable transport fixture."""
    try:
        copied = json.loads(json.dumps(dict(value)))
    except (TypeError, ValueError):
        return {}
    return copied if isinstance(copied, dict) else {}


def build_http_request(
    call: OpenAIResponsesCall, api_key: str
) -> OpenAIResponsesHTTPRequest:
    """Compile one exact Responses request without opening a socket."""
    if not isinstance(call, OpenAIResponsesCall):
        raise TypeError("build_http_request needs OpenAIResponsesCall")
    if not isinstance(api_key, str) or not api_key.strip():
        raise OpenAIResponsesError("OPENAI_API_KEY is not configured")
    capability = output_capability_for(call.model)
    maximum = require_declared_maximum(call.max_output_tokens, capability)
    payload: dict[str, object] = {
        "model": call.model,
        "input": call.prompt,
        "max_output_tokens": maximum,
        "reasoning": {"effort": call.reasoning_effort},
        "service_tier": call.service_tier,
        "store": call.store,
    }
    if call.system:
        payload["instructions"] = call.system
    return OpenAIResponsesHTTPRequest(
        method="POST",
        endpoint=API_URL,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        payload=payload,
    )


def _response_text(body: Mapping[str, object]) -> tuple[str, tuple[str, ...], bool]:
    text_parts: list[str] = []
    unsupported: list[str] = []
    reasoning_present = False
    output = body.get("output")
    for item in output if isinstance(output, list) else ():
        if not isinstance(item, Mapping):
            unsupported.append("non_object_output")
            continue
        item_type = str(item.get("type", "") or "")
        if item_type == "reasoning":
            reasoning_present = True
            continue
        if item_type != "message":
            unsupported.append(item_type or "unknown_output")
            continue
        content = item.get("content")
        for part in content if isinstance(content, list) else ():
            if not isinstance(part, Mapping):
                unsupported.append("non_object_content")
                continue
            part_type = str(part.get("type", "") or "")
            if part_type == "output_text":
                value = part.get("text")
                if isinstance(value, str) and value:
                    text_parts.append(value)
            elif part_type:
                unsupported.append(part_type)
            else:
                unsupported.append("unknown_content")
    return "".join(text_parts), tuple(unsupported), reasoning_present


def normalize_response(
    response: OpenAIResponsesHTTPResponse,
    *,
    expected_model: str,
    maximum_output_tokens: int,
    expected_service_tier: str = STANDARD_SERVICE_TIER,
) -> OpenAIResponsesResult:
    """Normalize one decoded Responses object without executing tool calls."""
    body = response.body
    usage_body = _mapping(body.get("usage"))
    input_details = _mapping(usage_body.get("input_tokens_details"))
    output_details = _mapping(usage_body.get("output_tokens_details"))
    usage = OpenAIResponsesUsage(
        input_tokens=_token(usage_body.get("input_tokens")),
        output_tokens=_token(usage_body.get("output_tokens")),
        total_tokens=_token(usage_body.get("total_tokens")),
        cached_input_tokens=_token(input_details.get("cached_tokens")),
        reasoning_output_tokens=_token(output_details.get("reasoning_tokens")),
        provider_fields=_json_copy(usage_body),
    )
    status_name = str(body.get("status", "") or "")
    incomplete = _mapping(body.get("incomplete_details"))
    error_body = _mapping(body.get("error"))
    safe_error = {
        name: str(error_body.get(name, "") or "")[:120]
        for name in ("code", "type", "param")
        if error_body.get(name) is not None
    }
    status = OpenAIResponsesStatus(
        response_id=str(body.get("id", "") or ""),
        status=status_name,
        incomplete_details=_json_copy(incomplete),
        service_tier=str(body.get("service_tier", "") or ""),
        error=safe_error,
    )
    reported_model = str(body.get("model", "") or "")
    text, unsupported, reasoning_present = _response_text(body)
    incomplete_reason = status.incomplete_reason
    output_limit_reached = incomplete_reason in {
        "max_output_tokens",
        "max_tokens",
        "length",
    }
    done: bool | None
    if status_name == "completed":
        done = True
    elif status_name:
        done = False
    else:
        done = None
    done_reason = incomplete_reason or status_name
    error = ""
    if response.status_code < 200 or response.status_code >= 300:
        error = f"HTTP {response.status_code}: provider returned an error"
    elif not reported_model:
        error = (
            "model_identity_missing: the provider response did not report "
            "the exact model identity"
        )
    elif reported_model != expected_model:
        error = (
            "model_identity_mismatch: requested exact model "
            f"{expected_model!r}, provider reported {reported_model!r}"
        )
    elif status.service_tier and status.service_tier != expected_service_tier:
        error = (
            "service_tier_mismatch: requested exact service tier "
            f"{expected_service_tier!r}, provider reported "
            f"{status.service_tier!r}"
        )
    elif any(value.endswith("_call") for value in unsupported):
        error = (
            "unsupported_tool_call: this text-only adapter does not execute "
            f"Responses output types {sorted(set(unsupported))}"
        )
    elif unsupported:
        error = (
            "unsupported_response_output: this text-only adapter cannot admit "
            f"Responses output types {sorted(set(unsupported))}"
        )
    elif output_limit_reached:
        error = (
            "output_limit_reached: Responses status was incomplete with "
            f"reason {incomplete_reason!r}"
        )
    elif error_body:
        code = str(error_body.get("code", "") or "provider_error")
        error = f"provider_error:{code}"
    elif status_name != "completed":
        error = (
            f"incomplete_response: Responses status was {status_name or 'missing'!r}"
        )
    elif not text:
        error = "empty_response: Responses returned no output text"
    return OpenAIResponsesResult(
        text=text,
        model=reported_model,
        ok=not error and bool(text),
        error=error,
        usage=usage,
        response_status=status,
        num_predict_used=maximum_output_tokens,
        response_received=True,
        done=done,
        done_reason=done_reason,
        reasoning_present=(reasoning_present or bool(usage.reasoning_output_tokens)),
        output_limit_reached=output_limit_reached,
        unsupported_output_types=unsupported,
    )


class OpenAIResponsesAdapter:
    """ProviderAdapter implementation with injectable transport and key source."""

    DEFAULT_MODEL = DEFAULT_MODEL
    WIRE_FORMAT = WIRE_FORMAT
    PROVIDER_CAPABILITIES = PROVIDER_CAPABILITIES

    def __init__(
        self,
        *,
        transport: OpenAIResponsesTransport | None = None,
        api_key_source: Callable[[], str | None] | None = None,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    ) -> None:
        if reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
            raise OpenAIResponsesError(
                "GPT-6 Astra reasoning effort must be low, medium, high, xhigh, or max"
            )
        self._transport = transport or UrllibOpenAIResponsesTransport()
        self._api_key_source = api_key_source or (
            lambda: os.environ.get("OPENAI_API_KEY")
        )
        self.reasoning_effort = reasoning_effort

    @staticmethod
    def output_capability_for(model: str) -> ModelOutputCapability:
        return output_capability_for(model)

    def chat_maxout(
        self,
        prompt: str,
        *,
        model: str = DEFAULT_MODEL,
        system: str = "",
        temperature: float = 0.7,
        timeout: float = 900.0,
        max_attempts: int = 1,
        max_output_tokens: int | None = None,
        output_capability: ModelOutputCapability | None = None,
    ) -> OpenAIResponsesResult:
        """Make one Responses call after exact local contract checks."""
        del temperature
        if max_attempts != 1:
            return OpenAIResponsesResult(
                "",
                model,
                False,
                error=("physical model retries require an explicit outer call budget"),
            )
        try:
            call = OpenAIResponsesCall(
                prompt=prompt,
                model=model,
                system=system,
                reasoning_effort=self.reasoning_effort,
                max_output_tokens=max_output_tokens,
            )
            capability = output_capability or output_capability_for(model)
            maximum = require_declared_maximum(max_output_tokens, capability)
            if capability != output_capability_for(model):
                raise ModelOutputLimitMismatch(
                    "model_output_limit_mismatch: supplied capability does "
                    "not match the exact source-backed Astra capability"
                )
            api_key = self._api_key_source()
            request = build_http_request(call, str(api_key or ""))
            response = self._transport.send(request, timeout=timeout)
            return normalize_response(
                response,
                expected_model=model,
                maximum_output_tokens=maximum,
                expected_service_tier=call.service_tier,
            )
        except (
            OpenAIResponsesError,
            OpenAIResponsesHTTPError,
            UnknownModelOutputLimit,
            ModelOutputLimitMismatch,
        ) as exc:
            return OpenAIResponsesResult("", model, False, error=str(exc))

    def live_models(self) -> list[str]:
        """List only the exact supported model when the live catalog confirms it."""
        api_key = str(self._api_key_source() or "").strip()
        if not api_key:
            return []
        request = OpenAIResponsesHTTPRequest(
            "GET",
            MODELS_URL,
            {"Authorization": f"Bearer {api_key}"},
            {},
        )
        try:
            response = self._transport.send(request, timeout=30.0)
        except (OpenAIResponsesHTTPError, OSError, ValueError):
            return []
        rows = response.body.get("data")
        names = (
            {str(row.get("id", "") or "") for row in rows if isinstance(row, Mapping)}
            if isinstance(rows, list)
            else set()
        )
        return [DEFAULT_MODEL] if DEFAULT_MODEL in names else []

    def verify(self, model: str = DEFAULT_MODEL) -> dict:
        """Perform one live text call. Callers must authorize it externally."""
        result = self.chat_maxout(
            "Reply with exactly the word READY.", model=model, timeout=60.0
        )
        exact_ready = bool(result.ok and result.text == "READY")
        error = result.error
        if result.ok and not exact_ready:
            error = "verification_response_mismatch: expected exactly READY"
        return {
            "record_type": "openai_astra_verify/v1",
            "provider": PROVIDER_ID,
            "model": result.model,
            "ok": exact_ready,
            "prompt_tokens": result.prompt_tokens,
            "eval_tokens": result.eval_tokens,
            "provider_status": result.provider_status,
            "error": error[:200],
            "text": result.text[:80],
        }


def self_test() -> dict:
    """Run offline fixtures without reading credentials or opening a socket."""
    from .openai_responses_client_checks import run_checks

    return run_checks()


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
