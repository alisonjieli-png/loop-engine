# Loop Engine plane-interaction architecture mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test, security,
and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement, migrate,
test, verify, document, and predeploy-gate the plane-interaction
architecture described here. Do not stop at a design memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package configuration;
- create a complete inventory of current model, effect, execution,
  verification, persistence, observability, and intelligence configuration;
- rename, move, split, merge, rewrite, or delete obsolete modules and folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL records,
  database migrations, and persisted references;
- replace scattered per-plane configuration with one shared engine;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Core JSONL records and neutral shards;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a stronger
  replacement;
- make reasonable architectural decisions without repeatedly asking for
  confirmation.

Do not merely add a new layer beside the old architecture. Do not leave two
competing configuration systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational, migrated,
tested, packaged, documented, and the obsolete behavior is absent or
explicitly quarantined behind a time-bounded compatibility shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Intelligence is one plane a LoopNode interacts with. It is not the only
one.

Implement one universal, composable, inheritable, versioned,
policy-constrained plane-interaction configuration system that governs
every operational plane a LoopNode touches:

```text
Core planes
├── Intelligence plane
│   └── search, retrieve, select, materialize, frame
├── Model plane
│   └── provider selection, model routing, thinking power,
│       maximum output, retry, failover, token accounting
├── Effect plane
│   └── filesystem, network, shell, MCP tools, workspaces,
│       sandboxes, approvals, external services
├── Execution plane
│   └── code execution, solution execution, delegation,
│       spawned Loops, scheduling
├── Verification plane
│   └── validators, evaluators, graders, acceptance checks
├── Persistence plane
│   └── stores, artifacts, checkpoints, run history, exports
└── Observability plane
    └── Chronicle, telemetry, reports, playback, traces
```

Each plane uses the same five-way split:

```text
PlaneAccessPolicy
└── hard permissions and restrictions

PlaneStrategy
└── declarative control-flow behavior

PlaneProfile
└── reusable soft preferences

PlaneBinding
└── universal attachment to any Loop, step, child, or invocation

ResolvedPlanePlan + PlaneReceipt
└── pinned runtime configuration and complete audit
```

One shared configuration engine serves all planes:

```text
Shared engine
├── InheritanceResolver
├── MergeEngine
├── CompatibilityHandshake
├── AdaptationEngine
├── BudgetAllocator
└── ReceiptWriter
```

The intelligence-seeking architecture already designed for the
Intelligence plane becomes instance one of this general model. The Model
plane becomes instance two, because its configuration is the most
developed in the current codebase. The remaining planes follow the same
pattern.

The implementation must make this statement true:

> A LoopNode interacts with several planes. Each plane has its own hard
> policy, declarative strategy, soft profile, and pinned resolved plan.
> One shared engine resolves, merges, negotiates, and audits them all.

## 2. Architectural baseline

### 2.1 One operational node

Preserve the hard Loop Engine invariant:

```text
Node
└── LoopNode
```

Node is an architectural category and namespace. LoopNode is the only
concrete operational node.

Never introduce a concrete generic Node, role-specific node classes,
mode-specific node classes, plane-specific node classes, plugin-defined
node kinds, or a second node executor.

Practitioner, Intelligence, and Solution are roles of the same LoopNode.
Root and Child are positions of the same LoopNode. Deterministic, hybrid,
and non-deterministic are run modes of the same LoopNode.

### 2.2 Governed work boundary

Every independently governed unit of work above the kernel executes as a
LoopNode. Create a separate LoopNode when work needs an independent goal,
contract, budget, stop condition, permissions, verification, retry,
Chronicle identity, scheduling, delegation, cancellation, or governance.

Ordinary adapter methods, SQL execution calls, hash calculations,
serialization helpers, schema validators, and provider SDK calls may
remain implementation primitives inside a governed LoopNode.

### 2.3 Planes are not runtimes

A plane is a configuration and interaction surface. It is not:

- a runtime type;
- a node class;
- a role;
- a folder kingdom;
- a service layer with its own executor.

A plane strategy is a declarative definition. When it executes, it
executes through ordinary LoopNodes. The Kernel enforces hard policies,
budgets, and stop conditions. Planes are above the Kernel.

### 2.4 Governance is the meta-authority, not a plane

Governance clamps every plane. It is not an eighth plane.

```text
Governance
├── clamps every plane's access policy
├── approves candidates and promotions
├── revokes and rolls back
├── records decisions
└── never executes plane work itself
```

Effect approvals are a governance interaction, but the approval
requirement lives in the Effect plane's access policy. The approval
service is the enforcement mechanism, not a separate plane.

## 3. Required canonical concepts

Implement and strictly distinguish these objects.

### 3.1 PlaneAccessPolicy

Hard constraints on what a LoopNode may do on one plane.

Examples per plane:

```text
Intelligence plane
├── allowed and denied catalog namespaces
├── allowed and denied plugins
├── sensitivity ceilings
├── minimum governance status
└── tenant and scope boundaries

Model plane
├── allowed providers and models
├── denied providers and models
├── maximum thinking power
├── maximum output tokens
├── failover permission
└── spending ceilings

Effect plane
├── allowed effect classes
├── denied effect classes
├── workspace confinement rules
├── sandbox requirements
├── approval requirements
└── network policy

Execution plane
├── allowed execution backends
├── denied execution backends
├── delegation depth ceilings
├── spawned-Loop ceilings
└── timeout ceilings

Verification plane
├── required validators
├── required evaluators
├── minimum acceptance thresholds
└── independent-review requirements

Persistence plane
├── allowed stores
├── denied stores
├── retention rules
├── export restrictions
└── content-addressing requirements

Observability plane
├── required event classes
├── redaction requirements
├── export restrictions
└── retention rules
```

Preference must never grant permission. A plane strategy may not broaden
a plane policy.

### 3.2 PlaneStrategy

A declarative control-flow graph over registered operators, describing
how a LoopNode approaches one plane.

The Intelligence plane already has its operator vocabulary:

```text
Query, Filter, Expand, Traverse Relationships, Generate Subqueries,
Sequence, Parallel, Branch, Repeat Until, Fallback, Compare, Challenge,
Diversify, Rerank, Verify Sources, Synthesize, Select, Stop
```

The Model plane needs its own vocabulary:

```text
Model Operators
├── Select Provider
├── Select Model
├── Resolve Capabilities
├── Request Maximum Output
├── Invoke
├── Retry
├── Same-Provider Fallback
├── Cross-Provider Failover
├── Format Repair
├── Evaluator-Triggered Repair
├── Replan
├── Account Tokens
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

The Effect plane needs:

```text
Effect Operators
├── Discover Capability
├── Validate Arguments
├── Request Approval
├── Consume Approval
├── Confine Workspace
├── Select Backend
├── Invoke
├── Capture Output
├── Verify Idempotency
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

The Execution plane needs:

```text
Execution Operators
├── Resolve Implementation
├── Check Compatibility
├── Select Backend
├── Execute
├── Delegate
├── Spawn Child
├── Join
├── Cancel
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

The Verification plane needs:

```text
Verification Operators
├── Validate Schema
├── Validate Contract
├── Evaluate Quality
├── Compare Candidates
├── Grade
├── Independent Review
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

The Persistence plane needs:

```text
Persistence Operators
├── Select Store
├── Check Authority
├── Write
├── Compare and Swap
├── Export
├── Import
├── Synchronize
├── Verify Hash
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

The Observability plane needs:

```text
Observability Operators
├── Emit Event
├── Redact
├── Export Trace
├── Generate Report
├── Sequence
├── Parallel
├── Branch
├── Fallback
└── Stop
```

Each operator vocabulary is registered and versioned. A strategy graph is
a definition, not another operational object. When it executes, it
executes through ordinary LoopNodes.

### 3.3 PlaneProfile

A reusable, versioned description of soft preferences for one plane.

Examples:

```text
Model plane profile
├── preferred providers
├── preferred models
├── preferred thinking power
├── cost versus quality tradeoff
├── latency preference
├── retry preference
└── failover preference

Effect plane profile
├── preferred backends
├── preferred workspace kind
├── inline versus offloaded output preference
└── approval batching preference

