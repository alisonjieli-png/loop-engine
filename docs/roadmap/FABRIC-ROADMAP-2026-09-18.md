# Fabric roadmap: build, verify, next step

Date: 2026-09-18. Owner direction recorded the same day. This document is
the plan a development loop walks one step at a time. Each step names what
to build, the boundary that owns it, the command that verifies it, the
adversarial check that must fail when the behavior is removed, the evidence
to record, and its status. The machine-readable copy is
[roadmap.yaml](roadmap.yaml); a loop reads that file, picks the first step
whose status is `ready` and whose dependencies are verified, builds, runs the
verification, records the evidence path, and moves the status.

The working title "fabric" is a proposal under review in the
[branding record](../research/BRANDING-OPTIONS-2026-09-18.md). Product and
repository names stay Loop Engine until the owner decides.

## How a loop uses this document

```text
One roadmap iteration
├── read roadmap.yaml and pick the first ready step with verified dependencies
├── build only what the step names, at the boundary it names
├── run the step's verification commands on an export of the exact tree
├── run the adversarial check: remove the behavior, confirm the check fails
├── record the evidence path, the commit, and the date in the status log
├── move the status: ready -> building -> offline_verified -> live_qualified -> published
└── commit and push; a failed verification leaves the status at building with the failure quoted
```

Status vocabulary: `proposed` (named, not scheduled), `ready` (dependencies
verified, can start), `building`, `offline_verified` (checks and mutants
pass on an exported tree), `live_qualified` (a matched live run recorded the
behavior), `published` (on `main`, documented, in the changelog), `blocked`
(names what only the owner can supply), and `superseded` (names the
replacement). A step never moves to `offline_verified` from file presence
or intent; it needs the recorded command output.

## Requirements register

Each requirement carries the date of the owner direction that produced it,
the boundary that owns it, and its state today. States use the status
vocabulary above; `partial` means some named parts are published and the
rest are listed.

