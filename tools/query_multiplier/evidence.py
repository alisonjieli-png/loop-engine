"""Raw responses as evidence, and the run ledger: a query counts as executed only once its response is stored.

```text
<root>/                                   private, mode 0700, outside the repository
├── state/ledger.sqlite                   cursors, queries, attempts, candidates, origins, daily usage, holds,
│                                         imported plans; WAL, one writer lock per process
├── state/status.json                     the last run's state for a timer or an operator
└── <YYYY-MM-DD>/                         one folder per UTC day
    ├── raw/<executor>/<qq>/<attempt>.json.gz   one response: request (no credential), status, kept headers,
    │                                           the body (bounded; text as text, other bytes as base64) and
    │                                           its SHA-256; gzip
    ├── routed/<line or pool>.jsonl       one row per new candidate proposed to a line or pool
    └── run-<id>.json                     the run's report
```

An attempt moves intent -> stored -> folded. The intent row exists before the request leaves, so a crash leaves
a trace. The response file is written to a temporary name, flushed and renamed before the ledger says "stored";
only then does the query count as executed, and only a 200 answer the executor could parse makes it executed
(a 403, a 429 or a timeout is stored as evidence of a failed attempt and the query stays unexecuted). Folding
(candidates, origins, routes) reads the stored file, never the network, so a crash between storing and folding
is repaired by folding again from the file; a crash between the intent and the store is found at the next start
and marked abandoned, with any response file that did reach the disk adopted rather than lost. Why a ledger and
not managed records: one managed record write measured 37.7 ms against 0.08 ms for this ledger on October 5, and
one run writes tens of thousands of rows.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from .client_profiles import validate_observation

EVIDENCE = "research_query_evidence/v2"
REPOSITORY = Path(__file__).resolve().parents[2]
SCHEMA = """
create table if not exists meta(key text primary key, value text);
create table if not exists cursors(product_id text primary key, product_digest text, next_k integer, examined integer,
  emitted integer, excluded text, duplicates integer, refreshes integer, updated_at text);
create table if not exists queries(query_id text primary key, executor_id text, product_id text, k integer, page integer,
  parent_query_id text, origin text, assignment text, request text, planned_at text, state text,
  executions integer default 0, last_attempt_id text, last_executed_at text, next_due_at text, last_status text,
  results integer default 0, new_unique integer default 0, total_count integer, sequence integer,
  cache_evidence_contract text, cache_evidence_executions integer);
create index if not exists queries_state on queries(state, next_due_at);
create index if not exists queries_executor on queries(executor_id, sequence);
create table if not exists attempts(attempt_id text primary key, query_id text, executor_id text, run_id text,
  started_at text, finished_at text, state text, http_status integer, evidence_path text, evidence_sha256 text,
  body_sha256 text, body_bytes integer, stored_bytes integer, truncated integer, error_class text, cost integer,
  items integer, new_unique integer, parse_status text, headers text, evidence_contract text);
create index if not exists attempts_state on attempts(state);
create table if not exists candidates(key text primary key, url text, kind text, title text, licence_reported text,
  licence_field text, licence_lead text, allowlisted integer, licence_basis text, route text, first_query_id text,
  first_executor text, first_seen_at text, first_day text, origins integer default 1, payload text);
create index if not exists candidates_route on candidates(route);
create table if not exists origins(key text, query_id text, attempt_id text, executor_id text, seen_at text,
  primary key(key, query_id));
create table if not exists daily_usage(executor_id text, day text, requests integer, cost integer,
  primary key(executor_id, day));
create table if not exists holds(executor_id text primary key, reason text, until text, attempt_id text, created_at text);
create table if not exists imported(text_key text primary key, query_text text, first_origin text, origins integer,
  sdg text, country text, rotation_key text, rotation_rank integer, state text, query_id text);
create index if not exists imported_rotation on imported(state, rotation_rank, rotation_key);
create table if not exists imported_origins(text_key text, origin text, external_id text, state text,
  primary key(text_key, origin, external_id));
