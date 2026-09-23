"""Retention checks: records the privacy notice keeps for a bounded time are removed on time, never early.

Every check runs over real SQLite records. The periodic task is checked inside
a real loopback service that starts and stops, and the operator command is run
through the real service entry point. Each guard has a named check and a
known-wrong case beside it: the same situation with that one guard patched
away, which shows the guard is what holds. No identity provider, payment
provider or other external service is contacted.
"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
from dataclasses import replace
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import time
from unittest.mock import patch

from ...catalog.protocol import (ATOMIC_REMOVAL_OPERATION, CatalogBatchAcknowledgment, CatalogWriteBatch,
                                 StoreError)
from ...catalog.stores.sqlite_store import SQLiteRecordStore
from . import retention, storage
from .access import ServiceAccessAdministration
from .access_checks import customer_prepared
from .http import ServiceHttpApplication, ServiceHttpConfiguration
from .http_test_fixtures import HttpDomainFixture, running_http
from .provisioning import DurableProvisioningBinding
from .records import ServiceCommitUnknown, ServiceRuntimeError
from .retention import (COMPLETED, EXPIRED, FAILED, READINESS_CHECK_NAME, RetentionSchedule,
                        ServiceRetentionPolicy, remove_expired_session_revocations, sweep_retention)
from .runtime import SCHEMAS, SESSION_REVOCATION, ServiceRuntime
from .storage import ServiceCatalogBinding

#: A whole digest or a service record identity in printed text. A retention
#: report may hold neither, because either one names a person's session.
_DISCLOSING = re.compile(r"[0-9a-f]{64}|service:")


class _Clock:
    """A runtime clock the check moves by hand."""

    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


def _digest(name):
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _folder(path):
    """Create one fixture folder and return it; each fixture owns its own store."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _attempt(function):
    """Return `(value, None)`, or `(None, the error)`, so one check can report a refusal by name."""
    try:
        return function(), None
    except Exception as error:
        return None, error


def refused(function, *codes):
    try:
        function()
    except ServiceRuntimeError as error:
        return not codes or error.code in codes
    return False


def _held(runtime, credential_digest):
    """The stored revocation of one session, as the store holds it, or None."""
    catalog = runtime._catalog
    with catalog.store() as store:
        return catalog.read(store, SESSION_REVOCATION, credential_digest)


def _plant(runtime, credential_digest, payload):
    """Write one revocation directly, the way an earlier release or a stale write would have left it."""
    catalog = runtime._catalog
    row = catalog.record(SESSION_REVOCATION, credential_digest, payload, tenant_id="alpha")
    with catalog.store(write=True) as store:
        catalog.commit(store, (row,), (catalog.guard(None, row["record_id"]),))
    return row


def _expired(runtime, name, seconds_ago=5):
    """Plant a revocation of the current version whose session expired a moment ago."""
    credential = _digest(name)
    _plant(runtime, credential, {"record_type": SCHEMAS[SESSION_REVOCATION], "tenant_id": "alpha",
                                 "credential_digest": credential,
                                 "expires_at": int(runtime._now()) - seconds_ago})
    return credential


def _signed_in(root):
    """One customer sign-in over real records, with a runtime clock the check controls."""
    fixture = customer_prepared(_folder(root))
    fixture.clock = _Clock(int(time.time()))
    fixture.runtime._clock = fixture.clock
    fixture.principal = fixture.customers["customer-a"]
    return fixture


