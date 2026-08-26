"""Focused offline checks for ``delegation_runtime``.

The checks live outside the runtime module so the lifecycle implementation
stays below the repository size cap. ``delegation_runtime.self_test`` remains
the single collection point used by the package test suite.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Any

from ..core.context_artifacts import (
    ContextArtifactManager,
    ContextArtifactRef,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
    ContextOffloadPolicy,
)
from ..core.runtime_memory import RunNoteBoard
from .spawned_runtime_port import (
    SpawnedLoopRuntimeConfigFacts,
    SpawnedLoopRuntimeCounters,
    SpawnedLoopRuntimeMemoryPort,
    SpawnedLoopRuntimeOutcome,
    SpawnedLoopRuntimePort,
    SpawnedStepRequest,
    RuntimeMemoryService,
)
from .delegation_runtime import (
    SpawnedExecutionRequest,
    SpawnedLoopResult,
    SpawnedTaskManager,
    SpawnedTaskStatus,
    SpawnedTaskUpdate,
    ContextVisibilityPolicy,
    DelegationBudget,
    DelegationConstraints,
    DelegationError,
    DelegationSpec,
    LoopPortValue,
)
from .loop_contract import LoopContract
from .loop_profile_catalog import LoopProfileRef, resolve_profile_alias
from .loop_role import (LoopRelationship, LoopRelationshipKind, LoopRole,
                        LoopRoleIdentity)
from .recursive_loop import MODES, Loop, LoopConfig, StepOutcome


def _solution_spec(**changes: Any) -> DelegationSpec:
    values: dict[str, Any] = {
        "goal": "normalize one customer row",
        "profile": LoopProfileRef("solution.atomic_component"),
        "contract": LoopContract(
            "normalize-row",
            "code_only",
            input_roles=("raw_row/v1",),
            output_roles=("clean_row/v1",),
        ),
        "inputs": (LoopPortValue("raw_row/v1", {"name": " Ada "}),),
        "constraints": DelegationConstraints(
            available_fields=("operation_ref",),
            capability_refs=("solution_canvas", "component_execution"),
        ),
    }
    values.update(changes)
    return DelegationSpec(**values)


def run_checks() -> dict:
    """Run positive, adversarial, budget, and asynchronous lifecycle checks."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    policy = ContextVisibilityPolicy()
    check(
        "default_context_is_fresh_private_and_summary_only",
        policy.fresh and not policy.selected_refs
        and not policy.shared_runtime_memory and policy.summary_return,
        "the default shares no parent references or Runtime Memory",
    )

    matrix = _role_relationship_matrix()
    check(
        "any_root_role_can_spawn_any_permitted_spawned_role",
        matrix["passed"],
        matrix["detail"],
    )

    parent = Loop(
        "prepare customer data",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ),
    )
    manager = SpawnedTaskManager(parent)
    task_id = manager.start(_solution_spec())
    snapshot = manager.status(task_id)
    check(
        "deterministic_spawned_uses_existing_loop_and_typed_result",
        snapshot.status == SpawnedTaskStatus.SUCCEEDED
        and snapshot.result is not None
        and tuple(value.role for value in snapshot.result.outputs)
        == ("clean_row/v1",)
        and parent.audit_closure()["orphaned_spawned_loops"] == [],
        "the spawned was spawned and closed through the existing Loop runtime",
    )
    public_fields = set(SpawnedLoopResult.__dataclass_fields__)
    check(
        "public_result_has_no_spawned_internals",
        not ({"loop", "ledger", "events", "messages", "tool_output"}
             & public_fields),
        "the public result carries typed outputs and counters only",
    )
    request_fields = set(SpawnedExecutionRequest.__dataclass_fields__)
    check(
        "public_request_replaces_loop_with_spawned_runtime_port",
        request_fields == {
            "task_id", "runtime", "spec", "control", "runtime_memory"}
        and "loop" not in request_fields,
        "the request has a spawned-only runtime port and no Loop field",
    )
    public_types = (
        SpawnedLoopRuntimePort, SpawnedLoopRuntimeConfigFacts, SpawnedLoopRuntimeCounters,
        SpawnedLoopRuntimeOutcome, SpawnedStepRequest, SpawnedLoopRuntimeMemoryPort,
        RuntimeMemoryService,
    )
    check(
        "spawned_runtime_contract_is_typed",
        all(value is not None for value in public_types),
        "identity, relationship, config, counters, run, cancel, and memory "
        "are typed without exposing a Loop",
    )

    private_case = _private_context_case()
    check(
        "default_executor_request_cannot_reach_parent_goal_or_ledger",
        private_case["passed"],
        private_case["detail"],
    )

    def spawned_cancel_executor(
            request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        counters = request.runtime.cancel("spawned executor stopped cleanly")
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.CANCELED,
            terminal_code=counters.terminal_code,
            steps_run=counters.steps_run,
            model_calls=counters.model_calls,
            error_code="CANCELED",
            error="spawned executor stopped cleanly",
        )

    cancel_manager = SpawnedTaskManager(parent, spawned_cancel_executor)
    spawned_canceled = cancel_manager.status(
        cancel_manager.start(_solution_spec()))
    check(
        "spawned_runtime_port_can_cancel_without_exposing_loop",
        spawned_canceled.status == SpawnedTaskStatus.CANCELED
        and parent.audit_closure()["orphaned_spawned_loops"] == [],
        "the typed cancel port closed the private spawned",
    )

    bad_input_refused = False
    before = len(parent.ledger.events)
    try:
        _solution_spec(inputs=(LoopPortValue("wrong/v1", "value"),))
    except DelegationError:
        bad_input_refused = True
    check(
        "input_roles_fail_closed_before_spawn",
        bad_input_refused and len(parent.ledger.events) == before,
        "an input outside the contract creates no spawned",
    )

    mode_refused = False
    hybrid_contract = LoopContract(
        "hybrid-spawned", "hybrid", output_roles=("answer/v1",))
    try:
        manager.start(DelegationSpec(
            goal="interpret one exception",
            profile=LoopProfileRef("practitioner.verifier"),
            contract=hybrid_contract,
            mode="hybrid",
            budget=DelegationBudget(max_model_calls=1),
            llm_thinking_power="medium",
            constraints=DelegationConstraints(
                available_fields=("claim_set", "acceptance_rule"),
                capability_refs=(
                    "loop_spawn", "run_history_write",
                    "independent_verification")),
        ))
    except DelegationError:
        mode_refused = True
    check(
        "parent_delegation_authority_is_enforced",
        mode_refused,
        "a deterministic-only delegation authority refused a hybrid spawned",
    )

    def wrong_output(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        loop_result = request.runtime.run(max_steps=1)
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("wrong/v1", "value"),),
            summary="one result",
            terminal_code=loop_result.counters.terminal_code,
            steps_run=loop_result.counters.steps_run,
        )

    wrong_manager = SpawnedTaskManager(parent, wrong_output)
    wrong_id = wrong_manager.start(_solution_spec())
    wrong_snapshot = wrong_manager.status(wrong_id)
    check(
        "wrong_output_contract_becomes_a_typed_failure",
        wrong_snapshot.status == SpawnedTaskStatus.FAILED
        and wrong_snapshot.result is not None
        and wrong_snapshot.result.error_code == "EXECUTOR_FAILED",
        "an executor cannot publish an undeclared output role",
    )

    def bypass_loop(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean_row/v1", "value"),),
            summary="one result",
            terminal_code="ACCEPTED",
        )

    bypass_manager = SpawnedTaskManager(parent, bypass_loop)
    bypass_id = bypass_manager.start(_solution_spec())
    bypass = bypass_manager.status(bypass_id)
    check(
        "executor_cannot_bypass_the_spawned_loop",
        bypass.status == SpawnedTaskStatus.FAILED
        and bypass.result is not None
        and bypass.result.error_code == "EXECUTOR_FAILED",
        "the manager refused a result from a spawned Loop that never terminated",
    )

    def oversized_output(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        loop_result = request.runtime.run(max_steps=1)
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean_row/v1", "x" * 100),),
            summary="oversized",
            terminal_code=loop_result.counters.terminal_code,
            steps_run=loop_result.counters.steps_run,
        )

    budget_manager = SpawnedTaskManager(parent, oversized_output)
    budget_id = budget_manager.start(_solution_spec(
        budget=DelegationBudget(max_output_bytes=20)))
    over_budget = budget_manager.status(budget_id)
    check(
        "output_budget_fails_closed",
        over_budget.status == SpawnedTaskStatus.FAILED
        and over_budget.result is not None
        and over_budget.result.error_code == "EXECUTOR_FAILED",
        "an oversized output was not published",
    )

    memory_destination_refused = False
    try:
        _solution_spec(return_destination="shared_runtime_memory")
    except DelegationError:
        memory_destination_refused = True
    check(
        "runtime_memory_return_requires_explicit_sharing",
        memory_destination_refused,
        "a destination cannot grant Runtime Memory access",
    )
    memory_case = _runtime_memory_case()
    check(
        "runtime_memory_is_available_only_through_explicit_typed_service",
        memory_case["passed"],
        memory_case["detail"],
    )
    artifact_case = _context_artifact_case()
    check(
        "fresh_spawned_offloads_large_text_and_keeps_small_values_inline",
        artifact_case["passed"],
        artifact_case["detail"],
    )

    check(
        "async_executor_uses_the_same_lifecycle",
        asyncio.run(_async_case()),
        "start, status, update, wait, and typed return work asynchronously",
    )
    check(
        "async_spawned_can_be_canceled_without_an_orphan",
        asyncio.run(_cancel_case()),
        "cancel closes the spawned Loop and preserves terminal status",
    )
    from .delegation_checkpoint_checks import run_checkpoint_checks
    tests.extend(run_checkpoint_checks())

    passed = sum(1 for test in tests if test["passed"])
    return {
        "record_type": "delegation_runtime_self_test",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def _private_context_case() -> dict[str, Any]:
    goal_marker = "PARENT_GOAL_SECRET_7b8f"
    ledger_marker = "PARENT_LEDGER_SECRET_91c2"
    observed: dict[str, Any] = {}

    def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        runtime_public = {
            name for name in dir(request.runtime)
            if not name.startswith("_")}
        request_public = set(SpawnedExecutionRequest.__dataclass_fields__)
        forbidden = {"loop", "ledger", "parent", "goal", "events"}
        step_safe = {"value": False}

        def handler(step_request: SpawnedStepRequest) -> StepOutcome:
            step_fields = set(SpawnedStepRequest.__dataclass_fields__)
            step_safe["value"] = not (forbidden & step_fields)
            return StepOutcome(
                output=f"{step_request.step}:private",
                mode="deterministic")

        result = request.runtime.run(handler=handler)
        surfaces = " ".join((
            repr(request), repr(request.runtime), repr(request.runtime.config),
            repr(request.runtime.counters),
            repr(request.runtime.relationship)))
        observed.update({
            "request_safe": not (forbidden & request_public),
            "runtime_safe": not (forbidden & runtime_public),
            "markers_absent": goal_marker not in surfaces
            and ledger_marker not in surfaces,
            "step_safe": step_safe["value"],
            "memory_absent": request.runtime_memory is None,
            "identity": request.runtime.loop_id == result.loop_id,
            "relationship": bool(
                request.runtime.relationship.spawned_by_loop_id),
            "config": request.runtime.config.allowable_modes
            == ("deterministic",),
            "counters": result.counters.steps_run > 0
            and result.counters.terminal,
        })
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean_row/v1", dict(observed)),),
            summary="Inspected only the documented spawned request surface.",
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
            model_calls=result.counters.model_calls,
        )

    parent = Loop(
        f"prepare customer data {goal_marker}",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ))
    parent.ledger.record(
        loop_id=parent.loop_id, event="custom", secret=ledger_marker)
    manager = SpawnedTaskManager(parent, executor)
    task = manager.status(manager.start(_solution_spec()))
    passed = (
        task.status == SpawnedTaskStatus.SUCCEEDED
        and task.result is not None
        and all(observed.values())
        and parent.audit_closure()["orphaned_spawned_loops"] == [])
    return {
        "passed": passed,
        "detail": (
            "sync executor saw spawned identity, relationship, config, and "
            "counters but no public parent goal or ledger path"),
    }


