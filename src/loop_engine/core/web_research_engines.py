"""Selectable ephemeral search engines behind the existing Web Research port.

Brave reuses its registered plugin; Exa and Tavily use their native search
endpoints through the same bounded transport. Manual Capability Directory
registration supplies the canonical capability Loop. No scheduled collector,
result store, customer activation, automatic retry or fallback is introduced.
Quota accounts identify provider accounts, never credential aliases. A host
must supply one shared, bounded run policy before a request can leave.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
import hashlib
import http.client
import json
import math
from pathlib import Path
import re
import threading
import time
from types import MappingProxyType
from urllib.parse import unquote, urlsplit

from . import brave_search
from .brave_search import (BRAVE_WEB_SEARCH_URL, BraveSearchConfig, BraveSearchPlugin, BraveWebSearchRequest,
                          EXTERNAL_READ_ACCESS_MODES, HttpResponse, UrllibTransport)
from .library_ingestion.request_log import RequestBudget
from .web_search import WebSearchRequest
from .web_research_quota import DurableSearchQuota, QuotaOutcome, QuotaRefused

REQUEST = "web_research_request/v1"
RESULT = "web_research_result/v1"
OBSERVATION = "web_research_observation/v1"
BACKEND = "web_research_backend/v1"
ENDPOINTS = MappingProxyType({"brave": BRAVE_WEB_SEARCH_URL,
                             "exa": "https://api.exa.ai/search", "tavily": "https://api.tavily.com/search"})
HTTP_ERRORS = {400: "invalid_request", 401: "authentication_failed", 403: "access_refused",
               404: "endpoint_not_found", 422: "invalid_request", 429: "rate_limited",
               432: "usage_limit_reached", 433: "usage_limit_reached"}
_IDENTITY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}\Z")
MAXIMUM_URL_CREDENTIAL_DECODINGS = 3


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@lru_cache(maxsize=1)
def implementation_digest():
    """Bind the adapter, normalizer and shared transport source of this installed revision."""
    folder = Path(__file__).resolve().parent
    return _digest({name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                    for name in ("web_research_engines.py", "brave_search.py", "web_research_quota.py")})


@dataclass(frozen=True)
class WebResearchRequest:
    query: str
    purpose: str
    maximum_results: int | None = None

    def __post_init__(self):
        WebSearchRequest(self.query, self.purpose, self.maximum_results)
        if (len(self.query) > 400 or len(self.query.split()) > 50 or len(self.purpose) > 2048
                or any(ord(character) < 32 for character in self.query + self.purpose)
                or self.maximum_results is not None and self.maximum_results > 20):
            raise ValueError("web_research_request_out_of_bounds")

    def to_record(self):
        return {"record_type": REQUEST, "query": self.query, "purpose": self.purpose,
                "maximum_results": self.maximum_results}

    @classmethod
    def from_record(cls, value):
        if (type(value) is not dict or set(value) != {"record_type", "query", "purpose", "maximum_results"}
                or value.get("record_type") != REQUEST):
            raise ValueError("web_research_request_version_or_fields")
        return cls(value["query"], value["purpose"], value["maximum_results"])


@dataclass(frozen=True)
class WebResearchEngineConfig:
    provider: str
    instance_id: str
    provider_account: str
    secret_ref: str
    timeout_seconds: float = 30.0
    maximum_response_bytes: int = 4_000_000

    def __post_init__(self):
        if self.provider not in ENDPOINTS:
            raise ValueError("web_research_engine_unknown")
        if any(not isinstance(value, str) or not _IDENTITY.fullmatch(value)
               for value in (self.instance_id, self.provider_account, self.secret_ref)):
            raise ValueError("web_research_engine_identity_invalid")
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 120 or type(self.maximum_response_bytes) is not int
                or not 1024 <= self.maximum_response_bytes <= 20_000_000):
            raise ValueError("web_research_transport_bounds_invalid")

    @property
    def quota_identity(self):
        return self.provider + ":" + self.provider_account


@dataclass
class WebResearchPolicy:
    """Run ceilings plus an optional host-bound durable provider-account projection."""

    total: RequestBudget
    accounts: dict[str, RequestBudget]
    deadline: float
    durable: DurableSearchQuota | None = None
    holds: dict[str, str] = field(default_factory=dict, init=False)
    lock: object = field(default_factory=threading.Lock, init=False, repr=False)
    durable_binding: str = field(default="", init=False)

    def __post_init__(self):
        budgets = (self.total, *self.accounts.values())
        if (not self.accounts or any(type(budget) is not RequestBudget or type(budget.maximum_requests) is not int
                or budget.maximum_requests < 1 or type(budget.used) is not int or budget.used < 0 for budget in budgets)
                or not math.isfinite(self.deadline)):
            raise ValueError("web_research_bounded_policy_required")
        self.accounts = dict(self.accounts)
        if self.durable is not None:
            if type(self.durable) is not DurableSearchQuota:
                raise ValueError("typed_web_research_quota_required")
            for account in self.accounts:
                self.durable.policy.account(account)
            self.durable_binding = self.durable.binding_digest

    def reserve(self, account, request_digest):
        with self.lock:
            reason = self._refusal(account)
            if reason:
                raise SearchPolicyRefused(reason)
            try:
                reservation = self.durable.reserve(account, request_digest) if self.durable is not None else None
            except QuotaRefused as error:
                raise SearchPolicyRefused(str(error)) from None
            own = self.accounts[account]
            self.total.admit()
            if own is not self.total:
                own.admit()
            return reservation

    def refusal(self, account):
        with self.lock:
            return self._refusal(account)

    def _refusal(self, account):
        if ((self.durable is not None and type(self.durable) is not DurableSearchQuota)
                or (self.durable.binding_digest if self.durable is not None else "") != self.durable_binding):
            return "quota_binding_changed"
        if account not in self.accounts:
            return "provider_account_not_authorized"
        if account in self.holds:
            return "provider_account_held"
        if time.monotonic() >= self.deadline:
            return "research_deadline_exhausted"
        own = self.accounts[account]
        if self.total.used >= self.total.maximum_requests or own.used >= own.maximum_requests:
            return "research_request_budget_exhausted"
        return self.durable.refusal(account) if self.durable is not None else ""

    def hold(self, account, reason):
        with self.lock:
            self.holds[account] = reason


class SearchPolicyRefused(ValueError):
    """A reservation refused before any HTTP request was dispatched."""


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def _retry_after(headers):
    text = next((str(value) for key, value in headers.items() if key.lower() == "retry-after"), "")
    if text.isdigit():
        return int(text)
    try:
        stamp = parsedate_to_datetime(text)
        if stamp.tzinfo is not None:
            return max(0.0, (stamp - datetime.now(timezone.utc)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _rate(headers):
    result = {}
    for key, value in headers.items():
        name, value = str(key).lower(), str(value)
        if name in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-policy"):
            if len(value) <= 256 and re.fullmatch(r"[0-9.,;=w \t]+", value):
                result[name] = value
    return result


def _cooldown(provider, headers):
    delay = _retry_after(headers)
    if provider != "brave":
        return delay
    # Brave documents reset durations per comma-separated quota window. Other
    # providers may use epochs instead, so do not reinterpret their reset field.
    rate = _rate(headers)
    remaining = rate.get("x-ratelimit-remaining", "").split(",")
    resets = rate.get("x-ratelimit-reset", "").split(",")
    waits = []
    for index, value in enumerate(remaining):
        if value.strip() != "0":
            continue
        try:
            reset = float(resets[index])
            if not math.isfinite(reset) or not 0 <= reset <= 31536000:
                return None
            waits.append(reset)
        except (IndexError, ValueError, OverflowError):
            return None
    return max([delay] + waits) if delay is not None and waits else max(waits) if waits else delay


def _candidate(rank, row, provider):
    if type(row) is not dict:
        raise ValueError("provider_row_invalid")
    title, url = row.get("title"), row.get("url")
    if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
        raise ValueError("provider_row_invalid")
    parsed = urlsplit(url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password
            or len(url) > 8192 or any(ord(character) < 32 for character in url)):
        raise ValueError("provider_url_invalid")
    if provider == "exa":
        excerpts = row.get("highlights", [])
        if type(excerpts) is not list or any(not isinstance(item, str) for item in excerpts):
            raise ValueError("provider_highlights_invalid")
    else:
        content = row.get("description" if provider == "brave" else "content", "")
        if not isinstance(content, str):
            raise ValueError("provider_content_invalid")
        excerpts = [content] if content else []
    published = row.get("publishedDate" if provider == "exa" else "published_date")
    if published is not None and not isinstance(published, str):
        raise ValueError("provider_date_invalid")
    return {"rank": rank, "title": title, "url": url, "excerpts": excerpts,
            "published_at_reported": published, "trust": "untrusted_external_content",
            "licence": "not_established"}


def _credential_in_candidate(candidate, tokens):
    """Inspect decoded values, never a serialization that can escape the credential again."""
    values = (candidate["title"], candidate["url"], candidate["published_at_reported"], *candidate["excerpts"])
    if any(token and token in value for token in tokens for value in values if isinstance(value, str)):
        return True
    # A source URL can percent-encode a credential even when its JSON string
    # contains no literal match. Inspection is bounded; deeper nesting is a
    # refused URL, not a claim that arbitrary encodings have been sanitized.
    url = candidate["url"]
    for _ in range(MAXIMUM_URL_CREDENTIAL_DECODINGS):
        decoded = unquote(url)
        if any(token and token in decoded for token in tokens):
            return True
        if decoded == url:
            return False
        url = decoded
    if re.search(r"%[0-9A-Fa-f]{2}", url):
        raise ValueError("provider_url_encoding_too_deep")
    return False


class _ReservedTransport:
    def __init__(self, backend, request_digest=None):
        self.backend = backend
        self.request_digest = request_digest
        self.reservation = None
        self.sent = 0
        self.last_response = None
        self.secret_values = ()

    def _send(self, method, url, headers, timeout, body=None):
        backend = self.backend
        # The adapter owns endpoint selection; neither query nor secret can
        # change the origin/path or introduce an unapproved redirect.
        if url.split("?", 1)[0] != ENDPOINTS[backend.config.provider]:
            raise SearchPolicyRefused("search_endpoint_changed")
        tokens = [value.removeprefix("Bearer ") for name, value in headers.items()
                  if name.lower() in ("authorization", "x-api-key", "x-subscription-token")]
        self.secret_values = tuple(tokens)
        if any(token and (token in url or token.encode() in (body or b"")) for token in tokens):
            raise SearchPolicyRefused("credential_in_search_request")
        self.reservation = backend.policy.reserve(backend.config.quota_identity, self.request_digest)
        if time.monotonic() >= backend.policy.deadline:
            # A database lock may have consumed the remaining time. Preserve
            # the reservation conservatively, but do not dispatch after it.
            raise SearchPolicyRefused("research_deadline_exhausted_after_reservation")
        self.sent += 1
        timeout = min(timeout, max(0.001, backend.policy.deadline - time.monotonic()))
        response = (backend.transport.get(url, headers=headers, timeout=timeout) if method == "GET" else
                    backend.transport.post(url, headers=headers, timeout=timeout, body=body))
        if isinstance(response, HttpResponse) and isinstance(response.body, bytes) and isinstance(response.headers, dict):
            self.last_response = response
            for token in tokens:
                if token and (token.encode() in response.body or any(token in str(item) for item in response.headers.values())):
                    raise OSError("credential_reflected_by_provider")
        return response

    def get(self, url, *, headers, timeout):
        return self._send("GET", url, headers, timeout)

    def post(self, url, *, headers, timeout, body):
        return self._send("POST", url, headers, timeout, body)


@dataclass(frozen=True)
class WebResearchBackend:
    """One selected engine; shared request/result semantics, no implicit retry or persistence."""

    config: WebResearchEngineConfig
    secret_provider: object = field(repr=False, compare=False)
    policy: WebResearchPolicy = field(repr=False, compare=False)
    transport: object = field(default=None, repr=False, compare=False)
    requires_durable: bool = field(default=False, init=False)

    def __post_init__(self):
        if type(self.config) is not WebResearchEngineConfig or type(self.policy) is not WebResearchPolicy:
            raise ValueError("typed_web_research_configuration_required")
        object.__setattr__(self, "requires_durable", self.transport is None or isinstance(self.transport, brave_search.UrllibTransport))
        if self.transport is None:
            object.__setattr__(self, "transport", UrllibTransport(self.config.maximum_response_bytes))

    def search(self, request, *, access_mode="offline"):
        config = self.config
        result = {"record_type": RESULT, "ok": False, "error_code": "", "provider": config.provider,
                  "engine_id": config.provider + "_web_search", "engine_version": "1.1.1",
                  "implementation_digest": implementation_digest(),
                  "instance_id": config.instance_id, "quota_identity": config.quota_identity,
                  "request_digest": _digest(request.to_record()) if type(request) is WebResearchRequest else None,
                  "attempt_count": 0, "http_status": None, "response_sha256": None, "observed_at": None,
                  "provider_usage": {"cost_usd": None, "credits": None}, "rate_limit": {},
                  "retry_after_seconds": None, "retryable": False, "candidate_count": 0,
                  "candidates": [], "persistable": False, "retention": "ephemeral",
                  "storage_rights": "not_established", "automatic_fallback": False}
        if type(request) is not WebResearchRequest:
            return {**result, "error_code": "invalid_request"}
        if access_mode not in EXTERNAL_READ_ACCESS_MODES:
            return {**result, "error_code": "internet_access_denied"}
        if self.requires_durable and self.policy.durable is None:
            return {**result, "error_code": "durable_quota_required"}
        if reason := self.policy.refusal(config.quota_identity):
            return {**result, "error_code": reason}
        transport = _ReservedTransport(self, result["request_digest"])
        try:
            if config.provider == "brave":
                plugin = BraveSearchPlugin(BraveSearchConfig(secret_ref=config.secret_ref, timeout=config.timeout_seconds,
                    max_response_bytes=config.maximum_response_bytes), self.secret_provider, transport)
                answer = plugin.search(BraveWebSearchRequest(request.query, count=request.maximum_results or 10), access_mode=access_mode)
                result.update({name: answer[name] for name in ("ok", "error_code", "http_status", "response_sha256", "retryable") if name in answer})
                if not result["ok"] and result["http_status"] in HTTP_ERRORS:
                    result["error_code"] = HTTP_ERRORS[result["http_status"]]
                if transport.last_response is not None:
                    if type(transport.last_response.status) is int:
                        result["http_status"] = transport.last_response.status
                    result["rate_limit"] = _rate(transport.last_response.headers)
                    result["retry_after_seconds"] = _cooldown(config.provider, transport.last_response.headers)
                rows = answer.get("candidates", [])
            else:
                try:
                    token = self.secret_provider.get(config.secret_ref)
                except Exception:
                    return {**result, "error_code": "secret_lookup_failed"}
                if not isinstance(token, str) or not token.strip():
                    return {**result, "error_code": "missing_secret"}
                if token.strip() in request.query:
                    return {**result, "error_code": "credential_in_search_request"}
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                if config.provider == "exa":
                    headers["x-api-key"] = token.strip()
                    body = {"query": request.query, "type": "auto", "contents": {"highlights": True}}
                    if request.maximum_results is not None:
                        body["numResults"] = request.maximum_results
                else:
                    headers["Authorization"] = "Bearer " + token.strip()
                    body = {"query": request.query, "search_depth": "basic", "auto_parameters": False,
                            "include_answer": False, "include_raw_content": False, "include_usage": True}
                    if request.maximum_results is not None:
                        body["max_results"] = request.maximum_results
                response = transport.post(ENDPOINTS[config.provider], headers=headers,
                    timeout=config.timeout_seconds, body=json.dumps(body, separators=(",", ":")).encode())
                if (not isinstance(response, HttpResponse) or type(response.body) is not bytes or type(response.headers) is not dict
                        or type(response.status) is not int or not 100 <= response.status <= 599):
                    raise ValueError("invalid_transport_response")
                result["http_status"] = response.status
                result["rate_limit"] = _rate(response.headers)
                result["retry_after_seconds"] = _retry_after(response.headers)
                if len(response.body) > config.maximum_response_bytes:
                    raise ValueError("response_too_large")
                result["response_sha256"] = hashlib.sha256(response.body).hexdigest()
                if response.status != 200:
                    result["error_code"] = HTTP_ERRORS.get(response.status, "unexpected_http_status")
                    result["retryable"] = response.status == 429 or response.status >= 500
                    rows = []
                else:
                    document = json.loads(response.body)
                    if type(document) is not dict or type(document.get("results")) is not list:
                        raise ValueError("invalid_provider_response")
                    rows = document["results"]
                    cost = document.get("costDollars")
                    usage = document.get("usage")
                    result["provider_usage"] = {"cost_usd": _number(cost.get("total")) if isinstance(cost, dict) else None,
                                                "credits": _number(usage.get("credits")) if isinstance(usage, dict) else None}
                    result["ok"] = True
            if result["ok"]:
                if len(rows) > (request.maximum_results or 100):
                    raise ValueError("provider_result_bound_exceeded")
                result["candidates"] = [_candidate(index, row, config.provider) for index, row in enumerate(rows, 1)]
                if any(_credential_in_candidate(candidate, transport.secret_values) for candidate in result["candidates"]):
                    raise ValueError("credential_reflected_by_provider")
                result["candidate_count"] = len(result["candidates"])
        except SearchPolicyRefused as error:
            result.update(ok=False, error_code=str(error))
        except (OSError, http.client.HTTPException):
            result.update(ok=False, error_code="transport_failure")
        except (ValueError, TypeError, AttributeError, OverflowError, RecursionError) as error:
            code = str(error) if str(error) in ("response_too_large", "invalid_transport_response", "provider_result_bound_exceeded", "credential_reflected_by_provider") else "invalid_provider_response"
            result.update(ok=False, error_code=code)
        result["attempt_count"] = transport.sent
        if result["http_status"] is not None:
            result["observed_at"] = datetime.now(timezone.utc).isoformat()
        if not result["ok"]:
            result["candidates"], result["candidate_count"] = [], 0
        if self.policy.durable is not None and transport.reservation is not None:
            try:
                self.policy.durable.finish(transport.reservation, QuotaOutcome.from_result(result))
            except QuotaRefused:
                # A crash, lost database or invalid completion must never make
                # an already reserved request eligible for a blind retry.
                self.policy.hold(config.quota_identity, "quota_completion_unknown")
                result.update(ok=False, error_code="quota_completion_unknown", candidates=[], candidate_count=0, retryable=False)
        elif result["http_status"] in (401, 403, 429, 432, 433):
            self.policy.hold(config.quota_identity, result["error_code"])
        elif any(part.strip() == "0" for part in result["rate_limit"].get("x-ratelimit-remaining", "").split(",")):
            # A successful final allowed request is still a success. Its
            # exhausted account/window prevents another dispatch in this run.
            self.policy.hold(config.quota_identity, "provider_allowance_exhausted")
        elif result["attempt_count"] and result["http_status"] is None:
            self.policy.hold(config.quota_identity, "unknown_transport_outcome")
        return result


def describe_web_research_engine(config):
    return {"record_type": BACKEND, "engine_id": config.provider + "_web_search", "engine_version": "1.1.1",
            "implementation_digest": implementation_digest(),
            "engine_kind": "search_service", "instance_id": config.instance_id, "quota_identity": config.quota_identity,
            "endpoint": ENDPOINTS[config.provider], "request_contract": REQUEST, "result_contract": RESULT,
            "retention": "ephemeral", "fallback": "none", "ready": "not_probed"}


def observation(result):
    """Metadata-only projection for operator reports; never store the candidate bodies."""
    fields = {"record_type", "ok", "error_code", "provider", "engine_id", "engine_version", "implementation_digest", "instance_id",
              "quota_identity", "request_digest", "attempt_count", "http_status", "response_sha256", "observed_at", "provider_usage",
              "rate_limit", "retry_after_seconds", "retryable", "candidate_count", "candidates", "persistable",
              "retention", "storage_rights", "automatic_fallback"}
    if (type(result) is not dict or set(result) != fields or result.get("record_type") != RESULT
            or result.get("persistable") is not False or result.get("retention") != "ephemeral"
            or result.get("automatic_fallback") is not False or type(result.get("candidates")) is not list
            or type(result.get("candidate_count")) is not int or result["candidate_count"] != len(result["candidates"])):
        raise ValueError("web_research_result_version")
    return {**{key: value for key, value in result.items() if key != "candidates"},
            "record_type": OBSERVATION, "results_retained": False}


def register_web_research(directory, *, config, secret_provider, policy, transport=None):
    """Install one engine behind the same manual capability edge without changing its caller."""
    from .capability_directory import CapabilityHandshake, Endpoint
    backend = WebResearchBackend(config, secret_provider, policy, transport)
    accounting_effects = ("reads_fs", "writes_fs") if policy.durable is not None else ()
    handshake = CapabilityHandshake("web_research_search", "static_component", "search the public web for source candidates with " + config.provider,
        operations=("search",), query_fields=("query",), accepts=("web_research_request",), returns=("web_research_result",),
        input_schema=REQUEST, output_schema=RESULT, locality="api_calling", effects=("reads_secret", "network") + accounting_effects,
        cost_class="metered", auth_method="provider_header", secret_ref=config.secret_ref, retention_default="ephemeral",
        timeout_seconds=config.timeout_seconds, max_response_bytes=config.maximum_response_bytes,
        quota_policy=config.quota_identity + (":" + policy.durable_binding if policy.durable is not None else ""),
        retry_policy="none; caller must reconcile and authorize another attempt",
        data_egress=("query",), privacy_class="public_web_query", license_terms="source and provider rights remain unestablished",
        provider_version="provider_latest")
    directory.register(handshake, [Endpoint("search", backend.search)])
    return backend


def self_test():
    """One shared offline conformance population, run against each engine independently."""
    from .brave_search import MappingSecretProvider
    tests = []
    rows = {"brave": {"type": "search", "web": {"results": [{"title": "Fixture", "url": "https://example.invalid/source"}]}},
            "exa": {"results": [{"title": "Fixture", "url": "https://example.invalid/source", "highlights": ["Example excerpt"]}]},
            "tavily": {"results": [{"title": "Fixture", "url": "https://example.invalid/source", "content": "Example excerpt"}]}}

    class FixtureTransport:
        def __init__(self, provider):
            self.provider, self.calls = provider, []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return HttpResponse(200, {}, json.dumps(rows[self.provider]).encode())

        def post(self, url, **kwargs):
            return self.get(url, **kwargs)

    for provider in ENDPOINTS:
        config = WebResearchEngineConfig(provider, "fixture-instance", "fixture-account", "fixture-ref")
        policy = WebResearchPolicy(RequestBudget(1), {config.quota_identity: RequestBudget(1)}, time.monotonic() + 30)
        secrets, wire = MappingSecretProvider({"fixture-ref": "offline-fixture-value"}), FixtureTransport(provider)
        backend = WebResearchBackend(config, secrets, policy, wire)
        request = WebResearchRequest("public documentation", "offline contract check")
        denied = backend.search(request)
        tests.append({"test": provider + "_refuses_before_secret_or_network", "passed": not denied["ok"] and secrets.calls == 0 and not wire.calls})
        answer = backend.search(request, access_mode="approved_external_read")
        metadata = observation(answer)
        tests.append({"test": provider + "_normalizes_ephemeral_candidates", "passed": answer["ok"] and answer["candidate_count"] == 1
                      and not answer["persistable"] and "candidates" not in metadata and "Example excerpt" not in json.dumps(metadata)})
        refused = backend.search(request, access_mode="approved_external_read")
        tests.append({"test": provider + "_budget_refuses_another_dispatch", "passed": refused["error_code"] == "research_request_budget_exhausted"
                      and len(wire.calls) == 1 and secrets.calls == 1})
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests), "provider_integration_proven": False}
