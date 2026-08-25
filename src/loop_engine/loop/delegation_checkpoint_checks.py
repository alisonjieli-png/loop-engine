"""Offline checks for async spawned deadlines, joins, and checkpoints.

The tests use local coroutines only. They make no provider, network, model,
workspace, MCP, or external-harness call.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import Any

from .spawned_task_checkpoint import (
    SPAWNED_TASK_CHECKPOINT_VERSION,
    SpawnedTaskCheckpoint,
    SpawnedTaskCheckpointError,
)
from .delegation_runtime import (
    SpawnedExecutionRequest,
    SpawnedLoopResult,
    SpawnedTaskId,
    SpawnedTaskManager,
    SpawnedTaskStatus,
    SpawnedTaskUpdate,
    DelegationBudget,
    DelegationConstraints,
    DelegationError,
    DelegationSpec,
    LoopPortValue,
)
from .loop_contract import LoopContract
from .loop_profile_catalog import LoopProfileRef
from .recursive_loop import Loop, LoopConfig, StepOutcome


def _parent(goal: str = "checkpoint parent") -> Loop:
    return Loop(
        goal,
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ))


def _spec(*, budget: "DelegationBudget | None" = None) -> DelegationSpec:
    return DelegationSpec(
        goal="normalize one durable row",
        profile=LoopProfileRef("solution.atomic_component"),
        contract=LoopContract(
            "durable-row",
            "code_only",
            input_roles=("raw/v1",),
            output_roles=("clean/v1",),
        ),
        inputs=(LoopPortValue("raw/v1", {"name": " Ada "}),),
        budget=budget or DelegationBudget(),
        constraints=DelegationConstraints(
            available_fields=("operation_ref",),
            capability_refs=("solution_canvas", "component_execution"),
        ),
    )


def run_checkpoint_checks() -> list[dict]:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    invalid_deadlines = 0
    for value in (0, -1, True, "1", float("inf"), float("nan")):
        try:
            DelegationBudget(wall_time_seconds=value)
        except DelegationError:
            invalid_deadlines += 1
    check(
        "wall_time_deadline_is_typed_optional_and_positive",
        invalid_deadlines == 6
        and DelegationBudget().wall_time_seconds is None
        and DelegationBudget(wall_time_seconds=0.25).wall_time_seconds == 0.25,
        "unset is allowed; non-positive, non-finite, bool, and string values "
        "are refused",
    )

    terminal = _terminal_checkpoint_case()
    check(
        "terminal_checkpoint_round_trips_and_restores_exact_metadata",
        terminal["passed"], terminal["detail"])

    invalid = _checkpoint_refusal_case(terminal["checkpoint"])
    check(
        "stale_version_tamper_and_invalid_state_fail_closed",
        invalid["passed"], invalid["detail"])

    deadline = asyncio.run(_deadline_case())
    check(
        "async_executor_wall_time_deadline_fails_and_closes_spawned",
        deadline["passed"], deadline["detail"])

    join = asyncio.run(_join_case())
    check(
        "join_returns_creation_order_with_updates_and_no_orphans",
        join["passed"], join["detail"])

    bounded_join = asyncio.run(_join_timeout_case())
    check(
        "wait_all_timeout_cancels_remaining_spawned_loops_without_orphans",
        bounded_join["passed"], bounded_join["detail"])

    race = asyncio.run(_cancellation_race_case())
    check(
        "completion_cancellation_race_publishes_one_terminal_state",
        race["passed"], race["detail"])

    interrupted = asyncio.run(_interrupted_recovery_case())
    check(
        "running_and_queued_checkpoints_restore_as_interrupted",
        interrupted["passed"], interrupted["detail"])

    return tests


def _terminal_checkpoint_case() -> dict[str, Any]:
    parent = _parent()
    manager = SpawnedTaskManager(parent)
    task_id = manager.start(_spec())
    checkpoint = manager.checkpoint(task_id)
    restored_value = SpawnedTaskCheckpoint.from_json(checkpoint.to_json())
    restored_parent = _parent()
    restored_manager = SpawnedTaskManager(restored_parent)
    snapshot = restored_manager.restore_checkpoint(restored_value)
    second_id = restored_manager.start(_spec())
    second = restored_manager.status(second_id)
    repeated = restored_manager.checkpoint(task_id)
    passed = (
        checkpoint.schema_version == SPAWNED_TASK_CHECKPOINT_VERSION
        and checkpoint.checkpoint_digest == restored_value.checkpoint_digest
        and snapshot.status == SpawnedTaskStatus.SUCCEEDED
        and snapshot.task_id == task_id
        and snapshot.identity == checkpoint.identity
        and snapshot.relationship == checkpoint.relationship
        and snapshot.result == checkpoint.result
        and snapshot.updates == checkpoint.update_count == 0
        and repeated.checkpoint_digest == checkpoint.checkpoint_digest
        and str(second_id).endswith(".spawned-task.2")
        and second.status == SpawnedTaskStatus.SUCCEEDED
        and restored_parent.audit_closure()["orphaned_spawned_loops"] == [])
    return {
        "passed": passed,
        "detail": (
            "schema, digest, task ID, relationship, result, counters, errors, "
            "order, and next ID survived terminal restoration"),
        "checkpoint": checkpoint,
    }


def _checkpoint_refusal_case(checkpoint: SpawnedTaskCheckpoint) -> dict[str, Any]:
    stale = json.loads(checkpoint.to_json())
    stale["schema_version"] = "spawned_task_checkpoint/v0"
    tampered = json.loads(checkpoint.to_json())
    tampered["spec"]["goal"] = "tampered goal"
    unknown = json.loads(checkpoint.to_json())
    unknown["unexpected"] = True
    refused = 0
    for value in (stale, tampered, unknown):
        try:
            SpawnedTaskCheckpoint.from_dict(value)
        except (SpawnedTaskCheckpointError, ValueError):
            refused += 1
    invalid_state = False
    try:
        replace(
            checkpoint,
            status=SpawnedTaskStatus.RUNNING,
            checkpoint_digest="")
    except SpawnedTaskCheckpointError:
        invalid_state = True
    return {
        "passed": refused == 3 and invalid_state,
        "detail": (
            "stale schema, changed body, unknown field, and result/status "
            "mismatch were refused"),
    }


async def _deadline_case() -> dict[str, Any]:
    canceled = {"value": False}

    async def slow_executor(
            request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            canceled["value"] = True
            raise
        raise AssertionError("deadline did not stop executor")

    parent = _parent("deadline parent")
    manager = SpawnedTaskManager(parent, slow_executor)
    task_id = await manager.start_async(_spec(
        budget=DelegationBudget(wall_time_seconds=0.01)))
    snapshot = await manager.wait(task_id)
    checkpoint = SpawnedTaskCheckpoint.from_json(
        manager.checkpoint(task_id).to_json())
    restored = SpawnedTaskManager(_parent("deadline parent")).restore_checkpoint(
        checkpoint)
    passed = (
        snapshot.status == SpawnedTaskStatus.FAILED
        and snapshot.result is not None
        and snapshot.result.error_code == "DEADLINE_EXCEEDED"
        and snapshot.result.terminal_code == "DEADLINE_EXCEEDED"
        and canceled["value"]
        and checkpoint.result is not None
        and checkpoint.result.error == snapshot.result.error
        and restored.result == checkpoint.result
        and parent.audit_closure()["orphaned_spawned_loops"] == [])
    return {
        "passed": passed,
        "detail": (
            "asyncio deadline canceled executor work and preserved typed "
            "deadline error in checkpoint restoration"),
    }


async def _join_case() -> dict[str, Any]:
    async def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        index = int(str(request.task_id).rsplit(".", 1)[-1])
        await asyncio.sleep((4 - index) * 0.005)
        result = request.runtime.run()
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean/v1", index),),
            summary=f"completed spawned {index}",
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
            model_calls=result.counters.model_calls,
        )

    parent = _parent("join parent")
    manager = SpawnedTaskManager(parent, executor)
    task_ids = [await manager.start_async(_spec()) for _ in range(3)]
    manager.update(
        task_ids[1], SpawnedTaskUpdate(instruction="preserve update count"))
    snapshots = await manager.join(timeout_seconds=1)
    checkpoints = manager.checkpoints()
    passed = (
        [snapshot.task_id for snapshot in snapshots] == task_ids
        and all(snapshot.status == SpawnedTaskStatus.SUCCEEDED
                for snapshot in snapshots)
        and snapshots[1].updates == checkpoints[1].update_count == 1
        and [checkpoint.task_id for checkpoint in checkpoints] == task_ids
        and parent.audit_closure()["orphaned_spawned_loops"] == [])
    return {
        "passed": passed,
        "detail": (
            "three spawned_loops completed out of order but joined in creation "
            "order with update metadata intact"),
    }


async def _join_timeout_case() -> dict[str, Any]:
    gate = asyncio.Event()

    async def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        await gate.wait()
        raise AssertionError("bounded join should cancel blocked work")

    parent = _parent("bounded join parent")
    manager = SpawnedTaskManager(parent, executor)
    task_ids = [await manager.start_async(_spec()) for _ in range(2)]
    snapshots = await manager.wait_all(timeout_seconds=0.01)
    repeated = await manager.join(task_ids, timeout_seconds=0.01)
    return {
        "passed": (
            [snapshot.task_id for snapshot in snapshots] == task_ids
            and all(snapshot.status == SpawnedTaskStatus.CANCELED
                    for snapshot in snapshots)
            and repeated == snapshots
            and parent.audit_closure()["orphaned_spawned_loops"] == []),
        "detail": (
            "bounded wait canceled blocked spawned_loops and repeat join returned "
            "the same ordered terminal snapshots"),
    }


async def _cancellation_race_case() -> dict[str, Any]:
    gate = asyncio.Event()

    async def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        await gate.wait()
        result = request.runtime.run()
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean/v1", "done"),),
            summary="race completed",
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
        )

    parent = _parent("cancellation race parent")
    manager = SpawnedTaskManager(parent, executor)
    task_id = await manager.start_async(_spec())

    async def release() -> None:
        await asyncio.sleep(0)
        gate.set()

    async def cancel() -> None:
        await asyncio.sleep(0)
        manager.cancel(task_id, "race cancellation")

    await asyncio.gather(release(), cancel())
    snapshot = await manager.wait(task_id)
    terminal_events = [
        event for event in parent.ledger.events
        if event.get("custom_kind") == "spawned_task_terminal"
        and event.get("spawned_task_id") == str(task_id)]
    return {
        "passed": (
            snapshot.status.terminal
            and len(terminal_events) == 1
            and parent.audit_closure()["orphaned_spawned_loops"] == []),
        "detail": (
            f"race resolved once as {snapshot.status.value} with one terminal "
            "event and no orphan"),
    }


async def _interrupted_recovery_case() -> dict[str, Any]:
    gate = asyncio.Event()

    async def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        request.runtime.run(
            handler=lambda step: StepOutcome(
                output=f"{step.step}:checkpointed", mode="deterministic"),
            max_steps=1)
        await gate.wait()
        raise AssertionError("original running task should be canceled")

    parent = _parent("interrupted parent")
    manager = SpawnedTaskManager(parent, executor)
    task_id = await manager.start_async(_spec())
    manager.update(
        task_id, SpawnedTaskUpdate(instruction="one durable update"))
    running = SpawnedTaskCheckpoint.from_json(
        manager.checkpoint(task_id).to_json())
    manager.cancel(task_id, "checkpoint captured")
    await manager.wait(task_id)

    restored_parent = _parent("interrupted parent")
    restored_manager = SpawnedTaskManager(restored_parent)
    interrupted = restored_manager.restore_checkpoint(running)
    queued_checkpoint = SpawnedTaskCheckpoint(
        task_id=SpawnedTaskId(
            f"{restored_parent.loop_id}.spawned-task.99"),
        spec=running.spec,
        identity=running.identity,
        relationship=running.relationship,
        status=SpawnedTaskStatus.QUEUED,
    )
    queued = restored_manager.restore_checkpoint(queued_checkpoint)
    joined = await restored_manager.wait_all(timeout_seconds=0.1)
    repeated = SpawnedTaskCheckpoint.from_json(
        restored_manager.checkpoint(task_id).to_json())
    passed = (
        running.status == SpawnedTaskStatus.RUNNING
        and interrupted.status == SpawnedTaskStatus.INTERRUPTED
        and interrupted.task_id == task_id
        and interrupted.updates == running.update_count == 1
        and interrupted.relationship == running.relationship
        and interrupted.result is not None
        and interrupted.result.error_code == "INTERRUPTED_ON_RESTORE"
        and interrupted.result.steps_run == running.steps_run
        and interrupted.result.model_calls == running.model_calls
        and queued.status == SpawnedTaskStatus.INTERRUPTED
        and [snapshot.task_id for snapshot in joined]
        == [task_id, queued_checkpoint.task_id]
        and repeated.status == SpawnedTaskStatus.INTERRUPTED
        and restored_parent.audit_closure()["orphaned_spawned_loops"] == [])
    return {
        "passed": passed,
        "detail": (
            "running and queued metadata restored as explicit INTERRUPTED "
            "terminal results with IDs, relationship, updates, counters, and "
            "errors preserved"),
    }
