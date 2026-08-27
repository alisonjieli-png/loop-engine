# Loop Engine Glossary

This glossary defines every major component and the differences
between similar-sounding components. It is normative: when code,
records, tests, and documentation disagree, this glossary and the
Constitution are the authority until an ADR changes them.

## 1. Node and Loop

| Term | Definition | Difference from neighbors |
|---|---|---|
| Node | Ontological category and package namespace only. There is no concrete operational Node class. | Node classifies; it does not run. |
| Loop | The sole concrete operational runtime and executable graph vertex, implemented in `loop/recursive_loop.py`. | A Loop runs; definitions and ontology records are passive. |
| `kind: loop_node` | Historical serialized record spelling accepted only by the legacy migration reader. | It becomes `LoopDefinitionRecord`; new code never emits it. |
| LoopDefinition | Immutable, versioned description used to instantiate a Loop: ID, version, digest, role profile, contract, modes, step profile, conditions, effects, permissions, capabilities. | A definition is data; a Loop is the live runtime. |
| LoopDefinitionRef | Exact reference: definition_id + version + content_digest. | A ref is a pointer; a definition is the body. |
| LoopStartRequest | The one object that starts a Loop: goal, complete definition, relationship, least-authority runtime context, and event log. | The only sanctioned entry point into the runtime. |
| LoopConfig | Runtime configuration: framework, modes, power, thinking power, budgets, conditions. | Config is settings; LoopDefinition is identity and contract. |
| LoopResult | Typed terminal result: steps run, mode counts, model calls, stop reason. | A result is output; a report is an explanation. |
| LoopLedger | The canonical in-process event log. | The ledger is events; RunHistory is the persisted form. |
| LoopProfileSpec / LoopProfileRef | Versioned behavior specification and exact reference for a common Loop behavior. | A profile is data; a subclass would be a new runtime. |
| LoopStepBinding | Typed instruction for instantiating and connecting a Loop Spawned by its parent. | A binding describes a Spawned Loop; it is not itself a Node. |
| LoopProcedure | Atomic, sequence, graph, state-machine, iterative, parallel, or dynamic procedure. | A procedure is the plan; the Loop executes it. |
| LoopGraphDefinition | The authoritative static DAG: versioned definition refs, vertices, typed edges, graph digest. | The graph is a contract; the Canvas is a builder. |
| SolutionCanvas | Product artifact describing a reusable solution for new inputs. | A Canvas builds; the graph is the authority. |
| IntelligenceItemRef / IntelligenceItemPackage | Small typed reference and lazy package returned by intelligence search. | A ref carries no payload; a package loads only after selection. Historical LoopRef and LoopCapsule imports are compatibility-only. |

## 2. Roles, relationships, and modes

| Term | Definition | Difference from neighbors |
|---|---|---|
| LoopRole | Practitioner, Intelligence, or Solution. | Role is why it runs; profile is how it behaves. |
| LoopProfileRef | Narrower reusable purpose: researcher, verifier, search_and_rank, validator... | Role is broad; profile is specific. |
| LoopRelationship | How a Loop entered the graph: Starting, Spawned by, Queried by, Retrieved by, Connected from. | Relationship is topology entry; role is purpose. |
| Run mode | deterministic, hybrid, non_deterministic. | Mode is how work resolves; placement is where it runs. |
| Execution placement | inline, task, process, container, serverless, remote. | Placement never grants permissions. |
| Scheduling pattern | sequential, fork_join, bounded_fanout, pipeline, race, quorum, detached. | Scheduling is overlap; mode is semantics. |
| ConcurrencyContract | Declared dependencies, reads, writes, effects, safety, resources, lifecycle. | A contract declares; a ConcurrencyDecision decides. |
| ConcurrencyDecision | safe, safe_with_constraints, unsafe, or unknown overlap verdict with reasons. | Unknown defaults to not parallel. |

## 3. Intelligence

