# Architecture map (generated)

> Generated 2026-08-25 by `PYTHONPATH=src python3 -m loop_engine --map`. Regenerate rather than hand-edit; freshness is gated (`architecture_map_freshness`).

ARCHITECTURE MAP: four top-level abstractions
  loop/  (48 modules)
    acceptance, arbiter, builtin_resolvers, canvas, context_shuffle, decision_engine, decision_slates, escalation_governor, hybrid_dimension_lattice, research_to_capability, list_intelligence, decision_envelope, decision_episode, decision_need, delegation, deliberation, kernel, kernel_model_impls, lens, loop, loop_handlers, loop_templates, methodical, moves, intelligence_loops, practitioner_campaign, practitioner_loop, practitioner_methods, receipts, effective_spec, encapsulate, loop_capsule, loop_contract, loop_doctrine, recursive_loop, regimes, registry, resolvers, route_bridge, runner, solve, solver, step_registry, steps, studio, sub_practitioner, tuning, wiring
  strings/  (19 modules)
    ask_strategies, bias_checklist, biases, context, decision_schemas, domain_pack, frame, intelligence_strings, interrogation, knowledge, knowledge_state, notes, output_templates, packs, prompt_fragments, question_bank, question_engine, solution_shaping, task_blueprint
  code_nodes/  (37 modules)
    blueprint, capture, closure, context_seed, competition_solver, enrichment, failure_response, follow_up, housekeeping, kaggle_executor, live_run_demo, learning_bundle, guided_setup, logic_ast, universal_solve, loop_report, measurement, pack_curation, planning, public_examples, review_mode, change_proposals, foundry_probes, guidance_ledger, rl_vocabulary, run_analytics, run_playback, run_quality, runtime_contracts, self_improve, self_improvement_loop, smoke_ladder, solution_canvas, solution_compiler, solution_graph, solution_records, string_foundry
  static_architecture/  (35 modules)
    asset_class, asset_lifecycle, capability_directory, chronicle, config, context_catalog, context_classification, event_vocabulary, duckdb_catalog, facets, intelligence_layers, runtime_memory, user_intelligence, intelligence_registry, model_call, model_routes, ollama_client, ollama_resolvers, mistral_client, openrouter_client, provider_failover, model_discovery, autoconfigure, custom_endpoint, knowledge_loader, opencode_client, operating_profile, persistence, reasoning_call, retrieval, solution_library, store_serve, boundary_registry, saas_routes, studio_server

THE REFERENCE NINE-STEP PROFILE: detailed step map

STEP 1: orient  [REQUIRED]
  Reconstruct the latest accepted problem state and assemble the verified context already available
  Q: What problem are we solving, and what verified context do we already have?
  PractitionerState  ->  Situation
  ways: cached state, retrieval, deterministic reconstruction
  modules:
    - kernel: default_orient (state reconstruction)
    - store_serve: search relevant resources
    - context: Context Views over memory
    - kernel_model_impls: orient (search-backed situation)
  default: kernel.default_orient
  extend: provide an `orient` impl returning a Situation; register context sources as searchable resources

STEP 2: reconcile_horizon  [OPTIONAL]
  Reconcile the ultimate goal, active checkpoint, and working blueprint with the latest accepted state
  Q: Where does this stand against the ultimate goal, the active checkpoint, and the working blueprint?
  PractitionerState + Situation  ->  LongHorizonAnchorPacket
  ways: no-op minimal anchor, goal-stack + blueprint reconciliation, typed Goal Graph / Plan Frontier
  modules:
    - blueprint: GoalStack, WorkingBlueprint, LongHorizonAnchorPacket, build_anchor, WorkPacket, ELABORATION_LEVELS
    - planning: GoalGraph, BlueprintItem, CheckpointContract, PlanFrontier, validate_blueprint
    - task_blueprint: opening-move sequence that biases step 4
    - kernel: default_reconcile_horizon
  default: kernel.default_reconcile_horizon
  extend: provide a `reconcile_horizon` impl returning a LongHorizonAnchorPacket; add plan schemas in planning.py

