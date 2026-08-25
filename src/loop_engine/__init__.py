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
        "Loop", "LoopConfig", "LoopLedger", "LoopResult", "StepOutcome",
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
        "LoopGraphValidation", "LoopGraphVertex",
    ),
    **_names(
        "code_nodes.solution_canvas",
        "SolutionSpec", "SolutionLoopSpec", "run_solution",
    ),
    **_names(
        "loop.canvas",
        "CANVAS_KINDS", "TypeContract", "SolutionLoopCandidate",
        "SolutionSlot", "Canvas", "SlotOutcome", "MatrixExecution",
        "execute_matrix",
    ),

    # Intelligence references, portfolios, and useful workflows.
    **_names("loop.loop_capsule", "LoopRef", "LoopCapsule"),
    **_names(
        "static_architecture.intelligence_portfolio",
        "IntelligencePortfolioError", "PortfolioCoverageError", "LensFamily",
        "REQUIRED_LENS_FAMILIES", "BenchmarkCodeRegistration",
        "BenchmarkCodePack", "PortfolioRequest", "PortfolioSelectionServices",
        "PortfolioMaterializationServices", "IntelligencePortfolio",
        "LoopIntelligenceConsumption", "LoopIntelligenceMaterialization",
        "select_intelligence_portfolio", "materialize_portfolio_for_loop",
        "fold_loop_intelligence_consumption", "export_intelligence_portfolios",
    ),
    **_names("code_nodes.context_seed", "ContextSeedSpec", "run_context_seed"),
    **_names(
        "code_nodes.self_improvement_loop",
        "SelfImprovementReport", "run_self_improvement", "load_run_history",
    ),

    # Saved Run History and event vocabulary.
    **_names(
        "static_architecture.run_history",
        "RunHistory", "RunHistoryEvent", "RunHistoryIntegrityError",
    ),
    **_names("static_architecture.event_vocabulary", "EVENT_FAMILIES"),

    # Typed settings and provider entry points.
    **_names(
        "static_architecture.runtime_settings",
        "SETTINGS_VERSION", "SEARCH_MODES", "SettingsError", "LoopDefaults",
        "LoopConfigOverride", "SearchSettings", "HistorySettings",
        "ProviderSettings", "ModelTier", "EscalationSettings",
        "ModelPolicyRequest", "ModelTask", "ModelSettings",
        "SettingsLoadResult", "SettingsWriteResult", "RuntimeSettings",
    ),
    **_names(
        "static_architecture.settings_loader",
        "runtime_settings_from_mapping", "default_user_settings_path",
        "load_runtime_settings", "default_settings_yaml",
        "write_default_settings",
    ),
    **_names(
        "static_architecture.model_gateway",
        "ProviderAdapter", "ProviderSpec", "ModelRouteAttemptSpec",
        "ModelGatewayConfig", "ModelGatewayRequest", "GatewayAttempt",
        "ModelGatewayResult", "ModelGateway", "builtin_provider_specs",
        "provider_spec_from_endpoint", "invoke_model_gateway",
    ),
    **_names(
        "static_architecture.model_routes",
        "ModelProviderCapabilities", "ModelRoute", "RoutePolicy",
        "RouteRegistry", "resolve_route",
    ),
    **_names("static_architecture.custom_endpoint", "CustomEndpoint"),
    **_names(
        "static_architecture.autoconfigure",
        "configure", "ModelAccess", "advice_function",
    ),
    **_names("static_architecture.provider_failover", "call_with_failover"),

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
        "static_architecture.workspace_backends",
        "WorkspaceSpec", "WorkspaceRef", "WorkspaceSnapshotRef",
        "WorkspaceBackend", "BackendAvailability", "FileOperation",
        "FileRequest", "FileResult", "CommandRequest", "CommandResult",
        "SnapshotRequest", "RestrictedLocalWorkspace", "DockerWorkspace",
        "DockerWorkspaceDeclaration", "DockerResourceLimits",
        "DeclaredRemoteWorkspace", "E2BWorkspaceDeclaration",
        "ModalWorkspaceDeclaration", "verify_live_docker_workspace",
    ),
    **_names(
        "static_architecture.workspace_operations",
        "WorkspaceApprovalPlan", "WorkspaceOperationError",
        "WorkspaceOperationService",
    ),

    # Context offloading and compaction.
    **_names(
        "static_architecture.context_artifacts",
        "ContextArtifactRef", "ContextArtifactStoreSpec",
        "ContextArtifactStore", "ContextOffloadPolicy", "ContextPayload",
        "ContextArtifactManager", "Utf8ChunkTokenCounter",
        "CompactionRequest", "CompactionResult", "HeadTailCompactor",
        "compact_context_as_loop",
    ),

    # MCP and skill adapters.
    **_names(
        "static_architecture.mcp_adapter",
        "McpServerSpec", "McpDiscoveryPolicy", "McpToolSpec",
        "McpCallRequest", "McpCallResult", "McpApprovalBinding",
        "McpApprovalPlan", "McpInvocationServices", "McpRegistry",
        "InjectedMcpTransport",
    ),
    **_names(
        "static_architecture.mcp_sdk_transport",
        "McpToolPolicy", "McpSecretResolver", "McpSdkTransport",
    ),
    **_names(
        "static_architecture.skill_registry",
        "SkillLoadPurpose", "SkillAdmissionRecord", "SkillManifest",
        "LoadedSkill", "SkillRegistry",
    ),

    # Observability and OpenTelemetry export.
    **_names(
        "static_architecture.runtime_observer",
        "RuntimeObservation", "RuntimeObserver", "NullRuntimeObserver",
        "LedgerRuntimeObserver", "RuntimeObservationServices",
    ),
    **_names(
        "static_architecture.otel_export",
        "RawLedgerEvents", "OtelSpanRecord", "InMemorySpanExporter",
        "OpenTelemetrySpanExporter", "run_history_to_spans",
        "export_run_history_as_loop",
    ),

    # External harness boundaries and published comparison evidence.
    **_names(
        "static_architecture.external_harness",
        "ModelOutputLimit", "StaticModelOutputResolver",
        "HarnessBudget", "HarnessRunRequest", "HarnessModelCall",
        "HarnessRunResult", "HarnessAdapterInfo", "HarnessRuntimeBinding",
        "HarnessRegistry", "HarnessServices", "run_external_harness",
    ),
    **_names(
        "static_architecture.external_harness_adapters",
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
    **_names("code_nodes.universal_solve", "solve", "read_task", "TaskReading"),
    **_names(
        "static_architecture.knowledge_loader",
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
