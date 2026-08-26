"""Offline durability checks for Spawned task lifecycle persistence.

These checks prove the local JSONL Spawned task state store survives
restart, refuses duplicate immutable versions, and preserves the
compare-and-swap contract without any provider, network, or model call.
"""
from __future__ import annotations

import asyncio
import json
import stat
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

from .delegation_runtime import (
    DelegationConstraints, DelegationSpec, LoopPortValue,
    SpawnedExecutionRequest, SpawnedLoopResult, SpawnedTaskManager,
    SpawnedTaskStatus, SpawnedTaskUpdate)
from .loop_contract import LoopContract
from .loop_profile_catalog import LoopProfileRef
from .recursive_loop import Loop, LoopConfig
from .spawned_task_checkpoint import (
    SpawnedTaskCheckpoint, SpawnedTaskCheckpointError)
from .spawned_task_state_store import (
    LocalJsonSpawnedTaskStateStore, SpawnedTaskServices,
    SpawnedTaskStateConflict, SpawnedTaskStateIntegrityError,
    StoredSpawnedTaskState)


def _parent(goal: str = "durable Spawned task owner") -> Loop:
    return Loop(goal, LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",)))


def _spec() -> DelegationSpec:
    return DelegationSpec(
        goal="normalize one durable row",
        profile=LoopProfileRef("solution.atomic_component"),
        contract=LoopContract(
            "durable-row", "code_only", input_roles=("raw/v1",),
            output_roles=("clean/v1",)),
        inputs=(LoopPortValue("raw/v1", {"name": " Ada "}),),
        constraints=DelegationConstraints(
            available_fields=("operation_ref",),
            capability_refs=("solution_canvas", "component_execution")))


def _interrupted(checkpoint: SpawnedTaskCheckpoint) -> SpawnedTaskCheckpoint:
    result = SpawnedLoopResult(
        checkpoint.task_id, SpawnedTaskStatus.INTERRUPTED,
        terminal_code="INTERRUPTED", steps_run=checkpoint.steps_run,
        model_calls=checkpoint.model_calls,
        error_code="INTERRUPTED_ON_RESTORE", error="saved active work stopped")
    return replace(
        checkpoint, status=SpawnedTaskStatus.INTERRUPTED,
        result=result, checkpoint_digest="")


def run_checks() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-spawned-state-") as root:
        store = LocalJsonSpawnedTaskStateStore(root)
        parent = _parent()
        manager = SpawnedTaskManager(
            parent, services=SpawnedTaskServices(state_store=store))
        task_id = manager.start(_spec())
        saved = store.load(parent.loop_id, str(task_id))
        path = store.object_path(parent.loop_id, str(task_id))
        check("automatic_start_and_terminal_state_are_persisted",
              saved.checkpoint.status is SpawnedTaskStatus.SUCCEEDED
              and saved.store_revision == 1
              and saved.checkpoint.result is not None)
        check("saved_state_uses_digest_only_names_and_private_file_mode",
              parent.loop_id not in str(path)
              and str(task_id) not in str(path)
              and len(path.stem) == 64
              and stat.S_IMODE(path.stat().st_mode) == 0o600)
        restored = StoredSpawnedTaskState.from_json(
            path.read_text(encoding="utf-8"))
        check("saved_state_round_trips_with_checkpoint_and_record_digests",
              restored == saved
              and restored.checkpoint.checkpoint_digest
              == manager.checkpoint(task_id).checkpoint_digest)

        second_parent = _parent()
        second = SpawnedTaskManager(
            second_parent, services=SpawnedTaskServices(state_store=
                                                        LocalJsonSpawnedTaskStateStore(root)))
        loaded = second.load_saved_checkpoints()
        check("all_terminal_tasks_for_the_same_owner_load_in_order",
              len(loaded) == 1 and loaded[0].task_id == task_id
              and loaded[0].status is SpawnedTaskStatus.SUCCEEDED)
        repeated_load_failed = False
        try:
            second.load_saved_checkpoints()
        except SpawnedTaskCheckpointError:
            repeated_load_failed = True
        check("saved_population_is_preflighted_before_duplicate_loading",
              repeated_load_failed and len(second.list()) == 1)

        duplicate_failed = False
        try:
            store.create(parent.loop_id, manager.checkpoint(task_id))
        except SpawnedTaskStateConflict:
            duplicate_failed = True
        check("duplicate_task_create_fails_closed", duplicate_failed)

        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["checkpoint"]["spec"]["goal"] = "tampered"
        path.write_text(json.dumps(payload), encoding="utf-8")
        tamper_failed = False
        try:
            store.load(parent.loop_id, str(task_id))
        except SpawnedTaskStateIntegrityError:
            tamper_failed = True
        check("changed_saved_checkpoint_fails_integrity_validation",
              tamper_failed)

    async_result = asyncio.run(_automatic_async_case())
    check("update_and_async_terminal_transitions_persist_automatically",
          async_result["passed"], async_result["detail"])

    cancel_result = asyncio.run(_automatic_cancel_case())
    check("cancel_persists_one_terminal_canceled_state",
          cancel_result["passed"], cancel_result["detail"])

    interrupted_result = asyncio.run(_interrupted_load_and_restart_case())
    check("saved_active_work_loads_as_interrupted_not_resumed",
          interrupted_result["interrupted"], interrupted_result["detail"])
    check("interrupted_work_restarts_under_a_new_task_and_loop_identity",
          interrupted_result["restarted"], interrupted_result["detail"])

    concurrency = _concurrent_cas_case()
    check("thread_and_process_compare_and_swap_have_one_winner",
          concurrency["passed"], concurrency["detail"])

    passed = sum(1 for test in tests if test["passed"])
    return {"record_type": "spawned_task_state_store_checks/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


async def _automatic_async_case() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="spawned-async-store-") as root:
        gate = asyncio.Event()

        async def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
            await gate.wait()
            loop_result = request.runtime.run()
            return SpawnedLoopResult(
                request.task_id, SpawnedTaskStatus.SUCCEEDED,
                outputs=(LoopPortValue("clean/v1", "done"),),
                summary="completed saved async work",
                terminal_code=loop_result.counters.terminal_code,
                steps_run=loop_result.counters.steps_run)

        parent = _parent("async persistence owner")
        store = LocalJsonSpawnedTaskStateStore(root)
        manager = SpawnedTaskManager(
            parent, executor,
            services=SpawnedTaskServices(state_store=store))
        task_id = await manager.start_async(_spec())
        initial = store.load(parent.loop_id, str(task_id))
        manager.update(task_id, SpawnedTaskUpdate(instruction="keep casing"))
        updated = store.load(parent.loop_id, str(task_id))
        gate.set()
        final = await manager.wait(task_id)
        saved = store.load(parent.loop_id, str(task_id))
        passed = (initial.store_revision == 0
                  and initial.checkpoint.status is SpawnedTaskStatus.RUNNING
                  and updated.store_revision == 1
                  and updated.checkpoint.update_count == 1
                  and saved.store_revision == 2
                  and saved.checkpoint.status is SpawnedTaskStatus.SUCCEEDED
                  and final.status is SpawnedTaskStatus.SUCCEEDED)
        return {"passed": passed,
                "detail": "saved revisions advanced start 0, update 1, terminal 2"}


async def _automatic_cancel_case() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="spawned-cancel-store-") as root:
        gate = asyncio.Event()

        async def executor(_request):
            await gate.wait()
            raise AssertionError("canceled executor resumed")

        parent = _parent("cancel persistence owner")
        store = LocalJsonSpawnedTaskStateStore(root)
        manager = SpawnedTaskManager(
            parent, executor,
            services=SpawnedTaskServices(state_store=store))
        task_id = await manager.start_async(_spec())
        manager.cancel(task_id, "save cancellation")
        await manager.wait(task_id)
        saved = store.load(parent.loop_id, str(task_id))
        return {"passed": (
                    saved.store_revision == 1
                    and saved.checkpoint.status is SpawnedTaskStatus.CANCELED
                    and saved.checkpoint.result is not None
                    and saved.checkpoint.result.error_code == "CANCELED"),
                "detail": "cancellation replaced running durable state once"}


