"""One run of the multiplier: every executor in its own lane, each within its source's limits, until a deadline.

```text
run (a Starting Practitioner task, code execution profile, deterministic: no model call)
└── one lane per available executor that a product names
    ├── wait     the executor's interval, its daily ceiling, its hold, the provider's reported allowance;
    │            GitHub lanes also wait while the shared core allowance is under 1,500 or a search bucket is low
    ├── choose   a follow-up page of a productive query, else a query due for refresh, else the next query of the
    │            lane's products in smooth weighted round-robin (imported plans are one more product)
    ├── send     intent recorded first; the transport refuses undeclared and forbidden hosts before sending
    ├── store    the raw response, before anything counts
    ├── execute  only a stored, parsed 200 answer
    └── fold     candidates, origins and routes from the stored response
```

A lane is a loop inside this one run, not a Loop vertex, a scheduler or a runtime: the run is the Practitioner
task and the lanes are its bounded parallel reads. The run grants nothing and publishes nothing; it writes only
the private ledger and evidence folder it was given.
"""
from __future__ import annotations

import json
import random
import shutil
import signal
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .evidence import Ledger, stamp
from .executors import EMPTY, OK, PARTIAL
from .planner import PlannedQuery, query_at, query_identity
from .routing import licence_lead, route
from .transport import RequestRefused, github_allowance
from .client_profiles import request_profile_matches

GITHUB_CORE_FLOOR = 1500
SEARCH_RESERVE = {"github_repositories": ("search", 6), "github_code": ("code_search", 4)}
FOLLOW_UNIQUE_SHARE = 0.5
#: Every tenth pick of a lane looks for an executed query whose refresh period has passed.
REFRESH_EVERY = 10
#: A pass stops before the disk holding its evidence falls under this much free space: a response that cannot be
#: stored executes nothing, and this machine has filled its disk before (September 27, 2026).
MINIMUM_FREE_BYTES = 40 * 1024 ** 3


class ProductStream:
    """One product's cursor: the next k, what was examined, skipped and emitted. Persisted after each attempt."""

    def __init__(self, product, library, executor, ledger: Ledger):
        self.product, self.library, self.executor, self.ledger = product, library, executor, ledger
        self.cursor = ledger.cursor(product.id, product.digest)
        self.exhausted = False
        self.current = 0  # smooth weighted round-robin credit
        self.weight = product.weight  # the declared prior; learned_weights may scale it by measured yield

    def next(self, *, scan_limit: int = 4000):
        for _ in range(scan_limit):
            k = self.cursor["next_k"]
            if k >= self.product.total:
                self.exhausted = True
                return None
            self.cursor["next_k"] = k + 1
            self.cursor["examined"] += 1
            query, reason = query_at(self.product, k, self.library, self.executor)
            if query is None:
                excluded = self.cursor["excluded"]
                excluded[reason] = excluded.get(reason, 0) + 1
                continue
            within = self.ledger.within_refresh(query.query_id)
            if within is True:
                self.cursor["duplicates"] += 1
                continue
            if within is False:
                self.cursor["refreshes"] = self.cursor.get("refreshes", 0) + 1
            self.cursor["emitted"] += 1
            return query
        return None

    def save(self):
        self.ledger.save_cursor(self.cursor)


class ImportedStream:
    """Imported plans (earlier research queues) rotated over their keys, executed by a web search engine."""

    def __init__(self, executor, ledger: Ledger, weight: int):
        self.executor, self.ledger, self.weight = executor, ledger, weight
        self.product = type("ImportedProduct", (), {"id": "imported_plans", "weight": weight, "refresh_days": executor.refresh_days,
                                                     "follow_pages": 0})()
        self.exhausted = False
        self.current = 0
        self.weight = weight
        self.pending = None

    def next(self, *, scan_limit: int = 50):
        rows = self.ledger.rows("select text_key, query_text from imported where state='planned' "
                                "order by rotation_rank, rotation_key limit ?", (scan_limit,))
        for text_key, text in rows:
            request = self.executor.text_request(text)
            query = PlannedQuery("imported_plans", self.executor.executor_id, 0, {}, request,
                                 query_identity(self.executor.executor_id, request), origin="imported")
            already = self.ledger.within_refresh(query.query_id) is True
            with self.ledger.lock:
                self.ledger.db.execute("update imported set state=?, query_id=? where text_key=?",
                                       ("executed" if already else "dispatched", query.query_id, text_key))
                self.ledger.db.commit()
            if not already:
                return query
        self.exhausted = not rows
        return None

    def save(self):
        return None


