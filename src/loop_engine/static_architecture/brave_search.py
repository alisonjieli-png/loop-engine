"""Manually registered Brave Web Search plugin.

Public capability groups: Web Research and Custom Plugins.

Owns: a narrow typed Brave Web Search request, fixed-host HTTPS transport,
secret lookup, response normalization, rate-limit metadata, and explicit
manual registration in the Capability Directory.

Does not own: plugin auto-discovery, page fetching, scraping, result storage,
source trust, or retries. Search results are untrusted and ephemeral by
default. Brave plan terms determine whether results may be stored.

Official API: ``GET https://api.search.brave.com/res/v1/web/search`` with
``X-Subscription-Token`` authentication.

Verification: ``self_test()`` uses only fake transports and fake secrets. It
makes no live request.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
SAFESEARCH = ("off", "moderate", "strict")
EXTERNAL_READ_ACCESS_MODES = (
    "approved_external_read", "broad_external_read",
    "approved_external_write")
_FRESHNESS = re.compile(
    r"^(?:pd|pw|pm|py|\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2})$")
_API_VERSION = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BraveSearchError(ValueError):
    pass


@dataclass(frozen=True)
class BraveWebSearchRequest:
    q: str
    count: int = 10
    offset: int = 0
    country: str = ""
    search_lang: str = ""
    ui_lang: str = ""
    safesearch: str = "moderate"
    freshness: str = ""
    extra_snippets: bool = False

    def __post_init__(self):
        query = self.q.strip()
        if not query or len(query) > 400 or len(query.split()) > 50:
            raise BraveSearchError(
                "q must contain 1 to 400 characters and at most 50 words")
        if not 1 <= int(self.count) <= 20:
            raise BraveSearchError("count must be between 1 and 20")
        if not 0 <= int(self.offset) <= 9:
            raise BraveSearchError("offset must be between 0 and 9")
        if self.safesearch not in SAFESEARCH:
            raise BraveSearchError(f"safesearch must be one of {SAFESEARCH}")
        if self.freshness and not _FRESHNESS.fullmatch(self.freshness):
            raise BraveSearchError(
                "freshness must be pd, pw, pm, py, or a YYYY-MM-DD date range")

    def params(self) -> dict:
        values = {"q": self.q.strip(), "count": int(self.count),
                  "offset": int(self.offset), "safesearch": self.safesearch,
                  "extra_snippets": str(bool(self.extra_snippets)).lower(),
                  # Keep this capability narrow: it returns Web source
                  # candidates, never hidden rich/local/summary work.
                  "result_filter": "web", "text_decorations": "false"}
        for key in ("country", "search_lang", "ui_lang", "freshness"):
            value = getattr(self, key)
            if value:
                values[key] = value
        return values


@dataclass(frozen=True)
class BraveSearchConfig:
    secret_ref: str = "env:BRAVE_SEARCH_API_KEY"
    api_version: str = ""
    timeout: float = 30.0
    max_response_bytes: int = 4_000_000
    retention_default: str = "ephemeral"

    def __post_init__(self):
        if not self.secret_ref:
            raise BraveSearchError("secret_ref must name a secret reference")
        if self.api_version and not _API_VERSION.fullmatch(self.api_version):
            raise BraveSearchError("api_version must use YYYY-MM-DD")
        if (not math.isfinite(float(self.timeout))
                or float(self.timeout) <= 0):
            raise BraveSearchError("timeout must be a positive finite number")
        if not 1024 <= int(self.max_response_bytes) <= 20_000_000:
            raise BraveSearchError(
                "max_response_bytes must be between 1024 and 20000000")
        if self.retention_default != "ephemeral":
            raise BraveSearchError(
                "the example plugin supports ephemeral results only")


class EnvSecretProvider:
    def get(self, ref: str) -> str:
        if not ref.startswith("env:"):
            raise KeyError("EnvSecretProvider accepts env: references only")
        return os.environ.get(ref.split(":", 1)[1], "")


class MappingSecretProvider:
    def __init__(self, values: dict):
        self.values = dict(values)
        self.calls = 0

    def get(self, ref: str) -> str:
        self.calls += 1
        return self.values.get(ref, "")


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict = field(default_factory=dict)
    body: bytes = b""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "redirect refused", headers, fp)


class UrllibTransport:
    """Fixed-host transport. The token-bearing request cannot redirect."""
    def get(self, url: str, *, headers: dict, timeout: float) -> HttpResponse:
        request = urllib.request.Request(url, headers=headers, method="GET")
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=timeout) as response:
                return HttpResponse(response.status, dict(response.headers),
                                    response.read())
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, dict(exc.headers or {}), exc.read())


class SequenceTransport:
    """Offline transport fixture with an inspectable request log."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url: str, *, headers: dict, timeout: float) -> HttpResponse:
        self.requests.append({"url": url, "headers": dict(headers),
                              "timeout": timeout})
        if not self.responses:
            raise OSError("no fake response remains")
        return self.responses.pop(0)


