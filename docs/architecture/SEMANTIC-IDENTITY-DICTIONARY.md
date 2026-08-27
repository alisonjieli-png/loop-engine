# Loop Engine data dictionary

This file is generated from the semantic constitution in `terminology.yaml`. The packaged YAML is a verified install-time projection. The dictionary records one meaning, category, authority, and customization decision for each material public concept.

## Decision rule

| Situation | Required representation |
|---|---|
| Values or behavior settings vary | Use one base type with immutable typed parameters or a versioned profile. |
| Algorithm or provider varies behind one contract | Register a strategy, port, or adapter and compose it into the owning runtime. |
| State, lifecycle, protocol, or authority differs | Create a separately named class with one semantic category and explicit contract. |
| Stateless deterministic operation | Use a typed function accepting at most three direct parameters. |
| Work needs independent governance | Create another Loop instance using a profile; never create another runtime subclass. |
| A truly substitutable subtype is unavoidable | Record the justification and conformance test; runtime inheritance from Loop is forbidden. |
| A passive typed contract is cohesive | Keep and version the typed class; consolidation must not collapse distinct data into strings or generic dictionaries. |

## Semantic categories

| Category | Meaning | Preferred suffixes |
|---|---|---|
| `runtime` | Stateful executable object with governed identity and lifecycle. | Loop, Runtime |
| `operation` | Governed or pure work performed through a declared contract. | none |
| `definition` | Immutable versioned description of permitted behavior. | Definition, Spec |
| `contract` | Typed compatibility and acceptance boundary. | Contract |
| `request` | Passive validated input for one operation. | Request |
| `context` | Scoped runtime identity, cancellation, deadline, and authority state. | Context |
| `record` | Passive persisted or observed fact with identity and provenance. | Record, Evidence |
| `snapshot` | Immutable point-in-time projection of selected state. | none |
| `reference` | Exact pointer to another object; never its full body. | Ref, Reference |
| `policy` | Hard permission, eligibility, budget, or effect constraint. | Policy |
| `preference` | Soft choice that never grants authority. | none |
| `strategy` | Replaceable algorithm or search behavior under one contract. | Strategy |
| `profile` | Versioned reusable behavior and preference configuration. | Profile, ProfileSpec, ProfileRef |
| `procedure` | Typed step, graph, state-machine, or bounded-cycle description. | none |
| `service` | Stateful implementation boundary used by an owning runtime. | Service, Gateway, Directory |
| `adapter` | Protocol-specific implementation behind a provider-neutral boundary. | Adapter, Port |
| `provider` | External or local service implementation identity. | none |
| `route` | Configured path to an exact provider or deployment. | none |
| `capability` | Declared operation that may be selected after compatibility checks. | none |
| `tool` | Invocable capability with typed input, output, permission, and effects. | none |
| `plugin` | Versioned extension contribution and provenance mechanism. | none |
| `registry` | Exact identity resolution authority. | none |
| `catalog` | Logical discovery and query surface over records. | none |
| `store` | Physical persistence authority for records in a declared scope. | Store, Journal, Catalog |
| `index` | Rebuildable query materialization traceable to canonical records. | Index, Materialization |
| `cache` | Discardable acceleration that owns no canonical identity. | none |
| `artifact` | Digest-addressed body or output stored outside small events. | none |
| `event` | One chronological typed fact in Run History. | none |
| `history` | Canonical append-only evidence of governed runtime events. | RunHistory, Event |
| `memory` | Bounded working state or reviewed reusable experience, claim, or procedure. | Memory, MemoryRecord |
| `candidate` | Unapproved proposed reusable knowledge or behavior. | Candidate |
| `active_intelligence` | Independently reviewed and promoted reusable intelligence. | none |
| `result` | Typed outcome of one completed or refused operation. | Result, Outcome, Decision |
| `report` | Read-only projection of canonical records and results. | none |
| `renderer` | Formatting implementation that cannot re-derive business facts. | none |
| `evaluator` | Independent contract-matched assessment implementation. | none |
| `benchmark` | Frozen task population, conditions, evaluator, and measured result. | Benchmark, Campaign, Trial |
| `scenario` | Passive capability-proof task definition, not achieved evidence. | none |
| `settings` | Validated user or organization configuration; never runtime authority by itself. | Settings, Defaults, Override |
| `builder` | Passive construction or comparison object that produces an authoritative definition. | Canvas, Builder, Candidate |
| `ontology_category` | Abstract classification used to organize concepts; never executable. | none |