class Lane:
    def __init__(self, run, executor, streams):
        self.run, self.executor, self.streams = run, executor, streams
        self.follow = []  # (query, parent new-unique share)
        self.stats = Counter()
        self.statuses = Counter()
        self.refusals = Counter()
        self.errors = []
        self.picks = 0
        self.refreshed = set()
        self.last_sent = 0.0
        self.next_allowed = 0.0
        self.done_reason = ""

    # -------------------------------------------------------------- choosing
    def choose(self):
        if self.follow:
            return self.follow.pop(0)
        self.picks += 1
        if self.picks % REFRESH_EVERY == 0:
            refreshed = self.due_refresh()
            if refreshed is not None:
                return refreshed
        live = [stream for stream in self.streams if not stream.exhausted]
        if not live:
            return None, None
        total = sum(stream.weight for stream in live)
        for stream in live:
            stream.current += stream.weight
        best = max(live, key=lambda stream: stream.current)
        best.current -= total
        query = best.next()
        if query is None and not best.exhausted:
            # This product's scan window was spent on skipped combinations; try the others before giving up.
            for stream in sorted(live, key=lambda stream: -stream.current):
                if stream is best:
                    continue
                query = stream.next()
                if query is not None:
                    return query, stream
            return None, best
        return query, best

    # -------------------------------------------------------------- waiting
    def wait_reason(self):
        run, executor = self.run, self.executor
        if shutil.disk_usage(run.ledger.root).free < run.minimum_free_bytes:
            return "disk_space_low"
        if executor.daily_ceiling is not None:
            requests, cost = run.ledger.usage(executor.executor_id)
            spent = cost if executor.cost_unit != "request" else requests
            if spent >= executor.daily_ceiling:
                return "daily_ceiling_reached"
        hold = run.ledger.hold(executor.executor_id)
        if hold:
            return "held:" + hold[0]
        if executor.access == "gh_api":
            gate = run.github_gate()
            core = gate.get("core", {}).get("remaining")
            if core is not None and core < GITHUB_CORE_FLOOR:
                return "github_core_below_floor"
            bucket, reserve = SEARCH_RESERVE[executor.executor_id]
            remaining = gate.get(bucket, {}).get("remaining")
            if remaining is not None and remaining < reserve:
                return "github_" + bucket + "_low"
        return ""

    def loop(self):
        run = self.run
        while not run.stop.is_set():
            if time.time() >= run.deadline:
                self.done_reason = "deadline"
                return
            reason = self.wait_reason()
            if reason:
                self.stats["waits:" + reason] += 1
                if reason in ("daily_ceiling_reached", "disk_space_low"):
                    self.done_reason = reason
                    return
                run.stop.wait(20 if reason.startswith("github") else 60)
                if reason.startswith("github"):
                    run.refresh_github_gate(force=True)
                continue
            pause = self.next_allowed - time.time()
            if pause > 0:
                run.stop.wait(min(pause, 30))
                continue
            query, stream = self.choose()
            if query is None:
                if all(getattr(item, "exhausted", False) for item in self.streams) and not self.follow:
                    self.done_reason = "plan_exhausted"
                    return
                run.stop.wait(1)
                continue
            try:
                self.attempt(query, stream)
                if self.done_reason.startswith("refused:"):
                    return
            except Exception as error:  # one bad response never ends the lane; too many do
                self.stats["attempt_errors"] += 1
                self.errors.append(type(error).__name__ + ": " + str(error)[:200])
                if stream is not None:
                    stream.save()
                if self.stats["attempt_errors"] >= 25:
                    self.done_reason = "too_many_attempt_errors"
                    return

    # -------------------------------------------------------------- one attempt
    def attempt(self, query, stream):
        run, executor, ledger = self.run, self.executor, self.run.ledger
        try:
            run.transport.check(executor, query.request)
        except RequestRefused as refusal:
            # Every refusal the transport makes before sending is about the lane (an unavailable engine, a
            # missing key, a refused host), not this query: the lane stops and its cursor stays where it was,
            # so no query is spent unsent.
            self.refusals[refusal.code] += 1
            self.done_reason = "refused:" + refusal.code
            return
        ledger.plan(query)
        attempt_id = ledger.intent(query, run.run_id, executor.cost(query.request))
        started = time.time()
        self.next_allowed = started + executor.minimum_interval * (1 + random.random() * 0.1)
        self.stats["sent"] += 1
        try:
            answer = run.transport.send(executor, query.request)
        except RequestRefused as refusal:  # a refusal found only at send time: nothing left the process
            ledger.store_failed(attempt_id, "refused:" + refusal.code)
            self.refusals[refusal.code] += 1
            if stream is not None:
                stream.save()
            return
        if answer.status is None:
            ledger.store_failed(attempt_id, answer.error_class or "no_response")
            self.stats["no_response"] += 1
            self.statuses["none"] += 1
            if stream is not None:
                stream.save()
            self.next_allowed = time.time() + max(30, executor.minimum_interval)
            return
        try:
            ledger.store(attempt_id, query, query.request, answer)
        except OSError as error:
            ledger.store_failed(attempt_id, "storage_failed:" + type(error).__name__)
            self.stats["storage_failed"] += 1
            run.stop.set()  # a disk that cannot store evidence ends the run: nothing may count unstored
            return
        self.stats["stored"] += 1
        self.statuses[str(answer.status)] += 1
        parsed = executor.parse(answer.status, answer.body)
        if answer.truncated and parsed.status == OK:
            parsed.status = PARTIAL
        self.observe_allowance(answer, attempt_id)
        if answer.status == 200 and parsed.status in (OK, EMPTY, PARTIAL):
            ledger.mark_executed(attempt_id, query, parse_status=parsed.status, total_count=parsed.total_count,
                                 refresh_days=stream.product.refresh_days if stream is not None else executor.refresh_days)
            self.stats["executed"] += 1
            self.stats["executed_" + parsed.status] += 1
            items, routes = [], {}
            for item in parsed.items:
                lead, allowed, basis = licence_lead(item.get("licence_reported"))
                item = {**item, "licence_lead": lead, "allowlisted": allowed, "licence_basis": basis}
                routes.setdefault(item["key"], route(item))
                items.append(item)
            # One response can list the same item twice (a file under two paths keeps two keys; a repeated row one).
            unique = {item["key"]: item for item in items}
            folded = ledger.fold(attempt_id, query, list(unique.values()), routes)
            self.stats["items"] += folded["items"]
            self.stats["new_unique"] += folded["new_unique"]
            run.yields[executor.executor_id].append((self.stats["executed"], folded["new_unique"], folded["items"]))
            self.maybe_follow(query, stream, parsed, folded)
            if query.origin == "imported":
                ledger.imported_outcome(query.query_id, "executed")
        else:
            ledger.mark_failed(attempt_id, query, parsed.status if answer.status == 200 else "http_" + str(answer.status))
            ledger.close_attempt(attempt_id)
            self.stats["failed"] += 1
            if query.origin == "imported":
                ledger.imported_outcome(query.query_id, "failed")
        if stream is not None:
            stream.save()

    def observe_allowance(self, answer, attempt_id):
        run, executor, headers = self.run, self.executor, answer.headers
        status = answer.status
        reset = None
        if headers.get("x-ratelimit-reset", "").isdigit():
            reset = datetime.fromtimestamp(int(headers["x-ratelimit-reset"]), timezone.utc)
        remaining = headers.get("x-ratelimit-remaining")
        if executor.access == "gh_api" and remaining is not None and remaining.isdigit():
            run.note_github(executor.executor_id, int(remaining), reset)
        if status == 429 or (status == 403 and remaining == "0"):
            retry = headers.get("retry-after")
            until = reset if reset and reset > datetime.now(timezone.utc) else (
                datetime.now(timezone.utc) + timedelta(seconds=int(retry) if retry and retry.isdigit() else 300))
            run.ledger.set_hold(executor.executor_id, "rate_limited_" + str(status), until + timedelta(seconds=5), attempt_id)
            self.stats["rate_limited"] += 1
        elif status in (401, 403) and executor.access == "gh_api":
            # GitHub's secondary rate limit answers 403 with a retry-after and allowance left; anything else
            # may be an access change. Either way the lane waits instead of repeating the request pattern.
            retry = headers.get("retry-after")
            seconds = int(retry) + 5 if retry and retry.isdigit() else 600
            run.ledger.set_hold(executor.executor_id, "github_refused_" + str(status),
                                datetime.now(timezone.utc) + timedelta(seconds=seconds), attempt_id)
        elif status in (401, 403):
            run.ledger.set_hold(executor.executor_id, "access_refused_" + str(status),
                                datetime.now(timezone.utc) + timedelta(hours=6), attempt_id)
        sustained = headers.get("x-ratelimit-available-anon_sustained")
        if sustained and sustained.isdigit() and int(sustained) < 40:
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
            run.ledger.set_hold(executor.executor_id, "anonymous_daily_allowance_low", tomorrow, attempt_id)
        if executor.executor_id == "openalex_works" and remaining and remaining.isdigit() and int(remaining) < 150:
            seconds = headers.get("x-ratelimit-reset")
            until = datetime.now(timezone.utc) + timedelta(seconds=int(seconds) if seconds and seconds.isdigit() else 3600)
            run.ledger.set_hold(executor.executor_id, "openalex_credits_reserved_for_others", until, attempt_id)
        if headers.get("ratelimit") and executor.host == "huggingface.co":
            parts = dict(part.split("=", 1) for part in headers["ratelimit"].split(";")[1:] if "=" in part)
            if parts.get("r", "").isdigit() and int(parts["r"]) < 100 and parts.get("t", "").isdigit():
                run.ledger.set_hold(executor.executor_id, "huggingface_window_low",
                                    datetime.now(timezone.utc) + timedelta(seconds=int(parts["t"]) + 5), attempt_id)

    def maybe_follow(self, query, stream, parsed, folded):
        if stream is None or query.origin == "refresh" or query.page > stream.product.follow_pages or not parsed.items:
            return
        if len(parsed.items) < self.executor.per_page or not parsed.total_count:
            return
        if parsed.total_count <= query.page * self.executor.per_page:
            return
        if folded["new_unique"] < FOLLOW_UNIQUE_SHARE * folded["items"]:
            return
        request = self.executor.render(query.assignment, dict(stream.product.params), page=query.page + 1)
        if isinstance(request, str):
            return
        follow = PlannedQuery(query.product_id, query.executor_id, query.k, query.assignment, request,
                              query_identity(query.executor_id, request), query.page + 1, query.query_id, "follow_page")
        if self.run.ledger.within_refresh(follow.query_id) is not True:
            self.follow.append((follow, stream))
            self.stats["follow_pages_planned"] += 1

    def due_refresh(self):
        """One executed query whose refresh period has passed, most productive first: the same request again, so
        a source's new items surface; a query inside its period is never repeated."""
        ledger = self.run.ledger
        for query_id, product_id, k, page, request, _ in ledger.due_queries(self.executor.executor_id, limit=5):
            if query_id in self.refreshed:
                continue
            # A changed header profile never refreshes a saved request under
            # the previous profile's identity. The current product plans its
            # own profile-bound query; both still share this executor's quota.
            if not request_profile_matches(self.executor, json.loads(request)):
                self.stats["refreshes_other_profile_skipped"] += 1
                continue
            self.refreshed.add(query_id)
            stream = next((item for item in self.streams if getattr(item.product, "id", None) == product_id), None)
            if stream is None:
                continue
            self.stats["refreshes_planned"] += 1
            return PlannedQuery(product_id, self.executor.executor_id, k, {}, json.loads(request), query_id, page,
                                origin="refresh"), stream
        return None