| Id | Requirement | Owner direction | Owning boundary | State |
|---|---|---|---|---|
| R-01 | Ask at every step whether this is the most efficient way, whether inputs or outputs are too big, which alternatives exist, and how confident each alternative is; let cheap judges (own models, language models, typed-decision services) make those calls. | 2026-09-18 | `core/step_efficiency_review` (proposed), `strings/question_engine` `efficiency_check` form and `practitioner.step_efficiency_review` contract (published) | partial |
| R-02 | Every component, including the four intelligence layers, is a Loop node with typed input and output. | 2026-09-18 | `loop/`, `core/boundary_registry`, intelligence Loop profiles | published for Loops; intelligence layer query Loops exist; provisioning manifest proposed |
| R-03 | A solutioning node is an independent harness instance given exactly the input it needs to make one decision or build one thing. | 2026-09-18 | `core/opencode_step_provision`, `core/step_content`, harness manifests | partial; provisioning manifest with tools, plugins, context files, contracts, hooks, and lookups is step S-2.2 |
| R-04 | Reasoning nodes and build or act nodes run in independent harnesses; execution nodes in the solutions space run with no reasoning. | 2026-09-18 | Loop modes and roles; `code_nodes/solution_export` | published for export; harness placement per node is S-2.2 |
| R-05 | A harness runs once or iteratively: it publishes a solution that lets dependent nodes run and keeps refining and publishing better alternatives. | 2026-09-12, 2026-09-18 | The discrete cognitive or act step Loop node explanation in `ASTRA.md`; `code_nodes/solutions_space` | published as explanation and record; iterative publication runtime is S-2.3 |
| R-06 | The solutioning space can enumerate every combination of values, inputs, and configurations per node and run them repeatedly to find the best. | 2026-09-18 | `core/configuration_grid`, campaign runner, `generation/` | partial; node-level grid with typed input parameters is S-2.4 |
| R-07 | A language model or reasoning step can choose the best set of solutioning nodes and the best set of solution nodes. | 2026-09-18 | meta-selectors (`configuration-preferences-and-meta-selection` guide) | represented; live qualification open |
| R-08 | Solution nodes with parameters get a grid and optimization (grid, Bayesian, evolutionary). | 2026-09-13, 2026-09-18 | `optimization` extra, `configuration-grid-search` guide | represented; runnable offline optimizer is S-3.4 |
| R-09 | Every harness instance receives the core tools, plugins, context, instruction files, contracts, hooks, loops, and lookups it needs to reach core intelligence (web research, intelligence layer queries) shipped with the project. | 2026-09-18 | Core Architecture ports; `core/capability_directory` | partial; provisioning manifest is S-2.2 |
| R-10 | External intelligence tools, plugins, and servers with authentication, as a paid feature. | 2026-09-18 | `core/custom_endpoint`, `core/mcp_adapter`, packaging tiers | represented; paywall tier is S-4.3 |
| R-11 | Run locally with every node on the host, or in the cloud where Kubernetes manages nodes and harness instances as containers. | 2026-09-18 | `core/workspace_backends` (Docker), `code_nodes/solution_export` (Job manifest), the published worker image (S-4.1, S-4.7) | partial; the image is published and the manifests validate offline; a cluster run needs the owner's account |
| R-12 | A working proof of concept of convergence and optimization end to end. | 2026-09-18 | evaluation product, configuration optimizer, node grid, convergence report | partial; offline convergence and noise injection landed (S-3.1, S-2.15); the live run is S-3.2 |
| R-13 | Research the business paths: own startup, partnering, joining a small startup for equity, and other options. | 2026-09-18 | `docs/research/BUSINESS-PATHS-2026-09-18.md` | offline_verified; the owner decides (S-5.2) |
| R-14 | Test with unseen tasks on a frontier model, then Kaggle tasks and hackathons, exporting solutions. | 2026-09-18 | campaigns, `solution_export` | blocked on a model key the owner authorizes; S-3.5 |
| R-15 | No heuristic decisions before one million recorded runs, except an exact fingerprint at the atomic level for reason, build, or execute; the data must be collected now in a versioned location fit for training specialized models. | 2026-09-18 | `core/model_call_records`, `core/operation_cost_records`, `core/reuse_evidence`, the training data store and `core/heuristic_adoption` | published (S-2.5); no live run feeds the store yet |
| R-16 | A roadmap with tests, checkpoints, status updates, and tasks that a loop can walk. | 2026-09-18 | this document and `roadmap.yaml` | published |
| R-17 | A live hosted proof of concept and a live hosted service that can charge. | 2026-09-18 | service software S-4.2, deployment S-4.4, billing S-4.5 | proposed; deployment and billing need owner accounts |
| R-18 | A documented Y in every column of the feature matrix, with every capability the compared companies have. | 2026-09-18 | the six-table matrix (S-1.9) | partial; seventy-five columns with two partial cells (task working folder, meta-selection) and two absent cells that need the owner (hosted cloud, public pricing) |
| R-19 | Consider a brand beyond Loop Engine, such as a frontier harness fabric. | 2026-09-18 | branding record S-5.1 | proposed |
| R-20 | Every contract names its matching mode; exact everywhere is brittle. | 2026-09-18 | `core/contract_matching` | published; review of remaining exact comparisons open |
| R-21 | Model calls under a model ontology with suggested outputs, recorded for later training. | 2026-09-18 | `core/model_ontology`, `core/model_call_contract`, `core/suggested_output` | published |
| R-22 | Solutioning space and solutions space as two named spaces. | 2026-09-18 | `code_nodes/solutions_space`, spaces document | published |
| R-23 | Persistence within declared authority at every component; giving up is not acceptable. | 2026-09-14 | supervision policy, failed-check review | published; live qualification continues |
| R-37 | Local resource detection and management: a supervisor keeps the number of live harness instances within what the machine carries, detects stalled instances and clears them through owned handles, pauses or hibernates a memory-heavy iterative instance and restarts it later, and logs every transition. | 2026-09-18 | `core/local_resources` (S-2.22) | building |
| R-38 | The same detection and management in the cloud, plus spinning up capacity within a client's budget and limits. | 2026-09-18 | quotas and spin-up policy (S-4.8), placement decision (S-2.23) | proposed; research recorded |
| R-39 | System administrators and client administrators manage resources, budgets, nodes, stalled instances, and logs from a front end. | 2026-09-18 | administrator surfaces (S-4.9) | proposed |
| R-40 | A node that is frozen keeps its memory; only a verified checkpoint and a confirmed stop release capacity, and a node continues to exist when its harness does not. | 2026-09-18 | `core/instance_hibernation` (S-2.24) | offline_verified |
| R-41 | Cost is reserved before work and reconciled afterwards, so a timeout never erases an outstanding liability. | 2026-09-18 | cost reservation ledger (S-4.10) | proposed |
| R-42 | Public skill repositories can enter as candidate Context Intelligence with their provenance, commit, and license recorded, while their scripts pass the code admission ladder separately. | 2026-09-18 | `core/skill_registry`, the skill pack importer (S-2.27) | partial; discovery and the admission record exist, the importer and the license refusal do not |
| R-43 | Every harness instance is started with an instruction file the engine composed from typed fields, in the name that harness reads, naming only the authority the step already holds, with a digest that can be recomputed after the run. | 2026-09-18 | `core/instance_instructions` (S-2.28) | offline_verified |
| R-44 | A harness is registered with a tested capability profile, not with a file name: its instruction discovery, precedence, documented ceiling, effective settings, and an observable confirmation that the instance loaded what it was given. | 2026-09-18 | harness capability profile (S-2.29) | proposed |
| R-45 | Capabilities travel as portable packages in the published plugin layout, carrying their skills and server declarations together, with a digest on every file and a license recorded; the engine adds its own qualification rather than redefining the package. | 2026-09-18 | portable capability package (S-2.30) | proposed |
| R-46 | What was offered, fetched, exposed to the model, used, and verified are five separate facts about one provisioning set, and a record never promotes one into another. | 2026-09-18 | provisioning set record (S-2.31) | proposed |
| R-47 | What a harness instance can be given is catalogued in one place as references with a digest, a size, a license, and declared effects, and never as a second copy of the record that holds the body. | 2026-09-18 | `core/harness_intelligence` (S-2.32) | offline_verified |
| R-48 | A run searches all four intelligence layers, returns typed references with the layer named, and loads a body only after selection. | 2026-09-18 | `core/adaptive_practitioner_orientation_capabilities`, `code_nodes/solve_runtime` (S-2.33) | offline_verified |
| R-49 | An outside service is recorded with its operator, its typed contract, the credential the host holds by name, the three authorities a call needs, its price with the source it was read from, and its qualification state; the credential value never appears. | 2026-09-18 | `core/external_service_intelligence` (S-2.34) | offline_verified |
| R-50 | The folder a module lives in carries its family, so no directory holds hundreds of unrelated files. | 2026-09-18 | the core folder tranches (S-3.7) | proposed |
| R-51 | The first paid surface is provisioning: what an instance can be given is listed and manifested for free with digests, and reading a body is the metered unit. A refusal is never metered and a body that no longer matches its digest is never served. | 2026-09-18 | `core/provisioning_server` (S-4.12) | offline_verified |
| R-52 | One atomic node becomes one provisioned folder: the instruction file in the name that harness reads, the assignment as typed fields, and a record of what was offered, withheld, and exposed. A reason node holds no write authority and a plan is provisioned whole or not at all. | 2026-09-18 | `core/node_provisioning` (S-2.37) | offline_verified |
| R-53 | Intelligence is filed on declared dimensions, closed where a wrong value is a policy error, so what suits a role, language, region, or sensitivity can be found and the combinations holding nothing specific can be named and generated. | 2026-09-18 | `core/intelligence_tagging` (S-2.35) | offline_verified |
| R-54 | The host authenticates once and leases that credential to every instance that needs it. A lease carries a scope, an expiry, and a use ceiling, never the value, and revoking the credential stops every lease at once. | 2026-09-18 | `core/credential_leases` (S-2.36) | offline_verified |
| R-55 | The first release hosts serving and deterministic work and leaves customer harness execution on the customer's machine, so no untrusted code runs here and no model allowance is required to demonstrate it. | 2026-09-18 | the hosting shape record (S-4.13) | ready |
| R-56 | A unit is metered only when the service observed it. A completion the service neither ran nor verified is never sold as a verified completion, and client reported telemetry carries that label wherever it is read. | 2026-09-18 | honest units (S-4.15) | ready |
| R-57 | Capabilities are generated against exact stated gaps, each carrying what would satisfy it, never in bulk against a guess. | 2026-09-19 | `core/capability_needs` (S-2.38) | offline_verified |
| R-58 | A guardrail narrows and never grants. Its category fixes how far its level can be relaxed, a narrower scope never loosens a wider one, and a rule that cannot be evaluated does what it declared in advance rather than passing quietly. | 2026-09-19 | `core/guardrail_intelligence` (S-2.39) | offline_verified |
| R-24 | One task working folder shared with Spawned Loops. | 2026-09-14 | source inventory, materials folder | partial |
| R-25 | Adaptable policies with lifecycle applicability. | 2026-09-16 | adaptable policies direction | proposed |
| R-26 | Reuse tiers and cost routing. | 2026-09-16 | reuse tiers direction, `core/reuse_evidence` | partial |
| R-27 | Adaptive cognition and atomic harness instances small enough to fingerprint. | 2026-09-16 | adaptive cognition direction | proposed |
| R-28 | Exceptions for data conformance can live in several places and be accessed in several ways. | 2026-09-18 | `code_nodes/text_conformance` five catalog layers | published |
| R-29 | A confidence score per correction; only low-confidence rows reach a model or browser research. | 2026-09-18 | `code_nodes/text_conformance` | published |
| R-30 | A solution can leave the solutioning space as a package, folder, container, and Kubernetes worker; publishing on a package index. | 2026-09-18 | `code_nodes/solution_export` | published for package, container, and Job; package index publication is S-4.6 |
| R-31 | Prompt construction elements (task background, context background, atomic information, inputs and outputs, expectations, format) and response-style requests (respond concisely, only what was asked) are declared dimensions that a grid can optimize. | 2026-09-18 | `strings/prompt_fragments`, configuration dimensions | proposed; S-2.7 |
| R-32 | Every setting or dimension at every level (space, graph, node, step, prompt, context, intelligence layer, harness, model, placement) is documented in one inventory, and the competitor comparison is rerun against what is built and what is planned. | 2026-09-18 | dimension inventory document, landscape record | proposed; S-2.6 and S-1.9 |
| R-33 | Middleware and wrapper abstractions so every boundary can be hosted in a microservice-style architecture. | 2026-09-18 | Core Architecture ports, `core/host_runtime`, service software | proposed; S-2.8 |
| R-34 | Pre-packaged basic intelligence: detection and correction nodes with confidence for addresses (postal standardization, address component extraction), fuzzy duplicate names and addresses, email verification and recovery, malformed field detection, database copy and deduplication; runnable with or without a harness call; a model double-check in declared scenarios. | 2026-09-18 | `code_nodes/text_conformance` family, capability directory | partial; text conformance published; S-1.10 |
| R-35 | Context Intelligence seeded by job description: companies, job titles, responsibilities, the questions such a person asks, the facts they use, and the code they reuse, in their country and language; also personas, geography, languages, and domain text such as chemistry. | 2026-09-18 | `strings/` seeds, example 11 seed space | proposed; S-1.11 |
| R-36 | Intelligence is stored and served through one store contract, never by editing text files: packaged JSONL and YAML ship as the default and are read and written through DuckDB or an equivalent with full create, read, update, and delete by tool or Python call; a server database (Postgres with vectors, BigQuery) serves wide rollouts; search characteristics (facets, embeddings) live in the database with a key that is a file location, an object store location, or a package reference such as `loop_engine.data.<collection>#<record_id>`; large bodies stay in files or packages; hybrid, iterative retrieval works over the same records; a rule refuses direct edits of intelligence files; every variation is analyzed for space, time, and flexibility and measured before one is chosen. | 2026-09-18 | `catalog/` (store protocol, adapters, composite), `core/record_operations`, `core/store_serve`, conformance scan | partial; the catalog contract and four adapters exist; S-2.9 to S-2.11 |