create table if not exists runs(run_id text primary key, started_at text, finished_at text, status text, summary text);
create table if not exists repo_licences(repo text primary key, spdx text, private integer, archived integer, found integer,
  resolved_at text, attempt_id text);
"""


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(moment: "datetime | None" = None) -> str:
    return (moment or now()).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_stamp(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


class Ledger:
    """The run ledger and evidence store under one private root."""

    def __init__(self, root: Path, *, clock=now):
        root = Path(root).expanduser().absolute()
        if root == Path(root.anchor) or root == Path.home() or root.is_relative_to(REPOSITORY):
            raise ValueError("ledger_root_must_be_private_and_outside_the_repository")
        if any(part == ".." for part in root.parts):
            raise ValueError("ledger_root_parent_step")
        (root / "state").mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        self.root = root
        self.clock = clock
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(root / "state" / "ledger.sqlite"), check_same_thread=False, timeout=60)
        self.db.execute("pragma journal_mode=wal")
        self.db.execute("pragma synchronous=normal")
        self.db.executescript(SCHEMA)
        # This is a cache eligibility projection, not a legacy evidence reader.
        # Existing rows stay NULL and cannot satisfy the current contract.
        for table, columns in (("queries", (("cache_evidence_contract", "text"),
                                           ("cache_evidence_executions", "integer"))),
                               ("attempts", (("evidence_contract", "text"),))):
            present = {row[1] for row in self.db.execute(f"pragma table_info({table})")}
            for name, kind in columns:
                if name not in present:
                    self.db.execute(f"alter table {table} add column {name} {kind}")
        self.db.commit()

    # ------------------------------------------------------------------ helpers
    def day(self) -> str:
        return self.clock().strftime("%Y-%m-%d")

    def day_folder(self, day: "str | None" = None) -> Path:
        folder = self.root / (day or self.day())
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        return folder

    def close(self):
        with self.lock:
            self.db.close()

    def scalar(self, sql, args=()):
        with self.lock:
            row = self.db.execute(sql, args).fetchone()
        return row[0] if row else None

    def rows(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    # ------------------------------------------------------------------ cursors
    def cursor(self, product_id: str, product_digest: str) -> dict:
        with self.lock:
            row = self.db.execute("select product_digest, next_k, examined, emitted, excluded, duplicates, refreshes "
                                  "from cursors where product_id=?", (product_id,)).fetchone()
        if row is None or row[0] != product_digest:
            # A changed product (values, rules, executor or implementation) starts its own cursor; executed
            # queries stay in the ledger, so the new order never repeats one inside its refresh period.
            return {"product_id": product_id, "product_digest": product_digest, "next_k": 0, "examined": 0, "emitted": 0,
                    "excluded": {}, "duplicates": 0, "refreshes": 0, "rebound": row is not None}
        return {"product_id": product_id, "product_digest": product_digest, "next_k": row[1], "examined": row[2],
                "emitted": row[3], "excluded": json.loads(row[4] or "{}"), "duplicates": row[5], "refreshes": row[6] or 0,
                "rebound": False}

    def save_cursor(self, cursor: dict) -> None:
        with self.lock:
            self.db.execute("insert into cursors values(?,?,?,?,?,?,?,?,?) on conflict(product_id) do update set "
                            "product_digest=excluded.product_digest, next_k=excluded.next_k, examined=excluded.examined, "
                            "emitted=excluded.emitted, excluded=excluded.excluded, duplicates=excluded.duplicates, "
                            "refreshes=excluded.refreshes, updated_at=excluded.updated_at",
                            (cursor["product_id"], cursor["product_digest"], cursor["next_k"], cursor["examined"],
                             cursor["emitted"], json.dumps(cursor["excluded"], sort_keys=True), cursor["duplicates"],
                             cursor.get("refreshes", 0), stamp(self.clock())))
            self.db.commit()

    # ------------------------------------------------------------------ queries
    def query_state(self, query_id: str):
        """None (never planned), or (state, next_due_at)."""
        with self.lock:
            row = self.db.execute("select state, next_due_at from queries where query_id=?", (query_id,)).fetchone()
        return row

    def within_refresh(self, query_id: str) -> "bool | None":
        """True: current cached execution. False: due. None: unexecuted or version-ineligible."""
        row = self.query_state(query_id)
        if row is not None and row[0] == "executed" and not self.cache_eligible(query_id):
            return None
        if row is None or row[0] != "executed" or not row[1]:
            return None if row is None or row[0] != "executed" else False
        return parse_stamp(row[1]) > self.clock()

    def cache_eligible(self, query_id: str) -> bool:
        with self.lock:
            row = self.db.execute("select cache_evidence_contract, cache_evidence_executions, executions "
                                  "from queries where query_id=?", (query_id,)).fetchone()
        # A previous runner may still know this ledger's ordinary columns.
        # Its later success increments executions without this contract-bound
        # counter, so it cannot relabel a v1 result as a current cache entry.
        return bool(row and row[0] == EVIDENCE and row[1] == row[2])

    def due_queries(self, executor_id: str, *, limit: int = 20) -> list:
        """Executed queries of one executor whose refresh period has passed, most productive first."""
        with self.lock:
            return self.db.execute(
                "select query_id, product_id, k, page, request, new_unique from queries where executor_id=? and "
                "state='executed' and next_due_at <= ? order by new_unique desc, next_due_at limit ?",
                (executor_id, stamp(self.clock()), limit)).fetchall()

    def plan(self, query) -> None:
        """Record a planned query once; planning twice keeps the first record."""
        with self.lock:
            sequence = (self.db.execute("select coalesce(max(sequence), 0) from queries where executor_id=?",
                                        (query.executor_id,)).fetchone()[0] or 0) + 1
            self.db.execute("insert or ignore into queries(query_id, executor_id, product_id, k, page, parent_query_id, "
                            "origin, assignment, request, planned_at, state, sequence) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (query.query_id, query.executor_id, query.product_id, query.k, query.page,
                             query.parent_query_id, query.origin,
                             json.dumps({name: (value.id if value is not None else None) for name, value in query.assignment.items()}, sort_keys=True),
                             json.dumps(query.request, sort_keys=True), stamp(self.clock()), "planned", sequence))
            self.db.commit()

    # ------------------------------------------------------------------ budgets and holds
    def usage(self, executor_id: str) -> tuple:
        with self.lock:
            row = self.db.execute("select requests, cost from daily_usage where executor_id=? and day=?",
                                  (executor_id, self.day())).fetchone()
        return row or (0, 0)

    def hold(self, executor_id: str):
        with self.lock:
            row = self.db.execute("select reason, until from holds where executor_id=?", (executor_id,)).fetchone()
        if row and parse_stamp(row[1]) > self.clock():
            return row
        return None

    def set_hold(self, executor_id: str, reason: str, until: datetime, attempt_id: str = "") -> None:
        with self.lock:
            self.db.execute("insert into holds values(?,?,?,?,?) on conflict(executor_id) do update set reason=excluded.reason, "
                            "until=excluded.until, attempt_id=excluded.attempt_id, created_at=excluded.created_at",
                            (executor_id, reason, stamp(until), attempt_id, stamp(self.clock())))
            self.db.commit()

    # ------------------------------------------------------------------ attempts
    def intent(self, query, run_id: str, cost: int) -> str:
        """The attempt exists before the request leaves; its cost is charged to the day's usage now."""
        attempt_id = uuid4().hex
        with self.lock:
            self.db.execute("insert into attempts(attempt_id, query_id, executor_id, run_id, started_at, state, cost, evidence_contract) "
                            "values(?,?,?,?,?,?,?,?)", (attempt_id, query.query_id, query.executor_id, run_id,
                                                         stamp(self.clock()), "intent", cost, EVIDENCE))
            self.db.execute("insert into daily_usage values(?,?,1,?) on conflict(executor_id, day) do update set "
                            "requests=requests+1, cost=cost+excluded.cost", (query.executor_id, self.day(), cost))
            self.db.execute("update queries set last_attempt_id=? where query_id=?", (attempt_id, query.query_id))
            self.db.commit()
        return attempt_id

    def evidence_path(self, executor_id: str, attempt_id: str, day: "str | None" = None) -> Path:
        return self.day_folder(day) / "raw" / executor_id / attempt_id[:2] / (attempt_id + ".json.gz")

    def store(self, attempt_id: str, query, request: dict, answer, *, write=None) -> dict:
        """Write the response file atomically, then mark the attempt stored. Returns the evidence record."""
        body = answer.body or b""
        envelope = {"record_type": EVIDENCE, "attempt_id": attempt_id, "query_id": query.query_id,
                    "executor_id": query.executor_id, "request": request, "target": answer.target,
                    "status": answer.status, "headers": answer.headers, "elapsed_ms": round(answer.elapsed_ms, 1),
                    "truncated": answer.truncated, "error_class": answer.error_class, "stored_at": stamp(self.clock()),
                    "body_sha256": hashlib.sha256(body).hexdigest(), "body_bytes": len(body),
                    "http_client": validate_observation(answer.extra.get("http_client"), request)}
        try:
            # Text bodies stay text, so gzip sees the JSON itself; anything else is kept exactly as base64.
            envelope["body_text"] = body.decode("utf-8")
        except UnicodeDecodeError:
            envelope["body_base64"] = base64.b64encode(body).decode("ascii")
        data = gzip.compress(json.dumps(envelope, sort_keys=True).encode(), compresslevel=6)
        path = self.evidence_path(query.executor_id, attempt_id)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_suffix(".tmp")
        (write or _write_durably)(temporary, data)
        temporary.replace(path)
        record = {"path": str(path.relative_to(self.root)), "sha256": hashlib.sha256(data).hexdigest(),
                  "stored_bytes": len(data), "body_sha256": envelope["body_sha256"], "body_bytes": len(body)}
        with self.lock:
            self.db.execute("update attempts set state='stored', finished_at=?, http_status=?, evidence_path=?, "
                            "evidence_sha256=?, body_sha256=?, body_bytes=?, stored_bytes=?, truncated=?, error_class=?, "
                            "headers=? where attempt_id=?",
                            (stamp(self.clock()), answer.status, record["path"], record["sha256"], record["body_sha256"],
                             record["body_bytes"], record["stored_bytes"], int(answer.truncated), answer.error_class,
                             json.dumps(answer.headers, sort_keys=True), attempt_id))
            self.db.commit()
        return record

    def store_failed(self, attempt_id: str, error_class: str) -> None:
        """Nothing came back to store: the attempt failed and the query stays unexecuted."""
        with self.lock:
            self.db.execute("update attempts set state='not_stored', finished_at=?, error_class=? where attempt_id=?",
                            (stamp(self.clock()), error_class[:80], attempt_id))
            self.db.commit()

    def mark_executed(self, attempt_id: str, query, *, parse_status: str, total_count, refresh_days: int) -> None:
        """Only a stored, parsed 200 answer executes a query; its next refresh is due after the period."""
        due = self.clock() + timedelta(days=refresh_days)
        with self.lock:
            state = self.db.execute("select state, evidence_contract from attempts where attempt_id=?", (attempt_id,)).fetchone()
            if not state or state[0] not in ("stored", "folded"):
                raise RuntimeError("query_not_executed_without_stored_response")
            if state[1] != EVIDENCE:
                raise ValueError("query_not_executed_from_prior_evidence_contract")
            self.db.execute("update queries set state='executed', executions=executions+1, last_executed_at=?, "
                            "next_due_at=?, last_status=?, total_count=?, cache_evidence_contract=?, "
                            "cache_evidence_executions=executions+1 where query_id=?",
                            (stamp(self.clock()), stamp(due), parse_status, total_count, EVIDENCE, query.query_id))
            self.db.execute("update attempts set parse_status=? where attempt_id=?", (parse_status, attempt_id))
            self.db.commit()

    def mark_failed(self, attempt_id: str, query, status: str) -> None:
        with self.lock:
            self.db.execute("update queries set state=case when state='executed' then 'executed' else 'failed' end, "
                            "last_status=? where query_id=?", (status, query.query_id))
            self.db.execute("update attempts set parse_status=? where attempt_id=?", (status, attempt_id))
            self.db.commit()

    def close_attempt(self, attempt_id: str) -> None:
        """A stored response that executed nothing (a refusal, a 429, an unparsable body) is closed, not refolded."""
        with self.lock:
            self.db.execute("update attempts set state='closed' where attempt_id=? and state='stored'", (attempt_id,))
            self.db.commit()

    def fold(self, attempt_id: str, query, items: list, routes: dict) -> dict:
        """Candidates and origins from parsed rows; one item found by two queries is one candidate.

        All rows of one response go in one transaction: a row that cannot be written rolls the whole response
        back, so a half-folded response never counts its candidates twice when it is folded again.
        """
        day = self.day()
        seen_at = stamp(self.clock())
        new, origins, routed = 0, 0, []
        items = [{key: (_text(value) if key in _TEXT_FIELDS else value) for key, value in item.items()} for item in items]
        with self.lock:
            try:
                for item in items:
                    inserted = self.db.execute(
                        "insert or ignore into candidates(key, url, kind, title, licence_reported, licence_field, licence_lead, "
                        "allowlisted, licence_basis, route, first_query_id, first_executor, first_seen_at, first_day, origins, payload) "
                        "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)",
                        (item["key"], item.get("url"), item["kind"], item.get("title"), item.get("licence_reported"),
                         item.get("licence_field"), item["licence_lead"], int(item["allowlisted"]), item["licence_basis"],
                         routes[item["key"]][0], query.query_id, query.executor_id, seen_at, day,
                         json.dumps({"description": item.get("description"), "extra": item.get("extra"),
                                     "proposal": routes[item["key"]][1]}, sort_keys=True, default=str))).rowcount
                    origin = self.db.execute("insert or ignore into origins values(?,?,?,?,?)",
                                             (item["key"], query.query_id, attempt_id, query.executor_id, seen_at)).rowcount
                    if inserted:
                        new += 1
                        routed.append(item)
                    elif origin:
                        self.db.execute("update candidates set origins=origins+1 where key=?", (item["key"],))
                    origins += origin
                self.db.execute("update attempts set state='folded', items=?, new_unique=? where attempt_id=?",
                                (len(items), new, attempt_id))
                self.db.execute("update queries set results=results+?, new_unique=new_unique+? where query_id=?",
                                (len(items), new, query.query_id))
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
        if routed:
            folder = self.day_folder(day) / "routed"
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            by_route = {}
            for item in routed:
                by_route.setdefault(routes[item["key"]][0], []).append(item)
            for name, rows in by_route.items():
                with open(folder / (name + ".jsonl"), "a", encoding="utf-8") as handle:
                    for item in rows:
                        handle.write(json.dumps({"key": item["key"], "url": item.get("url"), "kind": item["kind"],
                                                 "title": item.get("title"), "licence_reported": item.get("licence_reported"),
                                                 "licence_lead": item["licence_lead"], "allowlisted": item["allowlisted"],
                                                 "licence_basis": item["licence_basis"], "proposal": routes[item["key"]][1],
                                                 "query_id": query.query_id, "attempt_id": attempt_id,
                                                 "executor": query.executor_id,
                                                 "assignment": {name: (value.id if value is not None else None) for name, value in query.assignment.items()},
                                                 "first_seen_at": seen_at}, sort_keys=True) + "\n")
        return {"items": len(items), "new_unique": new, "origins": origins}

    # ------------------------------------------------------------------ recovery
    def require_current_unfinished_contract(self) -> None:
        """A new reader cannot resolve a prior writer's uncertain attempts."""
        with self.lock:
            count = self.db.execute("select count(*) from attempts where state in ('intent','stored') "
                                    "and coalesce(evidence_contract, '') != ?", (EVIDENCE,)).fetchone()[0]
        if count:
            raise ValueError("unfinished_prior_evidence_requires_pinned_runner_reconciliation")

    def unfinished(self) -> dict:
        """Attempts a crash left behind: intents with no stored response, stored responses not yet folded."""
        with self.lock:
            intents = self.db.execute("select attempt_id, query_id, executor_id, started_at from attempts where state='intent'").fetchall()
            stored = self.db.execute("select attempt_id, query_id, executor_id, evidence_path from attempts where state='stored'").fetchall()
        return {"intents": intents, "stored": stored}

    def abandon(self, attempt_id: str) -> None:
        with self.lock:
            self.db.execute("update attempts set state='abandoned_unknown_outcome', finished_at=? where attempt_id=?",
                            (stamp(self.clock()), attempt_id))
            self.db.commit()

    def find_evidence(self, executor_id: str, attempt_id: str) -> "Path | None":
        for folder in sorted(self.root.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"), reverse=True)[:3]:
            path = folder / "raw" / executor_id / attempt_id[:2] / (attempt_id + ".json.gz")
            if path.is_file():
                return path
        return None

    def read_evidence(self, path: Path) -> dict:
        envelope = json.loads(gzip.decompress(Path(path).read_bytes()))
        if envelope.get("record_type") != EVIDENCE:
            raise ValueError("evidence_version")
        validate_observation(envelope["http_client"], envelope["request"])
        if "body_text" in envelope:
            envelope["body"] = envelope.pop("body_text").encode("utf-8")
        else:
            envelope["body"] = base64.b64decode(envelope.pop("body_base64"))
        if hashlib.sha256(envelope["body"]).hexdigest() != envelope["body_sha256"]:
            raise ValueError("evidence_body_digest")
        return envelope

    def adopt(self, attempt_id: str, path: Path) -> None:
        """A response file that reached the disk before a crash is recorded as stored, not lost."""
        data = Path(path).read_bytes()
        envelope = self.read_evidence(path)
        with self.lock:
            self.db.execute("update attempts set state='stored', finished_at=?, http_status=?, evidence_path=?, "
                            "evidence_sha256=?, body_sha256=?, body_bytes=?, stored_bytes=?, truncated=?, error_class=?, "
                            "headers=? where attempt_id=?",
                            (envelope["stored_at"], envelope["status"], str(Path(path).relative_to(self.root)),
                             hashlib.sha256(data).hexdigest(), envelope["body_sha256"], envelope["body_bytes"], len(data),
                             int(envelope["truncated"]), envelope["error_class"], json.dumps(envelope["headers"]), attempt_id))
            self.db.commit()

    def imported_outcome(self, query_id: str, state: str) -> None:
        with self.lock:
            self.db.execute("update imported set state=? where query_id=?", (state, query_id))
            self.db.commit()

    def release_dispatched_imports(self) -> int:
        """Imported plans a crash left dispatched without an executed query go back to planned."""
        with self.lock:
            changed = self.db.execute("update imported set state='planned' where state='dispatched' and query_id not in "
                                      "(select query_id from queries where state='executed')").rowcount
            self.db.execute("update imported set state='executed' where state='dispatched'")
            self.db.commit()
        return changed

    # ------------------------------------------------------------------ status
    def write_status(self, value: dict) -> None:
        path = self.root / "state" / "status.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True, indent=1), encoding="utf-8")
        temporary.replace(path)

    def record_run(self, run_id: str, started: str, status: str, summary: dict, finished: "str | None" = None) -> None:
        with self.lock:
            self.db.execute("insert into runs values(?,?,?,?,?) on conflict(run_id) do update set finished_at=excluded.finished_at, "
                            "status=excluded.status, summary=excluded.summary",
                            (run_id, started, finished, status, json.dumps(summary, sort_keys=True)))
            self.db.commit()


_TEXT_FIELDS = ("key", "url", "kind", "title", "licence_reported", "licence_field", "licence_lead", "licence_basis", "description")


def _text(value):
    """A text column holds text: a source that answers a list or an object where text belongs is kept as JSON."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, default=str)[:500]


def _write_durably(path: Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
