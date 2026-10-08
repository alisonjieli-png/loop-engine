"""Each ephemeral search engine, shared reservations and the canonical Loop; no live provider calls."""
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from io import BytesIO, StringIO
import json
import http.client
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

from loop_engine import LoopLedger
from loop_engine.core.brave_search import (BraveSearchConfig, BraveSearchPlugin, BraveWebSearchRequest,
    HttpResponse, MappingSecretProvider, UrllibTransport, _NoRedirect)
from loop_engine.core.capability_directory import CapabilityDirectory
from loop_engine.core.library_ingestion.request_log import RequestBudget
from loop_engine.core.web_research_engines import (ENDPOINTS, REQUEST, RESULT, WebResearchBackend,
    WebResearchEngineConfig, WebResearchPolicy, WebResearchRequest, _ReservedTransport, SearchPolicyRefused,
    _credential_in_candidate, observation, register_web_research)
from loop_engine.loop.capability_loops import run_capability_ref_as_loop
from probe_web_research import main, selected_config
from loop_engine.core.web_research_quota import AccountQuota, SearchQuotaPolicy

TOKEN = "offline-fixture-credential"
QUERY = "public interoperability documentation"


def body(provider):
    row = {"title": "Fixture source", "url": "https://example.invalid/documentation"}
    if provider == "brave":
        return {"type": "search", "web": {"results": [{**row, "description": "fixture excerpt"}]}}
    if provider == "exa":
        return {"results": [{**row, "highlights": ["fixture excerpt"], "publishedDate": "2026-10-07"}], "costDollars": {"total": 0.007}}
    return {"results": [{**row, "content": "fixture excerpt"}], "usage": {"credits": 1}}


class Wire:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, "method": "GET", **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def post(self, url, **kwargs):
        answer = self.get(url, **kwargs)
        self.calls[-1]["method"] = "POST"
        return answer


def prepared(provider, *, status=200, headers=None, raw=None, policy=None, alias="fixture-ref", maximum_bytes=4_000_000):
    config = WebResearchEngineConfig(provider, alias, "shared-account", alias, maximum_response_bytes=maximum_bytes)
    policy = policy or WebResearchPolicy(RequestBudget(3), {config.quota_identity: RequestBudget(3)}, time.monotonic() + 30)
    secrets = MappingSecretProvider({alias: TOKEN})
    wire = Wire(HttpResponse(status, headers or {}, json.dumps(body(provider)).encode() if raw is None else raw))
    return WebResearchBackend(config, secrets, policy, wire), wire, secrets


