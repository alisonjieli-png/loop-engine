"""STEP 5 — Find, adapt, compose, or design the method for the action.

CONTRACT   PractitionerState + Situation + CandidateAction  ->  ExecutionPlan
REQUIRED   yes
WAYS       exact reuse · learned shortcut · deterministic wrapper ·
           compose/configure · template mutate · generate
EXTEND     register a node/executor as a searchable resource; provide a `how`
           impl to change method selection.

REUSE-FIRST is structural: the reuse_first_guard refuses an expensive rung until
'do we already have this?' is ruled out.  Learned shortcuts land on the reuse
rung, so a similar problem resolves with zero model calls.
"""
from ...loop.kernel import ExecutionPlan, default_how
from ...loop.methodical import EXECUTION_LADDER, reuse_first_guard
from ...code_nodes.self_improve import ShortcutStore, make_learning_probe
from ...code_nodes.competition_solver import find_executor, build_competition_store
from ...static_architecture.config import SolverConfig, permit_plan, screen_models

__all__ = ["ExecutionPlan", "default_how", "EXECUTION_LADDER",
           "reuse_first_guard", "ShortcutStore", "make_learning_probe",
           "find_executor", "build_competition_store", "SolverConfig",
           "permit_plan", "screen_models"]
