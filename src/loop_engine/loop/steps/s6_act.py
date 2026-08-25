"""STEP 6 — Execute the method, build/run the task graph, or delegate.

CONTRACT   PractitionerState + ExecutionPlan  ->  ResultPacket[]
REQUIRED   yes
WAYS       run a deterministic node · run a task graph · one model call ·
           author via an OpenCode worker · spawn Practitioner Loops ·
           matrix-of-solutions waterfall
EXTEND     register an executor behind execute(spec)->outcome and add it to the
           store; add a policy kind in rl_vocabulary.

A WorkPacket runs many deterministic ops per pass to a decision boundary — a
10,000-op task is not 10,000 passes.  Spawned Loops run the SAME kernel with a
narrower goal.
"""
from ...loop.kernel import ResultPacket, default_act
from ...code_nodes.competition_solver import (EXECUTORS, execute_tabular, execute_image,
                                 ExecOutcome)
from ...code_nodes.rl_vocabulary import (build_policy, search_action_sequences, train_q,
                            POLICY_KINDS, rollout)
from ...static_architecture.opencode_client import run_agent, parallel_agents
from ...loop.canvas import Canvas, SolutionSlot, execute_matrix
from ...loop.sub_practitioner import spawn_sub_practitioner

__all__ = ["ResultPacket", "default_act", "EXECUTORS", "execute_tabular",
           "execute_image", "ExecOutcome", "build_policy",
           "search_action_sequences", "train_q", "POLICY_KINDS", "rollout",
           "run_agent", "parallel_agents", "Canvas", "SolutionSlot",
           "execute_matrix", "spawn_sub_practitioner"]
