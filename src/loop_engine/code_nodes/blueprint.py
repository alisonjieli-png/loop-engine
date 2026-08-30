"""Long-horizon grounding — a goal stack + working blueprint the agent never loses.

Owner insight (2026-08-23): on 100-, 1,000-, 10,000-step tasks an agent asked
only to select the next action drifts — at step 40 of 100 it forgets the whole plan and
rushes to finish.  The fix is to ground EVERY decision in more than the next
step: the ultimate goal, the current sub-goal / checkpoint, and a working
blueprint of what the whole solution looks like.  That grounding is a memory item
re-fed into context every pass, and re-shaped as the plan is learned.

Three grounding layers, all carried in the practitioner state and rendered into
the standard prompt blocks (objective/state) every pass:

  * **GoalStack** — the ultimate goal, then a stack of sub-goals / checkpoints,
    with the current one marked.  The agent always sees where it is in the whole.
  * **WorkingBlueprint** — an outline that is progressively detailed: a high-level
    outline, then a detailed outline, then per-bucket detail.  It estimates how
    many steps/nodes "reasonable" looks like, so drift ("just finish fast") is
    visible against the plan.
  * **Progress** — steps done vs the blueprint's estimate, current checkpoint,
    and the recent trail — so the ground-truth of "how far are we, really" is
    never a hallucination.

``grounding_summary`` renders all three into a compact, stable block that is
prepended to the objective every pass — the anti-drift anchor.  The blueprint is
versioned and can spawn variations without losing the original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# Progressive detail levels of a blueprint.
BLUEPRINT_LEVELS = ("outline", "detailed_outline", "per_bucket_detail")

# The six progressive-elaboration levels (owner spec 2026-08-23): the whole
# program is covered broadly at levels 1-2; only the ACTIVE horizon is expanded
# to atomic actions.  Distant work stays an explicit unexpanded obligation —
# never hallucinated in detail, never dropped from the plan.
ELABORATION_LEVELS = (
    "L0_ultimate_goal",        # ultimate goal + completion contract
    "L1_major_phases",         # major phases / outcome areas
    "L2_checkpoints",          # evidence-based checkpoints
    "L3_work_packages",        # work packages for active/near-term checkpoints
    "L4_atomic_actions",       # atomic practitioner actions
    "L5_task_graph_nodes",     # concrete Task Graph nodes + parameter bindings
)

# The lifecycle of a checkpoint on the goal stack.
CHECKPOINT_STATES = ("pending", "active", "done", "blocked")

# The meaningful decision boundaries at which an admitted Task Graph must stop
# and return control to the practitioner (so a 10,000-op task is NOT 10,000
# passes — a WorkPacket runs deterministic ops until one of these).
DECISION_BOUNDARIES = (
    "branch_requiring_judgment", "missing_dependency", "new_material_evidence",
    "unrecoverable_failure", "irreversible_external_action",
    "budget_threshold", "checkpoint_closure", "blueprint_revision_required",
    "packet_complete")


@dataclass
class Checkpoint:
    name: str
    detail: str = ""
    state: str = "pending"
    est_steps: int = 1

    def __post_init__(self):
        if self.state not in CHECKPOINT_STATES:
            raise ValueError(f"state must be one of {CHECKPOINT_STATES}")


@dataclass
class GoalStack:
    """The ultimate goal + an ordered stack of sub-goals / checkpoints."""
    ultimate_goal: str
    checkpoints: list = field(default_factory=list)   # Checkpoints, in order

    def current_index(self) -> int:
        for i, c in enumerate(self.checkpoints):
            if c.state in ("active", "pending", "blocked"):
                return i
        return len(self.checkpoints)

    def current(self) -> "Checkpoint | None":
        i = self.current_index()
        return self.checkpoints[i] if i < len(self.checkpoints) else None

    def advance(self) -> "GoalStack":
        """Mark the current checkpoint done and activate the next — returns a
        NEW stack (never mutates, for reproducible state versions)."""
        cps = [Checkpoint(c.name, c.detail, c.state, c.est_steps)
               for c in self.checkpoints]
        i = self.current_index()
        if i < len(cps):
            cps[i].state = "done"
        if i + 1 < len(cps):
            cps[i + 1].state = "active"
        return GoalStack(self.ultimate_goal, cps)

    def total_est_steps(self) -> int:
        return sum(c.est_steps for c in self.checkpoints)


@dataclass
class WorkingBlueprint:
    """A progressively-detailed plan of the whole solution."""
    level: str = "outline"
    buckets: list = field(default_factory=list)   # list of {name, detail, steps}
    version: int = 1
    est_total_steps: int = 0
    notes: str = ""

    def __post_init__(self):
        if self.level not in BLUEPRINT_LEVELS:
            raise ValueError(f"level must be one of {BLUEPRINT_LEVELS}")
        if not self.est_total_steps and self.buckets:
            self.est_total_steps = sum(int(b.get("steps", 1))
                                       for b in self.buckets)

    def deepen(self, buckets: Sequence[dict]) -> "WorkingBlueprint":
        """Move to the next detail level with a richer bucket breakdown —
        outline -> detailed_outline -> per_bucket_detail.  A new version."""
        nxt = BLUEPRINT_LEVELS[min(len(BLUEPRINT_LEVELS) - 1,
                                   BLUEPRINT_LEVELS.index(self.level) + 1)]
        return WorkingBlueprint(level=nxt, buckets=list(buckets),
                                version=self.version + 1, notes=self.notes)

    def variation(self, buckets: Sequence[dict], note: str) -> "WorkingBlueprint":
        """A parallel variation of the plan (kept alongside the original)."""
        return WorkingBlueprint(level=self.level, buckets=list(buckets),
                                version=self.version + 1, notes=note)


@dataclass
class Progress:
    steps_done: int = 0
    trail: list = field(default_factory=list)      # last few actions taken

    def record(self, action: str, keep: int = 6) -> "Progress":
        return Progress(self.steps_done + 1,
                        (self.trail + [action])[-keep:])


def grounding_summary(goals: "GoalStack | None",
                      blueprint: "WorkingBlueprint | None",
                      progress: "Progress | None") -> str:
    """The compact, stable anti-drift block re-fed into the prompt EVERY pass.

    It states the ultimate goal, where we are on the checkpoint stack, the plan's
    expected size, and honest progress — so the agent is grounded in the whole,
    not just the next step, and cannot silently 'rush to finish'."""
    lines: list[str] = []
    if goals is not None:
        lines.append(f"ULTIMATE GOAL: {goals.ultimate_goal}")
        cur = goals.current()
        done = sum(1 for c in goals.checkpoints if c.state == "done")
        lines.append(f"CHECKPOINTS: {done}/{len(goals.checkpoints)} done; "
                     f"current = {cur.name if cur else 'complete'}")
        if cur and cur.detail:
            lines.append(f"CURRENT CHECKPOINT DETAIL: {cur.detail}")
    if blueprint is not None:
        names = ", ".join(str(b.get("name", "?")) for b in blueprint.buckets)
        lines.append(f"WORKING BLUEPRINT ({blueprint.level}, "
                     f"~{blueprint.est_total_steps} steps): {names}")
    if progress is not None:
        est = blueprint.est_total_steps if blueprint else 0
        lines.append(f"PROGRESS: {progress.steps_done} steps done"
                     + (f" of ~{est} planned" if est else "")
                     + (f"; recent: {' -> '.join(progress.trail[-3:])}"
                        if progress.trail else ""))
        if est and progress.steps_done < est * 0.9 and goals \
                and goals.current() is None:
            lines.append("WARNING: the goal stack says complete but progress is "
                         "well under the planned size — do NOT rush to finish; "
                         "re-examine the blueprint.")
    return "\n".join(lines)


@dataclass
class WorkPacket:
    """A unit of work the practitioner admits so a Task Graph can run
    MANY deterministic operations before the next decision — the answer to
    'a 10,000-operation task is not 10,000 practitioner passes'."""
    packet_id: str
    checkpoint: str
    objective: str
    max_operations: "int | None" = None
    stop_at: tuple = DECISION_BOUNDARIES     # boundaries that end this packet
    operations_done: int = 0
    stopped_because: str = ""

    def should_stop(self, boundary: str) -> bool:
        if boundary not in DECISION_BOUNDARIES:
            raise ValueError(f"unknown decision boundary {boundary!r}")
        return (boundary in self.stop_at
                or (self.max_operations is not None
                    and self.operations_done >= self.max_operations))


@dataclass
class LongHorizonAnchorPacket:
    """The MANDATORY grounding attached to any model call that selects the next
    action, generates/revises a blueprint, designs a method, reviews a
    checkpoint, or decides the run is finished.  It is why the practitioner
    never relies on a model remembering an action from hundreds of steps ago."""
    ultimate_goal: str
    success_criteria: tuple = ()
    non_goals: tuple = ()
    active_checkpoint: str = ""
    checkpoint_entry: str = ""
    checkpoint_exit: str = ""
    blueprint_revision: int = 0
    active_blueprint_path: tuple = ()
    ready_frontier: tuple = ()
    blocked_frontier: tuple = ()
    critical_dependencies: tuple = ()
    completed_progress: str = ""
    active_decisions: tuple = ()
    assumptions: tuple = ()
    blockers_risks_open_questions: tuple = ()
    remaining_budget: str = ""
    plan_health: str = "on_track"          # on_track | drifting | stalled

    def render(self) -> str:
        """The compact anchor block prepended to grounded prompts."""
        L = [f"ULTIMATE GOAL: {self.ultimate_goal}"]
        if self.success_criteria:
            L.append("SUCCESS CRITERIA: " + "; ".join(self.success_criteria))
        if self.non_goals:
            L.append("NON-GOALS: " + "; ".join(self.non_goals))
        if self.active_checkpoint:
            L.append(f"ACTIVE CHECKPOINT: {self.active_checkpoint}"
                     + (f" (exit when: {self.checkpoint_exit})"
                        if self.checkpoint_exit else ""))
        L.append(f"BLUEPRINT rev {self.blueprint_revision}; path: "
                 + " -> ".join(self.active_blueprint_path or ("(none)",)))
        if self.ready_frontier:
            L.append("READY NEXT: " + ", ".join(self.ready_frontier))
        if self.blocked_frontier:
            L.append("BLOCKED: " + ", ".join(self.blocked_frontier))
        if self.completed_progress:
            L.append(f"PROGRESS: {self.completed_progress}")
        if self.blockers_risks_open_questions:
            L.append("OPEN: " + "; ".join(self.blockers_risks_open_questions))
        if self.remaining_budget:
            L.append(f"REMAINING BUDGET: {self.remaining_budget}")
        L.append(f"PLAN HEALTH: {self.plan_health}")
        if self.plan_health != "on_track":
            L.append("Re-examine the blueprint; do NOT rush to finish.")
        return "\n".join(L)


def build_anchor(goals: "GoalStack | None",
                 blueprint: "WorkingBlueprint | None",
                 progress: "Progress | None", *,
                 success_criteria: Sequence[str] = (),
                 non_goals: Sequence[str] = (),
                 remaining_budget: str = "") -> LongHorizonAnchorPacket:
    """Assemble the anchor packet from the goal stack + blueprint + progress —
    the reconcile step's output, computed not hallucinated.  Plan health is
    derived: 'drifting' when the stack claims complete but progress is far
    under the plan, 'stalled' when no ready frontier remains."""
    cur = goals.current() if goals else None
    done = [c.name for c in goals.checkpoints if c.state == "done"] \
        if goals else []
    ready = tuple(c.name for c in (goals.checkpoints if goals else [])
                  if c.state in ("active", "pending"))[:3]
    blocked = tuple(c.name for c in (goals.checkpoints if goals else [])
                    if c.state == "blocked")
    est = blueprint.est_total_steps if blueprint else 0
    steps = progress.steps_done if progress else 0
    health = "on_track"
    if goals and goals.current() is None and est and steps < est * 0.9:
        health = "drifting"
    elif goals and not ready and goals.current() is not None:
        health = "stalled"
    return LongHorizonAnchorPacket(
        ultimate_goal=(goals.ultimate_goal if goals else ""),
        success_criteria=tuple(success_criteria), non_goals=tuple(non_goals),
        active_checkpoint=(cur.name if cur else ""),
        checkpoint_exit=(cur.detail if cur else ""),
        blueprint_revision=(blueprint.version if blueprint else 0),
        active_blueprint_path=tuple(b.get("name", "?")
                                    for b in (blueprint.buckets if blueprint
                                              else [])),
        ready_frontier=ready, blocked_frontier=blocked,
        completed_progress=(f"{len(done)} checkpoints done, {steps} steps"
                            + (f" of ~{est}" if est else "")),
        remaining_budget=remaining_budget, plan_health=health)


def seed_from_objective(objective: str, checkpoints: Sequence[str],
                        est_steps_each: int = 3) -> tuple:
    """Convenience: build an initial GoalStack + outline WorkingBlueprint from a
    plain objective and a first-cut list of checkpoint names (the outline that a
    'generate a blueprint first' bias produces)."""
    cps = [Checkpoint(name=c, est_steps=est_steps_each) for c in checkpoints]
    if cps:
        cps[0].state = "active"
    goals = GoalStack(ultimate_goal=objective, checkpoints=cps)
    bp = WorkingBlueprint(level="outline",
                          buckets=[{"name": c, "steps": est_steps_each}
                                   for c in checkpoints])
    return goals, bp


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    goals, bp = seed_from_objective(
        "win the RSNA knee competition",
        ["extract labels from reports", "train a 2.5D CNN",
         "calibrate + submit"], est_steps_each=10)

    # 1. the goal stack knows the ultimate goal and the current checkpoint.
    check("the_goal_stack_tracks_ultimate_goal_and_current_checkpoint",
          goals.ultimate_goal.startswith("win the RSNA")
          and goals.current().name == "extract labels from reports"
          and goals.total_est_steps() == 30,
          "the agent always sees where it is in the whole plan")

    # 2. advancing marks done + activates the next, without mutating.
    g2 = goals.advance()
    check("advancing_a_checkpoint_is_immutable_and_correct",
          goals.current().name == "extract labels from reports"   # original intact
          and g2.checkpoints[0].state == "done"
          and g2.current().name == "train a 2.5D CNN",
          "the original stack is unchanged; the new one advanced")

    # 3. the blueprint deepens outline -> detailed -> per-bucket.
    bp2 = bp.deepen([{"name": "regex+negation extractor", "steps": 4},
                     {"name": "LLM second extractor", "steps": 4},
                     {"name": "ensemble on gold", "steps": 2}])
    check("the_blueprint_progressively_details",
          bp.level == "outline" and bp2.level == "detailed_outline"
          and bp2.version == 2 and bp2.est_total_steps == 10,
          "outline -> detailed_outline with a step estimate")

    # 4. the GROUNDING SUMMARY carries goal + checkpoint + blueprint + progress.
    prog = Progress().record("built the extractor").record("validated on gold")
    summary = grounding_summary(goals, bp, prog)
    check("the_grounding_summary_anchors_the_whole_plan",
          "ULTIMATE GOAL:" in summary and "CHECKPOINTS:" in summary
          and "WORKING BLUEPRINT" in summary and "PROGRESS: 2 steps" in summary,
          "one compact block re-fed every pass keeps the agent grounded")

    # 5. the anti-rush WARNING fires when 'complete' but progress is far short.
    finished_stack = GoalStack("g", [Checkpoint("a", state="done"),
                                     Checkpoint("b", state="done")])
    big_bp = WorkingBlueprint(buckets=[{"name": "x", "steps": 100}])
    warn = grounding_summary(finished_stack, big_bp, Progress(steps_done=5))
    check("a_premature_completion_triggers_an_anti_rush_warning",
          "do NOT rush to finish" in warn,
          "goal stack says done but 5<<100 planned steps -> warn, do not drift")

    # 6. variations preserve the original blueprint.
    var = bp.variation([{"name": "alt plan", "steps": 5}], "aggressive path")
    check("blueprint_variations_are_kept_alongside_the_original",
          var.version == 2 and var.notes == "aggressive path"
          and bp.buckets[0]["name"] == "extract labels from reports",
          "a variation never destroys the plan it branched from")

    # 7. closed vocabularies.
    bad = 0
    for fn in (lambda: Checkpoint("x", state="vibes"),
               lambda: WorkingBlueprint(level="freeform")):
        try:
            fn()
        except ValueError:
            bad += 1
    check("checkpoint_states_and_blueprint_levels_are_closed", bad == 2,
          "the grounding vocabularies are closed")

    # 8. the LongHorizonAnchorPacket renders the mandatory grounding, computed
    # from the goal stack + blueprint + progress (not hallucinated).
    anchor = build_anchor(goals, bp, prog,
                          success_criteria=("macro-AUC beats 0.75",),
                          non_goals=("do not overfit the 58 gold",),
                          remaining_budget="6 model calls")
    rendered = anchor.render()
    check("the_anchor_packet_grounds_a_model_call_in_the_whole_plan",
          "ULTIMATE GOAL:" in rendered and "ACTIVE CHECKPOINT:" in rendered
          and "BLUEPRINT rev" in rendered and "NON-GOALS:" in rendered
          and anchor.active_checkpoint == "extract labels from reports",
          "the mandatory anchor carries goal/criteria/non-goals/checkpoint/"
          "path/progress")

    # 9. plan health derives 'drifting' when complete-but-short (anti-rush).
    fin = GoalStack("g", [Checkpoint("a", state="done")])
    big = WorkingBlueprint(buckets=[{"name": "x", "steps": 100}])
    drift = build_anchor(fin, big, Progress(steps_done=5))
    check("plan_health_flags_drift_on_premature_completion",
          drift.plan_health == "drifting"
          and "do NOT rush to finish" in drift.render(),
          "goal stack done but 5<<100 planned -> drifting, warn")

    # 10. a WorkPacket stops at a decision boundary or its op cap.
    wp = WorkPacket("wp1", "train", "fit the model", max_operations=50)
    wp.operations_done = 50
    boundary_stop = WorkPacket("wp2", "train", "x").should_stop(
        "checkpoint_closure")
    check("a_work_packet_stops_at_a_boundary_or_its_cap",
          wp.should_stop("packet_complete") and boundary_stop,
          "many deterministic ops per packet; stop at a meaningful boundary")

    # 11. the six elaboration levels + nine decision boundaries are closed sets.
    check("elaboration_levels_and_decision_boundaries_are_defined",
          len(ELABORATION_LEVELS) == 6 and len(DECISION_BOUNDARIES) == 9
          and ELABORATION_LEVELS[0] == "L0_ultimate_goal",
          "L0..L5 progressive elaboration; nine decision boundaries")
    bad_b = False
    try:
        WorkPacket("x", "c", "o").should_stop("teleport")
    except ValueError:
        bad_b = True
    check("an_unknown_decision_boundary_is_refused", bad_b,
          "the boundary vocabulary is closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "blueprint_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
