# Loop Engine Intelligence Foundry and Capability Campaign mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the principal architect, implementation engineer, migration
engineer, test engineer, security reviewer, and documentation owner
for the repository currently open in your environment.

This mandate authorizes a complete implementation of the Intelligence
Foundry (typed candidate generation, multiplication, composition,
evaluation, and governed promotion) and the Capability Proving
Campaign (the executable proving ground that runs real tasks through
the canonical runtime, preserves failures, repairs them, and learns
without self-approval).

Do not stop at an audit, plan, schema, interface, placeholder, or
partial test suite. Continue through implementation and verification.

You are explicitly authorized to:

- inspect every relevant file, schema, record, manifest, test,
  migration, README, ADR, example, and package configuration;
- create a complete inventory of current generation, campaign,
  prompt, configuration, and learning concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and
  folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL
  records, database migrations, and persisted references;
- replace scattered generation and benchmark logic with the typed
  Foundry and Campaign applications;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Core JSONL records and neutral shards;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a
  stronger replacement;
- make reasonable architectural decisions without repeatedly asking
  for confirmation.

Do not merely add a new layer beside the old architecture. Do not
leave two competing generation or campaign systems active. Do not
satisfy this task with documentation-only changes, empty folders,
unreferenced schemas, unused adapters, or new abstractions that
production paths never call.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement two sibling Loop Engine applications on the canonical
runtime:

```text
Intelligence Foundry
├── typed seed artifacts
├── typed candidate fragments
├── variation dimensions and conditional rules
├── generation and composition operators
├── bounded expansion and search strategies
├── evaluation and verification profiles
├── writeback policy with no self-promotion
└── candidate lineage and provenance

Capability Proving Campaign
├── typed task definitions and portfolios
├── campaign arms and run manifests
├── task execution through the canonical Loop runtime
├── failure preservation and classification
├── bounded repair loop
├── controls, treatments, and ablations
├── memory and strategy ablation matrix
├── independent assurance review
└── strict certification verdict
```

The governing invariants:

> Every independently governed act of generating, multiplying,
> composing, compiling, evaluating, selecting, persisting, or learning
> intelligence executes as a LoopNode. Seeds, strings, configurations,
> fragments, policies, records, and candidate artifacts are typed
> objects contained by or passed among LoopNodes. The Intelligence
> Foundry and the Capability Proving Campaign are applications of Loop
> Engine, not separate engines.

> Loop Engine is a self-improving work compiler and execution runtime.
> The prompt is an emitted artifact, not the architecture.

## 2. Positioning correction

Loop Engine is not only automation of the prompt-engineer role.

```text
Prompt engineering automation
        ⊂
Context engineering automation
        ⊂
Compound program optimization
        ⊂
Universal work compilation, execution, verification, and learning
```

The thing being learned is not `prompt_text -> score`. It is:

```text
Task and Environment Context
        ↓
Resolved ModelInvocationRecipe
        ↓
Observed Outcome, Cost, Failures, and Evidence
```

The learned policy approximates: given task contract, operator,
response contract, model and provider, available intelligence, tools,
risk, budget, prior episodes, and preferences, select or generate the
prompt assembly, context assembly, examples, retrieval strategy, tool
bindings, model settings, reasoning strategy, verifier, repair route,
and stop condition.

Prompt optimization is one specialized application inside the Foundry,
not the organizing principle of the architecture.

## 3. Terminology corrections

Use these distinctions:

| Term | Meaning |
|---|---|
| Seed Artifact | Starting material from which candidates are generated |
| Seed Source | Where starting material is obtained |
| Generation Operator | A transformation that generates or changes candidates |
| Composition Operator | A transformation that combines candidate components |
| Search Strategy | Determines which candidates are generated and evaluated |
| Evaluation Profile | Defines metrics, test cases, budgets, acceptance |
| Candidate Artifact | A generated but unapproved result |
| Variant Lineage | Exact ancestry and transformations producing a candidate |
| Promotion Policy | Rules governing adoption into Learned or Core |
| Writeback Policy | Where candidate records and artifacts may be written |
| Work Operator | What operation the task requires |
| Execution Binding | Which concrete implementation runs the operator |

Seeds are data; executing a seed transformation is a LoopNode.

## 4. Required implementation layers

### 4.1 Foundry model

Implement typed equivalents of:

```text
SeedArtifact
CandidateFragment
StringFragment
PromptBlock
ConfigPatch
VariationDimension
ConditionalRule
GenerationCampaign
GenerationOperator
CandidateRecord
WritebackPolicy
GenerationBudget
```

Fragment kinds:

```text
StringFragment, PromptBlock, ContextBlock, ExampleSet, ConfigPatch,
QueryFragment, ContractFragment, PolicyFragment, ProcedureFragment,
GraphFragment, ToolBindingFragment, VerificationFragment,
RoutingFragment, ServiceBindingFragment
```

