"""Offline fixtures for the GPT-6 Astra Responses adapter.

This module uses injected transports and fixture credentials only. It opens no
socket, reads no environment credential, and proves no provider integration.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from .openai_responses_client import (
    API_URL,
    CONTEXT_WINDOW_TOKENS,
    DEFAULT_MODEL,
    MODEL_DOCUMENTATION_URL,
    MODEL_GUIDANCE_URL,
    PROVIDER_ID,
    STANDARD_SERVICE_TIER,
    SUPPORTED_REASONING_EFFORTS,
    WIRE_FORMAT,
    OpenAIResponsesAdapter,
    OpenAIResponsesCall,
    OpenAIResponsesError,
    OpenAIResponsesHTTPRequest,
    OpenAIResponsesHTTPResponse,
    normalize_response,
    output_capability_for,
)


def run_checks() -> dict:
    """Offline adapter and gateway fixtures. No credential source or socket."""
    from .model_gateway import (
        ModelGateway,
        ModelGatewayConfig,
        ModelGatewayRequest,
        builtin_provider_specs,
    )
    from .model_routes import (
        ModelProviderCapabilities,
        ModelRoute,
        default_routes,
    )
    from .provider_failover import DEFAULT_ORDER
    from .runtime_settings import ModelSettings

    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    class FixtureTransport:
        def __init__(self, bodies: list[Mapping[str, object]]) -> None:
            self.bodies = list(bodies)
            self.requests: list[OpenAIResponsesHTTPRequest] = []

        def send(
            self, request: OpenAIResponsesHTTPRequest, *, timeout: float
        ) -> OpenAIResponsesHTTPResponse:
            if timeout <= 0:
                raise AssertionError("timeout must be positive")
            self.requests.append(request)
            if not self.bodies:
                raise AssertionError("fixture transport exhausted")
            return OpenAIResponsesHTTPResponse(200, self.bodies.pop(0))

    success_body = {
        "id": "resp_fixture_astra",
        "object": "response",
        "status": "completed",
        "incomplete_details": None,
        "model": DEFAULT_MODEL,
        "service_tier": "default",
        "output": [
            {
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "READY"}],
            }
        ],
        "usage": {
            "input_tokens": 31,
            "input_tokens_details": {"cached_tokens": 7},
            "output_tokens": 19,
            "output_tokens_details": {"reasoning_tokens": 11},
            "total_tokens": 50,
        },
    }
    fixture = FixtureTransport([success_body])
    key_reads = 0

    def fixture_key() -> str:
        nonlocal key_reads
        key_reads += 1
        return "offline-fixture-key"

    adapter = OpenAIResponsesAdapter(
        transport=fixture,
        api_key_source=fixture_key,
        reasoning_effort="medium",
    )
    specs = builtin_provider_specs({PROVIDER_ID: adapter})
    spec = specs[0]
    route = ModelRoute(
        "fixture.openai.astra",
        PROVIDER_ID,
        DEFAULT_MODEL,
        "cloud",
        purposes=("reasoning",),
        capabilities=ModelProviderCapabilities(
            PROVIDER_ID,
            "cloud",
            True,
            supports_structured_output=False,
            supports_tool_calls=False,
            max_context=CONTEXT_WINDOW_TOKENS,
        ),
    )
    gateway = ModelGateway(providers=specs, routes=(route,))
    gateway_result = gateway.invoke(
        ModelGatewayRequest(
            "Return READY.",
            ModelGatewayConfig(
                purpose="reasoning",
                route_names=(route.name,),
                allow_failover=False,
                max_route_attempts=1,
                max_output_tokens=128_000,
            ),
            system="Return plain text.",
            temperature=0.91,
        )
    )
    sent = fixture.requests[0] if fixture.requests else None
    expected_keys = {
        "model",
        "input",
        "instructions",
        "max_output_tokens",
        "reasoning",
        "service_tier",
        "store",
    }
    check(
        "astra_uses_the_exact_responses_request_contract",
        gateway_result.ok
        and gateway_result.provider == PROVIDER_ID
        and gateway_result.model == DEFAULT_MODEL
        and sent is not None
        and sent.method == "POST"
        and sent.endpoint == API_URL
        and set(sent.payload) == expected_keys
        and sent.payload["model"] == DEFAULT_MODEL
        and sent.payload["max_output_tokens"] == 128_000
        and sent.payload["reasoning"] == {"effort": "medium"}
        and sent.payload["service_tier"] == STANDARD_SERVICE_TIER
        and sent.payload["store"] is False
        and sent.payload["instructions"] == "Return plain text."
        and sent.headers.get("Authorization") == "Bearer offline-fixture-key"
        and key_reads == 1,
        "offline injected transport; no provider call",
    )
    unsupported_fields = {
        "temperature",
        "top_p",
        "top_logprobs",
        "logprobs",
        "include",
        "tools",
        "tool_choice",
    }
    check(
        "unsupported_sampling_logprob_and_tool_fields_are_omitted",
        sent is not None and not (unsupported_fields & set(sent.payload)),
        "gateway temperature is a compatibility input and is not sent",
    )
    safe_summary = sent.safe_summary() if sent is not None else {}
    check(
        "request_summary_hashes_private_prompt_and_instruction_text",
        "Return READY." not in json.dumps(safe_summary)
        and "Return plain text." not in json.dumps(safe_summary)
        and safe_summary.get("private_text_recorded") is False
        and safe_summary.get("input", {}).get("characters") == 13
        and bool(safe_summary.get("input", {}).get("sha256")),
    )
    check(
        "authorization_headers_are_hidden_from_request_repr",
        sent is not None
        and "offline-fixture-key" not in repr(sent)
        and "Authorization" not in repr(sent),
    )
    attempt = gateway_result.attempts[0]
    check(
        "provider_usage_status_and_stop_details_survive_the_gateway",
        gateway_result.input_tokens == 31
        and gateway_result.output_tokens == 19
        and attempt.provider_status == "completed"
        and attempt.provider_response_id == "resp_fixture_astra"
        and attempt.provider_service_tier == "default"
        and attempt.provider_incomplete_details == {}
        and attempt.provider_usage.get("input_tokens_details") == {"cached_tokens": 7}
        and attempt.provider_done is True
        and attempt.provider_stop_reason == "completed"
        and not attempt.output_limit_reached,
        "all values came from the injected provider-shaped response",
    )
    check(
        "the_output_capability_is_exact_and_source_backed",
        output_capability_for(DEFAULT_MODEL).maximum_output_tokens == 128_000
        and output_capability_for(DEFAULT_MODEL).endpoint == API_URL
        and output_capability_for(DEFAULT_MODEL).observed_at == "2026-09-04"
        and MODEL_DOCUMENTATION_URL in output_capability_for(DEFAULT_MODEL).source
        and MODEL_DOCUMENTATION_URL.startswith("https://developers.openai.com/")
        and MODEL_GUIDANCE_URL.startswith("https://developers.openai.com/"),
        "official OpenAI documentation observed 2026-09-04",
    )
    check(
        "all_and_only_documented_astra_reasoning_efforts_are_accepted",
        all(
            OpenAIResponsesCall("x", reasoning_effort=value)
            for value in SUPPORTED_REASONING_EFFORTS
        ),
    )
    refused_efforts = 0
    for value in ("none", "minimal", "ultra", ""):
        try:
            OpenAIResponsesCall("x", reasoning_effort=value)
        except OpenAIResponsesError:
            refused_efforts += 1
    check(
        "undocumented_or_unsupported_reasoning_efforts_fail_closed",
        refused_efforts == 4,
        "none and minimal are not valid for GPT-6 Astra",
    )
    nonstandard_tier_refused = False
    try:
        OpenAIResponsesCall("x", service_tier="auto")
    except OpenAIResponsesError:
        nonstandard_tier_refused = True
    check(
        "only_explicit_standard_service_tier_is_accepted",
        nonstandard_tier_refused,
        "Standard is encoded on the wire as service_tier=default",
    )

    no_key_transport = FixtureTransport([success_body])
    no_key_adapter = OpenAIResponsesAdapter(
        transport=no_key_transport,
        api_key_source=lambda: "",
    )
    missing_key = no_key_adapter.chat_maxout("x")
    check(
        "a_missing_key_fails_before_the_transport",
        not missing_key.ok
        and "OPENAI_API_KEY" in missing_key.error
        and not no_key_transport.requests,
    )
    catalog_transport = FixtureTransport(
        [
            {"data": [{"id": DEFAULT_MODEL}, {"id": "other-model"}]},
        ]
    )
    catalog_adapter = OpenAIResponsesAdapter(
        transport=catalog_transport,
        api_key_source=lambda: "offline-fixture-key",
    )
    check(
        "live_catalog_confirmation_uses_a_bodyless_GET_contract",
        catalog_adapter.live_models() == [DEFAULT_MODEL]
        and len(catalog_transport.requests) == 1
        and catalog_transport.requests[0].method == "GET"
        and catalog_transport.requests[0].payload == {},
        "injected transport only",
    )
    unknown = no_key_adapter.chat_maxout("x", model="gpt-6-astra-preview")
    check(
        "an_unknown_model_capability_fails_before_key_or_transport",
        not unknown.ok
        and "unknown_model_output_limit" in unknown.error
        and not no_key_transport.requests,
    )

    incomplete_body = {
        **success_body,
        "id": "resp_fixture_incomplete",
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
    }
    incomplete_transport = FixtureTransport([incomplete_body])
    incomplete = OpenAIResponsesAdapter(
        transport=incomplete_transport,
        api_key_source=lambda: "offline-fixture-key",
    ).chat_maxout("x")
    check(
        "an_incomplete_output_limit_is_not_accepted_as_success",
        not incomplete.ok
        and incomplete.response_received
        and incomplete.done is False
        and incomplete.done_reason == "max_output_tokens"
        and incomplete.output_limit_reached
        and incomplete.provider_incomplete_details == {"reason": "max_output_tokens"},
    )

    missing_model_body = dict(success_body)
    missing_model_body.pop("model")
    missing_model = normalize_response(
        OpenAIResponsesHTTPResponse(200, missing_model_body),
        expected_model=DEFAULT_MODEL,
        maximum_output_tokens=128_000,
    )
    check(
        "a_missing_provider_model_identity_fails_closed",
        not missing_model.ok
        and not missing_model.model
        and "model_identity_missing" in missing_model.error,
    )

    wrong_tier_body = {**success_body, "service_tier": "priority"}
    wrong_tier = normalize_response(
        OpenAIResponsesHTTPResponse(200, wrong_tier_body),
        expected_model=DEFAULT_MODEL,
        maximum_output_tokens=128_000,
    )
    check(
        "a_present_nonstandard_provider_service_tier_fails_closed",
        not wrong_tier.ok
        and wrong_tier.provider_service_tier == "priority"
        and "service_tier_mismatch" in wrong_tier.error,
    )

    absent_tier_body = dict(success_body)
    absent_tier_body.pop("service_tier")
    absent_tier = normalize_response(
        OpenAIResponsesHTTPResponse(200, absent_tier_body),
        expected_model=DEFAULT_MODEL,
        maximum_output_tokens=128_000,
    )
    check(
        "an_absent_provider_service_tier_remains_admissible_but_unknown",
        absent_tier.ok and not absent_tier.provider_service_tier,
        "the Responses contract requires validation when the field is present",
    )

    tool_body = {
        **success_body,
        "id": "resp_fixture_tool",
        "output": [
            {
                "type": "function_call",
                "call_id": "call_fixture",
                "name": "do_work",
                "arguments": "{}",
            }
        ],
    }
    tool_transport = FixtureTransport([tool_body])
    tool_result = OpenAIResponsesAdapter(
        transport=tool_transport,
        api_key_source=lambda: "offline-fixture-key",
    ).chat_maxout("x")
    check(
        "tool_call_output_is_preserved_as_an_explicit_unsupported_failure",
        not tool_result.ok
        and tool_result.unsupported_output_types == ("function_call",)
        and "unsupported_tool_call" in tool_result.error,
        "the adapter never executes a provider-requested tool",
    )

    private_error = normalize_response(
        OpenAIResponsesHTTPResponse(
            400,
            {
                "status": "failed",
                "model": DEFAULT_MODEL,
                "error": {
                    "code": "invalid_request",
                    "type": "request_error",
                    "message": "private prompt must not enter normalized evidence",
                },
            },
        ),
        expected_model=DEFAULT_MODEL,
        maximum_output_tokens=128_000,
    )
    check(
        "normalized_provider_errors_exclude_raw_private_messages",
        not private_error.ok
        and private_error.error == "HTTP 400: provider returned an error"
        and "private prompt" not in json.dumps(private_error.to_dict())
        and private_error.response_status.error
        == {
            "code": "invalid_request",
            "type": "request_error",
        },
    )

    wrong_verify_transport = FixtureTransport(
        [
            {
                **success_body,
                "output": [
                    {
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "NOT READY"}],
                    }
                ],
            },
        ]
    )
    wrong_verify = OpenAIResponsesAdapter(
        transport=wrong_verify_transport,
        api_key_source=lambda: "offline-fixture-key",
    ).verify()
    exact_verify_transport = FixtureTransport([success_body])
    exact_verify = OpenAIResponsesAdapter(
        transport=exact_verify_transport,
        api_key_source=lambda: "offline-fixture-key",
    ).verify()
    check(
        "live_verification_requires_the_exact_ready_text",
        not wrong_verify["ok"]
        and "verification_response_mismatch" in wrong_verify["error"]
        and exact_verify["ok"],
        "both exchanges use injected transports",
    )

    check(
        "astra_is_not_eligible_from_a_credential_or_default_alone",
        PROVIDER_ID not in DEFAULT_ORDER
        and all(route.provider != PROVIDER_ID for route in default_routes())
        and PROVIDER_ID not in ModelSettings().enabled_provider_ids(),
        "a future route needs explicit paid-model authority and a live probe",
    )
    check(
        "explicit_provider_spec_uses_responses_metadata_without_a_route",
        spec.provider_id == PROVIDER_ID
        and spec.adapter_type == WIRE_FORMAT
        and spec.credential_ref == "env:OPENAI_API_KEY"
        and spec.endpoint == API_URL
        and spec.wire_format == WIRE_FORMAT
        and "responses" in spec.capabilities,
    )

    passed = sum(1 for item in results if item["passed"])
    return {
        "record_type": "openai_astra_responses_contract_test/v1",
        "scope": "offline_injected_transport_only",
        "model": DEFAULT_MODEL,
        "endpoint": API_URL,
        "provider_integration_proven": False,
        "tools_supported_by_this_adapter": False,
        "route_registered": False,
        "network_calls": 0,
        "environment_credential_reads": 0,
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }
