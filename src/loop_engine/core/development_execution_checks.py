"""Executable proof for dependency waves, retry, verification, and blocking.

Owns focused runtime checks for the development execution service. It creates
no execution authority, provider substitute, or second graph.
"""
from __future__ import annotations

import hashlib
import threading

from ..scheduling import ConcurrencyContract
from .development_execution import (
    DevelopmentExecutionRequest, TaskAttemptDefinition, TaskOperationOutput,
    execute_development_plan,
)
from .development_planning import (
    PlanDefinition, PlanningAuthority, RequirementVerificationContract,
    RetryPolicy, TaskLoopBinding, TaskSliceDefinition, TerminalPlanCode,
)


def _verification(task_id: str) -> RequirementVerificationContract:
    return RequirementVerificationContract(
        f"criterion-{task_id}", f"{task_id} artifact is verified.",
        "artifact.inspect", ("artifact", "verification"),
        "verification_failed", True)


def _task(task_id: str, dependencies=()) -> TaskSliceDefinition:
    return TaskSliceDefinition(
        task_id, f"Execute {task_id}.", ("request",), (f"{task_id}/v1",),
        tuple(dependencies), (_verification(task_id),),
        ConcurrencyContract(
            reads=("workspace",), writes=(f"{task_id}.txt",),
            thread_safe=True, retry_safe=True),
        ("registered operation", "verified artifact"))


def _plan() -> PlanDefinition:
    return PlanDefinition(
        "development-execution", "original-task", "a" * 64,
        "Execute verified dependency work.", ("requested work",),
        ("unrelated work",), PlanningAuthority.AUTONOMOUS_LOW_RISK, (),
        (_task("task-a"), _task("task-b"),
         _task("task-c", ("task-a", "task-b"))))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _output(task_id: str, value) -> TaskOperationOutput:
    return TaskOperationOutput(
        value, (f"artifact:{task_id}",), (f"criterion-{task_id}",),
        (f"verification:{task_id}",), True)


def _request(attempts: tuple[TaskAttemptDefinition, ...]) \
        -> DevelopmentExecutionRequest:
    return DevelopmentExecutionRequest(
        _plan(), tuple(TaskLoopBinding(
            task_id, f"operation.{task_id}")
            for task_id in ("task-a", "task-b", "task-c")),
        attempts, tuple((task_id, RetryPolicy(
            f"retry-{task_id}", 2, ("test_failure",)))
            for task_id in ("task-a", "task-b", "task-c")), 3)


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    barrier = threading.Barrier(2, timeout=2.0)
    thread_ids = set()
    lock = threading.Lock()

    def parallel_operation(task, _dependencies):
        with lock:
            thread_ids.add(threading.get_ident())
        barrier.wait()
        return _output(task.task_id, task.task_id)

    def joined_operation(task, dependencies):
        return _output(task.task_id, tuple(sorted(dependencies)))

    first_attempts = tuple(TaskAttemptDefinition(
        f"attempt-{task_id}", task_id, f"operation.{task_id}",
        _digest(task_id)) for task_id in ("task-a", "task-b", "task-c"))
    completed = execute_development_plan(_request(first_attempts), {
        "operation.task-a": parallel_operation,
        "operation.task-b": parallel_operation,
        "operation.task-c": joined_operation,
    })
    check("independent_solution_loops_physically_overlap",
          len(thread_ids) == 2 and completed.elapsed_seconds < 2.0,
          f"threads={len(thread_ids)} elapsed={completed.elapsed_seconds}")
    check("dependencies_join_before_later_wave",
          completed.task_states[-1].value == ("task-a", "task-b"))
    check("verified_plan_completes_with_one_canonical_graph",
          completed.terminal_code is TerminalPlanCode.COMPLETED_VERIFIED
          and len(completed.graph_digest) == 64
          and completed.model_calls == 0
          and completed.run_history_events > 0)

    attempt_counts = {"task-a": 0}

    def fail_then_repair(task, _dependencies):
        attempt_counts[task.task_id] += 1
        return TaskOperationOutput(
            None, (), (), (), False, "test_failure")

    retry_attempts = (
        TaskAttemptDefinition("a-first", "task-a", "operation.task-a",
                              _digest("a-first")),
        TaskAttemptDefinition("a-repair", "task-a", "operation.task-a.repair",
                              _digest("a-repair")),
        TaskAttemptDefinition("b-first", "task-b", "operation.task-b",
                              _digest("b-first")),
        TaskAttemptDefinition("c-first", "task-c", "operation.task-c",
                              _digest("c-first")),
    )
    repaired = execute_development_plan(_request(retry_attempts), {
        "operation.task-a": fail_then_repair,
        "operation.task-a.repair": lambda task, dependencies: _output(
            task.task_id, "repaired"),
        "operation.task-b": lambda task, dependencies: _output(
            task.task_id, "independent"),
        "operation.task-c": joined_operation,
    })
    repaired_a = repaired.task_states[0]
    check("retry_uses_distinct_executable_delta",
          repaired_a.status == "completed"
          and len(repaired_a.attempt_results) == 2
          and repaired_a.attempt_results[0].operation_ref
          != repaired_a.attempt_results[1].operation_ref)

    blocked_attempts = tuple(TaskAttemptDefinition(
        f"blocked-{task_id}", task_id, f"operation.{task_id}",
        _digest(f"blocked-{task_id}"))
        for task_id in ("task-a", "task-b", "task-c"))
    blocked = execute_development_plan(_request(blocked_attempts), {
        "operation.task-a": fail_then_repair,
        "operation.task-b": lambda task, dependencies: _output(
            task.task_id, "independent"),
        "operation.task-c": joined_operation,
    })
    states = {item.task_id: item for item in blocked.task_states}
    check("blocked_is_terminal_and_independent_work_continues",
          blocked.terminal_code is TerminalPlanCode.TASKS_BLOCKED
          and states["task-a"].status == "blocked"
          and states["task-b"].status == "completed"
          and states["task-c"].status == "blocked")

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "development_execution_self_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