Each fragment must carry: fragment_id, version, artifact_kind,
content, input_contract, output_contract, compatible_targets,
required_fragments, conflicting_fragments, ordering_constraints,
merge_semantics, scope, provenance, evidence, content_hash.

Different artifact kinds need different combination semantics:

```text
Strings        ordered typed assembly
Configurations schema-aware overlay with declared merge rules
Policies       monotonic restriction unless explicitly authorized
Graphs         typed-port and edge compatibility
Examples       selection, ordering, diversity, token budget
Contracts      conjunction, refinement, or explicit alternative
Rankings       score aggregation or Pareto comparison
Procedures     sequence, branch, fallback, or graph composition
```

Do not use `deep_merge_everything(a, b)`.

### 4.2 Generation equation

```text
Candidate Set =
    Compile(
        Constrain(
            Compose(
                Transform(
                    SelectSeeds(Context)
                )
            )
        )
    )
```

The full Cartesian product must never be materialized unless small.
Use applicability filters, conditional rules, lazy generation,
deduplication, budgets, and stop conditions.

### 4.3 Seed sources

```text
Literal, Core Default, Historical Champion, Historical Diverse Set,
Historical Failure, Current Production, User Preference,
Project Preference, Analogy, First Principles, Adjacent Domain,
Opposite Hypothesis, Counterexample, Adversarial, Minimal,
Exhaustive, High Risk, Low Cost, Novelty, Historical Precedent
```

### 4.4 Search strategies

```text
Exact Enumeration, Pairwise, Stratified Sampling, Beam Search,
Successive Halving, Evolutionary, OPRO-style Trajectory Search,
Textual Feedback Optimization, Novelty Search, Adversarial Search,
Ablation Search, Multi-objective Pareto, Model-selected, Adaptive
```

### 4.5 Prompt assembly stays structured until rendering

```text
ModelInvocationRecipe
├── operator_contract
├── response_contract
├── PromptAssemblySpec
├── ContextAssemblySpec
├── MemoryRecallBinding
├── ModelPolicy
├── ToolBindings
├── DecodingConfiguration
├── PermissionConfiguration
├── VerificationConfiguration
├── FallbackConfiguration
├── RepairConfiguration
├── Budget
└── StopConditions
```

Render to strings only at the model boundary through a model-specific
Prompt Compiler. Learn block-level effects: for extraction tasks
examples-before-constraints may win for model A; for high-risk
decisions counterevidence blocks are mandatory.

### 4.6 Campaign model

```text
CapabilityTaskDefinition
CampaignDefinition
CampaignArm
CampaignRunManifest
CampaignResult
CapabilityGap
ImprovementCandidate
```

Task tiers:

```text
A: atomic deterministic (constant, config, contract, hash, gate)
B: composite graphs (fallback, repair, custom Practitioner,
   state machine, sequential/parallel equivalence)
C: data and ML (tabular ensembles, missing values, leakage checks,
   calibration, champion/challenger)
D: software engineering (bug find, patch, tests, assurance, rename,
   adapter behind port, migration forward/rollback)
E: memory and transfer (no-memory vs typed memory, failure episode,
   consolidation, procedural induction, independent promotion,
   negative transfer, blind lane)
F: storage and portability (in-memory, JSONL, DuckDB, SQLite,
   bundle round trip, semantic equivalence, stale replica)
G: concurrency and durability (fan-out, conflicts, fail-fast,
   isolate, first-success, quorum, durable child, no orphan tasks)
H: service generation (serviceization decision, contract, local run,
   typed port invocation, health, rollback, optional container)
I: adversarial (corruption, stale version, cross-tenant, poisoned
   memory, removed guard, interrupted migration, forbidden Node
   subclass fixture)
```

### 4.7 Flagship example

A three-model ensemble:

```text
Root Practitioner
├── Orient, inspect data and contracts, select family and metric
└── compile Solution Canvas
    ├── load or generate data
    ├── validate schema
    ├── split train/test
    ├── shared preprocessing
    ├── linear model  ──┐
    ├── neural model  ──┼── safe parallel children
    ├── tree model  ────┘
    ├── predictions
    ├── ensemble
    ├── metrics
    ├── member comparison
    ├── persist artifacts
    └── typed result
```

Requirements: same immutable split, no leakage, pinned seeds, exact
dependency versions, sequential control, semantic equivalence within
tolerance, per-member and ensemble metrics, failures preserved,
partial-ensemble only when declared, one documented command.

### 4.8 Controls and ablations

```text
Execution: direct reference vs minimal graph vs full treatment
Memory: M0 none through M6 all four plus blind lane
Intelligence: cost-first through exhaustive-before-action
Scheduling: sequential through quorum
Backend: in-memory through PostgreSQL when available
Run mode: deterministic through model-led
```

Matched budgets. No cherry-picking. Report all seeds and failures.
Development, validation, and sealed certification sets stay separate.
An LLM judge needs a typed rubric and an independent path.

### 4.9 Failure taxonomy and repair loop

