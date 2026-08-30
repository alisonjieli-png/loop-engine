"""Executable checks for planning, assurance, handoff, and task waves.

Owns cross-domain structural and adversarial proof for passive plan records.
It does not execute a plan.
"""
from __future__ import annotations

from ..scheduling import ConcurrencyContract
from .development_planning import (
    AssuranceVerdict, ClarificationDisposition, ClarificationItem,
    DevelopmentPlanError, PlanDefinition, PlanningAuthority,
    RequirementVerificationContract, RetryPolicy, TaskLoopBinding,
    TaskSliceDefinition, WorkerAssignmentEnvelope, assure_plan,
    compile_execution_waves, compile_plan_to_loop_graph)


def _verification(name="criterion"):
    return RequirementVerificationContract(
        name, "Requested result exists.", "artifact.inspect",
        ("artifact digest", "verification result"), "verification_failed", True)


def _task(task_id, dependencies=(), writes=()):
    return TaskSliceDefinition(
        task_id, f"Complete {task_id}.", ("input:task",), ("result/v1",),
        tuple(dependencies), (_verification(f"criterion-{task_id}"),),
        ConcurrencyContract(reads=("workspace",), writes=tuple(writes),
                            thread_safe=True),
        ("registered capability", "typed invocation", "verification"))


def _plan(tasks):
    return PlanDefinition(
        "plan-fixture", "task-original", "a" * 64,
        "Produce verified changed state.", ("requested change",),
        ("unrelated cleanup",), PlanningAuthority.AUTONOMOUS_WITH_SAFE_DEFAULTS,
        (ClarificationItem("filename", ClarificationDisposition.DELEGATED_CHOICE,
                           "Requester delegated a safe choice.", "result.txt"),),
        tuple(tasks))


def self_test():
    tests = []
    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    plan = _plan((_task("task-a"), _task("task-b"),
                  _task("task-c", ("task-a", "task-b"))))
    execution = compile_execution_waves(plan)
    check("independent_tasks_share_the_first_wave",
          execution.waves == (("task-a", "task-b"), ("task-c",)))
    graph = compile_plan_to_loop_graph(plan, (
        TaskLoopBinding("task-a", "development.execute.task_a"),
        TaskLoopBinding("task-b", "development.execute.task_b"),
        TaskLoopBinding("task-c", "development.execute.task_c"),
    ))
    check("task_plan_compiles_to_canonical_loop_graph",
          graph.validate().valid
          and {item.vertex_id for item in graph.vertices}
          == {"plan.controller", "task-a", "task-b", "task-c"}
          and graph.required_operation_refs()
          == ("development.execute.task_a", "development.execute.task_b",
              "development.execute.task_c"))
    assurance = assure_plan(plan, "loop-independent-reviewer")
    check("complete_plan_passes_structural_assurance",
          assurance.verdict is AssuranceVerdict.ACCEPT)
    check("original_task_identity_is_immutable_in_plan_digest",
          len(plan.content_digest) == 64 and plan.original_task_digest == "a" * 64)

    conflict_plan = _plan((_task("task-a", writes=("same.py",)),
                           _task("task-b", writes=("same.py",))))
    conflict = compile_execution_waves(conflict_plan)
    check("conflicting_writes_are_serialized",
          conflict.waves == (("task-a",), ("task-b",))
          and any(item.selected_wave_relation == "serialized"
                  for item in conflict.decisions))

    cycle = _plan((_task("task-a", ("task-b",)),
                   _task("task-b", ("task-a",))))
    refused = False
    try:
        compile_execution_waves(cycle)
    except DevelopmentPlanError:
        refused = True
    check("dependency_cycle_is_rejected", refused)

    handoff = WorkerAssignmentEnvelope(
        "loop-parent", "plan-fixture", "task-a", "task-original",
        "workspace:exact", "settings:sha256", "capabilities:sha256",
        "extensions:sha256", ("input:task",), (), ("context:bounded",),
        ("workspace_write",), ("src/a.py",), ("writes_fs",),
        ("result/v1",), ("criterion-task-a",), "parent_context")
    check("worker_handoff_preserves_exact_resolved_refs",
          len(handoff.content_digest) == 64
          and handoff.resolved_workspace_ref == "workspace:exact")

    retry = RetryPolicy("retry-python-test", 2, ("test_failure",))
    check("retry_limit_is_explicit_and_delta_required",
          retry.maximum_attempts == 2 and retry.executable_delta_required)
    no_delta = False
    try:
        RetryPolicy("retry-bad", 3, ("failure",), False)
    except DevelopmentPlanError:
        no_delta = True
    check("no_op_retry_policy_is_refused", no_delta)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "development_planning_self_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
