# Loop Engine LoopNode specification and configuration mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test, security,
and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement, migrate,
test, verify, document, and predeploy-gate the LoopNode specification and
configuration architecture described here. Do not stop at a design memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package configuration;
- create a complete inventory of current Loop, LoopDefinition, LoopConfig,
  step, procedure, mode, budget, and configuration concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL records,
  database migrations, and persisted references;
- replace scattered configuration with the universal LoopNodeSpec model;
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

Implement the universal LoopNode specification and configuration model:

```text
LoopNodeDefinitionRecord
        ↓ invoked through
LoopNodeInvocation
        ↓ resolved into
ResolvedLoopNodePlan
        ↓ instantiated as
LoopNode
        ↓ produces
LoopNodeResult + Chronicle Events
```

Every LoopNode carries the same typed configuration envelope, composed
from smaller typed objects rather than one giant settings dictionary.

The implementation must make these statements true:

- Every governed unit of work is a LoopNode.
- Every LoopNode is created from a versioned LoopNodeDefinition.
- Every composite LoopNode describes children through LoopStepBindings.
- Every child LoopNode may have its own role, profile, run mode,
  intelligence-seeking strategy, contracts, budget, permissions,
  verification, repair, and stop conditions.
- Core supplies defaults, not special runtime behavior.
- The resolved runtime plan records exactly what was inherited,
  overridden, selected, permitted, and executed.

## 2. Terminology corrections

Two corrections apply before implementation.

### 2.1 Do not call these "Core settings"

Core already means package-shipped, immutable catalog content. Call the
universal configuration envelope base settings, universal settings, or
preferably LoopNodeSpec.

### 2.2 Steps are bindings, not embedded objects

A parent definition contains references and bindings to child LoopNode
definitions, not embedded live child objects. The children become actual
LoopNode instances only at runtime.

## 3. Corrected object model: LoopNode is the composition root

The typed objects are objects inside LoopNode. They are not disconnected
top-level operational systems loosely associated with it.

```text
LoopNode
│
├── Definition
│   │   Immutable meaning and intended behavior
│   │
│   ├── Purpose
│   ├── Contracts
│   ├── Procedure
│   ├── Execution
│   ├── Intelligence Seeking
│   ├── Control
│   ├── Verification
│   ├── Routing
│   ├── Permissions
│   ├── Inheritance
│   ├── Compatibility
│   └── Observability Requirements
│
├── Invocation
│   │   Inputs and allowed run-specific changes
│   │
│   ├── Input Values
│   ├── Goal Bindings
│   ├── Context Bindings
│   ├── Parent Delegation
│   ├── Allowed Overrides
│   └── Invocation Metadata
│
└── Runtime
    │   Mutable state for this execution
    │
    ├── Identity
    ├── Topology
    ├── Resolved Configuration
    ├── Runtime State
    ├── Runtime Memory
    ├── Child LoopNode Handles
    ├── Chronicle
    └── Outcome
```

In code:

```python
@dataclass(slots=True)
class LoopNode:
    definition: LoopNodeDefinition
    invocation: LoopNodeInvocation
    runtime: LoopNodeRuntime
```

The objects are still inside LoopNode. The grouping prevents the class
from becoming a thousand flat fields.

### 2.1 Inline, reference, and resolved reference

Not every object should be physically duplicated inside every serialized
LoopNode. Use three representation forms:

```text
Inline<T>
└── The complete typed object is embedded

Reference<T>
└── Stable typed reference to a reusable versioned object

ResolvedReference<T>
└── Reference plus exact version, content hash,
    compatibility result, and resolved immutable value
```

Examples:

```text
ContractBinding = Inline[Contract] | Reference[Contract]
StrategyBinding = Inline[IntelligenceSeekingStrategy] | Reference[IntelligenceSeekingStrategy]
ProcedureBinding = Inline[LoopProcedure] | Reference[LoopProcedure]
```

At authoring time, the definition may contain inline values or
references. At runtime, the LoopNode contains the resolved typed objects
or resolved typed handles:

```text
Authored LoopNode Definition
├── strategy_ref: core.strategy.adversarial@^1
├── contract_ref: core.contract.typed-output@2
└── procedure_ref: learned.procedure.repository-migration@3

Resolved Runtime LoopNode
├── strategy:
│   ├── exact_version: 1.4.2
│   ├── content_hash: sha256:...
│   └── resolved_object: IntelligenceSeekingStrategy
├── contract:
│   ├── exact_version: 2.1.0
│   ├── content_hash: sha256:...
│   └── resolved_object: Contract
└── procedure:
    ├── exact_version: 3.0.1
    ├── content_hash: sha256:...
    └── resolved_object: LoopProcedure
```

That gives the LoopNode actual typed behavior while preserving reuse,
versioning, database storage, plugin distribution, and historical replay.

### 2.2 Child steps are also LoopNodes

For a composite LoopNode:

```text
Parent LoopNode
└── Definition
    └── Procedure
        └── Step Bindings
            ├── references Child LoopNode Definition A
            ├── references Child LoopNode Definition B
            └── references Child LoopNode Definition C
```

When the procedure runs:

```text
Parent LoopNode
└── Runtime
    └── Child LoopNode Handles
        ├── Child LoopNode A
        ├── Child LoopNode B
        └── Child LoopNode C
```

A LoopStepBinding is not another operational type. It is the typed
object inside the parent that describes how to create and connect a
child LoopNode.

Persistent serialization should use typed handles, not recursive full
child objects:

```text
LoopNodeHandle
├── loop_node_id
├── definition_ref
├── run_id
├── state_ref
├── result_ref
└── chronicle_ref
```

Typed handles avoid recursive duplication, enormous serialized records,
inconsistent child copies, circular references, concurrency problems,
conflicting runtime state, and difficult event replay.

### 2.3 Core, Learned, and Plugin supply the typed objects

Core, Learned, and Plugins supply definitions for the typed objects. The
resolved runtime LoopNode composes whichever exact objects were
selected:

