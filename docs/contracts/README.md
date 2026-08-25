# Contract index

The linked Python objects define current behavior. This page shows how the
objects fit together without creating another specification.

## Core contract chain

```text
LoopDefinition
  -> LoopDefinitionRef
  -> LoopStartRequest
  -> Loop

LoopGraphDefinition
  -> LoopGraphVertex with exact LoopDefinitionRef
  -> LoopGraphEdge with named typed roles
  -> validated execution order
```

## Contract map

| Boundary | Current authority | What it enforces |
|---|---|---|
| Loop definition | [`LoopDefinition`, `LoopDefinitionRef`, `ConfigurationFacts`](../../src/loop_engine/loop/loop_definition.py) | Semantic version, content digest, registered role profile, mode support, installed executors, step profile, conditions, effects, permissions, and required capabilities. |
| Loop start | [`LoopStartRequest`](../../src/loop_engine/loop/loop_definition.py) | Goal, complete definition, relationship, least-authority runtime context, and event log in one object. |
| Runtime | [`Loop`, `LoopConfig`, `LoopResult`](../../src/loop_engine/loop/recursive_loop.py) | One operational runtime, selected mode, lifecycle, nested work, conditions, and definition-bound events. |
| Role and relationship | [`LoopRoleIdentity`, `LoopRelationship`](../../src/loop_engine/loop/loop_role.py) | Practitioner, Intelligence, or Solution role plus Starting, Spawned by, Queried by, Retrieved by, or Connected from relationship. |
| Profile | [`LoopProfileRef`, `LoopProfileSpec`](../../src/loop_engine/loop/loop_profile_catalog.py), [`bind_profile()`](../../src/loop_engine/loop/loop_profile_ontology.py) | Exact profile version, inheritance, required fields, required capabilities, allowed modes, step template, and thinking-power policy. |
| Typed Loop ports | [`LoopContract`, `LoopPortBinding`, `LoopConnectionSpec`](../../src/loop_engine/loop/loop_contract.py) | Named input and output roles, effects, role identity, and connection compatibility. |
| Runtime services | [`LoopRuntimeContext`, `InternalRuntimeMechanics`](../../src/loop_engine/loop/runtime_context.py) | Three public Static Architecture ports, internal bindings, permissions, capabilities, and installed mode executors. |
| Static DAG | [`LoopGraphDefinition`, `LoopGraphVertex`, `LoopGraphEdge`, `LoopDefinitionRegistry`](../../src/loop_engine/code_nodes/solution_graph.py) | Exact definition references, graph digest, typed edges, acyclic order, adapters, relationships, graph ports, groups, and member-mode policy. |
| Solution builder | [`SolutionSpec`, `SolutionLoopSpec`](../../src/loop_engine/code_nodes/solution_canvas.py) | Builds and projects Solution graph groups without becoming a second graph authority. |
| Candidate matrix | [`Canvas`, `SolutionSlot`, `SolutionLoopCandidate`](../../src/loop_engine/loop/canvas.py) | Keeps alternatives passive, requires complete Solution definitions, checks compatible slots, and projects selected work into a graph. |
| Spawned work | [`DelegationSpec`, `SpawnedTaskManager`, `SpawnedLoopRuntimePort`](../../src/loop_engine/loop/delegation_runtime.py) | Typed values, private context, bounded authority, lifecycle control, cancellation, and durable task metadata. |
| Effect approval | [`EffectSpec`, `ApprovalRequest`, `EffectApprovalService`](../../src/loop_engine/loop/effect_approval.py) | One exact effect, durable decision state, one-use consumption, and refusal after replay or argument drift. |
| Workspace execution | [`WorkspaceSpec`, `FileRequest`, `CommandRequest`](../../src/loop_engine/static_architecture/workspace_contracts.py), [`WorkspaceOperationService`](../../src/loop_engine/static_architecture/workspace_operations.py) | Confined paths, explicit command policy, exact approval binding, bounded output, and backend-neutral results. |
| Context artifacts | [`ContextArtifactRef`, `ContextArtifactManager`, `CompactionRequest`](../../src/loop_engine/static_architecture/context_artifacts.py) | Digest-addressed raw storage, policy-based offloading, separate compacted artifacts, and Loop-owned compaction. |
| MCP | [`McpServerSpec`, `McpCallRequest`, `McpRegistry`](../../src/loop_engine/static_architecture/mcp_adapter.py), [`McpSdkTransport`, `McpSecretResolver`](../../src/loop_engine/static_architecture/mcp_sdk_transport.py) | Typed discovery, argument schemas, exact effects, one-attempt calls, output capture, secret resolution, timeout, and protocol negotiation. |
| Skills | [`SkillManifest`, `SkillAdmissionRecord`, `SkillRegistry`](../../src/loop_engine/static_architecture/skill_registry.py) | Candidate-only discovery, digest-bound independent admission, lazy instruction loading, and refusal after file changes. |
| OpenTelemetry | [`RawLedgerEvents`, `OtelSpanRecord`, `OpenTelemetrySpanExporter`](../../src/loop_engine/static_architecture/otel_export.py) | Verified Run History projection, explicit unverified compatibility, parented spans, safe attributes, and refusal of non-recording tracers. |
| External harness | [`HarnessRunRequest`, `HarnessRuntimeBinding`, `HarnessServices`](../../src/loop_engine/static_architecture/external_harness.py) | Exact provider and model identity, provider-backed output maximum, hard budgets, output artifacts, normalized usage, and independent acceptance. |
| Benchmark comparison | [`LoopEngineBenchmarkEvidence`, `PublishedHarnessMatchReport`](../../src/loop_engine/code_nodes/complex_task_native_evidence.py) | Exact population and evaluator matching between saved Loop Engine results and reviewed published harness evidence. |
| Intelligence reference | [`LoopRef`, `LoopCapsule`](../../src/loop_engine/loop/loop_capsule.py) | Small reference, exact locator, contract, digest, and selected materialization. |
| Event log and saved run | [`LoopLedger`](../../src/loop_engine/loop/recursive_loop.py), [`RunHistory`, `RunHistoryEvent`](../../src/loop_engine/static_architecture/run_history.py) | Ordered events, definition references, relationship records, saved playback, and chain checking. |
| User settings | [`RuntimeSettings`, `LoopDefaults`, `LoopConfigOverride`, `ModelSettings`](../../src/loop_engine/static_architecture/runtime_settings.py) | Typed defaults and overrides for modes, search, providers, effort, and model routing. |

