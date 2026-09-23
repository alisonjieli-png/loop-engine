"""Removal of the service records that the published privacy notice keeps for a bounded time.

Kind: internal service mechanics over the existing catalogue authority. This
module is not an executable graph vertex and adds no store. The work it does
belongs to the Loop that owns the sign-out, to the service process that starts
the periodic task, and to the operator command that runs the removal once.

Two kinds of record are kept only for a bounded time:

```text
retention
├── service_browser_session_revocation/v1
│   ├── kept until the signed-out session would have expired
│   ├── removed when expires_at is at or before now, never earlier
│   └── a record of a version this release cannot read is left in place
└── service_waitlist_source/v2
    ├── keeps the times of accepted requests inside the counting window
    └── a record with no time left inside the window is removed
```

The removal runs in three places:

1. right after every sign-out commits, on the same service runtime;
2. from one periodic task that the HTTP application starts with its lifespan
   and cancels when it stops, every `sweep_interval_seconds`;
3. by hand, through `loop-engine service remove-expired`.

Every removal is a catalogue removal batch, `catalog_atomic_write_batch/v2`,
with an exact version precondition for each removed record. A record that
another writer changed or removed first fails that precondition, so the
removal never works from a stale read. A lost race is read again and retried
for a bounded number of rounds, then left for the next run. A report holds
outcomes and counts only. It never holds a digest, a record identity or a
tenant.

Reading comes first, without write authority. A write connection is opened
only when there is something to remove, so a run with nothing to remove writes
nothing and never creates the database file of a service that has not been set
up yet.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ...catalog.protocol import StoreError
from .records import ServiceRuntimeError
from .runtime import SCHEMAS, SESSION_REVOCATION

RETENTION_POLICY_VERSION = "service_retention_policy/v1"
RETENTION_REPORT_VERSION = "service_retention_report/v1"
#: The default schedule: one run every ten minutes.
DEFAULT_SWEEP_INTERVAL_SECONDS = 600
#: At least one second between runs, so the task can never spin.
SHORTEST_SWEEP_INTERVAL_SECONDS = 1
#: At most one hour between runs, so a record outlives its promised time by at
#: most one hour even when nobody signs out and nobody joins the waiting list.
LONGEST_SWEEP_INTERVAL_SECONDS = 3600
#: Removals committed in one batch. A long outage can leave many expired
#: records; they are removed in batches of this size, each its own transaction.
REMOVALS_IN_ONE_BATCH = 500
#: How many times one run reads again after another writer won a race.
SWEEP_ROUNDS = 3
#: What one run of one kind of record ended with.
COMPLETED, INCOMPLETE, FAILED, NOT_RUN = "completed", "incomplete", "failed", "not_run"
CONCURRENT_UPDATE = "concurrent_update"
#: The part names of a report, one for each kind of record.
REVOCATION_PART, WAITLIST_PART = "browser_session_revocations", "waitlist_sources"
#: What the sweep may do with one revocation record.
EXPIRED, UNEXPIRED, UNRECOGNIZED = "expired", "unexpired", "unrecognized"
#: The code of a store failure that carries no code of its own.
STORE_FAILURE_CODE = "store_unavailable"
#: The name of the reported health check, and the codes it carries before a
#: run has finished and when no task runs at all.
READINESS_CHECK_NAME = "retention_sweep_current"
NOT_RUN_YET_CODE = "retention_sweep_not_run_yet"
NOT_RUNNING_CODE = "retention_sweep_not_running"
SWEEP_FAILED_CODE = "retention_sweep_failed"


@dataclass(frozen=True)
class ServiceRetentionPolicy:
    """How often one service process removes the records whose time has passed.

    There is no setting that switches the removal off. The published privacy
    notice promises it, so a host chooses only how often the periodic task
    runs, from one second to one hour. A sign-out removes expired revocations
    whatever this says.
    """

    sweep_interval_seconds: int = DEFAULT_SWEEP_INTERVAL_SECONDS
    record_type: str = RETENTION_POLICY_VERSION

    def __post_init__(self):
        if self.record_type != RETENTION_POLICY_VERSION:
            raise ServiceRuntimeError("unsupported_retention_policy")
        interval = self.sweep_interval_seconds
        if (type(interval) is not int
                or not SHORTEST_SWEEP_INTERVAL_SECONDS <= interval <= LONGEST_SWEEP_INTERVAL_SECONDS):
            raise ServiceRuntimeError("invalid_retention_policy",
                                      "the sweep interval is a whole number of seconds from 1 to 3600")


def _revocation_state(row, now):
    """Say whether one revocation may be removed now, must be kept, or cannot be read.

    Only a record of the version this release writes, with a whole-second
    expiry, is ever removed, and only when that expiry is at or before now. A
    record of another version is left in place: its expiry may not mean what
    this release would read into it, and removing a revocation early would let
    a signed-out session back in.
    """
    payload = row.get("payload")
    if (not isinstance(payload, dict) or payload.get("record_type") != SCHEMAS[SESSION_REVOCATION]
            or type(payload.get("expires_at")) is not int):
        return UNRECOGNIZED
    return EXPIRED if payload["expires_at"] <= now else UNEXPIRED


def _tally(rows, now):
    tally = {EXPIRED: [], UNEXPIRED: 0, UNRECOGNIZED: 0}
    for row in rows:
        state = _revocation_state(row, now)
        if state == EXPIRED:
            tally[EXPIRED].append(row)
        else:
            tally[state] += 1
    return tally


def _revocation_report(outcome, removed, tally):
    return {"outcome": outcome, "removed": removed, "kept_unexpired": tally[UNEXPIRED],
            "kept_unrecognized": tally[UNRECOGNIZED]}


def remove_expired_session_revocations(runtime):
    """Remove every browser session revocation whose session has expired, and nothing else.

    The expiry is compared with the runtime clock at the moment of each read.
    A revocation whose `expires_at` is at or before that moment is removed in
    a removal batch guarded by its exact version; every other revocation is
    kept. A concurrent sign-out writes a new record, which no removal names,
    so it never conflicts with this run.
    """
    catalog = runtime._catalog
    with catalog.store() as reader:
        tally = _tally(catalog.rows_all(reader, SESSION_REVOCATION), runtime._now())
    if not tally[EXPIRED]:
        return _revocation_report(COMPLETED, 0, tally)
    removed = 0
    with catalog.store(write=True) as store:
        for _round in range(SWEEP_ROUNDS):
            tally = _tally(catalog.rows_all(store, SESSION_REVOCATION), runtime._now())
            expired = tally[EXPIRED]
            try:
                for start in range(0, len(expired), REMOVALS_IN_ONE_BATCH):
                    chunk = expired[start:start + REMOVALS_IN_ONE_BATCH]
                    catalog.commit(store, (), tuple(catalog.guard(row) for row in chunk),
                                   tuple(row["record_id"] for row in chunk))
                    removed += len(chunk)
            except ServiceRuntimeError as error:
                if error.code != CONCURRENT_UPDATE:
                    raise
                continue
            return _revocation_report(COMPLETED, removed, tally)
    return _revocation_report(CONCURRENT_UPDATE, removed, tally)


def sweep_after_sign_out(runtime):
    """The removal that follows every sign-out, right after its own write commits.

    The sign-out is already durable when this runs. A failure here changes
    nothing about the sign-out or its answer: it is returned to the caller,
    which does not show it to the person signing out, and the periodic task
    and the next sign-out remove the same records again.
    """
    try:
        return remove_expired_session_revocations(runtime)
    except (ServiceRuntimeError, StoreError) as error:
        return {"outcome": FAILED, "code": getattr(error, "code", STORE_FAILURE_CODE)}


def remove_expired_waitlist_sources(runtime, waitlist=None):
    """Remove the times that have left the waiting list window, and every source record left with none.

    An installed waiting list names its own window. Without one, the longest
    window the privacy notice allows, one hour, is used, so a host that stopped
    serving the list still removes what the list kept.
    """
    from .waitlist import LONGEST_SOURCE_WINDOW_SECONDS, SOURCE, forget_expired_sources, plan_source_sweep
    window = waitlist.policy.source_window_seconds if waitlist is not None else LONGEST_SOURCE_WINDOW_SECONDS
    catalog = runtime._catalog
    with catalog.store() as reader:
        trimmed, removed = plan_source_sweep(catalog.rows_all(reader, SOURCE), runtime._now(), window)
    if not (trimmed or removed):
        return {"outcome": COMPLETED, "trimmed": 0, "removed": 0}
    with catalog.store(write=True) as store:
        for _round in range(SWEEP_ROUNDS):
            try:
                counts = forget_expired_sources(catalog, store, runtime._now(), window)
            except ServiceRuntimeError as error:
                if error.code != CONCURRENT_UPDATE:
                    raise
                continue
            return {"outcome": COMPLETED, **counts}
    return {"outcome": CONCURRENT_UPDATE, "trimmed": 0, "removed": 0}


def sweep_retention(runtime, *, waitlist=None):
    """Run every retention removal once and report outcomes and counts only.

    Each kind of record is removed on its own, so a failure with one kind does
    not stop the other. The report names the failure by its code and nothing
    else.
    """
    report = {"record_type": RETENTION_REPORT_VERSION}
    for name, part in ((REVOCATION_PART, lambda: remove_expired_session_revocations(runtime)),
                       (WAITLIST_PART, lambda: remove_expired_waitlist_sources(runtime, waitlist))):
        try:
            report[name] = part()
        except (ServiceRuntimeError, StoreError) as error:
            report[name] = {"outcome": FAILED, "code": getattr(error, "code", STORE_FAILURE_CODE)}
    report["outcome"] = (COMPLETED if all(report[name]["outcome"] == COMPLETED
                                          for name in (REVOCATION_PART, WAITLIST_PART)) else INCOMPLETE)
    return report


def _unfinished_code(report):
    """The code that names why a run did not complete, read from its report."""
    if not isinstance(report, dict):
        return SWEEP_FAILED_CODE
    for part in (report.get(REVOCATION_PART), report.get(WAITLIST_PART), report):
        if isinstance(part, dict) and part.get("outcome") not in (COMPLETED, INCOMPLETE):
            return part.get("code") or part.get("outcome") or SWEEP_FAILED_CODE
    return SWEEP_FAILED_CODE


class RetentionSchedule:
    """The one periodic retention task of a service process.

    The host application starts it inside its lifespan and cancels it when the
    service stops. It runs one removal soon after start and then one each
    interval, on the default executor, never on the bounded customer worker
    pool. A run that fails is recorded as the last outcome and the task keeps
    its schedule: it ends only when it is cancelled. A service without host
    write authority starts no task, because it could remove nothing.

    The health answer reads the last outcome from memory. Asking for health
    never runs a removal and never writes.
    """

    def __init__(self, runtime, policy=None, *, waitlist=None, sweep=None):
        policy = ServiceRetentionPolicy() if policy is None else policy
        if not isinstance(policy, ServiceRetentionPolicy) or (sweep is not None and not callable(sweep)):
            raise ServiceRuntimeError("invalid_retention_policy")
        self.runtime, self.policy = runtime, policy
        self._sweep = sweep if sweep is not None else (lambda: sweep_retention(runtime, waitlist=waitlist))
        self.finished_sweeps, self.last_outcome, self.last_code = 0, NOT_RUN, ""
        self._task = None

    @property
    def running(self):
        return self._task is not None and not self._task.done()

    def start(self):
        """Start the task in the running event loop, once. Returns the task, or None when none can run."""
        if self._task is None and self.runtime.config.writes_authorized is True:
            self._task = asyncio.get_running_loop().create_task(self._run())
        return self._task

    async def _run(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                report = await loop.run_in_executor(None, self._sweep)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                report = {"outcome": FAILED, "code": getattr(error, "code", SWEEP_FAILED_CODE)}
            self._finished(report)
            await asyncio.sleep(self.policy.sweep_interval_seconds)

    def _finished(self, report):
        self.finished_sweeps += 1
        completed = isinstance(report, dict) and report.get("outcome") == COMPLETED
        self.last_outcome = COMPLETED if completed else (
            report.get("outcome", FAILED) if isinstance(report, dict) else FAILED)
        self.last_code = "" if completed else _unfinished_code(report)

    async def stop(self):
        """Cancel the task and wait for it to end. A removal already running finishes its own transaction.

        Stopping never fails the shutdown it belongs to: a task that already
        ended with an error has nothing left to stop.
        """
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    def readiness_check(self):
        """The last outcome as a reported health check that is never required."""
        from .observability import ReadinessCheck
        if not self.running:
            return ReadinessCheck(READINESS_CHECK_NAME, False, False, NOT_RUNNING_CODE)
        if self.finished_sweeps == 0:
            return ReadinessCheck(READINESS_CHECK_NAME, False, False, NOT_RUN_YET_CODE)
        passed = self.last_outcome == COMPLETED
        return ReadinessCheck(READINESS_CHECK_NAME, False, passed, "" if passed else self.last_code)