```text
LoopNode
├── Core Contract
├── Learned Intelligence-Seeking Strategy
├── Plugin Implementation Binding
├── Core Verification Policy
└── Invocation-Specific Budget
```

They become one resolved typed object graph inside the LoopNode.

### 2.4 Recommended Python shape

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LoopNodeDefinition:
    purpose: Purpose
    contracts: ContractSet
    procedure: LoopProcedure
    execution: ExecutionConfiguration
    intelligence: IntelligenceSeekingConfiguration
    control: LoopControlConfiguration
    verification: VerificationConfiguration
    routing: RoutingConfiguration
    permissions: PermissionConfiguration
    inheritance: InheritanceConfiguration
    compatibility: CompatibilityConfiguration
    observability: ObservabilityConfiguration


@dataclass(frozen=True, slots=True)
class LoopNodeInvocation:
    inputs: InputBindings
    goal_bindings: GoalBindings
    context_bindings: ContextBindings
    delegated_permissions: DelegatedPermissions
    delegated_budget: DelegatedBudget
    allowed_overrides: InvocationOverrides


@dataclass(slots=True)
class LoopNodeRuntime:
    identity: LoopNodeIdentity
    topology: LoopNodeTopology
    resolved_configuration: ResolvedLoopNodeConfiguration
    state: LoopNodeState
    context: LoopNodeContext
    children: list[LoopNodeHandle] = field(default_factory=list)
    chronicle: ChronicleRef | None = None
    outcome: LoopNodeOutcome | None = None


@dataclass(slots=True)
class LoopNode:
    """
    HARD ARCHITECTURE INVARIANT:

    LoopNode is the only operational Node in Loop Engine.

    All contracts, procedures, run-mode policies, intelligence-seeking
    strategies, budgets, verification policies, routing policies,
    permissions, compatibility declarations, state, and topology are
    typed objects composed inside LoopNode.

    No parallel PractitionerNode, IntelligenceNode, SolutionNode,
    CodeNode, or generic concrete Node class may exist.
    """

    definition: LoopNodeDefinition
    invocation: LoopNodeInvocation
    runtime: LoopNodeRuntime
```

### 2.5 The strongest invariant

```text
The LoopNode is the composition root. Every typed object needed to
define, resolve, execute, observe, verify, route, and reproduce that
unit of work is contained by the LoopNode directly or through a typed,
version-pinned object reference.
```

Not:

```text
LoopNode
└── is a thin ID surrounded by unrelated global services
```

And not:

```text
LoopNodeDefinition
LoopNodeSpec
LoopProcedure
IntelligenceStrategy
Contract
Budget
Runtime
```

as disconnected top-level operational systems.

## 4. LoopNode presets: common behaviors without subclasses

"Suggested versions" of LoopNode for basic functionality are called
LoopNode presets. They are not subclasses.

Do not create:

```python
class ConfigurationNode(LoopNode): ...
class ValidationNode(LoopNode): ...
class StringNode(LoopNode): ...
```

Instead, create ordinary LoopNodes with preset references:

```text
LoopNode
├── preset_ref: core.loop_node_preset.configuration_provider@1.0.0
└── role: intelligence
```

### 4.1 Initial Core presets

```text
Core LoopNode Presets
│
├── Value Provider
│   └── Returns one embedded or referenced typed value
├── Configuration Provider
│   └── Returns a version-pinned configuration snapshot
├── Configuration Resolver
│   └── Resolves inheritance, overlays, and environment-specific settings
├── Reference Resolver
│   └── Resolves a typed reference to its exact object or materialization
├── Record Lookup
│   └── Retrieves one or more catalog records
├── Query
│   └── Executes a typed intelligence query
├── Identity / Pass-Through
│   └── Returns its typed input unchanged
├── Transform
│   └── Deterministically maps one typed value to another
├── Validate
│   └── Checks a value against a contract
├── Compare
│   └── Compares typed alternatives
├── Select
│   └── Selects one or more candidates
├── Gate
│   └── Allows, rejects, or routes based on a condition
├── Aggregate
│   └── Combines several child results
├── Persist
│   └── Writes a new immutable record or artifact version
├── Emit
│   └── Emits a typed event or result
└── Composite
    └── Runs a sequence, graph, state machine, iteration, or dynamic procedure
```

Every one of these remains the same LoopNode class.

### 4.2 Configuration presets

"Storing configuration" hides several different operations. They should
not all be collapsed into one vague configuration node.

```text
Configuration LoopNode Presets
│
├── Configuration Value Provider
│   ├── contains or references configuration
│   ├── deterministic
│   ├── read-only
│   └── returns one immutable snapshot
├── Configuration Lookup
│   ├── accepts a key or query
│   ├── queries a file, DuckDB, database, or plugin source
│   └── returns matching settings
├── Configuration Resolver
│   ├── combines Core defaults
│   ├── combines organization settings
│   ├── combines project settings
│   ├── combines user settings
│   ├── applies invocation overrides
│   ├── enforces frozen fields
│   └── returns the final resolved configuration
├── Configuration Validator
│   ├── checks schema
│   ├── checks contracts
│   ├── checks compatibility
│   ├── checks prohibited combinations
│   └── returns validation evidence
└── Configuration Writer
    ├── validates a proposed update
    ├── checks permissions
    ├── performs compare-and-swap
    ├── creates a new immutable version
    ├── records provenance
    └── returns a write receipt
