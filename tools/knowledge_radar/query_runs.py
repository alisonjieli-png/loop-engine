"""Query pages and attempts in the existing CommunityStore, not a second queue.

Manual, bounded ticks. No scheduler, provider, source registry or publication
path is installed. Unexecuted queries are source/run records, never observed
community leads. A crash after reserving a read leaves an explicit hold; it
does not silently repeat an external request. Retry requires reconciliation.
"""
from __future__ import annotations

import fcntl
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
from .community_store import CommunityStore
from .engines import ReadContext, default_registry
from .engines_network import RadarNetwork
from .query_matrix import GATES, PAGE, QUERY, QUERY_PARAMETERS, compile_query, cursor_for, digest, integer, page, strict, words
from .records import SourceBinding, read_observation, read_registry

WORK = "knowledge_radar_query_work/v1"
ATTEMPT = "knowledge_radar_query_attempt/v1"
PROGRESS = "knowledge_radar_query_progress/v1"
JOURNAL = "knowledge_radar_query_journal/v1"
RESULT = "knowledge_radar_query_tick/v1"


def clock():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def query_identity(work_id):
    return "community.query.work." + work_id


def read_query(value, matrix):
    strict(value, ("record_type", "query_id", "work_id", "plan_digest", "route", "facets", "query", "engine", "source_contract_digest", "dispatch", "purpose", "gates"), "query")
    if value["record_type"] != QUERY or value["gates"] != GATES or type(value["facets"]) is not dict or not 1 <= len(value["facets"]) <= 8:
        raise ValueError("query_contract")
    if value["plan_digest"] != matrix.plan_digest:
        raise ValueError("query_plan_binding")
    route = next((row for row in matrix.document["routes"] if row["id"] == value["route"]), None)
    if route is None or set(value["facets"]) != set(route["dimensions"]):
        raise ValueError("query_route_binding")
    for name, term in value["facets"].items():
        allowed = {words(candidate) for candidate in matrix.document["vocabulary"][name]}
        if words(term) != term or term not in allowed:
            raise ValueError("query_facet_binding")
    expected, reason = compile_query(matrix, route, value["facets"])
    if reason or digest(value) != digest(expected):
        raise ValueError("query_binding")
    return value


def read_page(value, matrix, cursor, *, limit, scan_limit):
    """Replay a bounded held page from its cursor, not from its claimed counts.

    Membership of omitted valid work can change during partial enqueue. The
    held selected IDs reconstruct that dedup mask; canonical replay still
    checks each emitted query, traversal, exclusion, count and next cursor.
    This detects corrupt records, not a malicious writer able to forge the
    entire operator-owned store and its inputs.
    """
    strict(value, ("record_type", "plan_digest", "limits", "cursor", "next_cursor", "queries", "complete",
                   "raw_combinations_upper_bound", "counts", "coverage"), "query_page")
    if value["record_type"] != PAGE or value["plan_digest"] != matrix.plan_digest or value["cursor"] != cursor:
        raise ValueError("query_page_binding")
    strict(value["limits"], ("page_size", "scan_limit"), "query_page_limits")
    if type(value["limits"]["page_size"]) is not int or type(value["limits"]["scan_limit"]) is not int or value["limits"] != {"page_size": limit, "scan_limit": scan_limit}:
        raise ValueError("query_page_limits_binding")
    rows = value["queries"]
    if type(rows) is not list or len(rows) > limit:
        raise ValueError("query_page_rows")
    selected = {read_query(row, matrix)["work_id"] for row in rows}
    if len(selected) != len(rows):
        raise ValueError("query_page_duplicate")
    expected = page(matrix, cursor, limit=limit, scan_limit=scan_limit, seen=lambda identity: identity not in selected)
    if digest(value) != digest(expected):
        raise ValueError("query_page_replay_binding")
    return value


def bounded_document(value):
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()) > 60000:
        raise ValueError("query_document_too_large")
    return value