## Component tree

```text
Fabric (working title) on the Loop runtime
├── Solutioning space
│   ├── Practitioner Loops: reason, build, act, verify (custom or native harness)
│   ├── Harness instance provisioning manifest (S-2.2)
│   ├── Step efficiency review on every step (S-2.1)
│   ├── Node grid: typed inputs, configurations, repeated runs (S-2.4)
│   ├── Iterative publication: publish, keep refining, name every output used (S-2.3)
│   └── Escalation only for low-confidence work (published in text conformance)
├── Solutions space
│   ├── SolutionsSpaceRecord: plural, append-only, verified by cited report
│   ├── Standalone export: package, tests, manifest, Dockerfile, Job (published)
│   └── Execution nodes with no reasoning (exported entry points)
├── Intelligence layers as Loops
│   ├── Context Intelligence: serve, search, frame; temporal fact graph (S-1.1)
│   ├── Code Intelligence: resolve, invoke, load; reusable capabilities
│   ├── Runtime History and Solution Intelligence: search, replay, compare; versioning (S-1.2)
│   └── User Feedback Intelligence: serve, scope, interpret; shared memory scopes (S-1.3)
├── Assurance
│   ├── Independent verification (published)
│   ├── Evaluation product: frozen suites, graders, comparison reports (S-1.4)
│   └── Failed-check review waterfall (published)
├── Selection and economics
│   ├── Model routing (published) and model-versus-not decision record (S-1.6)
│   ├── Per-implementation cost records wired into runs (S-1.5)
│   ├── Harness and prompt optimization runnable offline (S-1.7)
│   └── Specialist training from recorded calls (S-1.8)
├── Data for learning
│   ├── Versioned training data store (S-2.5)
│   ├── Heuristic adoption policy: one million runs, atomic fingerprints allowed (S-2.5)
│   └── Learnable call records and cost records (published)
└── Delivery
    ├── Local placement: every node on the host (published for Docker workspaces)
    ├── Cloud placement: worker image and Kubernetes manifests (S-4.1)
    ├── Service software with tenants, keys, and metering (S-4.2)
    ├── Packaging tiers: hosted intelligence versus hosted compute (S-4.3)
    ├── Deployment and billing (S-4.4, S-4.5; owner accounts)
    └── Package index publication (S-4.6)
```

## Steps

Every step has: build, verify, adversarial check, evidence, status. Commands
run on an export of the exact tree, as `AGENTS.md` requires. `CONF` means
`python -m loop_engine --conformance`, `SELF` means
`python -m loop_engine --self-test`, `HARD` means the hardcoding delta
audit, `LINT` means the documentation lint over the full scope, and
`MUTANT` means a mutant script that removes the behavior and confirms the
named check fails.

### Phase 0: landed this week

| Step | What landed | Evidence |
|---|---|---|
| S-0.1 | Failed-check review, budget-phase routing, nomenclature fixes | commit `4609539` |
| S-0.2 | Model ontology, model call boundary, suggested outputs, contract registry, matching modes, solutions space | commit `c308674` |
| S-0.3 | Reuse evidence, learnable call records, operation cost records, engineering-lab question forms, dependency ratchet | commit `d58f2f0` |
| S-0.4 | Competitive landscape, monetization, binary feature matrix | commits `c327bd9`, `1ac2268` |
| S-0.5 | Text conformance with a confidence per correction, five exception layers, escalation requests, standalone export with isolated verification, example 26, `export` command | this batch |

### Phase 1: feature matrix parity

| Step | Build | Verify | Adversarial check | Depends on |
|---|---|---|---|---|
| S-1.1 Temporal fact graph | Typed facts with subject, predicate, object, valid-from, valid-to, source, and confidence in Context Intelligence; supersession and as-of queries through the existing search Loop. | `SELF` module check; as-of query returns the fact valid at a time and not its successor | Remove the validity check; the as-of check must fail | S-0.5 |
| S-1.2 Memory versioning | Immutable revisions with a current reference for intelligence records; history, diff, and rollback through the existing record service. | `SELF`; rollback restores the exact prior digest | Remove the revision write; the history check must fail | S-1.1 |
| S-1.3 Shared memory scopes | Scoped shared stores with writer identity and read visibility for concurrent Loops; namespaces run, project, organization. | `SELF`; two Loops write, each read sees the other's record with its writer identity | Remove writer identity; the visibility check must fail | S-1.2 |
| S-1.4 Evaluation product | `loop-engine evaluate --suite PATH`: frozen task population, graders, deterministic replay, comparison report with exact denominators. | `SELF`; the command runs a frozen suite offline and writes a report | Remove the denominator; the report check must fail | S-0.5 |
| S-1.5 Cost records wired | Every capability invocation and model call emits an operation cost record; `cheapest_implementation(operation)` query. | `SELF`; a run with one deterministic and one model implementation records both and names the cheaper | Remove the emit; the query check must fail | S-1.4 |
| S-1.6 Model-versus-not decision | A typed decision record per operation naming the candidates (deterministic resolver, small model, large model), the evidence, the cost, and the choice; written by the fast path and the escalation path. | `SELF`; text conformance escalation writes the record | Remove the record; the check must fail | S-1.5 |
| S-1.7 Runnable optimization | `loop-engine optimize --suite PATH --dimension prompt` or `--dimension harness`: proposes variants, evaluates on the frozen suite with deterministic graders, keeps the best under independent evaluation. | `SELF`; the command improves a seeded deterministic score on a fixture suite | Remove the acceptance gate; the check must fail | S-1.4 |
| S-1.8 Specialist training | Train a small specialist (multinomial naive Bayes, standard library) from learnable call records for a classification-shaped contract; export weights as JSON and register the result as a candidate resolver. | `SELF`; the specialist reaches a declared accuracy on a held-out split and never on the training split alone | Remove the split; the check must fail | S-0.3 |
| S-1.9 Matrix regeneration | Regenerate the feature matrix with evidence links for every Loop Engine cell, including planned rows for the roadmap steps. | `LINT`; artifact republished | A cell without an evidence link fails the matrix script | S-1.1 to S-1.8 |
| S-1.10 Detection and correction node family | Address component extraction and postal standardization (optional `usaddress` and libpostal adapters behind the same typed correction record), fuzzy duplicate detection for names and addresses with blocking keys, email recovery, malformed field detection, database copy and deduplication; each with confidence, a with or without harness-call mode, and a declared model double-check scenario. | `SELF`; each node conforms a fixture with named reasons and refuses an unknown mode | Remove the confidence; the outcome check must fail | S-0.5 |
| S-1.11 Job-description-seeded intelligence | A pipeline record that takes a company, job title, responsibilities, country, and language and produces candidate questions, facts, and reusable code seeds, staged as candidates for review; the first packaged seeds for three roles. | `SELF`; seeds are candidates, never active, until approved | Remove the candidate state; the check must fail | S-1.10 |

### Phase 2: fabric core

