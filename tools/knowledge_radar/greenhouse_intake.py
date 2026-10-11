"""One public ATS read with existing durable quota, transport, Loop and records.

All Greenhouse boards share the host's one public-account quota binding.
No raw response, custom metadata, applicant field or job description is saved.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import urllib.request

from loop_engine.core.library_ingestion.https_transport import HttpsResponse, outcome_for
from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog, RequestObservation
from loop_engine.core.web_research_quota import DurableSearchQuota, QuotaOutcome, QuotaRefused
from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
from query_multiplier.executors import Executor
from query_multiplier.transport import RequestRefused, Transport, _NoRedirect, load_policy

from .community_intake import Lead
from .community_store import CommunityStore
from .community_work import component_work
from .engines import FAILED
from .engines_network import RadarNetwork
from .greenhouse_source import (ACCOUNT, ENGINE, HOST, MAXIMUM_BYTES, REQUEST, RESULT, RIGHTS,
                                GreenhouseError, GreenhousePublicJobs, read_context, source_contract)


class _GreenhouseHttp(Executor):
    executor_id, host, access = ENGINE, HOST, "https_get"


class GreenhouseGet:
    """Exactly one metadata-only list target, using the shared bounded transport."""

    def __init__(self, request, quota, budget, log, *, transport=None):
        self.selection, self.quota, self.budget, self.log = request, quota, budget, log
        self.executor = _GreenhouseHttp()
        self.transport = transport or Transport(load_policy(), maximum_bytes=MAXIMUM_BYTES, timeout_seconds=10,
            environment={}, opener=urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect))
        self.reservation_id = None

    def _request(self, host, path, query):
        if (host, path, query or {}) != (HOST, self.selection.path, {}):
            raise RequestRefused("greenhouse_fixed_metadata_target_required")
        return self.executor.request(path, [], page=1)

    def preflight(self):
        if type(self.quota) is not DurableSearchQuota or not self.quota.allow_writes:
            raise RequestRefused("greenhouse_shared_quota_required")
        policy = self.quota.policy.account(ACCOUNT)
        if policy.window_requests != 1 or policy.window_seconds < 10:
            raise RequestRefused("greenhouse_minimum_pacing_required")
        if self.transport.maximum_bytes > MAXIMUM_BYTES:
            raise RequestRefused("greenhouse_transport_bound_required")
        self.transport.check(self.executor, self._request(HOST, self.selection.path, {}))

    def get(self, host, path, query=None, *, validators=None):
        request = self._request(host, path, query)
        self.preflight()
        if self.reservation_id is not None:
            raise RequestRefused("greenhouse_one_dispatch_per_run")
        self.reservation_id = self.quota.reserve(ACCOUNT, sha256(json.dumps(request, sort_keys=True).encode()).hexdigest())
        self.budget.admit()
        started = now_utc()
        try:
            answer = self.transport.send(self.executor, request)
        except Exception:
            # A transport exception after reservation has an unknown outcome.
            # The shared quota retains the charge and prevents a later retry.
            self.quota.finish(self.reservation_id, QuotaOutcome(None, False, None, None, False, None))
            self.log.record(RequestObservation("https_get", HOST, self.selection.url, None, None,
                started, 0, "transport_error", error_class="unknown_dispatch_outcome"))
            return HttpsResponse(None, b"")
        truncated = answer.truncated or len(answer.body) > MAXIMUM_BYTES
        status = None if truncated else answer.status
        digest = sha256(answer.body).hexdigest()
        retry = answer.headers.get("retry-after", "")
        retry_seconds = int(retry) if type(retry) is str and retry.isascii() and retry.isdigit() and len(retry) <= 7 else None
        remaining = answer.headers.get("x-ratelimit-remaining")
        malformed_remaining = remaining is not None and not (type(remaining) is str
            and remaining.isascii() and remaining.isdigit() and len(remaining) <= 12)
        exhausted = remaining == "0" or malformed_remaining
        if malformed_remaining:
            retry_seconds = None
        self.quota.finish(self.reservation_id, QuotaOutcome(status, status == 200, None, retry_seconds, exhausted, digest))
        self.log.record(RequestObservation("https_get", HOST, self.selection.url, status,
            answer.body if not truncated else None, started, answer.elapsed_ms, outcome_for(status),
            error_class="response_too_large" if truncated else answer.error_class))
        return HttpsResponse(status, answer.body if status is not None else b"")


def network_for(request, quota, *, transport=None):
    budget, log = RequestBudget(1, maximum_pause_seconds=0, reserve=0), RequestLog()
    network = RadarNetwork(budget, log, {ENGINE: source_contract()})
    adapter = GreenhouseGet(request, quota, budget, log, transport=transport)
    network.transports[(ENGINE, "application/json")] = adapter
    network.greenhouse_managed_transport = True
    return network, adapter


def enqueue(store, observations, *, prepare_work=False):
    for item in observations:
        identity = "community.lead.greenhouse." + sha256(item.origin.encode()).hexdigest()
        signals = tuple(filter(None, item.facts["signals"].split(",")))
        tools = tuple(filter(None, item.facts["tools_mentioned"].split(",")))
        lead = Lead(ENGINE, item.url, item.title, item.source_published_at, item.facts["metadata_sha256"],
                    tools, signals, (item.source_address,), 0)
        data = {**lead.to_dict(), "observation": item.to_dict(), "rights": dict(RIGHTS),
                "evidence_class": "public_job_metadata_unverified", "content_is_untrusted": True,
                "classification": "literal_title_keywords_not_verified_tasks", "task_evidence": "not_collected",
                "independent_review": "not_done", "publication_authorized": False, "execution_authorized": False}
        store.put(identity, "lead", ENGINE, "needs_research", data, expected=store.get(identity))
        if prepare_work:
            work_id = "community.brief.greenhouse." + sha256((item.origin + item.facts["metadata_sha256"]).encode()).hexdigest()
            work = {**component_work(data), "source_observation": item.to_dict(), "lead_identity": identity,
                    "task_basis": "title_keyword_inference_only", "task_evidence": "not_collected",
                    "blocking_findings": ["Verify substantive responsibilities before opportunity generation",
                                          "Source reuse rights remain unestablished"]}
            store.put(work_id, "research_brief", ENGINE, "deferred", work, expected=store.get(work_id))
    return len(observations)


def read_once(request, root=None, *, quota=None, network_allowed=False, writes_allowed=False,
              queue_results=False, prepare_work=False, transport=None):
    if any(type(flag) is not bool for flag in (network_allowed, writes_allowed, queue_results, prepare_work)):
        raise GreenhouseError("greenhouse_grant_invalid")
    if not network_allowed or not writes_allowed:
        return {"record_type": RESULT, "status": "plan", "request": request.to_record(), "host": HOST,
                "path": request.path, "query": {}, "effects_performed": False, "physical_send_attempts": 0,
                "requires_credentials": False, "shared_quota_account": ACCOUNT, "rights": dict(RIGHTS)}
    if prepare_work and not queue_results:
        raise GreenhouseError("greenhouse_work_requires_leads")
    if not isinstance(root, Path):
        raise GreenhouseError("greenhouse_private_state_required")
    network, adapter = network_for(request, quota, transport=transport)
    adapter.preflight()
    store = CommunityStore(root, writes_allowed=True)

    def collect(active):
        moment = now_utc()
        try:
            answer = GreenhousePublicJobs().read(read_context(request, observed_at=moment, network=network))
        except (QuotaRefused, RequestRefused) as error:
            return {"record_type": RESULT, "status": "refused", "reason": str(error),
                    "physical_send_attempts": network.budget.used, "request": request.to_record()}
        count = enqueue(store, answer.observations, prepare_work=prepare_work) if queue_results else 0
        report = {"record_type": RESULT, "status": answer.status, "reason": answer.reason,
                  "request": request.to_record(), "observed_at": moment, "records": len(answer.observations),
                  "excluded": list(answer.excluded), "complete_selected_board": answer.complete,
                  "closure_inference_performed": False, "physical_send_attempts": network.budget.used,
                  "request_log": network.log.records, "quota_reservation_id": adapter.reservation_id,
                  "quota_binding_digest": quota.binding_digest, "shared_quota_account": ACCOUNT,
                  "private_leads_recorded": count, "deferred_work_orders_recorded": count if prepare_work else 0,
                  "loop_id": active.loop_id, "rights": dict(RIGHTS), "components_published": 0,
                  "task_evidence_collected": False, "documents_url": source_contract().terms_address}
        store.put("community.run.greenhouse." + store.run_id, "run", ENGINE,
                  "failed" if answer.status == FAILED else "complete", report)
        return report

    return run_service_operation(store.runtime, ServiceLoopSpec("greenhouse_source_intake", "practitioner.code_execution",
        REQUEST, RESULT, ("reads_fs", "writes_fs", "network"), "Read one public ATS metadata list into private records.",
        "greenhouse_source_failed"), collect)
