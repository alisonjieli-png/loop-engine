"""Durable trigger admission and fenced activation leasing.

This is an internal runtime mechanic.  It never performs semantic work and
never substitutes for the canonical ``Loop``.  Its job is to persist passive
series, trigger, activation, and lease records so a worker can start the exact
Loop definition named by a claimed activation.
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationHistoryDisposition, ActivationRecord,
    ActivationStartRequest, ActivationStatus, ActivationTerminalRequest,
    LeaseHeartbeatRequest, ReactiveSeriesDefinition, TriggerEnvelope,
    WorkLease)
from ..loop.reactive_contracts import (
    InputOrdering, PersistenceMode, ReactiveLoopProfile)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS reactive_series (
    series_id TEXT PRIMARY KEY,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reactive_triggers (
    trigger_id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    deduplication_key TEXT NOT NULL,
    priority INTEGER NOT NULL,
    deadline TEXT NOT NULL,
    received_at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL,
    UNIQUE(series_id, deduplication_key, input_digest)
);
CREATE TABLE IF NOT EXISTS reactive_activation_revisions (
    activation_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    series_id TEXT NOT NULL,
    status TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (activation_id, revision)
);
CREATE TABLE IF NOT EXISTS reactive_lease_revisions (
    lease_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    activation_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (lease_id, revision)
);
CREATE INDEX IF NOT EXISTS reactive_activation_series_status
ON reactive_activation_revisions(series_id, status, revision);
"""


class ReactiveSchedulerError(RuntimeError):
    """A trigger, lease, transition, or recovery invariant failed."""


class DurableSeriesHistoryError(ReactiveSchedulerError):
    """A DURABLE_SERIES series was offered a completed result without history."""