```

Their roles may differ:

```text
Configuration Value Provider  Intelligence-role LoopNode
Configuration Lookup          Intelligence-role LoopNode
Configuration Resolver        Usually Intelligence-role LoopNode
Configuration Validator       Usually Solution-role LoopNode
Configuration Writer          Solution-role LoopNode
```

The role describes why it runs. The preset describes its common
behavior.

### 4.3 Example: minimal configuration-provider LoopNode

```json
{
  "node_kind": "loop_node",
  "preset_ref": {
    "record_ref": "core.loop_node_preset.configuration_provider",
    "version": "1.0.0"
  },
  "purpose": {
    "role": "intelligence",
    "profile_ref": "core.loop_profile.configuration_provider@1.0.0",
    "goal": "Return a version-pinned configuration snapshot."
  },
  "contracts": {
    "input": { "type": "configuration_query", "optional": true },
    "output": { "type": "configuration_snapshot" }
  },
  "procedure": {
    "kind": "atomic",
    "operation": "return_or_resolve_configuration"
  },
  "execution": {
    "run_mode": "deterministic",
    "placement": "inline"
  },
  "payload": {
    "kind": "configuration",
    "value": {
      "maximum_child_loops": 5,
      "default_query_behavior": "guided",
      "require_verification": true
    }
  },
  "control": {
    "maximum_steps": 1,
    "maximum_model_calls": 0,
    "maximum_child_loops": 0,
    "stop_condition": "after_one_terminal_result"
  },
  "permissions": { "effects": [] },
  "observability": { "receipt_level": "minimal" }
}
```

When executed, it returns:

```json
{
  "configuration_snapshot": {
    "configuration_id": "core.config.default_practitioner",
    "configuration_version": "1.0.0",
    "content_hash": "sha256:...",
    "values": {
      "maximum_child_loops": 5,
      "default_query_behavior": "guided",
      "require_verification": true
    },
    "resolved_from": [
      "core.loop_node_preset.configuration_provider@1.0.0"
    ]
  }
}
```

### 4.4 Configuration bindings

The configuration payload inside the LoopNode should support several
typed bindings:

```text
ConfigurationBinding
├── Inline Configuration
│   └── Small configuration embedded directly
├── Record Reference
│   └── Versioned configuration record in the catalog
├── File Reference
│   └── JSON, JSONL, YAML, TOML, or another portable representation
├── Database Reference
│   └── DuckDB, SQLite, PostgreSQL, or another configured store
├── Plugin Reference
│   └── Namespaced plugin-provided configuration
└── Remote Reference
    └── Configuration obtained through a compatible remote catalog
```

The runtime should normalize all of them into one:

```text
ResolvedConfigurationSnapshot
├── logical configuration ID
├── exact version
├── content hash
├── resolved values
├── authority
├── materialization used
├── compatibility verdict
└── resolution receipt
```

This allows the same configuration LoopNode to work with files,
databases, plugins, bundles, and remote services.

### 4.5 A string can also be a minimal LoopNode

```text
String Value LoopNode
├── role: intelligence
├── run mode: deterministic
├── input: Unit
├── payload: StringValue
├── procedure: return payload
├── output: String
├── maximum steps: 1
├── maximum children: 0
├── maximum model calls: 0
└── stop: after output
```

The string is a typed payload inside the LoopNode:

```text
LoopNode
└── payload
    └── StringValue("Always verify output contracts.")
```

The string is not a StringNode class.

### 4.6 Avoid the bootstrap recursion problem

A literal rule that every configuration field must be fetched by
another LoopNode would create infinite recursion:

```text
LoopNode needs configuration
        ↓
starts Configuration LoopNode
        ↓
Configuration LoopNode needs configuration
        ↓
starts another Configuration LoopNode
        ↓
forever
```

The boundary should be:

```text
LoopNode's own resolved definition
└── is already contained inside the LoopNode when execution starts

Reusable or externally selected configuration
└── may be obtained through a Configuration LoopNode
```

Therefore:

- identity, contracts, hard permissions, and the minimum execution
  definition are available before the LoopNode runs;
- a LoopNode does not need another LoopNode merely to discover that it
  exists;
- reusable settings, project settings, user settings, plugin settings,
  and runtime settings may be accessed through configuration LoopNodes;
- the minimal bootstrap kernel directly loads and resolves the first
  LoopNode.

### 4.7 Avoid excessive runtime overhead

A deterministic value or configuration LoopNode should remain logically
a LoopNode, but the kernel may execute it as an inline micro-loop.

```text
Logical Object:    LoopNode

Execution Placement:
├── inline
├── local task
├── worker process
├── container
├── serverless function
└── remote service
```

A configuration provider might run:

```text
Logical LoopNode identity: yes
Typed input and output: yes
Contract enforcement: yes
Result receipt: yes
Separate operating-system process: no
Separate serverless invocation: no
Full verbose Chronicle stream: optional
```

This gives ontology consistency without paying full orchestration
overhead for returning one value.

Run mode and placement must remain separate:

```text
Run mode:  deterministic | hybrid | non_deterministic
Placement: inline | task | process | container | serverless | remote
```

A deterministic LoopNode may execute remotely. A non-deterministic
LoopNode may execute inline.

### 4.8 Recommended minimal LoopNode presets

A preset should fill in defaults, but every field remains overridable
within policy.

```text
core.loop_node_preset.constant_value@1
├── atomic
├── deterministic
├── one output
├── no effects
└── one step

core.loop_node_preset.configuration_provider@1
├── atomic
├── deterministic
├── immutable snapshot
├── no effects
└── one step

core.loop_node_preset.record_lookup@1
├── atomic or iterative
├── deterministic
├── catalog query
└── typed records

core.loop_node_preset.validator@1
├── deterministic
├── contract input
├── validation evidence output
└── no effects

core.loop_node_preset.transform@1
├── deterministic by default
├── typed input
├── typed output
└── pure operation preferred

core.loop_node_preset.effect@1
├── explicit permissions
├── idempotency policy
├── retry policy
├── rollback policy
└── detailed receipt

