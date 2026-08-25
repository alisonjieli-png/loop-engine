"""Typed planning layer — Goal Graph, Working Blueprint, Checkpoints, Frontier.

Owner spec section 6 (2026-08-23): goals and plans stay SEPARATE.  The Goal Graph
explains desired outcomes (WHY the work exists); the Working Blueprint explains a
proposed route (HOW).  A single goal may have several competing blueprint
variants; a blueprint item may support several subgoals; a result may show the
goal is still valid while the blueprint is wrong.  ``GoalBinding`` records connect
blueprint items to goals.

This is the richer, typed layer the reconcile step (kernel node 2) reasons over —
it supersedes the lightweight GoalStack in ``blueprint.py`` for real long-horizon
work.  Everything carries a closed status vocabulary and hard invariants:

  * a goal becomes ``satisfied`` only through accepted evaluation or an
    authorized waiver;
  * a blueprint item becomes ``completed`` only with accepted status evidence —
    never by assertion (this is the anti-premature-closure guard);
  * every required goal must have a plan path OR an explicit unresolved marker;
  * the plan is acyclic; a cycle or a dangling dependency fails validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# ── Goal Graph vocabularies ────────────────────────────────────────────────
GOAL_KINDS = ("ultimate", "outcome", "subgoal", "constraint", "non_goal")
GOAL_STATUS = ("proposed", "accepted", "active", "satisfied",
               "partially_satisfied", "blocked", "waived", "superseded",
               "rejected")

# ── Working Blueprint vocabularies ─────────────────────────────────────────
BLUEPRINT_ITEM_KINDS = ("phase", "checkpoint", "work_package", "atomic_action",
                        "decision_gate", "review_gate", "external_dependency")
BLUEPRINT_ITEM_STATUS = ("proposed", "unexpanded", "ready", "active", "blocked",
                         "deferred", "completed", "failed", "cancelled",
                         "waived", "superseded")
# Typed relationships — ordinal position is never identity.
BLUEPRINT_EDGE_TYPES = ("requires", "produces", "blocks", "supports",
                        "validates", "decomposes_to", "supersedes")
CHECKPOINT_STATUS = ("proposed", "active", "blocked", "closed", "abandoned")


class PlanInvariantError(RuntimeError):
    """A blueprint or goal-graph invariant was violated."""


@dataclass
class GoalNode:
    goal_id: str
    goal_kind: str
    statement: str
    version: int = 1
    parent_goal_ids: tuple = ()
    status: str = "proposed"
    hard: bool = True
    required_evidence_kinds: tuple = ()

    def __post_init__(self):
        if self.goal_kind not in GOAL_KINDS:
            raise ValueError(f"goal_kind must be one of {GOAL_KINDS}")
        if self.status not in GOAL_STATUS:
            raise ValueError(f"status must be one of {GOAL_STATUS}")


@dataclass
class GoalGraph:
    nodes: dict = field(default_factory=dict)      # goal_id -> GoalNode

    def add(self, node: GoalNode) -> None:
        self.nodes[node.goal_id] = node

    def ultimate(self) -> "GoalNode | None":
        for n in self.nodes.values():
            if n.goal_kind == "ultimate":
                return n
        return None

    def required_goals(self) -> list:
        """Hard goals that must have a plan path (non-goals/constraints excluded
        from the path requirement)."""
        return [n for n in self.nodes.values()
                if n.goal_kind in ("ultimate", "outcome", "subgoal") and n.hard]

    def satisfy(self, goal_id: str, *, evidence: tuple = (),
                waiver: str = "") -> None:
        """A goal may become satisfied ONLY through accepted evidence or an
        explicit authorized waiver — never by assertion."""
        n = self.nodes[goal_id]
        if not evidence and not waiver:
            raise PlanInvariantError(
                f"goal {goal_id!r} cannot be satisfied without accepted "
                f"evidence or an authorized waiver")
        n.status = "waived" if waiver and not evidence else "satisfied"


@dataclass
class GoalBinding:
    item_id: str
    goal_ids: tuple


@dataclass
class BlueprintItem:
    item_id: str
    item_kind: str
    statement: str
    goal_bindings: tuple = ()          # goal ids this item advances
    predecessor_item_ids: tuple = ()
    status: str = "proposed"
    status_evidence_refs: tuple = ()
    produced_artifact_kinds: tuple = ()
    consumed_artifact_kinds: tuple = ()

    def __post_init__(self):
        if self.item_kind not in BLUEPRINT_ITEM_KINDS:
            raise ValueError(f"item_kind must be one of {BLUEPRINT_ITEM_KINDS}")
        if self.status not in BLUEPRINT_ITEM_STATUS:
            raise ValueError(f"status must be one of {BLUEPRINT_ITEM_STATUS}")


@dataclass
class CheckpointContract:
    checkpoint_id: str
    blueprint_item_ref: str
    purpose: str
    entry_conditions: tuple = ()
    exit_criteria: tuple = ()
    required_evidence: tuple = ()
    status: str = "proposed"
    closure_evidence_refs: tuple = ()

    def __post_init__(self):
        if self.status not in CHECKPOINT_STATUS:
            raise ValueError(f"status must be one of {CHECKPOINT_STATUS}")
        if not self.exit_criteria:
            raise PlanInvariantError(
                f"checkpoint {self.checkpoint_id!r} needs TESTABLE exit "
                f"criteria — 'looks good' / 'made progress' are not sufficient")

    def close(self, evidence_refs: Sequence[str]) -> None:
        """A checkpoint may close only with exit evidence."""
        if not evidence_refs:
            raise PlanInvariantError(
                f"checkpoint {self.checkpoint_id!r} cannot close without exit "
                f"evidence")
        self.status = "closed"
        self.closure_evidence_refs = tuple(evidence_refs)


@dataclass
class WorkingBlueprint:
    revision_id: str
    items: dict = field(default_factory=dict)       # item_id -> BlueprintItem
    parent_revision_ref: str = ""
    variant_family: str = "main"

    def add(self, item: BlueprintItem) -> None:
        self.items[item.item_id] = item

    def complete_item(self, item_id: str, evidence_refs: Sequence[str]) -> None:
        """Mark an item completed — ONLY with accepted evidence (the anti-
        premature-closure invariant)."""
        item = self.items[item_id]
        if not evidence_refs:
            raise PlanInvariantError(
                f"blueprint item {item_id!r} cannot be 'completed' without "
                f"accepted status evidence")
        item.status = "completed"
        item.status_evidence_refs = tuple(evidence_refs)


@dataclass
class PlanFrontier:
    active_items: tuple = ()
    ready_items: tuple = ()
    blocked_items: tuple = ()
    deferred_items: tuple = ()
    unexpanded_items: tuple = ()
    missing_dependency_findings: tuple = ()


def compute_frontier(bp: WorkingBlueprint) -> PlanFrontier:
    """Derive the frontier from item status + dependencies.  An item is READY
    when every predecessor is completed/waived; BLOCKED when a predecessor is
    not; a dangling predecessor is a missing-dependency finding."""
    done = {i.item_id for i in bp.items.values()
            if i.status in ("completed", "waived", "superseded", "cancelled")}
    active, ready, blocked, deferred, unexpanded, missing = [], [], [], [], [], []
    for it in bp.items.values():
        if it.status in done or it.status in ("completed", "waived",
                                              "superseded", "cancelled",
                                              "failed"):
            continue
        preds = list(it.predecessor_item_ids)
        for p in preds:
            if p not in bp.items:
                missing.append((it.item_id, p))
        unresolved = [p for p in preds
                      if p in bp.items and p not in done]
        if it.status == "active":
            active.append(it.item_id)
        elif it.status == "unexpanded":
            unexpanded.append(it.item_id)
        elif it.status == "deferred":
            deferred.append(it.item_id)
        elif unresolved:
            blocked.append(it.item_id)
        else:
            ready.append(it.item_id)
    return PlanFrontier(tuple(active), tuple(ready), tuple(blocked),
                        tuple(deferred), tuple(unexpanded), tuple(missing))


def validate_blueprint(goals: GoalGraph, bp: WorkingBlueprint) -> dict:
    """Hard checks: the plan is acyclic, has no dangling dependency, and every
    required goal has at least one plan path (a bound item) OR an explicit
    unexpanded/deferred marker.  Returns findings; raises on a fatal cycle."""
    # cycle check (DFS over predecessor edges)
    WHITE, GREY, BLACK = 0, 1, 2
    color = {i: WHITE for i in bp.items}

    def visit(n):
        color[n] = GREY
        for p in bp.items[n].predecessor_item_ids:
            if p not in bp.items:
                continue
            if color[p] == GREY:
                raise PlanInvariantError(f"blueprint has a dependency cycle at "
                                         f"{n!r} -> {p!r}")
            if color[p] == WHITE:
                visit(p)
        color[n] = BLACK
    for i in bp.items:
        if color[i] == WHITE:
            visit(i)

    frontier = compute_frontier(bp)
    bound_goals = set()
    for it in bp.items.values():
        bound_goals.update(it.goal_bindings)
    unplanned = [g.goal_id for g in goals.required_goals()
                 if g.goal_id not in bound_goals]
    return {"record_type": "blueprint_validation/v1",
            "dangling_dependencies": list(frontier.missing_dependency_findings),
            "goals_without_a_plan_path": unplanned,
            "ok": not frontier.missing_dependency_findings and not unplanned}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    goals = GoalGraph()
    goals.add(GoalNode("g.win", "ultimate", "win the RSNA competition"))
    goals.add(GoalNode("g.labels", "subgoal", "derive labels from reports",
                       parent_goal_ids=("g.win",)))
    goals.add(GoalNode("g.model", "subgoal", "train an accurate model",
                       parent_goal_ids=("g.win",)))

    bp = WorkingBlueprint("rev1")
    bp.add(BlueprintItem("i.extract", "work_package", "build extractor",
                         goal_bindings=("g.labels",), status="ready"))
    bp.add(BlueprintItem("i.train", "work_package", "train CNN",
                         goal_bindings=("g.model",),
                         predecessor_item_ids=("i.extract",)))

    # 1. goals and blueprint are separate, linked by goal bindings.
    check("goals_and_blueprint_are_separate_and_linked",
          goals.ultimate().goal_id == "g.win"
          and bp.items["i.train"].goal_bindings == ("g.model",),
          "the Goal Graph explains why; the Blueprint explains how; bindings "
          "connect them")

    # 2. the frontier derives ready vs blocked from dependencies.
    fr = compute_frontier(bp)
    check("the_frontier_derives_ready_and_blocked",
          fr.ready_items == ("i.extract",) and fr.blocked_items == ("i.train",),
          "i.extract is ready; i.train is blocked on it")

    # 3. an item cannot be 'completed' without accepted evidence.
    bad = False
    try:
        bp.complete_item("i.extract", [])
    except PlanInvariantError:
        bad = True
    bp.complete_item("i.extract", ["eval_receipt_7"])
    fr2 = compute_frontier(bp)
    check("completed_requires_evidence_and_unblocks_successors",
          bad and bp.items["i.extract"].status == "completed"
          and "i.train" in fr2.ready_items,
          "premature closure refused; real completion unblocks the successor")

    # 4. a goal cannot be satisfied without evidence or a waiver.
    bad2 = False
    try:
        goals.satisfy("g.labels")
    except PlanInvariantError:
        bad2 = True
    goals.satisfy("g.labels", evidence=("gold_validation",))
    check("a_goal_needs_evidence_or_a_waiver_to_be_satisfied",
          bad2 and goals.nodes["g.labels"].status == "satisfied",
          "satisfaction is earned by evidence, not asserted")

    # 5. validation catches a goal with no plan path and a dangling dependency.
    bp2 = WorkingBlueprint("rev2")
    bp2.add(BlueprintItem("i.x", "atomic_action", "do x",
                          goal_bindings=("g.win",),
                          predecessor_item_ids=("i.missing",)))
    v = validate_blueprint(goals, bp2)
    check("validation_flags_unplanned_goals_and_dangling_deps",
          "g.labels" in v["goals_without_a_plan_path"]
          and ("i.x", "i.missing") in v["dangling_dependencies"]
          and not v["ok"],
          "an unplanned required goal and a dangling predecessor are caught")

    # 6. a dependency CYCLE fails validation loudly.
    bpc = WorkingBlueprint("rev3")
    bpc.add(BlueprintItem("a", "atomic_action", "a",
                          predecessor_item_ids=("b",)))
    bpc.add(BlueprintItem("b", "atomic_action", "b",
                          predecessor_item_ids=("a",)))
    cyc = False
    try:
        validate_blueprint(GoalGraph(), bpc)
    except PlanInvariantError:
        cyc = True
    check("a_dependency_cycle_fails_validation", cyc,
          "a plan cycle is a fatal invariant violation")

    # 7. a checkpoint needs testable exit criteria and evidence to close.
    bad3 = False
    try:
        CheckpointContract("c1", "i.extract", "extract labels")   # no exit crit
    except PlanInvariantError:
        bad3 = True
    cp = CheckpointContract("c1", "i.extract", "extract labels",
                            exit_criteria=("macro-acc >= 0.75 on gold",))
    bad4 = False
    try:
        cp.close([])
    except PlanInvariantError:
        bad4 = True
    cp.close(["gold_eval_receipt"])
    check("a_checkpoint_needs_testable_exit_criteria_and_evidence",
          bad3 and bad4 and cp.status == "closed",
          "no exit criteria -> refused; closing without evidence -> refused")

    # 8. closed vocabularies.
    bad5 = 0
    for fn in (lambda: GoalNode("x", "vibes", "s"),
               lambda: BlueprintItem("x", "teleport", "s"),
               lambda: BlueprintItem("x", "phase", "s", status="magic")):
        try:
            fn()
        except ValueError:
            bad5 += 1
    check("goal_and_item_vocabularies_are_closed", bad5 == 3,
          "goal kinds/status and item kinds/status are closed sets")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "planning_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