class LicenceLane:
    """GitHub code search reports no licence, and a web result names a repository without one. This lane asks
    GitHub's GraphQL interface what licence it detects for up to fifty such repositories at a time, stores each
    answer as evidence like any probe, and records it on every candidate of that repository. A detected licence is
    still a lead: the supply lines decide the licence again from the licence text at the pinned commit."""

    executor_id = "github_licences"
    interval = 12.0
    graphql_floor = 1000

    def __init__(self, run):
        self.run = run
        self.stats = Counter()
        self.statuses = Counter()
        self.refusals = Counter()
        self.errors = []
        self.follow = []
        self.done_reason = ""
        self.executor = type("LicenceExecutor", (), {"executor_id": self.executor_id})()

    def pending(self, limit=50) -> list:
        ledger = self.run.ledger
        rows = ledger.rows("select key from candidates where licence_reported is null and "
                           "(key like 'github-file:%' or key like 'github:%') order by first_seen_at limit 4000")
        repos, seen = [], set()
        for (key,) in rows:
            body = key.split(":", 1)[1]
            repo = "/".join(body.split("/")[:2])
            if repo in seen:
                continue
            seen.add(repo)
            if ledger.scalar("select 1 from repo_licences where repo=?", (repo,)):
                continue
            repos.append(repo)
            if len(repos) == limit:
                break
        return repos

    def loop(self):
        run = self.run
        while not run.stop.is_set() and time.time() < run.deadline:
            graphql = run.github_gate().get("graphql", {}).get("remaining")
            core = run.github_gate().get("core", {}).get("remaining")
            if (graphql is not None and graphql < self.graphql_floor) or (core is not None and core < GITHUB_CORE_FLOOR):
                self.stats["waits:github_allowance_low"] += 1
                run.stop.wait(60)
                continue
            repos = self.pending()
            if not repos:
                run.stop.wait(15)
                continue
            try:
                self.resolve(repos)
            except Exception as error:
                self.stats["attempt_errors"] += 1
                self.errors.append(type(error).__name__ + ": " + str(error)[:200])
                if self.stats["attempt_errors"] >= 25:
                    self.done_reason = "too_many_attempt_errors"
                    return
            run.stop.wait(self.interval)
        self.done_reason = self.done_reason or "deadline"

    def resolve(self, repos):
        run, ledger = self.run, self.run.ledger
        request = {"method": "POST", "host": "api.github.com", "path": "/graphql", "params": [],
                   "body": {"licences_of": sorted(repos)}, "page": 1}
        query = PlannedQuery("github_licences", self.executor_id, 0, {}, request, query_identity(self.executor_id, request),
                             origin="licence_resolution")
        ledger.plan(query)
        attempt_id = ledger.intent(query, run.run_id, 1)
        self.stats["sent"] += 1
        answer = run.transport.graphql_licences(repos)
        if answer.status is None:
            ledger.store_failed(attempt_id, answer.error_class or "no_response")
            return
        ledger.store(attempt_id, query, request, answer)
        self.statuses[str(answer.status)] += 1
        try:
            document = json.loads(answer.body)
        except ValueError:
            document = None
        data = document.get("data") if isinstance(document, dict) else None
        if answer.status != 200 or not isinstance(data, dict):
            ledger.mark_failed(attempt_id, query, "http_" + str(answer.status))
            ledger.close_attempt(attempt_id)
            return
        ledger.mark_executed(attempt_id, query, parse_status="ok", total_count=len(repos), refresh_days=90)
        found = 0
        with ledger.lock:
            for index, repo in enumerate(repos):
                row = data.get(f"r{index}")
                if not isinstance(row, dict) or row.get("isPrivate") is not False:
                    ledger.db.execute("insert or replace into repo_licences values(?,?,?,?,?,?,?)",
                                      (repo, None, None, None, 0, stamp(), attempt_id))
                    continue
                found += 1
                spdx = (row.get("licenseInfo") or {}).get("spdxId") if isinstance(row.get("licenseInfo"), dict) else None
                ledger.db.execute("insert or replace into repo_licences values(?,?,?,?,?,?,?)",
                                  (repo, spdx, 0, int(bool(row.get("isArchived"))), 1, stamp(), attempt_id))
                lead, allowed, basis = licence_lead(spdx)
                ledger.db.execute("update candidates set licence_reported=?, licence_field=?, licence_lead=?, allowlisted=?, "
                                  "licence_basis=? where licence_reported is null and (key=? or key like ?)",
                                  (spdx, "github licenseInfo.spdxId (graphql)", lead, int(allowed), basis,
                                   "github:" + repo.lower(), "github-file:" + repo.lower() + "/%"))
            ledger.db.execute("update attempts set state='folded', items=?, new_unique=0 where attempt_id=?", (found, attempt_id))
            ledger.db.commit()
        self.stats["executed"] += 1
        self.stats["repositories_resolved"] += found


