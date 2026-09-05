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
| Scoped managed records | [`RecordOperationPolicy`, `RecordOperationRequest`](../../src/loop_engine/core/record_operations_records.py), [`RecordOperationService`](../../src/loop_engine/core/record_operations.py) | Host schema/scope, exact effect approval, immutable document revisions, atomic current-reference preconditions, retirement, and explicit unknown commit outcomes. Uses existing catalog/artifact authorities; does not migrate Run History. |
| Reactive policy | [`ReactiveLoopProfile`, `OutputPortDefinition`, `PortfolioPolicy`](../../src/loop_engine/loop/reactive_contracts.py) | Independent activation, admission, scheduling, persistence, exploration, portfolio, emission, serving, retention, and liveness settings. |
| Reactive activation | [`ReactiveSeriesDefinition`, `TriggerEnvelope`, `ActivationRecord`, `WorkLease`](../../src/loop_engine/loop/reactive_activation.py) | Stable series identity, finite trigger-bound activations, retries, leases, fencing, and exact Loop definition references. |
| Reactive scheduler and worker | [`SQLiteReactiveScheduler`](../../src/loop_engine/core/reactive_scheduler.py), [`AsyncReactiveWorker`, `CanonicalReactiveExecutor`](../../src/loop_engine/core/reactive_worker.py) | Durable admission and recovery plus asynchronous execution through distinct canonical Loops. |
| Reactive outputs | [`CandidateOutput`, `CandidateEvaluation`, `OutputPortfolioSnapshot`](../../src/loop_engine/loop/reactive_outputs.py), [`SQLiteReactiveOutputStore`](../../src/loop_engine/core/reactive_output_store.py) | Immutable candidate metadata, independent evaluation, policy-versioned rank, append-only history, and read-only current or as-of serving. |
| MCP | [`McpServerSpec`, `McpCallRequest`, `McpRegistry`](../../src/loop_engine/core/mcp_adapter.py), [`McpSdkTransport`, `McpSecretResolver`](../../src/loop_engine/core/mcp_sdk_transport.py) | Typed discovery, argument schemas, exact effects, one-attempt calls, output capture, secret resolution, timeout, and protocol negotiation. |
| Skills | [`SkillManifest`, `SkillDiscoveryProjection`, `SkillAdmissionRecord`, `SkillRegistry`](../../src/loop_engine/core/skill_registry.py) | Standard-compatible new manifests, byte-bounded discovery cards, candidate-only discovery, digest-bound external-review records, lazy instruction loading, and refusal after file changes. The registry does not perform the external review. |
| Passive skill state context | [`SkillExecutionProfile`, `SkillExecutionBinding`, `SkillStateContextRequest`](../../src/loop_engine/core/skill_state_context.py) | Offline-only exact schema, state, observation, history, scope, privacy, materialization-reference, and byte-budget validation. The current product renderer does not consume it. |
| Passive procedural control candidates | [`ProceduralProbeEvidence`, `ProceduralControlAssessment`](../../src/loop_engine/memory/procedural/control_assessment.py) | Records candidate observations for initiation, termination, interruption, outcome devaluation, negative transfer, fresh control, and deliberative fallback. Its strongest status is pending canonical reference resolution. It does not prove packet freshness, assessor independence, fallback availability, or procedure-to-probe binding, and grants no retrieval, execution, or promotion authority. |
| Passive information evidence | [`InformationMeasurementSpec`, `InfrastructureValidityRecord`](../../src/loop_engine/core/information_evidence_contracts.py), [`InformationUpdateEvidence`](../../src/loop_engine/core/information_update_evidence.py), [`PredictiveStateSample`, `EmpiricalPredictiveInformation`](../../src/loop_engine/core/information_theory_evidence.py), [`PairedStatePolicyTrial`, `StatePolicyAssessment`](../../src/loop_engine/core/state_policy_evidence.py) | Computes unissued finite-distribution update quantities, declared base-two discrete plug-in estimates, and paired context-compression operating points from observed candidate records. Predictive and paired records bind population, evaluator, estimator contract, exclusions, minimum valid coverage, absolute loss, and exact occurrences. Information-update calculations do not yet bind a measurement population. External references and validity records are not resolved through canonical Run History, so these records do not establish generalization, causality, or economic benefit. |
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
| External harness | [`HarnessRunRequest`, `HarnessRegistry`, `HarnessServices`](../../src/loop_engine/core/external_harness.py) | Explicit host adapters, exact profile/provider/model identity, provider-backed output maximum, post-run budget assessment, captured output and normalized usage. Completion is not acceptance. |
| Harness mechanics | [`HarnessExecutionCapabilities`, `HarnessExecutionRequirements`](../../src/loop_engine/core/harness_execution_contracts.py) | Refuse missing mechanics, isolation, or requested preemptive limit support before execution. Declarations do not grant authority or qualification. |
| Shared mode policy | [`LoopModePolicy`](../../src/loop_engine/loop/loop_control.py) | All three modes, explicit preference/fallback order, profile/configuration restrictions and executor availability. No model or effect grant. |
| Output capacity and allocation | [`ModelOutputCapability`, `ModelOutputAllocation`](../../src/loop_engine/core/model_capabilities.py) | Source-backed provider capacity stays separate from a typed user/reasoning decision. Unknown capacity and contradictory bindings refuse. |
| Strict token preflight | [`TokenBoundRequest`, `ProviderTokenBound`](../../src/loop_engine/core/model_token_preflight.py) | Validate host-qualified exact-request bounds; no default estimator or independent qualification. Shared session owns accounting. |
| Benchmark comparison | [`LoopEngineBenchmarkEvidence`, `PublishedHarnessMatchReport`](../../src/loop_engine/code_nodes/complex_task_native_evidence.py) | Exact population and evaluator matching between saved Loop Engine results and reviewed published harness evidence. |
| Intelligence reference | [`LoopRef`, `LoopCapsule`](../../src/loop_engine/loop/loop_capsule.py) | Small reference, exact locator, contract, digest, and selected materialization. |
| Event log and saved run | [`LoopLedger`](../../src/loop_engine/loop/recursive_loop.py), [`RunHistory`, `RunHistoryEvent`](../../src/loop_engine/core/run_history.py), [`ProductOutcomeRef`, `SavedRunBundle`](../../src/loop_engine/core/product_outcome_store.py) | Ordered events, definition references, relationship records, distinct positive, missing, partial, and real-zero model usage, digest-bound product outcome, saved playback, and chain checking. |
| User settings | [`RuntimeSettings`, `LoopDefaults`, `LoopConfigOverride`, `ModelSettings`](../../src/loop_engine/core/runtime_settings.py) | Typed defaults and overrides for modes, search, providers, effort, and model routing. |
| Parameter resolution | [`ParameterDefinition`, `ParameterInput`, `ResolvedParameter`](../../src/loop_engine/core/parameter_resolution.py), [`RuntimeSettings.loop_config_with_record()`](../../src/loop_engine/core/runtime_settings.py) | Distinct omitted, null, empty, false, and zero states; exact source precedence; validation; safe value digests; and bounded Intelligence proposals that cannot override explicit values. |
| Prompt resources | [`PromptResourceBundle`, `PromptSlotDefinition`](../../src/loop_engine/strings/prompt_fragments.py) | Versioned component order, typed slots, trust boundaries, provenance, size and omission policy, output schema identity, and exact render digests. |
| Session handoff packet | [`session_handoff/v1`](session-handoff.schema.json) | Immutable generated checkout snapshot with authority digests, exact dirty paths, explicit ownership evidence, scoped test receipts, progressive context loading, and mandatory stale-state checks. It is not architecture authority. |
| Stage-assistance evidence foundation | [`StageOccurrenceIdentity`, `StageRetrievalSnapshot`, `StageExposureManifest`, `StageAssistanceDecision`, `StageTrialOutcome`](../../src/loop_engine/core/stage_evidence_records.py), [`StageAssistanceMaterial`](../../src/loop_engine/core/stage_assistance_material.py), [`StageAssistanceExperimentSpec`, `PairedStageAssistanceTrial`](../../src/loop_engine/core/stage_assistance_experiment.py), [`PublicSolveControlManifest`, `StageControlApplicationCandidate`](../../src/loop_engine/core/solve_control_manifest.py), [`SelectedActionLineageRequest`, `ActionExecutionLineageRequest`, `ActionVerificationLineageRequest`](../../src/loop_engine/core/stage_action_lineage.py), [`SQLiteStageEvidenceProjection`](../../src/loop_engine/core/stage_evidence_projection.py) | Separates activation, semantic-call, and similarity identities. The offline public `solve_task` fixture places digest-bound prior material in the rendered prompt and links one action stage by exact selection, execution, and verification occurrences. Active arms save a pre-run control manifest. The fixture classifies itself as mechanism-only because six controls remain unresolved. The stage control application is an unpopulated candidate, and the same-Practitioner verifier leaves attribution confidence unknown. Canonical per-stage pairs, Run History retrieval, exact control freezing, independent evaluation, live model behavior, and causal benefit remain unproven. |
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