async def _interrupted_load_and_restart_case() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="spawned-restart-store-") as root:
        gate = asyncio.Event()

        async def waiting(_request):
            await gate.wait()
            raise AssertionError("original task resumed")

        original_parent = _parent("restart persistence owner")
        original = SpawnedTaskManager(original_parent, waiting)
        old_id = await original.start_async(_spec())
        active = original.checkpoint(old_id)
        original.cancel(old_id, "capture simulated crash")
        await original.wait(old_id)

        store = LocalJsonSpawnedTaskStateStore(root)
        store.create(original_parent.loop_id, active)
        restored_parent = _parent("restart persistence owner")
        restored = SpawnedTaskManager(
            restored_parent,
            services=SpawnedTaskServices(state_store=store))
        snapshots = restored.load_saved_checkpoints()
        old_saved = store.load(restored_parent.loop_id, str(old_id))
        new_id = restored.restart_as_new_attempt(old_id)
        new_snapshot = restored.status(new_id)
        all_saved = store.load_owner(restored_parent.loop_id)
        restart_events = [event for event in restored_parent.ledger.events
                          if event.get("custom_kind")
                          == "spawned_task_restarted_as_new_attempt"]
        return {
            "interrupted": (
                len(snapshots) == 1
                and snapshots[0].status is SpawnedTaskStatus.INTERRUPTED
                and snapshots[0].result.error_code == "INTERRUPTED_ON_RESTORE"
                and old_saved.store_revision == 1
                and old_saved.checkpoint.status is SpawnedTaskStatus.INTERRUPTED),
            "restarted": (
                new_id != old_id and str(new_id).endswith(".spawned-task.2")
                and new_snapshot.status is SpawnedTaskStatus.SUCCEEDED
                and len(all_saved) == 2 and len(restart_events) == 1
                and restart_events[0]["previous_task_id"] == str(old_id)
                and restart_events[0]["new_task_id"] == str(new_id)),
            "detail": "active metadata closed as interrupted; attempt 2 ran fresh",
        }