LEARN_MINIMUM_EXECUTIONS = 20
LEARN_FACTOR_BOUNDS = (0.25, 4.0)


def learned_weights(ledger: Ledger, streams) -> dict:
    """Scale each product's declared weight by its measured yield, with a floor of one.

    A product's factor is its mean new distinct candidates per executed query over the lane's mean, from every
    earlier pass in the ledger, bounded to [0.25, 4]. A product with fewer than twenty executions keeps its prior,
    so a new product is explored before it is judged; no product falls below one share, so none leaves the
    rotation (low yield lowers priority; nothing is deleted).
    """
    measured = {}
    for stream in streams:
        product_id = getattr(stream.product, "id", None)
        row = ledger.rows("select count(*), avg(new_unique) from queries where product_id=? and state='executed' "
                          "and origin='product'", (product_id,))
        count, mean = row[0] if row else (0, None)
        measured[product_id] = (count or 0, mean or 0.0)
    known = [mean for count, mean in measured.values() if count >= LEARN_MINIMUM_EXECUTIONS]
    lane_mean = sum(known) / len(known) if known else 0.0
    out = {}
    for stream in streams:
        product_id = getattr(stream.product, "id", None)
        count, mean = measured[product_id]
        prior = stream.weight
        if count >= LEARN_MINIMUM_EXECUTIONS and lane_mean > 0:
            factor = min(max(mean / lane_mean, LEARN_FACTOR_BOUNDS[0]), LEARN_FACTOR_BOUNDS[1])
            stream.weight = max(1, round(prior * factor))
        out[product_id] = {"prior": prior, "weight": stream.weight, "executions": count, "mean_new_unique": round(mean, 2)}
    return out