def plan_into_store(store, matrix, *, limit=10, scan_limit=1000):
    """Write-ahead page makes a mid-materialization crash idempotently resumable."""
    progress_id = "community.query.progress." + matrix.plan_digest
    previous = store.get(progress_id)
    cursor = previous["document"]["data"]["cursor"] if previous else cursor_for(matrix)
    cursor_for(matrix, cursor)
    journal_id = "community.query.page." + digest(cursor)
    journal = store.get(journal_id)
    if journal:
        if journal["document"]["kind"] != "run" or journal["document"]["source_id"] != "query_planner" or journal["document"]["state"] not in ("recorded", "complete"):
            raise ValueError("query_journal_identity")
        held = journal["document"]["data"]
        strict(held, ("record_type", "page"), "query_journal")
        if held["record_type"] != JOURNAL or held["page"]["cursor"] != cursor:
            raise ValueError("query_journal_binding")
        planned = read_page(held["page"], matrix, cursor, limit=limit, scan_limit=scan_limit)
    else:
        planned = page(matrix, cursor, limit=limit, scan_limit=scan_limit,
                       seen=lambda work_id: store.get(query_identity(work_id)) is not None)
        store.put(journal_id, "run", "query_planner", "recorded",
                  bounded_document({"record_type": JOURNAL, "page": planned}))
        journal = store.get(journal_id)
    for query in planned["queries"]:
        read_query(query, matrix)
        identity = query_identity(query["work_id"])
        old = store.get(identity)
        if old is None:
            store.put(identity, "source", "query_planner", "queued" if query["dispatch"] == "supported" else "deferred",
                      {"record_type": WORK, "query": query, "attempt_id": None,
                       "outcome": "planned" if query["dispatch"] == "supported" else "deferred_adapter"})
    totals = dict(previous["document"]["data"]["totals"]) if previous else {
        "combinations_examined": 0, "queries_planned": 0, "duplicates": 0, "excluded": 0}
    for key in totals:
        value = planned["counts"][key]
        totals[key] += sum(value.values()) if isinstance(value, dict) else value
    store.put(progress_id, "source", "query_planner", "complete" if planned["complete"] else "recorded",
              {"record_type": PROGRESS, "plan_digest": matrix.plan_digest, "cursor": planned["next_cursor"],
               "totals": totals, "last_page": journal_id}, expected=previous)
    store.put(journal_id, "run", "query_planner", "complete", journal["document"]["data"], expected=journal)
    return planned, totals


def unresolved_holds(store):
    """Respect unresolved current-format records, including earlier parser binds.

    This bounded reconciliation read cannot claim an exhaustive census when
    either window fills. Stop dispatch rather than infer that no hold exists.
    Completed reads do not appear in these windows.
    """
    queries, sources = set(), set()
    incomplete = False
    for kind, state in (("source", "recorded"), ("source", "failed"), ("run", "recorded"), ("run", "failed")):
        rows = store.query(kind=kind, state=state, limit=1000)
        incomplete |= len(rows) == 1000
        for row in rows:
            data = row["document"]["data"]
            if data.get("record_type") == WORK and data.get("outcome") == "reserved_unknown_outcome" and type(data.get("query")) is dict:
                queries.add(data["query"].get("query_id"))
            if data.get("record_type") == "knowledge_radar_query_source_hold/v1" and data.get("held") is True:
                sources.add(row["document"]["source_id"])
            if data.get("record_type") == ATTEMPT and (data.get("status") == "reserved_unknown_outcome" or data.get("request_outcome_unknown") is True):
                queries.add(data.get("query_id"))
            if data.get("record_type") == ATTEMPT and any(record.get("status") in (401, 403, 404, 410, 429) for record in data.get("request_records", ())):
                sources.add(row["document"]["source_id"])
    return queries, sources, incomplete