## Public Static Architecture ports

`LoopRuntimeContext` contains exactly three public capability ports:

```text
LoopRuntimeContext
├── IntelligenceSearchRetrievalPort
├── WebResearchPort
├── CustomPluginsPort
└── InternalRuntimeMechanics
```

Internal mechanics include providers, settings, workspaces, approvals, stores,
Runtime Memory, event persistence, MCP, skills, reports, playback, and trace
export. They are not additional public capability groups.

## Definition and graph identity

A definition reference contains:

```text
definition_id + version + content_digest
```

A graph contains its own semantic version and content digest. Every executable
vertex resolves an exact definition reference through the graph registry.
Changing a definition, vertex, edge, group, parameter, or graph policy changes
the graph digest.

## Current limits

| Area | Current limit |
|---|---|
| Port types | Connections check named roles. Full value schemas for shapes, units, encodings, optionality, and field constraints are not enforced at every edge. |
| Solution modes | The in-process Solution runner installs deterministic leaf execution only. Hybrid and non-deterministic leaves fail preflight. |
| Constructor migration | Some established calls use observable compatibility composition to produce a complete definition and runtime context. |
| Event-log name | `LoopLedger` remains the internal class name until a versioned migration can preserve saved-run compatibility. |

See the [taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
for the full ontology and the [drift audit](../architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
for adversarial validation.