class Run:
    def __init__(self, *, library, products, executors, transport, ledger: Ledger, minutes: float,
                 only=None, imported_weight: int = 0, run_id: "str | None" = None, resolve_licences: bool = True,
                 learn: bool = True, minimum_free_bytes: int = MINIMUM_FREE_BYTES):
        self.library, self.executors, self.transport, self.ledger = library, executors, transport, ledger
        self.minimum_free_bytes = minimum_free_bytes
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:6]
        self.started = stamp()
        self.deadline = time.time() + minutes * 60
        self.stop = threading.Event()
        self.yields = defaultdict(list)
        self.gate_lock = threading.Lock()
        self.gate = {}
        self.gate_read = 0.0
        by_executor = defaultdict(list)
        for product in products:
            if only and product.executor_id not in only:
                continue
            executor = executors[product.executor_id]
            if executor.available:
                by_executor[product.executor_id].append(ProductStream(product, library, executor, ledger))
        if imported_weight and "ollama_web_search" in by_executor:
            by_executor["ollama_web_search"].append(ImportedStream(executors["ollama_web_search"], ledger, imported_weight))
        self.learned = {name: learned_weights(ledger, streams) for name, streams in by_executor.items()} if learn else {}
        self.lanes = [Lane(self, executors[name], streams) for name, streams in sorted(by_executor.items())]
        if resolve_licences and any(name.startswith("github") or name == "ollama_web_search" for name in by_executor):
            self.lanes.append(LicenceLane(self))

    def github_gate(self) -> dict:
        self.refresh_github_gate()
        return self.gate

    def refresh_github_gate(self, force=False):
        with self.gate_lock:
            if force or time.time() - self.gate_read > 30:
                fresh = github_allowance()
                if fresh:
                    self.gate = fresh
                self.gate_read = time.time()

    def note_github(self, executor_id, remaining, reset):
        bucket = SEARCH_RESERVE[executor_id][0]
        with self.gate_lock:
            entry = dict(self.gate.get(bucket, {}))
            entry["remaining"] = remaining
            if reset is not None:
                entry["reset"] = int(reset.timestamp())
            self.gate[bucket] = entry

    def reconcile(self) -> dict:
        """Before sending anything: adopt responses a crash stored, fold stored responses, abandon empty intents."""
        self.ledger.require_current_unfinished_contract()
        unfinished = self.ledger.unfinished()
        adopted = abandoned = folded = 0
        for attempt_id, query_id, executor_id, _ in unfinished["intents"]:
            path = self.ledger.find_evidence(executor_id, attempt_id)
            if path is not None:
                self.ledger.adopt(attempt_id, path)
                adopted += 1
                unfinished["stored"].append((attempt_id, query_id, executor_id, str(path.relative_to(self.ledger.root))))
            else:
                self.ledger.abandon(attempt_id)
                abandoned += 1
        for attempt_id, query_id, executor_id, evidence_path in unfinished["stored"]:
            if self.fold_stored(attempt_id, query_id, executor_id, self.ledger.root / evidence_path):
                folded += 1
        released = self.ledger.release_dispatched_imports()
        return {"adopted_after_crash": adopted, "abandoned_intents": abandoned, "folded_from_stored": folded,
                "imported_plans_released": released}

    def fold_stored(self, attempt_id, query_id, executor_id, path) -> bool:
        executor = self.executors.get(executor_id)
        row = self.ledger.rows("select product_id, k, page, parent_query_id, origin, request from queries where query_id=?", (query_id,))
        if executor is None or not row:
            return False
        product_id, k, page, parent, origin, request = row[0]
        envelope = self.ledger.read_evidence(path)
        query = PlannedQuery(product_id, executor_id, k, {}, json.loads(request), query_id, page, parent or "", origin)
        parsed = executor.parse(envelope["status"], envelope["body"])
        if envelope["status"] == 200 and parsed.status in (OK, EMPTY, PARTIAL):
            self.ledger.mark_executed(attempt_id, query, parse_status=parsed.status, total_count=parsed.total_count,
                                      refresh_days=executor.refresh_days)
            items, routes = [], {}
            for item in parsed.items:
                lead, allowed, basis = licence_lead(item.get("licence_reported"))
                item = {**item, "licence_lead": lead, "allowlisted": allowed, "licence_basis": basis}
                routes.setdefault(item["key"], route(item))
                items.append(item)
            self.ledger.fold(attempt_id, query, list({item["key"]: item for item in items}.values()), routes)
        else:
            self.ledger.mark_failed(attempt_id, query, "http_" + str(envelope["status"]))
            self.ledger.close_attempt(attempt_id)
        return True

    def status(self, state: str) -> dict:
        lanes = {}
        for lane in self.lanes:
            lanes[lane.executor.executor_id] = {"stats": dict(lane.stats), "statuses": dict(lane.statuses),
                                                "refusals": dict(lane.refusals), "follow_queue": len(lane.follow),
                                                "done": lane.done_reason, "errors": lane.errors[-5:]}
        return {"record_type": "research_query_run_status/v1", "run_id": self.run_id, "state": state,
                "started_at": self.started, "updated_at": stamp(), "deadline": stamp(datetime.fromtimestamp(self.deadline, timezone.utc)),
                "lanes": lanes, "learned_weights": self.learned}

    def execute(self) -> dict:
        reconciliation = self.reconcile()
        self.ledger.record_run(self.run_id, self.started, "running", {"reconciliation": reconciliation})
        threads = [threading.Thread(target=self._lane, args=(lane,), name=lane.executor.executor_id, daemon=True)
                   for lane in self.lanes]
        previous = {}
        for signum in (signal.SIGTERM, signal.SIGINT):
            try:
                previous[signum] = signal.signal(signum, lambda *_: self.stop.set())
            except ValueError:  # not the main thread (tests)
                pass
        for thread in threads:
            thread.start()
        stop_file = self.ledger.root / "state" / "stop"
        while any(thread.is_alive() for thread in threads):
            self.ledger.write_status(self.status("running"))
            if stop_file.exists():
                self.stop.set()
            self.stop.wait(15)
            if time.time() >= self.deadline + 120:
                self.stop.set()
        for thread in threads:
            thread.join(timeout=120)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        final = self.status("stopped" if self.stop.is_set() else "complete")
        final["reconciliation"] = reconciliation
        self.ledger.write_status(final)
        self.ledger.record_run(self.run_id, self.started, final["state"], final, stamp())
        return final

    def _lane(self, lane):
        try:
            lane.loop()
        except Exception as error:  # a lane failure is recorded; the other lanes go on
            lane.done_reason = "lane_error:" + type(error).__name__ + ":" + str(error)[:200]
