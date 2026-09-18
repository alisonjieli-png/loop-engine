# What powers each feature: subcomponents, dependencies, prerequisites, and the four intelligence layers

Date: 2026-09-18. Owner direction: break each feature into its
subcomponents, sub-architectural components, dependencies, and
prerequisites so everything that powers a feature can be tracked, and make
the four intelligence layers visible, because the matrix bands (memory,
procedures, assurance, selection, business) do not show Context
Intelligence, Code Intelligence, Runtime History and Solution
Intelligence, and User Feedback Intelligence as areas of their own.

This record does both. The first part maps the four layers to the
features and modules that realize them; the second part breaks every
feature into the pieces that power it. A prerequisite is something that
must exist or be configured before the feature works; a dependency is a
module or package the feature calls. Optional packages are named as such;
the engine's required dependencies are PyYAML and jsonschema only.

## The four intelligence layers as areas

```text
Intelligence layers and what realizes them
├── Context Intelligence: facts, instructions, personas, question forms, temporal facts
│   ├── stores: catalog adapters, the string bank, packaged data files
│   ├── serve, search, frame: intelligence_layers, retrieval, intelligence_loops, prompt_fragments
│   ├── temporal facts and versions: temporal_facts, catalog/versioning
│   ├── shared scopes: shared_memory_scopes
│   └── seeds by role: the job-description pipeline (S-1.11, proposed)
├── Code Intelligence: executable capabilities with identity, contract, tests, and digest
│   ├── registries: capability_directory surfaces, reusable_capability records, resolvers
│   ├── resolve, invoke, load: adaptive_practitioner_deterministic, capability_invocation
│   ├── packaged nodes: text_conformance family, specialists, exported solutions
│   └── admission: the reusable capability flywheel and qualification
├── Runtime History and Solution Intelligence: what ran, what it cost, what was verified
│   ├── run_history, product_outcome_store, solutions_space
│   ├── model_call_records, operation_cost_records, reuse_evidence, stage evidence
│   ├── evaluation reports, optimization results, node grid counts
│   └── training datasets and the heuristic adoption policy
└── User Feedback Intelligence: what people said and decided
    ├── the advice store (consult, advice_for, leave_advice)
    ├── typed task feedback slots and escalation answers
    ├── approvals and effect decisions
    └── reviewed candidates (accept, reject, rollback)
```

Every feature below names which layers it reads and which it writes. A
feature that writes no layer leaves nothing for the next run to learn from,
which is itself a finding.

## Feature breakdown

### Memory

| Feature | Subcomponents | Modules and records | Dependencies | Prerequisites | Layers read, written |
|---|---|---|---|---|---|
| Persistent memory | store contract; adapters (in-memory, SQLite, DuckDB, packaged JSONL); composite view; capability handshake; precondition writes | `catalog/protocol`, `catalog/stores/*`, `catalog/composite`, `catalog/handshake` | standard library; `duckdb` optional | a configured store per deployment profile (S-2.10) | reads and writes all four |
| Graph or temporal facts | fact record; interval normalization; functional-predicate refusal; supersession; as-of and as-of-all; neighbors; paths | `core/temporal_facts` | catalog store | a namespace; a writable store | Context (read, write) |
| Outcome changes retrieval | evidence record; posterior; surprise weighting; credit split; decay; first-strike; regime shift | `core/reuse_evidence` | none | a verified outcome to fold in | Runtime History (write); Context and Code (read) |
| Memory versioning | revision records; revise with precondition; history; diff; rollback | `catalog/versioning` | catalog store | a store that supports write | all layers it is applied to |
| Multi-agent shared memory | scope record; membership; visibility; signed writes; stale-write refusal; filtered reads | `core/shared_memory_scopes` | catalog store | member identities; a namespace | Context (read, write); User Feedback (write when notes are feedback) |

### Procedures