| Step | Build | Verify | Adversarial check | Depends on |
|---|---|---|---|---|
| S-2.1 Step efficiency review | `core/step_efficiency_review`: a typed record per step with input size, output size, size expectations from the contract, alternatives with confidence, the chosen alternative, and the judge kind (deterministic, specialist, model); a deterministic judge flags oversized inputs and outputs; the record is a learnable call record. | `SELF`; an oversized input produces a flagged record; a learnable row exports | Remove the size check; the flag check must fail | S-0.5 |
| S-2.2 Harness provisioning manifest | A typed manifest per harness instance: tools, plugins, context files, instruction files, contracts, hooks, lookups, intelligence access, external access with authentication, placement (local or container), and the exact input it receives; verified against what the harness loaded. | `SELF`; an instance that loads a file not in its manifest fails | Remove the load check; the check must fail | S-2.1 |
| S-2.3 Iterative publication | A Loop publishes a candidate output, dependent Loops start on it, the producer continues under its continuation conditions and publishes alternatives; consumers record exactly which output they used. | `SELF`; a consumer record names the output digest it used; a later alternative does not change it | Remove the output digest on the consumer; the check must fail | S-2.2 |
| S-2.4 Node grid | Each Loop node declares typed input parameters; a grid over the solutioning and solution nodes enumerates configurations, runs them repeatedly, and records represented, dispatched, evaluated, verified, and promoted counts separately. | `SELF`; a grid over text conformance thresholds runs offline and names the best cell by a deterministic grader | Remove the separate counts; the check must fail | S-1.7 |
| S-2.5 Training data store and adoption policy | A versioned dataset store (dataset id, version, digest, schema, split manifest, exclusions) for learnable records, and a `HeuristicAdoptionPolicy` that refuses adopting any heuristic beyond an atomic exact fingerprint until the declared run count is reached. | `SELF`; adopting a similarity heuristic at 999,999 runs is refused and an exact atomic fingerprint is allowed | Remove the threshold; the refusal check must fail | S-1.8 |
| S-2.6 Dimension inventory | One document listing every setting or dimension at every level: space, graph, node, step, prompt element, response style, context, intelligence layer, harness, model, placement, and economics, each with its owning boundary, initial choice, fallback order, and qualification state. | `LINT`; every dimension names a boundary | A dimension without an owning boundary fails review | S-0.5 |
| S-2.7 Prompt element and response-style dimensions | Prompt resources declare their elements (task background, context background, atomic information, inputs and outputs, expectations, format) and a response-style slot (concise, only what was asked, full); both are grid axes with recorded effects on verified outcomes and tokens. | `SELF`; a grid cell changes only the declared slot and the render digest records it | Remove the slot from the digest; the check must fail | S-2.6 |
| S-2.8 Middleware and wrapper abstractions | Typed service boundaries for the Core Architecture ports so each can run in process or as a microservice behind the same contract; request and response records, idempotency keys, and authority propagation. | `SELF`; the same contract passes in process and over a local service | Remove authority propagation; the check must fail | S-2.2 |
| S-2.15 Noise injection and explorative optimization | Perturb inputs, prompts, or catalogs of a frozen suite and require a candidate cell to hold its gain on the perturbed suite; explorative strategies from the campaign vocabulary run through the same acceptance gate. | `SELF`; a cell that wins only on clean inputs is refused | Remove the perturbed check; the refusal check must fail | S-1.7 |
| S-2.9 Intelligence storage analysis and measurement | A decision record that enumerates the storage and serving variations (files only, DuckDB over packaged files, SQLite, a server database with vectors, an analytics warehouse, package references, and a sidecar of search characteristics with body references), analyzes each for space, read and write time, offline availability, concurrency, and maintenance, and measures the existing adapters on one synthetic population; a recommendation with the measured numbers. | The record carries the measured table with its script and denominators | A variation without a measured row is marked unmeasured, never recommended | S-0.5 |
| S-2.10 Intelligence access contract and no-direct-edit rule | Every read and write of intelligence records goes through a catalog store call; the string bank and the question forms load through a store adapter; package references (`loop_engine.data.<collection>#<record_id>`) resolve through the catalog; a conformance scan refuses runtime code that opens an intelligence file for writing outside the declared adapters; a settings record names the default store per deployment profile (demo, self-hosted, hosted). | `CONF`; the scan finds a planted direct write and refuses it | Remove the scan; the planted write passes, so the check must fail | S-2.9 |
| S-2.16 Dated record folders by type | Superseded by S-2.17 and S-2.19: the [layout record](../architecture/REPOSITORY-LAYOUT-AND-RECORD-KINDS-2026-09-18.md) found that the folder already is the kind and that moving dated records breaks several hundred links for no information the index does not give. | none | none | none |
| S-2.17 Records index and folder charters | `tools/build_records_index.py` writes `docs/RECORDS-INDEX.md`, every version of each dated record under its folder and subject with the newest first; a README with a `Kind:` line in every docs folder; the conformance gate `docs_folders_without_a_charter_readme` with a canary. | tools test; `CONF` | A dated record added without regenerating the index fails the tools test; a docs folder with files and no chartered README fails conformance | none |
| S-2.18 Relayer declared boundaries | Move the implementation of each README-only package (`intelligence` first) out of `core` one boundary at a time behind the dependency ratchet, with import-boundary tests. | `CONF`; import-boundary tests | A move that raises the dependency-direction count above the ratchet fails | S-2.17 |
| S-2.19 Docs root specifications | Move the specifications at the `docs` root into their kind folders with redirect stubs so the root holds only entry points. | `LINT`; every moved link resolves | A moved record without a redirect stub fails the link check | S-2.17 |
| S-2.20 Typed action decisions over an element table | An indexed element table rendered as text lines, a declared action vocabulary with the browser vocabulary as the packaged default, a bounded request, admission under `typed_decision.action` that refuses an operation outside the vocabulary, a target outside the table, a typing operation without text, and a finishing operation with a target, and a decision that marks done or blocked as still needing independent verification. | `SELF`; eight killed mutants | A target outside the table or an operation outside the vocabulary must be refused | S-2.13 |
| S-2.21 Browser harness adapter | A page reader that builds the element table, an act adapter with declared effects and adaptive waits, and a live TypeSafe route; a done decision is accepted only by the independent verifier. | A recorded browser task with exact denominators | A done decision accepted without the verifier must fail | S-2.20, S-2.2, a key the owner authorizes |
| S-2.22 Local resource supervisor | `core/local_resources`: a measured snapshot (memory, pressure stall information, control group limits, load), an instance ledger with heartbeats and an append-only event log, admission against a ceiling derived from the machine, stall detection by heartbeat age, pause of the largest instance under memory pressure and resume on recovery, all through an injected controller that signals only owned handles. | `SELF`; mutants | An instance above the ceiling must be refused; a stalled instance must be stopped through its handle; an instance without a handle must never be signaled | S-2.2 |
| S-2.24 Hibernation and reservation | Four declared actions (yield, freeze, checkpoint and release, cancel); capacity reserved before a start and released only on a confirmed stop; the ordered hibernation protocol with a checkpoint that declares its restoration fidelity; a resume that reserves again and names unresolved effects; progress-aware stall assessment; a controller that signals only an owned process group. | `SELF`; eleven killed mutants | A freeze must not report memory released; capacity must not be released on an unconfirmed stop; a declared wait must not count as a stall | S-2.22 |
| S-2.27 Skill pack importer | Read SKILL.md front matter and body from a named repository and commit into candidate records through the store contract, with the license recorded and a refusal when none is stated; scripts and hooks take the separate code admission path. | `SELF`; mutants | A source without a license must be refused; a script must never become active through discovery | S-2.10 |
| S-2.25 Execution profiles | Direct execution, a retained worker pool, a process or sandbox per session, an isolated sandbox for untrusted work, a shared inference service, and a batch job, chosen per workload class instead of one shape for every node. | A measured comparison on one population | Two tenants must never share one writable environment | S-2.23 |
| S-4.12 Paid provisioning surface | Four operations over the harness catalogue: discover, list, manifest, read. Listing and manifests are free and carry digests and sizes; a body read is the one metered unit; a body is checked against its recorded digest before it leaves; the transport is injected rather than opened here. | `SELF`; mutants | A metadata tenant must never receive a body; a changed body must not be served; a refusal must never be metered | S-2.32 |
| S-2.34 External service capabilities | What an outside service can do for a run, with network, spending, and external change as three separate authorities, a credential named and never carried, a price that must name its source, and a qualification only a different reviewer can grant. | `SELF`; mutants | A credential value in a name field must be refused; a candidate must never be offered as qualified | S-2.10 |
| S-3.7 Folders that carry the family | Move one name family at a time out of the flat core folder into the subpackage its name already implies, with the architecture map, the folded self-test list, and every string that names a module moving in the same commit. | The full gate chain between tranches | A module named by a string must move with its file; a tranche that also changes behavior must be split | none |
| S-2.40 Spawned node provisioning | The folder a spawned node already receives is filled before the node starts: its instruction file, its typed assignment, and the record of what it was offered; the kind follows the authority the run granted rather than an objective sentence. | `SELF`; nine killed mutants | A blocking rule must refuse before the folder is filled; a run with no catalogue must be unchanged | S-2.37, S-2.39 |
| S-2.39 Guardrail intelligence | The recorded enforcement ladder as records a run can carry, search, and serve: four levels with none that permits, five evaluation points, categories whose level is fixed at blocking, an unavailable rule that refuses or escalates by prior declaration, and a review that examines a firing without changing the rule. | `SELF`; fifteen killed mutants | A protected category must not become a warning; a narrow scope must not loosen a wide one | S-2.35, S-2.37 |
| S-2.38 Capability need queue | The empty combinations of a coverage report become typed needs, each carrying its combination, its acceptance, and where to look first; a need becomes a build node whose objective states how the result will be judged. | `SELF`; ten killed mutants | A need without acceptance must be refused; a need must never claim to be a capability | S-2.35, S-2.37 |
| S-2.35 Tag dimensions | Seven dimensions, closed where a wrong value is a policy error and open where a list cannot be finished; alternatives within a dimension, requirements across them; coverage separates what a caller receives from what was written for that exact combination. | `SELF`; mutants | A general record must never count as covering a specific combination | S-2.32 |
| S-2.36 Shared authentication | One authentication held by the host, leased to each instance with a scope, an expiry, and a use ceiling; the value resolves at the point of use and never enters a folder; revoking the credential stops every lease. | `SELF`; mutants | A lease must never carry the value; a revoked lease must resolve nothing | S-2.28 |
| S-2.37 Node provisioning | One atomic node to one folder: instruction file, typed assignment, and the record of what was offered, withheld, and exposed; reason and build hold different authority; a plan is provisioned whole or not at all. | `SELF`; thirteen killed mutants | A reason node must never hold write authority; a half provisioned plan must be rolled back | S-2.32 |
| S-2.32 Harness Intelligence | One catalogue of what an instance can be given, in four kinds: reusable code, a skill, a tool, and an instruction file. Every item is a reference carrying a digest, a size, a license, and declared effects; an offer names what it withheld and why; where a body physically is and how much of it a model sees are separate fields. | `SELF`; seven killed mutants | An item without a digest must be refused; an item declaring an effect the step lacks must never be offered; a reference must never carry a body | S-2.28 |
| S-2.33 Four layer search in a run | The search a step performs reaches all four populations instead of packaged Context Intelligence alone, returns references with the layer named, and takes the reuse evidence the run holds as a ranking term. | `SELF`; six killed mutants | A catalog that is not a mapping of layers must be refused; evidence must reorder without removing; the search must make no model call | S-2.10 |
| S-2.29 Harness capability profile | Register each harness with its instruction discovery order, precedence rule, documented ceiling, effective settings, and a probe that observes what the instance loaded; an unobservable probe reports unknown. | `SELF`; mutants | Support recorded from a file name alone must be refused | S-2.28 |
| S-2.30 Portable capability package | Write and read capability bundles in the published plugin layout so a skill and its server declaration travel together, with a digest per file, the license recorded, and scripts taking the separate code admission path. | `SELF`; mutants | A digest mismatch must fail the import; a script must never activate through discovery | S-2.2 |
| S-2.31 Provisioning set record | One record per instance holding five separate facts: offered, fetched, exposed to the model, used, verified; plus whether a change needs a restart before it is active. | `SELF`; mutants | Installed must never be recorded as read, and exposed must never be recorded as used | S-2.2 |
| S-2.28 Instance instruction file | One file per harness instance in the standard name, with the names a particular harness also reads carried as data; composed from typed fields so no free text becomes an instruction; a section that names an effect the step does not hold refuses the dispatch; a digest in a trailing marker that verification recomputes. | `SELF`; thirteen killed mutants | A file the engine did not write must be left alone; a name that leaves the folder must be refused; verification must not trust the marker it reads | S-2.1 |
| S-2.26 Orphan recovery and shared residency | Recovery when contact is lost, and residency accounting so hibernating one instance cannot evict a model another still uses. | `SELF`; mutants | Lost contact must not release capacity or let a stale attempt publish | S-2.24 |
| S-2.23 Cluster placement decision | A measured study of one pod per node against a worker pool that hosts many nodes per pod, with the overhead per shape, the stall and hibernation mechanism per shape, and a queue with quotas for thousands of nodes. | Measured table with exact denominators | A placement claim without a measured overhead row is unmeasured, never recommended | S-2.22 |
| S-2.11 Search characteristics sidecar and hybrid retrieval | Facets, digests, and optional embeddings stored beside body references; a large body stays in a file, an object store, or a package; hybrid (lexical plus vector) and iterative retrieval over the same records through the existing Retriever; the same query answered by DuckDB and by a server adapter with identical results on the fixture population. | `SELF`; two adapters return identical ranked identities for the fixture queries | Remove the body reference; the large-body check must fail | S-2.10 |

