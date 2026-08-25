"""What Is Next — the expert's loop as the organizing spine of the solver.

An expert runs one loop: *here is what I presently know; given that, what is
next?*  This package makes that loop the centre of the system.  A **Practitioner**
runs it; **Knowledge** is what it presently knows (as references, not full
context); a **WhatIsNextResolver** is one named way to answer, and the resolver
CATEGORIES are the clean paths — deterministic rule, plan/recipe, fingerprint
recall (muscle memory), embedding similarity, small model, hybrid, test-driven,
research, one model, a council, blind, persona-salted, or a custom special case;
a **Move** is what an answer proposes to DO (not only "add a node" — also run
tests, do research, gather context, spawn sub-loops, ensemble, …); and an
**AskFrame** carries the persona/prompt dimensions.

New "what is next?" regimes are added with one call —
``register_regime(name, category, fn)`` — so the ontology stays open.  The loop
resolves cheapest-category-first via the escalation governor, so most steps cost
no model call; a council or research is the last resort.  Nothing here decides
truth: an answer orders what to try; the fold oracle decides what worked, and a
blind/random resolver always rides along so muscle memory never becomes destiny.

Public entry points::

    from ...benchmarks.whats_next import (Practitioner, Knowledge, AskFrame,
        move, answer, register_regime, register_builtins)

Self-test::

    PYTHONPATH=. python3 -m loop_engine --self-test
"""

from __future__ import annotations

from .strings.frame import AskFrame
from .strings.knowledge import Knowledge, CONTEXT_LEVELS
from .strings.knowledge_state import (Claim, Unknown, Contradiction, EpistemicState,
                              KnowledgeDelta, CLAIM_STATUSES, GROUND_STATUSES)
from .loop.moves import (MOVE_TYPES, MOVE_FAMILIES, move, answer, WhatIsNextAnswer,
                    family_of, is_valid_move_kind)
from .loop.decision_need import (FrontierItem, DecisionNeed, detect_decision_need,
                            frontier_from_state, DECISION_MODES,
                            DECISION_NEED_KINDS, MODE_MOVE_FAMILIES)
from .loop.resolvers import (RESOLVER_CATEGORIES, DEFAULT_CATEGORY_LEVEL,
                        MODEL_CATEGORIES, WhatIsNextResolver, ResolveFn)
from .loop.registry import (ResolverRegistry, DEFAULT_REGISTRY, register_regime,
                       register, registered_resolvers)
from .loop.loop import SolverCell, Practitioner, StepReceipt, ensemble_answers
from .loop.builtin_resolvers import (register_builtins, plan_recipe_resolver,
                                blind_baseline_resolver,
                                make_fingerprint_resolver)
from .loop.regimes import (register_library, catalog as regime_catalog,
                      make_recall_resolver, make_solved_route_replay,
                      make_analogy_transfer, make_single_model_regime,
                      make_council_regime, make_research_regime)
from .loop.deliberation import (DeliberationResult, blueprint_then_refine,
                           fan_out_and_test, multi_context_probe,
                           as_resolver as deliberation_as_resolver)
from .loop.lens import (LensSpec, ROLE_LENSES, METHOD_LENSES, get_lens, apply_lens)
from .strings.context import (ContextView, CONTEXT_POLICIES, build_view, build_lanes)
from .strings.packs import (Pack, PackItem, PackRegistry, PACK_KINDS, pack_from_dict,
                    seed_registry)
from .loop.arbiter import (Candidate, NextMoveDecision, arbitrate, pareto_front,
                      HARD_GATES, POLICY_WEIGHTS)
from .loop.delegation import (SubproblemSpec, JOIN_POLICIES, join_children,
                         request_fingerprint, ImpasseGuard, check_depth)
from .loop.receipts import (SolverIterationReceipt, build_iteration_receipt,
                       verify_chain)
from .loop.runner import SolverCellState, iterate, run
from .loop.practitioner_methods import (Check, Checklist, WeightedRule,
                                   checklist_resolver, checklist_status,
                                   weighted_heuristic_resolver,
                                   linear_regression_checklist)
from .strings.notes import (NoteTemplate, Note, NoteStore, NOTE_KINDS, NOTE_STATUSES,
                    fill_note, measure_note, council_review)
