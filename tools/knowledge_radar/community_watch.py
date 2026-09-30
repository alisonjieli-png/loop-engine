"""One bounded, resumable community discovery tick owned by canonical Loops.

Source state and leads use managed records; work uses the existing reactive
scheduler. Transports retain no thread bodies. A failed source keeps its last
successful state, conditional validators and explicit backoff. Repeated reads
deduplicate before work. Nothing approves or publishes library components.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlsplit

from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
from loop_engine.loop.service_loop_envelope import (
    ServiceLoopSpec,
    run_service_operation,
)

from .community_intake import make_lead, parse_feed
from .community_store import CommunityStore
from .community_work import open_queue, queue_lead, reconcile_definition, work_once
from .engines_network import RadarNetwork, request_key
from .records import SourceContract


def clock():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def later(now, seconds):
    return (datetime.fromisoformat(now.replace("Z", "+00:00")) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def due(state, now):
    return not state or state["data"].get("next_check_at", "") <= now


def network_for(registry, request_log):
    contracts = {}
    for source in registry["sources"]:
        contracts[source["id"]] = SourceContract(source["id"], "1.0.0", "https_get",
            (urlsplit(source["url"]).hostname,), "Private link discovery and keyword hints only",
            "No archive, media, credentials, copied code, executable instructions or publication",
            source["url"], source["terms_url"], 2.0, 1, "Record failure and back off; never bypass access controls",
            maximum_response_bytes=2 * 1024 * 1024, republication="live_lookup_only")
    network = RadarNetwork(RequestBudget(registry["maximum_reads_per_tick"], maximum_pause_seconds=0, reserve=0),
                           request_log, contracts)
    accept = "application/rss+xml, application/atom+xml, application/xml"
    for source_id, contract in contracts.items():
        network.transports[(source_id, accept)] = HttpsGetTransport(contract.hosts, network.budget, request_log,
            timeout_seconds=15, maximum_bytes=contract.maximum_response_bytes, accept=accept)
    return network


def ingest(store, scheduler, series, leads, now, loop_id):
    added, changed, queued = 0, 0, 0
    for lead in leads:
        previous = store.get(lead.identity)
        same = previous and previous["document"]["data"]["content_digest"] == lead.content_digest
        if same:
            held, version = previous["document"], previous["version"]
        else:
            data = {**lead.to_dict(), "first_observed_at": previous["document"]["data"]["first_observed_at"] if previous else now,
                    "observed_at": now}
            version = store.put(lead.identity, "lead", lead.source_id, "recorded", data, expected=previous)
            held = store.get(lead.identity, version)["document"]
            added += not bool(previous)
            changed += bool(previous)
        # Always reconcile queue admission, even if a crash occurred after storing a lead.
        queued += queue_lead(scheduler, series, lead.identity, version, held, now, loop_id)
    return {"added": added, "changed": changed, "work_queued": queued}


def scan_feeds(registry, store, scheduler, series, network, now, *, force=False):
    checks = []
    for source in registry["sources"]:
        if not source["enabled"]:
            continue
        identity = "community.source." + source["id"]
        previous = store.get(identity)
        document = previous["document"] if previous else None
        if not force and not due(document, now):
            checks.append({"source": source["id"], "status": "not_due"})
            continue
        old = document["data"] if document else {}
        binding = hashlib.sha256((source["engine"] + ":" + source["url"]).encode()).hexdigest()
        if old.get("binding_digest") != binding:
            old = {}
        state = {**old, "last_attempted_at": now, "next_check_at": later(now, source["interval_seconds"])}
        state["binding_digest"] = binding
        part = urlsplit(source["url"])
        query = dict(parse_qsl(part.query, keep_blank_values=True))
        key = request_key(part.hostname, part.path, query)
        network.conditional = {key: old["validators"]} if old.get("validators") else {}
        result = {"source": source["id"], "status": "failed"}

        def collect(active, source=source, part=part, old=old, state=state, query=query):
            response = network.get(source["id"], part.hostname, part.path, query, accept="application/rss+xml, application/atom+xml, application/xml")
            if response.status == 304:
                if not old.get("last_successful_at") or not old.get("validators"):
                    raise ValueError("unbound_304")
                return {"status": "not_modified"}
            if response.status != 200:
                raise ValueError("source_http_" + str(response.status))
            leads, coverage = parse_feed(response.body, source, registry)
            counts = ingest(store, scheduler, series, leads, now, active.loop_id)
            if not coverage["truncated"]:
                state["validators"] = {key: value for key, value in (("etag", response.etag), ("last_modified", response.last_modified)) if value}
            else:
                state["validators"] = {}
            return {"status": "checked", "leads": len(leads), "coverage": coverage, **counts}

        try:
            result.update(run_service_operation(store.runtime, ServiceLoopSpec("community_feed_read", "practitioner.code_execution",
                "community_source_read/v1", "community_source_result/v1", ("reads_fs", "writes_fs", "network"),
                "Read one declared feed and queue its metadata.", "community_source_failed"), collect))
            state.update(last_successful_at=now, failures=0)
        except Exception as error:  # noqa: BLE001 - isolate external engine failure without marking success
            # No raw body, credential or source instruction enters the diagnostic.
            result["reason"] = str(error)[:120] if isinstance(error, ValueError) else type(error).__name__
            state["failures"] = min(10, old.get("failures", 0) + 1)
            state["next_check_at"] = later(now, min(86400, source["interval_seconds"] * 2 ** state["failures"]))
        finally:
            network.conditional = {}
        state["status"] = result["status"]
        store.put(identity, "source", source["id"], "failed" if result["status"] == "failed" else "recorded", state, expected=previous)
        checks.append(result)
    return checks


def scan_research(registry, store, scheduler, series, now, researcher):
    """At most one native harness invocation per tick, with a durable daily ceiling."""
    budget_id = "community.budget." + now[:10]
    budget = store.get(budget_id)
    count = budget["document"]["data"]["invocations_reserved"] if budget else 0
    if budget and budget["document"]["data"].get("blocked_until", "") > now:
        return {"status": "provider_backoff"}
    if count >= registry["maximum_harness_runs_per_day"]:
        return {"status": "daily_invocation_limit"}
    topics = []
    for topic in registry["research_topics"]:
        held = store.get("community.source.research_" + topic["id"])
        attempted = held["document"]["data"].get("last_attempted_at", "") if held else ""
        topics.append((attempted, topic["id"], topic))
    for _attempted, _identity, topic in sorted(topics):
        identity = "community.source.research_" + topic["id"]
        previous = store.get(identity)
        if not due(previous["document"] if previous else None, now):
            continue
        # Reserve before dispatch. An interrupted or unknown outcome still consumes the reservation.
        store.put(budget_id, "harness_budget", "native_web_research", "recorded",
                  {"day_utc": now[:10], "invocations_reserved": count + 1}, expected=budget)
        answer = researcher(topic, store.runtime, authorized=True)
        old = previous["document"]["data"] if previous else {}
        state = {**old, "last_attempted_at": now, "next_check_at": later(now, topic["interval_seconds"]),
                 "status": answer["status"], "engine": answer.get("engine"), "reason": answer.get("reason", "")}
        if answer["status"] == "complete":
            leads = []
            for row in answer["findings"]:
                content = " ".join([row["summary"], *row["tools"], *row["steps"], *row["constraints"]])
                from html import escape
                content = escape(content) + " ".join('<a href="' + escape(url, quote=True) + '">source</a>' for url in row["linked_sources"])
                lead = make_lead("research_" + topic["id"], row["source_url"], row["title"], content, "", registry)
                if lead:
                    leads.append(lead)
            answer["intake"] = ingest(store, scheduler, series, leads, now, answer["loop_id"])
            state["last_successful_at"] = now
        else:
            state["next_check_at"] = later(now, 86400)
            if answer.get("reason") in ("usage_limit", "existing_subscription_login_not_confirmed"):
                held_budget = store.get(budget_id)
                store.put(budget_id, "harness_budget", "native_web_research", "recorded",
                          {**held_budget["document"]["data"], "blocked_until": later(now, 86400)}, expected=held_budget)
        store.put(identity, "source", "research_" + topic["id"], "recorded" if answer["status"] == "complete" else "failed", state, expected=previous)
        run_id = "community.run.research." + store.run_id
        store.put(run_id, "run", "research_" + topic["id"], "complete" if answer["status"] == "complete" else "failed", answer)
        return {"topic": topic["id"], **{key: value for key, value in answer.items() if key != "findings"},
                "findings": len(answer.get("findings", []))}
    return {"status": "not_due"}


def tick(registry, root, *, network_allowed=False, writes_allowed=False, native_research_allowed=False,
         now=None, force=False, network=None, researcher=None):
    if not writes_allowed or not network_allowed:
        return {"record_type": "community_watch_plan/v1", "preview": True, "sources": registry["sources"],
                "research_topics": registry["research_topics"], "effects_performed": False}
    store = CommunityStore(root, writes_allowed=True)
    store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = os.open(store.root / "scan.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    scheduler = None
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"record_type": "community_watch_run/v1", "status": "already_running"}
        moment = now or clock()
        scheduler, series = open_queue(store)
        reconciliation = reconcile_definition(store, scheduler, series, moment)
        request_log = RequestLog()
        source_network = network or network_for(registry, request_log)
        checks = scan_feeds(registry, store, scheduler, series, source_network, moment, force=force)
        research_result = {"status": "not_authorized"}
        if native_research_allowed:
            from .community_harness import research
            try:
                research_result = scan_research(registry, store, scheduler, series, moment, researcher or research)
            except Exception as error:  # noqa: BLE001 - keep successful feed work when the external harness fails
                research_result = {"status": "failed", "reason": type(error).__name__}
        work = work_once(store, scheduler, series, moment, maximum=registry["maximum_work_items_per_tick"])
        partial = any(row["status"] == "failed" for row in checks) or research_result["status"] in ("failed", "unavailable")
        report = {"record_type": "community_watch_run/v1", "run_id": store.run_id, "at": moment, "status": "partial" if partial else "complete",
                  "sources": checks, "requests": request_log.summary(), "research": research_result,
                  "compiler_reconciliation": reconciliation,
                  "work_orders_compiled": len(work), "work_order_ids": work, "loop_events": len(store.ledger.events),
                  "components_published": 0, "posts_sent": 0, "thread_bodies_stored": False}
        identity = "community.run." + store.run_id
        store.put(identity, "run", "community_watch", "failed" if partial else "complete", report)
        return report
    finally:
        if scheduler is not None:
            scheduler.close()
        os.close(lock)