The current learning-integrity extension adds subject-bound
`adaptive_verification/v2` records and
[`AdaptiveEvaluationBindingRequest`](../../src/loop_engine/core/adaptive_practitioner_verification.py).
The adaptive integrator and final-success gate require the matching recorded
evaluation. Rejected, provisional, and unbound attempts remain separate from
the accepted incumbent. This does not establish independent semantic
evaluation or freeze mutable source and artifact bytes.

[`CategoricalForecastScore`](../../src/loop_engine/core/information_update_evidence.py)
recomputes Brier and log losses from a validated finite distribution and
supplied outcome. Temporal order, population, evaluator authority, calibration,
and promotion remain explicitly unproven. The
[`ModelLadderEvidencePolicy`](../../src/loop_engine/core/model_demand.py) is a
per-route bootstrap evidence rule, not a calibrated routing policy.

| Area | Current limit |
|---|---|
| Port types | Connections check named roles. Full value schemas for shapes, units, encodings, optionality, and field constraints are not enforced at every edge. |
| Solution modes | Deterministic, hybrid, and non-deterministic execution require a compatible installed executor; model-enabled modes additionally require exact model authority. Unsupported combinations fail preflight. |
| Constructor migration | Some established calls use observable compatibility composition to produce a complete definition and runtime context. |
| Event-log name | `LoopLedger` remains the internal class name until a versioned migration can preserve saved-run compatibility. |
| Reuse evaluation | The current flywheel proof uses an injected model transport and in-memory artifact. It does not prove live provider quality, production sandboxing, or economic savings. |

See the [taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
for the full ontology and the [drift audit](../architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
for adversarial validation.