def _header(headers: dict, name: str) -> str:
    return next((str(value) for key, value in headers.items()
                 if str(key).lower() == name.lower()), "")


def _rate_limit(headers: dict) -> dict:
    raw = {"limit": _header(headers, "X-RateLimit-Limit"),
           "policy": _header(headers, "X-RateLimit-Policy"),
           "remaining": _header(headers, "X-RateLimit-Remaining"),
           "reset": _header(headers, "X-RateLimit-Reset")}

    def parts(value: str) -> list:
        return [piece.strip() for piece in value.split(",") if piece.strip()]

    limits, remaining, resets = (parts(raw[key]) for key in
                                  ("limit", "remaining", "reset"))
    windows = []
    for index in range(max(len(limits), len(remaining), len(resets))):
        windows.append({
            "limit": limits[index] if index < len(limits) else "",
            "remaining": (remaining[index]
                          if index < len(remaining) else ""),
            "reset_seconds": resets[index] if index < len(resets) else "",
        })
    raw["windows"] = windows
    return raw


def _failure(config: BraveSearchConfig, error_code: str, *,
             attempt_count: int, **details) -> dict:
    """One stable failure shape; never includes a token or response body."""
    out = {"ok": False, "error_code": error_code,
           "attempt_count": int(attempt_count), "retryable": False,
           "api_version_requested": config.api_version,
           "persistable": False, "candidates": []}
    out.update(details)
    return out