def _runtime_memory_case() -> dict[str, Any]:
    parent = Loop(
        "parent with explicit Runtime Memory service",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ))
    parent.ledger.record(
        loop_id=parent.loop_id, event="custom",
        secret="LEDGER_ONLY_NOT_A_MEMORY_NOTE")
    board = RunNoteBoard("delegation-memory", ledger=parent.ledger)
    shared = ContextVisibilityPolicy(shared_runtime_memory=True)
    no_service_refused = False
    before = len(parent.ledger.events)
    try:
        SpawnedTaskManager(parent).start(_solution_spec(context=shared))
    except DelegationError:
        no_service_refused = True
    after_refusal = len(parent.ledger.events)

    observed = {}

    def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        memory = request.runtime_memory
        public = {name for name in dir(memory) if not name.startswith("_")}
        written = memory.write("spawned-only note", topic="test")
        read = memory.read(topic="test")
        searched = memory.search("spawned-only")
        result = request.runtime.run()
        observed.update({
            "typed": isinstance(memory, SpawnedLoopRuntimeMemoryPort),
            "no_ledger": "ledger" not in public and "service" not in public,
            "bound_identity": memory.loop_id == request.runtime.loop_id,
            "write": written["loop_id"] == request.runtime.loop_id,
            "read": len(read) == 1 and read[0]["note"] == "spawned-only note",
            "search": len(searched) == 1,
            "ledger_secret_absent": all(
                note["note"] != "LEDGER_ONLY_NOT_A_MEMORY_NOTE"
                for note in read),
        })
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("clean_row/v1", "memory-bound"),),
            summary="Used the explicit Runtime Memory port.",
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
            model_calls=result.counters.model_calls,
        )

    manager = SpawnedTaskManager(parent, executor, runtime_memory=board)
    task = manager.status(manager.start(_solution_spec(context=shared)))
    return {
        "passed": (
            no_service_refused and after_refusal == before
            and task.status == SpawnedTaskStatus.SUCCEEDED
            and all(observed.values())),
        "detail": (
            "sharing without a service was refused; explicit memory read/write "
            "worked without exposing the ledger"),
    }


