"""Durable finite activations using Loop Engine's scheduler, worker and history."""

from __future__ import annotations

import os
import time
from dataclasses import replace

from loop_engine.code_nodes.solution_graph import LoopDefinitionRegistry
from loop_engine.core.reactive_scheduler import SQLiteReactiveScheduler
from loop_engine.core.reactive_worker import (
    AsyncReactiveWorker,
    CanonicalReactiveExecutor,
    ReactiveHandlerBinding,
    ReactiveHistoryPolicy,
    ReactiveWorkerHeartbeatPolicy,
    ReactiveWorkerRequest,
)
from loop_engine.loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from loop_engine.loop.effect_approval import ApprovalDecision
from loop_engine.loop.reactive_activation import (
    ActivationClaimRequest,
    ReactiveSeriesDefinition,
    TriggerEnvelope,
)
from loop_engine.loop.reactive_contracts import (
    ActivationPolicy,
    AdmissionPolicy,
    EmissionPolicy,
    ExplorationPolicy,
    InputSchedulingPolicy,
    MetricDirection,
    OutputPortDefinition,
    PersistenceMode,
    PortfolioPolicy,
    PortfolioView,
    RankingDimension,
    ReactiveLivenessPolicy,
    ReactiveLoopProfile,
    RetentionPolicy,
    ServingPolicy,
    TriggerKind,
)
from loop_engine.loop.recursive_loop import StepOutcome
from loop_engine.loop.runtime_context import LoopRuntimeContext

from ...contracts import digest
from ...runtime import compute, definition
from ...storage import now


def profile():
    return ReactiveLoopProfile(
        "lab.durable",
        "1.0.0",
        ActivationPolicy((TriggerKind.PUSH_EVENT,), reactivation_enabled=True),
        AdmissionPolicy(10000),
        InputSchedulingPolicy(),
        PersistenceMode.DURABLE_SERIES,
        ExplorationPolicy(),
        (OutputPortDefinition("result", "result", "embodiment_result/v1"),),
        PortfolioPolicy(
            "lab.durable.rank",
            "1.0.0",
            PortfolioView.VERIFIED_TOP_K,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            10,
        ),
        EmissionPolicy(),
        ServingPolicy(10),
        RetentionPolicy(10000, 10000),
        ReactiveLivenessPolicy(30),
    )


async def run(packets, context):
    spec, policy = definition(), profile()
    scheduler = SQLiteReactiveScheduler(str(context.root / "activations.sqlite"))
    scheduler.register_profile(policy)
    series = ReactiveSeriesDefinition(
        "lab.series",
        "Execute bounded mechanism tasks durably.",
        spec.ref,
        policy.profile_id,
        policy.version,
        policy.content_digest,
        "embodiment_work/v1",
        ("result",),
        2,
        context.policy.concurrency,
    )
    scheduler.register_series(series)
    by_ref, produced = {}, {}
    history_root = context.root / "reactive-history"
    history_root.mkdir(mode=0o700, exist_ok=True)

    def authorize(request):
        from pathlib import Path

        if not Path(request.effect.target).is_relative_to(history_root):
            raise ValueError("history effect escaped the experiment")
        return ApprovalDecision.approve(request.request_id, "lab.host.history")

    def handler(active, step, trigger):
        original = by_ref[trigger.input_ref.content_digest]
        packet = replace(
            original,
            request_id=original.request_id + "." + active.loop_id.split(".")[-1],
        )
        started = time.monotonic()
        output = compute(packet)
        result = {
            "record_type": "embodiment_candidate/v1",
            "request_id": packet.request_id,
            "task_digest": digest(packet.task.to_dict()),
            "packet_digest": digest(packet.to_dict()),
            "method": packet.method,
            "value": output,
            "value_digest": digest(output),
            "pid": os.getpid(),
            "loop_id": active.loop_id,
            "definition_ref": active.definition_ref.to_dict(),
            "elapsed_seconds": time.monotonic() - started,
            "model_calls": 0,
            "evidence_class": "deterministic_mechanism",
            "ledger": active.ledger.events,
        }
        produced[trigger.trigger_id] = packet, result
        return StepOutcome(output, "deterministic", 1.0)

    executor = CanonicalReactiveExecutor(
        LoopDefinitionRegistry((spec,)),
        LoopRuntimeContext.compatibility(
            capabilities=spec.required_capabilities,
            permissions=spec.permissions,
            executor_modes=spec.installed_executor_modes,
        ),
        (
            ReactiveHandlerBinding(
                spec.ref,
                handler,
                ReactiveHistoryPolicy(True, str(history_root), authorize),
            ),
        ),
    )
    worker = AsyncReactiveWorker(
        scheduler, executor, heartbeat=ReactiveWorkerHeartbeatPolicy(1.0, now)
    )
    admissions = []
    try:
        scheduler.recover_expired(now())
        for packet in packets:
            value = LoopValue.create(
                packet.to_dict(),
                LoopValueCreateRequest(
                    "embodiment_work/v1", "task", "lab.intake", "lab.study"
                ),
            )
            by_ref[value.content_digest] = packet
            stamp = now()
            trigger = TriggerEnvelope(
                packet.request_id,
                series.series_id,
                TriggerKind.PUSH_EVENT,
                packet.task.case_id,
                value.to_ref(),
                "lab.intake",
                stamp,
                stamp,
                packet.request_id,
                1.0,
            )
            admissions.append(scheduler.admit(trigger))
        while True:
            context.remaining()
            stamp = now()
            outcome = await worker.run_once(
                ReactiveWorkerRequest(
                    ActivationClaimRequest("lab.worker", stamp, 60, series.series_id),
                    stamp,
                    now(),
                )
            )
            if not outcome.claimed:
                break
            if outcome.error_code:
                activation = scheduler.get_activation(outcome.activation_id)
                packet = next(
                    p for p in packets if p.request_id == activation.trigger_id
                )
                context.failure(packet, RuntimeError(
                    outcome.underlying_error or outcome.error_code))
                continue
            activation = scheduler.get_activation(outcome.activation_id)
            packet, result = produced[activation.trigger_id]
            row = context.accept(packet, result)
            row["activation_id"] = outcome.activation_id
            row["reactive_terminal"] = outcome.terminal_code
            row["history_disposition"] = activation.history_disposition.value
        return {"activation_ids": [a.activation.activation_id for a in admissions]}
    finally:
        scheduler.close()