def _canonical(value: dict) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False)


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReactiveSchedulerError("timestamp must use ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TriggerAdmissionResult:
    """Exact activation selected for a trigger and whether work was created."""

    trigger: TriggerEnvelope
    activation: ActivationRecord
    created: bool
    reason: str


@dataclass(frozen=True)
class ActivationClaimResult:
    """One admitted activation plus its exclusive fenced lease."""

    activation: ActivationRecord
    lease: WorkLease


class SQLiteReactiveScheduler:
    """SQLite WAL scheduler state with append-only activation revisions."""

    installed_input_orderings = frozenset({
        InputOrdering.FIFO, InputOrdering.PRIORITY_AGING,
        InputOrdering.EARLIEST_DEADLINE, InputOrdering.SEEDED_RANDOM,
    })

    def __init__(self, database_path: str, observations=None, *,
                 enforce_durable_history: bool = False) -> None:
        # W6, behind a flag. A DURABLE_SERIES profile should refuse COMPLETED
        # without a persisted history, and this scheduler can. But the worker
        # does not yet persist history for durable series on its default
        # binding, and five of its checks assert that it does not, so turning
        # this on alone refuses every completed activation on a durable series.
        # Enabling it is a paired change with the worker, made deliberately.
        self._enforce_durable_history = bool(enforce_durable_history)
        from .runtime_observer import RuntimeObservationServices
        if not isinstance(database_path, str) or not database_path.strip():
            raise ReactiveSchedulerError(
                "reactive scheduler requires an explicit database path")
        path = Path(database_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = str(path)
        self._connection = sqlite3.connect(self.database_path, timeout=5.0)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()
        self._profiles: dict[tuple[str, str, str], ReactiveLoopProfile] = {}
        self._observations = observations or RuntimeObservationServices()

    def register_profile(self, profile: ReactiveLoopProfile) -> None:
        if not isinstance(profile, ReactiveLoopProfile):
            raise ReactiveSchedulerError(
                "scheduler profile registration requires ReactiveLoopProfile")
        key = (profile.profile_id, profile.version, profile.content_digest)
        current = self._profiles.get(key)
        if current is not None and current != profile:
            raise ReactiveSchedulerError(
                "reactive profile identity names changed content")
        self._profiles[key] = profile

    def register_series(self, series: ReactiveSeriesDefinition) -> None:
        if not isinstance(series, ReactiveSeriesDefinition):
            raise ReactiveSchedulerError(
                "series registration requires ReactiveSeriesDefinition")
        profile = self._profile_for(series)
        series.validate_profile(profile)
        if profile.input_scheduling.ordering not in self.installed_input_orderings:
            raise ReactiveSchedulerError(
                "reactive series requests an uninstalled input ordering")
        if (profile.activation.debounce_seconds
                or profile.activation.cooldown_seconds):
            raise ReactiveSchedulerError(
                "local scheduler does not yet install debounce or cooldown")
        body = _canonical(series.to_dict())
        digest = _digest(body)
        existing = self._connection.execute(
            "SELECT record_digest, body FROM reactive_series "
            "WHERE series_id = ?", (series.series_id,)).fetchone()
        if existing is not None:
            if tuple(existing) != (digest, body):
                raise ReactiveSchedulerError(
                    "series identity cannot be reused for changed content")
            return
        self._connection.execute(
            "INSERT INTO reactive_series VALUES (?, ?, ?)",
            (series.series_id, digest, body))
        self._connection.commit()

    def admit(self, trigger: TriggerEnvelope) -> TriggerAdmissionResult:
        """Deduplicate and admit one useful trigger as finite work."""
        if not isinstance(trigger, TriggerEnvelope):
            raise ReactiveSchedulerError("admit requires TriggerEnvelope")
        series = self._require_series(trigger.series_id)
        profile = self._profile_for(series)
        if trigger.trigger_kind not in profile.activation.accepted_triggers:
            raise ReactiveSchedulerError(
                "trigger kind is not accepted by the reactive profile")
        if (profile.admission.require_observable_delta
                and trigger.information_delta <= 0):
            raise ReactiveSchedulerError(
                "trigger has no observable information delta")
        if trigger.information_delta < \
                profile.activation.minimum_information_delta:
            raise ReactiveSchedulerError(
                "trigger information delta is below the activation policy")
        with self._revision_transaction(trigger.activation_id):
            duplicate = self._find_duplicate(trigger, profile)
            if duplicate is None:
                pending = self._pending_count(series.series_id)
                if pending >= profile.admission.maximum_pending_inputs:
                    raise ReactiveSchedulerError(
                        "reactive series pending-input limit is reached")
                trigger_body = _canonical(trigger.to_dict())
                self._connection.execute(
                    "INSERT INTO reactive_triggers VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (trigger.trigger_id, trigger.series_id,
                     trigger.subject_ref, trigger.input_ref.content_digest,
                     trigger.deduplication_key, trigger.priority,
                     trigger.deadline, trigger.received_at,
                     _digest(trigger_body), trigger_body))
                activation = ActivationRecord(
                    trigger.activation_id, trigger.series_id,
                    trigger.trigger_id, trigger.input_ref,
                    series.loop_definition_ref, ActivationStatus.ADMITTED,
                    0, 0, 0, trigger.received_at)
                self._append_activation(activation)
        if duplicate is not None:
            prior_trigger, activation = duplicate
            self._emit_trigger(prior_trigger, activation, False)
            return TriggerAdmissionResult(
                prior_trigger, activation, False, "duplicate_or_unchanged_input")
        self._emit_trigger(trigger, activation, True)
        return TriggerAdmissionResult(trigger, activation, True, "admitted")

    def claim(
            self, request: ActivationClaimRequest
            ) -> ActivationClaimResult | None:
        """Claim the next eligible activation with a new fencing token."""
        if not isinstance(request, ActivationClaimRequest):
            raise ReactiveSchedulerError(
                "claim requires ActivationClaimRequest")
        self.recover_expired(request.as_of)
        with self._revision_transaction() as scope:
            rows = self._admitted_rows(request.series_id)
            record = self._select(rows, request)
            if record is None:
                return None
            scope["activation_id"] = record.activation_id
            series = self._require_series(record.series_id)
            if self._active_count(record.series_id) >= \
                    series.maximum_active_activations:
                return None
            if record.attempt >= series.maximum_attempts_per_trigger:
                dead = replace(
                    record, status=ActivationStatus.DEAD_LETTER,
                    revision=record.revision + 1, terminal_at=request.as_of,
                    failure_code="ATTEMPT_BUDGET_EXHAUSTED")
                self._append_activation(dead)
                return None
            fence = record.fencing_token + 1
            lease_id = f"lease.{record.activation_id}.{fence}"
            expires = _iso(_instant(request.as_of) + timedelta(
                seconds=float(request.lease_seconds)))
            lease = WorkLease(
                lease_id, record.activation_id, request.worker_id, fence,
                request.as_of, request.as_of, expires)
            self._append_lease(lease)
            leased = replace(
                record, status=ActivationStatus.LEASED,
                revision=record.revision + 1, attempt=record.attempt + 1,
                fencing_token=fence, lease_id=lease_id,
                worker_id=(request.worker_id or None))
            self._append_activation(leased)
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_activation_leased", {
                "series_id": leased.series_id,
                "activation_id": leased.activation_id,
                "lease_id": leased.lease_id,
                "worker_id": leased.worker_id, "status": "leased",
                "fencing_token": leased.fencing_token,
                "attempt": leased.attempt,
            }))
        return ActivationClaimResult(leased, lease)

    def start(self, request: ActivationStartRequest) -> ActivationRecord:
        if not isinstance(request, ActivationStartRequest):
            raise ReactiveSchedulerError(
                "start requires ActivationStartRequest")
        with self._revision_transaction(request.activation_id):
            current = self._require_current(request.activation_id)
            self._require_fence(
                current, request.lease_id, request.fencing_token)
            if current.status is not ActivationStatus.LEASED:
                raise ReactiveSchedulerError(
                    "only a leased activation can start")
            started = replace(
                current, status=ActivationStatus.RUNNING,
                revision=current.revision + 1, started_at=request.started_at)
            self._append_activation(started)
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_activation_started", {
                "series_id": started.series_id,
                "activation_id": started.activation_id,
                "lease_id": started.lease_id,
                "worker_id": started.worker_id, "status": "running",
                "fencing_token": started.fencing_token,
                "revision": started.revision,
            }))
        return started

    def heartbeat(self, request: LeaseHeartbeatRequest) -> WorkLease:
        if not isinstance(request, LeaseHeartbeatRequest):
            raise ReactiveSchedulerError(
                "heartbeat requires LeaseHeartbeatRequest")
        with self._revision_transaction(request.activation_id):
            current = self._require_current(request.activation_id)
            self._require_fence(
                current, request.lease_id, request.fencing_token)
            if current.status not in {
                    ActivationStatus.LEASED, ActivationStatus.RUNNING}:
                raise ReactiveSchedulerError(
                    "terminal or admitted activation cannot heartbeat")
            previous = self._require_lease(request.lease_id)
            if (_instant(request.heartbeat_at)
                    < _instant(previous.heartbeat_at)
                    or _instant(request.expires_at)
                    <= _instant(request.heartbeat_at)):
                raise ReactiveSchedulerError(
                    "heartbeat time and expiry must move forward")
            renewed = WorkLease(
                previous.lease_id, previous.activation_id,
                previous.worker_id, previous.fencing_token,
                previous.acquired_at, request.heartbeat_at,
                request.expires_at)
            self._append_lease(renewed)
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_lease_heartbeat", {
                "series_id": current.series_id,
                "activation_id": current.activation_id,
                "lease_id": renewed.lease_id,
                "worker_id": renewed.worker_id, "status": "heartbeat",
                "fencing_token": renewed.fencing_token,
                "expires_at": renewed.expires_at,
            }))
        return renewed

    def terminal(self, request: ActivationTerminalRequest) -> ActivationRecord:
        if not isinstance(request, ActivationTerminalRequest):
            raise ReactiveSchedulerError(
                "terminal requires ActivationTerminalRequest")
        with self._revision_transaction(request.activation_id):
            current = self._require_current(request.activation_id)
            self._require_fence(
                current, request.lease_id, request.fencing_token,
                request.worker_id)
            if current.status not in {
                    ActivationStatus.LEASED, ActivationStatus.RUNNING}:
                raise ReactiveSchedulerError(
                    "only active leased work can become terminal")
            if request.status is ActivationStatus.COMPLETED:
                if self._enforce_durable_history:
                    self._require_durable_history(current, request)
            terminal = replace(
                current, status=request.status,
                revision=current.revision + 1, loop_id=request.loop_id,
                terminal_at=request.terminal_at,
                terminal_code=request.terminal_code,
                failure_code=request.failure_code,
                candidate_refs=request.candidate_refs,
                history_ref=request.history_ref,
                history_disposition=request.history_disposition)
            self._append_activation(terminal)
        from .runtime_observer import RuntimeObservation
        observation_kind = (
            "reactive_activation_completed"
            if terminal.status is ActivationStatus.COMPLETED
            else "reactive_activation_failed")
        fields = {
            "series_id": terminal.series_id,
            "activation_id": terminal.activation_id,
            "status": ("completed" if terminal.status
                       is ActivationStatus.COMPLETED else "failed"),
            "fencing_token": terminal.fencing_token,
            "candidate_count": len(terminal.candidate_refs),
        }
        if terminal.status is ActivationStatus.COMPLETED:
            fields["terminal_code"] = terminal.terminal_code
        else:
            fields["failure_code"] = terminal.failure_code
        self._observations.emit(RuntimeObservation(
            observation_kind, fields, loop_id=terminal.loop_id))
        return terminal

    def recover_expired(self, as_of: str) -> tuple[ActivationRecord, ...]:
        """Retry unstarted work; retain started work for effect reconciliation.

        Lease expiry does not establish that a running handler stopped or that
        its effects did not commit. No replay-safety policy is installed at
        this boundary, so attempts remaining cannot authorize its replay.
        """
        now = _instant(as_of)
        recovered = []
        active = {ActivationStatus.LEASED, ActivationStatus.RUNNING}
        for stale in self._active_records():
            # Each recovery is its own write transaction and rereads the
            # record under the lock: a peer's late terminal may have landed
            # between the survey above and this write, and its revision must
            # win rather than collide with ours.
            with self._revision_transaction(stale.activation_id):
                record = self._require_current(stale.activation_id)
                if record.status not in active:
                    continue
                lease = self._require_lease(record.lease_id)
                if _instant(lease.expires_at) > now:
                    continue
                series = self._require_series(record.series_id)
                if record.status is ActivationStatus.RUNNING:
                    updated = replace(
                        record, status=ActivationStatus.DEAD_LETTER,
                        revision=record.revision + 1, terminal_at=as_of,
                        failure_code="RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED")
                elif record.attempt >= series.maximum_attempts_per_trigger:
                    updated = replace(
                        record, status=ActivationStatus.DEAD_LETTER,
                        revision=record.revision + 1, terminal_at=as_of,
                        failure_code="LEASE_EXPIRED_ATTEMPTS_EXHAUSTED")
                else:
                    updated = replace(
                        record, status=ActivationStatus.ADMITTED,
                        revision=record.revision + 1, lease_id="",
                        worker_id="", loop_id="", started_at="",
                        terminal_at="", terminal_code="", failure_code="",
                        candidate_refs=())
                self._append_activation(updated)
            recovered.append(updated)
        from .runtime_observer import RuntimeObservation
        for updated in recovered:
            self._observations.emit(RuntimeObservation(
                "reactive_activation_recovered", {
                    "series_id": updated.series_id,
                    "activation_id": updated.activation_id,
                    "status": ("dead_letter" if updated.status
                               is ActivationStatus.DEAD_LETTER
                               else "recovered"),
                    "fencing_token": updated.fencing_token,
                    "attempt": updated.attempt,
                    "failure_code": updated.failure_code,
                }))
        return tuple(recovered)

    def get_activation(self, activation_id: str) -> ActivationRecord | None:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_activation_revisions "
            "WHERE activation_id = ? ORDER BY revision DESC LIMIT 1",
            (activation_id,)).fetchone()
        if row is None:
            return None
        return ActivationRecord.from_dict(json.loads(
            self._verified_body(row, "activation")))

    def get_series(self, series_id: str) -> ReactiveSeriesDefinition | None:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_series "
            "WHERE series_id = ?", (series_id,)).fetchone()
        if row is None:
            return None
        return ReactiveSeriesDefinition.from_dict(json.loads(
            self._verified_body(row, "series")))

    def get_trigger(self, trigger_id: str) -> TriggerEnvelope | None:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_triggers "
            "WHERE trigger_id = ?", (trigger_id,)).fetchone()
        if row is None:
            return None
        return TriggerEnvelope.from_dict(json.loads(
            self._verified_body(row, "trigger")))

    def activation_history(
            self, activation_id: str) -> tuple[ActivationRecord, ...]:
        rows = self._connection.execute(
            "SELECT record_digest, body FROM reactive_activation_revisions "
            "WHERE activation_id = ? ORDER BY revision",
            (activation_id,)).fetchall()
        return tuple(ActivationRecord.from_dict(json.loads(
            self._verified_body(row, "activation"))) for row in rows)

    def _find_duplicate(self, trigger, profile):
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_triggers "
            "WHERE series_id = ? AND deduplication_key = ? "
            "AND input_digest = ?",
            (trigger.series_id, trigger.deduplication_key,
             trigger.input_ref.content_digest)).fetchone()
        if row is None and profile.admission.require_new_input_digest:
            row = self._connection.execute(
                "SELECT record_digest, body FROM reactive_triggers "
                "WHERE series_id = ? AND subject_ref = ? AND input_digest = ? "
                "ORDER BY received_at DESC LIMIT 1",
                (trigger.series_id, trigger.subject_ref,
                 trigger.input_ref.content_digest)).fetchone()
        if row is None:
            return None
        prior = TriggerEnvelope.from_dict(json.loads(
            self._verified_body(row, "trigger")))
        return prior, self._require_current(prior.activation_id)

    def _emit_trigger(self, trigger, activation, created: bool) -> None:
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_trigger_admitted", {
                "series_id": trigger.series_id,
                "trigger_id": trigger.trigger_id,
                "activation_id": activation.activation_id,
                "status": "admitted" if created else "deduplicated",
                "created": created,
                "input_digest": trigger.input_ref.content_digest,
            }, loop_id=trigger.source_loop_id))

    def _admitted_rows(self, series_id: str):
        where = "AND r.series_id = ?" if series_id else ""
        params = (series_id,) if series_id else ()
        return self._connection.execute(
            "WITH latest AS (SELECT activation_id, MAX(revision) AS revision "
            "FROM reactive_activation_revisions GROUP BY activation_id) "
            "SELECT r.record_digest, r.body, t.priority, t.deadline, "
            "t.received_at FROM reactive_activation_revisions r "
            "JOIN latest l ON r.activation_id = l.activation_id "
            "AND r.revision = l.revision "
            "JOIN reactive_triggers t ON json_extract(r.body, '$.trigger_id') "
            "= t.trigger_id WHERE r.status = 'admitted' " + where,
            params).fetchall()

    def _select(self, rows, request):
        if not rows:
            return None
        records = [(ActivationRecord.from_dict(json.loads(
            self._verified_body(row[:2], "activation"))), row[2], row[3], row[4])
                   for row in rows]
        if request.series_id:
            profile = self._profile_for(self._require_series(request.series_id))
            ordering = profile.input_scheduling.ordering
            if ordering is InputOrdering.PRIORITY_AGING:
                rate = profile.input_scheduling.priority_aging_per_second
                records.sort(key=lambda item: (
                    -(item[1] + max(0.0, (_instant(request.as_of)
                                        - _instant(item[3])).total_seconds())
                       * rate), item[3], item[0].activation_id))
            elif ordering is InputOrdering.EARLIEST_DEADLINE:
                records.sort(key=lambda item: (
                    _instant(item[2]) if item[2]
                    else datetime.max.replace(tzinfo=timezone.utc), item[3],
                    item[0].activation_id))
            elif ordering is InputOrdering.SEEDED_RANDOM:
                seed = profile.input_scheduling.random_seed
                records.sort(key=lambda item: item[0].activation_id)
                random.Random(seed).shuffle(records)
            else:
                records.sort(key=lambda item: (
                    item[3], item[0].activation_id))
        if not request.series_id:
            records.sort(key=lambda item: (item[3], item[0].activation_id))
        return records[0][0]

    def _append_activation(self, record: ActivationRecord) -> None:
        body = _canonical(record.to_dict())
        self._connection.execute(
            "INSERT INTO reactive_activation_revisions VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.activation_id, record.revision, record.series_id,
             record.status.value, record.lease_id, record.worker_id,
             record.fencing_token, _digest(body), body))

    def _append_lease(self, lease: WorkLease) -> None:
        revision = self._connection.execute(
            "SELECT COALESCE(MAX(revision), -1) + 1 "
            "FROM reactive_lease_revisions WHERE lease_id = ?",
            (lease.lease_id,)).fetchone()[0]
        body = _canonical(lease.to_dict())
        self._connection.execute(
            "INSERT INTO reactive_lease_revisions VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?)",
            (lease.lease_id, revision, lease.activation_id, lease.worker_id,
             lease.fencing_token, lease.expires_at, _digest(body), body))

    def _require_current(self, activation_id: str) -> ActivationRecord:
        record = self.get_activation(activation_id)
        if record is None:
            raise ReactiveSchedulerError("activation is unavailable")
        return record

    def _require_lease(self, lease_id: str) -> WorkLease:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_lease_revisions "
            "WHERE lease_id = ? ORDER BY revision DESC LIMIT 1",
            (lease_id,)).fetchone()
        if row is None:
            raise ReactiveSchedulerError("work lease is unavailable")
        return WorkLease.from_dict(json.loads(
            self._verified_body(row, "lease")))

    @staticmethod
    def _require_fence(record, lease_id: str, fencing_token: int,
                       worker_id: str | None = None) -> None:
        if (record.lease_id != lease_id
                or record.fencing_token != fencing_token):
            raise ReactiveSchedulerError(
                "stale or foreign work lease cannot change activation")
        # The fencing token proves recency, not identity: any database reader
        # can copy it from the current revision. A terminal request must also
        # come from the worker that holds the lease.
        # An empty id is a caller that did not identify itself (every
        # pre-existing caller), not a worker named nothing. The fence binds
        # to the claimant only when an id is actually supplied.
        if worker_id and worker_id != record.worker_id:
            raise ReactiveSchedulerError(
                f"terminal from worker {worker_id} for activation "
                f"{record.activation_id} claimed by worker {record.worker_id}")

    def _require_durable_history(
            self, current: ActivationRecord,
            request: ActivationTerminalRequest) -> None:
        """A DURABLE_SERIES profile makes persisted history part of COMPLETED.

        Before this check "required" history was only a per-binding worker
        flag, so a worker bound without it could publish a completed result
        for a durable series that later had nothing to reconcile against.
        """
        profile = self._profile_for(self._require_series(current.series_id))
        if (profile.persistence is PersistenceMode.DURABLE_SERIES
                and request.history_disposition
                is not ActivationHistoryDisposition.PERSISTED):
            raise DurableSeriesHistoryError(
                f"durable series {current.series_id} refuses completed "
                f"activation {current.activation_id} with history "
                f"disposition {request.history_disposition.value}; "
                "persisted history is required")

    @contextmanager
    def _revision_transaction(self, activation_id: str = ""):
        """Serialize one read-then-append of a revision against peers.

        Two connections that each read revision N and append N+1 lose a
        primary-key race. Without an explicit transaction sqlite3 leaves the
        loser inside its implicit one, so every later BEGIN IMMEDIATE fails
        with "cannot start a transaction within a transaction" and the worker
        is wedged. Taking the write lock before the read makes peers observe
        the committed revision instead; a loser that still collides rolls back
        and surfaces a typed error naming the activation.
        """
        scope = {"activation_id": activation_id}
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield scope
        except sqlite3.IntegrityError as exc:
            self._connection.rollback()
            subject = (f"activation {scope['activation_id']}"
                       if scope["activation_id"] else "scheduler record")
            raise ReactiveSchedulerError(
                f"{subject} revision was appended concurrently by a peer; "
                "reread the current record before retrying") from exc
        except BaseException:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def _require_series(self, series_id: str) -> ReactiveSeriesDefinition:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_series "
            "WHERE series_id = ?", (series_id,)).fetchone()
        if row is None:
            raise ReactiveSchedulerError("reactive series is unavailable")
        return ReactiveSeriesDefinition.from_dict(json.loads(
            self._verified_body(row, "series")))

    def _profile_for(self, series) -> ReactiveLoopProfile:
        key = (series.reactive_profile_id, series.reactive_profile_version,
               series.reactive_profile_digest)
        profile = self._profiles.get(key)
        if profile is None:
            raise ReactiveSchedulerError(
                "exact reactive profile is not registered")
        return profile

    def _pending_count(self, series_id: str) -> int:
        return sum(record.status in {
            ActivationStatus.ADMITTED, ActivationStatus.LEASED,
            ActivationStatus.RUNNING} for record in self._latest_records(
                series_id))

    def _active_count(self, series_id: str) -> int:
        return sum(record.status in {
            ActivationStatus.LEASED, ActivationStatus.RUNNING}
                   for record in self._latest_records(series_id))

    def _active_records(self) -> tuple[ActivationRecord, ...]:
        return tuple(record for record in self._latest_records()
                     if record.status in {
                         ActivationStatus.LEASED, ActivationStatus.RUNNING})

    def _latest_records(self, series_id: str = ""):
        rows = self._connection.execute(
            "WITH latest AS (SELECT activation_id, MAX(revision) AS revision "
            "FROM reactive_activation_revisions GROUP BY activation_id) "
            "SELECT r.record_digest, r.body FROM reactive_activation_revisions r "
            "JOIN latest l ON r.activation_id = l.activation_id "
            "AND r.revision = l.revision" +
            (" WHERE r.series_id = ?" if series_id else ""),
            (series_id,) if series_id else ()).fetchall()
        return tuple(ActivationRecord.from_dict(json.loads(
            self._verified_body(row, "activation"))) for row in rows)

    @staticmethod
    def _verified_body(row, label: str) -> str:
        digest, body = row
        if _digest(body) != digest:
            raise ReactiveSchedulerError(
                f"stored {label} failed digest verification")
        return body

    def close(self) -> None:
        self._connection.close()