| Term | Definition | Difference from neighbors |
|---|---|---|
| Intelligence layer | One of four persistent layers: Context, Code, Runtime History and Solution, User Feedback. | A layer is storage organization; a function is why it is useful. |
| Functional Intelligence Domain | One of nine non-exclusive labels: ask, horizon, readiness, deliberation, implementation, execution, verification, integration, routing. | Multi-valued; a record may support several. |
| Memory type | working, episodic, semantic, or procedural. | Memory type is what kind of cognition; function is why it is useful. |
| IntelligenceAccessPolicy | Hard query and visibility constraints. | Policy is permission; strategy is behavior. |
| IntelligenceSeekingStrategy | Control flow for querying, expanding, challenging, ranking, selecting, stopping. | Strategy is how; profile is what weights. |
| IntelligenceQueryProfile | Reusable soft priorities, weights, requirements, ranking preferences. | Profile is preferences; policy is hard limits. |
| IntelligenceSeekingBinding | Attaches policy, strategy, profiles, inheritance, overrides to any Loop, step, spawn, or invocation. | One universal binding schema. |
| ResolvedIntelligenceSeekingPlan | Exact immutable runtime plan with pinned versions and hashes. | A plan is resolved; a binding is authored. |
| IntelligencePortfolioSnapshot | Exact selected records for one invocation. | A snapshot is a result; a profile is a preference. |
| IntelligenceSeekingReceipt | Complete explanation of queries, candidates, rankings, selections, failures, costs. | The seeking report explains; a snapshot selects. |
| IntelligenceQuery | Typed backend-neutral query: layers, sources, kinds, lifecycle, attributes, limit. | A query is typed; raw SQL is a privileged escape hatch. |
| IntelligenceItemEnvelope | Named envelope for one intelligence item served through a Loop. | An envelope is data; the Loop serves it. |
| LensSpec | Role or method lens: focus, questions, blind spots. | A lens shapes context; a profile shapes queries. |
| Runtime Memory | Temporary run-scoped note board (working memory). | Runtime Memory is transient; the four layers persist. |

## 4. Catalog and storage

| Term | Definition | Difference from neighbors |
|---|---|---|
| Catalog | Unified logical identity, query, and resolution surface. | A catalog is logical; a store is physical. |
| CatalogStore | Protocol for backend-neutral record access. | One protocol; many adapters. |
| StoreCapabilities | Declared operations, query features, pushdown, transactions, authority. | Capabilities are declared; conformance proves them. |
| StoreHandshake | Negotiated verdict: compatible, read_only, degraded, incompatible... | A handshake is computed; never guessed. |
| AdapterRegistry | Named adapter registration with capability negotiation and selection. | A registry selects; the composite resolves. |
| CompositeCatalog | Ordered fan-out over stores with dedupe by (record_id, version). | Composite merges; each store is one backend. |
| PackageJsonlStore | Read-only streaming over Core JSONL shards. | Core authority; never writable. |
| DuckDBFileQueryEngine | SQL over JSONL/Parquet files. | A query engine, not the ontology. |
| DuckDBRecordStore | Writable embedded DuckDB authority. | One supported backend. |
| SQLiteRecordStore | Writable embedded SQLite authority. | One supported backend. |
| EphemeralRecordStore | In-memory reference implementation. | Reference for conformance. |
| UnifiedCatalog | Ontology catalog over package core, instance learned, and plugin roots. | Resolves at-rest records; CatalogStore serves them. |
| CatalogRecord | Passive persistent record at rest (formerly Node). | A record is data; never a Node. |
| Materialization | One physical representation of a logical record. | Identity never depends on materialization. |
| Authority | The representation permitted to accept canonical writes. | One authority per record version. |

## 5. Memory subsystem