### Phase 3: proof of concept

| Step | Build | Verify | Adversarial check | Depends on |
|---|---|---|---|---|
| S-3.1 Offline convergence run | A grid over conformance and a fixture task suite with deterministic graders, repeated runs, and a convergence report. | The report shows the best cell, the counts, and the failures | A run with a broken grader must not report convergence | S-2.4 |
| S-3.2 Live convergence run | The same grid on an authorized Ollama Cloud route, with provider outages recorded and the runner waiting within a declared wait. | Recorded trials, physical calls, and costs | A trial that ended on an outage must not count as evaluated | S-3.1 |
| S-3.3 Adversarial validation | Independent skeptics refute each claimed improvement; only survivors are recorded. | Refutations recorded beside claims | A claim without a refutation attempt is not accepted | S-3.2 |
| S-3.4 Runnable optimizer proof | S-1.7 on the live suite. | Improvement over the seeded baseline with exact denominators | Same as S-1.7 | S-3.2 |
| S-3.5 Unseen tasks and Kaggle export | Unseen tasks on a frontier model the owner authorizes; Kaggle tasks with the solution exported and run standalone. | Frozen population, evaluator, failures, calls, costs, exported package verification | An exported solution that imports Loop Engine fails | S-3.3 |

### Phase 4: hosted delivery

