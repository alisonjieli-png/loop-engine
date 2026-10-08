"""Trendshift GET adapters reusing the existing bounded research transport.

The only authenticated host is api.trendshift.io. No secret enters a request
record, URL or diagnostic. One shared RequestBudget and RequestLog count
physical requests; a provider refusal is never retried here.
"""
from __future__ import annotations

import re

from loop_engine.core.library_ingestion.https_transport import HttpsResponse, outcome_for
from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog, RequestObservation
from query_multiplier.executors import Executor
from query_multiplier.transport import RequestRefused, Transport, load_policy

from .engines_network import RadarNetwork
from .trendshift_engines import source_contract
from .trendshift_request import MAXIMUM_BYTES, PUBLIC, SIGNAL

KEY_VARIABLE = "TRENDSHIFT_API_KEY"


class _PublicHttp(Executor):
    executor_id, host, access = PUBLIC, "trendshift.io", "https_get"
    accept = "text/html"


class _SignalHttp(Executor):
    executor_id, host, access = SIGNAL, "api.trendshift.io", "https_get_key"
    key_variable = KEY_VARIABLE


class TrendshiftGet:
    """Translate one source-contract GET to the shared transport; never accept another host."""

    def __init__(self, request, budget, log, *, transport=None):
        self.request, self.budget, self.log = request, budget, log
        self.executor = _SignalHttp() if request.engine == SIGNAL else _PublicHttp()
        self.transport = transport or Transport(load_policy(), maximum_bytes=MAXIMUM_BYTES, timeout_seconds=20)
        self.last_headers = {}
        self.selection = None

    def _request(self, host, path, query):
        if host != self.executor.host:
            raise RequestRefused("trendshift_fixed_host_required")
        return self.executor.request(path, list((query or {}).items()), page=1)

    def preflight(self, today):
        if self.request.engine == SIGNAL:
            key = self.transport.environment.get(KEY_VARIABLE, "")
            if key and not re.fullmatch(r"ts_live_[0-9a-fA-F]{64}", key):
                raise RequestRefused("trendshift_key_format_invalid")
        host, path, query, _ = self.request.target(today)
        self.transport.check(self.executor, self._request(host, path, query))
        self.selection = host, path, query

    def get(self, host, path, query=None, *, validators=None):
        request = self._request(host, path, query)
        if self.selection is None:
            raise RequestRefused("trendshift_preflight_required")
        if (host, path, query or {}) != self.selection:
            raise RequestRefused("trendshift_fixed_selection_required")
        self.transport.check(self.executor, request)
        self.budget.admit()
        started = now_utc()
        answer = self.transport.send(self.executor, request)
        self.last_headers = answer.headers
        key = self.transport.environment.get(KEY_VARIABLE, "") if self.request.engine == SIGNAL else ""
        if key and key.encode() in answer.body:
            self.log.record(RequestObservation("https_get", host, answer.target, answer.status, None, started,
                answer.elapsed_ms, "http_error", error_class="credential_echo_refused"))
            return HttpsResponse(None, b"")
        status = None if answer.truncated else answer.status
        self.log.record(RequestObservation("https_get", host, answer.target, status, answer.body, started,
            answer.elapsed_ms, outcome_for(status), error_class="response_too_large" if answer.truncated else answer.error_class))
        return HttpsResponse(status, answer.body if status is not None else b"")


def network_for(request, *, transport=None):
    budget, log = RequestBudget(1, maximum_pause_seconds=0, reserve=0), RequestLog()
    contract = source_contract(request.engine)
    network = RadarNetwork(budget, log, {request.engine: contract})
    adapter = TrendshiftGet(request, budget, log, transport=transport)
    accept = "application/json" if request.engine == SIGNAL else "text/html"
    network.transports[(request.engine, accept)] = adapter
    network.trendshift_managed_transport = True
    network.trendshift_authenticated_transport = request.engine == SIGNAL
    return network, adapter