Verification plane profile
├── preferred validators
├── preferred evaluators
├── strictness preference
└── evidence requirements
```

A profile is not an access policy, not a strategy, and not a runtime
result.

### 3.4 PlaneBinding

The universal configuration object that attaches access policies, one or
more profiles, and a strategy for one plane to an architectural subject.

The same binding schema must apply to:

- LoopDefinition;
- PractitionerDefinition;
- LoopGraphSpec;
- SolutionCanvas;
- StepDefinition;
- Child Loop spawn requests;
- LoopInvocation;
- organization, workspace, project, user, and deployment configuration.

A LoopDefinition carries one binding per plane:

```text
LoopDefinition
├── goal
├── role
├── profile
├── run mode
├── contracts
├── budget
├── stop condition
│
├── intelligence_binding
├── model_binding
├── effect_binding
├── execution_binding
├── verification_binding
├── persistence_binding
└── observability_binding
```

Do not create separate binding models for each step type or Loop role.

### 3.5 ResolvedPlanePlan

The exact runtime configuration for one plane after resolving version
ranges, pinning exact record versions and content hashes, resolving
inheritance, detecting cycles and conflicts, applying deterministic merge
rules, performing compatibility handshakes, applying invocation
overrides, applying the final governance clamp, calculating effective
budgets, and recording any degradation or rejected override.

The resolved plan is immutable for the invocation unless a bounded
adaptation produces a new versioned plan with a receipt.

### 3.6 PlaneReceipt

A structured account of what occurred on one plane.

It should include requester LoopNode ID and definition reference,
requesting step or graph position, resolved plan reference, bound policy,
strategy, and profiles with versions and hashes, strategy-selection
reason, adapters and stores used, handshakes, decisions, selected and
rejected items with reasons, budget consumption, latency, errors and
partial failures, redactions, runtime adaptations, and final status.

Do not log sensitive payloads when references or hashes are sufficient.

## 4. One shared engine, not seven copies

The inheritance, merge, compatibility, adaptation, budget, and receipt
machinery must be implemented once and parameterized by plane.

### 4.1 Shared inheritance

One InheritanceResolver serves all planes.

```text
Constitutional constraints
Deployment policy
Organization policy
Workspace policy
Project policy
User policy
Core Loop-role default
Practitioner-family default
Practitioner definition
LoopGraphSpec or SolutionCanvas
Step-trait defaults
Step definition
Parent LoopNode
Child-spawn request
Invocation override
Bounded runtime adaptation
Final governance clamp
```

Inheritance modes: none, constraints_only, defaults_only,
preferences_only, constraints_and_defaults, full, selected_fields.

Recommended default for child LoopNodes: constraints_and_defaults.

A Child LoopNode may specialize plane preferences but may not broaden
inherited hard access restrictions without an explicit delegated grant
authorized by policy.

### 4.2 Shared merge

One MergeEngine serves all planes. Every configurable field declares a
merge operator. Hard denials union. Allowed scopes intersect. Required
items union. Soft weights use weighted overlay then normalization.
Penalties are additive. Minimum evidence quality and minimum governance
status use the most restrictive value. Hard budgets use the minimum
ceiling. Frozen fields union. Adaptable fields intersect with non-frozen
fields.

Do not use a generic deep-merge library as the architecture.

### 4.3 Shared compatibility

One CompatibilityHandshake serves all planes. Verdicts: compatible,
compatible_with_migration, compatible_with_degradation,
compatible_read_only, compatible_export_only, incompatible, unknown,
refused_by_policy.

Every adapter, provider, backend, store, and plugin declares its real
capabilities before use. Unknown compatibility fails closed.

### 4.4 Shared adaptation

One AdaptationEngine serves all planes. A Practitioner may adapt a
resolved plane plan only within declared bounds. Adaptable fields are
soft preferences and bounded behavior. Frozen fields are access policy,
scope boundaries, sensitivity ceilings, consent requirements, minimum
governance status, hard budget ceilings, effect permissions, denied
plugins, retention rules, and required independent review.

A runtime adaptation must identify a typed trigger, propose a diff,
validate the diff against adaptable fields, apply hard ceilings, explain
the reason, create a new immutable resolved-plan version, emit a
Chronicle event, update the receipt, and preserve the original plan. An
LLM must not mutate the plan object directly.

### 4.5 Shared budgets

One BudgetAllocator serves all planes.

```text
LoopNode budget
├── total work ceiling
├── total call ceiling
├── total wall-time ceiling
│
├── Intelligence plane budget
│   ├── query ceiling
│   └── materialization ceiling
├── Model plane budget
│   ├── call ceiling
│   ├── input-token ceiling
│   ├── output-token ceiling
│   └── spending ceiling
├── Effect plane budget
│   ├── effect ceiling
│   └── approval ceiling
├── Execution plane budget
│   ├── execution ceiling
│   └── spawned-Loop ceiling
├── Verification plane budget
│   └── evaluation ceiling
├── Persistence plane budget
│   └── write ceiling
└── Observability plane budget
    └── event ceiling
