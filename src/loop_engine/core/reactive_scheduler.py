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
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationRecord, ActivationStartRequest,
    ActivationStatus, ActivationTerminalRequest, LeaseHeartbeatRequest,
    ReactiveSeriesDefinition, TriggerEnvelope, WorkLease)
from ..loop.reactive_contracts import (
    InputOrdering, ReactiveLoopProfile)


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

    def __init__(self, database_path: str, observations=None) -> None:
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
        duplicate = self._find_duplicate(trigger, profile)
        if duplicate is not None:
            prior_trigger, activation = duplicate
            self._emit_trigger(prior_trigger, activation, False)
            return TriggerAdmissionResult(
                prior_trigger, activation, False, "duplicate_or_unchanged_input")
        pending = self._pending_count(series.series_id)
        if pending >= profile.admission.maximum_pending_inputs:
            raise ReactiveSchedulerError(
                "reactive series pending-input limit is reached")
        trigger_body = _canonical(trigger.to_dict())
        self._connection.execute(
            "INSERT INTO reactive_triggers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (trigger.trigger_id, trigger.series_id, trigger.subject_ref,
             trigger.input_ref.content_digest, trigger.deduplication_key,
             trigger.priority, trigger.deadline, trigger.received_at,
             _digest(trigger_body), trigger_body))
        activation = ActivationRecord(
            trigger.activation_id, trigger.series_id, trigger.trigger_id,
            trigger.input_ref, series.loop_definition_ref,
            ActivationStatus.ADMITTED, 0, 0, 0, trigger.received_at)
        self._append_activation(activation)
        self._connection.commit()
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
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            rows = self._admitted_rows(request.series_id)
            record = self._select(rows, request)
            if record is None:
                self._connection.commit()
                return None
            series = self._require_series(record.series_id)
            if self._active_count(record.series_id) >= \
                    series.maximum_active_activations:
                self._connection.commit()
                return None
            if record.attempt >= series.maximum_attempts_per_trigger:
                dead = replace(
                    record, status=ActivationStatus.DEAD_LETTER,
                    revision=record.revision + 1, terminal_at=request.as_of,
                    failure_code="ATTEMPT_BUDGET_EXHAUSTED")
                self._append_activation(dead)
                self._connection.commit()
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
                worker_id=request.worker_id)
            self._append_activation(leased)
            self._connection.commit()
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
        except Exception:
            self._connection.rollback()
            raise

    def start(self, request: ActivationStartRequest) -> ActivationRecord:
        if not isinstance(request, ActivationStartRequest):
            raise ReactiveSchedulerError(
                "start requires ActivationStartRequest")
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
        self._connection.commit()
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
        current = self._require_current(request.activation_id)
        self._require_fence(
            current, request.lease_id, request.fencing_token)
        if current.status not in {
                ActivationStatus.LEASED, ActivationStatus.RUNNING}:
            raise ReactiveSchedulerError(
                "terminal or admitted activation cannot heartbeat")
        previous = self._require_lease(request.lease_id)
        if (_instant(request.heartbeat_at) < _instant(previous.heartbeat_at)
                or _instant(request.expires_at)
                <= _instant(request.heartbeat_at)):
            raise ReactiveSchedulerError(
                "heartbeat time and expiry must move forward")
        renewed = WorkLease(
            previous.lease_id, previous.activation_id, previous.worker_id,
            previous.fencing_token, previous.acquired_at,
            request.heartbeat_at, request.expires_at)
        self._append_lease(renewed)
        self._connection.commit()
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
        current = self._require_current(request.activation_id)
        self._require_fence(
            current, request.lease_id, request.fencing_token)
        if current.status not in {
                ActivationStatus.LEASED, ActivationStatus.RUNNING}:
            raise ReactiveSchedulerError(
                "only active leased work can become terminal")
        terminal = replace(
            current, status=request.status, revision=current.revision + 1,
            loop_id=request.loop_id, terminal_at=request.terminal_at,
            terminal_code=request.terminal_code,
            failure_code=request.failure_code,
            candidate_refs=request.candidate_refs)
        self._append_activation(terminal)
        self._connection.commit()
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
        """Return expired leases to admission or dead-letter exhausted work."""
        now = _instant(as_of)
        recovered = []
        for record in self._active_records():
            lease = self._require_lease(record.lease_id)
            if _instant(lease.expires_at) > now:
                continue
            series = self._require_series(record.series_id)
            if record.attempt >= series.maximum_attempts_per_trigger:
                updated = replace(
                    record, status=ActivationStatus.DEAD_LETTER,
                    revision=record.revision + 1, terminal_at=as_of,
                    failure_code="LEASE_EXPIRED_ATTEMPTS_EXHAUSTED")
            else:
                updated = replace(
                    record, status=ActivationStatus.ADMITTED,
                    revision=record.revision + 1, lease_id="", worker_id="",
                    loop_id="", started_at="", terminal_at="",
                    terminal_code="", failure_code="", candidate_refs=())
            self._append_activation(updated)
            recovered.append(updated)
            from .runtime_observer import RuntimeObservation
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
        if recovered:
            self._connection.commit()
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
    def _require_fence(record, lease_id: str, fencing_token: int) -> None:
        if (record.lease_id != lease_id
                or record.fencing_token != fencing_token):
            raise ReactiveSchedulerError(
                "stale or foreign work lease cannot change activation")

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


__all__ = (
    "ActivationClaimResult", "ReactiveSchedulerError",
    "SQLiteReactiveScheduler", "TriggerAdmissionResult",
)
