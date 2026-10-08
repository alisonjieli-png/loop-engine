"""Durable metadata-only quota projection owned by Web Research.

One shared SQLite file serializes provider-account reservations, rolling-window
and UTC-day allowances, cost reserves and cooldowns across local processes.
It stores no query, result body, header or credential. Generic managed-record
CAS and the post-hoc cost ledger do not supply this reservation transaction;
the query multiplier's raw-response evidence store is deliberately not used.
Construction and policy parsing perform no filesystem or network operation.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from uuid import uuid4

POLICY = "web_research_quota_policy/v1"
STORE = "web_research_quota_store/v1"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ACCOUNT = re.compile(r"[a-z0-9_-]+:[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_IDENTITY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z")
MAXIMUM_MONEY = 10 ** 12
SCHEMA = """
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE reservations(
 id TEXT PRIMARY KEY, account TEXT NOT NULL, request_digest TEXT NOT NULL,
 policy_digest TEXT NOT NULL, reserved_at REAL NOT NULL, day INTEGER NOT NULL,
 reserved_cost INTEGER, state TEXT NOT NULL, http_status INTEGER,
 outcome TEXT, actual_cost INTEGER, response_digest TEXT,
 completed_at REAL, completion_digest TEXT);
CREATE INDEX account_day ON reservations(account,day);
CREATE INDEX account_window ON reservations(account,reserved_at);
CREATE INDEX account_state ON reservations(account,state);
CREATE TABLE holds(account TEXT PRIMARY KEY, until_at REAL, reason TEXT);
CREATE TABLE events(sequence INTEGER PRIMARY KEY, reservation_id TEXT,
 event_type TEXT NOT NULL, recorded_at REAL NOT NULL, evidence_digest TEXT);