| Feature | Subcomponents | Modules and records | Dependencies | Prerequisites | Layers read, written |
|---|---|---|---|---|---|
| Procedures as instructions | question forms; ask strategies; personas; prompt resource bundles; seed dimensions | `strings/question_engine`, `strings/ask_strategies`, `strings/prompt_fragments`, `strings/*` | none | none for the packaged forms | Context (read) |
| Executable code reuse | resolver protocol; fast path; reuse opportunity, assessment, candidate, generalization, admission; capability records; aliases | `core/adaptive_practitioner_records.DeterministicTaskResolver`, `core/adaptive_practitioner_deterministic`, `core/reusable_capability_*` | catalog store for records | a registered resolver; `allow_fast_path_resolution` on model-led runs | Code (read, write); Runtime History (write) |
| Executes code or tools | workspace backends; command and file requests; Docker resource limits; effect approval; generated project execution | `core/workspace_backends`, `core/generated_project`, `loop/effect_approval` | Docker optional for the sandbox | a declared workspace and effect authority | Runtime History (write) |
| Standalone solution export | export specification; typed files; container specification; manifest with digests; isolated verification; conformance export builder | `code_nodes/solution_export` | standard library | a solution to export; an empty target | Code (read); Runtime History (write via the manifest) |

### Assurance

| Feature | Subcomponents | Modules and records | Dependencies | Prerequisites | Layers read, written |
|---|---|---|---|---|---|
| Independent verification | verification policy and request; probe planning; isolated oracle; read-only Docker execution; report acceptance; failed-check review; confirmation | `core/independent_verification`, `core/independent_probe_planning`, `core/independent_failure_review` | Docker for isolated execution | a frozen subject; a verifier route | Runtime History (write); Code (read) |
| Evaluation product | suite record; graders; case results; report; comparison; split; solver specifications; evaluate command and endpoint | `core/evaluation_suite`, `code_nodes/service_endpoints.solver_from_spec` | none | a frozen suite file | Runtime History (write) |
| Per-implementation cost records | cost record; ledger; implementation aggregates; comparison; capture with phases; directory wiring; cheapest query | `core/operation_cost_records`, `core/operation_cost_capture`, `core/capability_directory` | none | a ledger attached to the directory | Runtime History (write) |

### Selection

| Feature | Subcomponents | Modules and records | Dependencies | Prerequisites | Layers read, written |
|---|---|---|---|---|---|
| Model routing | route records; profiles; registry; tiers; gateway; accounting; admission; failover policy | `core/model_routes`, `core/model_gateway`, `core/model_ontology`, provider clients | provider credentials by reference | a configured route | Runtime History (write) |
| Model versus non-model choice | candidate; policy; decision; ledger fill; escalation decision | `core/implementation_choice` | cost ledger optional | candidates declared | Runtime History (read, write) |
| Harness or prompt optimization | parameter space; strategies; acceptance policy; cell evaluation; result; optimize command; node grid and ledger | `core/configuration_optimizer`, `core/node_grid` | evaluation suite | a declared space and a frozen suite | Runtime History (write) |
| Trains or exports specialists | learning records; training export policy; dataset versions; adoption policy; specialist specification, model, trainer, resolver | `core/model_call_records`, `core/heuristic_adoption`, `core/specialist_training` | none | recorded rows with run identifiers | Runtime History (read); Code (write as a candidate) |

### Business

| Feature | Subcomponents | Modules and records | Dependencies | Prerequisites | Layers read, written |
|---|---|---|---|---|---|
| Open source core | license; package metadata; extras | `LICENSE`, `pyproject.toml` | none | none | none |
| Self-hosted option | image recipe; worker Deployment; solution Job; offline validation | `Dockerfile`, example 28 | Docker and a cluster to run | an image build | none |
| Hosted cloud | tenants; digest-only keys; endpoints; handlers; metering ledger; serve command; tenant minting | `core/service_api`, `code_nodes/service_endpoints` | none | a tenants file; an operated endpoint (not yet) | Runtime History (write metering); User Feedback (none yet) |
| Public pricing | tiers; metered units; never-metered list | packaging guide | none | prices the owner sets (not yet) | none |

## Areas the matrix bands do not show

The owner asked for the kinds of memory, the integrations, the endpoints,
local and cloud usage, and the optimization methods to be visible as areas
of their own. Each row names the boundary and its state.

### Kinds of memory

| Kind | What it holds | Boundary | State |
|---|---|---|---|
| Runtime Memory | notes scoped to one run through the run's board | `core/runtime_memory` | published |
| Working memory | compartments with capacity, pinning, eviction, and compaction history | `memory/working` | published (demonstration store) |
| Episodic memory | what happened in a run: goal, acceptance, failure classes | `memory/episodic` | published (demonstration store) |
| Semantic memory | claims with subject, predicate, object, confidence, contradiction groups | `memory/semantic`, `strings/knowledge_state` | published (demonstration store) |
| Procedural memory | reusable procedures with purpose and applicability | `memory/procedural`, question forms, strategies | published |
| Temporal facts | triples with validity intervals in Context Intelligence | `core/temporal_facts` | published |
| Shared scopes | signed, membership-filtered memory across Loops | `core/shared_memory_scopes` | published |
| Versioned records | every previous version of any catalog record | `catalog/versioning` | published |

