# Taxonomy, ontology, and class map

This page maps the public architecture to the current code. The linked Python
objects are the implementation authority.

## One operational runtime

```text
Operational runtime
└── Loop
    ├── immutable versioned definition
    ├── selected role profile
    ├── selected mode
    ├── typed input and output roles
    ├── loop condition and exit condition
    ├── least-authority runtime context
    ├── relationship to other Loops
    └── ordered Run History events
```

Every executable graph vertex is a `Loop`. A service, file, record, port,
edge, slot, candidate, prompt, package, or report is not an executable graph
vertex.

## Definition, start request, and run instance

```text
LoopDefinition
├── definition_id
├── version
├── content_digest
├── role_profile_id and role_profile_version
├── LoopContract
├── ConfigurationFacts
├── supported_modes
├── installed_executor_modes
├── step_profile
├── loop_condition and exit_condition
├── effects and permissions
└── required_capabilities

LoopStartRequest
├── goal
├── LoopDefinition
├── LoopRelationship
├── LoopRuntimeContext
└── event_log

Loop instance
├── LoopDefinitionRef
├── one selected mode
├── mutable execution state
├── input and output values
└── events bound to the definition identity
```

[`LoopDefinition`](../../src/loop_engine/loop/loop_definition.py) is immutable.
Its canonical JSON determines its SHA-256 content digest. Deserialization
recomputes that digest and refuses changed content. The definition also checks
that the role profile is registered, the contract role matches the profile,
the supported modes stay within the profile, the selected contract mode is
supported, and required capabilities are present.

[`LoopStartRequest`](../../src/loop_engine/loop/loop_definition.py) carries all
public start inputs in one object. [`Loop`](../../src/loop_engine/loop/recursive_loop.py)
registers the definition with the event log and records the exact definition
ID, version, and digest in its lifecycle events.

Some established constructor calls still use an observable compatibility
path. That path composes a complete `LoopDefinition` and `LoopRuntimeContext`
before the Loop starts. It does not create a weaker runtime type.

## Role profile ontology

Profiles classify purpose. They do not describe graph position or selected
mode.

```text
Loop profile ontology
├── Practitioner
│   ├── practitioner.reference_nine_step
│   ├── practitioner.compact_five_step
│   ├── practitioner.research
│   ├── practitioner.solver
│   ├── practitioner.verifier
│   ├── practitioner.self_improvement
│   └── practitioner.code_execution
├── Intelligence
│   ├── intelligence.search
│   ├── intelligence.materialize
│   ├── intelligence.context
│   │   ├── intelligence.context.serve
│   │   ├── intelligence.context.search
│   │   └── intelligence.context.frame
│   ├── intelligence.code
│   │   ├── intelligence.code.resolve
│   │   ├── intelligence.code.invoke
│   │   └── intelligence.code.package
│   ├── intelligence.runtime_history_solution
│   │   ├── intelligence.runtime_history_solution.search
│   │   ├── intelligence.runtime_history_solution.replay
│   │   └── intelligence.runtime_history_solution.compare
│   └── intelligence.user_feedback
│       ├── intelligence.user_feedback.serve
│       ├── intelligence.user_feedback.scope
│       └── intelligence.user_feedback.interpret
└── Solution
    ├── solution.atomic_component
    ├── solution.pipeline
    ├── solution.router_fallback
    ├── solution.ensemble
    └── solution.validator
```

`loop`, `practitioner`, `intelligence`, `solution`, and the four Intelligence
branch entries are abstract. All leaf entries above are registered profiles.
The catalog does not register separate experimenter, builder, reviewer,
repairer, output-formatter, or ensemble-member profiles.

[`LoopProfileSpec`](../../src/loop_engine/loop/loop_profile_catalog.py) stores
the profile version, parent, state, step template, allowed modes, required
fields, required capabilities, and thinking-power policy.
[`resolve_profile()`](../../src/loop_engine/loop/loop_profile_ontology.py)
resolves inherited requirements. [`bind_profile()`](../../src/loop_engine/loop/loop_profile_ontology.py)
checks the requested contract and mode policy before creating runtime
configuration.