def session_checks(check, root):
    """A revocation is removed when its session has expired, and not one second before."""
    fixture = _signed_in(root / "sessions")
    runtime, clock, principal = fixture.runtime, fixture.clock, fixture.principal
    first, second = _digest("first session"), _digest("second session")
    start = clock.value
    runtime.revoke_browser_session(principal, first, start + 100)
    runtime.revoke_browser_session(principal, second, start + 200)
    clock.value = start + 99
    early = remove_expired_session_revocations(runtime)
    check("a_revocation_is_kept_until_the_moment_its_session_expires",
          early["removed"] == 0 and early["kept_unexpired"] == 2 and runtime.browser_session_revoked(first))
    clock.value = start + 100
    swept = remove_expired_session_revocations(runtime)
    check("an_expired_session_revocation_is_removed_by_the_sweep",
          swept["outcome"] == COMPLETED and swept["removed"] == 1 and _held(runtime, first) is None)
    check("a_revocation_whose_session_has_not_expired_is_kept_and_still_refuses_the_session",
          swept["kept_unexpired"] == 1 and _held(runtime, second) is not None
          and runtime.browser_session_revoked(second))
    # Known-wrong cases: a sweep that never finds anything expired leaves the
    # expired record, and a sweep that ignores the expiry removes a live one.
    idle = _signed_in(root / "idle")
    idle.runtime.revoke_browser_session(idle.principal, first, idle.clock.value + 100)
    idle.clock.value += 100
    with patch.object(retention, "_revocation_state", lambda row, now: retention.UNEXPIRED):
        remove_expired_session_revocations(idle.runtime)
    check("KNOWN_WRONG_a_sweep_that_finds_nothing_expired_leaves_the_expired_revocation",
          _held(idle.runtime, first) is not None)
    eager = _signed_in(root / "eager")
    eager.runtime.revoke_browser_session(eager.principal, second, eager.clock.value + 200)
    with patch.object(retention, "_revocation_state", lambda row, now: EXPIRED):
        remove_expired_session_revocations(eager.runtime)
    check("KNOWN_WRONG_a_sweep_that_ignores_the_expiry_lets_a_signed_out_session_back_in",
          not eager.runtime.browser_session_revoked(second))

    # A record of a version this release does not write is never removed.
    future = _digest("future version")
    _plant(runtime, future, {"record_type": SESSION_REVOCATION + "/v2", "tenant_id": "alpha",
                             "credential_digest": future, "expires_at": int(clock.value) - 50})
    unread = remove_expired_session_revocations(runtime)
    check("a_revocation_of_a_version_this_release_cannot_read_is_left_in_place",
          unread["kept_unrecognized"] == 1 and _held(runtime, future) is not None)


def sign_out_checks(check, root):
    """Every sign-out removes the revocations whose sessions have expired, and answers the same whatever happens."""
    fixture = _signed_in(root / "sign-out")
    runtime, clock, principal = fixture.runtime, fixture.clock, fixture.principal
    old, new = _digest("old session"), _digest("new session")
    runtime.revoke_browser_session(principal, old, clock.value + 10)
    clock.value += 10
    answer = runtime.revoke_browser_session(principal, new, clock.value + 600)
    check("every_sign_out_removes_the_expired_revocations",
          answer == {"committed": True, "revoked": True}
          and _held(runtime, old) is None and _held(runtime, new) is not None)
    kept = _signed_in(root / "sign-out-kept")
    kept.runtime.revoke_browser_session(kept.principal, old, kept.clock.value + 10)
    kept.clock.value += 10
    with patch.object(retention, "sweep_after_sign_out", lambda runtime: None):
        kept.runtime.revoke_browser_session(kept.principal, new, kept.clock.value + 600)
    check("KNOWN_WRONG_a_sign_out_without_its_removal_leaves_the_expired_revocation",
          _held(kept.runtime, old) is not None)

    # The sign-out is durable before the removal runs, so a failed removal
    # changes nothing about the sign-out's answer.
    def lost(runtime):
        raise ServiceCommitUnknown()
    third = _digest("third session")
    with patch.object(retention, "remove_expired_session_revocations", lost):
        answer, problem = _attempt(lambda: runtime.revoke_browser_session(principal, third, clock.value + 600))
    check("a_sign_out_answers_the_same_when_the_removal_after_it_fails",
          problem is None and answer == {"committed": True, "revoked": True}
          and runtime.browser_session_revoked(third))
    fourth = _digest("fourth session")
    with patch.object(retention, "remove_expired_session_revocations", lost), \
            patch.object(retention, "sweep_after_sign_out", lambda runtime: retention.remove_expired_session_revocations(runtime)):
        check("KNOWN_WRONG_a_removal_failure_that_escapes_turns_a_committed_sign_out_into_an_error",
              refused(lambda: runtime.revoke_browser_session(principal, fourth, clock.value + 600), "commit_unknown")
              and runtime.browser_session_revoked(fourth))


