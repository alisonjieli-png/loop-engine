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
| Solutions space | [`SolutionsSpaceRecord`, `SolutionsSpaceMember`](../../src/loop_engine/code_nodes/solutions_space.py) | Plural, append-only published solutions for one task; a member is verified only by citing a passed independent report; supersession names a successor and removes nothing. |
| Model ontology | [`ModelProfile`, `validate_tool_model_use`](../../src/loop_engine/core/model_ontology.py) | Closed vocabularies for model kind, determinism, placement, size class, provenance, modalities, output kinds, and qualification; a tool embeds only a small in-process model and calls anything larger as a service. |
| Model call | [`ModelCallRequest`, `ModelInput`, `ModelCallRecord`](../../src/loop_engine/core/model_call_contract.py) | One typed request for every model kind; a text-servable request becomes the text invocation and any other kind is refused by name; records keep digests and leave unknown counts unknown. |
| Suggested output | [`SuggestedOutput`](../../src/loop_engine/core/suggested_output.py) | The shape a step asks for, rendered into the packet, recorded beside the call, and checked deterministically; a deviation is a diagnostic, never a task failure. |
| Contract matching | [`ContractMatchPolicy`, `match_contract`](../../src/loop_engine/core/contract_matching.py) | Every contract names its matching mode: exact, canonical, purpose, semantic with blocking keys, or model judged; the decisive keys stay exact inside the looser modes, and a model judged match decides nothing by itself. |
| Reuse evidence | [`ReuseEvidence`, `ReuseEvidencePolicy`, `apply_outcome`](../../src/loop_engine/core/reuse_evidence.py) | How a verified outcome changes what a reused record is worth: surprise weighted, credit split, decayed, with first-strike tolerance and a regime-shift event; labels are evidence, never promotion. |
| Learning records | [`ModelCallLearningRecord`, `TrainingExportPolicy`, `export_training_rows`](../../src/loop_engine/core/model_call_records.py) | One record per model call labeled by the independent outcome; the export splits by run, excludes unverified, incomplete, synthetic, and secret-bearing rows by name. |
| Step efficiency review | [`EfficiencyReview`, `SizeExpectation`, `EfficiencyAlternative`, `deterministic_efficiency_judge`](../../src/loop_engine/core/step_efficiency_review.py) | Before a step spends anything: input and output sizes against the declared expectation, the alternatives with a confidence each, the chosen one, and the judge kind (deterministic, specialist, model); the record and its training row carry digests and sizes, never text. |
| Heuristic adoption and training data | [`DatasetVersion`, `TrainingDataStore`, `HeuristicProposal`, `HeuristicAdoptionPolicy`](../../src/loop_engine/core/heuristic_adoption.py) | Training exports publish as immutable dataset versions inside the catalog; a heuristic beyond an exact atomic fingerprint is adopted only when the declared run count (one million by default) is reached and the dataset version it was learned from is published. |
| Implementation choice | [`ImplementationCandidate`, `ImplementationPolicy`, `ImplementationDecision`, `choose_implementation`, `decision_for_escalation`](../../src/loop_engine/core/implementation_choice.py) | The model-versus-not decision for one operation: the cheapest candidate that meets the verified rate over enough samples wins; without evidence the declared fallback order decides and the reason says so; an escalation records the model as the next implementation with the confidence that fell short. |
| Specialist training | [`SpecialistSpec`, `SpecialistModel`, `train_specialist`, `SpecialistResolver`](../../src/loop_engine/core/specialist_training.py) | A bounded classifier trained from recorded rows with a run-level split, measured only on held-out runs, exported as JSON weights, and registered as a candidate resolver that never claims verification. |
| Operation cost capture | [`OperationCostCapture`, `cheapest_implementation`](../../src/loop_engine/core/operation_cost_capture.py) | Phases timed by a monotonic clock, unknown counts kept unknown, one record per implementation of one operation written to the ledger; the cheapest verified implementation named with the ranking it beat. |
| Temporal facts | [`TemporalFact`, `FactGraph`](../../src/loop_engine/core/temporal_facts.py) | Typed triples with validity intervals, confidence, and source stored as Context Intelligence catalog records; functional predicates refuse an overlapping different object; supersession closes an interval and names the successor; as-of, history, neighbors, and paths respect validity; nothing is deleted. |
| Record versioning | [`RecordRevision`, `revise`, `history`, `diff`, `rollback`](../../src/loop_engine/catalog/versioning.py) | Every previous version kept as an immutable revision record in the same store; a revision needs the version last read and a higher version; rollback is a new version that names its origin; ordinary lifecycle queries never see revisions. |
| Shared memory scopes | [`SharedMemoryScope`, `SharedMemory`, `SharedWrite`](../../src/loop_engine/core/shared_memory_scopes.py) | Scoped writes carry writer identity, scope, and time; non-members are refused; a stale concurrent write is refused by the version last read; reads are filtered by membership and visibility and show who wrote each record. |
| Text conformance | [`ExceptionCatalogLayer`, `ConformanceRule`, `ConformancePolicy`, `CorrectionRecord`, `EscalationRequest`, `ConformanceReport`, `TextConformanceResolver`](../../src/loop_engine/code_nodes/text_conformance.py) | Deterministic text corrections with a confidence that is the weakest named signal; five exception layers merged in precedence order; apply, hold, and escalate thresholds; escalation requests bound to a question form and a registered response contract that perform no call; a resolver that supports only a typed task record and verifies only a complete, idempotent pass. |
| Solution export | [`SolutionExportSpec`, `ExportedFile`, `ContainerSpec`, `export_solution`, `verify_export`, `ExportVerification`](../../src/loop_engine/code_nodes/solution_export.py) | A standalone package with sources, entry point, tests, a digest per file, a Dockerfile, and a Kubernetes Job; refuses traversal, absolute paths, `loop_engine` imports, secret-shaped text, and non-empty targets; verification runs in an isolated interpreter that cannot import `loop_engine`. |
| Operation cost | [`OperationCostRecord`, `OperationCostLedger`](../../src/loop_engine/core/operation_cost_records.py) | Phase costs per implementation of one operation; unknowns stay unknown; the comparison ranks only verified complete records. |
| Response contracts | [`ResponseContract`, `registered_contract`](../../src/loop_engine/core/response_contracts.py) | Named, versioned JSON shapes whose enumerations come from the validating vocabularies; a model step names the contract it used. |
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
| External harness | [`HarnessRunRequest`, `HarnessRegistry`, `HarnessServices`, `HarnessRunResult`](../../src/loop_engine/core/external_harness.py) | Explicit host adapters, exact profile/provider/model identity, provider-backed output maximum, post-run budget assessment, captured output, normalized usage, and an owning-Loop `outcome_vector/v2`. Adapter completion sets only the mechanical execution axis. It is not task acceptance. |
| Harness mechanics | [`HarnessExecutionCapabilities`, `HarnessExecutionRequirements`](../../src/loop_engine/core/harness_execution_contracts.py) | Refuse missing mechanics, isolation, or requested preemptive limit support before execution. Declarations do not grant authority or qualification. |
| Per-step harness recovery | [`HarnessFallbackPolicy`](../../src/loop_engine/core/harness_fallback.py), [`HarnessSemanticBinding`](../../src/loop_engine/core/harness_semantic.py) | Explicit ordered alternatives, fresh attempt Loops, shared authority and accounting, exact semantic-packet identity, and refusal to replay uncertain effects. Recovery stops at an admitted proposal, not task acceptance. |
| Observation expectations | [`ObservationExpectation`, `ObservationBinding`](../../src/loop_engine/core/observation_expectations.py), [`ModelInvocationRequest`](../../src/loop_engine/code_nodes/solution_model_port.py) | Exact operation and input binding, structural response admission, and recorded mismatches. Semantic uncertainty still needs independent review. |
| Action intent and outcome vectors | [`ActionIntentVector`, `OutcomeVector`, `OutcomeVectorPolicy`](../../src/loop_engine/core/outcome_vector.py), [`ActionVectorAssessment`](../../src/loop_engine/core/action_vector_assessment.py), [`ActionVectorRouteDecision`](../../src/loop_engine/core/action_vector_routing.py) | Every selected action binds its intended direction, expected delta, check, fallback, and decision coordinates. Every semantic stage retains separate tri-valued response-admission, observable-process, execution, output, verification, progress, continuation, use, branch, invalidation, and task signals. Unknown is not false. Private reasoning is not recorded. A separate pure guard rejects a normal stop while safe authorized continuation remains. |
| Cognitive response contract | [`ModelResponseContract`](../../src/loop_engine/core/model_response_admission.py), [`ModelStepRequest`](../../src/loop_engine/core/adaptive_practitioner_records.py) | Versioned schema and explicit normalization, bound before dispatch. Action and method constraints reach the actual response validator, and rejected-response feedback stays separate from transport recovery. |
| Recovery learning capture | [`capture_recovery_learning`](../../src/loop_engine/core/recovery_learning.py) | Opt-in self-improvement Loop, shared model and harness authority, explicit task-local or candidate disposition, and an unvalidated LearningBundle in the existing artifact store. No active intelligence update or self-promotion. |
| Shared mode policy | [`LoopModePolicy`](../../src/loop_engine/loop/loop_control.py) | All three modes, explicit preference/fallback order, profile/configuration restrictions and executor availability. No model or effect grant. |
| Output capacity and allocation | [`ModelOutputCapability`, `ModelOutputAllocation`](../../src/loop_engine/core/model_capabilities.py) | Source-backed provider capacity stays separate from a typed user/reasoning decision. Unknown capacity and contradictory bindings refuse. |
| Strict token preflight | [`TokenBoundRequest`, `ProviderTokenBound`](../../src/loop_engine/core/model_token_preflight.py) | Validate host-qualified exact-request bounds; no default estimator or independent qualification. Shared session owns accounting. |
| Benchmark comparison | [`LoopEngineBenchmarkEvidence`, `PublishedHarnessMatchReport`](../../src/loop_engine/code_nodes/complex_task_native_evidence.py) | Exact population and evaluator matching between saved Loop Engine results and reviewed published harness evidence. |
| Intelligence reference | [`LoopRef`, `LoopCapsule`](../../src/loop_engine/loop/loop_capsule.py) | Small reference, exact locator, contract, digest, and selected materialization. |
| Event log and saved run | [`LoopLedger`](../../src/loop_engine/loop/recursive_loop.py), [`RunHistory`, `RunHistoryEvent`](../../src/loop_engine/core/run_history.py), [`ProductOutcomeRef`, `SavedRunBundle`](../../src/loop_engine/core/product_outcome_store.py) | Ordered events, definition references, relationship records, distinct positive, missing, partial, and real-zero model usage, digest-bound product outcome, saved playback, and chain checking. |
| User settings | [`RuntimeSettings`, `LoopDefaults`, `LoopConfigOverride`, `ModelSettings`](../../src/loop_engine/core/runtime_settings.py) | Typed defaults and overrides for modes, search, providers, effort, and model routing. |
| Parameter resolution | [`ParameterDefinition`, `ParameterInput`, `ResolvedParameter`](../../src/loop_engine/core/parameter_resolution.py), [`RuntimeSettings.loop_config_with_record()`](../../src/loop_engine/core/runtime_settings.py) | Distinct omitted, null, empty, false, and zero states; exact source precedence; validation; safe value digests; and bounded Intelligence proposals that cannot override explicit values. |
| Prompt resources | [`PromptResourceBundle`, `PromptSlotDefinition`](../../src/loop_engine/strings/prompt_fragments.py) | Versioned component order, typed slots, trust boundaries, provenance, size and omission policy, output schema identity, and exact render digests. |
| Session handoff packet | [`session_handoff/v1`](session-handoff.schema.json) | Immutable generated checkout snapshot with authority digests, exact dirty paths, explicit ownership evidence, scoped test records, progressive context loading, and mandatory stale-state checks. It is not architecture authority. |
| Stage-assistance evidence foundation | [`StageOccurrenceIdentity`, `StageRetrievalSnapshot`, `StageExposureManifest`, `StageAssistanceDecision`, `StageTrialOutcome`](../../src/loop_engine/core/stage_evidence_records.py), [`StageAssistanceMaterial`](../../src/loop_engine/core/stage_assistance_material.py), [`StageAssistanceExperimentSpec`, `PairedStageAssistanceTrial`](../../src/loop_engine/core/stage_assistance_experiment.py), [`PublicSolveControlManifest`, `StageControlApplicationCandidate`](../../src/loop_engine/core/solve_control_manifest.py), [`SelectedActionLineageRequest`, `ActionExecutionLineageRequest`, `ActionVerificationLineageRequest`](../../src/loop_engine/core/stage_action_lineage.py), [`SQLiteStageEvidenceProjection`](../../src/loop_engine/core/stage_evidence_projection.py) | Separates activation, semantic-call, and similarity identities. The offline public `solve_task` fixture places digest-bound prior material in the rendered prompt and links one action stage by exact selection, execution, and verification occurrences. Active arms save a pre-run control manifest. The fixture classifies itself as mechanism-only because six controls remain unresolved. The stage control application is an unpopulated candidate, and the same-Practitioner verifier leaves attribution confidence unknown. Canonical per-stage pairs, Run History retrieval, exact control freezing, independent evaluation, live model behavior, and causal benefit remain unproven. |
| Public solve | [`SolveRequest`, `SolveOutcome`, `MaterialQuestion`](../../src/loop_engine/code_nodes/solve_runtime.py), [`SolveTerminalCode`, `ResolutionCompletionPolicy`, `ResolutionMethodAssessment`, `TaskResolutionPackage`](../../src/loop_engine/code_nodes/solve_terminal.py) | Immutable original task intake, advisory answerable questions, authorized model and effect calls, verified artifact records, workspace, Run History, and one honest terminal code. An unverified task-level outcome returns a complete `task_resolution_package/v1`. Every registered safe resolution method appears exactly once as completed, not applicable, unavailable, authority-required, or resource-exhausted. A completed method must carry its mapped material, and at least one useful method must complete. Resolution completion remains separate from requested-outcome verification and operational interruption. `solve_outcome/v6` preserves nullable model-call accounting plus stage and selected-action vector projections; saved v3, v4, and v5 records remain readable. |
| Captured instruction origin | [`CapturedInstructionProvenance`, `TaskIntake`](../../src/loop_engine/templates/intake.py) | Captured instruction text, digest, and file origin stay separate from external data references and permissions. A supplied instruction file does not require a fabricated later inspection. |
| Generated project delivery | [`GeneratedProjectCandidate`, `GeneratedProjectManifest`, `execute_generated_project`](../../src/loop_engine/core/generated_project.py) | Strict field/item validation; authored source versus command-produced outputs; verified code-only delivery; pre-write input/output collision refusal; post-run source identity and syntax checks. |
| Independent executable feedback | [`IndependentVerificationPolicy`, `IndependentVerificationRequest`, `run_independent_verification`](../../src/loop_engine/core/independent_verification.py) | Default-required checks for generated projects; isolated oracle design/review; frozen subject and retained regressions; read-only Docker execution; controller-owned comparisons; exact issued-report acceptance. Model-generated oracles remain fallible. |
| Host-owned task operations | [`HostRuntimeBinding`, `HostOperationBinding`, `HostOperationRequest`, `HostInvocation`](../../src/loop_engine/core/host_runtime.py) | Existing Capability Directory registrations; frozen schemas and callable identities; explicit output-sharing grant; scoped permission requests; exact host approvals; state-bound observations; separate host verifier; non-project result completion. Host callbacks, snapshots and sandbox policy remain host responsibilities. |
| Source admission | [`SourceInventory`, `SourceAdmissionRecord`, `inventory_source_files`](../../src/loop_engine/core/adaptive_practitioner_source.py) | Bounded UTF-8 inspection independent of language suffixes, explicit exclusions, existing disclosure authority, confined reads, and complete-text revalidation. |

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

The [record compatibility guide](../components/loop-object/RECORD-COMPATIBILITY.md)
documents version 2 Loop definitions, version 3 Spawned task checkpoints,
exact historical readers, and explicit per-input cardinality. The
[harness recovery guide](../components/core-architecture/HARNESS-FALLBACK.md)
documents optional reviewed-evidence selection and registered response
evaluation. The complete initial and fallback configuration requirement is
recorded in the
[dimension inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md);
that design inventory is not an executable configuration schema.

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