### Integrations, endpoints, and placement

| Area | Boundary | State |
|---|---|---|
| Model provider clients | `core/ollama_client`, `core/mistral_client`, `core/openrouter_client`, `core/openai_responses_client`, `core/custom_endpoint` | published; each in the network allow list |
| Model Context Protocol servers | `core/mcp_adapter`, `core/mcp_sdk_transport` | published as adapters used by Loops |
| Native harness recipes | `core/harness_*` recipes (OpenCode, Codex, Pi, Goose, Cline, Kilo, and others) | represented; qualification per profile |
| Plugins and skills | extension discovery, skill admission, plugin handshakes | published; admission before use |
| Web research | `core/brave_search`, `core/web_fetch`, `core/web_search` | published behind explicit access modes |
| Inbound endpoints | the hosted service surface (`core/service_api`), the Studio server, the MCP transport | published; no endpoint operated |
| Local placement | every node in one host process; Docker workspaces for effects | published |
| Cloud placement | the worker image, the Kubernetes Deployment and Job, tenant secrets | recipes published; not deployed |
| Outbound external intelligence with authentication | custom endpoints and provider routes with secret references | published; the paid tier is packaging, not code |

### Optimization and convergence methods

The owner named noise injection, explorative optimization, continuous
improvement, convergence, grid search, self-tuning, and the aim of
converging on the most efficient solution for every task with just the
right amount of information. Each is a method with a boundary and a
state; the last is the objective the others serve, and no method claims
it is reached.

| Method | What it does | Boundary | State |
|---|---|---|---|
| Grid search | Exhaustive enumeration of a finite declared space, counted as exhaustive only when every cell was evaluated | `core/configuration_optimizer` exact enumeration, `core/node_grid` | published |
| Explorative search | Seeded sampling of a space, and the campaign vocabulary's novelty, pairwise, beam, successive halving, evolutionary, and adaptive strategies | `core/configuration_optimizer` stratified sampling; `generation/model/campaign` strategies | sampling published; the campaign strategies are represented, not qualified |
| Noise injection | Perturb inputs, prompts, or catalogs to measure robustness of a verified outcome; a cell that only wins on clean inputs is refused | proposed (S-2.15) | proposed |
| Convergence | Repeated runs on a frozen suite with an acceptance gate; the best cell replaces the baseline only with a train gain and no held-out loss; a convergence report records the counts | `AcceptancePolicy`, `optimize`, S-3.1 report | offline published; live pending |
| Continuous improvement | Verified outcomes update reuse evidence; a successful execution becomes a candidate capability; candidates qualify through an independent review | `core/reuse_evidence`, the reusable capability flywheel | published; not consulted live |
| Self-tuning | The optimizer adjusts declared parameters, the adoption policy decides when a learned rule may be used, the specialist trainer produces candidate judges | `core/configuration_optimizer`, `core/heuristic_adoption`, `core/specialist_training` | published as candidates |
| Right amount of information | The efficiency review asks whether inputs and outputs are too big before a step; the context budget policy bounds what a step receives | `core/step_efficiency_review`, context budget policy | records published; the step that writes the review is not wired |
| Most efficient solution per task | The objective: for each task, the verified outcome with the fewest resources, chosen by evidence | the implementation decision, cost records, the evaluation product | the measuring instruments exist; no claim of reaching the objective |

## Findings from the breakdown

- Three features write Runtime History but read no layer back: the
  evaluation product, the optimizer, and cost records. The reuse evidence
  and the implementation decision are the readers, and neither is consulted
  in a live route yet (S-2.1 wiring, S-1.12 open items).
- User Feedback Intelligence is written by approvals, feedback slots, and
  reviewed candidates, but no matrix feature reads it at run time except
  through the advice store. An escalation answer from a person should
  land there and become a catalog layer for conformance (the fifth
  exception layer, not yet automated).
- The job-description seeds (S-1.11) are the only planned writer of
  Context Intelligence at scale; today the packaged forms and catalogs are
  hand-authored.
- Every layer has one storage authority in the design (the catalog) and
  two in practice (the string bank and the four-memory store), which is
  the storage decision's point 5 and inconsistency 2 in the component
  interface record.