def concurrency_checks(check, root):
    """A run that loses a race to another run reads again; a concurrent sign-out is never removed."""
    def raced(folder, rounds):
        fixture = _signed_in(folder)
        runtime, clock, principal = fixture.runtime, fixture.clock, fixture.principal
        stale, late = _digest("stale session"), _digest("late session")
        runtime.revoke_browser_session(principal, stale, clock.value + 10)
        clock.value += 10
        original, raced_once = ServiceCatalogBinding.commit, []

        def racing(binding, store, records, guards, removals=()):
            if removals and not raced_once:
                raced_once.append(True)
                # Another run removes the same record first, and another
                # person signs out, between this run's read and its write.
                remove_expired_session_revocations(runtime)
                runtime.revoke_browser_session(principal, late, clock.value + 600)
            return original(binding, store, records, guards, removals)
        with patch.object(ServiceCatalogBinding, "commit", racing), patch.object(retention, "SWEEP_ROUNDS", rounds):
            outcome = remove_expired_session_revocations(runtime)
        return outcome, _held(runtime, stale), _held(runtime, late), raced_once
    outcome, stale_row, late_row, happened = raced(root / "race", retention.SWEEP_ROUNDS)
    check("a_run_that_loses_a_race_reads_again_and_keeps_the_concurrent_sign_out",
          happened and outcome["outcome"] == COMPLETED and stale_row is None and late_row is not None)
    outcome, _stale, late_row, happened = raced(root / "race-once", 1)
    check("KNOWN_WRONG_without_a_second_read_a_lost_race_ends_the_run_incomplete",
          happened and outcome["outcome"] == retention.CONCURRENT_UPDATE and late_row is not None)


class _Delegating:
    """A store that answers as the real SQLite store does, except where a check says otherwise."""

    def __init__(self, inner):
        self.inner, self.batches = inner, []

    def __getattr__(self, name):
        return getattr(self.inner, name)


class _WritesOnly(_Delegating):
    """An adapter that declares atomic writes and not removal, and would drop a removal it was handed."""

    def capabilities(self):
        declared = self.inner.capabilities()
        return replace(declared,
                       operations={name: value for name, value in declared.operations.items()
                                   if name != ATOMIC_REMOVAL_OPERATION},
                       transactions={name: value for name, value in declared.transactions.items()
                                     if name != "atomic_removal_batch_version"})

    def apply_batch(self, request):
        self.batches.append(request)
        return CatalogBatchAcknowledgment(request.digest, True)


class _OtherRemovals(_Delegating):
    """An adapter that applies the batch and acknowledges a batch that removes something else."""

    def apply_batch(self, request):
        self.batches.append(request)
        self.inner.apply_batch(request)
        other = tuple(guard.record_id for guard in request.preconditions if guard.record_id not in request.removals)
        return CatalogBatchAcknowledgment(CatalogWriteBatch.from_records(
            request.records, request.preconditions, other).digest, True)


class _RemovesNothing(_Delegating):
    """An adapter that declares removal, acknowledges the exact batch, and removes nothing."""

    def apply_batch(self, request):
        self.batches.append(request)
        return CatalogBatchAcknowledgment(request.digest, True)


def _binding_over(fixture, adapter):
    """A service binding whose store is the real SQLite file behind one stand-in adapter."""
    held = []

    def opener(write):
        store = adapter(SQLiteRecordStore(fixture.runtime.config.database_path, read_only=not write))
        held.append(store)
        return store
    return ServiceCatalogBinding(fixture.runtime.config, opener), held


