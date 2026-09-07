"""Executable checks for durable reactive trigger and lease scheduling.

Owns deduplication, lease, fencing, recovery, and concurrent-claim proof.
It is verification only and never schedules production work itself.
"""
from __future__ import annotations

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from ..loop.loop_definition import LoopDefinitionRef
from ..loop.recursive_loop import LoopLedger
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationStartRequest, ActivationStatus,
    ActivationTerminalRequest, LeaseHeartbeatRequest,
    ReactiveSeriesDefinition, TriggerEnvelope)
from ..loop.reactive_contracts import (
    ActivationPolicy, AdmissionPolicy, EmissionPolicy, ExplorationPolicy,
    InputSchedulingPolicy, MetricDirection, OutputPortDefinition,
    PersistenceMode, PortfolioPolicy, PortfolioView, RankingDimension,
    ReactiveLivenessPolicy, ReactiveLoopProfile, RetentionPolicy,
    ServingPolicy, TriggerKind)
from .reactive_scheduler import (
    ActivationClaimResult, DurableSeriesHistoryError, ReactiveSchedulerError,
    SQLiteReactiveScheduler)
from .runtime_observer import RuntimeObservationServices


def _profile(profile_id: str = "profile-reactive") -> ReactiveLoopProfile:
    return ReactiveLoopProfile(
        profile_id, "1.0.0",
        ActivationPolicy(
            (TriggerKind.PUSH_EVENT, TriggerKind.SCHEDULE),
            reactivation_enabled=True,
            minimum_information_delta=0.01),
        AdmissionPolicy(10),
        InputSchedulingPolicy("priority_aging", 0.01),
        PersistenceMode.DURABLE_SERIES, ExplorationPolicy(),
        (OutputPortDefinition("result", "answer", "answer/v1"),),
        PortfolioPolicy(
            "policy-reactive", "1.0.0", PortfolioView.VERIFIED_TOP_K,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            10),
        EmissionPolicy(), ServingPolicy(10), RetentionPolicy(100, 100),
        ReactiveLivenessPolicy(30))


def _series(profile: ReactiveLoopProfile, series_id: str = "series-reactive",
            attempts: int = 2) -> ReactiveSeriesDefinition:
    return ReactiveSeriesDefinition(
        series_id, "Process new information and publish a verified result.",
        LoopDefinitionRef("practitioner.fixture", "1.0.0", "c" * 64),
        profile.profile_id, profile.version, profile.content_digest,
        "trigger/v1", ("result",), attempts, 2)


def _trigger(trigger_id: str, series_id: str, answer: int, *,
             received_at: str, priority: int = 0,
             deduplication_key: str = "") -> TriggerEnvelope:
    value = LoopValue.create(
        {"answer": answer}, LoopValueCreateRequest(
            "trigger/v1", "trigger_input", "loop-source",
            "core.fixture.source"))
    return TriggerEnvelope(
        trigger_id, series_id, TriggerKind.PUSH_EVENT, "subject-one",
        value.to_ref(), "loop-source", received_at, received_at,
        deduplication_key or f"dedup-{trigger_id}", 1.0, priority=priority)