Self-improvement is `practitioner.self_improvement`. It is a Practitioner task,
not a fourth Loop role.

## Modes and executors

The runtime defines three modes:

| Mode | Work leader |
|---|---|
| `deterministic` | Code, rules, retrieval, or an executable capability. |
| `hybrid` | Code, with a bounded language-model step when permitted. |
| `non_deterministic` | A language model leads semantic work under Loop controls. |

These fields remain separate:

```text
Role profile       -> what the Loop is for
Supported modes    -> what the definition may select
Installed executors -> what this runtime can physically execute
Selected mode      -> how this Loop instance runs
Thinking power     -> a model-routing setting for an authorized model mode
Permissions        -> effects and resources the Loop may use
```

A semantic mode without an installed executor fails before work. Mode does
not grant authority.

## Loop relationships

[`LoopRelationship`](../../src/loop_engine/loop/loop_role.py) records one of
five relationship kinds:

| Kind | Meaning |
|---|---|
| `STARTING` | This Loop has no incoming Loop relationship. |
| `SPAWNED_BY` | A Loop created dynamic bounded work. |
| `QUERIED_BY` | A Loop sent an Intelligence query. |
| `RETRIEVED_BY` | An Intelligence query selected this Intelligence item. |
| `CONNECTED_FROM` | One or more typed DAG edges supplied input values. |

Relationship does not imply role or mode. A deterministic Practitioner may
spawn a non-deterministic research Practitioner. A non-deterministic
Practitioner may spawn a deterministic verifier. A Solution pipeline normally
uses `CONNECTED_FROM`; it uses `SPAWNED_BY` only for a real dynamic branch,
fallback, repair, or ensemble action.

## Runtime context and Static Architecture

[`LoopRuntimeContext`](../../src/loop_engine/loop/runtime_context.py) gives one
Loop an explicit least-authority service context.

```text
LoopRuntimeContext
├── IntelligenceSearchRetrievalPort
├── WebResearchPort
├── CustomPluginsPort
└── InternalRuntimeMechanics
    ├── internal service bindings
    ├── permissions
    └── installed mode executors
```

The first three ports are the only public Static Architecture groups.
`LoopRuntimeContext.require()` refuses missing capabilities, permissions, or
executors. `derive()` can remove authority but cannot add it.

Provider routing, settings, workspaces, approvals, stores, Runtime Memory,
event persistence, reports, playback, MCP, skills, and trace export remain
inside `InternalRuntimeMechanics`. The work that calls one of these mechanisms
still runs in a classified Loop.

## Authoritative graph

[`LoopGraphDefinition`](../../src/loop_engine/code_nodes/solution_graph.py) is
the authoritative static DAG definition.

```text
LoopGraphDefinition
├── graph_id, version, and content_digest
├── LoopDefinitionRegistry
├── LoopGraphVertex records
├── LoopGraphEdge records
├── graph input and output ports
├── stage and composition groups
├── starting vertex and starting group
└── permitted_vertex_modes policy
```

Each `LoopGraphVertex` contains an exact `LoopDefinitionRef`, selected mode,
operation reference, relationship, and immutable parameters. Each edge names
source and target ports. An incompatible connection must name an explicit
Adapter Loop vertex. An edge never transforms data by itself.

Graph validation checks:

- definition identity and digest;
- selected mode and installed executor coverage;
- role-compatible relationships;
- typed input and output roles;
- acyclic execution order;
- declared graph inputs and outputs;
- stage, route, fallback, and group membership;
- exact graph digest after serialization.

`SolutionSpec` projects one graph or graph group into the Solution API.
`Canvas` organizes passive Solution candidates before selection. Neither is a
second execution authority.

Practitioner execution creates a dynamic graph recorded through Loop
relationships and ordered events. The reusable Solution DAG is a static
`LoopGraphDefinition` validated before execution. These views serve different
purposes, but both use `Loop` as the only executable vertex type.

## Intelligence branches

```text
Persistent intelligence
├── Context Intelligence
│   └── serve, search, frame
├── Code Intelligence
│   └── resolve, invoke, load package or repository
├── Runtime History and Solution Intelligence
│   └── search, replay, compare
└── User Feedback Intelligence
    └── serve, scope, interpret
```

