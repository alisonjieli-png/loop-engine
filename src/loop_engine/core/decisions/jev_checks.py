"""Provider-shaped fixtures and serializer checks. No live Jev request.

The actual adapter serializes requests through an injected local transport.
Tests cover authority, credentials, bounded responses, identity and malformed
answers. Successful fixture responses do not establish provider availability.
"""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from .contracts import DecisionProtocolError, canonical, strict_json
from .contract_checks import fixture_request, refused, report
from .jev import JevAdapter, JevConfiguration, JEV_ENDPOINT, _send


def provider_body():
    return {"model": "jev-1.13.0", "answers": {
        "route": {"type": "choice", "choice": "inspect", "probabilities": {"inspect": .8, "build": .2}, "confidence": .6},
        "coverage": {"type": "score", "score": .25, "legend": {"0": "Missing", "1": "Complete"},
                     "probabilities": {"0": .75, "1": .25}, "confidence": .5},
        "needed": {"type": "noul", "noul": .7}}, "usage": {"input_tokens": 40, "output_tokens": 20}}


def run_checks():
    tests, accesses, sends = [], [], []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    request = fixture_request()
    def secret(reference):
        accesses.append(reference)
        return "LOCAL_DECISION_FIXTURE_SECRET"
    def transport(payload, value, timeout, maximum):
        sends.append((strict_json(payload), value, timeout, maximum))
        return provider_body()
    disabled = JevAdapter(JevConfiguration("jev-1.13.0"), secret, transport)
    disabled.decision_capabilities()
    result = disabled.decide_questions(request, model="jev-1.13.0", timeout=1)
    check("discovery_and_disabled_provider_resolve_no_secret_and_send_nothing",
          not accesses and not sends and result.physical_requests == 0 and not result.ok)
    enabled = JevAdapter(replace(disabled.configuration, allow_network=True, allow_model_calls=True), secret, transport)
    value = enabled.decide_questions(request, model="jev-1.13.0", timeout=1)
    check("official_wire_shape_and_three_answer_kinds_are_mapped",
          value.ok and value.physical_requests == 1 and value.total_tokens == 60
          and set(sends[0][0]) == {"model", "state", "questions"}
          and sends[0][0]["questions"]["needed"]["type"] == "noul"
          and value.answers["needed"] == {"kind": "boolean_probability", "probability": .7})
    check("aliases_and_literal_secrets_are_not_accepted_in_configuration",
          refused(lambda: JevConfiguration("jev-latest"))
          and refused(lambda: JevConfiguration("jev-1.13.0", credential_ref="LOCAL_SECRET")))
    count = len(sends)
    missing = JevAdapter(enabled.configuration, lambda _ref: "", transport)
    check("missing_credentials_are_not_replaced_with_synthetic_answers",
          not missing.decide_questions(request, model="jev-1.13.0", timeout=1).ok and len(sends) == count)
    small = JevAdapter(replace(enabled.configuration, maximum_request_bytes=1), secret, transport)
    check("request_size_refuses_before_secret_resolution", not small.decide_questions(request, model="jev-1.13.0", timeout=1).ok
          and len(sends) == count and len(accesses) == 1)
    for name, mutate in (
        ("model", lambda body: {**body, "model": "another-model"}),
        ("partial", lambda body: {**body, "answers": {"route": body["answers"]["route"]}}),
        ("legend", lambda body: {**body, "answers": {**body["answers"], "coverage": {**body["answers"]["coverage"], "legend": {"0": "Changed", "1": "Complete"}}}}),
        ("usage", lambda body: {**body, "usage": {"input_tokens": True}}),
    ):
        adapter = JevAdapter(enabled.configuration, secret, lambda *args, mutate=mutate: mutate(provider_body()))
        response = adapter.decide_questions(request, model="jev-1.13.0", timeout=1)
        check("provider_" + name + "_refuses_without_an_answer", not response.ok and not response.answers and response.physical_requests == 1)
    unknown = JevAdapter(enabled.configuration, secret, lambda *args: {**provider_body(), "usage": {}})
    check("missing_usage_stays_unknown_not_zero", unknown.decide_questions(request, model="jev-1.13.0", timeout=1).total_tokens is None)
    def failing(*args):
        raise RuntimeError("LOCAL_DECISION_FIXTURE_SECRET")
    failed = JevAdapter(enabled.configuration, secret, failing).decide_questions(request, model="jev-1.13.0", timeout=1)
    check("transport_exception_does_not_leak_a_secret_or_retry", not failed.ok and failed.physical_requests == 1
          and failed.error_code == "decision_provider_failed" and failed.total_tokens is None)
    try:
        import httpx
    except ImportError:
        tests.append({"test": "provider_HTTP_serializer", "passed": None, "not_tested": True})
        return report(tests)
    calls, options = [], []
    status = {"code": 200, "body": canonical(provider_body()).encode()}
    original = httpx.Client
    def handler(outgoing):
        calls.append(outgoing)
        return httpx.Response(status["code"], content=status["body"], headers={"Location": "https://untrusted.example/"})
    def client(**kwargs):
        options.append(kwargs)
        return original(**kwargs, transport=httpx.MockTransport(handler))
    with patch.object(httpx, "Client", client):
        _send(b"{}", "LOCAL_DECISION_FIXTURE_SECRET", 1, 10000)
        check("provider_serializer_is_fixed_origin_no_proxy_no_redirect",
              str(calls[0].url) == JEV_ENDPOINT and calls[0].method == "POST"
              and options[0]["trust_env"] is False and options[0]["follow_redirects"] is False)
        status["code"] = 302
        check("provider_redirects_refuse", refused(lambda: _send(b"{}", "fixture", 1, 10000)))
        status.update(code=200, body=b"x" * 100)
        check("provider_response_limit_refuses", refused(lambda: _send(b"{}", "fixture", 1, 10)))
        status["body"] = b'{"model":"one","model":"two"}'
        check("duplicate_provider_fields_refuse", refused(lambda: _send(b"{}", "fixture", 1, 10000)))
    return report(tests)
