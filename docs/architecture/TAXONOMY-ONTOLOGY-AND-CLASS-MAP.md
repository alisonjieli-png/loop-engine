# Taxonomy, ontology, and class map

This page classifies Loop Engine without creating another specification. It
maps public concepts to current code and marks the consolidation gaps. The
[contract index](../contracts/) points to detailed contract objects. The
[drift audit](LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md) contains the
supporting findings.

## One operational runtime

```text
Operational runtime
└── Loop
    ├── role: Practitioner, Intelligence, or Solution
    ├── exact versioned role profile
    ├── selected mode for this Loop instance
    ├── step profile
    ├── typed input and output contract
    ├── settings, budget, permissions, and effects
    ├── loop condition and exit condition
    ├── relationship to other Loops
    └── Run History events
```

Every executable graph vertex must resolve to a Loop. A service, record, file,
port, edge, slot, prompt, package, or report is not a second runtime type.

## Definition and run instance

Definition and execution state belong in separate objects.

```text
Loop definition, immutable and reusable
├── definition identity, semantic version, and content digest
├── role and exact role profile
├── supported modes and installed executors
├── typed input and output PortSpecs
├── step profile and settings schema
├── loop condition and exit condition
├── budgets, permissions, and effects
├── required Static Architecture capabilities
└── required internal runtime mechanics

Loop instance, one run of one definition
├── instance identity
├── exact definition reference
├── selected mode
├── validated input values
├── run-scoped settings and counters
├── relationships to other Loop instances
├── output values
└── Run History event references
```

| State | Current implementation | Gap |
|---|---|---|
| Current | `LoopRoleIdentity`, `LoopRelationship`, `LoopProfileSpec`, `LoopConfig`, `LoopContract`, and `EffectiveLoopSpec` split these concerns into typed objects. | No single immutable `LoopDefinition` binds every field, semantic version, and digest. |
| Current | `Loop` stores identity, relationship, configuration, contract, state, counters, and an event ledger. | The constructor does not yet require one registered, digest-bound definition reference. |
| Target | Every runnable Loop comes from one validated definition. | Unknown profiles, abstract profiles, unavailable executors, incompatible settings, and unresolved service requirements must fail before execution. |

## Role profile ontology

Abstract branches organize registered profiles. They do not create runtime
classes.