from .loop.context_shuffle import (ShuffleFrame, DISTANT_DOMAINS, COGNITION_MODES,
                              make_shuffle_frame, shuffle_lanes,
                              cross_domain_bridge)
from .loop.decision_envelope import DecisionEnvelope
from .strings.prompt_fragments import (PromptFragment, PromptRecipe, FragmentRegistry,
                               seed_registry as seed_fragment_registry)
from .loop.decision_episode import (ProposalRecord, DecisionEpisode, EpisodeStore)
from .code_nodes.pack_curation import (PackItemCandidate, curate_from_findings,
                            review_candidate, promote_candidates)
from .loop.studio import StudioView, build_studio_view, render_markdown, render_html
from .static_architecture.persistence import (persist_note, load_notes, persist_episode,
                          load_episodes, persist_receipt, load_receipts)
from .loop.route_bridge import (RoutePriors, priors_from_slate, merge_priors,
                           bridge_from_decision)
from .loop.acceptance import self_test as acceptance_invariants
from .static_architecture.ollama_client import chat as ollama_chat, verify as ollama_verify, live_models, ChatResult
from .static_architecture.ollama_resolvers import (make_ollama_regime, make_ollama_proposer,
                               render_next_move_prompt, parse_moves,
                               deep_deliberate, make_ollama_council,
                               COUNCIL_MODELS)
# kaggle_executor: resolved LAZILY — see _PUBLIC below
from .static_architecture.opencode_client import (AgentResult, run_agent, parallel_agents,
                             build_command, DEFAULT_WORKER_MODEL)
from .loop.practitioner_loop import (NODE_SEQUENCE, CONTROL_SIGNALS, RESOLUTION_PATHS,
                               TUNING_DESIGN, NodeResult, LoopState,
                               PractitionerNode, run_practitioner_loop,
                               default_nodes, run_default, swarm_practitioner,
                               make_model_nodes)
from .loop.methodical import (CYCLE_STAGES, WHATS_NEXT_ANSWER_KINDS, ANSWER_KINDS,
                        EXECUTION_LADDER, VERIFY_OUTCOMES, GuardViolation,
                        NextAnswer, ExecutionDecision, VerifyResult, CycleStep,
                        run_cycle, run_cycle_deterministic, run_cycle_models,
                        make_model_cycle, reuse_first_guard, advance_guard)
from .loop.canvas import (CANVAS_KINDS, TypeContract, CanvasNode, SolutionSlot,
                    Canvas, SlotOutcome, MatrixExecution, execute_matrix)
from .loop.sub_practitioner import (MAX_PRACTITIONER_DEPTH, DepthExceeded,
                              SubPractitionerResult, spawn_sub_practitioner,
                              make_spawning_node, standard_order_decider,
                              run_orchestrated, make_llm_order_decider)
from .code_nodes.self_improve import (problem_signature, Shortcut, ShortcutStore,
                          CheaperVerdict, could_this_be_cheaper,
                          learn_from_cycle, make_learning_probe)
# `solve` is NOT re-exported here: the public front door is
# code_nodes.universal_solve.solve, which orients on the task and
# delegates HERE when there is no data. Two public functions named
# `solve` is the confusion that front door exists to remove.
from .loop.solver import (SOLVER_MODES, SolveResult, UniversalSolver,
                         solve as solve_from_knowledge)
from .loop.tuning import (TUNING_PLACES, TUNING_STRATEGIES, TuningPolicy, ParamSpec,
                    TuningResult, tune, grid_search, heuristic_search)
from .static_architecture.model_call import (DEFAULT_MODEL_CHAIN, CALL_STAGES, AskSpec, AskResult,
                        execute_ask, prepare_context, render as render_ask)
from .static_architecture.store_serve import (STORE_KINDS, TIERS, StoreRecord, SolverStore,
                         core_seed)
from .strings.ask_strategies import (STRATEGY_SHAPES, StrategySpec, StrategyRegistry,
                            core_strategies, run_strategy)