def _context_artifact_case() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="delegation-context-") as root:
        store = ContextArtifactStore(ContextArtifactStoreSpec(root))
        artifacts = ContextArtifactManager(
            store,
            ContextOffloadPolicy(max_inline_bytes=16, max_inline_tokens=4))
        parent = Loop(
            "offload fresh spawned input",
            LoopConfig(
                allowable_modes=("deterministic",),
                preferred_modes=("deterministic",),
                delegated_modes=("deterministic",),
            ))
        observed: dict[str, Any] = {}

        def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
            value = request.spec.inputs[0].value
            result = request.runtime.run()
            if isinstance(value, ContextArtifactRef):
                observed["large_ref"] = value
                output = "large-reference"
            else:
                observed["small_value"] = value
                output = "small-inline"
            return SpawnedLoopResult(
                request.task_id,
                SpawnedTaskStatus.SUCCEEDED,
                outputs=(LoopPortValue("clean_row/v1", output),),
                summary="Observed the typed spawned input port.",
                terminal_code=result.counters.terminal_code,
                steps_run=result.counters.steps_run,
            )

        manager = SpawnedTaskManager(
            parent, executor, context_artifacts=artifacts)
        large_text = "large context value " * 20
        large_spec = _solution_spec(inputs=(
            LoopPortValue("raw_row/v1", large_text),))
        large = manager.status(manager.start(large_spec))
        small_text = "small"
        small = manager.status(manager.start(_solution_spec(inputs=(
            LoopPortValue("raw_row/v1", small_text),))))
        reference = observed.get("large_ref")
        start_events = [
            event for event in parent.ledger.events
            if event.get("custom_kind") == "spawned_task_started"]
        passed = (
            large.status == SpawnedTaskStatus.SUCCEEDED
            and small.status == SpawnedTaskStatus.SUCCEEDED
            and isinstance(reference, ContextArtifactRef)
            and store.get_text(reference) == large_text
            and observed.get("small_value") == small_text
            and isinstance(observed.get("small_value"), str)
            and isinstance(large_spec.inputs[0].value, str)
            and any(event.get("offloaded_input_roles") == ("raw_row/v1",)
                    for event in start_events)
            and any(not event.get("offloaded_input_roles")
                    for event in start_events))
        return {
            "passed": passed,
            "detail": (
                "large UTF-8 text became a digest-addressed ContextArtifactRef; "
                "the exact small string stayed inline"),
        }