core.loop_node_preset.composite@1
├── child LoopNode bindings
├── scheduling
├── routing
├── aggregation
└── completion policy
```

Core supplies these presets. Learned Intelligence and Plugins may
contribute additional presets without creating additional node classes.

### 4.9 Hard code comment

Place this comment in the LoopNode class, the node package, and the
architecture contract:

```python
# HARD LOOP ENGINE ONTOLOGY INVARIANT
#
# Node is an ontological category and package namespace only.
# LoopNode is the only concrete graph-addressable operational Node.
#
# Never create:
# - a concrete generic Node class;
# - StringNode;
# - ConfigurationNode;
# - ContractNode;
# - CodeNode;
# - PractitionerNode;
# - IntelligenceNode;
# - SolutionNode;
# - plugin-defined Node classes;
# - another node executor.
#
# Common behaviors are represented by versioned LoopNode presets.
#
# Configurations, strings, contracts, rules, policies, references,
# payloads, results, receipts, and runtime state are typed objects
# contained by or returned from LoopNode. They are not Nodes.
```

### 4.10 Mechanical enforcement

The invariant must be impossible to violate, not merely documented.

Three enforcement layers:

1. Runtime guard: the canonical Loop class refuses subclassing at
   class-creation time:

```python
class Loop:
    def __init_subclass__(cls, **kwargs):
        raise TypeError(
            "Loop is the only operational runtime class and cannot be "
            "subclassed. Use a versioned LoopNode preset or a typed "
            "configuration object instead.")
```

1. No concrete Node class: the passive catalog record is named
   CatalogRecord, not Node. LoopNode is the only node-named class, and
   it is a record at rest, not a runtime.

1. Conformance gate: the operational-graph-vertex scanner fails the
   build on any class named Node or ending in Node or Vertex outside
   the explicit passive-record allowlist. Report projections use
   Record names (LoopReportRecord, LoopGraphVertexRecord,
   LoopRelationshipRecord). Passive envelopes use Envelope names
   (IntelligenceItemEnvelope).

Required tests:

```text
test_loop_cannot_be_subclassed
test_no_concrete_node_class_exists
test_only_loop_node_has_a_node_named_class
test_report_projections_use_record_names
test_passive_envelopes_use_envelope_names
test_conformance_gate_rejects_new_node_named_classes
```

### 4.11 Final formulation

```text
Never have a Node that is not a LoopNode.

Allow typed objects inside LoopNode.

Expose reusable values and basic functionality through minimal,
deterministic LoopNode presets.

Use presets rather than subclasses.

Allow small LoopNodes to execute inline as micro-loops.

Use typed references for large, shared, file-backed,
database-backed, or plugin-backed payloads.

Keep the minimum resolved configuration inside the LoopNode
to prevent recursive bootstrap.

Everything independently performing or governing work is a LoopNode.

Everything else is typed content owned, consumed, resolved,
validated, or returned by a LoopNode.
```

## 5. Architectural baseline

### 3.1 One operational node

Preserve the hard Loop Engine invariant:

```text
Node
└── LoopNode
```

Node is an architectural category and namespace. LoopNode is the only
concrete operational node.

Never introduce a concrete generic Node, role-specific node classes,
mode-specific node classes, step-specific node classes, plugin-defined
node kinds, or a second node executor.

Practitioner, Intelligence, and Solution are roles of the same LoopNode.
Root and Child are positions of the same LoopNode. Deterministic, hybrid,
and non-deterministic are run modes of the same LoopNode.

### 3.2 Governed work boundary

Every independently governed unit of work above the kernel executes as a
LoopNode. Create a separate LoopNode when work needs an independent goal,
contract, budget, stop condition, permissions, verification, retry,
repair, Chronicle identity, scheduling, delegation, cancellation, or
governance.

Ordinary adapter methods, SQL execution calls, hash calculations,
serialization helpers, schema validators, and provider SDK calls may
remain implementation primitives inside a governed LoopNode.

Named, independently governed semantic steps generally should be child
LoopNodes. A low-level implementation call does not automatically require
another LoopNode.

## 6. Required canonical objects

### 4.1 LoopNodeDefinitionRecord

The reusable, versioned object stored in Core, Learned, or Plugin
intelligence.

```text
LoopNodeDefinitionRecord
│
├── Record Envelope
│   ├── definition_id
│   ├── definition_version
│   ├── schema_version
│   ├── catalog_namespace
│   │   ├── core
│   │   ├── learned
│   │   └── plugin:<plugin_id>
│   ├── lifecycle
│   ├── provenance
│   ├── content_hash
│   └── compatibility_declaration
│
└── LoopNodeSpec
    ├── Purpose
    │   ├── role
    │   │   ├── practitioner
    │   │   ├── intelligence
    │   │   └── solution
    │   ├── profile_ref
    │   ├── goal_template
    │   └── success_criteria
    │
    ├── Contracts
    │   ├── input_contract_refs
    │   ├── output_contract_refs
    │   ├── precondition_refs
    │   ├── postcondition_refs
    │   └── invariant_refs
    │
    ├── Procedure
    │   └── procedure_spec
    │
    ├── Run Mode
    │   └── run_mode_policy
    │
    ├── Intelligence Seeking
    │   └── intelligence_seeking_binding
    │
    ├── Context
    │   ├── context_assembly_policy
    │   ├── runtime_memory_policy
    │   ├── parent_context_policy
    │   └── private_context_policy
    │
    ├── Execution
    │   ├── implementation_refs
    │   ├── binding_refs
    │   ├── resource_requirements
    │   └── effect_requirements
    │
    ├── Verification
    │   ├── verification_policy
    │   ├── evaluator_refs
    │   └── acceptance_policy
    │
    ├── Failure and Repair
    │   ├── retry_policy
    │   ├── repair_policy
    │   ├── fallback_policy
    │   └── escalation_policy
    │
    ├── Routing
    │   ├── continuation_policy
    │   ├── child_spawn_policy
    │   ├── parent_return_policy
    │   └── completion_policy
    │
    ├── Limits
    │   ├── work_budget
    │   ├── query_budget
    │   ├── model_budget
    │   ├── child_loop_budget
    │   └── stop_conditions
    │
    ├── Permissions
    │   ├── access_policy_refs
    │   ├── effect_policy_refs
    │   ├── approval_requirements
    │   └── delegated_permissions
    │
    ├── Inheritance
    │   ├── parent_inheritance
    │   ├── practitioner_inheritance
    │   ├── graph_inheritance
    │   ├── allowed_overrides
    │   └── frozen_fields
    │
    ├── Compatibility
    │   ├── engine_constraints
    │   ├── ontology_constraints
    │   ├── protocol_constraints
    │   ├── plugin_constraints
    │   └── migration_requirements
    │
    └── Observability
        ├── chronicle_policy
        ├── receipt_policy
        ├── trace_policy
        └── evidence_retention_policy