## Public concepts

| Term | Category | Meaning | Authority | Customization | Inheritance | Aliases |
|---|---|---|---|---|---|---|
| `Node` | `ontology_category` | Abstract category containing the sole executable kind, Loop. | `terminology.yaml#terms.Node` | not_applicable | no_concrete_base_class | none |
| `Loop` | `runtime` | Sole executable runtime and executable graph-vertex type. | `loop_engine.loop.recursive_loop:Loop` | role_mode_profile_procedure_and_settings | sealed_no_subclasses | none |
| `LoopDefinition` | `definition` | Immutable digest-pinned description bound to a Loop. | `loop_engine.loop.loop_definition:LoopDefinition` | immutable_fields | none | none |
| `LoopDefinitionRecord` | `record` | Passive searchable projection of a LoopDefinition. | `loop_engine.ontology.loop_definition_record:LoopDefinitionRecord` | immutable_fields | CatalogRecord_only | none |
| `LoopGraphDefinition` | `definition` | Sole authoritative reusable executable graph contract. | `loop_engine.code_nodes.solution_graph:LoopGraphDefinition` | vertices_edges_ports_and_groups | none | none |
| `LoopGraphVertexRecord` | `record` | Passive vertex record referencing one LoopDefinition. | `loop_engine.code_nodes.solution_graph:LoopGraphVertexRecord` | immutable_fields | none | none |
| `LoopProfileSpec` | `profile` | Versioned reusable Loop behavior configuration. | `loop_engine.loop.loop_profile_catalog:LoopProfileSpec` | profile_fields | profile_lineage_not_runtime_inheritance | none |
| `LoopProfileRef` | `reference` | Exact reference to one versioned profile. | `loop_engine.loop.loop_profile_catalog:LoopProfileRef` | identity_fields | none | none |
| `LoopStartRequest` | `request` | Complete validated request that creates one Loop instance. | `loop_engine.loop.loop_definition:LoopStartRequest` | cohesive_request_fields | none | none |
| `LoopRuntimeContext` | `context` | Least-authority ports and run-scoped state available to one Loop. | `loop_engine.loop.runtime_context:LoopRuntimeContext` | scoped_bindings | none | none |
| `IntelligenceItemRef` | `reference` | Body-free exact pointer to one intelligence item and its compatibility facts. | `loop_engine.loop.loop_capsule:IntelligenceItemRef` | identity_layer_contract_and_digest | none | `LoopRef` |
| `IntelligenceItemPackage` | `record` | Passive lazy package that resolves an intelligence payload only after selection. | `loop_engine.loop.loop_capsule:IntelligenceItemPackage` | immutable_package_fields | none | `LoopCapsule` |
| `LoopConfig` | `settings` | Compatibility constructor settings resolved into a LoopDefinition and runtime context. | `loop_engine.loop.recursive_loop:LoopConfig` | typed_fields | none | none |
| `SolutionCanvas` | `builder` | Candidate, comparison, and projection object that resolves to LoopGraphDefinition. | `loop_engine.code_nodes.solution_canvas:SolutionSpec` | candidate_solution_fields | none | `SolutionSpec`, `Canvas` |
| `WorkItemIR` | `record` | Typed preserved original input and normalized task interpretation. | `loop_engine.templates.model:WorkItemIR` | optional_typed_fields | none | none |
| `TaskCompileRequest` | `request` | Cohesive passive input to task compilation. | `loop_engine.templates.compiler:TaskCompileRequest` | request_fields | none | none |
| `IntelligenceAccessPolicy` | `policy` | Hard limits on visible intelligence scopes and records. | `loop_engine.core.intelligence_query_contracts:IntelligenceAccessPolicy` | policy_fields | none | none |
| `IntelligenceSeekingStrategy` | `strategy` | Search expansion and stopping behavior; cannot grant access. | `loop_engine.core.intelligence_query_contracts:IntelligenceSeekingStrategy` | strategy_fields | none | none |
| `IntelligenceQueryProfile` | `profile` | Soft ranking preferences separate from policy. | `loop_engine.core.intelligence_query_contracts:IntelligenceQueryProfile` | ranking_preferences | none | none |
| `IntelligencePortfolioSnapshot` | `record` | Exact reviewed records selected for one invocation. | `loop_engine.core.intelligence_query_contracts:IntelligencePortfolioSnapshot` | immutable_selection | none | none |
| `WorkingMemoryState` | `memory` | Bounded current-run state that is not automatically persistent. | `loop_engine.memory.working.state:WorkingMemoryState` | scope_and_capacity | none | `RuntimeMemory` |
| `EpisodicMemoryRecord` | `memory` | Exact prior experience with Run History provenance. | `loop_engine.memory.episodic.record:EpisodicMemoryRecord` | immutable_record_fields | none | none |
| `SemanticMemoryRecord` | `memory` | Independently reviewed reusable claim with scope and evidence. | `loop_engine.memory.semantic.record:SemanticMemoryRecord` | immutable_record_fields | none | none |
| `ProceduralMemoryRecord` | `memory` | Independently reviewed reusable procedure with contracts and rollback. | `loop_engine.memory.procedural.record:ProceduralMemoryRecord` | immutable_record_fields | none | none |
| `RunHistory` | `history` | Canonical persisted event evidence for all Loop work. | `loop_engine.core.run_history:RunHistory` | event_schema_and_storage_root | none | none |
| `LearningCandidate` | `candidate` | Durable unapproved proposal awaiting independent review. | `loop_engine.memory.storage.learning_records:CandidateStageRequest` | candidate_kind_and_scope | none | none |
| `CandidateJournal` | `store` | Durable governance store for candidate transitions and integrity. | `loop_engine.memory.storage.learning_cycle:CandidateJournal` | storage_root | none | none |
| `RuntimeSettings` | `settings` | Validated user and organization configuration without execution authority. | `loop_engine.core.runtime_settings:RuntimeSettings` | nested_typed_settings | none | none |
| `ModelGateway` | `service` | Sole provider-neutral physical model invocation boundary. | `loop_engine.core.model_gateway:ModelGateway` | gateway_config_routes_and_adapters | none | none |
| `ProviderAdapter` | `adapter` | Provider-specific transport behind ModelGateway. | `loop_engine.core.model_gateway:ProviderAdapter` | provider_protocol | protocol_implementation | none |
| `ModelRoute` | `definition` | Passive exact provider, model, locality, and capability route. | `loop_engine.core.model_routes:ModelRoute` | route_fields | none | none |
| `ModelCapabilityRecord` | `record` | Source-backed technical support facts; not suitability evidence. | `loop_engine.core.model_routing_records:ModelCapabilityRecord` | immutable_record_fields | none | none |
| `ModelSuitabilityRecord` | `record` | Measured task-conditioned quality and failure evidence. | `loop_engine.core.model_routing_records:ModelSuitabilityRecord` | task_population_and_metrics | none | none |
| `ModelRouteAvailabilitySnapshot` | `record` | Time-bounded reachability state; not persistent quality evidence. | `loop_engine.core.model_routing_records:ModelRouteAvailabilitySnapshot` | route_and_observation_time | none | none |
| `CatalogRecord` | `record` | Passive canonical catalog fact; never an executable Node. | `loop_engine.ontology.records:CatalogRecord` | immutable_record_fields | passive_record_only | none |
| `CatalogStore` | `store` | Provider-neutral persistence contract with declared capabilities. | `loop_engine.catalog.protocol:CatalogStore` | backend_configuration | protocol_implementation | none |
| `NgramIndex` | `index` | Rebuildable exact external retrieval materialization, never intelligence truth. | `loop_engine.core.ngram_retrieval:NgramIndex` | NgramSpaceDefinition | none | none |
| `CapabilityDirectory` | `service` | Effect-free plugin and capability discovery with typed handshakes. | `loop_engine.core.capability_directory:CapabilityDirectory` | registered_manifests | none | none |
| `HarnessRunResult` | `benchmark` | One exact task, harness, provider, model, budget, evaluator, and result cell. | `loop_engine.core.external_harness:HarnessRunResult` | immutable_comparison_key | none | none |
| `TaskFingerprintRequest` | `request` | Raw typed task facts used to construct one normalized TaskFingerprint. | `loop_engine.core.task_fingerprint:TaskFingerprintRequest` | cohesive_request_fields | none | none |
| `TaskFingerprint` | `contract` | Versioned structured task identity used for compatibility, search, and evidence. | `loop_engine.core.task_fingerprint:TaskFingerprint` | typed_fingerprint_fields | none | none |
| `CompatibilityAssessment` | `result` | Hard, soft, and unknown contract comparisons for one reusable candidate. | `loop_engine.core.task_fingerprint:CompatibilityAssessment` | comparison_dimensions | none | none |
| `ResolutionOrigin` | `contract` | Closed classification of how one candidate proposes to satisfy work. | `loop_engine.core.resolution:ResolutionOrigin` | enum_value | none | none |
| `ResolutionCandidate` | `candidate` | Passive proposed route with origin, compatibility, eligibility, expected outcomes, and evidence. | `loop_engine.core.resolution:ResolutionCandidate` | origin_contract_metrics_and_refs | none | none |
| `ResolutionRequest` | `request` | Hard constraints and soft origin preferences for one resolution decision. | `loop_engine.core.resolution:ResolutionRequest` | constraints_preferences_and_candidates | none | none |
| `ResolutionDecision` | `result` | Digest-pinned selection or abstention with considered candidates, rejection reasons, and required delta. | `loop_engine.core.resolution:ResolutionDecision` | selected_ref_rejections_and_delta | none | none |
| `ResolutionRunResult` | `result` | ResolutionDecision plus the Practitioner Loop identity and model-call count. | `loop_engine.core.resolution:ResolutionRunResult` | loop_identity_and_decision | none | none |
| `RequirementPolicy` | `policy` | Template-owned hard rule for whether interactive or autonomous compilation may delegate a missing choice and under which constraints. | `loop_engine.templates.model:RequirementPolicy` | cues_constraints_dependencies_and_feedback_slot | none | none |
| `RequirementDispositionState` | `contract` | Closed state distinguishing provided values, delegated choices, values requiring clarification, and autonomous abstention. | `loop_engine.templates.model:RequirementDispositionState` | enum_value | none | none |
| `RequirementDisposition` | `result` | Typed next action, constraints, dependencies, and optional feedback slot for one required task value. | `loop_engine.templates.model:RequirementDisposition` | state_reason_constraints_dependencies_and_feedback_slot | none | none |
| `InteractionMode` | `policy` | Closed task-compilation policy choosing material questions or terminal autonomous behavior. | `loop_engine.templates.model:InteractionMode` | enum_value | none | none |
| `TaskFeedback` | `request` | Optional invocation input for one registered task preference slot. | `loop_engine.templates.model:TaskFeedback` | slot_ref_and_value | none | none |
| `LiveTextScenario` | `scenario` | Reviewed public text task with one interaction policy and independently checkable next-state outcome. | `loop_engine.core.live_text_scenarios:LiveTextScenario` | task_text_interaction_mode_expected_status_and_source | none | none |
| `LiveTextScenarioSuiteRequest` | `request` | Explicit provider authority, route, call ceiling, token ceiling, timeout, and evidence destination for five live text tasks. | `loop_engine.core.live_text_scenarios:LiveTextScenarioSuiteRequest` | cohesive_live_suite_request_fields | none | none |

## Compatibility rule

An alias must resolve to the same object or be accepted only by an exact immutable-record reader. It cannot own execution, persistence, promotion, settings, or graph authority.