from .loop.practitioner_loop import detect_logjam, logjam_reset
from .loop.kernel import (KERNEL_NODES, HOW_MODES, ACT_MODES, VERIFY_VERDICTS,
                    ROUTES, RESET_MODES, ProblemSpec, PractitionerState,
                    Situation, CandidateAction, ExecutionPlan, ResultPacket,
                    EvaluationPacket, RouteDecision, PassRecord, DecisionSupportPortfolio,
                    SUFFICIENCY_OUTCOMES, KERNEL_NODES, KERNEL_NODE_NAMES,
                    default_reconcile_horizon,
                    KERNEL_NODE_QUESTIONS, KERNEL_REQUIRED_NODES,
                    KERNEL_OPTIONAL_NODES, KernelHandshakeError, handshake,
                    validate_impls, plan_skip_next_pass, run_pass,
                    run_practitioner, run_swarm, SwarmChildSpec,
                    default_impls as default_kernel_impls)
from .strings.question_engine import (ANSWER_SHAPES, SEED_SALTS, QuestionForm,
                             AskVariant, core_forms, multiply,
                             combination_space, register_generated_form,
                             as_store_records as question_forms_as_records)
from .loop.kernel_model_impls import make_model_impls
from .code_nodes.enrichment import (EnrichmentPolicy, CoverageReport, coverage_probe,
                        generate_enrichment, domain_terms)
from .static_architecture.model_call import PROMPT_ASSEMBLY_ORDER
from .code_nodes.review_mode import (REVIEW_VERDICTS, INTERROGATORIES, ReviewFinding,
                         ReviewReport, review, detect_constant_output,
                         detect_chance_level, detect_too_perfect)
from .strings.biases import (BIAS_REGISTRY, TRIAL_ARMS, BIAS_VERDICTS, BiasTrial,
                    BiasLedger, paired_trial, record_paired_outcome,
                    apply_biases)
from .static_architecture.config import (OPTIMIZE_FOR, REUSE_SOURCES, SolverConfig, Budgets,
                    ConfigViolation, TokenMeter, screen_models, permit_plan,
                    config_details)
# rl_vocabulary: resolved LAZILY — see _PUBLIC below
# competition_solver: resolved LAZILY — see _PUBLIC below
from .static_architecture.operating_profile import (ACCESS_MODES, REASONING_MODES,
                               CONSTRUCTION_MODES, EFFORT_MODES,
                               OPTIMIZATION_MODES, Limits, OperatingProfile,
                               resolve_chain, to_solver_config)
from .static_architecture.reasoning_call import (PROMPT_BLOCKS, PROMPT_LAYOUT_POLICIES, Seeds,
                             ReasoningRequest, PromptAssemblySpec,
                             ModelInvocationRequest, ModelInvocationResult,
                             layout_order, assemble_prompt, to_invocation,
                             invoke, run_reasoning)
from .code_nodes.blueprint import (BLUEPRINT_LEVELS, ELABORATION_LEVELS, CHECKPOINT_STATES,
                       DECISION_BOUNDARIES, Checkpoint, GoalStack,
                       WorkingBlueprint, Progress, WorkPacket,
                       LongHorizonAnchorPacket, grounding_summary, build_anchor,
                       seed_from_objective)
from .strings.question_bank import (MATURITY, QuestionDefinition, QuestionPattern,
                            QuestionInstance, QuestionOutcomeRecord, QuestionBank)
from .strings.domain_pack import (PACK_PARTS, DomainSupportPack, install_pack,
                         cardiology_pack)
from .code_nodes.closure import (TERMINAL_DISPOSITIONS, ITEM_KINDS, TrackedItem, RunLedger,
                     ClosureVerdict, audit_run)
from .code_nodes.planning import (GOAL_KINDS, GOAL_STATUS, BLUEPRINT_ITEM_KINDS,
                      BLUEPRINT_ITEM_STATUS, BLUEPRINT_EDGE_TYPES,
                      CHECKPOINT_STATUS, PlanInvariantError, GoalNode, GoalGraph,
                      GoalBinding, BlueprintItem, CheckpointContract,
                      WorkingBlueprint as TypedWorkingBlueprint, PlanFrontier,
                      compute_frontier, validate_blueprint)
from .strings.task_blueprint import (OPENING_MOVE_KINDS, OpeningMove, TaskBlueprint,
                            default_opening_sequence, bias_next_from_blueprint)
