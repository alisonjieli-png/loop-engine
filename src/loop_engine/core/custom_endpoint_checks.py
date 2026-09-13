"""Controls for the custom endpoint's Ollama-wire streaming, refusal
detail, body faults, think control, and classified model listing.

Every check answers through a fixture opener that never opens a socket,
so the contract holds offline before a live provider is spent on it.
"""
from __future__ import annotations

import email.message
import io
import json

from . import custom_endpoint as ce
from .custom_endpoint import (CustomEndpoint, EndpointError, forget_learned_stream_modes,
                              learned_stream_mode, make_adapter)
from .model_capabilities import ModelOutputCapability
from .model_gateway import _error_code
from .provider_failure_classes import ALLOWANCE, OUTAGE, failure_class


def _http_error(code, body=b"", headers=None):
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value
    # The error class comes from the adapter module's own namespace: this
    # module opens no socket and imports no network module.
    return ce.urllib.error.HTTPError("https://fixture.invalid/", code, f"status {code}", message,
                                     io.BytesIO(body))


class _Response:
    def __init__(self, body=b"", lines=()):
        self._body = body
        self._lines = list(lines)

    def read(self, limit=None):
        return self._body if limit is None else self._body[:limit]

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Opener:
    """Answers each open() from a script; the last item repeats."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def open(self, request, timeout=None):
        data = request.data
        self.requests.append({"url": request.full_url,
                              "json": json.loads(data.decode()) if data else None})
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        return item


def _endpoint(**overrides) -> CustomEndpoint:
    fields = {"name": "checks_box", "base_url": "https://box.example/", "model": "gpt-oss:20b",
              "wire": "ollama", "stream": "stream", "auth_scheme": "none",
              "output_capability": ModelOutputCapability(131072, "checks")}
    fields.update(overrides)
    return CustomEndpoint(**fields)


def _ndjson(*objects):
    return [json.dumps(item).encode() + b"\n" for item in objects]


def _chat(endpoint, opener, prompt="say online"):
    saved_opener, saved_slot = ce._endpoint_opener, ce._claim_call_slot
    ce._endpoint_opener = lambda ep: opener
    ce._claim_call_slot = lambda name: 0.0
    try:
        return make_adapter(endpoint).chat(prompt, max_tokens=0, temperature=0.0, timeout=5)
    finally:
        ce._endpoint_opener, ce._claim_call_slot = saved_opener, saved_slot


def _listing(endpoint, opener):
    saved = ce._endpoint_opener
    ce._endpoint_opener = lambda ep: opener
    try:
        return make_adapter(endpoint).live_model_listing(), make_adapter(endpoint).live_models()
    finally:
        ce._endpoint_opener = saved


def run_checks():
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    forget_learned_stream_modes()
    stream = _ndjson(
        {"model": "gpt-oss:20b", "message": {"role": "assistant", "content": "on"}, "done": False},
        {"model": "gpt-oss:20b", "message": {"role": "assistant", "content": "line",
                                             "thinking": "quietly"}, "done": False},
        {"model": "gpt-oss:20b", "message": {"role": "assistant", "content": ""}, "done": True,
         "done_reason": "stop", "prompt_eval_count": 11, "eval_count": 2})
    opener = _Opener([_Response(lines=stream)])
    result = _chat(_endpoint(), opener)
    check("the_ollama_wire_streams_as_newline_delimited_json_and_joins_the_deltas",
          result.ok and result.text == "online" and result.prompt_tokens == 11
          and result.eval_tokens == 2 and result.done_reason == "stop" and result.done is True
          and result.reasoning_present and result.delivered_by_stream
          and opener.requests[0]["json"]["stream"] is True
          and "stream_options" not in opener.requests[0]["json"],
          result.error or result.text)
    result = _chat(_endpoint(), _Opener([_Response(lines=stream[:2])]))
    check("a_stream_that_ends_without_a_done_line_is_incomplete_not_an_answer",
          not result.ok and result.done is False and result.text == "online"
          and result.error.startswith("incomplete_response"), result.error)
    result = _chat(_endpoint(), _Opener([_Response(lines=[
        b'data: {"message": {"content": "framed"}, "done": false}\n',
        b': keep-alive\n',
        b'data: {"message": {"content": ""}, "done": true, "done_reason": "stop", '
        b'"prompt_eval_count": 3, "eval_count": 1}\n'])]))
    check("a_proxy_that_reframes_the_stream_as_sse_still_parses",
          result.ok and result.text == "framed" and result.eval_tokens == 1, result.error)

    auto = _endpoint(name="auto_box", stream="auto")
    opener = _Opener([_http_error(504, b"upstream timed out"), _Response(lines=stream)])
    first = _chat(auto, opener)
    second_opener = _Opener([_Response(lines=stream)])
    second = _chat(auto, second_opener)
    check("auto_mode_learns_that_this_endpoint_needs_streaming_and_streams_first_next_time",
          first.ok and first.delivered_by_stream and len(opener.requests) == 2
          and opener.requests[0]["json"]["stream"] is False
          and opener.requests[1]["json"]["stream"] is True
          and learned_stream_mode("auto_box") == "stream"
          and second.ok and len(second_opener.requests) == 1
          and second_opener.requests[0]["json"]["stream"] is True
          and learned_stream_mode("never_seen") == "",
          f"{first.error} / requests {len(opener.requests)} then {len(second_opener.requests)}")
    forget_learned_stream_modes()
    check("learned_modes_can_be_forgotten", learned_stream_mode("auto_box") == "")

    result = _chat(_endpoint(stream="buffer"), _Opener([_Response(
        body=json.dumps({"error": "model 'gpt-oss:20b' not found, try pulling it first"}).encode())]))
    check("a_refusal_inside_a_200_body_is_classified_by_its_words_not_as_an_empty_answer",
          not result.ok and result.response_received
          and result.error.startswith("provider_error_body")
          and _error_code(result.error) == "model_not_found", result.error)
    result = _chat(_endpoint(stream="buffer", wire="openai"), _Opener([_Response(
        body=json.dumps({"error": {"message": "Rate limit reached", "code": 429}}).encode())]))
    check("a_200_body_that_names_a_status_is_classified_by_that_status",
          not result.ok and result.error.startswith("HTTP 429:")
          and _error_code(result.error) == "rate_limited", result.error)
    result = _chat(_endpoint(stream="buffer"), _Opener([_Response(
        body=b"<!DOCTYPE html><html><title>Just a moment...</title></html>")]))
    check("a_page_that_is_not_json_is_an_invalid_body_the_provider_did_not_send",
          not result.ok and result.response_received
          and result.error.startswith("invalid_response_body")
          and _error_code(result.error) == "invalid_response_body"
          and failure_class("invalid_response_body") == OUTAGE, result.error)
    result = _chat(_endpoint(stream="buffer"), _Opener([_Response(body=b"[1, 2]")]))
    check("json_that_is_not_an_object_is_an_invalid_body_too",
          not result.ok and result.error.startswith("invalid_response_body"), result.error)

    result = _chat(_endpoint(stream="buffer"), _Opener([_http_error(
        429, b'{"error":"rate limit exceeded"}', {"Retry-After": "120"})]))
    check("a_refusal_that_states_a_wait_carries_it_in_seconds_and_in_the_error_text",
          not result.ok and result.retry_after_seconds == 120.0
          and result.error.startswith("HTTP 429 (retry after 120s):")
          and _error_code(result.error) == "rate_limited"
          and failure_class(_error_code(result.error)) == ALLOWANCE
          and result.to_dict()["retry_after_seconds"] == 120.0, result.error)
    result = _chat(_endpoint(stream="buffer"), _Opener([_http_error(
        429, b'{"error":"you have reached your weekly usage limit, add usage credits (ref: 4013)"}')]))
    check("a_spent_weekly_allowance_states_no_wait_and_is_not_a_throttle",
          result.retry_after_seconds is None and "(retry after" not in result.error
          and _error_code(result.error) == "usage_limit_reached", result.error)
    dated = _chat(_endpoint(stream="buffer"), _Opener([_http_error(
        503, b"", {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})]))
    check("an_http_date_retry_after_reads_as_a_non_negative_wait",
          dated.retry_after_seconds == 0.0 and _error_code(dated.error) == "provider_unavailable",
          dated.error)
    junk = _chat(_endpoint(stream="buffer"), _Opener([_http_error(
        429, b"", {"Retry-After": "soon"})]))
    check("an_unreadable_retry_after_is_unstated_not_guessed", junk.retry_after_seconds is None)

    opener = _Opener([_Response(lines=stream)])
    _chat(_endpoint(think="off"), opener)
    off_payload = opener.requests[0]["json"]
    opener = _Opener([_Response(lines=stream)])
    _chat(_endpoint(), opener)
    default_payload = opener.requests[0]["json"]
    opener = _Opener([_Response(body=json.dumps({"choices": [{"message": {"content": "x"},
                                                              "finish_reason": "stop"}],
                                                 "usage": {"prompt_tokens": 1,
                                                           "completion_tokens": 1}}).encode())])
    _chat(_endpoint(wire="openai", stream="buffer", think="off"), opener)
    openai_payload = opener.requests[0]["json"]
    opener = _Opener([_Response(lines=stream)])
    _chat(_endpoint(think="model"), opener)
    model_payload = opener.requests[0]["json"]
    opener = _Opener([_Response(lines=stream)])
    _chat(_endpoint(think="on"), opener)
    on_payload = opener.requests[0]["json"]
    check("the_ollama_wire_sends_think_false_by_default_true_on_request_and_nothing_for_the_model_default",
          off_payload.get("think") is False and default_payload.get("think") is False
          and on_payload.get("think") is True and "think" not in model_payload
          and "think" not in openai_payload
          and _endpoint(think=True).think == "on" and _endpoint(think="false").think == "off"
          and _endpoint(think="auto").think == "model"
          and _endpoint().describe()["think"] == "default"
          and _endpoint().describe()["think_sent"] is False
          and _endpoint(wire="openai").describe()["think_sent"] is None
          and _endpoint(think="model").think_sent is None)
    try:
        _endpoint(think="maybe")
        check("an_unrecognized_think_spelling_is_refused", False, "accepted")
    except EndpointError:
        check("an_unrecognized_think_spelling_is_refused", True)

    listing, compat = _listing(_endpoint(), _Opener([_http_error(401, b'{"error":"unauthorized"}')]))
    check("a_refused_listing_says_how_it_was_refused_and_the_compatible_call_lists_nothing",
          not listing["ok"] and listing["http_status"] == 401
          and listing["error"].startswith("HTTP 401:") and listing["models"] == []
          and _error_code(listing["error"]) == "authentication_failed"
          and compat == [], listing["error"])
    listing, compat = _listing(_endpoint(), _Opener([_Response(
        body=json.dumps({"models": [{"name": "glm-5.3-flash"}, {"name": "kimi-k2.6"}]}).encode())]))
    check("a_listing_that_names_other_models_is_obtained_and_says_the_model_is_absent",
          listing["ok"] and listing["models"] == ["glm-5.3-flash", "kimi-k2.6"]
          and listing["model_listed"] is False and listing["listing_url"].endswith("/api/tags")
          and compat == ["glm-5.3-flash", "kimi-k2.6"])
    listing, _ = _listing(_endpoint(wire="openai"), _Opener([_Response(
        body=json.dumps({"data": [{"id": "gpt-oss:20b"}]}).encode())]))
    check("an_openai_wire_listing_reads_its_data_rows",
          listing["ok"] and listing["model_listed"] and listing["listing_url"].endswith("/models"))
    listing, _ = _listing(_endpoint(), _Opener([_Response(body=b"<html>login</html>")]))
    check("a_listing_that_is_not_json_is_an_invalid_body",
          not listing["ok"] and listing["error"].startswith("invalid_response_body"))
    listing, _ = _listing(_endpoint(), _Opener([_Response(body=json.dumps({"error": "down"}).encode())]))
    check("a_listing_that_carries_an_error_is_refused_by_its_words",
          not listing["ok"] and listing["error_type"] == "ErrorBody")
    check("listing_records_are_json_plain",
          json.loads(json.dumps(listing)) == listing)

    declared = _endpoint(name="declared_box", auth_scheme="bearer", api_key="",
                         credential_env="CHECKS_BOX_KEY", stream="buffer")
    opener = _Opener([_Response(body=b"{}")])
    result = _chat(declared, opener)
    listing, compat = _listing(declared, _Opener([_Response(body=b"{}")]))
    check("a_declared_but_unset_credential_refuses_before_any_request_as_the_built_ins_do",
          not result.ok and result.error.startswith("missing_credential: CHECKS_BOX_KEY")
          and result.physical_requests == 0 and opener.requests == []
          and _error_code(result.error) == "missing_credential"
          and declared.credential_missing and declared.describe()["credential_missing"]
          and "CHECKS_BOX_KEY" in declared.describe()["credential_env"]
          and not listing["ok"] and listing["error_type"] == "MissingCredential"
          and compat == [], result.error)
    check("a_declared_variable_that_holds_a_key_or_a_keyless_scheme_is_not_missing",
          not _endpoint(auth_scheme="bearer", api_key="k", credential_env="CHECKS_BOX_KEY").credential_missing
          and not _endpoint(auth_scheme="none", credential_env="CHECKS_BOX_KEY").credential_missing)

    sse = [b'data: {"choices": [{"delta": {"content": "hello, the ans"}}]}\n']
    result = _chat(_endpoint(wire="openai", stream="stream"), _Opener([_Response(lines=sse)]))
    complete = _chat(_endpoint(wire="openai", stream="stream"), _Opener([_Response(lines=sse + [
        b'data: {"choices": [{"delta": {}, "finish_reason": "stop"}], '
        b'"usage": {"prompt_tokens": 4, "completion_tokens": 3}}\n', b'data: [DONE]\n'])]))
    sentinel_only = _chat(_endpoint(wire="openai", stream="stream"),
                          _Opener([_Response(lines=sse + [b'data: [DONE]\n'])]))
    check("an_openai_stream_cut_before_its_stop_reason_or_done_sentinel_is_incomplete",
          not result.ok and result.done is False and result.text == "hello, the ans"
          and result.error.startswith("incomplete_response")
          and complete.ok and complete.done is True and complete.eval_tokens == 3
          and sentinel_only.ok and sentinel_only.done is True, result.error)

    result = _chat(_endpoint(stream="buffer"),
                   _Opener([ce.http.client.IncompleteRead(b"partial")]))
    streamed = _chat(_endpoint(stream="stream"),
                     _Opener([ce.http.client.RemoteDisconnected("closed")]))
    check("a_connection_that_ends_inside_the_body_is_an_incomplete_response_never_a_raise",
          not result.ok and result.error.startswith("incomplete_response: IncompleteRead")
          and result.response_received and _error_code(result.error) == "incomplete_response"
          and not streamed.ok and streamed.error.startswith("incomplete_response"),
          result.error)

    forget_learned_stream_modes()
    opener = _Opener([_http_error(504, b"upstream timed out"), _Response(lines=stream)])
    result = _chat(_endpoint(name="count_box", stream="auto"), opener)
    plain = _chat(_endpoint(stream="buffer"), _Opener([_Response(
        body=json.dumps({"message": {"content": "x"}, "done": True, "done_reason": "stop",
                         "prompt_eval_count": 1, "eval_count": 1}).encode())]))
    check("the_result_counts_the_http_requests_one_attempt_opened",
          result.ok and result.physical_requests == 2 and result.attempts == 1
          and plain.physical_requests == 1 and result.to_dict()["physical_requests"] == 2)
    forget_learned_stream_modes()

    secret = "sk-checks-secret-0123456789"
    echoing = _endpoint(stream="buffer", auth_scheme="bearer", api_key=secret)
    result = _chat(echoing, _Opener([_http_error(
        401, ('{"error":"invalid key ' + secret + ' sent as Bearer ' + secret + '"}').encode())]))
    listing, _ = _listing(echoing, _Opener([_http_error(401, ("key " + secret).encode())]))
    check("a_server_that_echoes_the_key_cannot_put_it_in_a_record",
          secret not in result.error and secret not in json.dumps(result.to_dict())
          and "<redacted>" in result.error and secret not in listing["error"]
          and _error_code(result.error) == "authentication_failed", result.error)

    roots = {
        ("ollama", "https://ollama.com"): ("https://ollama.com/api/chat", "https://ollama.com/api/tags"),
        ("ollama", "https://ollama.com/api"): ("https://ollama.com/api/chat", "https://ollama.com/api/tags"),
        ("ollama", "https://ollama.com/api/chat/"): ("https://ollama.com/api/chat", "https://ollama.com/api/tags"),
        ("ollama", "http://127.0.0.1:11434"): ("http://127.0.0.1:11434/api/chat", "http://127.0.0.1:11434/api/tags"),
        ("openai", "https://ollama.com/v1"): ("https://ollama.com/v1/chat/completions", "https://ollama.com/v1/models"),
        ("openai", "https://ollama.com/v1/chat/completions"): ("https://ollama.com/v1/chat/completions",
                                                              "https://ollama.com/v1/models"),
    }
    composed = {key: (_endpoint(wire=key[0], base_url=key[1]).chat_url,
                      _endpoint(wire=key[0], base_url=key[1]).listing_url) for key in roots}
    check("a_base_that_names_the_chat_path_the_api_prefix_or_the_root_composes_the_same_urls",
          composed == roots, str({k: v for k, v in composed.items() if roots[k] != v}))

    import os
    os.environ["CHECKS_ENV_KEY"] = "from-environment"
    try:
        parsed = ce.endpoints_from_env(
            "name=envbox,url=https://box.example,model=m,wire=ollama,think=on,key_env=CHECKS_ENV_KEY")
        unset = ce.endpoints_from_env(
            "name=envbox2,url=https://box.example,model=m,key_env=CHECKS_ENV_UNSET_KEY")
    finally:
        os.environ.pop("CHECKS_ENV_KEY", None)
    check("the_environment_declaration_accepts_think_and_a_key_variable_name",
          parsed[0].think == "on" and parsed[0].api_key == "from-environment"
          and parsed[0].credential_env == "CHECKS_ENV_KEY" and not parsed[0].credential_missing
          and unset[0].credential_missing and unset[0].api_key == "")
    try:
        ce.endpoints_from_env("name=b,url=https://box.example,model=m,key=k,key_env=X")
        check("key_and_key_env_together_are_refused", False, "accepted")
    except EndpointError:
        check("key_and_key_env_together_are_refused", True)
    return tests


def self_test() -> dict:
    tests = run_checks()
    return {"module": "core.custom_endpoint_checks", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