class EngineConformanceTests(unittest.TestCase):
    def test_decoded_source_fields_refuse_escaped_credentials_without_serializing_them_again(self):
        token = 'offline\\fixture"credential'
        for provider in ENDPOINTS:
            fields = ["title", "url", "highlights" if provider == "exa" else "description" if provider == "brave" else "content"]
            if provider != "brave":
                fields.append("publishedDate" if provider == "exa" else "published_date")
            for field in fields:
                with self.subTest(provider=provider, field=field):
                    document = body(provider)
                    row = document["web"]["results"][0] if provider == "brave" else document["results"][0]
                    row[field] = ([token] if field == "highlights" else "https://example.invalid/" + token if field == "url" else token)
                    raw = json.dumps(document).encode()
                    self.assertNotIn(token.encode(), raw, "This must exercise the decoded-value guard, not the raw-body guard")
                    backend, wire, secrets = prepared(provider, raw=raw)
                    secrets.values[backend.config.secret_ref] = token
                    directory = CapabilityDirectory()
                    register_web_research(directory, config=backend.config, secret_provider=secrets, policy=backend.policy, transport=wire)
                    returned = directory.call("web_research_search", "search", request=WebResearchRequest(QUERY, "fixture"),
                                              access_mode="approved_external_read")
                    result = returned.value
                    self.assertFalse(returned.ok)
                    self.assertEqual(result["error_code"], "credential_reflected_by_provider")
                    self.assertEqual((result["candidates"], result["candidate_count"], result["attempt_count"]), ([], 0, 1))
                    self.assertEqual((result["http_status"], backend.policy.total.used, len(wire.calls)), (200, 1, 1))
                    self.assertNotIn(token, returned.note or "")
                    self.assertEqual(result["provider_usage"]["cost_usd"], 0.007 if provider == "exa" else None)

    def test_every_normalized_string_field_is_checked_and_unrelated_data_is_preserved(self):
        token = 'offline\\fixture"credential'
        candidate = {"title": "Fixture", "url": "https://example.invalid/path%20with%20spaces",
                     "excerpts": ["safe excerpt"], "published_at_reported": "2026-10-08"}
        before = json.dumps(candidate)
        self.assertFalse(_credential_in_candidate(candidate, (token,)))
        self.assertEqual(json.dumps(candidate), before, "URL decoding is inspection, not a URL rewrite")
        for field in candidate:
            changed = {**candidate, field: [token] if field == "excerpts" else token}
            self.assertTrue(_credential_in_candidate(changed, (token,)), field)
        # Brave does not publish a normalized reported date; unused upstream
        # metadata is discarded rather than invented or returned to a caller.
        document = body("brave")
        document["web"]["results"][0]["published_date"] = token
        backend, _, secrets = prepared("brave", raw=json.dumps(document).encode())
        secrets.values[backend.config.secret_ref] = token
        result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
        self.assertTrue(result["ok"])
        self.assertIsNone(result["candidates"][0]["published_at_reported"])

    def test_url_percent_decoding_is_bounded_and_deeper_nesting_is_refused(self):
        token = "offline-fixture-credential"
        encoded = "".join("%%%02X" % byte for byte in token.encode())
        for provider in ENDPOINTS:
            for depth in range(1, 5):
                with self.subTest(provider=provider, depth=depth):
                    value = encoded
                    for _ in range(depth - 1):
                        value = urllib.parse.quote(value, safe="")
                    document = body(provider)
                    row = document["web"]["results"][0] if provider == "brave" else document["results"][0]
                    row["url"] = "https://example.invalid/?source=" + value
                    backend, wire, _ = prepared(provider, raw=json.dumps(document).encode())
                    with patch("loop_engine.core.web_research_engines.unquote", wraps=urllib.parse.unquote) as decoder:
                        result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
                    self.assertEqual(decoder.call_count, min(depth, 3))
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["error_code"], "credential_reflected_by_provider" if depth <= 3 else "invalid_provider_response")
                    self.assertEqual((result["candidates"], result["attempt_count"], len(wire.calls), backend.policy.total.used), ([], 1, 1, 1))

    def test_removed_decoded_reflection_guard_control_exposes_the_original_defect(self):
        token = 'offline\\fixture"credential'
        document = body("exa")
        document["results"][0]["title"] = token
        backend, _, secrets = prepared("exa", raw=json.dumps(document).encode())
        secrets.values[backend.config.secret_ref] = token
        with patch("loop_engine.core.web_research_engines._credential_in_candidate", return_value=False):
            wrong = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
        self.assertTrue(wrong["ok"])
        self.assertEqual(wrong["candidates"][0]["title"], token)
        # The old serialized search misses precisely this decoded field value.
        self.assertNotIn(token, json.dumps(wrong["candidates"], ensure_ascii=False))
        self.assertNotEqual(wrong["candidates"], [], "The repaired contract requires an empty candidate list on this input")

    def test_protocol_exceptions_are_sanitized_and_hold_every_alias(self):
        for provider in ENDPOINTS:
            backend, _, _ = prepared(provider)
            wire = Wire(http.client.BadStatusLine("reflected " + TOKEN))
            directory = CapabilityDirectory()
            register_web_research(directory, config=backend.config, secret_provider=backend.secret_provider,
                                  policy=backend.policy, transport=wire)
            request = WebResearchRequest(QUERY, "fixture")
            result = directory.call("web_research_search", "search", request=request, access_mode="approved_external_read")
            self.assertFalse(result.ok)
            self.assertEqual(result.value["error_code"], "transport_failure")
            self.assertEqual(result.value["attempt_count"], 1)
            self.assertNotIn(TOKEN, str(result))
            second, second_wire, _ = prepared(provider, policy=backend.policy, alias="different-key")
            self.assertEqual(second.search(request, access_mode="approved_external_read")["error_code"], "provider_account_held")
            self.assertEqual((len(wire.calls), len(second_wire.calls)), (1, 0))

    def test_encoded_credentials_are_refused_before_reservation(self):
        for provider in ENDPOINTS:
            token = 'offline+fixture/credential' if provider == 'brave' else 'offline\\fixture"credential'
            backend, wire, secrets = prepared(provider)
            secrets.values[backend.config.secret_ref] = token
            result = backend.search(WebResearchRequest(token, "fixture"), access_mode="approved_external_read")
            self.assertEqual(result["error_code"], "credential_in_search_request")
            self.assertEqual((result["attempt_count"], backend.policy.total.used, wire.calls), (0, 0, []))

    def test_huge_usage_and_deep_json_never_escape_the_typed_result(self):
        for provider in ENDPOINTS:
            backend, _, _ = prepared(provider, raw=b'[' * 1100 + b'0' + b']' * 1100)
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_code"], "invalid_provider_response")
        for provider in ("exa", "tavily"):
            document = body(provider)
            document["costDollars" if provider == "exa" else "usage"] = {"total" if provider == "exa" else "credits": 10 ** 400}
            backend, _, _ = prepared(provider, raw=json.dumps(document).encode())
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertTrue(result["ok"])
            self.assertIsNone(result["provider_usage"]["cost_usd" if provider == "exa" else "credits"])

    def test_strict_versioned_requests_and_declared_bounds(self):
        request = WebResearchRequest(QUERY, "fixture")
        self.assertEqual(WebResearchRequest.from_record(request.to_record()), request)
        for changed in ({**request.to_record(), "record_type": "web_research_request/v9"},
                        {**request.to_record(), "extra": True}):
            with self.assertRaises(ValueError):
                WebResearchRequest.from_record(changed)
        for count in (0, True, 21, "1"):
            with self.assertRaises(ValueError):
                WebResearchRequest(QUERY, "fixture", count)
        with self.assertRaises(ValueError):
            WebResearchRequest("query\nwith controls", "fixture")
        with self.assertRaises(ValueError):
            WebResearchEngineConfig("unregistered", "instance", "account", "ref")

    def test_same_edge_for_every_provider_without_unrequested_exa_fields(self):
        for provider in ENDPOINTS:
            with self.subTest(provider=provider):
                backend, wire, _ = prepared(provider)
                result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
                self.assertTrue(result["ok"], result)
                self.assertEqual((result["record_type"], result["attempt_count"], result["candidate_count"]), (RESULT, 1, 1))
                self.assertIsNotNone(result["observed_at"])
                self.assertEqual(result["candidates"][0]["excerpts"], ["fixture excerpt"])
                self.assertFalse(result["persistable"])
                self.assertEqual(result["storage_rights"], "not_established")
                self.assertEqual(wire.calls[0]["url"].split("?")[0], ENDPOINTS[provider])
                if provider == "brave":
                    self.assertEqual(wire.calls[0]["headers"]["X-Subscription-Token"], TOKEN)
                    self.assertEqual(result["provider_usage"], {"cost_usd": None, "credits": None})
                else:
                    payload = json.loads(wire.calls[0]["body"])
                    self.assertNotIn(TOKEN, wire.calls[0]["body"].decode())
                    if provider == "exa":
                        self.assertEqual(payload, {"query": QUERY, "type": "auto", "contents": {"highlights": True}})
                        self.assertEqual(result["provider_usage"], {"cost_usd": 0.007, "credits": None})
                    else:
                        self.assertEqual(payload, {"query": QUERY, "search_depth": "basic", "auto_parameters": False,
                            "include_answer": False, "include_raw_content": False, "include_usage": True})
                        self.assertEqual(result["provider_usage"], {"cost_usd": None, "credits": 1})
                metadata = json.dumps(observation(result))
                for excluded in (TOKEN, QUERY, "fixture excerpt", "https://example.invalid/documentation", "Fixture source"):
                    self.assertNotIn(excluded, metadata)

    def test_explicit_result_count_reaches_each_provider(self):
        for provider in ENDPOINTS:
            backend, wire, _ = prepared(provider)
            result = backend.search(WebResearchRequest(QUERY, "fixture", 1), access_mode="approved_external_read")
            self.assertTrue(result["ok"])
            if provider == "brave":
                self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(wire.calls[0]["url"]).query)["count"], ["1"])
            else:
                self.assertEqual(json.loads(wire.calls[0]["body"])["numResults" if provider == "exa" else "max_results"], 1)

    def test_denied_access_reads_no_secret_and_dispatches_nothing(self):
        for provider in ENDPOINTS:
            backend, wire, secrets = prepared(provider)
            result = backend.search(WebResearchRequest(QUERY, "fixture"))
            self.assertEqual(result["error_code"], "internet_access_denied")
            self.assertIsNone(result["observed_at"])
            self.assertEqual((secrets.calls, len(wire.calls), backend.policy.total.used), (0, 0, 0))

    def test_missing_secret_is_not_a_synthetic_success(self):
        for provider in ENDPOINTS:
            backend, wire, secrets = prepared(provider)
            secrets.values.clear()
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertEqual(result["error_code"], "missing_secret")
            self.assertEqual((result["attempt_count"], len(wire.calls), result["candidates"]), (0, 0, []))

    def test_all_provider_refusals_and_retry_after_are_preserved_without_retry(self):
        for provider in ENDPOINTS:
            for status, code in ((401, "authentication_failed"), (403, "access_refused"), (429, "rate_limited")):
                with self.subTest(provider=provider, status=status):
                    backend, wire, _ = prepared(provider, status=status, headers={"Retry-After": "120"}, raw=b"refused")
                    result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
                    self.assertEqual((result["ok"], result["error_code"], result["http_status"]), (False, code, status))
                    self.assertEqual((result["attempt_count"], len(wire.calls), result["retry_after_seconds"]), (1, 1, 120))
                    self.assertFalse(result["automatic_fallback"])
                    self.assertEqual(result["provider_usage"], {"cost_usd": None, "credits": None})
        for status in (432, 433):
            backend, _, _ = prepared("tavily", status=status, raw=b"quota")
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertEqual(result["error_code"], "usage_limit_reached")
            self.assertFalse(result["retryable"])

    def test_http_date_and_brave_window_reset_are_honest(self):
        backend, _, _ = prepared("exa", status=429, headers={"Retry-After": "Wed, 01 Jan 2031 00:00:00 GMT"})
        self.assertGreater(backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")["retry_after_seconds"], 0)
        backend, _, _ = prepared("brave", status=429, headers={"X-RateLimit-Limit": "1,15000",
            "X-RateLimit-Remaining": "0,0", "X-RateLimit-Reset": "1,45"})
        result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
        self.assertEqual(result["retry_after_seconds"], 45)
        self.assertEqual(result["rate_limit"]["x-ratelimit-remaining"], "0,0")

    def test_malformed_success_and_unsafe_result_urls_fail_closed(self):
        for provider in ENDPOINTS:
            for raw in (b"not-json", b"[]", b'{"results": {}}'):
                backend, wire, _ = prepared(provider, raw=raw)
                result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
                self.assertFalse(result["ok"])
                self.assertEqual((result["candidate_count"], result["candidates"], len(wire.calls)), (0, [], 1))
            document = body(provider)
            rows = document["web"]["results"] if provider == "brave" else document["results"]
            rows[0]["url"] = "https://user:private@example.invalid/"
            backend, _, _ = prepared(provider, raw=json.dumps(document).encode())
            self.assertFalse(backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")["ok"])
        for bad in ({"type": "search", "web": {"results": {}}}, {"type": "search", "web": {"results": None}}):
            backend, _, _ = prepared("brave", raw=json.dumps(bad).encode())
            self.assertEqual(backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")["error_code"], "invalid_provider_response")

    def test_secret_reflection_and_query_leak_are_refused(self):
        for provider in ENDPOINTS:
            backend, _, _ = prepared(provider, raw=TOKEN.encode())
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertFalse(result["ok"])
            self.assertNotIn(TOKEN, json.dumps(result))
            backend, wire, _ = prepared(provider)
            result = backend.search(WebResearchRequest(TOKEN, "fixture"), access_mode="approved_external_read")
            self.assertEqual((result["error_code"], result["attempt_count"], len(wire.calls)), ("credential_in_search_request", 0, 0))
            document = body(provider)
            rows = document["web"]["results"] if provider == "brave" else document["results"]
            rows[0]["title"] = TOKEN
            escaped = json.dumps(document).replace(TOKEN, "".join("\\u%04x" % ord(char) for char in TOKEN)).encode()
            self.assertNotIn(TOKEN.encode(), escaped)
            backend, _, _ = prepared(provider, raw=escaped)
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertFalse(result["ok"])
            self.assertNotIn(TOKEN, json.dumps(result))

    def test_oversized_fake_responses_cannot_bypass_the_result_guard(self):
        for provider in ENDPOINTS:
            backend, _, _ = prepared(provider, raw=b"x" * 1025, maximum_bytes=1024)
            result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
            self.assertEqual(result["error_code"], "response_too_large")

    def test_metadata_reader_refuses_unknown_fields_versions_or_persistable_claims(self):
        backend, _, _ = prepared("exa")
        result = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
        for change in ({"record_type": "web_research_result/v9"}, {"raw_response": "private"}, {"persistable": True}, {"candidate_count": 50}):
            with self.assertRaises(ValueError):
                observation({**result, **change})


class BudgetAndLoopTests(unittest.TestCase):
    def test_credential_aliases_and_engine_instances_do_not_reset_account_limits(self):
        policy = WebResearchPolicy(RequestBudget(3), {"exa:shared-account": RequestBudget(1)}, time.monotonic() + 30)
        first, _, _ = prepared("exa", policy=policy, alias="first-key")
        second, second_wire, second_secrets = prepared("exa", policy=policy, alias="second-key")
        request = WebResearchRequest(QUERY, "fixture")
        self.assertTrue(first.search(request, access_mode="approved_external_read")["ok"])
        answer = second.search(request, access_mode="approved_external_read")
        self.assertEqual(answer["error_code"], "research_request_budget_exhausted")
        self.assertEqual((policy.total.used, len(second_wire.calls), second_secrets.calls), (1, 0, 0))
        # Known wrong: a newly invented account namespace would erase this allowance.
        self.assertNotIn("exa:second-key", policy.accounts)

    def test_shared_account_hold_survives_a_new_key_and_instance(self):
        policy = WebResearchPolicy(RequestBudget(3), {"tavily:shared-account": RequestBudget(3)}, time.monotonic() + 30)
        first, _, _ = prepared("tavily", status=429, policy=policy, alias="first-key")
        second, wire, secrets = prepared("tavily", policy=policy, alias="second-key")
        request = WebResearchRequest(QUERY, "fixture")
        first.search(request, access_mode="approved_external_read")
        result = second.search(request, access_mode="approved_external_read")
        self.assertEqual((result["error_code"], result["attempt_count"], len(wire.calls), secrets.calls), ("provider_account_held", 0, 0, 0))

    def test_successful_last_allowed_request_holds_the_account_before_another_key(self):
        policy = WebResearchPolicy(RequestBudget(3), {"brave:shared-account": RequestBudget(3)}, time.monotonic() + 30)
        first, _, _ = prepared("brave", headers={"X-RateLimit-Remaining": "0,1999", "X-RateLimit-Reset": "1,123"}, policy=policy)
        second, wire, secrets = prepared("brave", policy=policy, alias="another-key")
        request = WebResearchRequest(QUERY, "fixture")
        self.assertTrue(first.search(request, access_mode="approved_external_read")["ok"])
        self.assertEqual(second.search(request, access_mode="approved_external_read")["error_code"], "provider_account_held")
        self.assertEqual((wire.calls, secrets.calls, policy.total.used), ([], 0, 1))
        # Nonzero reported allowance is not itself an access hold.
        open_backend, open_wire, _ = prepared("brave", headers={"X-RateLimit-Remaining": "1,1999"})
        self.assertTrue(open_backend.search(request, access_mode="approved_external_read")["ok"])
        self.assertTrue(open_backend.search(request, access_mode="approved_external_read")["ok"])
        self.assertEqual(len(open_wire.calls), 2)

    def test_explicit_engine_switch_keeps_total_allowance_and_has_no_automatic_fallback(self):
        policy = WebResearchPolicy(RequestBudget(1), {name + ":shared-account": RequestBudget(1) for name in ENDPOINTS}, time.monotonic() + 30)
        brave, wire, _ = prepared("brave", status=500, policy=policy)
        exa, alternative, _ = prepared("exa", policy=policy)
        request = WebResearchRequest(QUERY, "fixture")
        failed = brave.search(request, access_mode="approved_external_read")
        self.assertFalse(failed["ok"])
        self.assertEqual((len(wire.calls), len(alternative.calls)), (1, 0))
        self.assertEqual(exa.search(request, access_mode="approved_external_read")["error_code"], "research_request_budget_exhausted")

    def test_deadline_and_unknown_transport_outcome_hold_before_further_requests(self):
        backend, wire, secrets = prepared("exa")
        backend.policy.deadline = time.monotonic() - 1
        self.assertEqual(backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")["error_code"], "research_deadline_exhausted")
        self.assertEqual((secrets.calls, wire.calls), (0, []))
        backend, wire, _ = prepared("tavily")
        wire.response = OSError("an upstream message must not enter metadata")
        failed = backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")
        self.assertEqual((failed["error_code"], failed["attempt_count"]), ("transport_failure", 1))
        self.assertEqual(backend.search(WebResearchRequest(QUERY, "fixture"), access_mode="approved_external_read")["error_code"], "provider_account_held")
        self.assertNotIn("upstream message", json.dumps(failed))

    def test_every_engine_uses_the_same_canonical_capability_loop(self):
        for provider in ENDPOINTS:
            backend, wire, secrets = prepared(provider)
            directory = CapabilityDirectory()
            register_web_research(directory, config=backend.config, secret_provider=secrets, policy=backend.policy, transport=wire)
            selected = directory.search_core("search public web")[0]
            self.assertEqual((secrets.calls, wire.calls), (0, []))
            ledger = LoopLedger()
            result = run_capability_ref_as_loop(directory, selected, "search", request=WebResearchRequest(QUERY, "fixture"),
                                              ledger=ledger, access_mode="approved_external_read")
            self.assertTrue(result["ok"], result)
            self.assertEqual((result["input_schema"], result["output_schema"], result["model_calls"]), (REQUEST, RESULT, 0))
            self.assertEqual((result["value"]["attempt_count"], len(wire.calls)), (1, 1))
            history = json.dumps(ledger.events, default=str)
            for absent in (TOKEN, QUERY, "fixture excerpt", "Fixture source", "https://example.invalid/"):
                self.assertNotIn(absent, history)
            with self.assertRaises(FrozenInstanceError):
                backend.config = replace(backend.config, provider="tavily" if provider != "tavily" else "exa")

    def test_endpoint_change_is_refused_before_dispatch_and_declarations_are_immutable(self):
        backend, wire, _ = prepared("exa")
        with self.assertRaises(SearchPolicyRefused):
            _ReservedTransport(backend).post("https://other.invalid/search", headers={"x-api-key": TOKEN}, timeout=1, body=b"{}")
        self.assertEqual((wire.calls, backend.policy.total.used), ([], 0))
        with self.assertRaises(TypeError):
            ENDPOINTS["exa"] = "https://other.invalid/search"


class BoundedTransportTests(unittest.TestCase):
    class Stream(BytesIO):
        status = 200
        headers = {}

        def __init__(self):
            super().__init__(b"x" * 4096)
            self.bounds = []

        def read(self, size=-1):
            self.bounds.append(size)
            return super().read(size)

    def test_success_and_error_reads_are_bounded_for_get_and_post(self):
        for method in ("get", "post"):
            for failed in (False, True):
                stream = self.Stream()

                class Opener:
                    def open(self, request, timeout):
                        if failed:
                            raise urllib.error.HTTPError(request.full_url, 503, "unavailable", {}, stream)
                        return stream
                transport = UrllibTransport(1024, Opener())
                kwargs = {"headers": {}, "timeout": 1, **({"body": b"{}"} if method == "post" else {})}
                answer = getattr(transport, method)("https://api.exa.ai/search", **kwargs)
                self.assertEqual(len(answer.body), 1025)
                self.assertEqual(stream.bounds, [1025])
                self.assertTrue(stream.closed)
        wrong = self.Stream()
        self.assertGreater(len(wrong.read()), 1025)
        self.assertNotEqual(wrong.bounds, [1025])

    def test_redirect_handler_refuses_instead_of_forwarding_credentials(self):
        with self.assertRaises(urllib.error.HTTPError):
            _NoRedirect().redirect_request(urllib.request.Request(ENDPOINTS["exa"]), None, 302, "moved",
                {"Location": "https://other.invalid/"}, "https://other.invalid/")

    def test_brave_default_transport_obeys_the_plugins_configured_byte_limit(self):
        stream = self.Stream()

        class Opener:
            def open(self, request, timeout):
                return stream
        with patch("loop_engine.core.brave_search.urllib.request.build_opener", return_value=Opener()):
            plugin = BraveSearchPlugin(BraveSearchConfig(max_response_bytes=1024),
                MappingSecretProvider({"env:BRAVE_SEARCH_API_KEY": TOKEN}))
            result = plugin.search(BraveWebSearchRequest(QUERY), access_mode="approved_external_read")
        self.assertEqual(result["error_code"], "response_too_large")
        self.assertEqual(stream.bounds, [1025])


class OperatorProbeTests(unittest.TestCase):
    def manifest(self):
        return {"record_type": "operator_credential_references/v1", "api_keys": {"exa-ref": {
            "service": "exa", "account": "owner-plan", "purpose": "bounded-research-search", "environment": "EXA_API_KEY"}}}

    def test_configuration_uses_account_not_key_alias_and_rejects_foreign_provider(self):
        config = selected_config("exa", "exa-ref", self.manifest())
        self.assertEqual(config.quota_identity, "exa:owner-plan")
        with self.assertRaises(ValueError):
            selected_config("brave", "exa-ref", self.manifest())

    def test_plan_never_reads_keyring_and_live_fixture_prints_no_results_or_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "references.json"
            manifest.write_text(json.dumps(self.manifest()))
            arguments = ["--provider", "exa", "--credential-ref", "exa-ref", "--credentials", str(manifest), "--query", QUERY]
            output = StringIO()
            with patch("probe_web_research.operator_credentials.resolve", side_effect=AssertionError("no keyring read")), redirect_stdout(output):
                self.assertEqual(main(arguments), 0)
            self.assertFalse(json.loads(output.getvalue())["credentials_read"])
            output = StringIO()
            wire = Wire(HttpResponse(200, {}, json.dumps(body("exa")).encode()))
            quota_path = Path(folder) / "quota.json"
            quota_path.write_text(json.dumps(SearchQuotaPolicy("fixture", "1.0.0", (
                AccountQuota("exa:owner-plan", 1, 60, 1, 10000, 10000),)).to_record()))
            live_arguments = ["--authorize-network", "--authorize-accounting-writes", "--quota-policy", str(quota_path),
                              "--quota-state", str(Path(folder) / "quota.sqlite")]
            with patch("probe_web_research.operator_credentials.resolve", return_value=TOKEN), \
                 patch("loop_engine.core.web_research_engines.UrllibTransport", return_value=wire), redirect_stdout(output):
                self.assertEqual(main(arguments + live_arguments), 0)
            printed = output.getvalue()
            for absent in (TOKEN, QUERY, "fixture excerpt", "Fixture source", "https://example.invalid/"):
                self.assertNotIn(absent, printed)
            self.assertEqual(json.loads(printed)["run_requests_reserved"], 1)
            self.assertEqual(len(wire.calls), 1)


if __name__ == "__main__":
    unittest.main()