def binding_checks(check, root):
    """A removal reaches only a store that declares it, and only an exact acknowledgment counts."""
    fixture = HttpDomainFixture(_folder(root / "binding"))
    first, second = _expired(fixture.runtime, "binding one"), _expired(fixture.runtime, "binding two")

    def remove(binding, targets, guarded=()):
        with binding.store(write=True) as store:
            rows = [binding.read(store, SESSION_REVOCATION, target) for target in (*targets, *guarded)]
            binding.commit(store, (), tuple(binding.guard(row) for row in rows),
                           removals=tuple(row["record_id"] for row in rows[:len(targets)]))

    def attempt(adapter, targets, guarded=()):
        binding, stores = _binding_over(fixture, adapter)
        try:
            remove(binding, targets, guarded)
            code = None
        except ServiceRuntimeError as error:
            code = error.code
        return code, sum(len(store.batches) for store in stores)

    code, sent = attempt(_WritesOnly, (first,))
    check("a_removal_is_refused_before_any_effect_by_a_store_that_does_not_declare_it",
          code == "store_contract_unavailable" and sent == 0 and _held(fixture.runtime, first) is not None)
    with patch.object(storage, "require_atomic_removal", lambda store: None):
        code, sent = attempt(_WritesOnly, (first,))
    check("KNOWN_WRONG_without_the_negotiation_an_undeclared_store_is_handed_the_removal",
          sent == 1 and code != "store_contract_unavailable")

    code, _sent = attempt(_OtherRemovals, (first,), (second,))
    check("an_acknowledgment_for_a_batch_that_removes_something_else_is_an_unknown_commit",
          code == "commit_unknown")
    third, fourth = _expired(fixture.runtime, "binding three"), _expired(fixture.runtime, "binding four")
    unbound = property(lambda batch: hashlib.sha256(json.dumps(
        [batch.record_type, list(batch.record_documents),
         [(row.record_id, row.record_version, row.must_not_exist) for row in batch.preconditions]]).encode()).hexdigest())
    with patch.object(CatalogWriteBatch, "digest", unbound):
        code, _sent = attempt(_OtherRemovals, (third,), (fourth,))
    check("KNOWN_WRONG_a_digest_that_omits_removals_accepts_an_acknowledgment_for_another_batch",
          code is None)

    fifth = _expired(fixture.runtime, "binding five")
    code, sent = attempt(_RemovesNothing, (fifth,))
    check("a_store_that_acknowledges_a_removal_it_did_not_make_is_an_unknown_commit",
          code == "commit_unknown" and sent == 1 and _held(fixture.runtime, fifth) is not None)
    with patch.object(storage, "_no_longer_held", lambda row, version: True):
        code, _sent = attempt(_RemovesNothing, (fifth,))
    check("KNOWN_WRONG_without_reading_the_removal_back_an_unmade_removal_is_reported_as_committed",
          code is None and _held(fixture.runtime, fifth) is not None)


def access_order_checks(check, root):
    """A customer session is refused when its revocation is removed while it is being checked.

    The removal runs when the session expires. The expiry is read after the
    revocation, so a session whose revocation disappeared between the two reads
    is already past its expiry by the second one.
    """
    def scenario(folder, administration_type):
        fixture = _signed_in(folder)
        runtime, clock, principal = fixture.runtime, fixture.clock, fixture.principal
        session = replace(fixture.customer_sessions["customer-a"], expires_at=clock.value + 100)
        runtime.revoke_browser_session(principal, session.credential_digest, clock.value + 100)
        service = administration_type(runtime, fixture.client_access.policy)
        original = ServiceCatalogBinding.read

        def removed_while_read(binding, store, kind, logical_identity):
            if kind == SESSION_REVOCATION:
                clock.value = session.expires_at
                remove_expired_session_revocations(runtime)
            return original(binding, store, kind, logical_identity)
        with patch.object(ServiceCatalogBinding, "read", removed_while_read):
            return refused(lambda: service.inspect(principal, session=session), "unauthorized")
    check("a_client_access_session_whose_revocation_is_removed_while_it_is_checked_is_still_refused",
          scenario(root / "order", ServiceAccessAdministration))
    check("KNOWN_WRONG_reading_the_expiry_before_the_revocation_lets_that_client_access_session_through",
          not scenario(root / "order-wrong", _ExpiryReadFirst))


class _ExpiryReadFirst(ServiceAccessAdministration):
    """The earlier order: the session expiry first, then its revocation."""

    def _customer_authorize(self, store, principal, session):
        current, guards = self.runtime._revalidate(store, principal)
        if session.expires_at <= self.runtime._now():
            raise ServiceRuntimeError("unauthorized")
        catalog = self.runtime._catalog
        if catalog.read(store, SESSION_REVOCATION, session.credential_digest) is not None:
            raise ServiceRuntimeError("unauthorized")
        return current, (*guards, catalog.guard(None, catalog.identity(SESSION_REVOCATION, session.credential_digest)))