```text
Loop profile
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── self-improvement task
│   └── code execution
├── Intelligence
│   ├── cross-layer search
│   ├── cross-layer materialize
│   ├── Context Intelligence
│   │   ├── serve
│   │   ├── search
│   │   └── frame
│   ├── Code Intelligence
│   │   ├── resolve
│   │   ├── invoke
│   │   └── load package or repository
│   ├── Runtime History and Solution Intelligence
│   │   ├── search
│   │   ├── replay
│   │   └── compare
│   └── User Feedback Intelligence
│       ├── serve
│       ├── scope
│       └── interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

### Practitioner profiles

| Registered profile ID | Supported modes | Step template |
|---|---|---|
| `practitioner.reference_nine_step` | deterministic, hybrid, non-deterministic | `reference_nine_step` |
| `practitioner.compact_five_step` | deterministic, hybrid, non-deterministic | `compact_five_beat` |
| `practitioner.research` | deterministic, hybrid, non-deterministic | `research_intensive` |
| `practitioner.solver` | deterministic, hybrid, non-deterministic | `build_test_repair` |
| `practitioner.verifier` | deterministic, hybrid, non-deterministic | `adversarial_review` |
| `practitioner.self_improvement` | deterministic, hybrid, non-deterministic | `continuous_improvement` |
| `practitioner.code_execution` | deterministic | `atomic_code_only` |

### Intelligence profiles

| Registered profile ID | Supported modes | Step template |
|---|---|---|
| `intelligence.search` | deterministic | `compact_five_beat` |
| `intelligence.materialize` | deterministic | `atomic_code_only` |
| `intelligence.context.serve` | deterministic | `atomic_code_only` |
| `intelligence.context.search` | deterministic | `compact_five_beat` |
| `intelligence.context.frame` | deterministic, hybrid, non-deterministic | `compact_five_beat` |
| `intelligence.code.resolve` | deterministic | `compact_five_beat` |
| `intelligence.code.invoke` | deterministic | `atomic_code_only` |
| `intelligence.code.package` | deterministic | `compact_five_beat` |
| `intelligence.runtime_history_solution.search` | deterministic | `compact_five_beat` |
| `intelligence.runtime_history_solution.replay` | deterministic | `compact_five_beat` |
| `intelligence.runtime_history_solution.compare` | deterministic, hybrid, non-deterministic | `adversarial_review` |
| `intelligence.user_feedback.serve` | deterministic | `atomic_code_only` |
| `intelligence.user_feedback.scope` | deterministic | `compact_five_beat` |
| `intelligence.user_feedback.interpret` | deterministic, hybrid, non-deterministic | `compact_five_beat` |

The four abstract Intelligence branch IDs are `intelligence.context`,
`intelligence.code`, `intelligence.runtime_history_solution`, and
`intelligence.user_feedback`. Abstract profiles cannot run directly.

### Solution profiles

| Registered profile ID | Supported modes | Step template |
|---|---|---|
| `solution.atomic_component` | deterministic | `atomic_code_only` |
| `solution.pipeline` | deterministic | `compact_five_beat` |
| `solution.router_fallback` | deterministic | `compact_five_beat` |
| `solution.ensemble` | deterministic | `compact_five_beat` |
| `solution.validator` | deterministic | `adversarial_review` |

Loop Engine defines three modes, but a registered profile may support a safe
subset. The current in-process Solution runner supports deterministic Solution
Loops only. It must refuse unsupported Solution modes until real adapters pass
their tests.

## Selected mode and step profile

Mode and step profile are independent.

| Mode | What leads the work | Model use |
|---|---|---|
| deterministic | Code, rules, calculations, retrieval, or another repeatable operation. | No model call. |
| hybrid | Code leads. A model may resolve a bounded semantic step. | Optional and recorded. |
| non-deterministic | A model leads semantic work. Loop Engine controls tools, permissions, budgets, logging, and verification. | Required for the model-led step. |

One Loop instance selects one mode. A Canvas, pipeline, graph, or spawning Loop
does not assign one inherited mode to connected or spawned Loops.

| Step profile | Shape | Use |
|---|---|---|
| `atomic_code_only` | One bounded action. | Small deterministic work. |
| `compact_five_beat` | Load, choose, act, check, commit. | Short bounded work. |
| `reference_nine_step` | Orient, reconcile, assess, decide, determine how, act, verify, integrate, route. | General Practitioner work. |
| Task-specific registered templates | Research, build-test-repair, adversarial review, improvement, and other bounded sequences. | A registered role profile selects the template. |
| Validated custom profile | From 1 to 200 ordered steps. | Caller-defined work that passes template validation. |

## Loop and exit conditions

```text
Loop condition
├── steps_remain
└── chooser_selects_work

Exit condition
├── steps_complete
└── accepted_success
```

The loop condition answers whether another iteration may run. The exit
condition defines successful completion. A deadline, depth limit, call limit,
or resource budget is a safety limit, not a successful exit.

## Contracts, settings, and authority

```text
Loop boundary
├── LoopContract
│   ├── input roles
│   ├── output roles
│   └── declared effects
├── LoopConfig
│   ├── selected framework
│   ├── allowed and preferred modes
│   ├── delegated modes
│   ├── loop condition and exit condition
│   └── effort and depth limits
├── RuntimeSettings
│   ├── Loop defaults
│   ├── retrieval choices
│   ├── provider and model routes
│   ├── thinking-power tiers
│   └── operating policy
├── typed port values and connection checks
├── effect approval
└── workspace and network policy
```

These fields do not grant one another. A mode does not grant network access. A
larger model tier does not grant a larger effect policy. A successful retrieval
does not approve execution. Read the [contract index](../contracts/) for exact
objects and current gaps.

## Loop relationships

| Relationship | Required identity | Meaning |
|---|---|---|
| Starting | No incoming Loop relationship. | Begins one independent Practitioner, Intelligence, or Solution graph. |
| Spawned by | One spawning Loop ID. | Dynamic work created with its own goal, contract, budget, and exit. |
| Queried by | One querying Loop ID. | An Intelligence Query Loop receives a need. |
| Retrieved by | One retrieving Loop ID. | A selected Intelligence Item Loop verifies and serves one item. |
| Connected from | One or more upstream Loop IDs. | Typed values enter a Solution Loop through declared edges. |

Relationship is not role. A Retrieved Loop is still an Intelligence Loop. A
Connected Loop is still a Solution Loop. A Spawned Loop may use any role whose
profile and contract permit that work.

## Static Solution DAG and dynamic Practitioner graph

```text
Dynamic Practitioner run graph
Task
└── Starting Practitioner
    ├── Spawned by: research Practitioner
    ├── Queried by: Intelligence search
    │   └── Retrieved by: selected Intelligence item
    ├── Spawned by: candidate Practitioner
    └── Spawned by: verifier Practitioner