def _role_relationship_matrix() -> dict[str, Any]:
    """Exercise all nine root-role to spawned-role combinations."""
    root_profiles = {
        LoopRole.PRACTITIONER: (
            "practitioner.solver", "non_deterministic"),
        LoopRole.INTELLIGENCE: (
            "intelligence.user_feedback.interpret", "hybrid"),
        LoopRole.SOLUTION: (
            "solution.atomic_component", "deterministic"),
    }
    spawned_profiles = {
        LoopRole.PRACTITIONER: {
            "profile": resolve_profile_alias("verifier"),
            "mode": "non_deterministic",
            "fields": ("claim_set", "acceptance_rule"),
            "capabilities": (
                "loop_spawn", "run_history_write",
                "independent_verification"),
        },
        LoopRole.INTELLIGENCE: {
            "profile": resolve_profile_alias("intelligence.interpret"),
            "mode": "hybrid",
            "fields": ("guidance_ref", "task_context"),
            "capabilities": (
                "intelligence_reference", "guidance_interpretation"),
        },
        LoopRole.SOLUTION: {
            "profile": resolve_profile_alias("solution.component"),
            "mode": "deterministic",
            "fields": ("operation_ref",),
            "capabilities": ("solution_canvas", "component_execution"),
        },
    }

    def executor(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        result = request.runtime.run(
            handler=lambda step_request: StepOutcome(
                output=f"{step_request.step}:complete",
                mode=request.spec.mode),
            max_steps=request.spec.budget.max_iterations,
        )
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue("result/v1", {
                "spawned_loop_id": request.runtime.loop_id,
                "spawning_loop_id":
                    request.runtime.relationship.spawned_by_loop_id,
                "spawned_mode": request.runtime.config.allowable_modes[0],
            }),),
            summary="Completed one role compatibility case.",
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
            model_calls=result.counters.model_calls,
        )

    observed: list[tuple[str, str, str, str]] = []
    for root_role, (root_profile, root_mode) in root_profiles.items():
        root = Loop(
            f"root {root_role.value}",
            LoopConfig(
                allowable_modes=(root_mode,),
                preferred_modes=(root_mode,),
                delegated_modes=MODES,
            ),
            identity=LoopRoleIdentity(root_role, root_profile),
            relationship=LoopRelationship.starting(),
        )
        for spawned_role, values in spawned_profiles.items():
            mode = values["mode"]
            contract_mode = {
                "deterministic": "code_only",
                "hybrid": "hybrid",
                "non_deterministic": "model_led",
            }[mode]
            manager = SpawnedTaskManager(root, executor)
            task_id = manager.start(DelegationSpec(
                goal=f"spawned {spawned_role.value}",
                profile=values["profile"],
                contract=LoopContract(
                    f"{root_role.value}-{spawned_role.value}",
                    contract_mode,
                    output_roles=("result/v1",),
                ),
                mode=mode,
                budget=DelegationBudget(max_model_calls=1),
                constraints=DelegationConstraints(
                    available_fields=values["fields"],
                    capability_refs=values["capabilities"],
                ),
            ))
            snapshot = manager.status(task_id)
            if (snapshot.status != SpawnedTaskStatus.SUCCEEDED
                    or snapshot.result is None):
                return {
                    "passed": False,
                    "detail": (
                        f"{root_role.value} could not start "
                        f"{spawned_role.value}"),
                }
            output = snapshot.result.outputs[0].value
            observed.append((
                root_role.value,
                snapshot.identity.role.value,
                output["spawning_loop_id"],
                output["spawned_mode"],
            ))
            if (snapshot.relationship.kind
                    != LoopRelationshipKind.SPAWNED_BY
                    or snapshot.relationship.spawned_by_loop_id != root.loop_id
                    or snapshot.identity.role != spawned_role
                    or not output["spawned_loop_id"].startswith("loop")
                    or output["spawned_loop_id"] == root.loop_id
                    or output["spawning_loop_id"] != root.loop_id
                    or output["spawned_mode"] != mode):
                return {
                    "passed": False,
                    "detail": "an identity, relationship, or mode binding drifted",
                }
    return {
        "passed": len(observed) == 9,
        "detail": (
            "all 3 root roles started all 3 spawned roles; each spawned kept its "
            "own selected mode"),
    }