```text
Reproduce -> Minimize -> Classify -> Hypotheses -> Smallest
architecture-correct repair -> Focused test -> Original scenario ->
Related scenarios -> Negative fixture -> Mutation test ->
Independent assurance -> Integrate or reject
```

Never weaken a test to pass, never hide a failure, never bypass the
canonical runtime, never promote a one-off patch into Core without
evidence.

### 4.10 Memory integration

The Foundry and Campaign use all four memory types:

```text
Working:  current goal, candidate set, best candidates, budget
Episodic: prior generation runs, scores, costs, failures, lineage
Semantic: evidence-backed component effects and interactions
Procedural: how to generate, optimize, select, diagnose, repair
```

Learn components and interactions, not only whole candidates.
Record `ComponentEffectEstimate` and `InteractionEffectEstimate` with
uncertainty, supporting and contradicting runs, and applicability
limits. Keep a history-blind lane.

### 4.11 Writeback and promotion

```text
WritebackPolicy
├── allowed namespaces, database bindings, file roots
├── permitted artifact kinds
├── maximum artifacts and bytes
├── append-only requirement
├── content-addressing requirement
├── provenance requirement
├── dry-run and shadow modes
└── candidate-only by default
```

A generation LoopNode normally receives `may_write_candidates: true`,
`may_write_learned: false`, `may_write_core: false`,
`may_promote: false`.

Promotion requires an independent governed review with exact evidence,
reviewer identity, policy version, and receipt.

## 5. Guardrails

1. No separate generator or campaign runtime.
2. No opaque prompt authority; prompt text grants nothing.
3. No global best-prompt without scope: task contract, model,
   provider, version, evaluation data, as-of time, snapshots, tools,
   budget, metrics, confidence, limitations.
4. No unbounded combinatorial generation: candidate, call, cost,
   time, and iteration ceilings.
5. No self-promotion.
6. No evaluation leakage between development, selection, holdout,
   adversarial, and canary sets.
7. A blind lane always remains available.
8. Exact provenance for every candidate: seeds, operators, versions,
   parameters, parents, generation model and prompt, environment,
   content hash, evaluation runs, write location.

## 6. Required tests

```text
test_generation_runs_through_canonical_loop_runtime
test_no_separate_generation_engine
test_seed_artifact_is_not_a_node
test_generation_operator_is_typed_data
test_candidate_fragment_has_deterministic_digest
test_prompt_block_renders_deterministically
test_config_patch_overlays_with_frozen_fields
test_policy_patch_cannot_broaden_permissions
test_variation_dimensions_expand_deterministically
test_conditional_rules_prune_combinations
test_expansion_respects_candidate_limit
test_campaign_refuses_self_promotion
test_campaign_refuses_unknown_search_strategy
test_candidates_carry_seed_and_operator_lineage
test_duplicate_candidates_are_deduplicated
test_writeback_dry_run_writes_nothing
test_writeback_candidate_only_refuses_learned_write
test_generated_candidate_cannot_promote_itself
test_task_runs_through_canonical_loop
test_failures_are_preserved_not_hidden
test_campaign_report_counts_all_results
test_timeout_is_classified_not_hidden
test_control_and_treatment_budgets_are_matched
test_sequential_and_parallel_results_are_equivalent
test_no_memory_control_remains_available
test_blind_lane_never_consumes_learned_priors
test_negative_transfer_is_detected
test_sealed_certification_set_is_not_used_for_tuning
test_mutation_of_self_approval_guard_is_killed
test_prompt_injection_in_seed_is_treated_as_data
test_generated_config_cannot_enable_prohibited_provider
```

## 7. Documentation deliverables

```text
docs/architecture/INTELLIGENCE_FOUNDRY.md
docs/architecture/CAPABILITY_CAMPAIGN.md
docs/architecture/PROMPT_IS_AN_EMITTED_ARTIFACT.md
docs/guides/GENERATION_CAMPAIGN_GUIDE.md
docs/guides/BENCHMARK_SCIENCE.md
docs/guides/FAILURE_AND_REPAIR_PROTOCOL.md
```

Document the positioning hierarchy, the generation equation, the
fragment model, the search strategies, the campaign tiers, the
ablation matrix, the failure taxonomy, and the promotion governance.

## 8. Final completion standard

The work is complete only when all of the following are true:

- The Intelligence Foundry and Capability Campaign are applications
  on the canonical Loop runtime.
- Seeds, fragments, dimensions, operators, and candidates are typed
  data, never Nodes.
- Prompt assembly stays structured until the model boundary.
- Expansion is bounded and conditionally pruned.
- Generation never self-promotes.
- The campaign runs real tasks, preserves failures, and reports
  honestly.
- Controls, treatments, and ablations are matched.
- All four memory types participate in generation and learning.
- A history-blind lane always remains.
- Independent assurance reviews every repair and promotion.
- A clean installation runs the flagship ensemble through one
  documented command.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step.
