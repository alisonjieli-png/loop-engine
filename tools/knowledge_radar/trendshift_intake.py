"""One private Trendshift read or capture import, owned by the existing Loop and managed store.

Both engines share the same source reservation, cooldown and provider hold.
An interrupted read stays charged and requires explicit local reconciliation.
Leads never approve themselves, become public files or start another job.
"""
from __future__ import annotations

import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from loop_engine.core.library_ingestion.record_rules import now_utc, utc_time
from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
from query_multiplier.transport import RequestRefused

from .community_intake import Lead
from .community_store import CommunityStore
from .engines import FAILED, EngineAnswer
from .trendshift_engines import TrendshiftPublic, TrendshiftSignal, read_context
from .trendshift_network import network_for
from .trendshift_request import MAXIMUM_BYTES, MINIMUM_INTERVAL_SECONDS, PUBLIC, RIGHTS, SIGNAL, SPIKES, TrendshiftError

ACCESS_ID = "community.source.trendshift.access"
ACCESS_RECORD = "trendshift_access_state/v1"
RESULT = "trendshift_source_result/v1"
QUOTA_HOLD = "trendshift_quota_hold/v1"
QUOTA_REASONS = ("exhausted_without_future_reset", "malformed_remaining_allowance", "rate_limited_without_retry_evidence")


