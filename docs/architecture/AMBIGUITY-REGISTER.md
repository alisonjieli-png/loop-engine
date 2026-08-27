# Ambiguity register

This is the rendered review register for semantic collisions. The machine-readable source is `SEMANTIC-AMBIGUITY-REGISTER.yaml`; canonical term meanings remain in `terminology.yaml`.

| ID | Subsystem | Collision | Accepted resolution | Status |
|---|---|---|---|---|
| `SEM-001` | intelligence_and_memory | Five memory labels and a one-layer-to-one-memory map compete with the canonical four memory types. | Import the four memory types from memory.model; remove social memory and the layer-to-memory bijection. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-002` | intelligence_runtime_identity | LoopRef, LoopCapsule, and IntelligenceItemEnvelope make passive intelligence objects sound executable. | Use IntelligenceItemRef and loaded intelligence values; use LoopDefinitionRef only when invocation is executable. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-003` | catalog_records | Passive storage emits the runtime-shaped word node. | Emit catalog_record or exact artifact kinds; read node only through compatibility migration. | `IMPLEMENTED_PARTIALLY` |
| `SEM-004` | catalogs | UnifiedCatalog, CompositeCatalog, build_intelligence_catalog, and SolverStore appear to own overlapping query authority. | CatalogStore plus CompositeCatalog own query and resolution; discovery and legacy stores become named adapters. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-005` | learning_governance | Asset lifecycle, IntelligenceRegistry, and CandidateJournal expose separate promotion authorities. | One governed learning repository owns promotion; former calls delegate with exact evidence and identities. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-006` | model_invocation | Public provider_failover invokes adapters beside the sole ModelGateway. | Compatibility entry builds ModelGatewayRequest and delegates to ModelGateway. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-007` | model_capabilities | Model maximum output is stored as context capacity during discovery. | Keep context_window_tokens and maximum_output_tokens independent with source and unknown state. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-008` | studio | Studio is described as read-only while its HTTP handler writes User Feedback. | Separate StudioReadModelServer and an authorized UserFeedbackSubmissionEndpoint, or remove the read-only claim. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-009` | studio_projections | Studio loops, strings, solutions, and improvements use inventories that do not read canonical authorities. | Project Run History, catalog, definitions, graphs, and governed candidate repository. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-010` | runtime_memory | RunNoteBoard, WorkingMemoryState, and RuntimeMemoryService describe different scopes under similar names. | Use RunSharedNoteBoard, LoopWorkingMemoryState, and RunSharedMemoryService. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-011` | event_history | LoopLedger, RunHistoryEvent, EVENT_FAMILIES, and retired history references obscure buffer, stored envelope, vocabulary, and history. | Name live buffer, stored event, event vocabulary, and Run History separately; the retired spelling is reader-only. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-012` | generation_governance | Generation stage, governed lifecycle, and writeback destination share state labels. | Separate GenerationEvaluationStage, GovernedLifecycle, and WritebackDestination. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-013` | settings | SolverConfig overlaps RuntimeSettings, OperatingProfile, and LoopConfig; LoopConfig.settings returns effort only. | Use ResolvedOperatingConstraints, rename settings to effort_limits, and keep authored, resolved, and invocation scopes distinct. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-014` | configuration_records | ConfigurationFacts represents Loop configuration, vertex parameters, and edge metadata. | Use CanonicalJsonObject internally with LoopConfigurationSnapshot, VertexParameters, and EdgeMetadata wrappers. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-015` | model_output_limits | Output maxima appear in provider settings, model tiers, route attempts, and gateway configuration. | One source-backed ModelOutputCapability; total usage budget stays a distinct max_total_tokens field. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-016` | model_vocabularies | Routing records and model discovery locally redefine Loop roles, modes, thinking powers, lifecycles, and model purposes. | Import canonical vocabularies and use one ModelJobPurpose enumeration. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-017` | model_capability_stages | Provider capability hints, provider binding, and deployment evidence use overlapping capability names. | Name route hints, resolved provider binding, and reviewed deployment evidence explicitly. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-018` | plugins | Plugin means provenance, adapter mechanism, and public capability port; Brave spans Web Research and Custom Plugins. | Reserve plugin for provenance and extension mechanism; use CustomCapabilitiesPort and BraveWebSearchAdapter. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-019` | materialization | Materialization names both persistent representations and runtime body loading. | Reserve materialization for at-rest representations; runtime operations use load. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-020` | scenarios | Capability scenario definitions live under benchmarks and use achieved-sounding tiers before execution. | Name them validation scenarios and intended_gate until population, evaluator, execution, and evidence are frozen. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-021` | intelligence_layers | Layer and User Feedback coexist with pillar, guidance, and user intelligence names. | New APIs use layer and user_feedback; former names become exact aliases only. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-022` | duckdb_catalog | DuckDBCatalogBackend and DuckDBFileQueryEngine overlap legacy and canonical query paths. | Former path delegates to the CatalogStore adapter and is removed after migration. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-023` | adapter_and_memory_store_names | AdapterRegistry is domain-ambiguous and InMemoryMemoryStore does not state persistent scope. | Use CatalogStoreAdapterRegistry and InMemoryPersistentMemoryRepository. | `REQUIRED_NOT_IMPLEMENTED` |
| `SEM-024` | benchmark_evidence | complex_task_benchmark contains evidence matching rather than benchmark execution. | Move behavior to benchmark_evidence and retain the old module only as an import facade. | `REQUIRED_NOT_IMPLEMENTED` |

## Already clear

- MemoryQuery and IntelligenceQuery have distinct lifecycle and cross-layer contracts.
- RunHistory is authority while EpisodicMemoryRecord is an interpreted derivative.
- ModelSelectionRequest, ModelSelectionDecision, ModelGatewayConfig, and ModelGateway are distinct stages.
- ProviderSettings, ProviderSpec, ModelRoute, and ModelRouteAvailabilitySnapshot are distinct authored, resolved, route, and observed forms.
- Benchmark definitions, Loop Engine evidence, third-party evidence, and comparison matches remain distinct.