Static Solution DAG
Input
└── Starting Solution
    └── Connected from: validation Solution
        └── Connected from: transformation Solution
            └── Connected from: execution Solution
                └── Connected from: output validation Solution
```

The Practitioner graph records how Loop Engine built and tested work. The
Solution DAG defines what runs for a new input. Dynamic fallback, repair, and
ensemble selection may add Spawned Solution Loops. A straight deterministic
pipeline uses Connected from relationships.

The current package has `Canvas`, `SolutionSpec`, and `LoopGraphSpec`. These
are overlapping graph records. The target is one versioned
`LoopGraphDefinition`; the other views become projections or builders.

## Intelligence branches and operations

| Public branch | Persistent key | Stored material | Loop operations |
|---|---|---|---|
| Context Intelligence | `context_intelligence` | Questions, methods, checklists, examples, formats, source notes, and evaluation criteria. | search, serve, frame |
| Code Intelligence | `code_intelligence` | Functions, packages, repositories, tools, services, workflows, datasets, and large systems. | search, resolve, invoke, load |
| Runtime History and Solution Intelligence | `runtime_history_solution_intelligence` | Saved runs, decisions, failures, repairs, measurements, comparisons, and Solutions. | search, replay, compare |
| User Feedback Intelligence | `user_feedback_intelligence` | Advice, corrections, sources, constraints, priorities, approvals, and vetoes. | serve, scope, interpret |

A stored record is passive. Searching, selecting, materializing, framing,
invoking, replaying, comparing, and interpreting are work, so those operations
run through Intelligence Loops. Runtime Memory is temporary and is not a fifth
persistent branch.

## Static Architecture capability classes

Static Architecture has three public groups. The work that uses a capability
remains owned by a classified Loop.

| Capability group | Current classes | Source |
|---|---|---|
| Intelligence Search and Retrieval | `Retriever` | [`static_architecture/retrieval.py`](../../src/loop_engine/static_architecture/retrieval.py) |
| Web Research | `BraveWebSearchRequest`, `BraveSearchConfig`, `BraveSearchPlugin` | [`static_architecture/brave_search.py`](../../src/loop_engine/static_architecture/brave_search.py) |
| Custom Plugins | `CapabilityDirectory`, `CapabilityHandshake`, `McpRegistry`, `SkillRegistry` | [`capability_directory.py`](../../src/loop_engine/static_architecture/capability_directory.py), [`mcp_adapter.py`](../../src/loop_engine/static_architecture/mcp_adapter.py), [`skill_registry.py`](../../src/loop_engine/static_architecture/skill_registry.py) |

## Internal runtime mechanics classes

These classes support execution. They are not peer Static Architecture
capability groups.

| Mechanic | Current classes | Source |
|---|---|---|
| Model access and routing | `ModelGateway`, `ModelGatewayConfig`, `ModelGatewayRequest`, `ModelGatewayResult` | [`model_gateway.py`](../../src/loop_engine/static_architecture/model_gateway.py) |
| Typed settings | `RuntimeSettings`, `LoopDefaults`, `ModelSettings` | [`runtime_settings.py`](../../src/loop_engine/static_architecture/runtime_settings.py) |
| Workspace | `WorkspaceBackend`, `WorkspaceSpec`, `RestrictedLocalWorkspace`, `DockerWorkspace` | [`workspace_contracts.py`](../../src/loop_engine/static_architecture/workspace_contracts.py), [`workspace_local.py`](../../src/loop_engine/static_architecture/workspace_local.py), [`workspace_optional.py`](../../src/loop_engine/static_architecture/workspace_optional.py) |
| Effect approval | `EffectApprovalService`, `EffectSpec`, `ApprovalRequest` | [`loop/effect_approval.py`](../../src/loop_engine/loop/effect_approval.py) |
| Large context | `ContextArtifactManager`, `ContextArtifactRef`, `ContextArtifactStoreSpec` | [`context_artifacts.py`](../../src/loop_engine/static_architecture/context_artifacts.py) |
| Runtime Memory | `RunNoteBoard`, `RuntimeMemoryService` | [`runtime_memory.py`](../../src/loop_engine/static_architecture/runtime_memory.py), [`spawned_runtime_port.py`](../../src/loop_engine/loop/spawned_runtime_port.py) |
| Run History | `RunHistory`, `RunHistoryEvent` | [`run_history.py`](../../src/loop_engine/static_architecture/run_history.py) |
| Stores | `SolverStore`, `StoreRecord`, `SolutionLibrary`, `AdviceStore` | [`store_serve.py`](../../src/loop_engine/static_architecture/store_serve.py), [`solution_library.py`](../../src/loop_engine/static_architecture/solution_library.py), [`user_feedback_intelligence.py`](../../src/loop_engine/static_architecture/user_feedback_intelligence.py) |
| Runtime views | `RuntimeObservationServices`, `StudioReadSources` | [`runtime_observer.py`](../../src/loop_engine/static_architecture/runtime_observer.py), [`studio_operational_views.py`](../../src/loop_engine/static_architecture/studio_operational_views.py) |

The target `LoopRuntimeContext` does not exist yet. Every Loop does not yet
receive one common permission-limited set of capability and internal mechanic
ports.

## Public code class map

| Boundary | Current public classes | Source |
|---|---|---|
| Runtime | `Loop`, `LoopConfig`, `LoopLedger`, `LoopResult` | [`loop/recursive_loop.py`](../../src/loop_engine/loop/recursive_loop.py) |
| Role and relationship | `LoopRole`, `LoopRoleIdentity`, `LoopRelationshipKind`, `LoopRelationship` | [`loop/loop_role.py`](../../src/loop_engine/loop/loop_role.py) |
| Profile catalog | `LoopProfileRef`, `LoopProfileSpec` | [`loop/loop_profile_catalog.py`](../../src/loop_engine/loop/loop_profile_catalog.py) |
| Profile binding | `LoopProfileBindingRequest`, `BoundLoopProfile`, `LoopProfileRequirement`, `LoopProfileHandshakeResult` | [`loop/loop_profile_ontology.py`](../../src/loop_engine/loop/loop_profile_ontology.py) |
| Contract and connection | `LoopContract`, `LoopPortBinding`, `LoopConnectionSpec`, `LoopConnectionResult` | [`loop/loop_contract.py`](../../src/loop_engine/loop/loop_contract.py) |
| Discovery reference | `LoopHandshake`, `LoopRef`, `LoopCapsule` | [`loop/loop_capsule.py`](../../src/loop_engine/loop/loop_capsule.py) |
| Spawned lifecycle | `DelegationSpec`, `LoopPortValue`, `SpawnedTaskManager`, `SpawnedExecutionRequest`, `SpawnedLoopResult`, `SpawnedTaskCheckpoint` | [`loop/delegation_runtime.py`](../../src/loop_engine/loop/delegation_runtime.py), [`loop/spawned_task_checkpoint.py`](../../src/loop_engine/loop/spawned_task_checkpoint.py) |
| Restricted spawned runtime | `SpawnedLoopRuntimePort`, `SpawnedLoopRuntimeMemoryPort`, `SpawnedStepRequest` | [`loop/spawned_runtime_port.py`](../../src/loop_engine/loop/spawned_runtime_port.py) |
| Solution declaration | `SolutionLoopSpec`, `SolutionSpec` | [`code_nodes/solution_canvas.py`](../../src/loop_engine/code_nodes/solution_canvas.py) |
| Typed graph | `LoopVertexSpec`, `LoopPortRef`, `LoopEdgeSpec`, `LoopGraphSpec` | [`code_nodes/solution_graph.py`](../../src/loop_engine/code_nodes/solution_graph.py) |
| Candidate matrix | `SolutionLoopCandidate`, `Canvas` | [`loop/canvas.py`](../../src/loop_engine/loop/canvas.py) |

The last three rows are current transitional graph surfaces. They are not
three independent architecture authorities.

## Versioning and handshakes

| Boundary | Current check | Target |
|---|---|---|
| Role profile | `LoopProfileRef` carries a semantic version. `profile_handshake()` checks branch and compatible major version. | Bind every runnable Loop to one exact profile and definition digest. |
| Loop role | `LoopRoleIdentity` binds role, profile ID, and profile version. | Resolve the profile through the catalog during construction. |
| Typed connection | `LoopConnectionSpec` checks declared input and output roles. | Add versioned `PortSpec` schemas and validate values, shapes, units, optionality, and encoding. |
| Capability | `CapabilityHandshake` and `LoopHandshake` describe operations and contracts before invocation. | Add one shared adapter handshake version policy across every service class. |
| Saved run | `RunHistory` stores ordered hash-linked events. | Bind every event to the exact Loop definition and graph definition used for the run. |
| Graph | `LoopGraphSpec` validates current references and edges. | Resolve every vertex through a versioned, digest-bound Loop definition registry. |

## Extension rules

1. Add work by registering a Loop profile or extending an existing profile.
2. Add a public capability under Intelligence Search and Retrieval, Web
   Research, or Custom Plugins. Use a typed handshake and request contract.
3. Add a graph vertex only through an exact Loop definition reference.
4. Add a new intelligence category inside one of the four persistent branches.
   A source format does not create a fifth branch.
5. Keep discovery free of effects. Materialization and execution require
   separate selection, permission, and validation.
6. Version serialized contracts and fail closed on unknown fields or
   incompatible major versions.
7. Keep candidate creation separate from independent review and activation.
8. Add current behavior to the registry and conformance checks before adding
   it to diagrams.

## Anti-conflation rules

| Do not combine | Reason |
|---|---|
| Role and relationship | Practitioner describes purpose. Spawned by describes how one Loop entered the graph. |
| Mode and model tier | Mode describes how work is led. Model tier chooses a configured route for model-using work. |
| Step profile and role profile | Step profile defines sequence. Role profile defines purpose, required fields, capabilities, and supported modes. |
| Loop condition and exit condition | One permits another iteration. The other defines successful completion. |
| Budget and exit | Exhausting a safety limit is not successful completion. |
| Retrieval and execution | A search result grants no authority to run code, call a model, access a network, or change state. |
| Runtime Memory and persistent Intelligence | Runtime Memory lasts for one run. Persistent Intelligence requires classification and independent review. |
| Static Architecture capability and Loop | A capability is reusable. A Loop owns the work that calls it. |
| Static Architecture and internal runtime mechanics | Static Architecture has three public capability groups. Providers, settings, workspaces, stores, history, and viewing remain internal mechanics. |
| Practitioner graph and Solution DAG | One explains how work was built. The other defines what runs for a new input. |
| Candidate staging and activation | A self-improvement Practitioner task cannot approve its own candidates. |

## Current status summary

| Area | Current | Target gap |
|---|---|---|
| Runtime ontology | One public `Loop` class with typed roles and relationships. | Require one complete versioned Loop definition at construction. |
| Modes | Node-level mode policy exists. Physical provider events are available. | Provide standard real hybrid and non-deterministic executors across supported profiles. |
| Intelligence | Four branches and Loop-wrapped search, materialization, invocation, replay, and interpretation paths exist. | Build every path from the same bound Loop definition and avoid mixed relationship events. |
| Solution execution | Deterministic Solution execution fails closed for unsupported modes. | Consolidate graph schemas and add tested model-using Solution adapters only when real. |
| Static Architecture | Three public capability groups use typed objects and extension seams. | Keep the groups closed while improving their handshakes and plugin registration. |
| Internal runtime mechanics | Providers, settings, workspaces, approvals, stores, memory, history, and viewing use typed objects. | Inject one standard permission-limited runtime context into every Loop. |
| Run History | Ordered hash-linked events support reports and playback. | Project the complete semantic relationship DAG and bind it to exact definitions. |
| Documentation | Current public trees use one Loop ontology and exact branch names. | Generate profile and class tables from runtime registries so future drift fails CI. |