Cross-layer search uses `intelligence.search`. Loading a selected reference
uses `intelligence.materialize`. Search results are small `LoopRef` objects.
The selected body is loaded after reference, digest, contract, and permission
checks.

Runtime Memory is temporary. It is not a fifth persistent layer.

## Class map

| Concept | Current class or function | Authority |
|---|---|---|
| Immutable Loop definition | `LoopDefinition`, `LoopDefinitionRef`, `ConfigurationFacts` | [`loop_definition.py`](../../src/loop_engine/loop/loop_definition.py) |
| Start boundary | `LoopStartRequest` | [`loop_definition.py`](../../src/loop_engine/loop/loop_definition.py) |
| Operational runtime | `Loop`, `LoopConfig`, `LoopResult` | [`recursive_loop.py`](../../src/loop_engine/loop/recursive_loop.py) |
| Role and relationship | `LoopRoleIdentity`, `LoopRelationship` | [`loop_role.py`](../../src/loop_engine/loop/loop_role.py) |
| Typed Loop contract | `LoopContract`, `LoopConnectionSpec`, `validate_loop_connection()` | [`loop_contract.py`](../../src/loop_engine/loop/loop_contract.py) |
| Role profile | `LoopProfileRef`, `LoopProfileSpec`, `bind_profile()` | [`loop_profile_catalog.py`](../../src/loop_engine/loop/loop_profile_catalog.py) and [`loop_profile_ontology.py`](../../src/loop_engine/loop/loop_profile_ontology.py) |
| Least-authority services | `LoopRuntimeContext`, three public port classes, `InternalRuntimeMechanics` | [`runtime_context.py`](../../src/loop_engine/loop/runtime_context.py) |
| Static DAG | `LoopGraphDefinition`, `LoopGraphVertex`, `LoopGraphEdge`, `LoopDefinitionRegistry` | [`solution_graph.py`](../../src/loop_engine/code_nodes/solution_graph.py) |
| Solution definition builder | `SolutionSpec`, `SolutionLoopSpec` | [`solution_canvas.py`](../../src/loop_engine/code_nodes/solution_canvas.py) |
| Solution candidate matrix | `Canvas`, `SolutionSlot`, `SolutionLoopCandidate` | [`canvas.py`](../../src/loop_engine/loop/canvas.py) |
| Intelligence reference | `LoopRef`, `LoopCapsule` | [`loop_capsule.py`](../../src/loop_engine/loop/loop_capsule.py) |
| Spawned work | `SpawnedTaskManager`, `DelegationSpec`, `SpawnedLoopRuntimePort` | [`delegation_runtime.py`](../../src/loop_engine/loop/delegation_runtime.py) |
| Ordered event log | `LoopLedger` | [`recursive_loop.py`](../../src/loop_engine/loop/recursive_loop.py) |
| Saved run | `RunHistory`, `RunHistoryEvent` | [`run_history.py`](../../src/loop_engine/static_architecture/run_history.py) |

## Separation rules

1. Runtime type is always `Loop`.
2. Role does not determine relationship, mode, or step profile.
3. A graph policy may restrict member modes but does not own one mode.
4. A passive candidate becomes executable only through a complete
   `LoopDefinition` and graph vertex.
5. A service call is not a graph vertex. The classified Loop that owns the
   call is the vertex.
6. A graph edge carries a typed value. A conversion requires an Adapter Loop.
7. Runtime Memory is not persistent intelligence.
8. Self-improvement can stage candidates but cannot approve them.
9. Saved legacy records may use explicit compatibility readers. New records
   use current relationship and definition fields.

## Current limits

- Typed role names are checked at connections. Full value-schema enforcement
  for units, shapes, encodings, and field constraints is not available at
  every port.
- The built-in Solution runner executes deterministic leaves only. Hybrid and
  non-deterministic Solution executors are not installed.
- Some established constructor calls still use observable compatibility
  composition for a definition and runtime context.
- `LoopLedger` remains the internal event-log class name until a versioned
  public migration can preserve saved-run compatibility.