def _wait(condition, seconds=10.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def schedule_checks(check, root):
    """The periodic task starts with the service, removes on its schedule, survives a failure and stops with it."""
    fixture = HttpDomainFixture(_folder(root / "schedule"))
    before_start = _expired(fixture.runtime, "expired before start")

    def application(configuration):
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                                      retention=ServiceRetentionPolicy(sweep_interval_seconds=1))
    with running_http(fixture, application_factory=application) as (_base, service):
        schedule = service.retention_schedule
        started = _wait(lambda: schedule.finished_sweeps >= 1)
        check("the_retention_task_starts_with_the_service_and_removes_what_has_expired",
              started and schedule.running and _held(fixture.runtime, before_start) is None)
        after_start = _expired(fixture.runtime, "expired after start")
        check("the_retention_task_removes_again_on_its_schedule",
              _wait(lambda: schedule.finished_sweeps >= 3) and _held(fixture.runtime, after_start) is None
              and schedule.last_outcome == COMPLETED)

    # The lifespan itself must end the task. It is run here in an event loop
    # that keeps running afterwards, because a server that closes its loop
    # would cancel a forgotten task anyway and hide the missing stop.
    async def cycle(service):
        app = service.create_app()
        async with app.router.lifespan_context(app):
            for _ in range(500):
                if service.retention_schedule.finished_sweeps >= 1:
                    break
                await asyncio.sleep(0.01)
            task = service.retention_schedule._task
        ended = task is not None and task.done()
        if task is not None and not task.done():
            task.cancel()
        return task, ended
    served = application(ServiceHttpConfiguration("http://127.0.0.1:8765", ("127.0.0.1:8765",),
                                                  allow_loopback_http=True))
    task, ended = asyncio.run(cycle(served))
    check("the_retention_task_is_cancelled_when_the_service_stops",
          ended and task.cancelled() and not served.retention_schedule.running)

    # A run that fails is recorded, and the task keeps its schedule.
    calls = []

    def flaky():
        calls.append(True)
        if len(calls) == 1:
            raise ServiceRuntimeError("store_unavailable")
        return sweep_retention(fixture.runtime)

    def failing_application(configuration):
        service = application(configuration)
        service.retention_schedule = RetentionSchedule(fixture.runtime, service.retention, sweep=flaky)
        return service
    with running_http(fixture, application_factory=failing_application) as (_base, service):
        schedule = service.retention_schedule
        recovered = _wait(lambda: schedule.finished_sweeps >= 2)
        check("a_failed_run_is_recorded_and_the_retention_task_keeps_its_schedule",
              recovered and schedule.running and schedule.last_outcome == COMPLETED and len(calls) >= 2)

    class _Unguarded(RetentionSchedule):
        async def _run(self):
            loop = asyncio.get_running_loop()
            while True:
                self._finished(await loop.run_in_executor(None, self._sweep))
                await asyncio.sleep(self.policy.sweep_interval_seconds)
    calls.clear()

    def unguarded_application(configuration):
        service = application(configuration)
        service.retention_schedule = _Unguarded(fixture.runtime, service.retention, sweep=flaky)
        return service
    with running_http(fixture, application_factory=unguarded_application) as (_base, service):
        schedule = service.retention_schedule
        _wait(lambda: schedule._task is not None and schedule._task.done(), 3.0)
        check("KNOWN_WRONG_a_task_that_does_not_catch_a_failed_run_ends_on_the_first_failure",
              not schedule.running and schedule.finished_sweeps == 0)

    # A service without host write authority can remove nothing, so it starts
    # no task, and its health answer says so without being made unready.
    read_only = ServiceRuntime(replace(fixture.runtime.config, writes_authorized=False))
    provisioning = DurableProvisioningBinding(read_only, fixture.catalogue,
                                              fixture.provisioning.qualification_resolver,
                                              fixture.provisioning.body_reader)
    with running_http(fixture, application_factory=lambda configuration: ServiceHttpApplication(
            read_only, provisioning, configuration)) as (base, service):
        import httpx
        health = httpx.get(base + "/api/v1/health", trust_env=False, timeout=5).json()["result"]
        reported = next((row for row in health["checks"] if row["name"] == READINESS_CHECK_NAME), None)
        check("a_service_without_write_authority_starts_no_retention_task_and_says_so",
              service.retention_schedule._task is None and reported is not None
              and reported["required"] is False and reported["passed"] is False
              and reported["code"] == retention.NOT_RUNNING_CODE)