| Step | Build | Verify | Adversarial check | Depends on |
|---|---|---|---|---|
| S-4.1 Worker image and manifests | A digest-pinned engine image, a Kubernetes worker Deployment and Job templates, and a placement policy (local or container per node). | The image builds; the manifests validate; a Job runs example 26 inside the container | A manifest without resource limits fails validation | S-0.5 |
| S-4.2 Service software | `loop-engine serve --api`: tenants, keys stored as digests, per-tenant metering of verified completions, avoided model calls, optimize hours, and judgment depth; no prompt bodies stored. | `SELF`; a request without a key is refused; usage records carry no prompt text | Remove the key check; the refusal check must fail | S-4.1 |
| S-4.3 Packaging tiers | Hosted intelligence versus hosted compute; open core, self-hosted, hosted; the external intelligence tier behind authentication. | `LINT`; tiers document and pricing draft | A tier that meters outcomes fails review | S-4.2 |
| S-4.4 Deployment | Deploy the service and the site to the owner's cloud account. | A public health endpoint answers; a recorded run | Blocked until the owner supplies the account | S-4.2 |
| S-4.5 Billing | Payment provider integration with metered usage. | A test-mode charge recorded | Blocked until the owner supplies the account | S-4.4 |
| S-4.6 Package index publication | Publish `loop-engine` and an exported solution to a package index. | Installable from the index in a clean environment | Blocked until the owner supplies the account | S-0.5 |
| S-4.10 Cost reservation ledger | Estimated execution, external calls, provisioning, and retained infrastructure reserved before work and reconciled against actual charges afterwards. | `SELF`; mutants | A timeout must not erase an outstanding liability | S-2.24 |
| S-4.8 Cloud capacity within a client budget | Per-tenant quotas, a spin-up policy that stops at the declared budget, and the record of every scale decision. | A recorded scale-up that stops at the budget | A scale-up beyond the budget must be refused | S-2.23, S-4.2 |
| S-4.9 Administrator surfaces | Resource state, budgets, node counts, stalled instances, pause and resume, and logs for system administrators and, per tenant, client administrators. | Browser audit of the views | A client administrator must not see another tenant's nodes or logs | S-2.22, S-4.8 |
| S-4.7 Worker image publication | The publish workflow builds the digest-pinned image on every push to `main`, pushes it to the GitHub Container Registry under this repository as `main` and `sha-<commit>`, pulls it back by digest, runs `doctor`, and records the digest in the job summary. | The workflow run succeeds and the digest is recorded in this roadmap | A pushed image whose `doctor` command fails must fail the workflow | S-4.1 |

### Phase 5: business and brand

| Step | Build | Verify | Depends on |
|---|---|---|---|
| S-5.1 Branding record | Candidate names checked against repository, package index, and domain use; recommendation. | Record with verified checks | none |
| S-5.2 Business paths | Own startup, partnering, joining for equity, licensing; evidence from the landscape record; decision criteria. | Record | S-5.1 |
| S-5.3 Career research | Deferred by the owner until the engineering track is further along. | none | S-5.2 |

## Data collection and heuristic adoption

The owner's rule: make no heuristic decisions until at least one million
recorded runs exist, except an exact fingerprint at the atomic level for a
reason, build, or execute step. The infrastructure must collect the data
now. Today the learnable model call records, operation cost records, reuse
evidence, and stage evidence records exist as typed records. Step S-2.5 adds
the versioned dataset store and the adoption policy that enforces the rule.
Until then, no similarity-based routing, embedding-based blocking beyond
declared keys, or learned threshold is adopted; each is a proposal with its
required evidence count.

## Status log

Append one line per iteration: date, step, result, evidence path, commit.

- 2026-09-18, S-0.5, published as commit `fcca293` after the batch 6 gates
  (conformance, hardcoding, documentation lint, self-test, battery of 29
  steps) and fourteen killed mutants.
- 2026-09-18, S-1.1, S-1.2, S-1.3, published as commit `67d5d8f` after the
  batch 7 gates (battery of 30 steps including example 26) and thirteen
  killed mutants; the feature matrix cells for graph or temporal facts,
  memory versioning, and multi-agent shared memory now have tested behavior
  behind them and are regenerated at S-1.9.
- 2026-09-18, S-5.1, offline_verified; evidence
  `docs/research/BRANDING-OPTIONS-2026-09-18.md`.
- 2026-09-18, S-2.9, offline_verified; evidence
  `docs/architecture/INTELLIGENCE-STORAGE-AND-SERVING-2026-09-18.md` with
  the measured adapter table; decision: DuckDB over packaged files as the
  default, package references and a characteristics sidecar as the record
  shape, a server database behind the same contract for rollout.
- 2026-09-18, S-1.1, S-1.2, S-1.3, building: temporal facts, record
  versioning, and shared memory scopes pass their module checks; gates and
  mutants pending.
- 2026-09-18, research for S-1.10, S-1.11, S-2.7, and S-2.8 recorded in
  `docs/research/PREPACKAGED-INTELLIGENCE-AND-DIMENSIONS-2026-09-18.md`.
- 2026-09-18, S-2.6, offline_verified; evidence
  `docs/architecture/DIMENSION-INVENTORY-2026-09-18.md`, which places the
  twenty-five baseline node dimensions in the levels above and below and
  adds the deployment, space, graph, step, prompt, model call, intelligence
  access, solutions space, and economics rows with their owning boundaries.
- 2026-09-18, S-2.1, S-2.5, S-1.5, S-1.6, S-1.8, published as commit
  `b1fbcdc` after the batch 8 gates (battery of 30 steps) and eighteen
  killed mutants.
- 2026-09-18, S-1.12, S-2.15, S-3.1, S-1.4, S-1.7, S-2.4 published as
  commit `130c86c` after the batch 10 gates (conformance, hardcoding
  delta, documentation lint, self-test of 5,103 checks, battery of 32
  steps) and ten killed mutants; S-1.4, S-1.7, and S-2.4 had landed as
  `f8a2ec1` in batch 9.
- 2026-09-18, S-2.17 offline_verified and S-2.16 superseded: the
  [layout and record kinds record](../architecture/REPOSITORY-LAYOUT-AND-RECORD-KINDS-2026-09-18.md)
  answers the owner's folder question; every docs folder now states its
  kind; the records index lists 146 dated records under 143 subjects; the
  conformance gate and its canary hold new folders to the charter. S-2.18
  and S-2.19 proposed.
- 2026-09-18, S-1.11 offline_verified: seeded generation reads an
  occupation table through a declared column mapping (the O*NET and ESCO
  layouts ship as data), six hand-authored occupations generate 327
  candidate questions, facts, and code seed specifications, staging goes
  through a store contract and reports only acknowledged writes, and nine
  mutants including the candidate token replaced by registered are killed;
  the conformance scan now refuses a direct write to a packaged
  intelligence path outside the catalog adapters (S-2.10 partial).
- 2026-09-18, batch 11 published as commit `855ab32` after the gates
  (conformance, hardcoding delta, documentation lint, tools tests with the
  records index check, self-test of 5,131 checks, battery of 32 steps) and
  twenty-six killed mutants across the typed-decision, seeded generation,
  and layout scripts.
- 2026-09-18, the
  [skill repositories record](../research/SKILL-REPOSITORIES-AS-CONTEXT-INTELLIGENCE-2026-09-18.md)
  answers the owner's question about the twelve shared skill repositories.
  All twelve short links are dead, so every repository was resolved by
  search and marked inferred; eight resolved and two stayed unresolved
  rather than being guessed. Every SKILL.md read states only a name and a
  description, none declares its allowed tools, and six of the eight carry
  executable scripts. One repository states no license at all, which is no
  permission to redistribute, and one splits its license so that hosting it
  needs a commercial agreement. The importer is S-2.27, proposed, with
  R-42 registered.
- 2026-09-18, S-2.23 part measured: on this machine a container from the
  published worker image starts and exits in a median 230.4 milliseconds
  over ten runs, against 10.4 milliseconds for a process, about
  twenty-two times. That decides the short-node case between one pod per
  node and a worker pool. The cluster half of the study still needs a
  cluster, and no Kubernetes tooling is installed on this host.
- 2026-09-18, S-4.11 offline_verified: the strict total token ceiling now
  refuses with a code that names its cause and a remedy that names an
  existing control. An absent resolver is `token_bound_resolver_not_installed`,
  kept apart from the resolver that returned nothing, every failure code
  carries a remedy, the live probe record shows it, and the command help
  states that a strict ceiling needs an installed resolver. A rerun of the
  strict probe refused with zero dispatch and printed the remedy. Five
  killed mutants. Installing a qualified resolver for the Ollama route is
  still open.
