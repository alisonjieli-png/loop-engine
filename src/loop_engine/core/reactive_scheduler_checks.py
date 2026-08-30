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
from .reactive_scheduler import ReactiveSchedulerError, SQLiteReactiveScheduler
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
        check("expired_lease_returns_bounded_work_to_admission",
              len(recovered) == 1
              and recovered[0].status is ActivationStatus.ADMITTED
              and recovered[0].attempt == 1)
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

        reclaimed = scheduler.claim(ActivationClaimRequest(
            "worker-two", "2026-08-29T14:06:02Z", 60,
            series.series_id))
        scheduler.start(ActivationStartRequest(
            reclaimed.activation.activation_id, reclaimed.lease.lease_id,
            reclaimed.lease.fencing_token, "2026-08-29T14:06:03Z"))
        completed = scheduler.terminal(ActivationTerminalRequest(
            reclaimed.activation.activation_id, reclaimed.lease.lease_id,
            reclaimed.lease.fencing_token, ActivationStatus.COMPLETED,
            "2026-08-29T14:06:04Z", "loop-completed", "ACCEPTED",
            ("candidate-final",)))
        history = scheduler.activation_history(completed.activation_id)
        check("recovered_activation_completes_under_new_fence",
              completed.fencing_token == 2
              and completed.status is ActivationStatus.COMPLETED
              and [item.status for item in history] == [
                  ActivationStatus.ADMITTED, ActivationStatus.LEASED,
                  ActivationStatus.RUNNING, ActivationStatus.ADMITTED,
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
        scheduler.start(ActivationStartRequest(
            exhausted_claim.activation.activation_id,
            exhausted_claim.lease.lease_id,
            exhausted_claim.lease.fencing_token,
            "2026-08-29T15:00:01Z"))
        scheduler.recover_expired("2026-08-29T15:00:03Z")
        exhausted = scheduler.get_activation(
            exhausted_admission.activation.activation_id)
        check("expired_final_attempt_dead_letters_honestly",
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

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_scheduler_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