def health_checks(check, root):
    """Asking for health reads the last outcome from memory. It never runs a removal and never writes."""
    fixture = HttpDomainFixture(_folder(root / "health"))

    def application(configuration):
        return ServiceHttpApplication(fixture.runtime, fixture.provisioning, configuration,
                                      retention=ServiceRetentionPolicy(sweep_interval_seconds=3600))

    def observed(patched=None):
        with running_http(fixture, application_factory=application) as (base, service):
            import httpx
            _wait(lambda: service.retention_schedule.finished_sweeps >= 1)
            planted = _expired(fixture.runtime, "planted " + str(time.monotonic()))
            before = Path(fixture.runtime.config.database_path).read_bytes()
            context = patch.object(ServiceHttpApplication, "_readiness", patched) if patched else _Nothing()
            with context:
                answers = [httpx.get(base + "/api/v1/health", trust_env=False, timeout=5) for _ in range(3)]
            after = Path(fixture.runtime.config.database_path).read_bytes()
            return answers, before == after, _held(fixture.runtime, planted) is not None
    answers, unchanged, still_held = observed()
    last = answers[-1].json()["result"]
    reported = next((row for row in last["checks"] if row["name"] == READINESS_CHECK_NAME), None)
    check("asking_for_health_never_runs_a_removal_and_never_writes",
          all(answer.status_code == 200 for answer in answers) and unchanged and still_held)
    check("the_health_answer_reports_the_retention_task_without_requiring_it",
          reported is not None and reported["required"] is False and reported["passed"] is True
          and last["ready"] is True)
    original = ServiceHttpApplication._readiness

    async def sweeping(self):
        await asyncio.get_running_loop().run_in_executor(None, lambda: sweep_retention(self.runtime))
        return await original(self)
    _answers, unchanged, still_held = observed(sweeping)
    check("KNOWN_WRONG_a_health_answer_that_runs_the_removal_writes_and_removes",
          not unchanged and not still_held)


class _Nothing:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def command_checks(check, root):
    """The operator command runs the removal once and prints outcomes and counts, never a digest."""
    from .http_entrypoint import main
    from .waitlist import SOURCE, SOURCE_SCHEMA
    fixture = HttpDomainFixture(_folder(root / "command"))
    runtime = fixture.runtime
    expired = _expired(runtime, "command expired")
    live = _digest("command live")
    _plant(runtime, live, {"record_type": SCHEMAS[SESSION_REVOCATION], "tenant_id": "alpha",
                           "credential_digest": live, "expires_at": int(time.time()) + 600})
    catalog = runtime._catalog
    source = catalog.record(SOURCE, _digest("command source"), {
        "record_type": SOURCE_SCHEMA, "accepted": [time.time() - 7200], "window_seconds": 3600})
    with catalog.store(write=True) as store:
        catalog.commit(store, (source,), (catalog.guard(None, source["record_id"]),))
    host = root / "command" / "host.json"
    host.write_text(json.dumps({"record_type": "service_http_host_configuration/v1",
                                "runtime": {"database_path": runtime.config.database_path,
                                            "writes_authorized": True}}))
    printed = StringIO()
    with redirect_stdout(printed):
        status = main(["remove-expired", "--config", str(host)])
    text = printed.getvalue()
    report = json.loads(text)
    check("the_remove_expired_command_removes_what_has_expired_and_nothing_else",
          status == 0 and report["outcome"] == COMPLETED
          and report["browser_session_revocations"]["removed"] == 1
          and report["browser_session_revocations"]["kept_unexpired"] == 1
          and report["waitlist_sources"]["removed"] == 1
          and _held(runtime, expired) is None and _held(runtime, live) is not None)
    check("the_remove_expired_command_prints_counts_and_no_digest_or_identity",
          not _DISCLOSING.search(text) and "alpha" not in text)
    check("KNOWN_WRONG_a_report_that_names_what_it_removed_is_found",
          bool(_DISCLOSING.search(json.dumps({**report, "removed_records": [source["record_id"]]}))))
    failing = StringIO()
    with patch.object(retention, "remove_expired_session_revocations",
                      lambda runtime: (_ for _ in ()).throw(StoreError("fixture"))), redirect_stdout(failing):
        failed_status = main(["remove-expired", "--config", str(host)])
    failed = json.loads(failing.getvalue())
    check("a_run_that_cannot_finish_says_which_part_failed_and_exits_with_failure",
          failed_status == 1 and failed["browser_session_revocations"] == {"outcome": FAILED,
                                                                           "code": "store_unavailable"})


def run_checks(check, root):
    """Run every retention check group, each in its own folder under `root`."""
    for name, function in (("sessions", session_checks), ("sign_out", sign_out_checks),
                           ("concurrency", concurrency_checks), ("binding", binding_checks),
                           ("access", access_order_checks), ("schedule", schedule_checks),
                           ("health", health_checks), ("command", command_checks)):
        folder = Path(root) / name
        folder.mkdir(parents=True, exist_ok=True)
        try:
            function(check, folder)
        except Exception as error:
            # A group that stops part way is a failure with a name, so a
            # missing guard is reported as such instead of ending the run.
            check(f"the_retention_{name}_checks_ran_to_completion:{type(error).__name__}", False)