from .loop.step_registry import (KernelStep, KERNEL_STEP_REGISTRY, SERVICE_MAP, step,
                            steps_for_module, render_step, render_map)
from ._self_test import self_test

__all__ = [
    "AskFrame", "Knowledge", "CONTEXT_LEVELS",
    "Claim", "Unknown", "Contradiction", "EpistemicState", "KnowledgeDelta",
    "CLAIM_STATUSES", "GROUND_STATUSES",
    "MOVE_TYPES", "MOVE_FAMILIES", "move", "answer", "WhatIsNextAnswer",
    "family_of", "is_valid_move_kind",
    "FrontierItem", "DecisionNeed", "detect_decision_need",
    "frontier_from_state", "DECISION_MODES", "DECISION_NEED_KINDS",
    "MODE_MOVE_FAMILIES",
    "RESOLVER_CATEGORIES", "DEFAULT_CATEGORY_LEVEL", "MODEL_CATEGORIES",
    "WhatIsNextResolver", "ResolveFn",
    "ResolverRegistry", "DEFAULT_REGISTRY", "register_regime", "register",
    "registered_resolvers",
    "SolverCell", "Practitioner", "StepReceipt", "ensemble_answers",
    "register_builtins", "plan_recipe_resolver", "blind_baseline_resolver",
    "make_fingerprint_resolver",
    "register_library", "regime_catalog", "make_recall_resolver",
    "make_solved_route_replay", "make_analogy_transfer",
    "make_single_model_regime", "make_council_regime", "make_research_regime",
    "DeliberationResult", "blueprint_then_refine", "fan_out_and_test",
    "multi_context_probe", "deliberation_as_resolver",
    "LensSpec", "ROLE_LENSES", "METHOD_LENSES", "get_lens", "apply_lens",
    "ContextView", "CONTEXT_POLICIES", "build_view", "build_lanes",
    "Pack", "PackItem", "PackRegistry", "PACK_KINDS", "pack_from_dict",
    "seed_registry",
    "Candidate", "NextMoveDecision", "arbitrate", "pareto_front", "HARD_GATES",
    "POLICY_WEIGHTS",
    "SubproblemSpec", "JOIN_POLICIES", "join_children", "request_fingerprint",
    "ImpasseGuard", "check_depth",
    "SolverIterationReceipt", "build_iteration_receipt", "verify_chain",
    "SolverCellState", "iterate", "run",
    "Check", "Checklist", "WeightedRule", "checklist_resolver",
    "checklist_status", "weighted_heuristic_resolver",
    "linear_regression_checklist",
    "NoteTemplate", "Note", "NoteStore", "NOTE_KINDS", "NOTE_STATUSES",
    "fill_note", "measure_note", "council_review",
    "ShuffleFrame", "DISTANT_DOMAINS", "COGNITION_MODES", "make_shuffle_frame",
    "shuffle_lanes", "cross_domain_bridge",
    "DecisionEnvelope",
    "PromptFragment", "PromptRecipe", "FragmentRegistry",
    "seed_fragment_registry",
    "ProposalRecord", "DecisionEpisode", "EpisodeStore",
    "PackItemCandidate", "curate_from_findings", "review_candidate",
    "promote_candidates",
    "StudioView", "build_studio_view", "render_markdown", "render_html",
    "persist_note", "load_notes", "persist_episode", "load_episodes",
    "persist_receipt", "load_receipts",
    "RoutePriors", "priors_from_slate", "merge_priors", "bridge_from_decision",
    "acceptance_invariants",
    "make_ollama_regime", "make_ollama_proposer", "render_next_move_prompt",
    "parse_moves", "deep_deliberate", "make_ollama_council", "COUNCIL_MODELS",
    "TaskRoles", "ExecutionResult", "resolve_roles", "estimator_from_moves",
    "execute_tabular",
    "AgentResult", "run_agent", "parallel_agents", "build_command",
    "DEFAULT_WORKER_MODEL",
    "CYCLE_STAGES", "WHATS_NEXT_ANSWER_KINDS", "ANSWER_KINDS",
    "EXECUTION_LADDER", "VERIFY_OUTCOMES", "GuardViolation", "NextAnswer",
    "ExecutionDecision", "VerifyResult", "CycleStep", "run_cycle",
    "run_cycle_deterministic", "run_cycle_models", "make_model_cycle",
    "reuse_first_guard", "advance_guard",
    "NODE_SEQUENCE", "CONTROL_SIGNALS", "RESOLUTION_PATHS", "TUNING_DESIGN",
    "NodeResult", "LoopState", "PractitionerNode", "run_practitioner_loop",
    "default_nodes", "run_default", "swarm_practitioner", "make_model_nodes",
    "CANVAS_KINDS", "TypeContract", "CanvasNode", "SolutionSlot", "Canvas",
    "SlotOutcome", "MatrixExecution", "execute_matrix",
    "MAX_PRACTITIONER_DEPTH", "DepthExceeded", "SubPractitionerResult",
    "spawn_sub_practitioner", "make_spawning_node", "standard_order_decider",
    "run_orchestrated", "make_llm_order_decider",
    "problem_signature", "Shortcut", "ShortcutStore", "CheaperVerdict",
    "could_this_be_cheaper", "learn_from_cycle", "make_learning_probe",
    "SOLVER_MODES", "SolveResult", "UniversalSolver", "solve",
    "TUNING_PLACES", "TUNING_STRATEGIES", "TuningPolicy", "ParamSpec",
    "TuningResult", "tune", "grid_search", "heuristic_search",
    "DEFAULT_MODEL_CHAIN", "CALL_STAGES", "AskSpec", "AskResult",
    "execute_ask", "prepare_context", "render_ask",
    "STORE_KINDS", "TIERS", "StoreRecord", "SolverStore", "core_seed",
    "STRATEGY_SHAPES", "StrategySpec", "StrategyRegistry", "core_strategies",
    "run_strategy", "detect_logjam", "logjam_reset",
    "KERNEL_NODES", "HOW_MODES", "ACT_MODES", "VERIFY_VERDICTS", "ROUTES",
    "RESET_MODES", "ProblemSpec", "PractitionerState", "Situation",
    "CandidateAction", "ExecutionPlan", "ResultPacket", "EvaluationPacket",
    "RouteDecision", "PassRecord", "DecisionSupportPortfolio",
    "SUFFICIENCY_OUTCOMES", "KERNEL_NODES", "KERNEL_NODE_NAMES",
    "KERNEL_NODE_QUESTIONS", "KERNEL_REQUIRED_NODES",
    "KERNEL_OPTIONAL_NODES", "KernelHandshakeError", "handshake",
    "validate_impls", "plan_skip_next_pass", "run_pass",
    "run_practitioner",
    "run_swarm",
    "SwarmChildSpec", "default_kernel_impls",
    "ANSWER_SHAPES", "SEED_SALTS", "QuestionForm", "AskVariant", "core_forms",
    "multiply", "combination_space", "register_generated_form",
    "question_forms_as_records", "make_model_impls",
    "EnrichmentPolicy", "CoverageReport", "coverage_probe",
    "generate_enrichment", "domain_terms", "PROMPT_ASSEMBLY_ORDER",
    "OPTIMIZE_FOR", "REUSE_SOURCES", "SolverConfig", "Budgets",
    "ConfigViolation", "TokenMeter", "screen_models", "permit_plan",
    "config_details", "BIAS_REGISTRY", "apply_biases", "TRIAL_ARMS",
    "BIAS_VERDICTS", "BiasTrial", "BiasLedger", "paired_trial",
    "record_paired_outcome",
    "REVIEW_VERDICTS", "INTERROGATORIES", "ReviewFinding", "ReviewReport",
    "review", "detect_constant_output", "detect_chance_level",
    "detect_too_perfect",
    "POLICY_KINDS", "Trajectory", "rollout", "RandomPolicy", "HeuristicPolicy",
    "ScriptedPolicy", "EpsilonGreedyQPolicy", "UCBBandit", "NoveltyArchive",
    "build_policy", "train_q", "cross_entropy_method",
    "search_action_sequences",
    "MODALITIES", "CompetitionSpec", "resolve_competition", "ExecOutcome",
    "execute_image", "execute_tabular", "EXECUTORS", "executor_node_records",
    "build_competition_store", "find_executor", "make_competition_impls",
    "CompetitionResult", "solve_competition",
    "ACCESS_MODES", "REASONING_MODES", "CONSTRUCTION_MODES", "EFFORT_MODES",
    "OPTIMIZATION_MODES", "Limits", "OperatingProfile", "resolve_chain",
    "to_solver_config",
    "PROMPT_BLOCKS", "PROMPT_LAYOUT_POLICIES", "Seeds", "ReasoningRequest",
    "PromptAssemblySpec", "ModelInvocationRequest", "ModelInvocationResult",
    "layout_order", "assemble_prompt", "to_invocation", "invoke",
    "run_reasoning",
    "BLUEPRINT_LEVELS", "CHECKPOINT_STATES", "Checkpoint", "GoalStack",
    "WorkingBlueprint", "Progress", "WorkPacket", "LongHorizonAnchorPacket",
    "grounding_summary", "build_anchor", "seed_from_objective",
    "ELABORATION_LEVELS", "DECISION_BOUNDARIES", "default_reconcile_horizon",
    "TERMINAL_DISPOSITIONS", "ITEM_KINDS", "TrackedItem", "RunLedger",
    "ClosureVerdict", "audit_run",
    "GOAL_KINDS", "GOAL_STATUS", "BLUEPRINT_ITEM_KINDS", "BLUEPRINT_ITEM_STATUS",
    "BLUEPRINT_EDGE_TYPES", "CHECKPOINT_STATUS", "PlanInvariantError",
    "GoalNode", "GoalGraph", "GoalBinding", "BlueprintItem",
    "CheckpointContract", "TypedWorkingBlueprint", "PlanFrontier",
    "compute_frontier", "validate_blueprint",
    "OPENING_MOVE_KINDS", "OpeningMove", "TaskBlueprint",
    "default_opening_sequence", "bias_next_from_blueprint",
    "KernelStep", "KERNEL_STEP_REGISTRY", "SERVICE_MAP", "step",
    "steps_for_module", "render_step", "render_map",
    "MATURITY", "QuestionDefinition", "QuestionPattern", "QuestionInstance",
    "QuestionOutcomeRecord", "QuestionBank",
    "PACK_PARTS", "DomainSupportPack", "install_pack", "cardiology_pack",
    "self_test",
]