def _later(now, seconds):
    return (datetime.fromisoformat(now.replace("Z", "+00:00")) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _engine(request):
    return TrendshiftPublic() if request.engine == PUBLIC else TrendshiftSignal()


def _report(request, answer, observed_at, *, requests=0, reserved=0, page=None):
    freshness = {}
    for item in answer.observations:
        label = item.facts["freshness"]
        freshness[label] = freshness.get(label, 0) + 1
    return {"record_type": RESULT, "engine": request.engine, "request": request.to_record(),
            "observed_at": observed_at, "status": answer.status, "reason": answer.reason,
            "records": len(answer.observations), "excluded": list(answer.excluded),
            "complete_selected_source_page": answer.complete, "physical_requests": requests,
            "requests_reserved": reserved, "unknown_dispatch_outcomes": max(0, reserved - requests),
            "source_rows": page.source_rows if page is not None else None,
            "source_list_date": page.source_date if page is not None else None,
            "next_cursor": page.next_cursor if page is not None else None,
            "empty_source_list_observed": page is not None and page.source_rows == 0,
            "history_requested": request.period is not None or request.kind == SPIKES,
            "freshness_counts": freshness,
            "rights": dict(RIGHTS), "components_published": 0, "external_messages_sent": 0}


def enqueue(store, request, observations):
    """Private managed leads only; source data cannot alter review or publication state."""
    count = 0
    selection = request.to_record()
    selection.pop("cursor", None);selection.pop("limit", None)
    for observation in observations:
        identity = "community.lead.trendshift." + sha256(json.dumps(
            {"origin": observation.origin, "selection": selection}, sort_keys=True).encode()).hexdigest()
        previous = store.get(identity)
        lead = Lead("trendshift", observation.url, observation.title, observation.source_published_at,
                    observation.facts["source_body_sha256"], (), (), (observation.source_address,), 0)
        data = {**lead.to_dict(), "observation": observation.to_dict(),
                "evidence_class": "unverified_provider_ranking", "classification": "no_workflow_hints_inferred",
                "request": request.to_record(), "rights": dict(RIGHTS), "content_is_untrusted": True,
                "independent_review": "not_done", "repository_code_licence": "not_checked",
                "publication_authorized": False, "execution_authorized": False}
        store.put(identity, "lead", "trendshift", "needs_research", data, expected=previous)
        count += 1
    return count


def parse_capture(request, path: Path, *, observed_at=None):
    moment = utc_time(observed_at or now_utc(), "observed_at")
    with Path(path).open("rb") as stream:body = stream.read(MAXIMUM_BYTES + 1)
    context = read_context(request, observed_at=moment)
    request.target(context.today)
    try:
        answer, page = _engine(request).parse_with_page(context, body, transport_observed=False)
    except (ValueError, RecursionError):
        answer = EngineAnswer(FAILED, "capture_parse_failed", complete=False)
        page = None
    report = _report(request, answer, moment, page=page)
    report.update(capture_sha256=sha256(body).hexdigest(), capture_kind="operator_supplied_not_a_transport_read",
                  capture_digest_scope="complete_file" if len(body) <= MAXIMUM_BYTES else "oversized_file_prefix_only")
    return report, answer.observations


def _private_lock(store):
    store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(store.root / "scan.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _access(previous):
    if previous is None:return {"record_type": ACCESS_RECORD, "reservations_total": 0, "request_state": "idle"}
    data = previous["document"]["data"]
    if data.get("record_type") != ACCESS_RECORD or type(data.get("reservations_total")) is not int or data["reservations_total"] < 0:
        raise TrendshiftError("trendshift_access_state_invalid")
    if data.get("request_state") not in ("idle", "pending", "completed", "closed_unknown"):
        raise TrendshiftError("trendshift_access_state_invalid")
    for key in ("next_allowed_at", "blocked_until"):
        if key in data:utc_time(data[key], key)
    if "quota_hold" in data:
        hold = data["quota_hold"]
        if (type(hold) is not dict or set(hold) != {"record_type", "source_id", "observed_at", "reason"}
                or hold.get("record_type") != QUOTA_HOLD or hold.get("source_id") != "trendshift"
                or hold.get("reason") not in QUOTA_REASONS):
            raise TrendshiftError("trendshift_quota_hold_invalid")
        utc_time(hold["observed_at"], "quota_hold.observed_at")
    return dict(data)


def _header_integer(value):
    return int(value) if type(value) is str and value.isascii() and value.isdigit() and len(value) <= 12 else None


def _quota_hold(status, headers, now):
    """An exhausted allowance needs evidence of a future reset, not a guessed delay."""
    remaining = headers.get("x-ratelimit-remaining")
    amount = _header_integer(remaining)
    reset = _header_integer(headers.get("x-ratelimit-reset"))
    epoch = datetime.fromisoformat(now.replace("Z", "+00:00")).timestamp()
    known_reset = reset is not None and epoch < reset <= 253402300799
    reason = None
    if remaining is not None and amount is None:
        reason = QUOTA_REASONS[1]
    elif amount == 0 and not known_reset:
        reason = QUOTA_REASONS[0]
    elif status == 429 and not known_reset:
        retry = _header_integer(headers.get("retry-after"))
        if retry is None or not 0 < retry <= 86400:reason = QUOTA_REASONS[2]
    return ({"record_type": QUOTA_HOLD, "source_id": "trendshift", "observed_at": now, "reason": reason}
            if reason is not None else None)


def _blocked_until(status, headers, now):
    waits = [86400] if status in (401, 403) else []
    if status == 429:waits.append(60)
    value = headers.get("retry-after", "")
    if type(value) is str and value.isascii() and value.isdigit() and len(value) <= 8:waits.append(int(value))
    elif type(value) is str and value:
        try:
            retry = parsedate_to_datetime(value)
            if retry.tzinfo is not None:
                waits.append(max(0, int((retry - datetime.fromisoformat(now.replace("Z", "+00:00"))).total_seconds())))
        except (ValueError, TypeError, OverflowError):
            pass
    if status == 429 or _header_integer(headers.get("x-ratelimit-remaining")) == 0:
        reset = headers.get("x-ratelimit-reset", "")
        if type(reset) is str and reset.isascii() and reset.isdigit() and len(reset) <= 12:
            epoch = int(datetime.fromisoformat(now.replace("Z", "+00:00")).timestamp())
            if epoch < int(reset) <= 253402300799:waits.append(int(reset) - epoch)
    if not waits:return None
    ceiling = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    remaining = int((ceiling - datetime.fromisoformat(now.replace("Z", "+00:00"))).total_seconds())
    return _later(now, min(max(waits), remaining))


def read_once(request, root, *, network_allowed=False, writes_allowed=False, queue_results=False,
              observed_at=None, transport=None):
    moment = utc_time(observed_at or now_utc(), "observed_at")
    host, path, query, _ = request.target(moment[:10])
    if not network_allowed or not writes_allowed:
        return {"record_type": "trendshift_read_plan/v1", "request": request.to_record(), "host": host,
                "path": path, "query": query, "effects_performed": False, "physical_requests": 0,
                "requires_existing_signal_key": request.engine == SIGNAL, "rights": dict(RIGHTS)}
    store = CommunityStore(root, writes_allowed=True)
    try:lock = _private_lock(store)
    except BlockingIOError:return {"record_type": RESULT, "status": "already_running", "physical_requests": 0}
    try:
        previous = store.get(ACCESS_ID);state = _access(previous)
        if state["request_state"] == "pending":
            return {"record_type": RESULT, "status": "reconcile_required", "physical_requests": 0}
        if state.get("quota_hold"):
            return {"record_type": RESULT, "status": "needs_verified_quota_reconciliation", "physical_requests": 0,
                    "quota_hold": state["quota_hold"], "reservations_total": state["reservations_total"]}
        if state.get("blocked_until", "") > moment or state.get("next_allowed_at", "") > moment:
            return {"record_type": RESULT, "status": "source_hold", "physical_requests": 0,
                    "next_allowed_at": max(state.get("blocked_until", ""), state.get("next_allowed_at", ""))}
        effects = ("reads_fs", "writes_fs", "network") + (("reads_secret",) if request.engine == SIGNAL else ())

        def collect(active):
            network, adapter = network_for(request, transport=transport)
            try:adapter.preflight(moment[:10])
            except RequestRefused as error:
                return {"record_type": RESULT, "status": "refused", "reason": error.code, "physical_requests": 0}
            reserved = {**state, "reservations_total": state["reservations_total"] + 1,
                        "request_state": "pending", "last_attempted_at": moment,
                        "next_allowed_at": _later(moment, MINIMUM_INTERVAL_SECONDS), "request": request.to_record()}
            store.put(ACCESS_ID, "source", "trendshift", "recorded", reserved, expected=previous)
            context = read_context(request, observed_at=moment, network=network)
            try:answer, page = _engine(request).read_with_page(context)
            except Exception as error:
                answer = EngineAnswer(FAILED, error.code if isinstance(error, (TrendshiftError, RequestRefused)) else type(error).__name__, complete=False)
                page = None
            report = _report(request, answer, moment, requests=len(network.log.records), reserved=network.budget.used, page=page)
            report["request_log"] = network.log.records
            report["private_leads_recorded"] = enqueue(store, request, answer.observations) if queue_results else 0
            report["loop_id"] = active.loop_id
            held = store.get(ACCESS_ID)
            finished_at = moment if observed_at is not None else now_utc()
            finished = {**reserved, "request_state": "pending" if report["unknown_dispatch_outcomes"] else "completed",
                        "last_outcome": answer.status, "physical_requests_last_run": len(network.log.records),
                        "unknown_dispatch_outcomes_last_run": report["unknown_dispatch_outcomes"],
                        "next_allowed_at": _later(finished_at, MINIMUM_INTERVAL_SECONDS)}
            status = network.log.records[-1]["status"] if network.log.records else None
            blocked = _blocked_until(status, adapter.last_headers, finished_at)
            if blocked:finished["blocked_until"] = blocked
            quota_hold = _quota_hold(status, adapter.last_headers, finished_at)
            if quota_hold:
                finished["quota_hold"] = quota_hold
                report["quota_hold"] = quota_hold
            if answer.status != FAILED:finished["last_successful_at"] = moment
            store.put("community.run.trendshift." + store.run_id, "run", "trendshift",
                      "failed" if answer.status == FAILED else "complete", report)
            store.put(ACCESS_ID, "source", "trendshift", "recorded", finished, expected=held)
            return report

        return run_service_operation(store.runtime, ServiceLoopSpec("trendshift_source_intake", "practitioner.code_execution",
            "trendshift_source_request/v1", RESULT, effects, "Read one Trendshift source page into private research records.",
            "trendshift_source_failed"), collect)
    finally:os.close(lock)


def reconcile_unknown(root, *, writes_allowed=False):
    if not writes_allowed:raise PermissionError("local_write_grant_required")
    store = CommunityStore(root, writes_allowed=True)
    lock = _private_lock(store)
    try:
        previous = store.get(ACCESS_ID);state = _access(previous)
        if state["request_state"] != "pending":return {"status": "nothing_to_reconcile", "physical_requests": 0}
        store.put(ACCESS_ID, "source", "trendshift", "failed", {**state, "request_state": "closed_unknown",
            "last_outcome": "unknown_read_outcome", "reconciled_at": now_utc()}, expected=previous)
        return {"status": "closed_unknown", "reservations_total": state["reservations_total"], "physical_requests": 0}
    finally:os.close(lock)


def import_capture(request, root, report, observations, *, writes_allowed=False):
    if not writes_allowed:raise PermissionError("local_write_grant_required")
    store = CommunityStore(root, writes_allowed=True);lock = _private_lock(store)
    try:
        recorded = enqueue(store, request, observations)
        result = {**report, "private_leads_recorded": recorded}
        store.put("community.run.trendshift." + store.run_id, "run", "trendshift", "recorded", result)
        return result
    finally:os.close(lock)