def self_test() -> dict:
    import shutil
    import tempfile
    import threading

    from ..loop.atomic_primitives import LoopValueRef
    from ..loop.loop_definition import LoopDefinitionRef
    from ..loop.reactive_activation import ActivationHistoryRef
    from ..loop.reactive_contracts import (
        ActivationPolicy, AdmissionPolicy, EmissionPolicy, ExplorationPolicy,
        InputSchedulingPolicy, MetricDirection, OutputPortDefinition,
        PortfolioPolicy, PortfolioView, RankingDimension,
        ReactiveLivenessPolicy, RetentionPolicy, ServingPolicy, TriggerKind)

    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    definition_ref = LoopDefinitionRef("practitioner.fixture", "1.0.0", "c" * 64)

    def profile(persistence: PersistenceMode) -> ReactiveLoopProfile:
        return ReactiveLoopProfile(
            f"profile-{persistence.value}", "1.0.0",
            ActivationPolicy((TriggerKind.PUSH_EVENT,),
                             reactivation_enabled=True),
            AdmissionPolicy(1000), InputSchedulingPolicy(), persistence,
            ExplorationPolicy(),
            (OutputPortDefinition("result", "answer", "answer/v1"),),
            PortfolioPolicy(
                "policy-fixture", "1.0.0", PortfolioView.VERIFIED_TOP_K,
                (RankingDimension("evidence_coverage",
                                  MetricDirection.MAXIMIZE),), 10),
            EmissionPolicy(), ServingPolicy(10), RetentionPolicy(100, 100),
            ReactiveLivenessPolicy(30))

    def series(prof: ReactiveLoopProfile, series_id: str, attempts: int = 3,
               active: int = 1000) -> ReactiveSeriesDefinition:
        return ReactiveSeriesDefinition(
            series_id, "Self-test fixture series.", definition_ref,
            prof.profile_id, prof.version, prof.content_digest, "trigger/v1",
            ("result",), attempts, active)

    def trigger(series_id: str, index: int) -> TriggerEnvelope:
        digest = hashlib.sha256(f"{series_id}:{index}".encode()).hexdigest()
        moment = f"2026-09-07T00:{index // 60:02d}:{index % 60:02d}Z"
        return TriggerEnvelope(
            f"trigger-{series_id}-{index}", series_id, TriggerKind.PUSH_EVENT,
            f"subject-{index}",
            LoopValueRef(digest, "trigger/v1", "trigger_input",
                         "loop-source", "core.fixture.source"),
            "loop-source", moment, moment, f"dedup-{index}", 1.0)

    def open_scheduler(path: str, prof, definition) -> SQLiteReactiveScheduler:
        instance = SQLiteReactiveScheduler(path)
        instance.register_profile(prof)
        instance.register_series(definition)
        return instance

    def claim_and_start(scheduler, definition, worker: str, at: str,
                        lease_seconds: float = 60):
        claim = scheduler.claim(ActivationClaimRequest(
            worker, at, lease_seconds, definition.series_id))
        scheduler.start(ActivationStartRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, at))
        return claim

    root = tempfile.mkdtemp(prefix="reactive-scheduler-self-test-")
    try:
        durable = profile(PersistenceMode.DURABLE_SERIES)
        checkpointed = profile(PersistenceMode.CHECKPOINTED)
        durable_series = series(durable, "series-durable")
        plain_series = series(checkpointed, "series-plain")

        # W2 (direct): a lost primary-key race surfaces as a typed error
        # naming the activation, and the connection is usable afterwards.
        path = f"{root}/w2-direct.sqlite"
        scheduler = open_scheduler(path, checkpointed, plain_series)
        admitted = scheduler.admit(trigger("series-plain", 1)).activation
        collision = None
        try:
            with scheduler._revision_transaction(admitted.activation_id):
                scheduler._append_activation(admitted)
        except ReactiveSchedulerError as exc:
            collision = str(exc)
        usable = None
        try:
            usable = scheduler.claim(ActivationClaimRequest(
                "worker-one", "2026-09-07T00:10:00Z", 60,
                plain_series.series_id))
        except Exception as exc:  # any error here means the connection wedged
            usable = exc
        check("w2_lost_revision_race_raises_typed_error_and_leaves_connection_usable",
              collision is not None
              and admitted.activation_id in collision
              and not scheduler._connection.in_transaction
              and isinstance(usable, ActivationClaimResult)
              and usable.activation.activation_id == admitted.activation_id,
              f"collision={collision!r}")
        scheduler.close()

        # W2 (natural): terminal() on one connection races recover_expired()
        # on another for many rounds; nobody sees IntegrityError, nobody is
        # wedged, and every activation ends in exactly one terminal state.
        path = f"{root}/w2-race.sqlite"
        driver = open_scheduler(path, checkpointed, plain_series)
        rounds = 40
        start_gate, end_gate = threading.Barrier(3), threading.Barrier(3)
        shared: dict = {"claim": None, "errors": [], "wedged": []}

        def contender(label: str, action) -> None:
            peer = open_scheduler(path, checkpointed, plain_series)
            for _ in range(rounds):
                start_gate.wait(timeout=30)
                try:
                    action(peer, shared["claim"])
                except ReactiveSchedulerError:
                    pass  # losing the race by name is the expected outcome
                except Exception as exc:
                    shared["errors"].append((label, type(exc).__name__))
                if peer._connection.in_transaction:
                    shared["wedged"].append(label)
                end_gate.wait(timeout=30)
            peer.close()

        def finish(peer, claim) -> None:
            peer.terminal(ActivationTerminalRequest(
                claim.activation.activation_id, claim.lease.lease_id,
                claim.lease.fencing_token, ActivationStatus.COMPLETED,
                "2026-09-07T00:00:05Z", "loop-a", "ACCEPTED",
                worker_id="worker-a"))

        def recover(peer, claim) -> None:
            peer.recover_expired("2026-09-07T00:00:05Z")

        threads = (threading.Thread(target=contender, args=("terminal", finish)),
                   threading.Thread(target=contender, args=("recover", recover)))
        for thread in threads:
            thread.start()
        driven = []
        for index in range(rounds):
            admitted = driver.admit(trigger("series-plain", index + 1))
            shared["claim"] = claim_and_start(
                driver, plain_series, "worker-a", "2026-09-07T00:00:00Z", 1)
            driven.append(admitted.activation.activation_id)
            start_gate.wait(timeout=30)
            end_gate.wait(timeout=30)
        for thread in threads:
            thread.join(timeout=60)
        finals = [driver.get_activation(item).status for item in driven]
        check("w2_natural_terminal_versus_recovery_race_never_wedges_a_connection",
              not shared["errors"] and not shared["wedged"]
              and len(driven) == rounds
              and all(status.terminal for status in finals)
              and all(len([item for item in driver.activation_history(a)
                           if item.status.terminal]) == 1 for a in driven),
              f"errors={shared['errors']} wedged={shared['wedged']}")
        driver.close()

        # W4: a peer that copied lease id and fencing token from the durable
        # record still cannot publish a terminal for another worker's claim.
        path = f"{root}/w4.sqlite"
        owner = open_scheduler(path, checkpointed, plain_series)
        peer = open_scheduler(path, checkpointed, plain_series)
        admitted = owner.admit(trigger("series-plain", 1)).activation
        claim = claim_and_start(owner, plain_series, "worker-a",
                                "2026-09-07T00:00:00Z")
        leaked = peer.get_activation(admitted.activation_id)
        refusal = ""
        try:
            peer.terminal(ActivationTerminalRequest(
                leaked.activation_id, leaked.lease_id, leaked.fencing_token,
                ActivationStatus.COMPLETED, "2026-09-07T00:00:02Z",
                "loop-forged", "ACCEPTED", worker_id="worker-b"))
        except ReactiveSchedulerError as exc:
            refusal = str(exc)
        after = owner.get_activation(admitted.activation_id)
        check("w4_terminal_from_non_claimant_worker_is_refused_by_name",
              "terminal from worker worker-b" in refusal
              and "claimed by worker worker-a" in refusal
              and after.status is ActivationStatus.RUNNING
              and after.loop_id == "" and not peer._connection.in_transaction,
              refusal)
        owned = owner.terminal(ActivationTerminalRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, ActivationStatus.COMPLETED,
            "2026-09-07T00:00:03Z", "loop-a", "ACCEPTED", worker_id="worker-a"))
        check("w4_claimant_worker_still_publishes_its_own_terminal",
              owned.status is ActivationStatus.COMPLETED
              and owned.worker_id == "worker-a")
        owner.close()
        peer.close()

        # W6: a DURABLE_SERIES profile refuses COMPLETED without persisted
        # history with a typed error; a non-durable profile still accepts it;
        # the same durable series accepts COMPLETED with a bound history ref.
        path = f"{root}/w6.sqlite"
        scheduler = SQLiteReactiveScheduler(path, enforce_durable_history=True)
        scheduler.register_profile(durable)
        scheduler.register_profile(checkpointed)
        scheduler.register_series(durable_series)
        scheduler.register_series(plain_series)
        scheduler.admit(trigger("series-durable", 1))
        claim = claim_and_start(scheduler, durable_series, "worker-a",
                                "2026-09-07T00:00:00Z")
        typed = None
        try:
            scheduler.terminal(ActivationTerminalRequest(
                claim.activation.activation_id, claim.lease.lease_id,
                claim.lease.fencing_token, ActivationStatus.COMPLETED,
                "2026-09-07T00:00:02Z", "loop-a", "ACCEPTED",
                worker_id="worker-a"))
        except DurableSeriesHistoryError as exc:
            typed = exc
        still_running = scheduler.get_activation(
            claim.activation.activation_id).status is ActivationStatus.RUNNING
        check("w6_durable_series_refuses_completed_without_persisted_history",
              isinstance(typed, ReactiveSchedulerError) and still_running
              and "not_persisted" in str(typed)
              and not scheduler._connection.in_transaction,
              str(typed))
        history = ActivationHistoryRef(
            "run-one", "a" * 64, 3, claim.activation.activation_id,
            claim.activation.attempt, claim.lease.fencing_token, "loop-a",
            definition_ref, claim.activation.input_ref, "b" * 64, "d" * 64,
            "ACCEPTED", "approval-one", "e" * 64)
        completed = scheduler.terminal(ActivationTerminalRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, ActivationStatus.COMPLETED,
            "2026-09-07T00:00:03Z", "loop-a", "ACCEPTED",
            history_ref=history,
            history_disposition=ActivationHistoryDisposition.PERSISTED,
            worker_id="worker-a"))
        check("w6_durable_series_accepts_completed_with_persisted_history",
              completed.status is ActivationStatus.COMPLETED
              and completed.history_ref == history)
        scheduler.admit(trigger("series-durable", 2))
        claim = claim_and_start(scheduler, durable_series, "worker-a",
                                "2026-09-07T00:00:04Z")
        failed = scheduler.terminal(ActivationTerminalRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, ActivationStatus.FAILED,
            "2026-09-07T00:00:05Z", failure_code="HANDLER_ERROR",
            worker_id="worker-a"))
        check("w6_durable_series_history_rule_applies_only_to_completed",
              failed.status is ActivationStatus.FAILED)
        scheduler.admit(trigger("series-plain", 1))
        claim = claim_and_start(scheduler, plain_series, "worker-a",
                                "2026-09-07T00:00:06Z")
        plain = scheduler.terminal(ActivationTerminalRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, ActivationStatus.COMPLETED,
            "2026-09-07T00:00:07Z", "loop-a", "ACCEPTED", worker_id="worker-a"))
        check("w6_non_durable_profile_still_accepts_completed_without_history",
              plain.status is ActivationStatus.COMPLETED
              and plain.history_disposition
              is ActivationHistoryDisposition.NOT_PERSISTED)
        scheduler.close()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    passed = sum(item["passed"] for item in tests)
    return {"module": "loop_engine.core.reactive_scheduler", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = (
    "ActivationClaimResult", "DurableSeriesHistoryError",
    "ReactiveSchedulerError", "SQLiteReactiveScheduler",
    "TriggerAdmissionResult",
)