| Term | Definition | Difference from neighbors |
|---|---|---|
| WorkingMemoryState | Bounded, run-scoped, Loop-scoped cognitive state with compartments, pinning, eviction, snapshots. | Working memory is transient; the other three persist. |
| EpisodicMemoryRecord | Immutable, versioned, time-ordered experience with Run History provenance and failures. | An episode is one experience; a semantic claim generalizes. |
| SemanticMemoryRecord | Evidence-backed generalized claim with validity, scope, confidence, contradiction groups. | Semantic is general; episodic is specific. |
| ProceduralMemoryRecord | Contracted, versioned know-how with applicability, permissions, verification, evidence. | Procedural is how-to; semantic is what-is. |
| MemoryQuery | Typed query over persistent memory with scope and lifecycle filters. | MemoryQuery queries memory; IntelligenceQuery queries intelligence. |
| MemoryRetrievalReceipt | Explained retrieval: candidates, rejections, scores, selections, conflicts. | The retrieval report explains; a snapshot selects. |
| MemoryReviewReceipt | Evidence of one independent review decision. | The producer cannot be the reviewer. |
| MemoryConsolidationReceipt | Evidence of one non-destructive consolidation. | Sources remain immutable. |
| InMemoryMemoryStore | Deterministic in-process store for persistent memory records. | Reference backend. |

## 6. Generation and campaign

| Term | Definition | Difference from neighbors |
|---|---|---|
| SeedArtifact | Starting material for generation: data, never a Node. | A seed is input; a candidate is output. |
| CandidateFragment | Smallest typed unit a generation operator may transform. | A fragment is a part; a candidate is a whole. |
| PromptBlock | One structured block of a model invocation prompt. | Blocks compose; strings render at the model boundary. |
| ConfigPatch | Typed configuration patch with declared merge semantics and frozen fields. | A patch overlays; it never silently expands. |
| VariationDimension | One typed axis of a generation variation space. | A dimension declares; expansion materializes. |
| ConditionalRule | One applicability constraint pruning the variation space. | Rules prune; dimensions vary. |
| GenerationCampaign | Bounded campaign: target, seeds, dimensions, rules, strategy, budgets, writeback. | A campaign generates; it never promotes. |
| GenerationOperator | One reusable generation transformation, typed data. | An operator transforms; a Loop executes it. |
| CandidateRecord | One generated, immutable, content-addressed candidate. | Candidate-only until independent review. |
| WritebackPolicy | Where candidates may be written: dry_run, shadow, candidate, reviewed, active. | may_promote is always false for generators. |
| CapabilityTaskDefinition | One typed task the campaign may execute. | A task is the work; the campaign is the harness. |
| CampaignRunManifest | Exact environment facts for one run, digest-pinned. | A manifest pins; a result reports. |
| TaskRunResult | One task execution with status, metrics, failures, elapsed time. | Failures are preserved, never hidden. |
| CampaignState | Accumulated campaign state with honest reporting. | State accumulates; the report summarizes. |

## 7. Core Architecture and runtime mechanics

| Term | Definition | Difference from neighbors |
|---|---|---|
| Core Architecture | The built-in, immutable, released portion of Core Code Intelligence. | Core is shipped; Learned is adopted after install. |
| LoopRuntimeContext | The three public ports plus internal mechanics. | Context is per-Loop; settings are global. |
| IntelligenceSearchRetrievalPort | Search, rank, select, materialize records from the four layers. | One of exactly three public ports. |
| WebResearchPort | Discover, fetch, inspect, verify permitted external sources. | One of exactly three public ports. |
| CustomPluginsPort | Discover and invoke registered capabilities through typed handshakes. | One of exactly three public ports. |
| EffectApprovalService | One exact effect, durable decision, one-use consumption. | Approvals bind one effect; never reused. |
| WorkspaceOperationService | Confined paths, explicit command policy, bounded output. | Workspaces confine; approvals authorize. |
| ContextArtifactManager | Digest-addressed raw storage with offloading and compaction. | Artifacts are payloads; records are metadata. |
| RunHistory | Persisted ordered event history with integrity checks. | RunHistory persists; LoopLedger is in-process. |
| ModelGateway | The one model invocation boundary with routes and failover. | All model calls cross the gateway. |
| CapabilityDirectory | Machine-readable handshakes and registered endpoints. | Discovery is effect-free. |
| BoundaryRegistry | Canonical operational-boundary register: every boundary joined to a role profile. | The register declares; conformance verifies. |
| StoreRecord / SolverStore | Legacy search/serve record shapes in core/store_serve.py. | Legacy shapes; the catalog stores are canonical. |
| DuckDBCatalogBackend | Query layer over JSONL files, never a second truth. | A derived index; the JSONL is authority. |