STEP 3: assess_prepare  [OPTIONAL]
  Assess whether the current decision is sufficiently supported and prepare any additional evidence, questions, perspectives, or research
  Q: Is the current decision sufficiently supported, and if not, what evidence / questions / perspectives / research should we prepare?
  PractitionerState + Situation  ->  DecisionSupportPortfolio
  ways: sufficient_no_expansion, retrieve reusable resources, generate provisional resources, spawn a research child
  modules:
    - enrichment: coverage_probe, generate_enrichment (personas/questions)
    - question_engine + question_bank: question forms and tiers
    - capture: required opening scaffolding (research, outline, watch-outs, common/uncommon mistakes, best practices, success measures)
    - sub_practitioner: spawn a research child practitioner
    - kernel: default_assess_prepare
  default: kernel.default_assess_prepare
  extend: provide an `assess_prepare` impl; register question/persona generators and research recipes

STEP 4: decide_next  [REQUIRED]
  Generate, challenge, and select the most valuable next action that advances the active checkpoint without violating the broader blueprint
  Q: What is the most valuable next action that advances the checkpoint without violating the blueprint?
  PractitionerState + Situation  ->  CandidateAction[]
  ways: deterministic rule, muscle-memory shortcut, heuristic, one model call, council / debate, biased by opening sequence
  modules:
    - biases: apply_biases (standing instincts, evidence-demotable)
    - bias_checklist: semi-persistent preferred-steps checklist carried in every prompt (research-first; before AND after; skips tracked with why/when/where/how; freedom to choose once all steps resolved)
    - task_blueprint: bias_next_from_blueprint (opening moves)
    - solution_shaping: should_decompose (decompose / monolithic / escalate) + shaping strings (outside-the-box, stacking/bagging/ensemble)
    - decision_schemas: prompt-side reasoning shapes that bias what the model CONSIDERS (INTELLIGENCE; check_engagement is a soft signal: admission is runtime_contracts, bridged via to_contract)
    - output_templates: the response-form ladder (string->list->if/then->measurement->evaluation->code) biasing reusable forms
    - follow_up: reactive scheduler obligations (justify/review/structure/reframe) that lead the candidate list
    - failure_response: on an error, bias toward diagnose_and_repair / research / try_other_method (don't hit the same wall; escalate/abstain when exhausted)
    - intelligence_strings: compose reasoning strings into the prompt
    - ask_strategies + question_engine: ways of asking
    - ollama_resolvers: debate / council
    - kernel: default_decide_next; kernel_model_impls: decide_next
  default: kernel.default_decide_next
  extend: register a bias in biases.py or a question form/strategy; provide a `decide_next` impl to change candidate generation

STEP 5: how  [REQUIRED]
  Find, adapt, compose, or design the most appropriate method for carrying out the selected action
  Q: What is the best available method to carry out that action?
  PractitionerState + Situation + CandidateAction  ->  ExecutionPlan
  ways: exact reuse, learned shortcut, deterministic wrapper, compose / configure, template mutate, generate
  modules:
    - methodical: EXECUTION_LADDER + reuse_first_guard (cheapest-first)
    - self_improve: shortcut probe (learned zero-model routes)
    - store_serve: capability search (find_executor / nodes)
    - solution_shaping: sub-model / sub-process / ensemble moves
    - config: permit_plan (authority gates)
    - kernel: default_how
  default: kernel.default_how
  extend: register a node/executor as a searchable resource; provide a `how` impl to change method selection

STEP 6: act  [REQUIRED]
  Execute the method, build or run the required task graph, or delegate bounded subproblems to child practitioners
  Q: How do we execute it, build the task graph, or delegate to a child practitioner?
  PractitionerState + ExecutionPlan  ->  ResultPacket[]
  ways: run a deterministic node, run a task graph, one model call, author via OpenCode worker, spawn child practitioners, matrix waterfall
  modules:
    - competition_solver: tabular/image executors (searchable nodes)
    - rl_vocabulary: policies + novelty/action search
    - opencode_client: headless coding workers
    - sub_practitioner + kernel.run_practitioner: child practitioners
    - canvas: matrix-of-solutions execution
    - kaggle_executor: real tabular submissions
    - kernel: default_act
  default: kernel.default_act
  extend: register an executor node behind execute(spec)->outcome and add it to the resource store; add a policy kind in rl_vocabulary

STEP 7: verify  [REQUIRED]
  Independently interrogate the inputs, outputs, and process; test the results, compare alternatives, and identify remaining gaps or failures
  Q: Did it work, is it better than the alternatives, and what gaps remain?
  PractitionerState + ExecutionPlan + ResultPacket[]  ->  EvaluationPacket
  ways: deterministic checks, degeneracy detectors, contract check, model interrogation, adversarial review
  modules:
    - review_mode: degeneracy detectors + the interrogatory battery (a constant / chance-level / empty result is DEGENERATE, rejected)
    - measurement: select_measures + read_generalization_gap (train-CV gap) + measurement strings (metrics, industry conventions, success framing)
    - interrogation: the expert questions that separate naive from expert solutions (residual patterns, latent structure, errors-of-errors, is-this-the-best-way); each says if a code node or an LLM answers it
    - kernel: default_verify
  default: kernel.default_verify
  extend: add a detector or interrogatory in review_mode.py; provide a `verify` impl for domain evaluators

STEP 8: integrate_commit  [OPTIONAL]
  Integrate accepted results, update the blueprint and checkpoint state, and commit validated evidence, artifacts, and reusable learning
  Q: What accepted results and reusable learning do we commit to memory?
  PractitionerState + PassRecord  ->  committed PractitionerState
  ways: no-op (route commits), distill shortcuts, update plan + checkpoint, track dispositions
  modules:
    - self_improve: could_this_be_cheaper -> distill a Shortcut
    - capture: encapsulate open-ended results into standardized reusable units + the fail-closed gate before composing the next step
    - learning_bundle: every pass gets a LearningBundle + disposition; requires_additional_structuring blocks integration (3 storage stages)
    - planning: complete_item / satisfy (evidence-gated)
    - closure: track item dispositions for the no-orphan audit
    - kernel: default_integrate_commit
  default: kernel.default_integrate_commit
  extend: provide an `integrate_commit` impl to commit domain artifacts; add a distillation trigger in self_improve.py

STEP 9: route  [REQUIRED]
  Choose whether to continue the checkpoint, revise the blueprint, branch, retry, reset, distill, escalate, close a checkpoint, or finish
  Q: Should we continue, branch, retry, reset, distill, escalate, or finish?
  PractitionerState + PassRecord  ->  RouteDecision + new PractitionerState
  ways: continue, repair, reset ladder (soft->cold), branch, distill, escalate, close checkpoint, finish
  modules:
    - kernel: default_route (repair->soft_reset->cold_restart escalation)
    - closure: audit_run (fail-closed no-orphan check before close)
    - kernel: plan_skip_next_pass (per-pass optional-node skip)
    - practitioner_loop: logjam detection + documented reset (reference)
  default: kernel.default_route
  extend: provide a `route` impl to emit richer routes (branch/distill/escalate); call closure.audit_run before finishing

CROSS-CUTTING SERVICES (used by many steps, never step-specific):
  - model-call DAG  [model_call + reasoning_call + model_routes]
      every model call: ReasoningRequest -> PromptAssemblySpec (13 blocks) -> ModelInvocationRequest -> ModelInvocationResult; provider-neutral routes (cloud-only policy, local wired-but-gated); fallbacks + seeds
  - two primitives (String | Code node)  [asset_class]
      THE classification of everything: literally every resource, asset, node, and text is a STRING (an LLM reads it) or a CODE NODE (the machine runs it; may READ strings). 'Contract / logic / capability' are ROLES a code node plays (validate / decide / execute / adapt / detect), not separate primitives. Same need, either primitive; the arrow STRING -> CODE NODE is the distillation flywheel
  - logic (safe AST)  [logic_ast]
      the Logic category: a closed-operator expression AST (never eval) that COMPUTES/DECIDES deterministically; the executor for a captured logic_candidate; emits findings/actions, abstains outside scope, never mutates state
  - capability directory (handshakes + endpoints)  [capability_directory]
      how the practitioner KNOWS what strings / code nodes / static components are available and HOW to call them: a CapabilityHandshake per surface (kind, operations, query fields, ranking, health: read before use, never assumed), and a standardized directory (discover / negotiate / call / serve) with declared fallbacks. serve() is the two-rail bias: use a code node if one serves the op, else fall back to the LLM-call pipeline
  - real loop handlers  [loop_handlers]
      the Loop on the REAL infrastructure: directory_handler pulls the mandatory string intelligence per step (the power lever), probes the code rail with a real search through the capability directory, resolves deterministic steps to real code nodes, escalates an empty code rail to the LLM surface (hybrid), and records every infra call on the ledger; run_loop_via_kernel delegates a nine_step loop to the wired kernel
  - the Loop (everything is a loop)  [recursive_loop]
      the fundamental object: a Loop is an initializable, parameterized CLASS: pass in framework (nine_step | five_step | custom | open), allowable + preferred MODES (deterministic | hybrid | non_deterministic, a waterfall with fallback), and a POWER lever (small..max sets string-intelligence pull + model-call budget). One loop can SPAWN another (recursive initialization; loops of loops), all tracked on one shared ledger. nine_step is the default; the kernel is its executor. The wedge is reusable code nodes + string intelligence flowing through it
  - decision engine (per-node sub-layer)  [decision_engine]
      the immediate sub-node under EVERY one of the nine kernel nodes: resolve_path asks 'deterministic, deterministic + LLM repair, or non-deterministic?' and branches into three, deciding from heuristics / memory / policy (settings like model + internet access gate the paths): the two-rail choice refined into three, one engine per node
  - continuous improvement (housekeeping)  [housekeeping]
      a SEPARATE-PURPOSE run of the SAME practitioner loop (self-improvement objective + instructions): on a trigger/cron it mines our runtimes/logs and customer legacy code (GitHub URLs) and proposes new code nodes, strings, logic, and biases: classified string vs code, all runtime CANDIDATES (promotion is the evidence-gated boundary, never done here)
  - live wiring  [wiring]
      the composed entry point run_wired: enriches the deterministic kernel defaults so the LIVE loop exercises guidance, shaping, measurement, contracts, capture, and learning end-to-end
  - runtime contracts  [runtime_contracts]
      executable TRUTH at every boundary: ContractDefinition (immutable, versioned) + deterministic validator + explicit adapter. Distinct authority from intelligence: a contract ADMITS/REJECTS a result; intelligence only PROPOSES a contract (to_contract / ContractCandidate)
  - search / serve DAG  [store_serve]
      one strict search over ALL resources (nodes, packs, rules, prior runs); tier gates; capability requests
  - resources  [question_engine + question_bank + domain_pack + intelligence_strings + intelligence_registry + packs]
      question forms/tiers, personas, context/layout policies, Domain Support Packs, and intelligence-as-strings; intelligence_registry standardizes the Database vs Runtime tiers (serve/version/track/promote)
  - operating profile + config  [operating_profile + config]
      five enum modes resolved Platform->Org->Project->Run->Child; enforced at the how/act/model boundaries
  - model transport  [ollama_client + opencode_client]
      Ollama Cloud (token-counted) + OpenCode headless workers (cloud-only)
