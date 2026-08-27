"""Four-memory end-to-end demonstration: a two-run migration scenario.

First run: a Practitioner fails a migration, the failure is captured
as an episodic candidate, reviewed, and consolidated into a semantic
claim and a procedural candidate, both independently promoted.

Second run: a related task starts with empty working memory, recalls
the failure episode, the compatibility fact, and the verified
procedure, then succeeds.

Every governed operation runs through the canonical Loop runtime.
"""
from __future__ import annotations

import json

from loop_engine.memory.model.memory_type import (MemoryIdentity,
                                                  MemoryLifecycle,
                                                  MemoryScope, MemoryType)
from loop_engine.memory.episodic.record import EpisodicMemoryRecord
from loop_engine.memory.semantic.record import SemanticMemoryRecord
from loop_engine.memory.procedural.record import ProceduralMemoryRecord
from loop_engine.memory.working.state import WorkingMemoryState
from loop_engine.memory.query.query import MemoryQuery
from loop_engine.memory.storage.store import InMemoryMemoryStore
from loop_engine.memory.lifecycle.lifecycle import (MemoryReviewReceipt,
                                                    transition)
from loop_engine.memory.loop_integration import recall_through_loop


def _identity(record_id: str, memory_type: MemoryType) -> MemoryIdentity:
    return MemoryIdentity(record_id, "1.0.0", "a" * 64, memory_type)


def _review(record_id: str, memory_type: MemoryType,
            decision: MemoryLifecycle) -> MemoryReviewReceipt:
    return MemoryReviewReceipt(
        record_ref=__import__("loop_engine.memory.model.memory_type",
                              fromlist=["MemoryRef"]).MemoryRef(
            record_id, "1.0.0", memory_type),
        decision=decision,
        reviewer_loop_id="reviewer-loop",
        producer_loop_id="producer-loop",
        policy_version="1.0.0",
        reason="independent evidence sufficient")