```

This is the complete reusable definition. It can be serialized to JSON,
stored in Core JSONL, persisted in DuckDB or PostgreSQL, exported in a
portable bundle, or supplied by a plugin without changing its identity.

### 4.2 LoopProcedureSpec

The current code calls this a "step profile." Refine it into a
LoopProcedureSpec, because it can describe much more than a fixed list of
steps.

```text
LoopProcedureSpec
│
├── procedure_kind
│   ├── atomic
│   ├── sequence
│   ├── directed_graph
│   ├── state_machine
│   ├── iterative
│   ├── parallel
│   └── dynamic
│
├── child_loop_bindings
│   └── LoopStepBinding[]
│
├── connections
│   ├── dependency_edges
│   ├── typed_value_edges
│   ├── conditional_edges
│   ├── fallback_edges
│   └── repair_edges
│
├── scheduling
│   ├── sequential
│   ├── parallel
│   ├── bounded_parallel
│   └── dynamically_selected
│
├── repetition
│   ├── iteration_conditions
│   ├── maximum_iterations
│   └── convergence_conditions
│
├── completion
│   ├── required_children
│   ├── optional_children
│   ├── quorum
│   ├── first_success
│   └── aggregate_results
│
└── dynamic_spawning
    ├── allowed
    ├── child_definition_constraints
    ├── maximum_dynamic_children
    └── spawn_approval_policy
```

### 4.3 LoopStepBinding

A step is not a second operational type. It is a binding that says which
child LoopNode definition should be instantiated and how it connects to
the containing LoopNode.

```text
LoopStepBinding
├── step_id
├── loop_definition_ref
├── input_mapping
├── output_mapping
├── dependency_refs
├── activation_condition
├── skip_condition
├── optional
├── repeat_policy
├── local_configuration_overrides
├── intelligence_seeking_override
├── run_mode_override
├── budget_delegation
├── permission_delegation
└── inheritance_mode
```

At definition time:

```text
Parent LoopNodeDefinition
└── contains LoopStepBindings
    └── each references a child LoopNodeDefinition
```

At runtime:

```text
Parent LoopNode
└── starts Child LoopNodes
    └── tracks their LoopNode IDs
```

The parent should not recursively embed complete live child objects. It
keeps child references, while the runtime and Chronicle preserve the
actual run tree.

### 4.4 RunModePolicy

The reusable definition contains a RunModePolicy, not only an enum.

```text
RunModePolicy
│
├── selection_mode
│   ├── fixed
│   ├── rule_selected
│   ├── model_selected
│   └── adaptive
│
├── preferred_mode
│   ├── deterministic
│   ├── hybrid
│   └── non_deterministic
│
├── allowed_modes
├── prohibited_modes
│
├── escalation_order
│   ├── deterministic
│   ├── hybrid
│   └── non_deterministic
│
├── escalation_conditions
│   ├── deterministic_failure
│   ├── semantic_ambiguity
│   ├── low_confidence
│   ├── verification_failure
│   └── explicit_parent_request
│
├── deescalation_conditions
├── maximum_mode_transitions
└── mode_transition_receipt_required
```

Example:

```json
{
  "selection_mode": "adaptive",
  "preferred_mode": "deterministic",
  "allowed_modes": [
    "deterministic",
    "hybrid",
    "non_deterministic"
  ],
  "escalation_order": [
    "deterministic",
    "hybrid",
    "non_deterministic"
  ],
  "maximum_mode_transitions": 2
}
```

The actual runtime instance records resolved_run_mode, attempt_run_modes,
mode_transition_reasons, model_calls, and verification results.

Keep model configuration separate from run mode:

```text
Run Mode
└── Who leads the work and whether a model may participate

Model Policy
└── Which model, provider, thinking level, call budget,
    fallback, timeout, and response contract apply
```

"LLM mode" can be a user-facing label, but the canonical architecture
term remains non_deterministic or a clearer alias such as model_led.

### 4.5 IntelligenceSeekingBinding

Intelligence seeking is a standard part of every LoopNodeSpec, not
Practitioner-only.

```text
IntelligenceSeekingBinding
│
├── access_policy_ref
│
├── strategy_selection
│   ├── fixed
│   ├── ranked_set
│   ├── rule_selected
│   ├── model_selected
│   ├── synthesized
│   └── adaptive
│
├── strategy_refs
├── query_profile_refs
│
├── preferences
│   ├── functional_domain_priorities
│   ├── perspective_priorities
│   ├── artifact_kind_priorities
│   ├── catalog_namespace_priorities
│   ├── evidence priorities
│   └── ranking objectives
│
├── requirements
│   ├── required_domains
│   ├── required_perspectives
│   ├── required_artifact_kinds
│   ├── minimum_evidence_quality
│   ├── minimum_source_diversity
│   └── minimum_governance_status
│
├── query_behavior
│   ├── open
│   ├── guided
│   ├── bounded
│   └── strict
│
├── expansion_policy
├── fallback_policy
├── adaptation_policy
├── query_budget
└── receipt_policy
```

A deterministic LoopNode can still use an intelligence-seeking strategy.
Its search may simply be deterministic SQL, exact filtering, graph
traversal, or ranking.

A non-deterministic LoopNode may generate subqueries or synthesize a
run-scoped seeking strategy, but access policies and hard budgets remain
outside its control.

### 4.6 ResolvedLoopNodePlan

The reusable definition should not be copied blindly into runtime. It
should be resolved through an explicit inheritance chain:

```text
Constitutional Constraints
        ↓
Deployment Policies
        ↓
Organization Policies
        ↓
