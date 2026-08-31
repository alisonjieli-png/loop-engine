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
| Runtime services | [`LoopRuntimeContext`, `InternalRuntimeMechanics`](../../src/loop_engine/loop/runtime_context.py) | Three public Core Architecture ports, internal bindings, permissions, capabilities, and installed mode executors. |
| Static DAG | [`LoopGraphDefinition`, `LoopGraphVertex`, `LoopGraphEdge`, `LoopDefinitionRegistry`](../../src/loop_engine/code_nodes/solution_graph.py) | Exact definition references, graph digest, typed edges, acyclic order, adapters, relationships, graph ports, groups, and member-mode policy. |
| Solution builder | [`SolutionSpec`, `SolutionLoopSpec`](../../src/loop_engine/code_nodes/solution_canvas.py) | Builds and projects Solution graph groups without becoming a second graph authority. |
| Candidate matrix | [`Canvas`, `SolutionSlot`, `SolutionLoopCandidate`](../../src/loop_engine/loop/canvas.py) | Keeps alternatives passive, requires complete Solution definitions, checks compatible slots, and projects selected work into a graph. |
| Spawned work | [`DelegationSpec`, `SpawnedTaskManager`, `SpawnedLoopRuntimePort`](../../src/loop_engine/loop/delegation_runtime.py) | Typed values, private context, bounded authority, lifecycle control, cancellation, and durable task metadata. |
| Effect approval | [`EffectSpec`, `ApprovalRequest`, `EffectApprovalService`](../../src/loop_engine/loop/effect_approval.py) | One exact effect, durable decision state, one-use consumption, and refusal after replay or argument drift. |
| Workspace execution | [`WorkspaceSpec`, `FileRequest`, `CommandRequest`](../../src/loop_engine/core/workspace_contracts.py), [`WorkspaceOperationService`](../../src/loop_engine/core/workspace_operations.py) | Confined paths, explicit command policy, exact approval binding, bounded output, and backend-neutral results. |
| Context artifacts | [`ContextArtifactRef`, `ContextArtifactManager`, `CompactionRequest`](../../src/loop_engine/core/context_artifacts.py) | Digest-addressed raw storage, policy-based offloading, separate compacted artifacts, and Loop-owned compaction. |
| Storage-neutral Loop values | [`LoopValueRef`, `InformationStorageBinding`, `InformationResolver`](../../src/loop_engine/core/information_access.py) | One exact value identity across inline, content-addressed file, and SQLite materializations, with scope, permission, size, and digest checks. |
| Reactive policy | [`ReactiveLoopProfile`, `OutputPortDefinition`, `PortfolioPolicy`](../../src/loop_engine/loop/reactive_contracts.py) | Independent activation, admission, scheduling, persistence, exploration, portfolio, emission, serving, retention, and liveness settings. |
| Reactive activation | [`ReactiveSeriesDefinition`, `TriggerEnvelope`, `ActivationRecord`, `WorkLease`](../../src/loop_engine/loop/reactive_activation.py) | Stable series identity, finite trigger-bound activations, retries, leases, fencing, and exact Loop definition references. |
| Reactive scheduler and worker | [`SQLiteReactiveScheduler`](../../src/loop_engine/core/reactive_scheduler.py), [`AsyncReactiveWorker`, `CanonicalReactiveExecutor`](../../src/loop_engine/core/reactive_worker.py) | Durable admission and recovery plus asynchronous execution through distinct canonical Loops. |
| Reactive outputs | [`CandidateOutput`, `CandidateEvaluation`, `OutputPortfolioSnapshot`](../../src/loop_engine/loop/reactive_outputs.py), [`SQLiteReactiveOutputStore`](../../src/loop_engine/core/reactive_output_store.py) | Immutable candidate metadata, independent evaluation, policy-versioned rank, append-only history, and read-only current or as-of serving. |
| MCP | [`McpServerSpec`, `McpCallRequest`, `McpRegistry`](../../src/loop_engine/core/mcp_adapter.py), [`McpSdkTransport`, `McpSecretResolver`](../../src/loop_engine/core/mcp_sdk_transport.py) | Typed discovery, argument schemas, exact effects, one-attempt calls, output capture, secret resolution, timeout, and protocol negotiation. |
| Skills | [`SkillManifest`, `SkillAdmissionRecord`, `SkillRegistry`](../../src/loop_engine/core/skill_registry.py) | Candidate-only discovery, digest-bound independent admission, lazy instruction loading, and refusal after file changes. |
| Reusable Code asset admission | [`CodeAssetSpec`, `CodeAssetAdmissionRecord`](../../src/loop_engine/core/code_intelligence_assets.py) | Immutable body reference plus exact artifact, dependency, contract, effect, producer, verifier, and evidence binding. |
| Reusable capability lifecycle | [`CapabilityAuthority`](../../src/loop_engine/core/reusable_capability_flywheel.py) | Candidate isolation, independent qualification, explicit promotion, immutable transition records, quarantine, and versioned repair. |
| Capability resolution and invocation | [`CapabilityNeed`, `CapabilityResolutionPlan`](../../src/loop_engine/core/reusable_capability_records.py), [`CapabilityResolver`](../../src/loop_engine/core/reusable_capability_resolution.py) | Rebuildable projection search, hard eligibility before ranking, exact active-state recheck, zero-model deterministic invocation, and output verification. |
| Hybrid capability assistance | [`HybridAssistanceProfile`, `run_hybrid_assistance_as_loop`](../../src/loop_engine/core/reusable_capability_hybrid.py) | Bounded structured normalization, reranking, adaptation, diagnosis, repair, or composition under the existing hybrid mode. |
| Semantic Loop contract | [`SemanticLoopContractDraft`, `SemanticLoopContract`](../../src/loop_engine/core/semantic_runtime_records.py), [`bind_semantic_loop_contract`](../../src/loop_engine/core/semantic_runtime.py) | Complete implementation-independent behavior whose specification digest is bound into one exact `LoopDefinition`. |
| Semantic realization and interpreter | [`SemanticRealizationBinding`, `SemanticInterpreterProfile`](../../src/loop_engine/core/semantic_runtime_records.py), [`select_semantic_realization`](../../src/loop_engine/core/semantic_runtime.py) | Exact qualified deterministic, hybrid, or direct semantic realization under the three existing modes. |
| Semantic trust transition | [`SemanticCandidateOutput`, `ProposedStateDelta`, `SemanticVerificationRecord`, `SemanticEffectAuthorization`, `SemanticExecutionRecord`](../../src/loop_engine/core/semantic_runtime_records.py), [`CatalogTrustedSemanticState`](../../src/loop_engine/core/semantic_state.py) | Candidate-only model output, issued verification, issued effect authorization, stale-state refusal, idempotency, compare-and-swap commit, and complete ProgramID evidence. |
| Plugin bundles | [`PluginBundleManifest`, `ResolvedPluginSnapshot`](../../src/loop_engine/core/plugin_bundles.py) | Passive distribution, exact admitted-skill composition, deterministic conflict refusal, full-content drift detection, and shared JSON/ASCII projections. |
| Added-file extensions | [`ExtensionDiscoveryRequest`, `ExtensionSnapshot`, `ProviderRouteBundle`, `CapabilityCandidate`](../../src/loop_engine/core/extension_discovery.py) | Conventional project/user roots, exact file digests, provider-route composition, candidate-only capabilities and intelligence, existing skill/plugin authority, and fail-closed identity conflicts. |
| OpenTelemetry | [`RawLedgerEvents`, `OtelSpanRecord`, `OpenTelemetrySpanExporter`](../../src/loop_engine/core/otel_export.py) | Verified Run History projection, explicit unverified compatibility, parented spans, safe attributes, and refusal of non-recording tracers. |
| External harness | [`HarnessRunRequest`, `HarnessRuntimeBinding`, `HarnessServices`](../../src/loop_engine/core/external_harness.py) | Exact provider and model identity, provider-backed output maximum, hard budgets, output artifacts, normalized usage, and independent acceptance. |
| Benchmark comparison | [`LoopEngineBenchmarkEvidence`, `PublishedHarnessMatchReport`](../../src/loop_engine/code_nodes/complex_task_native_evidence.py) | Exact population and evaluator matching between saved Loop Engine results and reviewed published harness evidence. |
| Intelligence reference | [`LoopRef`, `LoopCapsule`](../../src/loop_engine/loop/loop_capsule.py) | Small reference, exact locator, contract, digest, and selected materialization. |
| Event log and saved run | [`LoopLedger`](../../src/loop_engine/loop/recursive_loop.py), [`RunHistory`, `RunHistoryEvent`](../../src/loop_engine/core/run_history.py), [`ProductOutcomeRef`, `SavedRunBundle`](../../src/loop_engine/core/product_outcome_store.py) | Ordered events, definition references, relationship records, digest-bound product outcome, saved playback, and chain checking. |
| User settings | [`RuntimeSettings`, `LoopDefaults`, `LoopConfigOverride`, `ModelSettings`](../../src/loop_engine/core/runtime_settings.py) | Typed defaults and overrides for modes, search, providers, effort, and model routing. |
| Parameter resolution | [`ParameterDefinition`, `ParameterInput`, `ResolvedParameter`](../../src/loop_engine/core/parameter_resolution.py), [`RuntimeSettings.loop_config_with_record()`](../../src/loop_engine/core/runtime_settings.py) | Distinct omitted, null, empty, false, and zero states; exact source precedence; validation; safe value digests; and bounded Intelligence proposals that cannot override explicit values. |
| Prompt resources | [`PromptResourceBundle`, `PromptSlotDefinition`](../../src/loop_engine/strings/prompt_fragments.py) | Versioned component order, typed slots, trust boundaries, provenance, size and omission policy, output schema identity, and exact render digests. |
| Public solve | [`SolveRequest`, `SolveOutcome`, `SolveTerminalCode`, `MaterialQuestion`](../../src/loop_engine/code_nodes/solve_runtime.py) | Immutable original task intake, answerable material questions, authorized model and effect calls, verified artifact records, workspace, Run History, and one honest terminal code. |

## Public Core Architecture ports

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
| Reuse evaluation | The current flywheel proof uses an injected model transport and in-memory artifact. It does not prove live provider quality, production sandboxing, or economic savings. |

See the [taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
for the full ontology and the [drift audit](../architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
for adversarial validation.
