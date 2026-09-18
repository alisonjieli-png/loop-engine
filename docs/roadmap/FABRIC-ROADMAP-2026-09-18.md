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
| R-11 | Run locally with every node on the host, or in the cloud where Kubernetes manages nodes and harness instances as containers. | 2026-09-18 | `core/workspace_backends` (Docker), `code_nodes/solution_export` (Job manifest) | partial; placement policy and worker image are S-4.1 |
| R-12 | A working proof of concept of convergence and optimization end to end. | 2026-09-18 | campaign runner, evaluation product | proposed; S-3.1 to S-3.5 |
| R-13 | Research the business paths: own startup, partnering, joining a small startup for equity, and other options. | 2026-09-18 | research records | proposed; S-5.2 |
| R-14 | Test with unseen tasks on a frontier model, then Kaggle tasks and hackathons, exporting solutions. | 2026-09-18 | campaigns, `solution_export` | blocked on a model key the owner authorizes; S-3.5 |
| R-15 | No heuristic decisions before one million recorded runs, except an exact fingerprint at the atomic level for reason, build, or execute; the data must be collected now in a versioned location fit for training specialized models. | 2026-09-18 | `core/model_call_records`, `core/operation_cost_records`, `core/reuse_evidence`; training data store and heuristic adoption policy proposed | partial; S-2.5 |
| R-16 | A roadmap with tests, checkpoints, status updates, and tasks that a loop can walk. | 2026-09-18 | this document and `roadmap.yaml` | published |
| R-17 | A live hosted proof of concept and a live hosted service that can charge. | 2026-09-18 | service software S-4.2, deployment S-4.4, billing S-4.5 | proposed; deployment and billing need owner accounts |
| R-18 | A documented Y in every column of the feature matrix, with every capability the compared companies have. | 2026-09-18 | matrix gaps S-1.1 to S-1.9 | partial |
| R-19 | Consider a brand beyond Loop Engine, such as a frontier harness fabric. | 2026-09-18 | branding record S-5.1 | proposed |
| R-20 | Every contract names its matching mode; exact everywhere is brittle. | 2026-09-18 | `core/contract_matching` | published; review of remaining exact comparisons open |
| R-21 | Model calls under a model ontology with suggested outputs, recorded for later training. | 2026-09-18 | `core/model_ontology`, `core/model_call_contract`, `core/suggested_output` | published |
| R-22 | Solutioning space and solutions space as two named spaces. | 2026-09-18 | `code_nodes/solutions_space`, spaces document | published |
| R-23 | Persistence within declared authority at every component; giving up is not acceptable. | 2026-09-14 | supervision policy, failed-check review | published; live qualification continues |
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

## Unresolved questions for the owner

- Which cloud account and region host the proof of concept and the service.
- Which payment provider and which introductory prices.
- Which frontier model key is authorized for the unseen-task runs.
- Whether the product name changes, and to what.