- 2026-09-18, live route probe and folder rehearsal recorded in
  [the live route probe record](../verification/LIVE-ROUTE-PROBE-2026-09-18.md).
  A problem folder with an instruction file and a defective supplier file
  was accepted by the intake and reached orientation; a deterministic run
  ended `CAPABILITY_GAP` naming the missing model route instead of
  inventing a result. The one authorized live route answered a single probe
  call with a usage limit, so no live qualification is possible until the
  allowance is restored or a second route is authorized, and no further
  live calls were made. A strict total token ceiling refused before
  dispatch at every value because no token bound resolver is installed;
  that is S-4.11, ready.
- 2026-09-18, S-2.24 offline_verified: hibernation, reservation, and
  progress-aware stalls in `core/instance_hibernation.py`. A freeze keeps the
  memory and says so; only a checkpoint and a confirmed stop release it.
  Capacity is reserved before an instance starts and counted against the next
  admission; an unconfirmed stop keeps the reservation and is recorded. The
  protocol walks its steps in order and the report names the last one
  reached. A checkpoint declares its restoration fidelity and cannot claim
  more than the adapter performs. A declared wait on an authorized model call
  is not a stall; a heartbeat without progress is. Eleven killed mutants; no
  live harness has been hibernated yet. S-2.25 execution profiles, S-2.26
  orphan recovery and shared model residency, and S-4.10 the cost reservation
  ledger are proposed.
- 2026-09-18, S-2.23 ready: the
  [hosting and resource management record](../research/LOCAL-AND-CLUSTER-RESOURCE-MANAGEMENT-2026-09-18.md)
  reads the documented Kubernetes limits (110 pods per Kubernetes node,
  5,000 nodes, 150,000 pods), pod overhead, quotas, Indexed Jobs,
  autoscaling, and container checkpointing; Kueue, Argo Workflows, and
  Volcano for queueing; Ray, Dask, Celery, and Temporal for placing many
  small tasks on shared workers; gVisor, Kata, Firecracker, E2B, and Modal
  for sandboxes; Linux detection and control (pressure stall information,
  control groups, systemd scopes, signals, the freezer, CRIU) with a live
  test of an unprivileged systemd scope on this machine; the budget chain
  from currency to quotas; a four-shape decision table with every figure
  labeled documented, measured, or estimate; and the administrator needs
  against what exists. The measured placement study is the remaining work.
- 2026-09-18, S-2.22 offline_verified: local resource detection and a
  supervisor for harness instances in `core/local_resources.py` (measured
  snapshot with unknown kept distinct from zero, instance ledger with an
  append-only event log, admission within a ceiling derived from the
  machine, stall detection, pause under memory pressure and resume on
  recovery through an injected controller that signals only owned
  handles); eight killed mutants; no live harness run supervised yet.
  R-37 to R-39 registered; S-2.23, S-4.8, and S-4.9 proposed; the hosting
  and resource management research record is in progress.
- 2026-09-18, S-2.20 offline_verified: typed action decisions over an
  element table in `core/typed_action_decision.py` after the owner pointed
  at Jev Ultrafast from browser-use (facts read from the repository the
  same day are in the typed-decision research record); eight killed
  mutants; a live TypeSafe route needs a key the owner authorizes and the
  browser act adapter is S-2.21, proposed.
- 2026-09-18, S-2.7 offline_verified: prompt elements and response style
  are two integer-range grid axes in `core/prompt_elements.py` that address
  all 192 combinations exactly once, render only the selected elements
  plus the style instruction from a data table, refuse a selected element
  without text, and record the slot a cell changed in the render digest;
  five killed mutants; no live grid has measured the axes yet.
- 2026-09-18, S-1.10 building: duplicate detection landed as the second
  detection and correction family (`code_nodes/duplicate_detection.py`):
  names, addresses, emails, and phones keyed with the text conformance
  catalogs, five blocking keys so rows are never compared all against all
  by accident, a block above the size ceiling recorded as skipped, a
  confidence that is the weakest named field signal so a shared email with
  a different name is a possible pair for review and never a merge,
  clusters from duplicate decisions only, a dedupe proposal that names
  survivors and merged identities, and possible pairs escalated as typed
  decisions through the typed-decision route; eight killed mutants.
  Email recovery and malformed field detection followed in
  `code_nodes/field_recovery.py` with declared repair tables, the same
  apply, hold, and escalate bands, and a dominant-pattern margin; seven
  killed mutants. Database copy (`code_nodes/database_copy.py`) copies a
  delimited file or SQLite table to a new target with applied corrections
  and a dedupe proposal, never in place, with a manifest of digests and
  counts; six killed mutants. Address component extraction
  (`code_nodes/address_components.py`) splits a line into house number,
  street, unit, city, region, postal code, and country from declared
  patterns with a weakest-signal confidence, and the optional usaddress
  and libpostal adapters report unavailability instead of guessing; six
  killed mutants. S-1.10 is offline_verified; no live run has consumed a
  member yet.
- 2026-09-18, S-4.7 published: the first run of the publish workflow on
  commit `855ab32` pushed
  `ghcr.io/alisonjieli-png/loop-engine@sha256:5e97636b9e0e4d2301d4d0f7489dfe58a7c4b4e9760f91be0802039ef4002d01`
  with the tags `main` and `sha-855ab32`, the package is public, and the
  image was pulled back by digest and its `doctor` command run both in the
  workflow and from the development host; the matrix cell for a published
  image is now present.
- 2026-09-18, S-1.12 offline_verified: the fifth and last attack closed.
  The verification policy may declare `separate_route`; every verifier call
  then excludes the routes the producer's own calls used through the
  gateway's `excluded_routes`, the report records `route_separation/v1`, a
  run whose only route is the producer's ends unavailable with the reason
  on record, and the confirmation of a claimed check defect excludes the
  classification call's route; nine killed mutants. Separation is off
  unless declared, because a run with one authorized route cannot
  separate.
- 2026-09-18, S-5.2 offline_verified: the
  [business paths record](../research/BUSINESS-PATHS-2026-09-18.md) reads
  the latest funding or acquisition, partner programs, and open roles of
  seventeen landscape companies with a source and date per cell, lays out
  own startup, partnering, joining for equity, and licensing with decision
  criteria, and recommends a sequence (licensing decision first, partnering
  for evidence, own startup after a hosted proof of concept and a paying
  run, joining for equity as the fallback); the owner decides.
- 2026-09-18, S-2.13 offline_verified: the typed-decision route behind the
  model call boundary with the `typed_decision.choice` contract, admission
  rules, route validation, a specialist judge in process, an endpoint judge
  over an injected transport, and a suite with exact denominators; eleven
  killed mutants; no live provider route declared.
- 2026-09-18, S-4.1 offline_verified: the Dockerfile pins its base by
  digest and the image builds locally (75.8 MB) and runs `doctor`; S-4.7
  building: the publish workflow to the GitHub Container Registry lands
  with batch 11 and its first digest is recorded after the run. S-1.9
  offline_verified: the matrix generator refuses a Loop Engine cell
  without an evidence note; seventy-four columns across the six tables.
- 2026-09-18, S-1.12 building: four of the five attacks that succeeded
  are closed with checks and mutants (reuse evidence reaches retrieval as
  a bounded ranking term; the gateway writes a cost record per invocation;
  the fast path records its model-versus-not decision; the service binds
  the memory writer to the authenticated tenant); verification on a
  different route from the producer stays open. S-2.15 and S-3.1 building:
  noise injection refuses a memorizing cell, and the convergence report
  runs seeded rounds with honest stability.
- 2026-09-18, the feature matrix became six tables with fifty-two columns,
  one table per band, with vendor counts per table; competitor cells in
  added columns are unverified unless an earlier note supported them.
- 2026-09-18, S-1.12 ready and S-2.12 offline_verified: the
  [per-feature adversarial validation plan](../architecture/FEATURE-ADVERSARIAL-VALIDATION-PLAN-2026-09-18.md)
  lists the attacks and audit questions for all twenty features and five
  open attacks that currently succeed; the
  [component interface record](../architecture/COMPONENT-INTERFACES-AND-INTELLIGENCE-FLOW-2026-09-18.md)
  names every hop of a solve and nine inconsistencies; the
  [deployment shapes guide](../guides/feature-deployment-shapes-and-substitution.md)
  says how each feature is containerized, wrapped, and swapped; the
  [typed-decision model record](../research/JEV-TYPED-DECISION-INTEGRATION-2026-09-18.md)
  answers the Jev question and adds S-2.13.