def reconcile_interrupted(store, *, now=None):
    """Close the two recovery gaps the October 1 review left to an operator, without any request.

    An attempt still at `intent_recorded_no_dispatch` proves that no request left: the attempt is advanced to
    `reserved_unknown_outcome` before the request is sent. Such an orphan is closed as
    `abandoned_before_dispatch`, any dispatch hold naming it is released and its work returns to the queue, so it
    is dispatched at most once later and never mistaken for a held read. A completed attempt whose origins, work
    row and dispatch hold were not yet written (a crash after the result was saved) is folded from the saved
    result; the read is not repeated. Each window reads at most 1,000 records and reports when it may be capped.
    """
    now = now or clock()
    counts = {"orphan_intents_closed": 0, "saved_results_folded": 0, "windows_may_be_incomplete": False}
    intents = store.query(kind="run", state="recorded", limit=1000)
    counts["windows_may_be_incomplete"] |= len(intents) == 1000
    for row in intents:
        data = row["document"]["data"]
        if data.get("record_type") != ATTEMPT or data.get("status") != "intent_recorded_no_dispatch":
            continue
        attempt_id, engine = row["identity"], row["document"]["source_id"]
        store.put(attempt_id, "run", engine, "failed", {**data, "status": "abandoned_before_dispatch",
                                                         "reconciled_at": now}, expected=row)
        hold_id = "community.query.dispatch_hold." + str(data.get("query_id"))
        hold = store.get(hold_id)
        if hold and hold["document"]["data"].get("attempt_id") == attempt_id and hold["document"]["data"].get("held") is True:
            store.put(hold_id, "source", engine, "complete", {**hold["document"]["data"], "held": False,
                                                              "status": "abandoned_before_dispatch"}, expected=hold)
        work_id = query_identity(str(data.get("work_id")))
        work = store.get(work_id)
        if work and work["document"]["data"].get("record_type") == WORK and work["document"]["data"].get("attempt_id") in (None, attempt_id) \
                and work["document"]["data"].get("outcome") in ("planned", "reserved_unknown_outcome"):
            store.put(work_id, "source", "query_planner", "queued",
                      {**work["document"]["data"], "attempt_id": None, "outcome": "planned"}, expected=work)
        counts["orphan_intents_closed"] += 1
    works = store.query(kind="source", state="recorded", limit=1000)
    counts["windows_may_be_incomplete"] |= len(works) == 1000
    for row in works:
        data = row["document"]["data"]
        if data.get("record_type") != WORK or data.get("outcome") != "reserved_unknown_outcome" or not data.get("attempt_id"):
            continue
        attempt = store.get(data["attempt_id"])
        if attempt is None or attempt["document"]["state"] not in ("complete", "failed"):
            continue
        result = attempt["document"]["data"]
        if result.get("status") not in ("ok", "partial", "failed", "gone"):
            continue
        engine = attempt["document"]["source_id"]
        for observation in result.get("observations") or []:
            origin_id = "community.query.origin." + digest(observation["origin"])
            if store.get(origin_id) is None:
                store.put(origin_id, "source", engine, "needs_research",
                          {"record_type": "knowledge_radar_query_origin/v1", "observation": observation,
                           "first_attempt": data["attempt_id"], "gates": dict(GATES)})
        failed = result["status"] in ("failed", "gone")
        store.put(row["identity"], "source", "query_planner", "failed" if failed else "complete",
                  {**data, "outcome": result["status"]}, expected=row)
        hold_id = "community.query.dispatch_hold." + str(result.get("query_id"))
        hold = store.get(hold_id)
        if hold and hold["document"]["data"].get("attempt_id") == data["attempt_id"]:
            unknown = bool(result.get("request_outcome_unknown"))
            store.put(hold_id, "source", engine, "failed" if unknown else "complete",
                      {**hold["document"]["data"], "held": unknown,
                       "status": "reserved_unknown_outcome" if unknown else result["status"]}, expected=hold)
        counts["saved_results_folded"] += 1
    return counts


