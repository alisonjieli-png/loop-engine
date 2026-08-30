"""Wall-clock and identity checks for asynchronous canonical Loop workers.

Owns overlap, exact-definition, unique-ID, and terminal-history proof.
It is verification only and never installs a production worker.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from ..loop.loop_contract import LoopContract
from ..loop.loop_definition import LoopDefinition
from ..loop.loop_role import LoopRole, LoopRoleIdentity
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationStatus, ReactiveSeriesDefinition,
    TriggerEnvelope)
from ..loop.reactive_contracts import (
    ActivationPolicy, AdmissionPolicy, EmissionPolicy, ExplorationPolicy,
    InputSchedulingPolicy, MetricDirection, OutputPortDefinition,
    PersistenceMode, PortfolioPolicy, PortfolioView, RankingDimension,
    ReactiveLivenessPolicy, ReactiveLoopProfile, RetentionPolicy,
    ServingPolicy, TriggerKind)
from ..loop.recursive_loop import LoopConfig, StepOutcome
from ..loop.runtime_context import LoopRuntimeContext
from .reactive_scheduler import SQLiteReactiveScheduler
from .reactive_worker import (
    AsyncReactiveWorker, CanonicalReactiveExecutor, ReactiveHandlerBinding,
    ReactiveWorkerRequest)


def _definition() -> LoopDefinition:
    config = LoopConfig(
        framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        exit_condition="accepted_success")
    contract = LoopContract(
        "reactive fixture", "code_only", ("trigger/v1",), ("answer/v1",),
        ("pure",), role="practitioner")
    return LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.code_execution"),
        contract=contract, config=config,
        definition_id="practitioner.reactive_fixture", version="1.0.0",
        installed_executor_modes=("deterministic",))


def _profile() -> ReactiveLoopProfile:
    return ReactiveLoopProfile(
        "profile-worker", "1.0.0",
        ActivationPolicy(
            (TriggerKind.PUSH_EVENT,), reactivation_enabled=True),
        AdmissionPolicy(10), InputSchedulingPolicy(),
        PersistenceMode.DURABLE_SERIES, ExplorationPolicy(),
        (OutputPortDefinition("result", "answer", "answer/v1"),),
        PortfolioPolicy(
            "policy-worker", "1.0.0", PortfolioView.VERIFIED_TOP_K,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            10),
        EmissionPolicy(), ServingPolicy(10), RetentionPolicy(100, 100),
        ReactiveLivenessPolicy(30))


def _trigger(index: int, definition: LoopDefinition) -> TriggerEnvelope:
    value = LoopValue.create(
        {"index": index}, LoopValueCreateRequest(
            "trigger/v1", "trigger_input", "loop-source",
            definition.definition_id))
    moment = f"2026-08-29T17:00:0{index}Z"
    return TriggerEnvelope(
        f"trigger-worker-{index}", "series-worker", TriggerKind.PUSH_EVENT,
        f"subject-{index}", value.to_ref(), "loop-source", moment, moment,
        f"dedup-worker-{index}", 1.0)


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    definition = _definition()
    profile = _profile()
    series = ReactiveSeriesDefinition(
        "series-worker", "Run one bounded reactive fixture activation.",
        definition.ref, profile.profile_id, profile.version,
        profile.content_digest, "trigger/v1", ("result",), 2, 3)
    started: list[float] = []
    finished: list[float] = []

    def handler(_loop, step: str, _trigger_value) -> StepOutcome:
        if step != "act":
            raise AssertionError("fixture definition contains act only")
        started.append(time.monotonic())
        time.sleep(0.2)
        finished.append(time.monotonic())
        return StepOutcome("reactive:completed", "deterministic", 1.0)

    with tempfile.TemporaryDirectory() as temporary:
        scheduler = SQLiteReactiveScheduler(os.path.join(
            temporary, "worker.sqlite"))
        scheduler.register_profile(profile)
        scheduler.register_series(series)
        admissions = tuple(scheduler.admit(_trigger(index, definition))
                           for index in range(1, 4))
        context = LoopRuntimeContext.compatibility(
            capabilities=definition.required_capabilities,
            permissions=definition.permissions,
            executor_modes=definition.installed_executor_modes)
        executor = CanonicalReactiveExecutor(
            LoopDefinitionRegistry((definition,)), context,
            (ReactiveHandlerBinding(definition.ref, handler),))
        worker = AsyncReactiveWorker(scheduler, executor)
        requests = tuple(ReactiveWorkerRequest(
            ActivationClaimRequest(
                f"worker-{index}", "2026-08-29T17:01:00Z", 60,
                series.series_id),
            "2026-08-29T17:01:01Z", "2026-08-29T17:01:02Z")
            for index in range(1, 4))
        wall_start = time.monotonic()
        outcomes = asyncio.run(worker.run_many(requests))
        wall_elapsed = time.monotonic() - wall_start

        check("three_reactive_activations_create_three_distinct_loops",
              len({item.loop_id for item in outcomes}) == 3
              and all(item.claimed and item.terminal_code == "ACCEPTED"
                      for item in outcomes), str(outcomes))
        check("blocking_handlers_overlap_through_thread_placement",
              len(started) == 3 and len(finished) == 3
              and max(started) < min(finished),
              f"all handlers started before the first finished; "
              f"elapsed={wall_elapsed:.3f}")
        check("every_claimed_loop_has_its_own_terminal_history",
              all(any(event.get("event") == "terminal"
                      and event.get("loop_id") == item.loop_id
                      for event in executor.ledger_for(
                          item.activation_id).events)
                  for item in outcomes))
        terminal = tuple(scheduler.get_activation(
            admission.activation.activation_id) for admission in admissions)
        check("durable_activation_records_bind_exact_loop_results",
              all(item.status is ActivationStatus.COMPLETED
                  and item.loop_id in {outcome.loop_id for outcome in outcomes}
                  and item.loop_definition_ref == definition.ref
                  for item in terminal))
        scheduler.close()

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_worker_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
