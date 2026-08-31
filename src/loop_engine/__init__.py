"""Curated public API for Loop Engine.

Every executable graph vertex uses the same ``Loop`` runtime. Public names in
this module define Loop contracts, versioned profiles and definitions, typed
Solution graphs, runtime access ports, and the services needed to run and
inspect work. Internal decision strategies are intentionally absent.
"""

from __future__ import annotations

from importlib import import_module as _import_module


def _names(module: str, *names: str) -> dict[str, tuple[str, str]]:
    """Map public names to one lazy source module."""
    return {name: (module, name) for name in names}


_PUBLIC: dict[str, tuple[str, str]] = {
    # One operational runtime.
    **_names(
        "loop.recursive_loop",
        "Loop", "LoopConfig", "LoopLedger", "LoopResult",
        "StepOutcome",
    ),

    # Versioned Loop definition, identity, relationship, and runtime context.
    **_names(
        "loop.loop_definition",
        "ConfigurationFacts", "LoopDefinition", "LoopDefinitionError",
        "LoopDefinitionRef", "LoopStartRequest",
    ),
    **_names(
        "loop.loop_role",
        "LOOP_RELATIONSHIP_KINDS", "LOOP_ROLES", "LoopRelationshipKind",
        "LoopRole", "LoopRoleIdentity", "LoopRelationship",
    ),
    **_names(
        "loop.runtime_context",
        "CustomPluginsPort", "IntelligenceSearchRetrievalPort",
        "InternalRuntimeBinding", "InternalRuntimeMechanics",
        "LoopRuntimeContext", "LoopRuntimeContextError", "WebResearchPort",
    ),

    # Typed contracts, ports, and versioned profiles.
    **_names(
        "loop.loop_contract",
        "LoopContract", "LoopContractError", "LoopPortBinding",
        "LoopConnectionSpec", "LoopConnectionResult",
        "validate_loop_connection",
    ),
    **_names(
        "loop.loop_profile_catalog",
        "PROFILE_ONTOLOGY_VERSION", "PROFILE_FAMILIES",
        "ROLE_PROFILE_ALIASES", "LOOP_PROFILE_ONTOLOGY",
        "LoopProfileError", "LoopProfileRef", "LoopProfileSpec",
        "profile_catalog", "resolve_profile_alias",
    ),
    **_names(
        "loop.loop_profile_ontology",
        "ResolvedLoopProfile", "OntologyValidationResult",
        "LoopProfileBindingRequest", "BoundLoopProfile",
        "LoopProfileRequirement", "LoopProfileHandshakeResult",
        "get_profile", "resolve_profile", "validate_profile_ontology",
        "bind_profile", "profile_handshake", "identity_for_profile",
    ),

    # Canonical Solution graph and Canvas.
    **_names(
        "code_nodes.solution_graph",
        "LoopDefinitionRegistry", "LoopGraphDefinition", "LoopGraphEdge",
        "LoopGraphEndpoint", "LoopGraphError", "LoopGraphGroup",
        "LoopGraphInputPort", "LoopGraphOutputPort", "LoopGraphStage",
        "LoopGraphValidation", "LoopGraphVertexRecord",
    ),
    **_names(
        "code_nodes.solution_canvas",
        "SolutionSpec", "SolutionLoopSpec", "run_solution",
    ),
    **_names(
        "code_nodes.solution_model_port",
        "ModelExecution", "ModelInvocationPort", "SolutionModelError",
    ),
    **_names(
        "code_nodes.solve_runtime",
        "SolveRequest", "SolveOutcome", "SolveError", "SolveTerminalCode",
        "MaterialQuestion",
        "solve_task",
    ),
    **_names(
        "templates.intake",
        "TaskIntake", "TaskIntakeRequest", "TaskIntakeError", "intake_task",
    ),
    **_names(
        "templates.model", "WorkItemIR", "SemanticCoordinates",
    ),
    **_names(
        "loop.canvas",
        "CANVAS_KINDS", "TypeContract", "SolutionLoopCandidate",
        "SolutionSlot", "Canvas", "SlotOutcome", "MatrixExecution",
        "execute_matrix",
    ),

    # Intelligence references, portfolios, and useful workflows.
    **_names(
        "loop.loop_capsule", "IntelligenceItemHandshake",
        "IntelligenceItemPackage", "IntelligenceItemRef",
        "IntelligenceLoadContext", "IntelligenceLoadRequest",
        "IntelligenceReframeRequest", "load_intelligence_ref",
        "reframe_intelligence_ref"),
    **_names(
        "core.intelligence_portfolio",
        "IntelligencePortfolioError", "PortfolioCoverageError", "LensFamily",
        "REQUIRED_LENS_FAMILIES", "BenchmarkCodeRegistration",
        "BenchmarkCodePack", "PortfolioRequest", "PortfolioSelectionServices",
        "PortfolioMaterializationServices", "IntelligencePortfolioCandidates",
        "IntelligencePortfolio",
        "LoopIntelligenceConsumption", "LoopIntelligenceMaterialization",
        "discover_intelligence_candidates", "select_intelligence_portfolio",
        "materialize_portfolio_for_loop",
        "fold_loop_intelligence_consumption", "export_intelligence_portfolios",
    ),
    **_names("code_nodes.context_seed", "ContextSeedSpec", "run_context_seed"),
    **_names(
        "code_nodes.self_improvement_loop",
        "SelfImprovementReport", "run_self_improvement", "load_run_history",
    ),

    # Saved Run History and event vocabulary.
    **_names(
        "core.product_outcome_store",
        "PRODUCT_OUTCOME_FILENAME", "ProductOutcomeRef", "SavedRunBundle",
        "bind_product_outcome", "load_saved_run_bundle",
    ),
    **_names(
        "core.run_history",
        "RunHistory", "RunHistoryEvent", "RunHistoryIntegrityError",
        "verify_saved_run",
    ),
    **_names("core.event_vocabulary", "EVENT_FAMILIES"),

    # Typed settings and provider entry points.
    **_names(
        "core.runtime_settings",
        "SETTINGS_VERSION", "SEARCH_MODES", "SettingsError", "LoopDefaults",
        "LoopConfigOverride", "SearchSettings", "HistorySettings",
        "ProviderSettings", "ModelTier", "EscalationSettings",
        "ModelPolicyRequest", "ModelTask", "ModelSettings",
        "SettingsLoadResult", "SettingsWriteResult", "RuntimeSettings",
    ),
    **_names(
        "core.settings_loader",
        "runtime_settings_from_mapping", "default_user_settings_path",
        "load_runtime_settings", "default_settings_yaml",
        "write_default_settings",
    ),
    **_names(
        "core.parameter_resolution",
        "ParameterValueState", "ParameterSourceKind",
        "ParameterResolutionStatus", "ParameterResolutionError",
        "ParameterInput", "ParameterDefinition", "ParameterSource",
        "ParameterIntelligenceProposal", "ParameterResolutionTrace",
        "ResolvedParameter", "ParameterResolutionRequest",
        "LoopConfigResolutionRecord", "ParameterInferenceRequest",
        "resolve_parameter", "run_parameter_inference_as_loop",
    ),
    **_names(
        "strings.prompt_fragments",
        "PromptSlotDefinition", "PromptResourceComponent",
        "PromptResourceBundle", "PromptResourceRender",
        "campaign_problem_prompt_bundle",
        "parameter_inference_prompt_bundle",
        "external_harness_instruction_bundle",
    ),
    **_names(
        "core.model_gateway",
        "ProviderAdapter", "ProviderSpec", "ModelRouteAttemptSpec",
        "ModelGatewayConfig", "ModelGatewayRequest", "GatewayAttempt",
        "ModelGatewayResult", "ModelGateway", "builtin_provider_specs",
        "provider_spec_from_endpoint", "invoke_model_gateway",
    ),
    **_names(
        "core.model_routing_intelligence",
        "MODEL_ROUTING_PORTFOLIO", "MODEL_ROUTING_PORTFOLIO_ID",
        "ModelCapabilityRecord", "ModelSuitabilityRecord",
        "ModelRouteAvailabilitySnapshot", "ModelSelectionRequest",
        "ModelSelectionDecision", "ModelOutcomeEvidence",
        "ModelRoutingLearningCandidate", "ModelRouteBootstrapSelector",
        "select_model_as_loop",
    ),
    **_names(
        "core.model_routes",
        "ModelProviderCapabilities", "ModelRoute", "RoutePolicy",
        "RouteRegistry", "resolve_route",
    ),
    **_names("core.custom_endpoint", "CustomEndpoint"),
    **_names(
        "core.autoconfigure",
        "configure", "ModelAccess", "advice_function",
    ),
    **_names(
        "core.provider_failover", "ProviderFailoverContext",
        "ProviderFailoverRequest", "call_with_failover"),

    # Typed spawned-Loop delegation and isolated context.
    **_names(
        "loop.delegation_runtime",
        "SpawnedTaskManager", "DelegationSpec", "DelegationBudget",
        "DelegationConstraints", "ContextVisibilityPolicy", "SpawnedTaskId",
        "SpawnedTaskStatus", "SpawnedReturnDestination", "SpawnedTaskUpdate",
        "SpawnedTaskSnapshot", "SpawnedTaskManagerLimits",
        "SpawnedExecutionRequest", "SpawnedLoopResult", "LoopPortValue",
        "SpawnedExecutor", "DeterministicSpawnedExecutor",
    ),
    **_names(
        "loop.spawned_runtime_port",
        "SpawnedLoopRuntimePortError", "SpawnedLoopRuntimePort",
        "SpawnedLoopRuntimeConfigFacts", "SpawnedLoopRuntimeCounters",
        "SpawnedLoopRuntimeOutcome", "SpawnedStepRequest",
        "SpawnedStepHandler", "RuntimeMemoryService",
        "SpawnedLoopRuntimeMemoryPort",
    ),
    **_names(
        "loop.spawned_task_checkpoint",
        "SPAWNED_TASK_CHECKPOINT_VERSION", "SpawnedTaskCheckpointError",
        "SpawnedTaskCheckpoint", "SpawnedTaskLifecycleMixin",
    ),
    **_names("loop.spawned_practitioner", "spawn_practitioner_loop"),

    # Durable approvals and controlled workspaces.
    **_names(
        "loop.effect_approval",
        "EffectClass", "ApprovalAction", "ApprovalStatus", "EffectSpec",
        "ApprovalRequest", "ApprovalDecision", "PendingApprovalState",
        "ApprovalCheckpoint", "EffectApprovalService",
        "EFFECT_APPROVAL_SCHEMA_VERSION",
    ),
    **_names(
        "loop.approval_state_store",
        "APPROVAL_STATE_STORE_SCHEMA", "ApprovalStateStore",
        "LocalJsonApprovalStateStore", "ApprovalStateStoreError",
        "ApprovalStateNotFound", "ApprovalStateConflict",
        "ApprovalStateIntegrityError",
    ),
    **_names(
        "core.workspace_backends",
        "WorkspaceSpec", "WorkspaceRef", "WorkspaceSnapshotRef",
        "WorkspaceBackend", "BackendAvailability", "FileOperation",
        "FileRequest", "FileResult", "CommandRequest", "CommandResult",
        "SnapshotRequest", "RestrictedLocalWorkspace", "DockerWorkspace",
        "DockerWorkspaceDeclaration", "DockerResourceLimits",
        "DeclaredRemoteWorkspace", "E2BWorkspaceDeclaration",
        "ModalWorkspaceDeclaration", "verify_live_docker_workspace",
    ),
    **_names(
        "core.workspace_operations",
        "WorkspaceApprovalPlan", "WorkspaceOperationError",
        "WorkspaceOperationService",
    ),

    # Context offloading and compaction.
    **_names(
        "core.context_artifacts",
        "ContextArtifactRef", "ContextArtifactStoreSpec",
        "ContextArtifactStore", "ContextOffloadPolicy", "ContextPayload",
        "ContextArtifactManager", "Utf8ChunkTokenCounter",
        "CompactionRequest", "CompactionResult", "HeadTailCompactor",
        "compact_context_as_loop",
    ),

    # Storage-neutral values and reactive Loop contracts.
    **_names(
        "loop.atomic_primitives", "LoopValue", "LoopValueCreateRequest",
        "LoopValueRef", "AtomicPrimitiveDefinition", "AtomicPrimitiveRequest",
        "run_atomic_primitive",
    ),
    **_names(
        "core.information_access",
        "InformationAccessError", "InformationAccessFailureCode",
        "InformationAccessOperation", "InformationAccessRequest",
        "InformationBindingDescriptor", "InformationDescriptor",
        "InformationDurability", "InformationMaterialization",
        "InformationPublicationRequest", "InformationResolver",
        "InformationScope", "InformationStorageBinding",
        "InlineInformationAdapter", "ContextArtifactInformationAdapter",
        "SQLiteInformationAdapter",
    ),
    **_names(
        "loop.reactive_contracts", "ActivationPolicy", "AdmissionPolicy",
        "CandidateVerdict", "EmissionPolicy", "EmissionTrigger",
        "ExplorationPolicy", "ExplorationStrategy", "InputOrdering",
        "InputSchedulingPolicy", "MetricDirection", "OutputCardinality",
        "OutputPortDefinition", "OutputUpdateSemantics", "PersistenceMode",
        "PortfolioPolicy", "PortfolioView", "RankingDimension",
        "ReactiveLivenessPolicy", "ReactiveLoopProfile", "RetentionPolicy",
        "ServingPolicy", "TriggerKind",
    ),
    **_names(
        "loop.reactive_outputs", "CandidateEvaluation", "CandidateOutput",
        "ConfidenceVector", "OutputPortfolioSnapshot", "OutputQuery",
        "PortfolioBuildRequest", "PortfolioEntry", "build_output_portfolio",
    ),
    **_names(
        "loop.reactive_activation", "ActivationClaimRequest",
        "ActivationRecord", "ActivationStartRequest", "ActivationStatus",
        "ActivationTerminalRequest", "LeaseHeartbeatRequest",
        "ReactiveSeriesDefinition", "TriggerEnvelope", "WorkLease",
    ),
    **_names(
        "core.reactive_output_store", "OutputQueryResult",
        "ReactiveOutputStoreError", "SQLiteReactiveOutputStore",
    ),
    **_names(
        "core.reactive_scheduler", "ActivationClaimResult",
        "ReactiveSchedulerError", "SQLiteReactiveScheduler",
        "TriggerAdmissionResult",
    ),
    **_names(
        "core.reactive_worker", "AsyncReactiveWorker",
        "CanonicalActivationResult", "CanonicalReactiveExecutor",
        "ReactiveExecutionRequest", "ReactiveHandlerBinding",
        "ReactiveWorkerError", "ReactiveWorkerOutcome",
        "ReactiveWorkerRequest",
    ),
    **_names(
        "core.plugin_bundles", "PLUGIN_MANIFEST_NAME", "PluginBundleError",
        "PluginBundleManifest", "PluginDiscoveryRequest",
        "PluginDiscoveryResult", "PluginResolutionRequest", "PluginSkillRef",
        "ResolvedPlugin", "ResolvedPluginSnapshot",
        "discover_plugin_bundles", "resolve_plugin_snapshot",
        "resolve_plugin_snapshot_as_loop",
    ),
    **_names(
        "core.extension_discovery", "CAPABILITY_SCHEMA", "EXTENSION_FOLDER",
        "EXTENSION_ROOTS_ENV", "PROVIDER_SCHEMA", "CapabilityCandidate",
        "ExtensionApplication", "ExtensionDiscoveryError",
        "ExtensionDiscoveryRequest", "ExtensionRoot", "ExtensionSnapshot",
        "ExtensionApplicationRequest", "ProviderAuthDefinition",
        "ProviderEndpointDefinition", "ProviderRouteBundle",
        "ProviderSourceRef",
        "apply_provider_extensions",
        "discover_extensions", "discover_extensions_as_loop",
    ),
    **_names(
        "core.development_planning", "AssuranceVerdict",
        "ClarificationDisposition", "ClarificationItem",
        "ConcurrencyDecisionRecord", "DevelopmentPlanError",
        "PlanAssuranceResult", "PlanDefinition", "PlanningAuthority",
        "RequirementVerificationContract", "ResolutionDisposition",
        "RetryPolicy", "TaskExecutionPlan", "TaskLoopBinding",
        "TaskSliceDefinition",
        "TerminalPlanCode", "WorkerAssignmentEnvelope", "assure_plan",
        "compile_execution_waves", "compile_plan_to_loop_graph",
    ),
    **_names(
        "core.lifecycle_extensions", "DriftDisposition",
        "ExecutionContextFingerprint", "ExtensionExecutionMode",
        "ExtensionResolutionRequest", "FingerprintComparison",
        "LifecycleExtensionDefinition", "LifecycleExtensionError",
        "ProcedureLifecycleDefinition", "ResolvedExtensionSetSnapshot",
        "compare_fingerprints", "resolve_extensions",
    ),
    **_names(
        "core.development_governance", "ContributionIsolationRequest",
        "ContributionIsolationResult",
        "DevelopmentGovernanceError", "LegacyAuthorityDisposition",
        "LegacyAuthorityState", "PublicationAuthorization",
        "PublicationEffect", "ResumeReconciliationRequest",
        "ResumeReconciliationResult", "SelfHostingProfile", "TaskReality",
        "isolate_contribution", "reconcile_resume",
    ),
    **_names(
        "core.development_execution", "DevelopmentExecutionError",
        "DevelopmentExecutionRequest", "DevelopmentExecutionResult",
        "TaskAttemptDefinition", "TaskAttemptResult", "TaskExecutionState",
        "TaskOperationOutput", "execute_development_plan",
    ),
    **_names(
        "code_nodes.ascii_views", "render_loop_graph_ascii",
        "render_run_tree_ascii",
    ),

    # MCP and skill adapters.
    **_names(
        "core.mcp_adapter",
        "McpServerSpec", "McpDiscoveryPolicy", "McpToolSpec",
        "McpCallRequest", "McpCallResult", "McpApprovalBinding",
        "McpApprovalPlan", "McpInvocationServices", "McpRegistry",
        "InjectedMcpTransport",
    ),
    **_names(
        "core.mcp_sdk_transport",
        "McpToolPolicy", "McpSecretResolver", "McpSdkTransport",
    ),
    **_names(
        "core.skill_registry",
        "SkillLoadPurpose", "SkillAdmissionRecord", "SkillManifest",
        "LoadedSkill", "SkillRegistry",
    ),

    # Governed reusable Code Intelligence and bounded hybrid assistance.
    **_names(
        "core.code_intelligence_assets",
        "CodeAssetAdmissionError", "CodeAssetAdmissionRecord",
        "CodeAssetSpec", "admit_code_asset", "code_asset_capsule",
        "code_asset_record", "spec_from_template",
    ),
    **_names(
        "core.reusable_capability_records",
        "CapabilityCandidateMatch", "CapabilityGeneralizationRecord",
        "CapabilityInvocationRecord", "CapabilityNeed",
        "CapabilityResolutionPlan", "HarvestDispatch",
        "HybridAssistanceProfile", "HybridAssistanceStage",
        "REUSE_ASSESSMENT_DIMENSIONS",
        "ReuseAssessment", "ReuseHarvestPolicy",
        "ReuseOpportunityObserved", "ReuseRecommendation",
    ),
    **_names(
        "core.reusable_capability_flywheel",
        "CandidateRegistrationRequest", "CandidateRegistrationResult",
        "CapabilityAuthority", "LifecycleTransitionResult",
        "PromotionRequest", "QualificationRequest", "ReusableCapabilityError",
    ),
    **_names(
        "core.reusable_capability_harvest",
        "GeneralizedCapabilityCandidate", "ReuseDispatchResult",
        "ReuseHarvestRequest", "ReuseHarvestResult", "ReuseHarvestServices",
        "ReuseObservationPort",
        "ReuseObservationRequest",
        "dispatch_reuse_opportunity_as_loop",
        "harvest_reuse_opportunity_as_loop",
        "observe_reuse_opportunity_as_loop",
    ),
    **_names(
        "core.reusable_capability_resolution",
        "CapabilityInvocationRequest", "CapabilityInvocationResult",
        "CapabilityResolutionRequest", "CapabilityResolutionResult",
        "CapabilityResolver", "ProjectionRebuildResult",
        "ReusableCapabilityTaskResolver",
        "invoke_capability_as_loop", "rebuild_capability_projection_as_loop",
    ),
    **_names(
        "core.reusable_capability_hybrid",
        "AdapterExecutionRequest", "HybridAssistanceError",
        "HybridAssistanceRequest", "HybridAssistanceResult",
        "execute_ephemeral_adapter_as_loop", "hybrid_assistance_profile",
        "load_hybrid_assistance_profiles", "normalized_need_from_assistance",
        "run_hybrid_assistance_as_loop",
        "selected_candidate_from_assistance",
    ),
    **_names(
        "core.semantic_runtime_records",
        "CommittedSemanticResult", "ProposedStateDelta",
        "SemanticCandidateOutput", "SemanticContextItem",
        "SemanticContextPack", "SemanticDisposition",
        "SemanticEffectAuthorization", "SemanticExecutionRecord",
        "SemanticInterpreterProfile", "SemanticInterpreterQualification",
        "SemanticLoopContract", "SemanticLoopContractDraft",
        "SemanticProgramIdentity", "SemanticRealizationBinding",
        "SemanticRealizationKind", "SemanticRuntimeContractError",
        "SemanticVerificationRecord", "TrustedStateSnapshot",
    ),
    **_names(
        "core.semantic_runtime_evidence",
        "SemanticReliabilityEnvelope", "SemanticStrategyBenchmark",
        "SemanticStrategyMeasurement",
    ),
    **_names(
        "core.semantic_state",
        "CatalogTrustedSemanticState", "SemanticEffectController",
        "SemanticStateConflict", "SemanticStateError", "SemanticVerifier",
    ),
    **_names(
        "core.semantic_runtime",
        "SemanticExecutionError", "SemanticExecutionRequest",
        "SemanticExecutionResult", "SemanticExecutionServices",
        "SemanticInterpreterPort", "SemanticInterpreterResult",
        "bind_semantic_loop_contract", "execute_semantic_loop",
        "select_semantic_realization",
    ),

    # Observability and OpenTelemetry export.
    **_names(
        "core.runtime_observer",
        "RuntimeObservation", "RuntimeObserver", "NullRuntimeObserver",
        "LedgerRuntimeObserver", "RuntimeObservationServices",
    ),
    **_names(
        "core.otel_export",
        "RawLedgerEvents", "OtelSpanRecord", "InMemorySpanExporter",
        "OpenTelemetrySpanExporter", "run_history_to_spans",
        "export_run_history_as_loop",
    ),

    # External harness boundaries and published comparison evidence.
    **_names(
        "core.external_harness",
        "ModelOutputLimit", "StaticModelOutputResolver",
        "HarnessBudget", "HarnessRunRequest", "HarnessModelCall",
        "HarnessRunResult", "HarnessAdapterInfo", "HarnessRuntimeBinding",
        "HarnessRegistry", "HarnessServices", "run_external_harness",
    ),
    **_names(
        "core.external_harness_adapters",
        "ConfiguredHarnessAdapter", "builtin_harness_adapters",
    ),
    **_names(
        "code_nodes.complex_task_benchmark",
        "PublishedBenchmarkEvidence", "PublishedComparisonGroup",
        "PublishedEvidenceCatalog", "PublishedEvidenceError",
        "PublishedEvidenceFinding", "LoopEngineBenchmarkEvidence",
        "LoopEngineEvidenceCatalog", "PublishedHarnessMatch",
        "PublishedHarnessMatchReport", "default_loop_engine_catalog_path",
        "default_published_catalog_path", "load_native_evidence",
        "load_published_evidence", "match_loop_engine_to_published",
        "native_catalog_from_mapping", "published_catalog_from_mapping",
    ),

    # Main user workflows and package verification.
    **_names(
        "core.knowledge_loader",
        "load_knowledge", "load_into_store",
    ),
    **_names("_self_test", "self_test"),
}


__all__ = tuple(_PUBLIC)


def __getattr__(name: str):
    """Load a documented public name only when it is requested."""
    target = _PUBLIC.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    return getattr(_import_module(f"{__name__}.{module}"), attribute)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_PUBLIC))
