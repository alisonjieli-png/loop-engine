"""STEP 2 — Reconcile the ultimate goal, active checkpoint, and working blueprint.

CONTRACT   PractitionerState + Situation  ->  LongHorizonAnchorPacket
REQUIRED   no (optional; kernel default builds a minimal anchor)
WAYS       no-op minimal anchor · goal-stack+blueprint reconciliation ·
           typed Goal Graph / Plan Frontier
EXTEND     provide a `reconcile_horizon` impl; add plan schemas in planning.py.

The mandatory long-horizon grounding: every important model call carries the
anchor so a 100/1000/10000-step task never loses the goal or rushes to finish.
Goals (why) and blueprints (how) stay SEPARATE; completion needs evidence.
"""
from ...loop.kernel import default_reconcile_horizon
from ...code_nodes.blueprint import (GoalStack, WorkingBlueprint, LongHorizonAnchorPacket,
                         build_anchor, WorkPacket, ELABORATION_LEVELS,
                         DECISION_BOUNDARIES, grounding_summary,
                         seed_from_objective)
from ...code_nodes.planning import (GoalGraph, GoalItem, BlueprintItem, CheckpointContract,
                        PlanFrontier, compute_frontier, validate_blueprint)
from ...strings.task_blueprint import (TaskBlueprint, default_opening_sequence,
                             bias_next_from_blueprint, OpeningMove)

__all__ = ["default_reconcile_horizon", "GoalStack", "WorkingBlueprint",
           "LongHorizonAnchorPacket", "build_anchor", "WorkPacket",
           "ELABORATION_LEVELS", "DECISION_BOUNDARIES", "grounding_summary",
           "seed_from_objective", "GoalGraph", "GoalItem", "BlueprintItem",
           "CheckpointContract", "PlanFrontier", "compute_frontier",
           "validate_blueprint", "TaskBlueprint", "default_opening_sequence",
           "bias_next_from_blueprint", "OpeningMove"]
