"""Dependency-wave software work executed through the canonical Loop runtime.

The plan, attempts, outputs, and results are passive records. A starting
Solution Loop coordinates waves and spawns one Solution Loop per attempt.
The service reuses ``LoopGraphDefinition`` for graph authority and the
canonical parallel runner for safe overlap. It creates no task runtime.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable, Mapping

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
from ..parallel_runner import BranchSpec, SchedulingConfiguration, run_parallel
from .development_planning import (
    PlanDefinition, RetryPolicy, TaskLoopBinding,
    TerminalPlanCode, compile_execution_waves, compile_plan_to_loop_graph,
)


_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class DevelopmentExecutionError(ValueError):
    """A development execution request or result is not governable."""


@dataclass(frozen=True)
class TaskAttemptDefinition:
    attempt_id: str
    task_id: str
    operation_ref: str
    executable_delta_digest: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
                self.attempt_id, self.task_id, self.operation_ref)):
            raise DevelopmentExecutionError("task attempt identity is incomplete")
        if not _DIGEST.fullmatch(self.executable_delta_digest):
            raise DevelopmentExecutionError("attempt delta needs SHA-256")


@dataclass(frozen=True)
class TaskOperationOutput:
    value: object
    artifact_refs: tuple[str, ...]
    verified_criterion_ids: tuple[str, ...]
    verification_evidence_refs: tuple[str, ...]
    passed: bool
    failure_class: str = ""

    def __post_init__(self) -> None:
        for label, values in (
                ("artifact_refs", self.artifact_refs),
                ("verified_criterion_ids", self.verified_criterion_ids),
                ("verification_evidence_refs", self.verification_evidence_refs)):
            if (any(not isinstance(value, str) or not value.strip()
                    for value in values)
                    or len(values) != len(set(values))):
                raise DevelopmentExecutionError(
                    f"{label} needs unique non-empty references")
        if self.passed and (not self.artifact_refs
                            or not self.verification_evidence_refs):
            raise DevelopmentExecutionError(
                "passing task output needs artifact and verification evidence")
        if not self.passed and not self.failure_class:
            raise DevelopmentExecutionError(
                "failed task output needs a failure class")


@dataclass(frozen=True)
class DevelopmentExecutionRequest:
    plan: PlanDefinition
    bindings: tuple[TaskLoopBinding, ...]
    attempts: tuple[TaskAttemptDefinition, ...]
    retry_policies: tuple[tuple[str, RetryPolicy], ...]
    maximum_concurrency: int = 4

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PlanDefinition):
            raise DevelopmentExecutionError("execution needs PlanDefinition")
        if self.maximum_concurrency < 1:
            raise DevelopmentExecutionError("maximum concurrency must be positive")
        task_ids = {item.task_id for item in self.plan.task_slices}
        bindings = tuple(self.bindings)
        attempts = tuple(self.attempts)
        policies = tuple(self.retry_policies)
        if ({item.task_id for item in bindings} != task_ids
                or len(bindings) != len(task_ids)):
            raise DevelopmentExecutionError(
                "execution needs one exact binding per task")
        if (any(not isinstance(item, TaskAttemptDefinition)
                for item in attempts)
                or {item.task_id for item in attempts} != task_ids
                or len({item.attempt_id for item in attempts}) != len(attempts)):
            raise DevelopmentExecutionError(
                "execution needs unique typed attempts for every task")
        policy_map = dict(policies)
        if (len(policy_map) != len(policies)
                or set(policy_map) != task_ids
                or any(not isinstance(value, RetryPolicy)
                       for value in policy_map.values())):
            raise DevelopmentExecutionError(
                "execution needs one retry policy per task")
        binding_map = {item.task_id: item for item in bindings}
        for task_id in sorted(task_ids):
            selected = [item for item in attempts if item.task_id == task_id]
            if selected[0].operation_ref != binding_map[task_id].operation_ref:
                raise DevelopmentExecutionError(
                    "first attempt must match the compiled task operation")
            if len(selected) > policy_map[task_id].maximum_attempts:
                raise DevelopmentExecutionError("attempts exceed retry policy")
            if (len({item.executable_delta_digest for item in selected})
                    != len(selected)
                    or len({item.operation_ref for item in selected})
                    != len(selected)):
                raise DevelopmentExecutionError(
                    "every retry needs a distinct executable delta")
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "retry_policies", policies)


@dataclass(frozen=True)
class TaskAttemptResult:
    task_id: str
    attempt_id: str
    loop_id: str
    operation_ref: str
    passed: bool
    failure_class: str
    error: str
    artifact_refs: tuple[str, ...]
    verification_evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class TaskExecutionState:
    task_id: str
    status: str
    attempt_results: tuple[TaskAttemptResult, ...]
    value: object = None
    blocked_reason: str = ""


@dataclass(frozen=True)
class DevelopmentExecutionResult:
    plan_id: str
    plan_digest: str
    graph_digest: str
    waves: tuple[tuple[str, ...], ...]
    task_states: tuple[TaskExecutionState, ...]
    terminal_code: TerminalPlanCode
    controller_loop_id: str
    run_history_events: int
    model_calls: int
    elapsed_seconds: float


def _attempts_by_task(request: DevelopmentExecutionRequest):
    return {task.task_id: tuple(
        attempt for attempt in request.attempts
        if attempt.task_id == task.task_id)
        for task in request.plan.task_slices}


def execute_development_plan(
        request: DevelopmentExecutionRequest,
        operation_registry: Mapping[str, Callable], *,
        ledger: LoopLedger | None = None) -> DevelopmentExecutionResult:
    """Execute safe dependency waves and stop honestly on blocked work."""
    if not isinstance(request, DevelopmentExecutionRequest):
        raise DevelopmentExecutionError("typed execution request required")
    operations = dict(operation_registry)
    unresolved = sorted({item.operation_ref for item in request.attempts}
                        - set(operations))
    if unresolved or any(not callable(value) for value in operations.values()):
        raise DevelopmentExecutionError(
            f"attempt operations are unresolved: {unresolved}")
    graph = compile_plan_to_loop_graph(request.plan, request.bindings)
    execution = compile_execution_waves(request.plan)
    by_task = {item.task_id: item for item in request.plan.task_slices}
    retry_by_task = dict(request.retry_policies)
    attempts_by_task = _attempts_by_task(request)
    states: dict[str, TaskExecutionState] = {}
    result_lock = threading.Lock()
    spawn_lock = threading.Lock()
    shared_ledger = ledger or LoopLedger(
        id_namespace=f"development.{request.plan.content_digest[:12]}")
    controller = Loop(
        f"execute development plan {request.plan.plan_id}",
        LoopConfig(
            framework="custom",
            custom_steps=tuple(
                f"wave_{index}" for index in range(1, len(execution.waves) + 1)),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            exit_condition="steps_complete", power="light"),
        ledger=shared_ledger,
        identity=LoopRoleIdentity(LoopRole.SOLUTION, "solution.pipeline"),
        relationship=LoopRelationship.starting())
    started = time.monotonic()

    def run_task(task_id: str):
        task = by_task[task_id]
        prior_values = {
            dependency: states[dependency].value
            for dependency in task.dependency_ids
        }
        recorded = []
        for attempt_index, attempt in enumerate(attempts_by_task[task_id]):
            with spawn_lock:
                spawned = controller.spawn(
                    f"execute {task_id} attempt {attempt.attempt_id}",
                    LoopConfig(
                        framework="custom", custom_steps=("execute",),
                        allowable_modes=("deterministic",),
                        preferred_modes=("deterministic",),
                        delegated_modes=("deterministic",),
                        exit_condition="steps_complete", power="light"),
                    identity=LoopRoleIdentity(
                        LoopRole.SOLUTION, "solution.atomic_component"),
                    relationship=LoopRelationship.spawned_by(
                        controller.loop_id))
            holder = {}

            def task_handler(_loop, _step, _context):
                try:
                    holder["output"] = operations[attempt.operation_ref](
                        task, prior_values)
                    if not isinstance(holder["output"], TaskOperationOutput):
                        raise DevelopmentExecutionError(
                            "task operation must return TaskOperationOutput")
                except Exception as exc:  # normalized at this boundary
                    holder["error"] = exc
                return StepOutcome(
                    output=("task:attempted" if "error" not in holder
                            else f"task:error:{type(holder['error']).__name__}"),
                    mode="deterministic",
                    confidence=0.95 if "error" not in holder else 0.2)

            spawned.run(handler=task_handler, max_steps=2)
            output = holder.get("output")
            error = holder.get("error")
            if error is not None:
                failure_class = "execution_error"
                passed = False
                artifact_refs = ()
                evidence_refs = ()
                error_text = f"{type(error).__name__}: {error}"[:320]
            else:
                required = {item.criterion_id for item in task.verifications}
                verified = set(output.verified_criterion_ids)
                passed = (output.passed and required <= verified
                          and bool(output.artifact_refs)
                          and bool(output.verification_evidence_refs))
                failure_class = "" if passed else (
                    output.failure_class or "verification_failed")
                artifact_refs = output.artifact_refs
                evidence_refs = output.verification_evidence_refs
                error_text = "" if passed else "verification obligations unmet"
            result = TaskAttemptResult(
                task_id, attempt.attempt_id, spawned.loop_id,
                attempt.operation_ref, passed, failure_class, error_text,
                artifact_refs, evidence_refs)
            recorded.append(result)
            if passed:
                state = TaskExecutionState(
                    task_id, "completed", tuple(recorded), output.value)
                with result_lock:
                    states[task_id] = state
                return state
            policy = retry_by_task[task_id]
            retryable = failure_class in policy.allowed_failure_classes
            has_next = attempt_index + 1 < len(attempts_by_task[task_id])
            if not (retryable and has_next):
                break
        state = TaskExecutionState(
            task_id, "blocked", tuple(recorded), blocked_reason=(
                recorded[-1].failure_class or "repair_unavailable"))
        with result_lock:
            states[task_id] = state
        return state

    def controller_handler(_loop, step, _context):
        wave_index = int(step.rsplit("_", 1)[1]) - 1
        wave = execution.waves[wave_index]
        runnable = []
        for task_id in wave:
            blocked_dependencies = tuple(
                dependency for dependency in by_task[task_id].dependency_ids
                if states.get(dependency, TaskExecutionState(
                    dependency, "pending", ())).status != "completed")
            if blocked_dependencies:
                states[task_id] = TaskExecutionState(
                    task_id, "blocked", (), blocked_reason=(
                        "blocked dependencies: " + ", ".join(blocked_dependencies)))
            else:
                runnable.append(task_id)
        if runnable:
            branches = tuple(BranchSpec(
                task_id, run_task, contract=by_task[task_id].concurrency,
                args=(task_id,)) for task_id in runnable)
            run_parallel(branches, config=SchedulingConfiguration(
                scheduling_pattern="bounded_fanout",
                maximum_concurrency=min(
                    request.maximum_concurrency, len(branches)),
                join_policy="all", failure_policy="isolate"))
        completed = sum(states.get(task_id, TaskExecutionState(
            task_id, "pending", ())).status == "completed" for task_id in wave)
        return StepOutcome(
            output=f"{step}:{completed}/{len(wave)} completed",
            mode="deterministic",
            confidence=0.95 if completed == len(wave) else 0.5)

    controller_result = controller.run(
        handler=controller_handler, max_steps=len(execution.waves) + 1)
    ordered_states = tuple(states[task.task_id] for task in request.plan.task_slices)
    terminal = (TerminalPlanCode.COMPLETED_VERIFIED
                if all(item.status == "completed" for item in ordered_states)
                else TerminalPlanCode.TASKS_BLOCKED)
    return DevelopmentExecutionResult(
        request.plan.plan_id, request.plan.content_digest,
        graph.content_digest, execution.waves, ordered_states, terminal,
        controller.loop_id, len(shared_ledger.events),
        controller_result.model_calls,
        round(time.monotonic() - started, 3))


__all__ = (
    "DevelopmentExecutionError", "DevelopmentExecutionRequest",
    "DevelopmentExecutionResult", "TaskAttemptDefinition",
    "TaskAttemptResult", "TaskExecutionState", "TaskOperationOutput",
    "execute_development_plan",
)