def _retry_after_seconds(rate_limit: dict):
    """Wait until every exhausted rate window has reset, when parseable."""
    waits = []
    for window in rate_limit.get("windows", ()):
        try:
            if int(window["remaining"]) <= 0:
                waits.append(float(window["reset_seconds"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not waits:
        return None
    wait = max(waits)
    return int(wait) if wait.is_integer() else wait


def _optional_text(row: dict, key: str) -> str:
    value = row.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BraveSearchError(f"provider field {key!r} must be a string")
    return value


class BraveSearchPlugin:
    def __init__(self, config: BraveSearchConfig, secret_provider,
                 transport=None):
        self.config = config
        self.secret_provider = secret_provider
        self.transport = transport or UrllibTransport()

    def search(self, request: BraveWebSearchRequest, *,
               access_mode: str = "offline") -> dict:
        if not isinstance(request, BraveWebSearchRequest):
            return _failure(self.config, "invalid_request", attempt_count=0)
        if access_mode not in EXTERNAL_READ_ACCESS_MODES:
            return _failure(self.config, "internet_access_denied",
                            attempt_count=0)
        try:
            token = self.secret_provider.get(self.config.secret_ref)
        except Exception as exc:  # noqa: BLE001 - secret boundary, type only
            return _failure(self.config, "secret_lookup_failed",
                            attempt_count=0, error=type(exc).__name__,
                            secret_ref=self.config.secret_ref)
        if not isinstance(token, str) or not token.strip():
            return _failure(self.config, "missing_secret", attempt_count=0,
                            secret_ref=self.config.secret_ref)
        token = token.strip()
        url = BRAVE_WEB_SEARCH_URL + "?" + urllib.parse.urlencode(
            request.params())
        headers = {"Accept": "application/json",
                   "X-Subscription-Token": token}
        if self.config.api_version:
            headers["Api-Version"] = self.config.api_version
        try:
            response = self.transport.get(
                url, headers=headers, timeout=self.config.timeout)
        except (OSError, urllib.error.URLError) as exc:
            return _failure(self.config, "transport_failure", attempt_count=1,
                            error=type(exc).__name__)
        if (not isinstance(response, HttpResponse)
                or not isinstance(response.headers, dict)
                or not isinstance(response.body, bytes)):
            return _failure(self.config, "invalid_transport_response",
                            attempt_count=1)
        if len(response.body) > self.config.max_response_bytes:
            return _failure(
                self.config, "response_too_large", attempt_count=1,
                response_bytes=len(response.body),
                max_response_bytes=self.config.max_response_bytes)
        rate = _rate_limit(response.headers)
        digest = hashlib.sha256(response.body).hexdigest()
        if response.status != 200:
            error_by_status = {404: "endpoint_not_found",
                               422: "invalid_request",
                               429: "rate_limited"}
            return _failure(
                self.config,
                error_by_status.get(response.status,
                                    "unexpected_http_status"),
                attempt_count=1, http_status=response.status,
                rate_limit=rate, response_sha256=digest,
                retryable=response.status == 429,
                retry_after_reset=(rate["reset"]
                                   if response.status == 429 else ""),
                retry_after_seconds=(_retry_after_seconds(rate)
                                     if response.status == 429 else None))
        try:
            body = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        if not isinstance(body, dict) or body.get("type") != "search":
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        web = body.get("web")
        if web is None:
            web = {}
        if not isinstance(web, dict):
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        rows = web.get("results") or []
        if not isinstance(rows, list):
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        candidates = []
        try:
            for rank, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    raise BraveSearchError(
                        "each provider Web result must be an object")
                title = _optional_text(row, "title")
                result_url = _optional_text(row, "url")
                if not title or not result_url:
                    raise BraveSearchError(
                        "provider Web results require non-empty title and url")
                snippets = row.get("extra_snippets") or []
                if (not isinstance(snippets, list)
                        or any(not isinstance(value, str)
                               for value in snippets)):
                    raise BraveSearchError(
                        "provider extra_snippets must be an array of strings")
                candidates.append({
                    "rank": rank, "title": title, "url": result_url,
                    "description": _optional_text(row, "description"),
                    "age": _optional_text(row, "age"),
                    "extra_snippets": list(snippets),
                    "trust": "untrusted_external_content"})
        except BraveSearchError:
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        query = body.get("query")
        if query is None:
            query = {}
        if not isinstance(query, dict):
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        more = query.get("more_results_available", False)
        if not isinstance(more, bool):
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        try:
            original = _optional_text(query, "original") or request.q
            altered = _optional_text(query, "altered")
        except BraveSearchError:
            return _failure(
                self.config, "invalid_provider_response", attempt_count=1,
                http_status=200, rate_limit=rate, response_sha256=digest)
        return {"ok": True, "provider": "brave",
                "query_original": original, "query_altered": altered,
                "more_results_available": more,
                "candidates": candidates, "rate_limit": rate,
                "http_status": 200, "attempt_count": 1,
                "retryable": False,
                "response_sha256": digest,
                "api_version_requested": self.config.api_version,
                "persistable": False,
                "storage_note": "ephemeral; storage rights depend on Brave plan"}


def register_brave_search(directory, *, config=None, secret_provider=None,
                          transport=None) -> BraveSearchPlugin:
    """Manually register Brave. Importing this module registers nothing."""
    from .capability_directory import CapabilityHandshake, Endpoint
    plugin = BraveSearchPlugin(
        config or BraveSearchConfig(),
        secret_provider or EnvSecretProvider(), transport=transport)
    handshake = CapabilityHandshake(
        "brave_web_search", "static_component",
        "search the current public web with Brave and return source candidates",
        operations=("search",), query_fields=("q", "country", "freshness"),
        ranking=("provider_rank",), embeddings=False,
        accepts=("web_search_request",), returns=("web_source_candidate_batch",),
        input_schema="brave_web_search_request/v1",
        output_schema="web_source_candidate_batch/v1",
        locality="api_calling", effects=("reads_secret", "network"),
        cost_class="metered", auth_method="subscription_token_header",
        secret_ref=plugin.config.secret_ref, retention_default="ephemeral",
        idempotency="read_only_but_results_and_billing_may_differ",
        timeout_seconds=plugin.config.timeout,
        max_response_bytes=plugin.config.max_response_bytes,
        quota_policy="Brave subscription plan",
        rate_limit_policy="provider headers with one-second sliding window",
        retry_policy="Route schedules a new visible loop attempt",
        data_egress=("query", "country", "language", "freshness"),
        privacy_class="public_web_query",
        license_terms="Brave plan controls result storage rights",
        provider_version=plugin.config.api_version or "provider_latest")
    directory.register(
        handshake,
        [Endpoint("search", lambda request, access_mode="offline":
                  plugin.search(request, access_mode=access_mode))])
    return plugin


def self_test() -> dict:
    from .capability_directory import CapabilityDirectory, HandshakeError
    from ..loop.capability_loops import run_capability_as_loop
    from ..loop.recursive_loop import LoopLedger

    def fixture_response(status=200, body=None, headers=None):
        body = body if body is not None else {
            "type": "search",
            "query": {"original": "Loop Engine static architecture",
                      "more_results_available": False},
            "web": {"results": [{
                "title": "Static Architecture Example",
                "url": "https://example.test/static-architecture",
                "description": "A deterministic fixture.",
                "extra_snippets": ["Additional fixture context."]}]}}
        default_headers = {
            "X-RateLimit-Limit": "1, 15000",
            "X-RateLimit-Remaining": "0, 14999",
            "X-RateLimit-Reset": "1, 1000"}
        return HttpResponse(status, headers or default_headers,
                            json.dumps(body).encode())

    def plugin_for(responses, token="fixture-token"):
        transport = SequenceTransport(responses)
        secrets = MappingSecretProvider(
            {"env:BRAVE_SEARCH_API_KEY": token} if token else {})
        return BraveSearchPlugin(BraveSearchConfig(), secrets, transport), \
            transport, secrets

    transport = SequenceTransport([fixture_response()])
    secrets = MappingSecretProvider({"env:BRAVE_SEARCH_API_KEY":
                                     "fixture-token"})
    directory = CapabilityDirectory()
    import_registered_nothing = not directory.available()
    register_brave_search(directory, secret_provider=secrets, transport=transport)
    handshake = directory.handshake("brave_web_search")
    refs = directory.search_static_architecture("current public web search")
    discovery_counts = (len(transport.requests), secrets.calls)
    denied = run_capability_as_loop(
        directory, "brave_web_search", "search",
        request=BraveWebSearchRequest("Loop Engine"),
        access_mode="offline")
    denied_counts = (len(transport.requests), secrets.calls)
    ledger = LoopLedger()
    run = run_capability_as_loop(
        directory, "brave_web_search", "search",
        request=BraveWebSearchRequest(
            "Loop Engine static architecture", count=1,
            extra_snippets=True), access_mode="approved_external_read",
        ledger=ledger)
    serialized = json.dumps({"run": run, "events": ledger.events}, default=str)
    spec = next(e for e in ledger.events if e.get("event") == "spec")
    duplicate = False
    try:
        register_brave_search(directory, secret_provider=secrets,
                              transport=SequenceTransport([]))
    except HandshakeError:
        duplicate = True

    def refused(factory, cases):
        count = 0
        for kwargs in cases:
            try:
                factory(**kwargs)
            except BraveSearchError:
                count += 1
        return count

    invalid = refused(BraveWebSearchRequest, (
        {"q": "x", "count": 21}, {"q": "x", "offset": 10},
        {"q": "x", "safesearch": "maximum"}, {"q": " "}))
    invalid_configs = refused(BraveSearchConfig, (
        {"api_version": "latest"}, {"timeout": 0}, {"secret_ref": ""},
        {"max_response_bytes": 1000}))
    rate_directory = CapabilityDirectory()
    rate_transport = SequenceTransport([fixture_response(429, {"error": "rate"})])
    register_brave_search(
        rate_directory,
        secret_provider=MappingSecretProvider(
            {"env:BRAVE_SEARCH_API_KEY": "rate-fixture-token"}),
        transport=rate_transport)
    rate = run_capability_as_loop(
        rate_directory, "brave_web_search", "search",
        request=BraveWebSearchRequest("x"),
        access_mode="approved_external_read")
    error_plugin, _, _ = plugin_for(
        [fixture_response(404, {"error": "not found"}),
         fixture_response(422, {"error": "invalid"})])
    errors = [error_plugin.search(BraveWebSearchRequest("x"),
                                  access_mode="approved_external_read")
              for _ in range(2)]
    missing_plugin, missing_transport, _ = plugin_for([], token="")
    missing = missing_plugin.search(BraveWebSearchRequest("x"),
                                    access_mode="approved_external_read")
    malformed_plugin, _, _ = plugin_for(
        [HttpResponse(200, {}, b'[]')], token="malformed-token")
    malformed = malformed_plugin.search(
        BraveWebSearchRequest("x"), access_mode="approved_external_read")
    oversized_plugin, _, _ = plugin_for(
        [HttpResponse(200, {}, b"x" * 1025)], token="oversized-token")
    oversized_plugin.config = BraveSearchConfig(max_response_bytes=1024)
    oversized = oversized_plugin.search(
        BraveWebSearchRequest("x"), access_mode="approved_external_read")
    broad_plugin, _, _ = plugin_for(
        [fixture_response(body={"type": "search", "web": None})],
        token="broad-token")
    broad = broad_plugin.search(BraveWebSearchRequest("x"),
                                access_mode="broad_external_read")
    query_params = urllib.parse.parse_qs(
        urllib.parse.urlsplit(transport.requests[0]["url"]).query)
    tests = [
        {"test": "registration_is_manual_and_discovery_is_effect_free",
         "passed": bool(import_registered_nothing and refs
                        and discovery_counts == (0, 0) and duplicate
                        and handshake.effects == ("reads_secret", "network")
                        and handshake.locality == "api_calling"
                        and handshake.max_response_bytes == 4_000_000
                        and handshake.retry_policy.startswith("Route"))},
        {"test": "offline_refuses_before_secret_or_transport",
         "passed": bool(not denied["ok"]
                        and denied["value"]["error_code"]
                            == "internet_access_denied"
                        and denied["capability_terminal_code"]
                            == "POLICY_DENIED"
                        and denied_counts == discovery_counts)},
        {"test": "approved_search_runs_once_and_normalizes_untrusted_results",
         "passed": bool(run["ok"] and run["model_calls"] == 0
                        and run["effects"] == ["reads_secret", "network"]
                        and spec["effects"] == ("reads_secret", "network")
                        and run["value"]["candidates"][0]["trust"]
                            == "untrusted_external_content"
                        and run["value"]["persistable"] is False
                        and run["value"]["rate_limit"]["reset"] == "1, 1000"
                        and len(run["value"]["rate_limit"]["windows"]) == 2
                        and len(transport.requests) == 1
                        and transport.requests[0]["url"].startswith(
                            BRAVE_WEB_SEARCH_URL)
                        and query_params["result_filter"] == ["web"]
                        and query_params["text_decorations"] == ["false"]
                        and transport.requests[0]["headers"][
                            "X-Subscription-Token"] == "fixture-token"
                        and "fixture-token" not in serialized)},
        {"test": "rate_limit_and_invalid_requests_are_typed",
         "passed": bool(not rate["ok"]
                        and rate["value"]["error_code"] == "rate_limited"
                        and rate["value"]["retryable"] is True
                        and rate["value"]["retry_after_reset"] == "1, 1000"
                        and rate["value"]["retry_after_seconds"] == 1
                        and rate["capability_terminal_code"] == "BLOCKED"
                        and invalid == 4 and invalid_configs == 4)},
        {"test": "documented_http_errors_and_missing_key_fail_without_fallback",
         "passed": bool(errors[0]["error_code"] == "endpoint_not_found"
             and errors[1]["error_code"] == "invalid_request"
             and not errors[0]["retryable"] and not errors[1]["retryable"]
             and missing["error_code"] == "missing_secret"
             and missing["attempt_count"] == 0
             and not missing_transport.requests)},
        {"test": "malformed_provider_shape_fails_closed",
         "passed": bool(not malformed["ok"]
                        and malformed["error_code"]
                            == "invalid_provider_response"
                        and oversized["error_code"] == "response_too_large"
                        and oversized["response_bytes"] == 1025)},
        {"test": "all_external_read_authority_modes_can_use_read_search",
         "passed": bool(broad["ok"] and broad["candidates"] == [])},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
