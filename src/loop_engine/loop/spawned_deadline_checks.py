"""Deterministic deadline checks using a local clock and local callbacks.

These checks distinguish acceptance deadlines from physical cancellation and
verify that expired authority cannot turn a completed callback into success.
"""
from __future__ import annotations

from unittest.mock import patch

from .delegation_runtime import (
    DelegationBudget, DelegationError, SpawnedTaskManager, SpawnedTaskStatus,
)
from .recursive_loop import Loop, LoopConfig
from .spawned_runtime_port import DeterministicSpawnedExecutor


def run_deadline_checks():
    from .delegation_runtime_checks import _solution_spec

    checks = []

    def check(name, passed):
        checks.append({"test": name, "passed": bool(passed), "detail": "offline injected clock"})

    def parent():
        return Loop("deadline fixture", LoopConfig(
            allowable_modes=("deterministic",), preferred_modes=("deterministic",),
            delegated_modes=("deterministic",)))

    returned = []

    def execute(request):
        result = DeterministicSpawnedExecutor()(request)
        returned.append(result)
        return result

    spec = _solution_spec(budget=DelegationBudget(wall_time_seconds=1.0))
    owner = parent()
    manager = SpawnedTaskManager(owner, execute)
    with patch("loop_engine.loop.spawned_deadline.monotonic", side_effect=(10.0, 10.01, 12.0)):
        task = manager.start(spec)
    result = manager.status(task).result
    assessment = next(event for event in owner.ledger.events
                      if event.get("custom_kind") == "spawned_deadline_assessed")
    check("synchronous_late_return_cannot_be_success",
          result.status == SpawnedTaskStatus.FAILED
          and result.terminal_code == "DEADLINE_EXCEEDED"
          and result.error_code == "DEADLINE_EXCEEDED")
    check("synchronous_deadline_retains_returned_outputs_and_counters",
          result.outputs == returned[0].outputs and result.summary == returned[0].summary
          and result.steps_run == returned[0].steps_run
          and result.model_calls == returned[0].model_calls)
    check("synchronous_deadline_neither_replays_nor_claims_cancellation",
          len(returned) == 1 and assessment["executor_returned"]
          and assessment["exceeded"] and not assessment["physical_cancellation_confirmed"]
          and not assessment["replay_authorized"]
          and assessment["callback_effect_state"] == "unreconciled")

    timely = SpawnedTaskManager(parent(), execute)
    with patch("loop_engine.loop.spawned_deadline.monotonic", side_effect=(20.0, 20.01, 20.5)):
        timely_task = timely.start(spec)
    check("synchronous_return_within_declared_deadline_still_succeeds",
          timely.status(timely_task).status == SpawnedTaskStatus.SUCCEEDED)

    no_limit = SpawnedTaskManager(parent(), execute)
    with patch("loop_engine.loop.spawned_deadline.monotonic",
               side_effect=AssertionError("an absent deadline does not invent a limit")):
        no_limit_task = no_limit.start(_solution_spec())
    check("undeclared_synchronous_deadline_does_not_invent_a_limit",
          no_limit.status(no_limit_task).status == SpawnedTaskStatus.SUCCEEDED)

    calls_before = len(returned)
    expired_owner = parent()
    expired = SpawnedTaskManager(expired_owner, execute)
    with patch("loop_engine.loop.spawned_deadline.monotonic", side_effect=(30.0, 32.0)):
        expired_task = expired.start(spec)
    expired_assessment = next(event for event in expired_owner.ledger.events
                             if event.get("custom_kind") == "spawned_deadline_assessed")
    check("deadline_expired_during_admission_prevents_callback_dispatch",
          len(returned) == calls_before
          and expired.status(expired_task).result.terminal_code == "DEADLINE_EXCEEDED"
          and expired_assessment["phase"] == "before_dispatch"
          and expired_assessment["callback_effect_state"] == "not_dispatched")

    preemptive_owner = parent()
    preemptive = SpawnedTaskManager(preemptive_owner, execute)
    refused = False
    try:
        preemptive.start(spec, require_preemptive_deadline=True)
    except DelegationError as exc:
        refused = "does not support preemptive deadlines" in str(exc)
    check("unsupported_synchronous_preemption_refuses_before_spawning",
          refused and len(returned) == calls_before and len(preemptive_owner.ledger.loops()) == 1)
    return checks
