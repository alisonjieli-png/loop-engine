"""Bounded read-only HTTPS requests to declared public hosts, and the component's address helpers.

The transport sends only GET requests, only to hosts the caller declared,
follows no redirect, reads at most a declared number of bytes within a
declared time and never sends a credential. A 429 answer with a Retry-After
time pauses through the run's budget, within its declared bound, and is
tried once more. Every request is admitted by the budget and recorded in
the run's request log. The official Model Context Protocol registry reader
and the package checks use it.

This is the one module of the component that imports urllib. The address
helpers below (split an address, quote or unquote one part of it) send
nothing; they live here so that one declared module owns every address the
component builds or reads, and the network gate names a single file.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlencode, urlsplit, urlunsplit

from .record_rules import now_utc
from .request_log import RequestBudget, RequestLog, RequestObservation

_USER_AGENT = "loop-engine library-ingestion (read-only)"
HTTPS_TRANSPORT = "https_get"
#: The only scheme a rendered connection file or a request of this component may use.
HTTPS_SCHEME = "https"


def split_address(value: str):
    """The scheme, host, path and query of an address, read without sending anything."""
    return urlsplit(value)


def quote_part(value: str, safe: str = "") -> str:
    """One part of an address with every character outside `safe` percent-encoded."""
    return quote(value, safe=safe)


def unquote_part(value: str) -> str:
    """One part of an address with its percent-encoding undone, to check what it names."""
    return unquote(value)


class HostNotDeclared(ValueError):
    """A request named a host the run did not declare; nothing was sent."""


@dataclass(frozen=True)
class HttpsResponse:
    status: "int | None"
    body: bytes
    retry_after: "float | None" = None
    #: The validators the source sent, so a later read can ask whether anything changed (a 304 answer).
    etag: "str | None" = None
    last_modified: "str | None" = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _retry_after(headers) -> "float | None":
    value = (headers or {}).get("Retry-After") if headers is not None else None
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


class HttpsGetTransport:
    """GET requests to declared hosts, admitted by a budget and recorded in a log."""

    transport = HTTPS_TRANSPORT

    def __init__(self, hosts, budget: RequestBudget, log: RequestLog, *, timeout_seconds: float = 30.0,
                 maximum_bytes: int = 8 * 1024 * 1024, accept: str = "application/json",
                 user_agent: str = _USER_AGENT) -> None:
        self.hosts = frozenset(hosts)
        self.budget, self.log = budget, log
        self.timeout_seconds, self.maximum_bytes = timeout_seconds, maximum_bytes
        # The media type asked for; an Atom or XML interface refuses a request that accepts only JSON.
        self.accept = accept
        # A source whose terms ask every call to name the software making it (Poly Haven's API terms, 2.4) is read
        # with that name; every other caller keeps the component's own.
        self.user_agent = user_agent
        self._opener = urllib.request.build_opener(_NoRedirect)

    def get(self, host: str, path: str, query: "dict | None" = None, *,
            validators: "dict | None" = None) -> HttpsResponse:
        """One GET. ``validators`` (``etag`` and ``last_modified`` from an earlier answer) make it conditional:
        a source that has not changed answers 304 with no body, and the answer says so."""
        if host not in self.hosts:
            raise HostNotDeclared(f"{host} is not a declared host of this run")
        if not path.startswith("/") or ".." in path.split("/"):
            raise HostNotDeclared("a request path is absolute within its host and has no parent step")
        target = urlunsplit((HTTPS_SCHEME, host, path, urlencode(query or {}), ""))
        conditions = _conditions(validators)
        response = self._send(host, target, conditions)
        if response.status == 429 and response.retry_after is not None:
            self.budget.pause(response.retry_after + 1.0, f"{host} asked to retry later")
            response = self._send(host, target, conditions)
        return response

    def _send(self, host: str, target: str, conditions: "dict | None" = None) -> HttpsResponse:
        self.budget.admit()
        started, clock = now_utc(), time.monotonic()
        request = urllib.request.Request(target, method="GET", headers={
            "User-Agent": self.user_agent, "Accept": self.accept, **(conditions or {})})
        status, body, retry, error_class, headers = None, None, None, "", None
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as answer:
                status, body, headers = answer.status, answer.read(self.maximum_bytes + 1), answer.headers
        except urllib.error.HTTPError as error:
            status, retry, headers = error.code, _retry_after(error.headers), error.headers
            try:
                body = error.read(self.maximum_bytes + 1)
            except OSError:
                body = b""
        except (urllib.error.URLError, OSError, ValueError) as error:
            error_class = type(error).__name__
        elapsed = (time.monotonic() - clock) * 1000
        if body is not None and len(body) > self.maximum_bytes:
            body, error_class, status = None, "response_too_large", None
        self.log.record(RequestObservation(self.transport, host, target, status, body, started, elapsed,
                                           outcome_for(status), error_class=error_class))
        return HttpsResponse(status, body or b"", retry, _header(headers, "ETag"), _header(headers, "Last-Modified"))


def _conditions(validators) -> dict:
    """The conditional request headers for the validators of an earlier answer; nothing else is sent."""
    if not isinstance(validators, dict):
        return {}
    conditions = {}
    for key, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
        value = validators.get(key)
        if isinstance(value, str) and value and len(value) <= 200 and "\n" not in value and "\r" not in value:
            conditions[header] = value
    return conditions


def _header(headers, name: str) -> "str | None":
    value = headers.get(name) if headers is not None else None
    return value if isinstance(value, str) and value and len(value) <= 200 else None


def outcome_for(status: "int | None") -> str:
    """The recorded outcome of one answer: ok, not_modified, not_found, rate_limited, http_error or transport_error."""
    if status is None:
        return "transport_error"
    return {200: "ok", 304: "not_modified", 404: "not_found", 429: "rate_limited"}.get(status, "http_error")