"""


class QuotaRefused(ValueError):
    """A stable, non-sensitive refusal code; no provider or database text."""


class ReservationState(str, Enum):
    """Closed lifecycle vocabulary of web_research_quota_store/v1."""

    RESERVED = "reserved"
    UNKNOWN = "unknown"
    COMPLETED = "completed"
    RECONCILED = "reconciled"


def _require(condition, code="quota_policy_invalid"):
    if not condition:
        raise QuotaRefused(code)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _money(value):
    return type(value) is int and 0 <= value <= MAXIMUM_MONEY


def _finite(value, maximum):
    # Compare bounds before isfinite: converting an unbounded JSON integer to
    # float can itself overflow. Boolean values are not numeric allowances.
    return type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value)


def reported_microusd(value):
    """A reported USD value, rounded upward to a microdollar; unknown never becomes zero."""
    if type(value) not in (int, float):
        return None
    try:
        amount = Decimal(str(value)) * 1_000_000
        if not amount.is_finite() or amount < 0 or amount > MAXIMUM_MONEY:
            return None
        return int(amount.to_integral_value(rounding=ROUND_CEILING))
    except (ValueError, InvalidOperation, OverflowError):
        return None


@dataclass(frozen=True)
class AccountQuota:
    account: str
    daily_requests: int
    window_seconds: int
    window_requests: int
    daily_cost_microusd: int | None
    request_cost_reserve_microusd: int | None

    def __post_init__(self):
        _require(isinstance(self.account, str) and _ACCOUNT.fullmatch(self.account))
        _require(type(self.daily_requests) is int and 1 <= self.daily_requests <= 1_000_000)
        _require(type(self.window_seconds) is int and 1 <= self.window_seconds <= 86400)
        _require(type(self.window_requests) is int and 1 <= self.window_requests <= self.daily_requests)
        money = (self.daily_cost_microusd, self.request_cost_reserve_microusd)
        _require(all(value is None for value in money) or all(_money(value) for value in money))
        if self.daily_cost_microusd is not None:
            _require(self.request_cost_reserve_microusd <= self.daily_cost_microusd)


@dataclass(frozen=True)
class SearchQuotaPolicy:
    policy_id: str
    revision: str
    accounts: tuple[AccountQuota, ...]

    def __post_init__(self):
        _require(isinstance(self.policy_id, str) and _IDENTITY.fullmatch(self.policy_id))
        _require(isinstance(self.revision, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.revision))
        _require(type(self.accounts) is tuple and 1 <= len(self.accounts) <= 64
                 and all(type(item) is AccountQuota for item in self.accounts))
        _require(len({item.account for item in self.accounts}) == len(self.accounts))

    def to_record(self):
        return {"record_type": POLICY, "policy_id": self.policy_id, "revision": self.revision,
                "day_timezone": "UTC", "accounts": [item.__dict__ for item in self.accounts]}

    @property
    def digest(self):
        return _digest(self.to_record())

    def account(self, identity):
        selected = next((item for item in self.accounts if item.account == identity), None)
        _require(selected is not None, "quota_account_not_authorized")
        return selected

    @classmethod
    def from_record(cls, value):
        _require(type(value) is dict and set(value) == {"record_type", "policy_id", "revision", "day_timezone", "accounts"})
        _require(value["record_type"] == POLICY and value["day_timezone"] == "UTC" and type(value["accounts"]) is list)
        entries = []
        for item in value["accounts"]:
            _require(type(item) is dict and set(item) == set(AccountQuota.__dataclass_fields__))
            entries.append(AccountQuota(**item))
        return cls(value["policy_id"], value["revision"], tuple(entries))


@dataclass(frozen=True)
class QuotaOutcome:
    http_status: int | None
    ok: bool
    actual_cost_microusd: int | None
    retry_after_seconds: float | None
    remaining_zero: bool
    response_digest: str | None

    def __post_init__(self):
        _require(self.http_status is None or type(self.http_status) is int and 100 <= self.http_status <= 599, "quota_outcome_invalid")
        _require(type(self.ok) is bool and type(self.remaining_zero) is bool, "quota_outcome_invalid")
        _require(self.actual_cost_microusd is None or _money(self.actual_cost_microusd), "quota_outcome_invalid")
        _require(self.retry_after_seconds is None or _finite(self.retry_after_seconds, 31536000), "quota_outcome_invalid")
        _require(self.response_digest is None or isinstance(self.response_digest, str) and _DIGEST.fullmatch(self.response_digest), "quota_outcome_invalid")

    @classmethod
    def from_result(cls, value):
        _require(type(value) is dict and value.get("record_type") == "web_research_result/v1", "quota_outcome_invalid")
        usage = value.get("provider_usage") or {}
        rate = value.get("rate_limit") or {}
        _require(type(usage) is dict and type(rate) is dict, "quota_outcome_invalid")
        remaining = rate.get("x-ratelimit-remaining", "")
        retry = value.get("retry_after_seconds")
        if not _finite(retry, 31536000):
            retry = None
        return cls(value.get("http_status"), value.get("ok"), reported_microusd(usage.get("cost_usd")), retry,
                   isinstance(remaining, str) and any(part.strip() == "0" for part in remaining.split(",")),
                   value.get("response_sha256"))


@dataclass(frozen=True)
class DurableSearchQuota:
    state_path: Path
    policy: SearchQuotaPolicy
    allow_writes: bool = False
    clock: object = field(default=time.time, repr=False, compare=False)

    def __post_init__(self):
        path = Path(self.state_path)
        _require(path.is_absolute() and ".." not in path.parts and path.suffix == ".sqlite", "quota_path_invalid")
        _require(type(self.policy) is SearchQuotaPolicy and type(self.allow_writes) is bool and callable(self.clock))
        object.__setattr__(self, "state_path", path)

    @property
    def binding_digest(self):
        return _digest({"state_path": str(self.state_path), "policy_digest": self.policy.digest,
                        "allow_writes": self.allow_writes})

    def _time(self):
        value = self.clock()
        _require(_finite(value, 2 ** 40), "quota_clock_invalid")
        return float(value)

    def _path(self, create):
        _require(self.allow_writes, "quota_accounting_write_grant_required")
        parent = self.state_path.parent
        if create:
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _require(parent.resolve() == parent and not parent.is_symlink(), "quota_path_symlink_refused")
        details = parent.stat()
        _require(details.st_uid == os.geteuid() and not details.st_mode & 0o022, "quota_directory_not_private")
        flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0)
        descriptor = os.open(self.state_path, flags, 0o600)
        try:
            details = os.fstat(descriptor)
            _require(stat.S_ISREG(details.st_mode) and details.st_uid == os.geteuid()
                     and not details.st_mode & 0o077, "quota_file_not_private")
        finally:
            os.close(descriptor)

    def _schema(self, connection, create):
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables and create:
            # execute statements inside the caller's transaction; executescript
            # would commit that transaction before running its own statements.
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.executemany("INSERT INTO metadata VALUES(?,?)", (
                ("record_type", STORE), ("policy_digest", self.policy.digest),
                ("policy", json.dumps(self.policy.to_record(), sort_keys=True))))
        else:
            _require("metadata" in tables, "quota_store_not_initialized")
            version = connection.execute("SELECT value FROM metadata WHERE key='record_type'").fetchone()
            _require(version is not None and version[0] == STORE, "quota_store_version")
        current = connection.execute("SELECT value FROM metadata WHERE key='policy_digest'").fetchone()
        _require(current is not None and current[0] == self.policy.digest, "quota_policy_changed")

    @contextmanager
    def _transaction(self, *, create=True):
        _require(self.allow_writes, "quota_accounting_write_grant_required")
        connection = None
        try:
            self._path(create)
            connection = sqlite3.connect(self.state_path, timeout=30, isolation_level=None)
            connection.execute("PRAGMA busy_timeout=30000")
            connection.execute("BEGIN IMMEDIATE")
            self._schema(connection, create)
            yield connection
            connection.commit()
        except (sqlite3.Error, OSError):
            if connection is not None:
                connection.rollback()
            raise QuotaRefused("quota_state_unavailable") from None
        except Exception:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    def _reason(self, db, account, now):
        limits = self.policy.account(account)
        if db.execute("SELECT 1 FROM reservations WHERE account=? AND state NOT IN (?,?,?,?) LIMIT 1",
                      (account, *(state.value for state in ReservationState))).fetchone():
            return "quota_record_state_invalid"
        latest = db.execute("SELECT MAX(reserved_at) FROM reservations WHERE account=?", (account,)).fetchone()[0]
        if latest is not None and now < latest:
            return "quota_clock_regressed"
        if db.execute("SELECT 1 FROM reservations WHERE account=? AND state IN (?,?) LIMIT 1",
                      (account, ReservationState.RESERVED.value, ReservationState.UNKNOWN.value)).fetchone():
            return "quota_outcome_pending"
        held = db.execute("SELECT until_at,reason FROM holds WHERE account=?", (account,)).fetchone()
        if held and held[1]:
            return "quota_account_held"
        if held and held[0] is not None and now < held[0]:
            return "quota_cooldown_active"
        day = int(now // 86400)
        daily = db.execute("SELECT COUNT(*) FROM reservations WHERE account=? AND day=?", (account, day)).fetchone()[0]
        window = db.execute("SELECT COUNT(*) FROM reservations WHERE account=? AND reserved_at>?", (account, now - limits.window_seconds)).fetchone()[0]
        if daily >= limits.daily_requests:
            return "quota_daily_requests_exhausted"
        if window >= limits.window_requests:
            return "quota_window_requests_exhausted"
        if limits.daily_cost_microusd is not None:
            unknown, spent = db.execute("SELECT SUM(CASE WHEN actual_cost IS NULL AND reserved_cost IS NULL THEN 1 ELSE 0 END), "
                "COALESCE(SUM(COALESCE(actual_cost,reserved_cost)),0) FROM reservations WHERE account=? AND day=?", (account, day)).fetchone()
            if unknown:
                return "quota_cost_unknown"
            if spent + limits.request_cost_reserve_microusd > limits.daily_cost_microusd:
                return "quota_daily_cost_exhausted"
        return ""

    def refusal(self, account):
        try:
            self.policy.account(account)
            _require(self.allow_writes, "quota_accounting_write_grant_required")
            if not self.state_path.exists():
                return ""
            with self._transaction(create=False) as db:
                return self._reason(db, account, self._time())
        except QuotaRefused as error:
            return str(error)
        except OSError:
            return "quota_state_unavailable"

    def reserve(self, account, request_digest):
        _require(isinstance(request_digest, str) and _DIGEST.fullmatch(request_digest), "quota_request_digest_invalid")
        limits = self.policy.account(account)
        self._time()  # Reject an invalid host clock before creating any state.
        identity = uuid4().hex
        with self._transaction() as db:
            # Read the clock after acquiring the write lock. A process waiting
            # across midnight must not charge its next dispatch to yesterday.
            now = self._time()
            reason = self._reason(db, account, now)
            _require(not reason, reason)
            db.execute("INSERT INTO reservations(id,account,request_digest,policy_digest,reserved_at,day,reserved_cost,state) "
                       "VALUES(?,?,?,?,?,?,?,?)", (identity, account, request_digest, self.policy.digest,
                                                 now, int(now // 86400), limits.request_cost_reserve_microusd,
                                                 ReservationState.RESERVED.value))
            db.execute("INSERT INTO events(reservation_id,event_type,recorded_at) VALUES(?,'reserved',?)", (identity, now))
        return identity

    def finish(self, reservation_id, outcome: QuotaOutcome):
        _require(type(outcome) is QuotaOutcome, "quota_outcome_invalid")
        completion_digest = _digest(outcome.__dict__)
        with self._transaction(create=False) as db:
            now = self._time()
            row = db.execute("SELECT account,state,reserved_cost,completion_digest FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            _require(row is not None, "quota_reservation_unknown")
            account, state, reserve, previous = row
            self.policy.account(account)
            if previous == completion_digest:
                return
            _require(state == ReservationState.RESERVED.value, "quota_completion_conflict")
            unknown = outcome.http_status is None
            money_unknown = reserve is not None and outcome.actual_cost_microusd is None
            code = ("unknown_outcome" if unknown else "cost_unknown" if money_unknown else
                    "success" if outcome.ok else "failed_response")
            db.execute("UPDATE reservations SET state=?,http_status=?,outcome=?,actual_cost=?,response_digest=?,completed_at=?,completion_digest=? WHERE id=?",
                       (ReservationState.UNKNOWN.value if unknown or money_unknown else ReservationState.COMPLETED.value, outcome.http_status, code,
                        outcome.actual_cost_microusd, outcome.response_digest, now, completion_digest, reservation_id))
            until, reason = None, None
            if outcome.http_status in (401, 403, 432, 433):
                reason = "provider_access_or_usage_refused"
            elif outcome.http_status == 429 or outcome.remaining_zero:
                if outcome.retry_after_seconds is None:
                    reason = "provider_cooldown_unknown"
                else:
                    until = now + max(1, math.ceil(outcome.retry_after_seconds))
            if reserve is not None and outcome.actual_cost_microusd is not None and outcome.actual_cost_microusd > reserve:
                reason = "declared_cost_reserve_exceeded"
            if until is not None or reason:
                db.execute("INSERT INTO holds VALUES(?,?,?) ON CONFLICT(account) DO UPDATE SET "
                           "until_at=MAX(COALESCE(holds.until_at,0),COALESCE(excluded.until_at,0)),reason=COALESCE(excluded.reason,holds.reason)",
                           (account, until, reason))
            db.execute("INSERT INTO events(reservation_id,event_type,recorded_at,evidence_digest) VALUES(?,'completed',?,?)", (reservation_id, now, completion_digest))

    def reconcile(self, reservation_id, *, evidence_digest, actual_cost_microusd=None):
        """Explicit operator reconciliation; request counts are never refunded."""
        _require(isinstance(evidence_digest, str) and _DIGEST.fullmatch(evidence_digest), "quota_reconciliation_evidence_required")
        _require(actual_cost_microusd is None or _money(actual_cost_microusd), "quota_outcome_invalid")
        with self._transaction(create=False) as db:
            row = db.execute("SELECT account,state,reserved_cost FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            _require(row is not None and row[1] in (ReservationState.RESERVED.value, ReservationState.UNKNOWN.value), "quota_reconciliation_state")
            self.policy.account(row[0])
            _require(row[2] is None or actual_cost_microusd is not None, "quota_reconciliation_cost_required")
            db.execute("UPDATE reservations SET state=?,actual_cost=?,outcome='operator_reconciled',completed_at=? WHERE id=?",
                       (ReservationState.RECONCILED.value, actual_cost_microusd, self._time(), reservation_id))
            db.execute("INSERT INTO events(reservation_id,event_type,recorded_at,evidence_digest) VALUES(?,'reconciled',?,?)",
                       (reservation_id, self._time(), evidence_digest))
            if row[2] is not None and actual_cost_microusd > row[2]:
                db.execute("INSERT INTO holds VALUES(?,NULL,'declared_cost_reserve_exceeded') ON CONFLICT(account) "
                           "DO UPDATE SET reason='declared_cost_reserve_exceeded'", (row[0],))

    def snapshot(self, account):
        """Read an explicitly authorized accounting view; no request or result text exists here."""
        self.policy.account(account)
        with self._transaction(create=False) as db:
            now = self._time()
            used, known, unknown = db.execute("SELECT COUNT(*),COALESCE(SUM(actual_cost),0), "
                "SUM(CASE WHEN actual_cost IS NULL THEN 1 ELSE 0 END) FROM reservations WHERE account=? AND day=?",
                (account, int(now // 86400))).fetchone()
            pending = [row[0] for row in db.execute("SELECT id FROM reservations WHERE account=? AND state IN (?,?)",
                (account, ReservationState.RESERVED.value, ReservationState.UNKNOWN.value))]
            return {"record_type": "web_research_quota_snapshot/v1", "account": account, "scope": "this_shared_accounting_store",
                    "other_account_usage": "unknown", "policy_digest": self.policy.digest, "requests_reserved_today": used,
                    "reported_cost_microusd_subtotal": known, "requests_with_unknown_cost": unknown or 0,
                    "unresolved_reservations": pending, "refusal": self._reason(db, account, now)}


def self_test():
    """Qualify the accounting contract on an owned temporary file, without provider effects."""
    import tempfile
    tests = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "qualification.sqlite"
        account = "exa:offline-fixture"
        policy = SearchQuotaPolicy("offline", "1.0.0", (AccountQuota(account, 1, 60, 1, None, None),))
        store = DurableSearchQuota(path, policy, True, clock=lambda: 1000)
        tests.append({"test": "constructor_is_effect_free", "passed": not path.exists()})
        reservation = store.reserve(account, _digest({"fixture": "request"}))
        tests.append({"test": "pending_outcome_blocks_restart", "passed":
                      DurableSearchQuota(path, policy, True, clock=lambda: 1001).refusal(account) == "quota_outcome_pending"})
        store.finish(reservation, QuotaOutcome(200, True, None, None, False, None))
        tests.append({"test": "completed_request_keeps_shared_daily_count", "passed":
                      store.refusal(account) == "quota_daily_requests_exhausted"})
        view = store.snapshot(account)
        tests.append({"test": "unreported_cost_and_other_usage_stay_unknown", "passed":
                      view["requests_with_unknown_cost"] == 1 and view["other_account_usage"] == "unknown"})
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests), "provider_integration_proven": False}