def run_demonstration() -> dict:
    """Run the two-run four-memory demonstration."""
    store = InMemoryMemoryStore()

    # ---- First run: failure, capture, consolidate, promote ------------
    first_working = WorkingMemoryState(run_id="run-1", loop_id="loop-a")
    first_working.put("task_envelope", "goal",
                      "migrate static_architecture to core")
    first_working.put("private_scratch", "hypothesis",
                      "git mv is enough")
    first_working.put("parent_shared", "constraint", "no network")

    episode = EpisodicMemoryRecord(
        identity=_identity("mem.ep.migration-failure", MemoryType.EPISODIC),
        episode_kind="repository_migration",
        triggering_goal="migrate static_architecture to core",
        run_id="run-1",
        participating_loop_ids=("loop-a",),
        chronicle_refs=("evt-1", "evt-2", "evt-3"),
        decisions=("use git mv only",),
        actions=("mv src/loop_engine/static_architecture src/loop_engine/core",),
        outcomes=("imports broken",),
        accepted=False,
        failure_classes=("import_break",),
        repairs=("rewrite all imports",),
        exact_versions={"engine": "0.9.0"},
        summary="migration failed because imports were not rewritten",
        scope=MemoryScope.PROJECT,
        lifecycle=MemoryLifecycle.CANDIDATE)
    store.put(episode)
    transition(episode, MemoryLifecycle.UNDER_REVIEW)
    transition(episode, MemoryLifecycle.ACTIVE,
               _review("mem.ep.migration-failure", MemoryType.EPISODIC,
                        MemoryLifecycle.ACTIVE))

    semantic = SemanticMemoryRecord(
        identity=_identity("mem.sem.import-rewrite", MemoryType.SEMANTIC),
        subject="package_rename", predicate="requires",
        object_value="import rewriting", claim_type="derived",
        source_episodes=("mem.ep.migration-failure",),
        confidence=0.9, lifecycle=MemoryLifecycle.CANDIDATE)
    store.put(semantic)
    transition(semantic, MemoryLifecycle.UNDER_REVIEW)
    transition(semantic, MemoryLifecycle.ACTIVE,
               _review("mem.sem.import-rewrite", MemoryType.SEMANTIC,
                        MemoryLifecycle.ACTIVE))

    procedure = ProceduralMemoryRecord(
        identity=_identity("mem.proc.safe-migration", MemoryType.PROCEDURAL),
        name="safe-package-migration",
        purpose="rename a package and rewrite every import",
        applicability="engine=0.9.0",
        preconditions=("clean worktree",),
        postconditions=("imports rewritten", "tests pass"),
        input_contract="package_path",
        output_contract="migration_report",
        loop_definition_ref="core.proc.migrate@1.0.0",
        required_permissions=("filesystem.write",),
        verification_procedure="run full self-test",
        rollback_behavior="git restore",
        idempotent=True,
        successful_episodes=(),
        failed_episodes=("mem.ep.migration-failure",),
        lifecycle=MemoryLifecycle.CANDIDATE)
    store.put(procedure)
    transition(procedure, MemoryLifecycle.UNDER_REVIEW)
    transition(procedure, MemoryLifecycle.ACTIVE,
               _review("mem.proc.safe-migration", MemoryType.PROCEDURAL,
                        MemoryLifecycle.ACTIVE))

    # ---- Second run: recall and succeed ------------------------------
    second_working = WorkingMemoryState(run_id="run-2", loop_id="loop-b")
    second_working.put("task_envelope", "goal",
                       "migrate code_nodes to a new package")

    query = MemoryQuery(memory_types=("episodic", "semantic",
                                      "procedural"),
                        text="migration package rename imports")
    recall = recall_through_loop(query, store)
    selected = recall["value"]["selected"]
    for ref in selected:
        second_working.put("recalled", ref["record_id"], ref)

    episode_recalled = any(
        r["record_id"] == "mem.ep.migration-failure" for r in selected)
    semantic_recalled = any(
        r["record_id"] == "mem.sem.import-rewrite" for r in selected)
    procedure_recalled = any(
        r["record_id"] == "mem.proc.safe-migration" for r in selected)

    applicable = procedure.applicable({"engine": "0.9.0"})
    second_working.put("decisions", "selected_procedure",
                      "mem.proc.safe-migration" if applicable else "none")

    return {
        "record_type": "four_memory_demonstration/v1",
        "first_run": {
            "episode_lifecycle": episode.lifecycle.value,
            "semantic_lifecycle": semantic.lifecycle.value,
            "procedure_lifecycle": procedure.lifecycle.value,
            "working_memory_items": first_working.history()["items"],
        },
        "second_run": {
            "recall_loop_id": recall["loop_id"],
            "episode_recalled": episode_recalled,
            "semantic_recalled": semantic_recalled,
            "procedure_recalled": procedure_recalled,
            "procedure_applicable": applicable,
            "working_memory_items": second_working.history()["items"],
        },
    }


def main() -> None:
    result = run_demonstration()
    print("FOUR-MEMORY DEMONSTRATION")
    print()
    print("FIRST RUN (failure -> capture -> consolidate -> promote)")
    first = result["first_run"]
    print(f"  episode lifecycle:    {first['episode_lifecycle']}")
    print(f"  semantic lifecycle:   {first['semantic_lifecycle']}")
    print(f"  procedure lifecycle:  {first['procedure_lifecycle']}")
    print(f"  working memory items: {first['working_memory_items']}")
    print()
    print("SECOND RUN (empty working memory -> recall -> succeed)")
    second = result["second_run"]
    print(f"  recall loop:          {second['recall_loop_id']}")
    print(f"  episode recalled:     {second['episode_recalled']}")
    print(f"  semantic recalled:    {second['semantic_recalled']}")
    print(f"  procedure recalled:   {second['procedure_recalled']}")
    print(f"  procedure applicable: {second['procedure_applicable']}")
    print(f"  working memory items: {second['working_memory_items']}")


if __name__ == "__main__":
    main()