def execute_queued(store, matrix, repository, network, *, maximum_queries=5, per_source=5, now=None, engines=None):
    """Dispatch only supported bindings, through canonical Loop + radar transports.

    The query count bounds operations; RequestBudget bounds physical requests.
    Results are metadata observations with all material gates still pending.
    Nothing is promoted into the downstream component factory automatically.
    """
    integer(maximum_queries, 1, 100, "maximum_queries")
    integer(per_source, 1, 100, "per_source")
    now = now or clock()
    datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    engines = engines or default_registry(network_allowed=True)
    registry = read_registry(json.loads((Path(repository) / "tools/knowledge_radar/questions-v1.json").read_bytes()))
    template = next(question for question in registry.questions if any(binding.engine == "github_search" for binding in question.sources))
    queued = store.query(kind="source", state="queued", limit=1000)
    counts = {"queries_executed": 0, "physical_requests_reserved": 0, "request_records": 0,
              "successful_queries": 0, "empty_queries": 0, "partial_queries": 0,
              "failed_queries": 0, "new_origins": 0, "duplicate_origins": 0,
              "unknown_request_outcomes": 0, "binding_refusals": 0, "other_plan_pending": 0, "observations": 0,
              "candidate_packages_created": 0, "files_published": 0}
    attempts, by_source, source_holds, query_holds = [], {}, set(), set()
    previous_queries, previous_sources, holds_incomplete = unresolved_holds(store)
    request_start, log_start = network.budget.used, len(network.log.records)
    for row in queued:
        if holds_incomplete:
            break
        data = row["document"]["data"]
        if data.get("record_type") != WORK:
            continue
        if type(data.get("query")) is dict and data["query"].get("plan_digest") != matrix.plan_digest:
            counts["other_plan_pending"] += 1
            continue
        try:
            strict(data, ("record_type", "query", "attempt_id", "outcome"), "query_work")
            query = read_query(data["query"], matrix)
            if row["identity"] != query_identity(query["work_id"]) or data["attempt_id"] is not None or data["outcome"] != "planned" or row["document"]["source_id"] != "query_planner":
                raise ValueError("query_work_identity_binding")
        except ValueError:
            store.put(row["identity"], "source", "query_planner", "deferred",
                      {**data, "outcome": "binding_revalidation_refused"}, expected=row)
            counts["binding_refusals"] += 1
            continue
        engine = query["engine"]
        if query["dispatch"] != "supported":
            continue
        source_hold_id = "community.query.source_hold." + digest(engine)
        source_hold = store.get(source_hold_id)
        if source_hold and (source_hold["document"]["data"].get("record_type") != "knowledge_radar_query_source_hold/v1" or source_hold["document"]["source_id"] != engine or type(source_hold["document"]["data"].get("held")) is not bool):
            raise ValueError("query_source_hold_binding")
        if engine in previous_sources or (source_hold and source_hold["document"]["data"]["held"]):
            source_holds.add(engine)
            continue
        dispatch_hold_id = "community.query.dispatch_hold." + query["query_id"]
        dispatch_hold = store.get(dispatch_hold_id)
        if dispatch_hold and (dispatch_hold["document"]["data"].get("record_type") != "knowledge_radar_query_dispatch_hold/v1" or dispatch_hold["document"]["data"].get("query_id") != query["query_id"] or type(dispatch_hold["document"]["data"].get("held")) is not bool):
            raise ValueError("query_dispatch_hold_binding")
        if query["query_id"] in previous_queries or (dispatch_hold and dispatch_hold["document"]["data"]["held"]):
            query_holds.add(query["query_id"])
            continue
        if counts["queries_executed"] == maximum_queries or network.budget.used >= network.budget.maximum_requests:
            break
        original = matrix.contracts[engine]
        active_contract = network.contracts.get(engine)
        if active_contract is None or not 0 < active_contract.maximum_requests_per_run <= min(per_source, original.maximum_requests_per_run) or replace(active_contract, maximum_requests_per_run=original.maximum_requests_per_run) != original:
            raise ValueError("query_network_source_contract_binding")
        if by_source.get(engine, 0) >= active_contract.maximum_requests_per_run:
            continue
        selected_engine = engines.engine(engine)
        if selected_engine.engine_id != engine or selected_engine.engine_version != original.parser_version:
            raise ValueError("query_engine_version_binding")
        # A UUID is an attempt, never a distinct query or capability.
        attempt_id = "community.query.attempt." + uuid4().hex
        reservation = {"record_type": ATTEMPT, "query_id": query["query_id"], "work_id": query["work_id"],
                       "started_at": now, "status": "intent_recorded_no_dispatch", "source_contract_digest": query["source_contract_digest"],
                       "request_log": str(network.log.path) if network.log.path else None,
                       "request_sequence_start": len(network.log.records) + 1}
        store.put(attempt_id, "run", engine, "recorded", reservation)
        dispatch_data = {"record_type": "knowledge_radar_query_dispatch_hold/v1", "query_id": query["query_id"],
                         "work_id": query["work_id"], "held": True, "attempt_id": attempt_id,
                         "status": "reserved_unknown_outcome"}
        store.put(dispatch_hold_id, "source", engine, "recorded", dispatch_data, expected=dispatch_hold)
        store.put(row["identity"], "source", "query_planner", "recorded",
                  {**data, "attempt_id": attempt_id, "outcome": "reserved_unknown_outcome"}, expected=row)
        reservation["status"] = "reserved_unknown_outcome"
        store.put(attempt_id, "run", engine, "recorded", reservation, expected=store.get(attempt_id))
        counts["queries_executed"] += 1
        by_source[engine] = by_source.get(engine, 0) + 1
        binding = SourceBinding(engine, query["route"], {"q": query["query"], **QUERY_PARAMETERS})
        question = replace(template, id="q_" + query["query_id"][:40], sources=(binding,), limit=QUERY_PARAMETERS["limit"])
        context = ReadContext(question, binding, now, now[:10], network.contracts[engine], Path(repository), None, network)

        def collect(active):
            return selected_engine.read(context)

        before = network.budget.used
        before_log = len(network.log.records)
        result = dict(reservation)
        observations = []
        try:
            answer = run_service_operation(store.runtime, ServiceLoopSpec("research_query_read", "practitioner.code_execution",
                QUERY, "knowledge_radar_source_answer/v1", ("reads_fs", "writes_fs", "network", "spawns_process"),
                "Read public repository metadata for one bounded research hypothesis.", "research_query_failed"), collect)
            if answer.status not in ("ok", "partial", "failed", "gone") or len(answer.observations) > 10:
                raise ValueError("query_answer_contract")
            if answer.status in ("failed", "gone") and answer.observations:
                raise ValueError("query_failed_answer_has_observations")
            observations = [read_observation(observation.to_dict()).to_dict() for observation in answer.observations]
            if any(observation["engine_id"] != engine or observation["engine_version"] != original.parser_version for observation in observations):
                raise ValueError("query_observation_engine_binding")
            result.update(status=answer.status, answer_requests=answer.requests,
                          observations=observations, excluded_count=len(answer.excluded), gates=dict(GATES))
            bounded_document(result)
        except Exception as error:  # Transport/engine failures remain failed, never empty successes.
            result.update(status="failed", error_class=type(error).__name__, observations=[])
            observations = []
        result["physical_requests_reserved"] = network.budget.used - before
        result["request_records"] = network.log.records[before_log:]
        result["request_outcome_unknown"] = result["physical_requests_reserved"] != len(result["request_records"])
        counts["unknown_request_outcomes"] += result["request_outcome_unknown"]
        # Save the complete attempt before origin folding; an interrupted fold cannot cause a reread.
        old_attempt = store.get(attempt_id)
        store.put(attempt_id, "run", engine, "failed" if result["status"] in ("failed", "gone") else "complete",
                  bounded_document(result), expected=old_attempt)
        if any(record["status"] in (401, 403, 404, 410, 429) for record in result["request_records"]):
            store.put(source_hold_id, "source", engine, "failed",
                      {"record_type": "knowledge_radar_query_source_hold/v1", "held": True,
                       "reason": "source_access_or_rate_limit_requires_reconciliation", "attempt_id": attempt_id,
                       "source_contract_digest": query["source_contract_digest"]}, expected=source_hold)
            source_holds.add(engine)
        for observation in observations:
            origin_id = "community.query.origin." + digest(observation["origin"])
            old_origin = store.get(origin_id)
            counts["duplicate_origins" if old_origin else "new_origins"] += 1
            if old_origin is None:
                store.put(origin_id, "source", engine, "needs_research",
                          {"record_type": "knowledge_radar_query_origin/v1", "observation": observation,
                           "first_attempt": attempt_id, "gates": dict(GATES)})
        final = store.get(row["identity"])
        failed = result["status"] in ("failed", "gone")
        store.put(row["identity"], "source", "query_planner", "failed" if failed else "complete",
                  {**data, "attempt_id": attempt_id, "outcome": result["status"]}, expected=final)
        store.put(dispatch_hold_id, "source", engine, "failed" if result["request_outcome_unknown"] else "complete",
                  {**dispatch_data, "held": result["request_outcome_unknown"],
                   "status": "reserved_unknown_outcome" if result["request_outcome_unknown"] else result["status"]},
                  expected=store.get(dispatch_hold_id))
        counts["failed_queries"] += failed
        counts["successful_queries"] += result["status"] == "ok"
        counts["partial_queries"] += result["status"] == "partial"
        counts["empty_queries"] += result["status"] == "ok" and not observations
        counts["observations"] += len(observations)
        attempts.append({"attempt_id": attempt_id, "query_id": query["query_id"], "engine": engine,
                         "status": result["status"], "observations": len(observations)})
    counts["physical_requests_reserved"] = network.budget.used - request_start
    counts["request_records"] = len(network.log.records) - log_start
    return {"counts": counts, "attempts": attempts, "by_source": by_source,
            "held_sources": sorted(source_holds),
            "held_queries": sorted(query_holds), "hold_lookup_limit_per_state": 1000,
            "hold_lookup_may_be_incomplete": holds_incomplete,
            "queued_lookup_limit": 1000, "queued_lookup_may_be_incomplete": len(queued) == 1000,
            "automatic_retries": False}