async def _async_case() -> bool:
    gate = asyncio.Event()
    goal_marker = "ASYNC_PARENT_GOAL_SECRET_a31f"
    ledger_marker = "ASYNC_PARENT_LEDGER_SECRET_b09c"

    async def async_executor(
            request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        await gate.wait()
        updates = request.control.updates()
        forbidden = {"loop", "ledger", "parent", "goal", "events"}
        runtime_public = {
            name for name in dir(request.runtime)
            if not name.startswith("_")}
        surfaces = " ".join((repr(request), repr(request.runtime),
                             repr(request.runtime.config),
                             repr(request.runtime.counters)))
        isolated = (
            not (forbidden & set(SpawnedExecutionRequest.__dataclass_fields__))
            and not (forbidden & runtime_public)
            and goal_marker not in surfaces
            and ledger_marker not in surfaces
            and request.runtime_memory is None)
        loop_result = request.runtime.run(max_steps=1)
        return SpawnedLoopResult(
            request.task_id,
            SpawnedTaskStatus.SUCCEEDED,
            outputs=(LoopPortValue(
                "clean_row/v1", {
                    "updates": len(updates), "isolated": isolated}),),
            summary="normalized after one parent update",
            terminal_code=loop_result.counters.terminal_code,
            steps_run=loop_result.counters.steps_run,
        )

    parent = Loop(
        f"prepare async customer data {goal_marker}",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ),
    )
    parent.ledger.record(
        loop_id=parent.loop_id, event="custom", secret=ledger_marker)
    manager = SpawnedTaskManager(parent, async_executor)
    task_id = await manager.start_async(_solution_spec())
    running = manager.status(task_id)
    updated = manager.update(
        task_id, SpawnedTaskUpdate(instruction="keep original casing"))
    gate.set()
    finished = await manager.wait(task_id)
    return (
        running.status == SpawnedTaskStatus.RUNNING
        and updated.updates == 1
        and finished.status == SpawnedTaskStatus.SUCCEEDED
        and finished.result is not None
        and finished.result.outputs[0].value
        == {"updates": 1, "isolated": True}
    )


async def _cancel_case() -> bool:
    gate = asyncio.Event()

    async def waiting_executor(
            request: SpawnedExecutionRequest) -> SpawnedLoopResult:
        await gate.wait()
        raise AssertionError("a canceled executor must not resume")

    parent = Loop(
        "cancel one spawned",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ),
    )
    manager = SpawnedTaskManager(parent, waiting_executor)
    task_id = await manager.start_async(_solution_spec())
    canceled = manager.cancel(task_id, "parent stopped the task")
    final = await manager.wait(task_id)
    return (
        canceled.status == SpawnedTaskStatus.CANCELED
        and final.status == SpawnedTaskStatus.CANCELED
        and parent.audit_closure()["orphaned_spawned_loops"] == []
    )