```

A plane may not spend another plane's budget. A child may not exceed the
parent's delegated ceiling. Budget accounting is shared and monotonic.

## 5. Cross-plane rules

### 5.1 Cross-plane references go through resolved plans

A plane strategy may reference another plane's results. A verification
strategy may query intelligence. An execution strategy may request
effects. A model strategy may persist results.

Every cross-plane reference goes through the other plane's resolved plan.
It never bypasses the other plane's access policy, budget, or receipt.

### 5.2 No policy bypass through another plane

A plane strategy may not use another plane to do what its own policy
forbids. A model strategy may not use the effect plane to write a file
the effect policy denies. An intelligence strategy may not use the
persistence plane to export records the intelligence policy forbids.

### 5.3 No circular plane resolution

Plane resolution must terminate. A verification strategy that requires
intelligence, an intelligence strategy that requires verification, and a
verification strategy that requires intelligence again must be detected
and refused or bounded with an explicit iteration limit.

### 5.4 Plane defaults

Every plane has a Core default strategy, profile, and access policy. A
LoopDefinition that binds nothing inherits the defaults. A plane with a
zero budget refuses work with a typed error, not a silent no-op.

### 5.5 Plugin planes

Plugins may contribute namespaced strategies, profiles, and operator
terms for existing planes. Plugins may not define new core planes. A
plugin plane extension must declare compatibility and pass the same
handshakes.

## 6. Migration of current scattered configuration

The current codebase already contains pieces of every plane. Migrate
them into the shared model.

### 6.1 Model plane

Current pieces:

```text
LoopConfig.power
LoopConfig.llm_thinking_power
LoopConfig.allowable_modes
LoopConfig.preferred_modes
provider_failover
model_routes
model_capabilities
model_gateway
reasoning_call
live_model_verification
```

Target:

```text
Model plane access policy
├── allowed providers and models
├── denied providers and models
├── maximum thinking power
├── maximum output tokens
├── failover permission
└── spending ceilings

Model plane strategy
├── provider selection
├── model selection
├── capability resolution
├── maximum-output request
├── retry
├── same-provider fallback
├── cross-provider failover
├── format repair
├── evaluator-triggered repair
└── replanning

Model plane profile
├── preferred providers and models
├── preferred thinking power
├── cost versus quality tradeoff
└── latency preference
```

Preserve the existing hard rules: request the exact provider-supported
maximum output; never silently replace a failed call with canned output;
preserve provider-reported token usage; keep retry, same-provider
fallback, cross-provider failover, formatting repair,
evaluator-triggered repair, and replanning distinct; do not enable
failover unless the run contract permits it.

### 6.2 Effect plane

Current pieces:

```text
LoopDefinition.effects
LoopDefinition.permissions
effect_approval
workspace_contracts
workspace_operations
workspace_backends
mcp_adapter
mcp_sdk_transport
skill_registry
```

Target:

```text
Effect plane access policy
├── allowed effect classes
├── denied effect classes
├── workspace confinement rules
├── sandbox requirements
├── approval requirements
└── network policy

Effect plane strategy
├── capability discovery
├── argument validation
├── approval request and consumption
├── workspace confinement
├── backend selection
├── invocation
├── output capture
└── idempotency verification

Effect plane profile
├── preferred backends
├── preferred workspace kind
├── inline versus offloaded output preference
└── approval batching preference
```

Preserve the existing hard rules: discovery must be effect-free; bind an
approval to one exact effect, arguments digest, target, operation, and
request identity; consume one-use approval authority before crossing the
effect boundary; do not retry a failed effect automatically; confine
workspace paths and refuse traversal, symlink escape, and unsafe
overwrite.

### 6.3 Execution plane

Current pieces:

```text
recursive_loop execution regimes
delegation_runtime
spawned_practitioner
spawned_workspace_executor
solution_canvas execution
capability_loops
```

Target:

```text
Execution plane access policy
├── allowed execution backends
├── denied execution backends
├── delegation depth ceilings
├── spawned-Loop ceilings
└── timeout ceilings

Execution plane strategy
├── implementation resolution
├── compatibility checking
├── backend selection
├── execution
├── delegation
├── child spawning
├── joining
└── cancellation

Execution plane profile
├── preferred backends
├── inline versus delegated preference
└── parallelism preference
```

Preserve the existing hard rules: a Spawned Loop receives only its typed
inputs and explicitly selected references; do not expose the spawning
Loop object, goal, private history, sibling context, or shared ledger to
a Spawned Loop executor; async lifecycle must include start, status,
typed update, cancel, wait, terminal result, deadline handling, and no
orphaned task.

### 6.4 Verification plane

Current pieces:

```text
solution validators
benchmark evaluators
run_quality
acceptance checks
```

Target:

```text
Verification plane access policy
├── required validators
├── required evaluators
├── minimum acceptance thresholds
└── independent-review requirements