Core Role Defaults
        ↓
Practitioner Definition Defaults
        ↓
LoopGraphSpec Defaults
        ↓
LoopNodeDefinition
        ↓
Parent Delegation
        ↓
LoopStepBinding Overrides
        ↓
Invocation Overrides
        ↓
Compatibility Handshake
        ↓
Governance Clamp
        ↓
ResolvedLoopNodePlan
```

The final plan is immutable for that invocation and pins:

- exact definition versions;
- exact profile versions;
- exact strategy versions;
- content hashes;
- resolved run mode;
- resolved permissions;
- resolved budgets;
- resolved contracts;
- store snapshots;
- plugin versions;
- compatibility verdicts.

This makes historical playback and reproducibility possible.

### 4.7 LoopNode runtime object

The actual runtime LoopNode should be much smaller than the reusable
definition:

```text
LoopNode
│
├── loop_node_id
├── definition_ref
├── invocation_id
├── resolved_plan_ref
│
├── topology
│   ├── position
│   ├── parent_loop_node_id
│   └── child_loop_node_ids
│
├── runtime_state
│   ├── status
│   ├── current_attempt
│   ├── resolved_run_mode
│   ├── current_procedure_position
│   ├── consumed_budget
│   └── active_effects
│
├── context_refs
│   ├── input_refs
│   ├── runtime_memory_ref
│   ├── private_context_ref
│   └── intelligence_portfolio_snapshot_refs
│
├── chronicle_ref
├── result_ref
└── failure_ref
```

The LoopNode does not need to carry every definition body inline. It
carries exact references to the resolved plan and records.

### 4.8 Embed versus reference rule

The typed objects are fields inside the LoopNode, but only the ones that
are single-owner and invocation-specific. Shared, versioned, governed
artifacts are referenced, never embedded.

```text
LoopNodeDefinitionRecord
└── LoopNodeSpec                    (embedded: this definition's authoritative config)
    ├── RunModePolicy               (embedded value object)
    ├── ModelPolicy                 (embedded value object)
    ├── LoopProcedureSpec           (embedded value object)
    │   └── LoopStepBinding[]       (embedded, but each references a child definition)
    ├── IntelligenceSeekingBinding  (embedded value object)
    ├── budgets, stop conditions    (embedded value objects)
    ├── permissions                 (embedded value objects)
    │
    └── references (ID + version + hash, never embedded copies)
        ├── profile_ref
        ├── contract_refs
        ├── strategy_refs
        ├── access_policy_refs
        ├── implementation_refs
        └── child loop_definition_refs
```

Rules:

- Embed what is small, immutable, and owned by this one definition:
  policies, budgets, conditions, procedure, bindings. A change to them
  changes this definition's content hash.
- Reference what is shared, versioned, and governed: contracts,
  profiles, strategies, access policies, child definitions,
  implementations. Embedding copies would break governance; a contract
  revision must not silently change every LoopNode that copied it.
- Runtime state (consumed budget, current position, active effects,
  mode transitions) are fields on the runtime LoopNode itself.

Code location is separate from object composition. A policy class may
live in a planes module, but the policy object is a field inside the
LoopNodeSpec and the resolved plan.

## 7. Default Practitioner versus custom Practitioners

The nine-step Practitioner should be shipped as a Core
LoopNodeDefinition plus a Core LoopProcedureSpec.

```text
core.default_practitioner@1.0.0
│
├── role: practitioner
├── procedure_kind: directed_graph
└── nine LoopStepBindings
```

Each default step references its own Core LoopNode definition and default
intelligence-seeking configuration.

A custom Practitioner can instead define one step, four steps, twenty
steps, parallel steps, repeated steps, conditional steps, dynamically
generated child loops, a state machine, or a cyclic graph with bounded
termination.

The kernel does not know or care that the default Practitioner contains
nine steps.

## 8. Required implementation architecture

Inspect the current repository and adapt paths as needed, but target a
compact architecture like this:

```text
src/loop_engine/
├── node/
│   └── loop_node/
│       ├── README.md
│       ├── definition_record.py
│       ├── spec.py
│       ├── procedure_spec.py
│       ├── step_binding.py
│       ├── run_mode_policy.py
│       ├── model_policy.py
│       ├── invocation.py
│       ├── resolved_plan.py
│       ├── model.py
│       ├── result.py
│       └── references.py
│
├── planes/
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

Do not create physical folders for individual steps, roles, modes, or
default step names. Core records ship in package data. Learned data lives
in instance stores. Plugin data lives in plugin packages, bundles,
stores, or services.

## 9. Migration of current scattered configuration

The current codebase already contains pieces of this model. Migrate them.

### 7.1 Current pieces

```text
LoopDefinition
├── definition_id, version, content_digest
├── role_profile_id, role_profile_version
├── contract
├── configuration_facts
├── supported_modes, installed_executor_modes
├── step_profile
├── loop_condition, exit_condition
├── effects, permissions, required_capabilities

LoopConfig
├── framework
├── logical_kind
├── allowable_modes, preferred_modes, delegated_modes
├── power, llm_thinking_power
├── custom_steps
├── max_depth
├── loop_condition, exit_condition
├── success_confidence_min

LoopStartRequest
├── goal
├── definition
├── relationship
├── runtime context
├── event log
```

### 7.2 Target mapping

```text
LoopDefinition → LoopNodeDefinitionRecord
LoopConfig → LoopNodeSpec (resolved through the inheritance chain)
step_profile → LoopProcedureSpec
custom_steps → LoopStepBindings
allowable_modes → RunModePolicy.allowed_modes
preferred_modes → RunModePolicy.preferred_mode
power → ModelPolicy.thinking_power
llm_thinking_power → ModelPolicy.thinking_power
max_depth → ExecutionPolicy.delegation_depth_ceiling
loop_condition → LoopCondition
exit_condition → ExitCondition
effects → EffectPolicy
permissions → AccessPolicy
required_capabilities → CapabilityRequirements
```

Preserve the existing hard rules: a Loop refuses to start when its
definition is invalid, its digest changed, its profile is not
registered, or its required capabilities, permissions, or executors are
missing. Mode never grants file, network, secret, model, spending, or
external-effect permission.

## 10. Adversarial corner cases

The implementation must support and test all of these.

### 8.1 Zero-step Practitioner

A declarative Practitioner that delegates immediately. Define valid
behavior for zero-step and empty graphs.

### 8.2 Arbitrary step names

Step behavior must not depend on names such as orient, act, verify, or
route. Test names such as alpha, compare_architecture_variants, 批准,
مرحلة_الفحص, and step-001. Use stable IDs separate from display names.

### 8.3 Repeated steps

The same definition may execute multiple times. Each invocation must
receive a unique runtime identity, a pinned resolved plan, its own
receipts, inherited constraints, and explicit previous-attempt
references.

### 8.4 Optional and skipped steps

A skipped step must record the skip reason, conditions evaluated, whether
a plan was resolved, whether any required intelligence was omitted, and
the routing decision.

### 8.5 Branches and concurrency

Different branches may bind different profiles. The merge system must
not leak branch-private adaptations into siblings. Concurrent steps may
share read-only snapshots, use separate private portfolio snapshots,
consume shared budgets, and encounter catalog updates mid-run.

### 8.6 Cycles and iterative loops

A Practitioner graph may revisit a step. Prevent profile-resolution
accumulation on every pass, duplicate inherited weights, unbounded
receipt growth, and stale record reuse when refresh is required.

### 8.7 Dynamic graph generation

A generated step must pass schema validation, trait validation,
access-policy inheritance, profile compatibility, budget allocation,
parent authorization, and Chronicle registration. A generated step may
not introduce an unregistered executable node type.

### 8.8 Internal step versus Child LoopNode

Use the same binding schema. Document the atomicity rule determining
when an internal step becomes a Child LoopNode. Test equivalent behavior
when the same governed work is represented internally versus as a child,
except where isolation or budget scope intentionally differs.

### 8.9 Parent and child privacy

A child may inherit shared run context according to policy. A child must
not automatically receive sibling private history, sibling portfolio
snapshots, user-scoped intelligence outside delegated scope, parent
secrets not explicitly delegated, or private model transcripts.

### 8.10 Nested Practitioners

A Practitioner-role Child Loop may start another Practitioner-role Child
Loop. Ensure constraints remain monotonic, budgets are accounted, exact
profile versions are pinned, no privilege broadening occurs through deep
nesting, and cycle and depth limits work.

### 8.11 Mode escalation

A deterministic attempt fails, the RunModePolicy escalates to hybrid,
then to non-deterministic, and the maximum_mode_transitions ceiling
stops further escalation. Each transition emits a receipt.

### 8.12 Mode deescalation

A non-deterministic attempt succeeds and the policy deescalates future
attempts to deterministic. The deescalation is recorded.

### 8.13 Model policy separation

A LoopNode with a non-deterministic run mode and a zero-call model
budget refuses with a typed error, not a silent no-op.

### 8.14 Historical replay

Replaying a run must use the exact definition, profile, strategy, and
plan versions, hashes, and store snapshots resolved at the original
time. New defaults must not leak into replay.

### 8.15 LLM-authored procedure

An LLM Practitioner proposes a custom LoopProcedureSpec. The draft
passes schema validation, operator validation, access-policy check,
budget check, cycle and termination check, adapter compatibility
handshake, and governance clamp. The LLM may not edit hard policy.

## 11. Required test suite

### 9.1 Architecture tests

```text
test_loop_node_is_only_operational_node
test_no_concrete_generic_node
test_no_role_specific_node_classes
test_no_mode_specific_node_classes
test_no_step_specific_node_classes
test_steps_are_bindings_not_embedded_objects
test_parent_definition_contains_references_not_live_children
test_kernel_has_no_default_nine_step_knowledge
test_semantic_folders_have_readmes
test_architecture_manifest_matches_tree
```

### 9.2 Definition and spec tests

```text
test_definition_record_round_trips_through_json
test_definition_record_round_trips_through_jsonl
test_definition_record_round_trips_through_database
test_spec_validates_required_fields
test_spec_rejects_unknown_roles
test_spec_rejects_unknown_modes
test_spec_rejects_negative_budgets
test_spec_pins_content_hash
test_modified_definition_invalidates_hash
test_policies_are_embedded_value_objects
test_shared_artifacts_are_referenced_not_embedded
test_contract_revision_does_not_silently_change_definitions
test_child_definitions_are_referenced_not_embedded
test_runtime_state_lives_on_the_runtime_loop_node
test_loop_node_is_the_composition_root
test_definition_invocation_runtime_are_inside_loop_node
test_inline_and_reference_bindings_are_supported
test_resolved_reference_pins_version_and_hash
test_child_handles_are_not_recursive_full_objects
test_serialized_loop_node_has_no_circular_references
test_core_learned_plugin_objects_compose_into_one_loop_node
test_presets_are_not_subclasses
test_no_configuration_node_class
test_no_string_node_class
test_configuration_provider_preset_returns_snapshot
test_configuration_resolver_preset_resolves_inheritance
test_configuration_writer_preset_uses_compare_and_swap
test_string_value_loop_node_returns_typed_payload
test_inline_micro_loop_keeps_logical_loop_node_identity
test_run_mode_and_placement_are_separate
test_bootstrap_does_not_require_recursive_configuration_loops
test_minimum_resolved_configuration_is_inside_the_loop_node
test_plugin_preset_cannot_shadow_core_preset
```

### 9.3 Procedure tests

```text
test_atomic_procedure
test_sequence_procedure
test_directed_graph_procedure
test_state_machine_procedure
test_iterative_procedure_with_bounded_termination
test_parallel_procedure
test_dynamic_procedure
test_procedure_cycle_detection
test_procedure_requires_termination_bound
test_step_binding_maps_inputs_and_outputs
test_step_binding_activation_and_skip_conditions
test_step_binding_repeat_policy
```

### 9.4 Run mode tests

```text
test_fixed_mode_selection
test_rule_selected_mode
test_model_selected_mode_from_approved_set
test_adaptive_mode_escalation
test_adaptive_mode_deescalation
test_maximum_mode_transitions_enforced
test_mode_transition_receipt_emitted
test_mode_never_grants_permission
test_model_policy_is_separate_from_run_mode
test_zero_model_budget_refuses_with_typed_error
```

### 9.5 Intelligence seeking tests

```text
test_every_loop_node_spec_may_bind_intelligence_seeking
test_deterministic_loop_node_may_seek_intelligence
test_non_deterministic_loop_node_may_synthesize_strategy
test_synthesized_strategy_cannot_edit_access_policy
test_seeking_budget_is_enforced
```

### 9.6 Resolution tests

```text
test_inheritance_chain_resolves_deterministically
test_child_cannot_broaden_parent_scope
test_invocation_override_beats_definition_default
test_governance_clamp_beats_invocation_override
test_resolved_plan_pins_exact_versions
test_resolved_plan_pins_content_hashes
test_resolved_plan_is_immutable
test_running_plan_remains_pinned_after_definition_update
test_merge_receipt_explains_every_effective_field
```

### 9.7 Runtime tests

```text
test_loop_node_carries_references_not_bodies
test_child_loop_node_ids_are_tracked
test_parent_does_not_embed_live_children
test_runtime_state_tracks_consumed_budget
test_runtime_state_tracks_mode_transitions
test_result_and_failure_are_typed
test_cancellation_is_terminal_and_recorded
```

### 9.8 Default Practitioner tests

```text
test_default_practitioner_is_a_core_record
test_default_practitioner_has_nine_step_bindings
test_each_default_step_references_its_own_definition
test_custom_practitioner_may_have_any_step_count
test_custom_practitioner_may_have_any_step_names
test_kernel_does_not_branch_on_default_step_names
```

### 9.9 Migration tests

```text
test_loop_definition_migrates_to_definition_record
test_loop_config_migrates_to_spec
test_step_profile_migrates_to_procedure_spec
test_custom_steps_migrate_to_step_bindings
test_allowable_modes_migrate_to_run_mode_policy
test_power_migrates_to_model_policy
test_old_serialized_definitions_remain_readable
test_migration_is_resumable_and_idempotent
test_migration_round_trip_preserves_identity
```

### 9.10 End-to-end scenarios

Automate at least:

- Scenario A: default nine-step Practitioner runs with Core defaults.
- Scenario B: four-step custom Practitioner with arbitrary step names.
- Scenario C: one-step deterministic validator.
- Scenario D: dynamic Practitioner creating steps mid-run.
- Scenario E: concurrent children with private plans.
- Scenario F: adaptive mode escalation with receipts.
- Scenario G: historical replay with original plan versions.
- Scenario H: LLM-authored procedure validated and executed through
  ordinary LoopNodes.

## 12. Development workflow

Execute in this order.

- Phase 0: inventory. Read repository instructions, inspect current
  Loop, LoopDefinition, LoopConfig, step, and mode code, inventory paths
  and symbols, identify production call paths, identify persistence and
  serialized references, identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: schemas and models. Implement LoopNodeDefinitionRecord,
  LoopNodeSpec, LoopProcedureSpec, LoopStepBinding, RunModePolicy,
  ModelPolicy, LoopNodeInvocation, ResolvedLoopNodePlan, LoopNode,
  LoopNodeResult. Add contract tests.
- Phase 3: resolution engine. Implement the inheritance chain,
  deterministic merge, cycle detection, conflict detection, exact version
  pinning, compatibility handshakes, and governance clamp.
- Phase 4: runtime integration. Wire the resolved plan into the existing
  Loop runtime. Migrate LoopConfig and LoopDefinition onto the new
  model.
- Phase 5: Core defaults. Ship the default Practitioner as Core records
  with nine step bindings.
- Phase 6: migration. Migrate production paths, migrate records, migrate
  docs, remove legacy architecture, add temporary shims only when
  necessary.
- Phase 7: red team. Run security tests, fuzz tests, failure injection,
  concurrency tests, mutation tests.
- Phase 8: packaging and clean install. Build wheel and source
  distribution, inspect package data, verify Core JSONL and schemas
  ship, install in a clean environment, run default and custom
  scenarios.
- Phase 9: predeploy. Run one strict command, such as
  `python -m loop_engine.predeploy --strict`. Return one verdict: PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 13. Prohibited shortcuts

Do not:

- create step-specific or mode-specific node classes;
- embed live child objects in parent definitions;
- hard-code the nine default step names;
- merge run mode and model policy;
- merge access policy and preferences;
- use one generic config dictionary;
- use one ambiguous version, status, or source;
- trust filesystem order or plugin discovery order;
- silently broaden a policy;
- silently drop conflicts;
- let an LLM edit hard policy;
- let a Child Loop broaden parent scope;
- let self-review approve itself;
- preserve the old architecture indefinitely beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths still
  use legacy code.

## 14. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented schemas and models;
- Core JSONL records and manifests;
- resolution engine implementation;
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

## 15. Final completion standard

The work is complete only when all of the following are true:

- Every governed unit of work is a LoopNode.
- Every LoopNode is created from a versioned LoopNodeDefinition.
- Every composite LoopNode describes children through LoopStepBindings.
- Every child LoopNode may have its own role, profile, run mode,
  intelligence-seeking strategy, contracts, budget, permissions,
  verification, repair, and stop conditions.
- Run mode is a policy, separate from model policy.
- Intelligence seeking is a standard field on every LoopNodeSpec.
- The default Practitioner is expressed entirely through Core versioned
  records and bindings.
- The kernel contains no dependency on default step names.
- The resolved runtime plan records exactly what was inherited,
  overridden, selected, permitted, and executed.
- Access policies remain hard and monotonic.
- Preferences remain soft and composable.
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