- 2026-09-18, S-4.1, S-4.2, S-4.3, building: the repository `Dockerfile`,
  example 28 with a worker Deployment and a solution Job validated
  offline, the hosted service surface with tenants, digest-only keys,
  four endpoints, and metering, and the packaging tiers guide; the image
  is not yet built or digest-pinned, no endpoint is operated, and no price
  is set.
- 2026-09-18, S-1.4, S-1.7, S-2.4, building: evaluation suites with
  registered graders and exact denominators, the configuration optimizer
  with its train-gain and holdout-loss acceptance gate, and the node grid
  with separate stage counts pass their module checks; on the twelve-case
  company-name suite of example 27 the conformance solver passed eight,
  and the optimizer accepted, exhaustively over twelve cells, the best
  qualifying cell, a gain of three training cases without a held-out
  loss; gates and mutants pending.
- 2026-09-18, S-2.1, S-2.5, S-1.5, S-1.6, S-1.8, building: the efficiency
  review record with its deterministic judge, the versioned training data
  store with the heuristic adoption policy, operation cost capture wired
  into every capability directory call, the model-versus-not decision
  written for every text conformance escalation, and specialist training
  with a run-level split all pass their module checks; gates and mutants
  pending.

- 2026-09-18, S-2.28, offline_verified: every harness instance is now given
  one instruction file before its adapter runs. The file name is the one that
  has settled across harnesses, the second name a particular harness reads is
  carried as data rather than as a branch, and the body is composed from typed
  fields, so a model cannot write its own instructions. A section that names an
  effect the step does not hold refuses the dispatch by name, a file the engine
  did not write is left alone, and the digest in the trailing marker is
  recomputed by verification rather than trusted. The semantic harness
  dispatch installs a writer that declares the two effects a step folder
  actually grants. Thirteen mutants, no survivors; one of them found a check
  that asserted a refusal without asserting the refusal was seen, which was
  corrected rather than weakened.

- 2026-09-18, S-2.2, S-2.29, S-2.30, S-2.31, proposed: twelve harnesses, the
  skills format, the protocol, the plugin and bundle formats, and the container
  lock file were read from their own pages and recorded in
  `docs/research/HARNESS-PROVISIONING-STANDARDS-2026-09-18.md`. Four findings
  shape the provisioning work. The two most used formats, the instruction file
  and the file system skill, carry no digest, no signature, and no version
  field. No vendor neutral format states what an instance is allowed to do; the
  one candidate field is marked experimental by its own specification and one
  major harness omits it. Precedence has five different documented resolutions,
  and documented ceilings range from six thousand characters to eighty thousand
  with truncation that at least two vendors document as silent. Only one vendor
  documents any observable signal that a file was loaded. The skills extension
  to the Model Context Protocol, final on 2026-09-13, is the only format read
  that makes digest verification mandatory and binds an approval to the exact
  set of files, and it is the contract to model admission and pinning on.

- 2026-09-18, S-2.32, S-2.33, offline_verified: before this step, a
  measurement found that no caller on the run path reached the four layer
  query at all. A solve searched packaged Context Intelligence alone, which is
  one layer of four, through one capability. The search now reaches every
  installed layer, returns typed references with the layer named and no body,
  and takes the reuse evidence the run holds as a ranking term that reorders
  without removing. The catalog is installed as a builder, so a run that never
  searches pays nothing for it, and `solve_dependencies` makes what a run
  receives observable without running a whole solve, which is how the wiring
  itself is checked rather than the function behind it. Beside it,
  `core/harness_intelligence` holds what an instance can be given as
  references with digests, licenses, sizes, and declared effects. Thirteen
  mutants, no survivors.

- 2026-09-18, S-2.34, S-4.12, offline_verified: the owner's direction is to
  keep every way of running in parallel and configurable while the first
  version concentrates on setting these up, and to put a provisioning service
  behind a paid line so a caller can obtain everything that goes into a
  harness instance. The surface for that now exists offline. Listing what is
  available and asking for one item's manifest are free, because a caller
  needs identities, purposes, digests, sizes, and licenses to decide; reading
  a body is the metered unit, because that is the part with cost behind it. A
  refusal is never metered, an unknown key is compared in constant time, and a
  body that no longer matches its recorded digest is refused rather than
  served with a warning. Beside it, external services are recorded with their
  operator, contract, credential name, three separate authorities, price with
  a source, and a qualification only a different reviewer can grant. What is
  still missing is not software: an operated endpoint, a price, and a payment
  provider.

- 2026-09-18, S-2.35, S-2.36, S-2.37, offline_verified: the first release
  shape is one harness instance per atomic node, given exactly the files it
  needs. The spine for that now exists offline. A plan's slices become nodes
  only when each declares whether it reasons or builds, because those hold
  different authority; each node gets a folder with its instruction file, its
  assignment as typed fields, and a record separating what was offered from
  what was actually exposed to a model. Intelligence is filed on seven
  dimensions so the material for a role, a language, a region, or a
  sensitivity can be found, and so the combinations holding nothing specific
  can be listed and generated rather than guessed at. One authentication is
  held by the host and leased to every instance, which removes the worst
  consequence of one instance per node: a person being asked to approve the
  same access once per instance. Eighteen mutants, no survivors; three of them
  found checks that passed for the wrong reason.

- 2026-09-18, S-4.13, S-4.14, S-4.15, ready: two hosting proposals both began
  by asking which platform should run harness instances. The prior question is
  whether the first release hosts execution at all, and the measurements say
  it should not. The serving side holds twenty thousand capabilities in
  sixty five megabytes and answers a manifest in six microseconds, which is
  below the smallest tier any platform sells, so the platform choice is not an
  architectural one at this size. Transfer is the distinguishing cost: an
  unfiltered listing of five hundred references is four hundred times the
  manifest a caller wanted, which is an interface decision rather than a
  hosting one. The detection and correction families resolve with no model
  call, so a release built on provisioning and deterministic correction can be
  demonstrated today while the one authorized model route is answering with a
  usage limit. Two consequences were recorded that neither proposal drew:
  three of the four published metering units cannot be observed when the
  customer runs execution, and telemetry a client reports is evidence about
  what a client says happened.

- 2026-09-19, S-2.40, offline_verified: the provisioning spine was a
  subsystem no run reached. One seam closed that. A run already breaks a task
  into spawned subproblems, orders them by their dependencies, and forks a
  workspace folder for each one; that folder now receives the instruction file
  in the name its harness reads, the assignment as typed fields, and the
  record of what was offered, withheld, and exposed to a model, with the
  provisioning recorded on the owning ledger. The kind is derived from the
  authority the run already granted rather than from an objective sentence: a
  node authorized to write its workspace builds, and one that was not reasons.
  Five modules moved onto the run path together, and the import closure grew
  from 344 to 349 of 585.

## Unresolved questions for the owner

- Which cloud account and region host the proof of concept and the service.
- Which payment provider and which introductory prices.
- Which frontier model key is authorized for the unseen-task runs.
- Whether the product name changes, and to what.
- Whether the first release is the serving and deterministic shape, which
  needs no model allowance and no untrusted execution, with hosted execution
  following when a customer asks for it and chooses the backend.
- Whether Harness Intelligence becomes a fifth queryable layer beside the
  four, or stays a component that references them. The repository rule today
  is that a source format does not define a layer, and the layer vocabulary
  is closed and read by conformance, record identities, routing records, and
  query contracts, so adding a name is a wide change. The argument for it is
  that what can be handed to a harness instance is a purpose rather than a
  format, and purposes are what the other four layers are organized by.