# ---------------------------------------------------------------------------
# The public surface the charter documents: `from loop_engine import
# PractitionerLoop, LoopSpec, SolutionSpec`.  Resolved lazily so importing the
# package stays cheap and no import cycle is created — the names below are the
# canonical runtime, not aliases onto a second one.
# ---------------------------------------------------------------------------

_PUBLIC = {
    "PractitionerLoop": ("loop.recursive_loop", "Loop"),
    "Loop": ("loop.recursive_loop", "Loop"),
    "LoopSpec": ("loop.recursive_loop", "LoopConfig"),
    "LoopConfig": ("loop.recursive_loop", "LoopConfig"),
    "LoopLedger": ("loop.recursive_loop", "LoopLedger"),
    "LoopResult": ("loop.recursive_loop", "LoopResult"),
    "SolutionSpec": ("code_nodes.solution_canvas", "SolutionSpec"),
    "SolutionLoopSpec": ("code_nodes.solution_canvas", "SolutionLoopSpec"),
    "run_solution": ("code_nodes.solution_canvas", "run_solution"),
    "EffectiveLoopSpec": ("loop.effective_spec", "EffectiveLoopSpec"),
    "LoopRef": ("loop.loop_capsule", "LoopRef"),
    "LoopCapsule": ("loop.loop_capsule", "LoopCapsule"),
    "Chronicle": ("static_architecture.chronicle", "Chronicle"),
    "EVENT_FAMILIES": ("static_architecture.event_vocabulary",
                       "EVENT_FAMILIES"),
    # Setup surface: bring a key, learn what this installation can run.
    # `configure()` is the first call a new user makes, so it is public.
    "configure": ("static_architecture.autoconfigure", "configure"),
    "ModelAccess": ("static_architecture.autoconfigure", "ModelAccess"),
    "advice_function": ("static_architecture.autoconfigure",
                        "advice_function"),
    "discover_roster": ("static_architecture.model_discovery",
                        "discover_roster"),
    "ModelRoster": ("static_architecture.model_discovery", "ModelRoster"),
    "call_with_failover": ("static_architecture.provider_failover",
                           "call_with_failover"),

    # THE FRONT DOOR: a goal and your data. It works out the shape itself.
    "solve": ("code_nodes.universal_solve", "solve"),
    "read_task": ("code_nodes.universal_solve", "read_task"),
    "TaskReading": ("code_nodes.universal_solve", "TaskReading"),
    "load_knowledge": ("static_architecture.knowledge_loader",
                       "load_knowledge"),
    "load_into_store": ("static_architecture.knowledge_loader",
                        "load_into_store"),
    "run_setup": ("code_nodes.guided_setup", "run_setup"),

    # --- DOMAIN ADAPTERS: resolved lazily -------------------------------
    # These are ONE domain (tables / competitions / reinforcement learning),
    # not the core. Importing them eagerly made numpy a hard dependency of the
    # whole package — a universal loop runtime that could not be installed
    # without a scientific stack. They keep their names; they are simply not
    # paid for until asked for.
    "TaskRoles": ("code_nodes.kaggle_executor", "TaskRoles"),
    "ExecutionResult": ("code_nodes.kaggle_executor", "ExecutionResult"),
    "resolve_roles": ("code_nodes.kaggle_executor", "resolve_roles"),
    "estimator_from_moves": ("code_nodes.kaggle_executor", "estimator_from_moves"),
    "execute_tabular": ("code_nodes.kaggle_executor", "execute_tabular"),
    "POLICY_KINDS": ("code_nodes.rl_vocabulary", "POLICY_KINDS"),
    "Trajectory": ("code_nodes.rl_vocabulary", "Trajectory"),
    "rollout": ("code_nodes.rl_vocabulary", "rollout"),
    "RandomPolicy": ("code_nodes.rl_vocabulary", "RandomPolicy"),
    "HeuristicPolicy": ("code_nodes.rl_vocabulary", "HeuristicPolicy"),
    "ScriptedPolicy": ("code_nodes.rl_vocabulary", "ScriptedPolicy"),
    "EpsilonGreedyQPolicy": ("code_nodes.rl_vocabulary", "EpsilonGreedyQPolicy"),
    "UCBBandit": ("code_nodes.rl_vocabulary", "UCBBandit"),
    "NoveltyArchive": ("code_nodes.rl_vocabulary", "NoveltyArchive"),
    "build_policy": ("code_nodes.rl_vocabulary", "build_policy"),
    "train_q": ("code_nodes.rl_vocabulary", "train_q"),
    "cross_entropy_method": ("code_nodes.rl_vocabulary", "cross_entropy_method"),
    "search_action_sequences": ("code_nodes.rl_vocabulary", "search_action_sequences"),
    "MODALITIES": ("code_nodes.competition_solver", "MODALITIES"),
    "CompetitionSpec": ("code_nodes.competition_solver", "CompetitionSpec"),
    "resolve_competition": ("code_nodes.competition_solver", "resolve_competition"),
    "ExecOutcome": ("code_nodes.competition_solver", "ExecOutcome"),
    "execute_image": ("code_nodes.competition_solver", "execute_image"),
    "EXECUTORS": ("code_nodes.competition_solver", "EXECUTORS"),
    "executor_node_records": ("code_nodes.competition_solver", "executor_node_records"),
    "build_competition_store": ("code_nodes.competition_solver", "build_competition_store"),
    "find_executor": ("code_nodes.competition_solver", "find_executor"),
    "make_competition_impls": ("code_nodes.competition_solver", "make_competition_impls"),
    "CompetitionResult": ("code_nodes.competition_solver", "CompetitionResult"),
    "solve_competition": ("code_nodes.competition_solver", "solve_competition"),
}


def __getattr__(name):
    """Lazily expose the documented public names."""
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod, attr = target
    from importlib import import_module
    return getattr(import_module(f"{__name__}.{mod}"), attr)


def __dir__():
    return sorted(set(list(globals()) + list(_PUBLIC)))