def tick(matrix, repository, state, *, writes_allowed=False, network_allowed=False, execute=False,
         page_size=10, scan_limit=1000, maximum_queries=5, maximum_requests=5, per_source=5, network=None, now=None):
    integer(page_size, 1, 20, "page_limit")
    integer(scan_limit, 1, 10000, "scan_limit")
    integer(maximum_queries, 1, 100, "maximum_queries")
    integer(maximum_requests, 1, 100, "maximum_requests")
    integer(per_source, 1, 100, "per_source")
    if execute and (not writes_allowed or not network_allowed):
        raise PermissionError("query_execution_requires_write_and_network_grants")
    store = CommunityStore(Path(state), writes_allowed=writes_allowed)
    if not writes_allowed:
        held = store.get("community.query.progress." + matrix.plan_digest)
        planned = page(matrix, held["document"]["data"]["cursor"] if held else None,
                       limit=page_size, scan_limit=scan_limit,
                       seen=lambda work_id: store.get(query_identity(work_id)) is not None)
        return {"record_type": RESULT, "preview": True, "page": planned, "execution": None}
    store.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Reuse the watcher lock so local planning and source ticks cannot race state.
    descriptor = os.open(store.root / "scan.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reconciled = reconcile_interrupted(store, now=now)
        planned, totals = plan_into_store(store, matrix, limit=page_size, scan_limit=scan_limit)
        execution = None
        if execute:
            contracts = {name: replace(contract, maximum_requests_per_run=min(per_source, contract.maximum_requests_per_run))
                         for name, contract in matrix.contracts.items()}
            if network is None:
                run_folder = store.root / "runs" / ("query-" + uuid4().hex)
                run_folder.mkdir(parents=True, mode=0o700)
                network = RadarNetwork(RequestBudget(maximum_requests, maximum_pause_seconds=0, reserve=0),
                                       RequestLog(run_folder / "requests.jsonl"), contracts)
            if network.budget.maximum_requests > maximum_requests or network.budget.used:
                raise ValueError("query_network_budget_binding")
            execution = execute_queued(store, matrix, repository, network, maximum_queries=maximum_queries, per_source=per_source, now=now)
        return {"record_type": RESULT, "preview": False, "page": planned, "reconciled": reconciled,
                "plan_totals": totals, "execution": execution, "loop_events": len(store.ledger.events)}