def _concurrent_cas_case() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="spawned-cas-store-") as root:
        parent = _parent("CAS owner")
        manager = SpawnedTaskManager(parent)
        task_id = manager.start(_spec())
        terminal = manager.checkpoint(task_id)
        running = replace(
            terminal, status=SpawnedTaskStatus.RUNNING, result=None,
            steps_run=0, model_calls=0, checkpoint_digest="")
        replacement = _interrupted(running)
        store = LocalJsonSpawnedTaskStateStore(root)
        expected = store.create(parent.loop_id, running)

        def attempt(_index):
            try:
                LocalJsonSpawnedTaskStateStore(root).compare_and_swap(
                    expected, replacement)
            except SpawnedTaskStateConflict:
                return "conflict"
            return "stored"

        with ThreadPoolExecutor(max_workers=2) as workers:
            threaded = sorted(workers.map(attempt, range(2)))
        process_ok = True
        if store.process_locking_supported:
            import multiprocessing
            with tempfile.TemporaryDirectory(
                    prefix="spawned-process-cas-") as second_root:
                second_store = LocalJsonSpawnedTaskStateStore(second_root)
                process_expected = second_store.create(parent.loop_id, running)
                context = multiprocessing.get_context("fork")
                start = context.Event(); output = context.Queue()
                processes = [context.Process(
                    target=_process_cas,
                    args=(second_root, process_expected.to_json(),
                          replacement.to_json(), start, output))
                    for _index in range(2)]
                for process in processes:
                    process.start()
                start.set()
                outcomes = sorted(output.get(timeout=5) for _ in processes)
                for process in processes:
                    process.join(timeout=5)
                process_ok = outcomes == ["conflict", "stored"] \
                    and all(process.exitcode == 0 for process in processes)
        return {"passed": threaded == ["conflict", "stored"] and process_ok,
                "detail": "CAS allowed one thread and one process winner"}


def _process_cas(root: str, expected_json: str, replacement_json: str,
                 start, output) -> None:
    expected = StoredSpawnedTaskState.from_json(expected_json)
    replacement = SpawnedTaskCheckpoint.from_json(replacement_json)
    start.wait(timeout=5)
    try:
        LocalJsonSpawnedTaskStateStore(root).compare_and_swap(
            expected, replacement)
    except SpawnedTaskStateConflict:
        output.put("conflict")
    else:
        output.put("stored")