## 8. Development planes

| Term | Definition | Difference from neighbors |
|---|---|---|
| Development Engineering Plane | Code assistance, planning, editing, migration, testing, repair. | Engineering builds; Assurance certifies. |
| Development Assurance Plane | Independent auditing, evidence, conformance, adversarial review, verdicts. | Assurance is read-only by default. |
| Repository Assurance Practitioner | Root devtools supervisor running on the canonical Loop kernel. | A Practitioner, not a second engine. |
| Bootstrap verifier | Deterministic checks that run without importing Loop Engine. | A broken runtime cannot disable review. |
| RepositoryEntity | Non-operational record describing a file, symbol, class, test, manifest. | Entities are records; never Nodes. |
| AssuranceClaim | Claim to be supported or refuted with evidence. | A claim is asserted; evidence supports it. |
| FindingOccurrence | One observation of a problem in one snapshot. | An occurrence is specific; a pattern generalizes. |
| FindingPattern | Reviewed reusable intelligence generalized from occurrences. | Patterns require independent review. |
| AssuranceCase | Claim, argument, evidence, counterevidence, uncertainty, conclusion. | A case certifies; a finding reports. |

## 9. Conformance and contracts

| Term | Definition | Difference from neighbors |
|---|---|---|
| architecture.yaml | Machine-readable invariants, forbidden classes, forbidden paths, import boundaries. | The machine contract; the Constitution explains it. |
| terminology.yaml | Canonical terms, deprecated terms, forbidden class names, qualified terms. | The vocabulary contract. |
| CONSTITUTION.md | Normative invariants with stable IDs (LE-NODE-001...). | The prose authority. |
| architecture_contract.py | Validates the machine-readable contracts against the live tree. | Enforcement, not documentation. |
| repository_conformance.py | File-by-file, symbol-by-symbol, reference-by-reference harness. | Canary-proven detectors. |
| repository_structure.py | Tree, folder, README, and junk-drawer checks. | Structure rules, not exact snapshots. |
| runtime_ontology_check.py | Loaded-class audit, subclass-tree audit, gc instance audit. | Proves the live process, not just source. |
| backend_isolation.py | Provider imports confined to adapters; base package imports without optional backends. | Portability enforcement. |
| structure_review.py | Evidence packet for LLM semantic review with the no-waiver rule. | LLM may identify; never waive. |
| scheduling.py | ConcurrencyContract, SchedulingConfiguration, ConcurrencyDecision. | Typed parallel-safety decisions. |

## 10. The strongest distinctions

```text
Node is the category. Loop is the only operational runtime.

A definition is data. A Loop is the runtime.

A ref is a pointer. A capsule loads lazily.

A layer is storage organization. A function is why intelligence is useful.

A memory type is what kind of cognition. A function is why it is useful now.

A policy is permission. A strategy is behavior. A profile is preference.

A query is typed. Raw SQL is a privileged escape hatch.

A catalog is logical. A store is physical. A materialization is one representation.

A seed is input. A fragment is a part. A candidate is unapproved output.

A task is the work. A campaign is the harness. A report explains. A verdict certifies.

Engineering builds. Assurance certifies. Repair returns to Engineering.
Reverification remains independent.

The prompt is an emitted artifact, not the architecture.
```
