"""STEP 4 — Generate, challenge, and select the most valuable next action.

CONTRACT   PractitionerState + Situation  ->  CandidateAction[]
REQUIRED   yes
WAYS       deterministic rule · muscle-memory · heuristic · one model call ·
           council/debate · biased by the opening-move sequence
EXTEND     register a bias (BIAS_REGISTRY) or a question form / strategy; or
           provide a `decide_next` impl to change candidate generation.

Standing biases are instincts that must EARN their keep (paired trials, evidence
demotion).  The opening-move Task Blueprint biases early passes toward context /
outline before solving — the secret sauce, as a swappable resource.
"""
from ...loop.kernel import CandidateAction, default_decide_next
from ...strings.biases import (BIAS_REGISTRY, apply_biases, BiasLedger, paired_trial,
                     record_paired_outcome)
from ...strings.task_blueprint import (TaskBlueprint, default_opening_sequence,
                             bias_next_from_blueprint)
from ...strings.ask_strategies import StrategyRegistry, run_strategy, core_strategies
from ...static_architecture.ollama_resolvers import debate, make_ollama_council, deep_deliberate

__all__ = ["CandidateAction", "default_decide_next", "BIAS_REGISTRY",
           "apply_biases", "BiasLedger", "paired_trial", "record_paired_outcome",
           "TaskBlueprint", "default_opening_sequence",
           "bias_next_from_blueprint", "StrategyRegistry", "run_strategy",
           "core_strategies", "debate", "make_ollama_council",
           "deep_deliberate"]