Verification plane strategy
├── schema validation
├── contract validation
├── quality evaluation
├── candidate comparison
├── grading
└── independent review

Verification plane profile
├── preferred validators and evaluators
├── strictness preference
└── evidence requirements
```

### 6.5 Persistence plane

Current pieces:

```text
persistence
store_serve
duckdb_catalog
context_artifacts
run_history stores
catalog stores
```

Target:

```text
Persistence plane access policy
├── allowed stores
├── denied stores
├── retention rules
├── export restrictions
└── content-addressing requirements

Persistence plane strategy
├── store selection
├── authority checking
├── writing
├── compare and swap
├── export and import
├── synchronization
└── hash verification

Persistence plane profile
├── preferred stores
├── inline versus offloaded preference
└── replication preference
```

Preserve the existing hard rules: one authority per record version; never
dual-write files and databases without an explicit recovery protocol;
derived indexes are disposable and rebuildable; content hashes verify
before serving.

### 6.6 Observability plane

Current pieces:

```text
run_history
event_vocabulary
otel_export
loop_report
run_analytics
run_playback
studio views
```

Target:

```text
Observability plane access policy
├── required event classes
├── redaction requirements
├── export restrictions
└── retention rules

Observability plane strategy
├── event emission
├── redaction
├── trace export
├── report generation
└── playback projection

Observability plane profile
├── preferred report formats
├── verbosity preference
└── export preference
```

Preserve the existing hard rules: Run History is the canonical
append-only event history; use one canonical event vocabulary and one
OpenTelemetry projection; do not export raw prompts, secrets, tool
bodies, intelligence bodies, or private spawned context.

### 6.7 Intelligence plane

The intelligence-seeking architecture already designed becomes instance
one of this model. Migrate it onto the shared engine. Its access policy,
seeking strategy, query profile, binding, resolved plan, portfolio
snapshot, and receipt keep their names and semantics.

## 7. Required implementation architecture

Inspect the current repository and adapt paths as needed, but target a
compact architecture like this:

```text
src/loop_engine/
├── node/
│   └── loop_node/
│       ├── model.py
│       ├── dimensions.py
│       ├── invocation.py
│       ├── result.py
│       └── references.py
│
├── planes/
│   ├── README.md
│   ├── plane.py
│   ├── access_policy.py
│   ├── strategy.py
│   ├── profile.py
│   ├── binding.py
│   ├── resolved_plan.py
│   ├── receipt.py
│   │
│   ├── engine/
│   │   ├── inheritance_resolver.py
│   │   ├── merge_engine.py
│   │   ├── compatibility_handshake.py
│   │   ├── adaptation_engine.py
│   │   ├── budget_allocator.py
│   │   └── receipt_writer.py
│   │
│   ├── intelligence/
│   │   ├── access_policy.py
│   │   ├── seeking_strategy.py
│   │   ├── query_profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   ├── portfolio_snapshot.py
│   │   └── receipt.py
│   │
│   ├── model/
│   │   ├── access_policy.py
│   │   ├── invocation_strategy.py
│   │   ├── profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   └── receipt.py
│   │
│   ├── effect/
│   │   ├── access_policy.py
│   │   ├── effect_strategy.py
│   │   ├── profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   └── receipt.py
│   │
│   ├── execution/
│   │   ├── access_policy.py
│   │   ├── execution_strategy.py
│   │   ├── profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   └── receipt.py
│   │
│   ├── verification/
│   │   ├── access_policy.py
│   │   ├── verification_strategy.py
│   │   ├── profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   └── receipt.py
│   │
│   ├── persistence/
│   │   ├── access_policy.py
│   │   ├── persistence_strategy.py
│   │   ├── profile.py
│   │   ├── binding.py
│   │   ├── resolved_plan.py
│   │   └── receipt.py
│   │
│   └── observability/
│       ├── access_policy.py
│       ├── observability_strategy.py
│       ├── profile.py
│       ├── binding.py
│       ├── resolved_plan.py
│       └── receipt.py
│
├── ontology/
├── intelligence/
├── catalog/
├── governance/
├── compatibility/
├── runtime/
├── kernel/
├── plugin_host/
└── interfaces/
```

Do not create physical folders for individual strategies, profiles, or
default step names. Core records ship in package data. Learned data lives
in instance stores. Plugin data lives in plugin packages, bundles,
stores, or services.

## 8. Core defaults

Ship Core records for every plane:

```text
Core access policies
├── core.plane_policy.intelligence.default@1
├── core.plane_policy.model.default@1
├── core.plane_policy.effect.default@1
├── core.plane_policy.execution.default@1
├── core.plane_policy.verification.default@1
├── core.plane_policy.persistence.default@1
└── core.plane_policy.observability.default@1

