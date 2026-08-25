"""Typed entry point for starting one Spawned Practitioner Loop.

This module delegates to ``SpawnedTaskManager`` and the canonical ``Loop``.
It contains no alternate Practitioner runtime, state machine, or graph.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .delegation_runtime import (
        DelegationSpec,
        SpawnedExecutor,
        SpawnedTaskManagerLimits,
        SpawnedTaskSnapshot,
    )
    from .recursive_loop import Loop


def spawn_practitioner_loop(
        spawning_loop: "Loop", spec: "DelegationSpec", *,
        executor: "SpawnedExecutor | None" = None,
        limits: "SpawnedTaskManagerLimits | None" = None,
        runtime_memory=None, context_artifacts=None) -> "SpawnedTaskSnapshot":
    """Run one registered Practitioner profile as a Spawned Loop."""
    from .delegation_runtime import (
        DelegationError,
        SpawnedTaskManager,
    )
    from .loop_profile_ontology import resolve_profile

    if resolve_profile(spec.profile).spec.family != "practitioner":
        raise DelegationError(
            "spawn_practitioner_loop requires a Practitioner profile")
    manager = SpawnedTaskManager(
        spawning_loop, executor, limits,
        runtime_memory=runtime_memory,
        context_artifacts=context_artifacts,
    )
    return manager.status(manager.start(spec))


def self_test() -> dict:
    """Prove that the wrapper uses the canonical typed delegation path."""
    from .delegation_runtime import (
        DelegationConstraints,
        DelegationSpec,
        SpawnedTaskStatus,
    )
    from .loop_contract import LoopContract
    from .loop_profile_catalog import resolve_profile_alias
    from .loop_role import LoopRelationshipKind, LoopRole
    from .recursive_loop import Loop, LoopConfig

    spawning_loop = Loop(
        "run one bounded operation",
        LoopConfig(
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
        ),
    )
    snapshot = spawn_practitioner_loop(
        spawning_loop,
        DelegationSpec(
            goal="run the selected operation",
            profile=resolve_profile_alias("practitioner.code_execution"),
            contract=LoopContract(
                "run-operation", "code_only",
                output_roles=("operation_result/v1",),
                role="practitioner",
            ),
            constraints=DelegationConstraints(
                available_fields=("operation_ref",),
                capability_refs=(
                    "loop_spawn", "run_history_write", "code_execution"),
            ),
        ),
    )
    passed = (
        snapshot.status == SpawnedTaskStatus.SUCCEEDED
        and snapshot.relationship.kind == LoopRelationshipKind.SPAWNED_BY
        and snapshot.identity.role == LoopRole.PRACTITIONER
    )
    return {
        "record_type": "spawned_practitioner_checks/v1",
        "tests": [{
            "test": "spawned_practitioner_uses_the_canonical_loop_runtime",
            "passed": passed,
            "detail": str(snapshot.task_id),
        }],
        "passed": int(passed),
        "total": 1,
        "all_passed": passed,
    }