def _hardening_checks() -> dict:
    from ..loop.reactive_activation import ActivationHistoryDisposition
    import hashlib
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


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    profile = _profile()
    series = _series(profile)
    with tempfile.TemporaryDirectory() as temporary:
        path = os.path.join(temporary, "scheduler.sqlite")
        ledger = LoopLedger(id_namespace="reactive-scheduler")
        scheduler = SQLiteReactiveScheduler(
            path, RuntimeObservationServices(ledger=ledger))
        scheduler.register_profile(profile)
        scheduler.register_series(series)

        low = _trigger(
            "trigger-low", series.series_id, 1,
            received_at="2026-08-29T14:00:00Z", priority=0)
        high = _trigger(
            "trigger-high", series.series_id, 2,
            received_at="2026-08-29T14:01:00Z", priority=10)
        low_result = scheduler.admit(low)
        high_result = scheduler.admit(high)
        duplicate = scheduler.admit(_trigger(
            "trigger-duplicate", series.series_id, 2,
            received_at="2026-08-29T14:02:00Z", priority=50,
            deduplication_key="different-key"))
        check("new_inputs_create_work_and_unchanged_input_does_not",
              low_result.created and high_result.created
              and not duplicate.created
              and duplicate.activation.activation_id
              == high_result.activation.activation_id)

        claim = scheduler.claim(ActivationClaimRequest(
            "worker-one", "2026-08-29T14:03:00Z", 60,
            series.series_id))
        check("priority_aging_selects_one_exclusive_activation",
              claim is not None
              and claim.activation.activation_id
              == high_result.activation.activation_id
              and claim.lease.fencing_token == 1)
        started = scheduler.start(ActivationStartRequest(
            claim.activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, "2026-08-29T14:03:01Z"))
        renewed = scheduler.heartbeat(LeaseHeartbeatRequest(
            started.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, "2026-08-29T14:03:30Z",
            "2026-08-29T14:05:00Z"))
        check("current_worker_can_extend_its_fenced_lease",
              renewed.expires_at == "2026-08-29T14:05:00Z"
              and not scheduler.recover_expired("2026-08-29T14:04:00Z"))

        recovered = scheduler.recover_expired("2026-08-29T14:06:00Z")
        check("expired_running_work_requires_reconciliation_before_replay",
              len(recovered) == 1
              and recovered[0].status is ActivationStatus.DEAD_LETTER
              and recovered[0].attempt == 1
              and recovered[0].failure_code == "RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED")
        stale_refused = False
        try:
            scheduler.terminal(ActivationTerminalRequest(
                started.activation_id, claim.lease.lease_id,
                claim.lease.fencing_token, ActivationStatus.COMPLETED,
                "2026-08-29T14:06:01Z", "loop-stale", "ACCEPTED"))
        except ReactiveSchedulerError:
            stale_refused = True
        check("expired_worker_cannot_commit_with_stale_fencing_token",
              stale_refused)

        unstarted = scheduler.claim(ActivationClaimRequest(
            "worker-two", "2026-08-29T14:06:02Z", 1,
            series.series_id))
        recovered_unstarted = scheduler.recover_expired("2026-08-29T14:06:04Z")
        check("expired_unstarted_lease_remains_retryable_within_attempt_budget",
              unstarted.activation.activation_id == low_result.activation.activation_id
              and len(recovered_unstarted) == 1
              and recovered_unstarted[0].status is ActivationStatus.ADMITTED
              and scheduler.get_activation(started.activation_id).status is ActivationStatus.DEAD_LETTER)
        reclaimed = scheduler.claim(ActivationClaimRequest(
            "worker-three", "2026-08-29T14:06:05Z", 60, series.series_id))
        scheduler.start(ActivationStartRequest(
            reclaimed.activation.activation_id, reclaimed.lease.lease_id,
            reclaimed.lease.fencing_token, "2026-08-29T14:06:06Z"))
        completed = scheduler.terminal(ActivationTerminalRequest(
            reclaimed.activation.activation_id, reclaimed.lease.lease_id,
            reclaimed.lease.fencing_token, ActivationStatus.COMPLETED,
            "2026-08-29T14:06:07Z", "loop-completed", "ACCEPTED",
            ("candidate-final",)))
        history = scheduler.activation_history(completed.activation_id)
        check("recovered_activation_completes_under_new_fence",
              completed.fencing_token == 2
              and completed.status is ActivationStatus.COMPLETED
              and [item.status for item in history] == [
                  ActivationStatus.ADMITTED, ActivationStatus.LEASED,
                  ActivationStatus.ADMITTED,
                  ActivationStatus.LEASED, ActivationStatus.RUNNING,
                  ActivationStatus.COMPLETED])

        invalid_kind = False
        try:
            value = _trigger(
                "trigger-manual", series.series_id, 3,
                received_at="2026-08-29T14:07:00Z")
            scheduler.admit(TriggerEnvelope(
                value.trigger_id, value.series_id, TriggerKind.MANUAL_REFRESH,
                value.subject_ref, value.input_ref, value.source_loop_id,
                value.source_event_time, value.received_at,
                value.deduplication_key, value.information_delta))
        except ReactiveSchedulerError:
            invalid_kind = True
        check("unregistered_trigger_kind_fails_before_admission", invalid_kind)

        low_delta_refused = False
        low_delta = _trigger(
            "trigger-low-delta", series.series_id, 12,
            received_at="2026-08-29T14:08:00Z")
        try:
            scheduler.admit(TriggerEnvelope(
                low_delta.trigger_id, low_delta.series_id,
                low_delta.trigger_kind, low_delta.subject_ref,
                low_delta.input_ref, low_delta.source_loop_id,
                low_delta.source_event_time, low_delta.received_at,
                low_delta.deduplication_key, 0.0))
        except ReactiveSchedulerError:
            low_delta_refused = True
        check("below_threshold_information_delta_is_not_admitted",
              low_delta_refused)

        exhausted_profile = _profile("profile-exhausted")
        exhausted_series = _series(
            exhausted_profile, "series-exhausted", attempts=1)
        scheduler.register_profile(exhausted_profile)
        scheduler.register_series(exhausted_series)
        exhausted_admission = scheduler.admit(_trigger(
            "trigger-exhausted", exhausted_series.series_id, 9,
            received_at="2026-08-29T15:00:00Z"))
        exhausted_claim = scheduler.claim(ActivationClaimRequest(
            "worker-exhausted", "2026-08-29T15:00:01Z", 1,
            exhausted_series.series_id))
        scheduler.recover_expired("2026-08-29T15:00:03Z")
        exhausted = scheduler.get_activation(
            exhausted_admission.activation.activation_id)
        check("expired_unstarted_final_attempt_dead_letters_honestly",
              exhausted.status is ActivationStatus.DEAD_LETTER
              and exhausted.failure_code
              == "LEASE_EXPIRED_ATTEMPTS_EXHAUSTED")
        from .event_vocabulary import to_canonical_events
        families = {item["type"] for item in to_canonical_events(ledger.events)}
        check("scheduler_transitions_use_canonical_run_events",
              {"loop.activation.admitted", "loop.activation.leased",
               "loop.activation.started", "loop.activation.heartbeat",
               "loop.activation.recovered", "loop.activation.completed"}
              <= families)
        scheduler.close()

        reopened = SQLiteReactiveScheduler(path)
        reopened.register_profile(profile)
        reopened.register_series(series)
        restored = reopened.get_activation(completed.activation_id)
        check("activation_history_survives_scheduler_restart",
              restored.status is ActivationStatus.COMPLETED
              and restored.loop_id == "loop-completed")
        reopened.close()

        concurrent_path = os.path.join(temporary, "concurrent.sqlite")
        seed = SQLiteReactiveScheduler(concurrent_path)
        seed.register_profile(profile)
        seed.register_series(series)
        concurrency_trigger = seed.admit(_trigger(
            "trigger-concurrent", series.series_id, 11,
            received_at="2026-08-29T16:00:00Z"))
        seed.close()
        barrier = Barrier(2)

        def contender(worker_id: str):
            instance = SQLiteReactiveScheduler(concurrent_path)
            instance.register_profile(profile)
            instance.register_series(series)
            barrier.wait(timeout=5)
            result = instance.claim(ActivationClaimRequest(
                worker_id, "2026-08-29T16:00:01Z", 60,
                series.series_id))
            instance.close()
            return result

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = tuple(workers.map(
                contender, ("worker-a", "worker-b")))
        claimed = tuple(item for item in outcomes if item is not None)
        check("two_workers_cannot_claim_the_same_activation",
              len(claimed) == 1
              and claimed[0].activation.activation_id
              == concurrency_trigger.activation.activation_id)

    for item in _hardening_checks()["tests"]:
        tests.append(item)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_scheduler_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