Core strategies
├── core.plane_strategy.intelligence.balanced@1
├── core.plane_strategy.intelligence.adversarial@1
├── core.plane_strategy.intelligence.cost_first@1
├── core.plane_strategy.model.standard@1
├── core.plane_strategy.model.no_failover@1
├── core.plane_strategy.model.cheapest_first@1
├── core.plane_strategy.effect.approval_required@1
├── core.plane_strategy.effect.local_workspace@1
├── core.plane_strategy.execution.inline@1
├── core.plane_strategy.execution.delegated@1
├── core.plane_strategy.verification.standard@1
├── core.plane_strategy.verification.strict@1
├── core.plane_strategy.persistence.local@1
├── core.plane_strategy.persistence.replicated@1
├── core.plane_strategy.observability.standard@1
└── core.plane_strategy.observability.minimal@1

Core profiles
├── core.plane_profile.model.quality_first@1
├── core.plane_profile.model.cost_first@1
├── core.plane_profile.effect.offload_output@1
├── core.plane_profile.verification.high_assurance@1
└── ...
```

The default Practitioner binds the defaults. Custom Practitioners may
bind any plane configuration.

## 9. Adversarial corner cases

The implementation must support and test all of these.

### 9.1 Cross-plane policy bypass

A model strategy attempts to use the effect plane to write a file the
effect policy denies. The effect plane refuses. The model plane receipt
records the refusal.

### 9.2 Budget double-spending

A verification strategy queries intelligence and a model strategy also
queries intelligence. Both consume the shared Intelligence plane budget.
The BudgetAllocator refuses the second query when the ceiling is
reached.

### 9.3 Circular plane resolution

A verification strategy requires intelligence. The intelligence strategy
requires verification. The resolver detects the cycle and refuses or
bounds it with an explicit iteration limit.

### 9.4 LLM-authored multi-plane strategy

An LLM Practitioner proposes strategies for several planes at once. Each
draft passes schema validation, operator validation, access-policy check,
budget check, cycle and termination check, adapter compatibility
handshake, and governance clamp. The LLM may not edit hard policy.

### 9.5 Plane-specific emergency revocation

A model provider is revoked mid-run. The running LoopNode keeps its
resolved plan unless emergency policy requires termination. A new
invocation resolves the new policy.

### 9.6 Historical replay across planes

Replaying a run must use the exact plane plan versions, hashes, and store
snapshots resolved at the original time. New defaults must not leak into
replay.

### 9.7 Plugin plane extension

A plugin contributes a namespaced model strategy. It cannot shadow Core
strategies, broaden access, or self-approve Learned output.

### 9.8 Zero-budget plane

A LoopDefinition binds a zero-budget verification plane. Verification
work refuses with a typed error, not a silent no-op.

### 9.9 Plane with no binding

A LoopDefinition binds nothing for the persistence plane. The Core
default persistence policy, strategy, and profile apply.

### 9.10 Cross-plane deadlock

Two concurrent child Loops each hold a plane budget the other needs. The
BudgetAllocator detects the deadlock or the stop conditions terminate
the run. No orphaned tasks remain.

## 10. Required test suite

### 10.1 Architecture tests

```text
test_loop_node_is_only_operational_node
test_no_plane_specific_node_classes
test_planes_are_not_runtimes
test_governance_is_not_a_plane
test_one_shared_engine_serves_all_planes
test_no_plane_specific_inheritance_engine
test_no_plane_specific_merge_engine
test_no_plane_specific_compatibility_engine
test_no_plane_specific_adaptation_engine
test_no_plane_specific_budget_engine
test_semantic_folders_have_readmes
test_architecture_manifest_matches_tree
```

### 10.2 Shared engine tests

```text
test_same_binding_schema_applies_to_every_plane
test_same_inheritance_modes_apply_to_every_plane
test_same_merge_operators_apply_to_every_plane
test_same_handshake_verdicts_apply_to_every_plane
test_same_adaptation_bounds_apply_to_every_plane
test_cycle_detection_works_for_every_plane
test_diamond_inheritance_applies_ancestor_once
test_merge_receipt_explains_every_effective_field
test_resolved_plan_pins_exact_versions_for_every_plane
test_running_plan_remains_pinned_after_policy_update
```

### 10.3 Model plane tests

```text
test_model_policy_denies_provider
test_model_strategy_selects_cheapest_first
test_model_strategy_retries_then_falls_back
test_failover_requires_run_contract_permission
test_maximum_output_is_requested_exactly
test_failed_call_is_never_replaced_with_canned_output
test_provider_token_usage_is_preserved
test_missing_usage_remains_unknown_not_zero
test_model_budget_ceiling_is_enforced
test_model_adaptation_cannot_raise_thinking_power_ceiling
```

### 10.4 Effect plane tests

```text
test_effect_policy_denies_network
test_effect_strategy_requests_approval_before_crossing
test_approval_binds_exact_effect_and_arguments_digest
test_approval_is_consumed_once
test_failed_effect_is_not_retried_automatically
test_workspace_refuses_traversal_and_symlink_escape
test_effect_strategy_cannot_bypass_effect_policy
test_effect_budget_ceiling_is_enforced
```

### 10.5 Execution plane tests

```text
test_execution_policy_denies_backend
test_execution_strategy_delegates_within_depth_ceiling
test_spawned_loop_receives_only_typed_inputs
test_spawned_loop_cannot_see_parent_private_history
test_async_lifecycle_has_no_orphaned_tasks
test_execution_budget_ceiling_is_enforced
test_execution_adaptation_cannot_raise_depth_ceiling
```

### 10.6 Verification plane tests

```text
test_verification_policy_requires_independent_review
test_verification_strategy_runs_validators_then_evaluators
test_verification_budget_ceiling_is_enforced
test_verification_adaptation_cannot_drop_required_validator
test_verification_strategy_can_query_intelligence_through_its_plan
```

### 10.7 Persistence plane tests

```text
test_persistence_policy_denies_store
test_persistence_strategy_checks_authority_before_write
test_no_dual_write_without_recovery_protocol
test_derived_index_is_never_authoritative
test_content_hash_verifies_before_serving
test_persistence_budget_ceiling_is_enforced
test_persistence_adaptation_cannot_change_authority
```

### 10.8 Observability plane tests

```text
test_observability_policy_requires_event_classes
test_observability_strategy_redacts_secrets
test_no_raw_prompts_or_tool_bodies_in_exports
test_one_canonical_event_vocabulary
test_observability_budget_ceiling_is_enforced
test_observability_adaptation_cannot_drop_required_events
```

### 10.9 Cross-plane tests

```text
test_cross_plane_reference_goes_through_resolved_plan
test_plane_strategy_cannot_bypass_another_plane_policy
test_circular_plane_resolution_is_detected
test_shared_budget_is_monotonic_across_planes
test_plane_cannot_spend_another_planes_budget
test_llm_authored_multi_plane_strategy_is_validated
test_plugin_plane_extension_cannot_shadow_core
test_zero_budget_plane_refuses_with_typed_error
test_unbound_plane_uses_core_defaults
test_historical_replay_uses_original_plane_versions
```

### 10.10 Migration tests

```text
test_loop_config_power_migrates_to_model_profile
test_provider_failover_migrates_to_model_strategy
test_effect_approval_migrates_to_effect_policy_and_strategy
test_workspace_operations_migrate_to_effect_plane
test_run_history_migrates_to_observability_plane
test_old_configuration_remains_readable
test_migration_is_resumable_and_idempotent
test_migration_round_trip_preserves_identity
```

### 10.11 End-to-end scenarios

Automate at least:

- Scenario A: default Practitioner runs all seven planes with Core
  defaults.
- Scenario B: custom Practitioner binds an adversarial intelligence
  strategy, a no-failover model strategy, and a strict verification
  strategy.
- Scenario C: regulated Practitioner requires approval for every effect
  and independent review for every verification.
- Scenario D: offline Practitioner uses local stores, no network, and
  minimal observability.
- Scenario E: concurrent children share the model budget and receive
  private plane plans.
- Scenario F: mid-run provider revocation leaves the running plan pinned
  and the next invocation resolved against the new policy.
- Scenario G: historical replay reproduces the original plane plans.
- Scenario H: LLM-authored multi-plane strategy passes validation and
  executes through ordinary LoopNodes.

## 11. Development workflow

Execute in this order.

- Phase 0: inventory. Read repository instructions, inspect current
  configuration surfaces, inventory paths and symbols, identify
  production call paths, identify persistence and serialized references,
  identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: shared engine. Implement the plane model, access policy,
  strategy, profile, binding, resolved plan, receipt, inheritance
  resolver, merge engine, compatibility handshake, adaptation engine,
  budget allocator, and receipt writer. Add contract tests.
- Phase 3: intelligence plane. Migrate the intelligence-seeking
  architecture onto the shared engine.
- Phase 4: model plane. Migrate LoopConfig power, thinking power,
  provider failover, model routes, and model capabilities onto the shared
  engine.
- Phase 5: effect plane. Migrate effect approval, workspace operations,
  MCP, and skills onto the shared engine.
- Phase 6: execution plane. Migrate delegation, spawned Loops, and
  solution execution onto the shared engine.
- Phase 7: verification plane. Migrate validators, evaluators, and
  acceptance checks onto the shared engine.
- Phase 8: persistence plane. Migrate stores, artifacts, and run history
  persistence onto the shared engine.
- Phase 9: observability plane. Migrate Run History, event vocabulary,
  OpenTelemetry export, reports, and playback onto the shared engine.
- Phase 10: Core defaults. Ship Core policies, strategies, and profiles
  for every plane.
- Phase 11: red team. Run security tests, fuzz tests, failure injection,
  concurrency tests, multi-tenant tests, mutation tests.
- Phase 12: packaging and clean install. Build wheel and source
  distribution, inspect package data, verify Core JSONL and schemas
  ship, install in a clean environment, run default and custom scenarios.
- Phase 13: predeploy. Run one strict command, such as
  `python -m loop_engine.predeploy --strict`. Return one verdict: PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 12. Prohibited shortcuts

Do not:

- create plane-specific node classes or runtimes;
- create seven parallel configuration engines;
- merge access policy and preferences;
- use one generic config dictionary;
- use one ambiguous version, status, or source;
- trust filesystem order or plugin discovery order;
- silently broaden a plane policy;
- silently drop conflicts;
- silently ignore unavailable sources;
- let an LLM edit hard policy;
- let a Child Loop broaden parent scope;
- let self-review approve itself;
- make both files and a database independent writable authorities;
- make a derived index authoritative;
- preserve the old architecture indefinitely beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths still
  use legacy code.

## 13. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented schemas and models;
- Core JSONL records and manifests;
- shared engine implementation;
- per-plane implementations;
- compatibility matrix;
- migration scripts;
- architecture tests;
- property-based and fuzz tests;
- security and failure-injection results;
- end-to-end scenario results;
- performance measurements;
- package and clean-install verification;
- strict predeploy report;
- list of deleted obsolete paths;
- list of remaining compatibility shims with removal conditions;
- unresolved risks, if any;
- exact commands required to reproduce every verification.

Do not hide failures. Do not say "implemented" when a path is only
scaffolded. Do not say "compatible" without a handshake and test. Do not
say "portable" without a round trip. Do not say "secure" without
adversarial tests. Do not say "reproducible" without exact version, hash,
and snapshot pinning.

## 14. Final completion standard

The work is complete only when all of the following are true:

- Every plane uses the same five-way split: access policy, strategy,
  profile, binding, resolved plan, and receipt.
- One shared engine resolves, merges, negotiates, adapts, budgets, and
  receipts every plane.
- The intelligence-seeking architecture is instance one of the model.
- The model plane is instance two, migrated from the scattered current
  configuration.
- The effect, execution, verification, persistence, and observability
  planes are migrated onto the shared engine.
- Governance clamps every plane and is not a plane itself.
- Cross-plane references go through resolved plans and never bypass
  policy or budget.
- Access policies remain hard and monotonic.
- Preferences remain soft and composable.
- Strategies are declarative, versioned, and executable only through
  ordinary LoopNodes.
- Inheritance is deterministic, cycle-safe, conflict-aware, and
  receipted.
- Runtime adaptation is bounded, versioned, and observable.
- Resolved plans pin exact versions, hashes, and store snapshots.
- Security, privacy, tenant isolation, and prompt-injection boundaries
  pass.
- Migrations preserve identity, evidence, provenance, and history.
- The obsolete scattered configuration is absent from active production
  paths.
- A clean installation passes the default and custom scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step. Do not paper over the failure with documentation.
