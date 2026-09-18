# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0]: unreleased

First public release.

### Added on 2026-09-18

- Three records for the September 18 direction: the
  [fabric roadmap](docs/roadmap/FABRIC-ROADMAP-2026-09-18.md) with its
  machine-readable copy, the
  [intelligence storage and serving decision](docs/architecture/INTELLIGENCE-STORAGE-AND-SERVING-2026-09-18.md)
  with the measured adapter table, the
  [dimension inventory](docs/architecture/DIMENSION-INVENTORY-2026-09-18.md)
  at every level, the
  [pre-packaged intelligence research](docs/research/PREPACKAGED-INTELLIGENCE-AND-DIMENSIONS-2026-09-18.md)
  with verified package and occupation-database facts, and the
  [branding options](docs/research/BRANDING-OPTIONS-2026-09-18.md).
- The first worker image is published:
  `ghcr.io/alisonjieli-png/loop-engine@sha256:5e97636b9e0e4d2301d4d0f7489dfe58a7c4b4e9760f91be0802039ef4002d01`
  (tags `main` and `sha-855ab32`, public package), pushed by the publish
  workflow on commit `855ab32`, pulled back by digest and its `doctor`
  command run in the workflow and from the development host. The feature
  matrix marks the image as published; the cells that stay absent are
  hosted cloud and public pricing.
- Verification on a different model route is implemented, closing the last
  open attack in the adversarial validation plan. `ModelGatewayConfig` and
  `ModelInvocationRequest` gain `excluded_routes`; the gateway drops the
  named routes from its plan and ends with `no_eligible_route` when nothing
  remains, with accounting kept certain. `IndependentVerificationPolicy`
  gains `separate_route` (off by default): the verifier's calls then run
  through a `RouteSeparatedSession` that excludes the routes the producer's
  own calls used, calls owned by verifier-profile Loops are not counted as
  the producer's, the report records `route_separation/v1` with the
  producer routes, the verifier routes, and whether separation was
  achieved, its independence label says so, a report that required
  separation and lacks it is refused at acceptance, and a run whose only
  route is the producer's ends with the verification unavailable and the
  reason on record. The failure review's confirmation of a claimed check
  defect excludes the classification call's route under the same policy.
  Nine mutants are killed.
- The [business paths record](docs/research/BUSINESS-PATHS-2026-09-18.md)
  (roadmap S-5.2) reads the latest funding or acquisition, partner
  programs, and open roles of seventeen landscape companies with a source
  and date per cell, lays out own startup, partnering, joining for equity,
  and licensing with decision criteria, lists every fact that stayed
  unverified, and recommends a sequence; it decides nothing.
- The repository layout is chartered. The
  [layout and record kinds record](docs/architecture/REPOSITORY-LAYOUT-AND-RECORD-KINDS-2026-09-18.md)
  separates a folder path, a classification tree, and a record file, and
  gives every top-level entry and every documentation folder its kind,
  naming rule, and version rule. Every documentation folder that holds
  files now carries a README whose head states `Kind:`, the conformance
  gate `docs_folders_without_a_charter_readme` counts any that do not, and
  its self-test plants an uncharted folder to prove the detector. The
  records index (`python tools/build_records_index.py`, committed as
  `docs/RECORDS-INDEX.md`) lists every version of each dated record under
  its folder and subject with the newest first, and its test fails when a
  dated record is added without regenerating it. The intelligence package
  README names the modules that implement each of the four layers.
- The worker image is digest-pinned and published. The `Dockerfile` pins
  `python:3.12-slim` by digest, the image builds locally and runs
  `doctor`, and the publish workflow builds it on every push to `main`,
  pushes it to the GitHub Container Registry under this repository as
  `main` and `sha-<commit>`, pulls it back by digest, runs `doctor`, and
  records the digest in the job summary.
- The feature matrix has seventy-four columns across its six tables. The
  twenty added columns name tested behavior (typed references before
  bodies, reuse evidence with credit split, suggested output shapes, the
  task working folder, run-scoped Runtime Memory, the fast path, the
  resolution package, multiplied question forms, action vectors,
  budget-phase supervision, contract matching modes, verification on a
  different route, the step efficiency review, meta-selection, the model
  ontology, the convergence report, packaging tiers, the machine-readable
  roadmap, the verified comparison, and the digest-pinned base image);
  vendor cells in added columns are unverified unless an earlier note
  supported them, and the generator now refuses a Loop Engine cell
  without an evidence note.
- Seeded generation by role or domain landed as the first
  job-description-seeded intelligence pipeline (roadmap S-1.11).
  `core/seeded_generation.py` reads an occupation table through a declared
  column mapping (the public O*NET and ESCO layouts ship as data, their
  files are not downloaded), turns each occupation into a seed batch of
  candidate questions from six general forms, fact triples, and code seed
  specifications emitted only for a whole-word verb match, and stages the
  batch through the catalog or the search and serve store contract, never
  a file, reporting only acknowledged writes. Six hand-authored
  occupations ship in `data/occupation_seeds.yaml` and generate 327
  candidate seeds. No path in the module emits any maturity but candidate
  and no function promotes or qualifies; nine mutants, including the
  candidate token replaced by registered, are killed.
- The conformance scan gains `intelligence_file_direct_write` and the gate
  `direct_writes_to_intelligence_files_outside_adapters`: a module outside
  the declared catalog adapters that opens a packaged intelligence path
  for writing, or calls `write_text` or `write_bytes` on one, fails the
  build; the canary plants such a write and a read and expects only the
  write reported. This is the durable form of the owner's rule that
  intelligence is written through the store contract, never by editing
  files (Constitution LE-DATA-002, proposed).
- The typed-decision model route landed behind the model call boundary
  (roadmap S-2.13). `core/typed_decision.py` bounds one question to at most
  ten declared candidates, builds a judgment model call with labeled parts
  and the registered suggested output, and admits an answer only under the
  `typed_decision.choice` contract: rows name exactly the declared
  candidates and sum to one within a named tolerance, the choice is the
  top row or an abstention with no choice, and a route without a judgment
  profile declaring label and probability outputs is refused before any
  judge runs. Two judges ship: a specialist judge over an in-process
  trained naive Bayes specialist with a declared memory ceiling, and an
  endpoint judge that maps a provider body received through an injected
  transport, so a Jev-class provider enters as a declared network adapter
  outside the module. Every decision passes the same route screen as every
  model call, writes a model call record with digests and counts only, and
  writes one operation cost record when a ledger is given. A typed
  decision suite scores a judge with exact denominators, and an erroring
  judge is errored, never correct. Eleven mutants are killed.
- The response contract registry gains `typed_decision.choice`: one chosen
  candidate from a declared set of at most ten, a probability per
  candidate as the row confidence, a decision confidence, and an
  abstention flag, with a ranked-list suggested output.
- Four of the five open attacks in the adversarial validation plan are
  closed. Reuse evidence now reaches retrieval: `Retriever` accepts reuse
  evidence by record identity and adds a bounded ranking term (a fully
  validated record overtakes one adjacent rank near the top, a discredited
  record sinks last, nothing is removed), and `IntelligenceSearchRequest`
  carries it. `ModelGateway` accepts a cost ledger and writes one operation
  cost record per invocation with the physical model calls and
  provider-reported tokens, unknown counts kept unknown. The fast path
  records the model-versus-not decision it made as an
  `implementation_decision` output on the deterministic attempt trace. The
  hosted service gains `memory_write` and `memory_read` endpoints whose
  writer is always the authenticated tenant, with declared shared scopes
  and a private scope per tenant. The optimizer gains noise injection
  (`optimize_with_noise` refuses a cell that loses held-out cases under a
  whitespace, case, typographic quote, or extra token perturbation) and a
  convergence report (`converge` runs seeded rounds and says whether the
  best cell stabilized). The fifth attack, verification on a different
  route from the producer, stays open.
- The
  [feature component breakdown](docs/architecture/FEATURE-COMPONENT-BREAKDOWN-2026-09-18.md)
  maps the four intelligence layers to the modules that realize them and
  breaks every matrix feature into subcomponents, dependencies,
  prerequisites, and the layers it reads and writes; the feature matrix
  gains an intelligence layers band.
- Four records for the September 18 review requests: the
  [per-feature adversarial validation plan](docs/architecture/FEATURE-ADVERSARIAL-VALIDATION-PLAN-2026-09-18.md),
  the
  [component interfaces and intelligence flow record](docs/architecture/COMPONENT-INTERFACES-AND-INTELLIGENCE-FLOW-2026-09-18.md)
  with nine inconsistencies, the
  [deployment shapes and substitution guide](docs/guides/feature-deployment-shapes-and-substitution.md),
  and the
  [typed-decision model integration record](docs/research/JEV-TYPED-DECISION-INTEGRATION-2026-09-18.md).
- The hosted service surface, the worker image recipe, and the packaging
  tiers. `core/service_api.py` serves health, conform, evaluate, and usage
  endpoints over the standard library HTTP server for tenants whose keys
  are stored only as digests; every request is authenticated before any
  work, endpoints are restricted per tenant, and metering records count
  verified completions, avoided model calls, optimize hours, and judgment
  depth with digests and never bodies. `loop-engine serve api --tenants
  PATH` runs it and `loop-engine --new-tenant ID --tenants PATH` mints a
  key shown once. The repository `Dockerfile` builds the engine image as a
  non-root user; example 28 carries a worker Deployment and a solution Job
  and validates them offline. The
  [packaging tiers guide](docs/guides/packaging-tiers-and-hosted-service.md)
  records hosted intelligence versus hosted compute, the three tiers, the
  metered units, and what is never metered. No hosted endpoint is operated
  and no price is published.
- An evaluation product and a runnable optimizer. `core/evaluation_suite.py`
  owns `EvaluationSuite` (a frozen population with a digest), six
  registered deterministic graders, `EvaluationReport` with exact
  denominators per status, grader, and tag, and case-level
  `compare_reports` that refuses different populations;
  `loop-engine evaluate SUITE --solver-spec SPEC` scores a text
  conformance rule set or recorded outputs. `core/configuration_optimizer.py`
  owns `ParameterSpace`, `AcceptancePolicy`, and `optimize`, which counts
  represented, dispatched, evaluated, and accepted cells separately and
  accepts a cell only when it gains on the training side and does not lose
  on the held-out side; `loop-engine optimize SUITE --solver-spec SPEC
  --space SPACE` runs it. `core/node_grid.py` owns `NodeGrid` over one
  node's typed parameters and `GridLedger`, which refuses skipped stages
  and claims exhaustive coverage only when every applicable cell was
  evaluated. Example 27 walks a grid over the company-name suite offline.
- The efficiency review a step records before it spends anything.
  `core/step_efficiency_review.py` owns `SizeExpectation`,
  `EfficiencyAlternative`, and `EfficiencyReview` with the judge kind
  recorded; the deterministic judge flags oversized inputs and outputs from
  declared limits and ranks the available methods cheapest first; a
  specialist or model review is built from the registered
  `practitioner.step_efficiency_review` contract. Records and training rows
  carry digests and sizes, never text.
- Versioned training datasets and the heuristic adoption policy.
  `core/heuristic_adoption.py` owns `DatasetVersion` (published as an
  immutable catalog record with schema, split counts, exclusions, digest,
  and run count), `TrainingDataStore` over any catalog store, and
  `HeuristicAdoptionPolicy`, which allows an exact atomic fingerprint and
  refuses every other heuristic until the declared run count (one million
  by default) is reached and the dataset version is published.
- The model-versus-not decision. `core/implementation_choice.py` owns
  `ImplementationCandidate`, `ImplementationPolicy`, and
  `ImplementationDecision`; `choose_implementation` picks the cheapest
  candidate that meets the verified rate over enough ledger samples and
  otherwise follows the declared fallback order, saying which happened;
  `decision_for_escalation` records the model as the next implementation
  when a deterministic pass fell below its threshold.
- Specialist training. `core/specialist_training.py` trains a multinomial
  naive Bayes specialist from recorded rows with a run-level split, refuses
  leaked splits, measures only on held-out runs, exports JSON weights, and
  registers a `SpecialistResolver` that answers only its typed task and
  never claims verification.
- Operation cost capture. `core/operation_cost_capture.py` times the
  declared phases with a monotonic clock, keeps unknown counts unknown,
  writes one record per implementation to the ledger, and names the
  cheapest verified implementation with the ranking it beat.
- Temporal facts and a fact graph over Context Intelligence records.
  `core/temporal_facts.py` owns `TemporalFact` (subject, predicate, object,
  validity interval, confidence, source, successor) stored as catalog
  records with artifact kind `temporal_fact`, and `FactGraph` with
  assertion, functional-predicate conflict refusal, supersession that
  closes the old interval and names the successor, as-of and as-of-all
  queries, history, neighbors, and time-aware paths. Nothing is deleted.
- Record versioning over any catalog store. `catalog/versioning.py` keeps
  every previous version as an immutable `record_revision` record with
  lifecycle `revision`, so ordinary queries do not see it, and offers
  `revise` under a precondition, `history`, `diff`, and `rollback` as a new
  version that names its origin.
- Shared memory scopes. `core/shared_memory_scopes.py` owns
  `SharedMemoryScope` (namespace, members, visibility) and `SharedMemory`,
  whose writes carry the writer identity, scope, and time, refuse
  non-members, and guard against stale concurrent writes by the version
  last read; reads are filtered by membership and visibility and show who
  wrote each record.
- Text conformance with a confidence per correction.
  `code_nodes/text_conformance_operations.py` imports only the standard
  library and owns seven operations (whitespace, Unicode, case with catalog
  and evidence exceptions, legal suffixes, phones, emails, websites), each
  returning the proposed value, a confidence that is the weakest named
  signal, and the reasons. `code_nodes/text_conformance.py` owns the typed
  layer: `ExceptionCatalogLayer` with five sources (packaged, task folder,
  column evidence, inline, escalation answers) merged in precedence order,
  `ConformanceRule`, `ConformancePolicy` with apply and escalate thresholds,
  `CorrectionRecord`, `EscalationRequest` bound to the `disambiguate_value`
  question form and the `text_conformance.escalation_response` contract,
  `ConformanceReport` with an idempotence proof, `propose_rules` from column
  profiles, the `TextConformanceResolver` that supports only a typed task
  record, and the `text_conformance` capability surface. The packaged
  catalogs live in `data/text_conformance_catalogs.yaml`.
  `CapabilityDirectory.default_directory` accepts typed `SurfaceRegistration`
  records so a code intelligence package registers its own surface and core
  imports nothing from it; the dependency direction ratchet stays at its
  baseline.
- Standalone solution export. `code_nodes/solution_export.py` writes an
  installable package (sources, console entry point, tests, manifest with a
  digest per file, Dockerfile, Kubernetes Job) from a typed
  `SolutionExportSpec`, refuses traversal, absolute paths, `loop_engine`
  imports, and secret-shaped text, and verifies the export in an isolated
  interpreter that cannot import `loop_engine`. The first exported solution
  is text conformance; `loop-engine export solution SPEC --out DIR` and
  `loop-engine export verify DIR` expose it, and example 26 runs the whole
  path offline.
- Two question forms, `disambiguate_value` and `efficiency_check`, and two
  response contracts, `text_conformance.escalation_response` and
  `practitioner.step_efficiency_review`, each with a ranked-list suggested
  output and a unit-interval confidence.
- A model ontology. `core/model_ontology.py` owns closed vocabularies for
  what a model is (generative text, judgment, classification, extraction,
  embedding, reranking, vision, forecasting, tabular foundation, custom
  trained), its determinism, placement, size class, provenance, input
  modalities, output kinds, and qualification state, and the typed
  `ModelProfile` a route or a tool declares. `ModelRoute.profile` is an
  optional typed field. `CapabilityHandshake.model_use` and `model_profile`
  declare whether a tool uses no model, calls a model service, or embeds a
  small in-process model; `validate_tool_model_use` refuses a tool that
  would load a service-sized model inside itself. No route declares a
  profile yet, and no route of a non-text kind exists.
- One model call boundary in front of the text seam.
  `core/model_call_contract.py` owns `ModelInput` parts typed by modality,
  `ModelCallRequest` with the purpose, model kind, named response contract,
  suggested output, and determinism expectation, and `ModelCallRecord`,
  which keeps digests and token counts and leaves unknown counts unknown.
  A text-servable request becomes the existing text invocation; any other
  kind is refused with `UnsupportedModelKind` naming the route it needs, so
  no image or table is flattened into a prompt by accident.
- Suggested outputs. `core/suggested_output.py` owns `SuggestedOutput`: the
  shape a step asks for (scalar, list, ranked list, table, object), its
  columns, cardinality, confidence scale, abstention rule, and the key it
  lives under. `ModelStepRequest.suggested_output` renders the suggestion
  into the packet's output contract, and an admitted answer outside the
  suggested shape is recorded as the advisory diagnostic
  `model.step.suggested_output_deviation`, never retried or failed. The
  first user is `decide_next`, which asks for a ranked list of at most ten
  candidates with an action kind and a confidence from 0 to 1.
- A response contract registry. `core/response_contracts.py` names and
  versions the JSON shapes the route, verify, criterion judgment, and
  failure confirmation steps ask for, builds their enumerations from the
  vocabularies that validate the answers, and renders the same JSON text
  the former inline literals produced. `ModelStepRequest.contract_id` names
  the contract; the packet's output contract, the
  `llm_work_packet_assembled` record, and the `model.step.started` trace
  event carry `output_contract_id`.
- The solutions space record. `code_nodes/solutions_space.py` keeps every
  published Solution Canvas for one task as a member with its graph digest,
  status, verification report digest, applicability, cost, and evidence.
  Adding a member never removes another, a member with the same graph
  digest is the same member, supersession names a successor, and
  `solutions_space_from_adaptive` projects a finished run's candidate
  canvases, verifying only the accepted canvas when the run is solved and
  holds a passed independent report. The run does not write the space yet.
- Contract matching modes. `core/contract_matching.py` owns the five ways a
  value is compared with a contract: exact, canonical (whitespace, case,
  quotes, and key order), purpose (required keys present with compatible
  types, extra keys allowed), semantic with blocking keys (the decisive
  keys stay exact and the remaining text must be similar above a declared
  threshold, measured deterministically), and model judged (decides
  nothing and names the judgment contract a separate call must answer).
  The criterion rubric now restates the registered criterion in canonical
  text instead of byte-exact text; an added sentence is still refused.
- Reuse evidence. `core/reuse_evidence.py` owns the rule for how one
  verified outcome changes what a reused record is worth: a recency
  weighted Beta posterior with a surprise term, a credit split across the
  records one outcome cited, first-strike tolerance for a long-validated
  record, a windowed regime-shift event, evidence labels (untested,
  validated, contested, discredited) kept separate from lifecycle status,
  inherited evidence for a restated claim, and a marked contrast lesson
  for a fail-then-succeed run. Design input: the evidence model in the
  raia-live/amfs repository at b9547b4, re-expressed in typed records.
- Learnable model call records. `core/model_call_records.py` joins a run's
  model step events into one record per call (contract identifier,
  prompt and output digests, attempts, rejections, suggested output
  deviations) labeled by the independently verified outcome, and exports
  training rows split by run so no run straddles the sides, excluding
  unverified outcomes, incomplete calls, synthetic records, and any row
  that matches the repository's secret patterns, each with its reason.
- Operation cost records. `core/operation_cost_records.py` keeps what
  each implementation of one operation cost by phase (setup, execution,
  verification, recovery) with the outcome it earned; unknown timings
  stay unknown, only verified complete records are averaged, and the
  comparison prefers the lowest mean total time, then fewer model calls.
- Engineering-lab question forms. Eight forms join the question engine:
  model necessity, implementation choice, train or call, data
  sufficiency, step confidence from 0 to 100, minimum context, a context
  boundary probe, and reuse before reasoning, each mapped to an existing
  question family.
- A dependency-direction ratchet. The conformance scanner counts imports
  from `core` into `code_nodes` (73 statements in 38 modules on
  2026-09-18) against a declared baseline in `forbidden_paths.json`; the
  count is published, the gate fails if it rises, and the baseline may
  only be lowered.
- Two research records: the SenseLab record with a source inspection of
  the raia-live/amfs repository at b9547b4, and the competitive landscape
  and monetization record comparing nineteen adjacent companies on
  packaging, pricing, metering units, and their overlap with Loop Engine's
  boundaries, with the metering units that fit Loop Engine's thesis.
- Six terminology entries: SolutioningSpace, SolutionsSpace, ModelProfile,
  ModelCallRequest, SuggestedOutput, and ResponseContract, with the
  dictionary projection and rendered dictionary regenerated.

### Added on 2026-09-15

- The independent verifier refuses a probe that infers the subject location.
  In the September 15 flash cell SCM-001, the subject report had already
  satisfied every registered criterion and passed its own checks, but the
  probe resolved the subject directory from its own file location and joined
  the subject file names to that parent, so execution failed with a missing
  source file and the verified-quality work ended `VERIFICATION_FAILED`.
  The probe design and file-generation prompts now state the exact container
  binding: one read-only working directory at `/workspace`, subject files at
  exactly `/workspace/subject/<name>` (also `subject/<name>` relative to the
  working directory), probe files under `checks/`. The oracle review is told
  to refuse probe code that infers the subject location from the probe file,
  and plan validation refuses that shape at plan time with a repairable
  `subject_location_inferred` diagnostic naming the declared binding, before
  any sandbox run spends a cycle.
- A model-led solve may declare a fast path. The recorded policy skipped
  the deterministic attempt in a model-led run entirely, so a task a
  registered exact resolver could already complete still spent a full
  reasoning loop on it, and no run could apply a habit before deliberate
  reasoning. `AdaptivePractitionerRequest` and the public `SolveRequest`
  take `allow_fast_path_resolution` (default false, so the recorded
  `SKIPPED_LLM_LED` policy stands undeclared), exposed on the command line
  as `--allow-fast-path`. With the allowance, registered exact resolvers
  run before the first model call: a completed verified fast path finishes
  the run with zero model calls, and an incomplete trace stays preserved as
  hybrid-repair evidence before semantic orientation proceeds. The
  allowance never applies to the deterministic mode, which already runs
  exact resolution.
- A supervision policy can declare budget-phase routing. In the September
  14 matched rerun, ten cells spent their entire declared call authority
  generating new candidates and ended `BUDGET_EXHAUSTED`, with earlier
  passing work left unverified: a budget was a wall the run hit at full
  speed. `SupervisionPolicy` now takes optional `budget_phase_thresholds`,
  one or two strictly descending fractions of the whole-run call authority.
  When the remaining-call fraction reaches the first threshold the phase is
  `conserve` and exploration routes (`explore_branch`, `continue`, `retry`,
  `soft_reset`, `cold_restart`) are demoted to consolidation; at the second
  the phase is `final_verify` and the run presents its best available result
  for verification instead of any new generation. The demotion is recorded
  as a `budget_phase_route_demoted` diagnostic, never demotes a verified
  success or an honest stop, and without a declared policy or without a
  declared maximum the phase is `explore` and no behavior changes. The
  default policy declares no thresholds.

### Changed on 2026-09-14

- An unverified task-level outcome now returns a complete
  `task_resolution_package/v1` instead of an empty blocked product. The
  package preserves completed work, observed evidence, model analysis,
  assumptions, missing or unverified material, scenario choices,
  provisional file bodies, alternative approaches, questions, and next
  actions. `COMPLETED_PARTIAL` means the useful response is complete while
  the original requested outcome remains unverified. Provider interruption
  and operator cancellation keep their operational terminal codes.
- The Practitioner receives a versioned best-available-resolution policy.
  Before a task-level stop it considers safe pro forma analysis, synthetic
  examples, estimates, analogous solutions, first-principles approaches,
  supplemental artifacts, and missing component maps. None of these may
  invent facts, authority, independent verification, or external effects.
- A user-facing material question now requires a matching typed
  `USER_CLARIFICATION_REQUIRED` ambiguity. Questions about runtime
  capabilities or workspaces remain internal. An inline task pack with no
  external source references no longer enters the impossible state where
  project generation requires the unavailable `core.source.inspect`
  capability.
- Every selected action now binds an `action_intent_vector/v1`, and every
  semantic stage exports `outcome_vector/v2`. Response admission, observable
  process alignment, harness or capability execution, expected action output,
  requested task output, local verification, material progress, continuation,
  downstream use, branch contribution, invalidation, and whole-task outcome
  remain separate tri-valued signals. A normal stop is rejected while safe
  authorized continuation remains. The policy is bound by the owning
  Practitioner Loop for the custom, OpenCode, Codex, Pi, and other registered
  harness paths. An adapter cannot grade or accept its own vector.
- A best-available resolution now assesses every registered safe method
  exactly once and requires mapped content for every completed method. The
  task-database campaign retains complete-source execution and evaluation as
  one lane and sends missing-source or missing-instruction tasks through a
  separate best-available-resolution lane that cannot enter original-task
  success denominators.
- A public solve request can declare its supervision policy.
  `SolveRequest.supervision` takes a typed `SupervisionPolicy`, the solve
  command reads one from `--supervision-policy FILE` through the strict
  `SupervisionPolicy.from_dict`, and the policy now reaches the Starting
  Practitioner Loop's configuration and every Spawned Practitioner it starts.
  Before this change a solve run always used the default policy, and a
  declared policy reached only the kernel's pass counts, not the Loop-level
  identical-failure limit, iteration backstop, or spawn depth guard.
- A stalled format repair no longer ends a run. When a model step repeats an
  invalid output or uses all four format repairs, orientation records the
  stall and makes its repair attempt, verification treats the verifier as
  unavailable and routes to repair, project generation records a typed
  refusal, and routing falls back to its deterministic policy or reframes
  when the recovery panel stalls. Each stall stays in Run History, and the
  run ends only through a declared limit or another recorded reason.
- A rejected orientation no longer ends a run. The orientation step asks
  again for the whole record with each finding quoted, then asks only for the
  fields that the findings name, and then carries the best orientation
  forward with its findings recorded. A carried orientation withholds only
  what the findings protect later steps from: an immediate goal that
  describes the orientation step, verification obligations that describe the
  orientation protocol, and questions or an ask action that the orientation
  policy did not accept. The declared supervision policy decides when a
  repair strategy is exhausted, and only spent model-call authority or an
  unavailable provider ends orientation. Results list each carried
  orientation. Before this change two rejected proposals raised an error. In
  a live Ollama Cloud rerun on September 14 that ended five of the first nine
  trials after two model calls, because the prompt showed the step objective
  as the task's immediate goal and the model copied it. The prompt now leaves
  the immediate goal empty until an orientation exists.
- A recovery panel directive now passes the same action vector guard and
  final acceptance binding as the model's route. Before this change a stalled
  pass adopted the panel's route unchecked: `stop_unprofitable` could end a
  run while the action vector recorded safe authorized work, and
  `stop_success` skipped the exact verification binding.
- The independent verifier now repairs a response whose format is not
  admitted. It asks again with the failure on record, as Practitioner steps
  do, and stops at a repeated identical response, at the shared bound of four
  format attempts, or when no declared model call remains. Before this change
  one inadmissible response made the whole independent report unavailable.
- Supplied archives are unpacked before the Practitioner starts, as a person
  would unpack a project's files. Zip, tar, gzip, bzip2, and xz archives are
  recognized by their content, unpacked into the run's materials folder, and
  unpacked again when they contain further archives. The source inventory
  walks that folder, so a text file inside an archive can be inspected,
  profiled, selected, and delivered to a project like any other supplied
  file. Unpacking needs declared workspace write authority, stays within the
  capacity this machine measures, refuses entries that would leave their
  folder, links, and devices, skips archives whose bytes were already
  unpacked, and records everything it unpacked or refused in the result's
  `task_materials` record.
- A supplied binary file, such as a spreadsheet, an image, or a Parquet table,
  can be selected for a project's inputs. `core.source.inspect` accepts its
  path and returns its size, digest, and media type, marked not readable by the
  model, and never its content; the project receives the exact bytes, and the
  runtime facts list these files with their sandbox paths. Hidden, linked, and
  protected files stay excluded for every purpose. The profile operation moved
  to `core.source_profile` to make room in the source module and is
  re-exported for existing callers.
- New task database campaign configuration spaces declare `attachment_files`
  as `supplied`. Every admitted attachment then reaches the run as a source
  file, as a person saves each attachment into a project folder, and bounded
  inline delivery still includes the text in the prompt. A saved
  configuration without the setting keeps its recorded `inline_only`
  behavior, so a matched rerun does not change. The artifact task trial
  accepts the setting, and each trial records it with its selected sources.
- An unverified run now presents its latest execution whose checks passed as
  the best available result when a later execution failed its checks. A
  verified run still presents its latest accepted attempt.
- The independent verifier's oracle review prompt is a governed constant
  beside its design prompt. It keeps every refusal class, states that an
  expected value recomputed from the task is required evidence and not a
  hardcoded observation, and lists only defects as issues. The design prompt
  asks for `timeout_seconds` as a number of seconds.
- A model recovery that independent verification declines is now recorded in
  the verifier's Run History with its phase, error code, whether it was
  reasoned, the selected option, the blocker, and the reason, and the refusal
  then stands. In a live rerun two verifier calls reached the output limit, and
  no record showed why no retry followed.
- The independent verifier can judge a natural-language deliverable, such as
  a customer message, a report, or a plan, against its registered acceptance
  criteria. A probe case may declare `criterion_judgment`: the probe prints
  the deliverable text read from the subject files, the case restates one
  registered criterion word for word, and a separate model call judges that
  criterion from the task, the criterion, and the printed text alone. The
  judgment passes only when it is satisfied and every quoted passage appears
  in the printed text, and validation grounds each stored judgment again
  without a model call. In the September 14 rerun on `2aaa5d5`, all five
  oracle reviews for CS-001 refused probes that searched the customer reply
  for literal phrases, as stricter than the task or looser than its criteria,
  so no check program could accept or reject the reply.
- The independent verifier's review prompt states that an expected value
  stated by the task or its criteria is independent evidence and that one
  copied from the subject is not. The design prompt asks a probe to run the
  subject's code, queries, or scripts instead of reimplementing their logic.
  In the rerun on `2aaa5d5`, one AE-001 review refused expected rows taken
  from the task as hardcoded values that should have come from the subject's
  SQL model, and two AE-001 probes reimplemented that model in Python instead
  of running it.
- A failed independent check is now reviewed before it forces repair. In the
  September 14 rerun on `2aaa5d5`, an approved FIN-001 probe searched the
  exception report with fixed patterns and failed a report that stated the
  requested totals and its refusal to approve payment, on five later
  attempts, because the retained check is reused and nothing asked whether
  the check was wrong. An isolated review call now classifies the failure as
  a correct failure, a wrong expectation, a check stricter than the task, an
  environment defect, an ambiguous requirement, or unknown. Every finding must
  quote evidence that appears in the failed cases, the probe source, or
  excerpts of the authored and produced subject files, and supplied inputs
  are never sent. A correct failure names the part of the work to repair. A
  claim that the check is wrong needs a second isolated call that confirms it
  with its own quotes. The revised check is designed with the disputed check
  and both reviews as untrusted feedback, passes the normal oracle review, and
  must fail on the same subject with its authored and produced files emptied
  before it runs on the real subject; otherwise the original check and its
  failure stand. Acceptance checks that discrimination again from the stored
  records, and one failed report is reviewed once.
- A criterion judgment response may carry additional fields. Grounding reads
  only `satisfied`, `evidence`, and `reason`, so a judge that adds a note is
  no longer failed for it.

### Fixed on 2026-09-14

- A planned probe file response that gives only its content no longer makes
  independent verification unavailable. It receives the path its plan
  declared, as a fenced body already did, and records that representation. A
  response with a different path or another shape is asked again through the
  bounded format repair and is never rebound to the declared file. In a live
  rerun this made a correct first attempt impossible to verify.
- A refused independent probe case now names the case and the field to
  repair, such as a `timeout_seconds` written as text. The earlier generic
  refusal gave the plan repair nothing to change, so a live model repeated the
  same value until its plan attempts ran out. Which plans are accepted is
  unchanged.
- An independent oracle review can now approve checks for a task with several
  acceptance criteria. Its response contract showed one example criterion
  reference, live reviewers copied it, and admission requires the covered
  references to match every registered criterion, so such an approval was
  refused. The contract now shows one item per registered criterion.
  Admission is unchanged: a review must be valid, list no issues, and cover
  exactly the registered criteria.
- `RETURN_RESULT` now submits the latest execution whose checks passed when a
  later attempt failed its checks, instead of the failed attempt. In a live
  rerun the Practitioner returned a passing attempt for verification twice,
  rewrote it into a failing attempt, and could then return only that failure.
  The submitted record becomes the latest task result, so verification,
  routing, and the final result read the same attempt, and no project runs
  again. The runtime facts name the attempt that would be submitted and whether
  its checks passed.
- Recovery reasoning now runs for every model session the model authority
  admits. A campaign builds its authority with a session factory whose session
  wraps the in-process one, and recovery reasoning and recovery learning
  required the in-process class, so in every campaign trial a failed model
  call got no reasoned recovery and no recovery call was made. Both now check
  the session contract that the authority already enforces: `invoke`,
  `results`, `calls_used`, and `accounting_uncertain`.
- The independent verifier now names each undeclared file when it refuses a
  subject, and says how to repair it. In the September 14 rerun on
  `2aaa5d5`, DA-001's third attempt passed its checks, but its program wrote
  `analysis.md`, the requested analysis, without declaring it as an expected
  artifact. All eight verification attempts were refused before any model
  call with "independent subject has undeclared dependency files", which named
  no file, so the Practitioner could not tell what to declare. The refusal
  still stands. It now names up to ten files and asks that each file the
  project's commands write be declared as an expected artifact.
- A malformed method assessment from the model no longer discards a finished
  run's outcome. The model-facing resolution contract listed every method
  identifier in the value position, and a live model returned that list, or a
  one-item array, as each `method_id`; building the best-available resolution
  then raised, and a campaign trial lost its whole outcome. The contract now
  shows one assessment per registered method with a single text identifier, a
  one-item array is read as its single choice, and an assessment that still
  cannot be admitted is replaced by dispositions derived from the preserved
  material, with the refusal reason listed as unverified material.

- An accepted, deterministically verified result now publishes and stops by
  default when the verifier still lists optional work. `OutcomeVectorPolicy`
  1.1.0 adds `after_acceptance`, with `publish_and_stop` as the default and
  `continue_while_work_remains` kept as an explicit level. Before this fix
  an accepted result could keep running without a bound, and a correct
  deliverable was reported unsolved.
- A best-available resolution is `COMPLETE` only when substantive work
  completed a method: observed artifacts, inspections, provisional outputs,
  the Practitioner's own resolution contribution, or recovery alternatives.
  A restatement of the task and the runtime's recovery hint stay visible but
  complete nothing. Provider interruptions and cancellations report
  `OPERATIONAL_INTERRUPTION`. `COMPLETED_PARTIAL` names only a complete
  package, so a run with no model now returns `CAPABILITY_GAP` with a
  constraint report.
- The integrated resolution and vector work passes the gates. The practitioner
  portfolio manifest digest, ontology index, architecture map, semantic
  projection, dictionary page, and packaged `architecture.yaml` and
  `terminology.yaml` copies are current; the work-function catalog is
  registered; three modules declare size exceptions with split plans; and
  eighteen new hardcoding findings are fixed at their owning boundaries with
  byte-identical prompt text. Campaign page cells show the underlying failure
  code, and `task_database/`, `task-campaign-runs/`, and `stub-test/` are
  ignored.
- Eleven recursive spawn checks failed once the verification response
  required an `action_vector`: the spawn fixture scripted one shared answer
  that assessed only `criterion:0`, while each verify step registers its own
  criteria. The fixture now scripts answers that assess exactly the criteria
  each step registers; the stricter contract is unchanged.
- A refused generated project command keeps its reason. `construct()` used
  to replace typed refusals, such as the inline code refusal that names the
  admitted command shape, with `commands[N]: invalid_value`, so the next
  proposal had nothing to change. The refusal keeps its location prefix.
- A source inspection or source profile request for a path that was not
  admitted now names each matching exclusion with its reason, for example
  `repo/binary.bin (binary_or_unsupported_encoding)`. A basename, an
  absolute path, or a path inside an excluded directory matches. Only paths
  and reasons are reported, never excluded content.
- An independent verifier case may declare a comparison policy.
  `json_equal` and `text_equal` keep their meaning, `json_subset` lets
  observed objects carry fields the case does not constrain, and a JSON
  policy may declare a finite non-negative `absolute` or `relative`
  tolerance. Plan validation refuses a malformed tolerance, and the oracle
  review is asked to refuse a policy looser than the task justifies. Each
  new check was confirmed to fail when its fix is removed.
- Product solve acceptance failed with `VERIFICATION_FAILED` once the
  verification response required an `action_vector`: its scripted verifier
  answers carried no vector, so format repair consumed the answer queue.
  The acceptance oracle now binds each scripted verification answer to the
  criteria registered in the actual verify prompt, and the answer declares
  only whether requested work remains. The stricter contract is unchanged.

### Fixed on 2026-09-13

- The hardcoding delta gate is green again on `main`. The experiment
  evidence commit had introduced ten new high findings: raw tokens that
  select behaviour now come from closed vocabularies at their owning
  boundary (`SETUP_UNAVAILABLE_REASONS` in the harness process adapter,
  `CORE_TIER` and `GATED_TIER` beside `TIERS` in the store, the existing
  `MODEL_INVOCATION_EVENT` in the Studio run detail, `SOURCE_IDENTITY_KINDS`
  in the campaign source snapshot, `NATIVE_GATEWAY_HARNESS` in the artifact
  trial), and the artifact trial's instruction texts are governed prompt
  resources in `strings/prompt_fragments.py` (`ARTIFACT_TRIAL_*_PROMPT`,
  identified by `ARTIFACT_TRIAL_PROMPT_RESOURCE`), whose identity the trial
  state now records. No behaviour changed; the model-facing prompt text is
  byte-identical.
- The self-improvement review counts its run population exactly. The
  population is the directories holding a manifest, saved runs and
  append-only checkpoint stores alike (a store loads as its latest
  checkpoint, so the campaign's step histories are reviewable); an
  artifact directory beside its run is reported under
  `ignored_directories` and no longer takes a selected run's place, which
  with a limit of one used to select the artifact directory and review
  nothing. One ledger projected twice under two run ids no longer counts
  as two independent runs: `RunHistory.content_digest()` names what a
  history records rather than which projection recorded it (the run id,
  the chain links, and the synthesized start event's projection time are
  dropped, the ledger's own timestamps kept, so a genuine repetition at
  other times stays distinct), the loader excludes each later copy naming
  the run it repeats, and the pattern miner deduplicates on that digest
  beside the run id and the chain head.
- A Practitioner request declares its supervision policy. `AdaptivePractitionerRequest`
  takes a typed `supervision` (the non-progress and unaccepted-pass counts,
  the escalation ladder, the spawn depth guard) and threads it to the
  kernel, so a campaign's per-cell ceiling is a configuration level rather
  than the repository default; the outcome names the policy that applied,
  declared or default, and a request digest moves only when a policy is
  declared. An untyped value is refused.
- A Practitioner run whose fresh candidates the verifier keeps refusing
  now reaches the honest stop. The live pro cell on CS-001 made more than
  470 model calls and consumed over 14 million tokens with sixty
  verification rounds and no end in sight: every pass produced a new
  candidate, so the kernel's non-progress guard saw progress on every
  pass, the Practitioner's own exit condition is `steps_complete` so the
  iteration backstops for `accepted_success` Loops never applied, and the
  route reasoner kept choosing repair. The kernel now applies the declared
  supervision policy's `unaccepted_passes_before_stop` to its own passes
  when the caller declared no pass budget: after that many passes without
  an accepted verification it climbs the same ladder (soft reset with the
  failure memory, cold restart, then `stop_unprofitable`), each trigger
  with its own count, and an accepted pass resets it. A declared pass
  budget keeps its own meaning. This bounds such a run to three times the
  policy's count, twenty-seven passes by default. The next pass's reasoning
  sees the supervision knowns as facts (passes refused so far, the count
  at which the ladder climbs, escalations used, the ladder), so the route
  reasoner can stop honestly before the ladder does. The allowance the
  runaway cell spent was gone again by 02:04 UTC: the flash worker's next
  access check was refused with `usage_limit_reached`.
- `RunHistory.verified_checkpoints(root, run_id)` settles every revision
  of an append-only store from one reading of the shared log (a revision
  is intact when no link before its count is broken and the digest at its
  count is the head it recorded). The evidence report had reloaded and
  re-digested the log once per checkpoint: a live cell with sixty-nine
  checkpoints over six thousand events took over forty-five seconds to
  verify and now takes a quarter of a second.
- Schema repair is told which declared field failed. The first finished
  live cell (deepseek-v4-pro on AE-001, eighteen calls, no verified
  artifact) spent twelve admissions on `schema_constraint_failed:minItems`
  with no field named, so the repair prompt could only say "an array is
  too short". The admission policy now has an opt-in
  `report_constraint_paths`, under which each failure also carries the
  schema's own path to the constraint (`schema_constraint_at:
  properties/steps/minItems`); it names what the trusted contract
  declared, never a candidate's keys, and a contract's digest is unchanged
  unless the policy is on. The Practitioner's own step, planning, and
  recovery contracts turn it on.
- A fallback order that names an uninstalled harness no longer fails the
  assignment before any attempt. The first live campaign cell with
  `harness_fallback: registered_alternatives` failed at the trial boundary
  with a process error while loading the alternatives' configurations,
  before its first model call, because the process spec refuses an
  executable that is not installed here. `load_harness_binding` and
  `load_harness_fallback_binding` now accept `allow_unavailable`, under
  which such a declaration registers as an `UnavailableHarnessAdapter`
  (`available=False` with the exact reason), so the executor answers
  `adapter_unavailable`, the failure kind the fallback policy already
  knows, and moves on; a malformed declaration refuses either way.
- Campaign activation and safety, after a same-night offline
  [review](docs/verification/CAMPAIGN-ACTIVATION-REVIEW-2026-09-13.md) of
  the Codex session's activation gate, access check, and worker: a page in
  the provider's place (a login page, a proxy notice, a 200 body with an
  error field) no longer drains the queue, because the harness accounting
  check accepts the ledger's reported zero and the gateway's absent usage
  as one description of one response, and the typed
  `invalid_response_body` code reaches the worker as a counted call and an
  outage to wait on; hexadecimal reference
  ids are dropped before any bare-digit status rule reads an error body; a
  suspension resets the per-cell attempt counter so a restarted worker
  waits its full ceiling; the activation gate refuses a non-text time
  instead of opening for a null. A self-contained campaign page
  (`devtools/embodiment_lab/campaign_report.py`) renders a campaign root's
  coverage, evidence links, accounting from each cell's own outcome, and
  population by job family, from exported records only, counts the
  worker's access-probe calls from their own saved histories apart from
  task calls, shows a cell whose projection the running worker holds
  locked as in progress, and draws the campaign's grid: every visited cell
  placed at its index in the declared configuration space with a
  coordinate on each axis, one mark per cell by job family and status
  across the space's full cardinality, and the counts by axis level; a
  cell whose configuration is not an address of the space is counted as
  unindexed, never placed. Left
  open for the Codex session: acknowledging an interrupted occurrence,
  engine identity over the controller and package resources, and
  route-stop on a single generic 400.
- Append-only Run History checkpoints. `RunHistory.append_checkpoint(root)`
  stores every event once and one checkpoint line per call (revision,
  events covered, head digest), so N checkpoints of an n-event history
  store n events rather than n(n+1)/2 as N full copies do; a history that
  diverges from the stored prefix is refused, never written over.
  `load_checkpoint(root, run_id, revision)` rebuilds the history at any
  checkpoint from the shared log's prefix and verifies the chain and the
  recorded head; a tampered log is a typed integrity error.
  `extend_from_ledger` grows a history with its ledger while keeping the
  prefix it already projected (a rebuild from the whole ledger cannot,
  since the synthesized start event is timed). The campaign runner now
  keeps one history per trial, grown by extension and checkpointed after
  every invocation into that store, so the per-step full copies whose
  growth the Codex session named as the remaining storage problem are
  gone; every checkpoint stays referenced and reloads at its revision, and
  the evidence report verifies either layout.
- The built-in Ollama adapter can learn a model's output ceiling from the
  service's own refusal (`learn_output_capability`): one streamed request
  for far more output than any model allows, on the OpenAI-compatible
  path; a 400 that names exactly one maximum yields a source-backed
  capability, an accepted request is closed on its first byte and recorded
  as acceptance without a ceiling, and a refusal by allowance or credential
  stops a batch. When the allowance reset at 00:25 UTC on September 14 the
  batch read all thirteen missing maxima from the service's refusals in
  one request each (the wording names the number beside a reference id
  and a model name with digits, which the parser now sets aside), so every
  one of the nineteen listed models carries a source-backed output maximum
  in the built-in table.
- A provider's stated wait is honoured. A refusal that carries
  `Retry-After` is waited for before the same route is retried, up to a
  sixty-second ceiling, and the ledger records what was stated, what was
  waited, and whether the ceiling cut it; a throttle that states no wait
  gets the fifteen-second backoff the Practitioner had documented but never
  applied, recorded as unstated; the recovery reasoner now sees the
  failure's class and the stated wait as facts beside the code. The
  guided setup asks the wire format instead of inferring it from port
  11434, suggesting one from the URL's path, so a hosted Ollama at
  `https://ollama.com` is not offered the OpenAI path. The campaign's
  per-cell evidence report re-verifies what disk can prove instead of
  trusting the writer's flags: a saved step history's chain is reloaded and
  verified, a delivered artifact must exist with its recorded digest, and
  an applied configuration must be reported applied and be the trial's
  own; the report names the links it re-verified and any disagreement
  between what was recorded and what it confirmed.
- Ollama adapter path, after a same-day probe-verified
  [review](docs/verification/OLLAMA-ADAPTER-REVIEW-2026-09-13.md) and one
  live observation (the key lists twenty models; generation is refused
  with HTTP 429 "weekly usage limit" and no `Retry-After`). The custom
  endpoint's Ollama wire streams newline-delimited JSON instead of
  returning "empty_response", so `stream: auto` can deliver after a proxy
  timeout; the gateway classifies by the status an adapter puts first, so
  a hexadecimal reference in a body cannot read as `401`, and a 429 whose
  body names a usage limit, quota, or credits is the new
  `usage_limit_reached`, an allowance the Practitioner does not retry
  inside a step; a refusal inside a 200 body is classified by its words, a
  page that is not JSON is `invalid_response_body` (outage class),
  context-length refusals and 413 are `context_window_exceeded` (request
  class, the cell fails and the route stays), 422 is `invalid_request`,
  408 is `timeout`, and Ollama's "model 'x' not found, try pulling it
  first" is `model_not_found`. `Retry-After` is read as seconds or an HTTP
  date onto `retry_after_seconds` and the attempt record; a `think`
  control on the custom endpoint is sent on the Ollama wire when
  declared; `auto` streaming remembers the mode that delivered, and the
  result says so; `live_model_listing()` on both adapters says how a
  listing was refused. A declared credential
  variable that is unset refuses before any request (`missing_credential`,
  as the built-ins do) and the environment declaration accepts `key_env`;
  an OpenAI stream cut before its stop reason is incomplete; an HTTP
  exception inside the body is `incomplete_response`, never a raise; the
  result counts the requests one attempt opened; keys are redacted from
  provider error text; a base URL naming the API prefix or the chat path
  composes the same URLs; `live_models` lists nothing on a refusal and
  catalog-only discovery reads a refused listing as a failed provider.
  Thirty offline checks in `core/custom_endpoint_checks.py`.
- Hardcoding gate, third batch: closed vocabularies compared by name.
  Response evaluation statuses (`PASSED`, `REJECTED`, `INCONCLUSIVE`),
  harness fallback decision reasons (`DECISION_REASONS`), harness run
  statuses (`BUDGET_EXHAUSTED_STATUS` and the rest, unpacked from
  `HARNESS_STATUSES`), search observation states (`OBSERVATION_STATES`),
  axis value kinds (`INTEGER_RANGE`, `ORDINAL`, `FLOAT_VALUES`), evidence
  validity statuses, generated-project command kinds, markup media types
  and read modes, and the stage-assistance arms (`SHADOW_MODE`,
  `ADVISORY_MODE`, `FRESH_MODE`, with `STAGE_ASSISTANCE_MODES` now owned by
  the control manifest and re-exported by the Practitioner records) are
  named once and compared by name in the harness, generation, evidence,
  project, and Practitioner modules; behaviour is unchanged and every
  module self-test passes. The auditor classes the strings of the
  versioned step-content record as governed prompt resources, as it already
  did for the prompt-fragment module, since that record is where step
  prompts are meant to live. Seven more findings carry written reasons: the
  OpenAI client's two documented endpoints it refuses to deviate from, the
  laboratory probe's local Ollama address, the campaign tool's health-probe
  default, Python's `mode` keyword name, and two record field names.
- Hardcoding gate, fourth batch: the Loop's own vocabularies compared by
  name. Run modes (`DETERMINISTIC`, `HYBRID`, `NON_DETERMINISTIC` from
  `MODES`), terminal codes (`ACCEPTED`, `CANCELED`, and the rest from
  `TERMINAL_CODES`), output types (`SINGLE_OUTPUT`, `MULTIPLE_OUTPUT`),
  and Run History event types (`MODEL_INVOCATION_EVENT`, `LOOP_INIT_EVENT`,
  `EVALUATION_EVENT`, `CUSTOM_EVENT`, and the rest from `EVENT_TYPES`) are
  unpacked once from their existing authorities and compared by name in the
  Loop runtime, the kernel, the reactive worker, the checkpoint, the
  Practitioner scope, recovery learning, and the stage evidence projection.
  The committed tree's new-high count fell from 140 to 118.
- Hardcoding gate, fifth batch: the last shared vocabularies and the
  laboratory. Fallback actions (`DIFFERENT_HARNESS` and the rest from
  `FALLBACK_ACTIONS`), review decisions (`APPROVED`, `REJECTED`), the
  next-action kinds unpacked from `NEXT_ACTION_KINDS`, the act modes, the
  evaluation verdicts (`ADMITTED_VERDICTS`, now owned by the independent
  evidence module), Astra readiness states, intake kinds, the sqlite
  journal mode, the diagram's container kinds, the Gemini command line's
  two roles, secret file suffixes, the OpenAI Responses API's item, part,
  and status names, and the configuration modules' fact states, change
  phases, and run modes (the latter from `MODES`) are named once and
  compared by name. The laboratory's serving views and git tree-entry
  vocabulary became constants. The auditor treats the frozen review probes
  under `devtools/review-probes/` as evidence scripts, as it already did
  for tests and examples, with a canary. Seventeen findings in the tools
  and the laboratory carry written reasons: subcommand names, transcript
  block kinds, record field names, store result statuses, and the legacy
  tools' own prompt constants. The committed tree's new-high count fell
  from 118 to 24.
- Hardcoding gate, sixth batch: the last twenty-four, and the gate is
  green. The built-in OpenCode step prompts (implement, verify, inventory,
  requirements, both observation forms, provision) now live in the
  versioned step-content record under `prompt_templates`, read through
  `step_content.prompt_template` with validation of every built-in name;
  the code composes each system prompt from those texts and its run-time
  facts, and the rendered prompts are byte-identical to the previous
  ones. The independent verification practitioner's system and probe-design
  prompts moved into the governed prompt-fragment module. The remaining
  singletons compare by name: the solve outcome record type, the
  deterministic attempt's completion status, OpenCode's finish reason, the
  information measure kinds, the token-bound record type, the store
  compatibility verdicts unpacked from the handshake's `VERDICTS`, the
  retry-same-route recovery option, skill lifecycle states, majority vote
  scopes, the fresh assistance arm, the projection's journal mode, and the
  legacy stage observation record type. One written reason covers the
  generated-project capability's contract description. Against the frozen
  CI baseline the committed tree now has zero new high findings, so the
  `Self-orientation and hardcoding delta gates` step passes without any
  change to the baseline.
- Hardcoding gate, second batch. A `None` compared under a role named
  `environment` was reported as a deployment value read at a boundary; the
  environment-read class now needs a value. Seventy-nine deployment
  findings in the harness recipes, the embodiment laboratory, and the
  tools were decided with written reasons: placeholder relay credentials
  the harness command lines require to be nonempty, the harnesses' own
  documented consent and startup switches fixed by the confinement design,
  locations inside the confined workspace, environment-variable names read
  at the boundary, empty "unset" defaults, and the raw-host verifier's
  minimal fixed `PATH`. With the sandbox layout moved to the typed record,
  the committed tree's new-high count against the frozen CI baseline fell
  from 318 to 225.
- Hardcoding audit precision. The auditor marked any literal anywhere
  inside a comparison as the token being compared, so `x is None`, a
  subscript index such as `items[0]`, and the key of a mapping read such as
  `decision.get("action")` were all reported as high-severity state
  comparisons whenever a state word appeared nearby, while the value
  actually compared kept its own class. The literal context now records
  whether the literal is an operand of the comparison (or an element of a
  literal collection that is one, or a match-case value), and both
  comparison classes require it. Finding identities are unchanged, so no
  baseline entry moved: findings that were never the compared token drop to
  low severity, and true vocabulary tokens (`status == 'active'`,
  `state in ('advisory', 'fresh')`) keep their high class. Four canary
  checks cover the four cases. Against the frozen CI baseline the
  new-high count fell from 502 to 335 in the shared working tree (which
  held another session's uncommitted modules) and stands at 318 on a clean
  export of this commit, with the baseline untouched; the remaining
  findings are raw vocabulary tokens compared directly, environment
  values, prompt texts, and endpoint addresses, each of which needs a
  written decision.
- Wide configuration search, after a same-day execution-verified review of
  the modules that reached `main` in `d8caea2` (probes under
  `.loop-engine-dev/fable-review-probe-20260913/agent-review-search/`).
  Exact-task identity for no-repeat, dominance, and optimizer history is now
  `SearchTask.identity_digest` (task, digest, contract, evaluator), so
  attaching or re-versioning task features no longer disconnects prior
  evidence and re-proposes observed addresses; `SearchTask.digest` still
  covers every field. One evaluation artifact counts once: the same
  evaluation reference, or byte-identical history and evaluation digests
  under other references, is excluded as `duplicate_evaluation_artifact`.
  An optional `SearchTask.evaluator_digest` is compared when both sides
  state it (`evaluator_implementation_changed`) and is left out of the task
  digest when absent, so earlier digests hold. The vector warm start skips
  the target task's own measurements, which could fill the draw allowance
  and starve related tasks. `propose_configurations` raises the typed
  `GenerationError` again instead of the Loop wrapper that hid it in
  `__cause__`. The batch record names its seed, cursor, shard, batch size,
  and draw allowance in plain fields beside the request digest. Seeded
  exploration reports an empty shard as exhausted. A conditional rule
  naming a value its axis or fixed context never takes is refused at
  construction instead of being dead or excluding every matching address.
  When Optuna or cmaes is absent, the fifteen optimizer controls appear in
  the aggregate self-test as not tested with the missing dependency named,
  and the 120-Canvas control records `optimizer_unavailable_not_exercised`
  for those methods and still writes its summary. Still open from the same
  review: a cursor is a bare integer the request does not bind to its space
  and shard, and the search records have no typed readers.
- [Claude Fable 5.1 review of 2026-09-13](docs/verification/CLAUDE-FABLE-5.1-REVIEW-2026-09-13.md),
  fixes applied the same day. A registered evaluator's verdict
  (`semantic_response_rejected` or `response_evaluation_inconclusive`) is
  now recorded on the physical attempt with its own code and ends the
  invocation on the route that produced the answer; the new
  `ModelGatewayConfig.allow_evaluator_route_failover` permission is the only
  way a verdict may move to another route. A harness selection policy
  refuses two records that cite one Run History reference, so a copied
  successful record can neither satisfy the minimum-evidence gate nor change
  which harness ranks first. The spawned task checkpoint reader and the
  information binding reader require a stored SHA-256 digest and stored
  integer counters instead of recomputing a blank digest or narrowing a
  coerced value. The raw-host verifier runs in its own process group, ends
  every process it started on timeout, bounds captured output, and returns
  the output tail with a timeout error. Evaluation records are
  `harness_response_evaluation/v2` with the evaluated subject contract, and a
  two-parameter callback receives the occurrence it is judging. The
  definition reader raises only `LoopDefinitionError` for stored contract
  faults. The adaptive Practitioner treats an evaluator verdict as response
  repair work rather than a transport failure. The Practitioner command line
  derives the credential variable an OpenCode step may inherit from the
  provider specification the gateway owns instead of naming it by hand, and
  `--step-credential-env NAME` adds names explicitly for custom providers.

### Added

- [Confined environment record](src/loop_engine/core/harness_confinement.py).
  The environment the sandbox sets after clearing the host's is a typed,
  digest-bound `ConfinedEnvironment`: the sandbox's own layout (`PATH`,
  `HOME`, the XDG directories), deterministic text modes (`LANG`, `TERM`,
  `NO_COLOR`), and the consent switches every brokered harness gets
  (`DO_NOT_TRACK`, `CI`, `PYTHONDONTWRITEBYTECODE`), with `with_switches`
  for a recipe's own documented variables, a refusal when a switch would
  override a layout variable or change a value silently, `setenv_arguments`
  for the launcher, and a record with a content digest. The sandbox
  argument builder uses it; the variables it sets are unchanged.
- [Layering as a configuration target](docs/components/core-architecture/HARNESS-FALLBACK.md#declare-wrapper-layers-and-native-control-ownership).
  `core.harness_layering_configuration` describes one assignment's layering
  space as a `ConfigurationTargetSpec` for the configuration setters and the
  meta-selector: two integer settings on a `LayeringConfiguration`, support
  and availability facts that cite the availability projection by digest,
  allowed values equal to the addresses that execute today, qualification
  only from a supplied independent fact, inspection through the setters'
  own view, and a joined record that keeps the declared-but-unexecutable
  remainder visible. Ten checks, including a space the outer policy refuses
  everywhere reporting unavailable with no allowed values.
- Search records read back, and a cursor that knows where it belongs. The
  two items the wide-search review left open are closed: every search
  record (`ConfigurationAxis`, `ConfigurationSpace`, `SearchObjective`,
  `SearchTask`, `SearchObservation`, `SearchRequest`, and the new
  `SearchCursor`) has a `from_dict` reader that rebuilds it with the same
  digest and refuses unknown or missing fields or another record type; a
  proposal batch carries a `SearchCursor` bound to the space digest and the
  shard, and a request given one as `cursor_record` resumes exactly there
  and refuses a cursor from another space or shard or one disagreeing with
  an integer cursor beside it. Thirteen new search checks.
- [Provider failure classes](src/loop_engine/core/provider_failure_classes.py).
  Every code the gateway, the solve terminal, and the Practitioner can
  report for a provider attempt now names its class: an outage a later
  retry may pass, an allowance the provider resets on its own schedule, a
  configuration fault no retry can change, a fault of the request itself,
  a violated engine contract, or unclassified. `decide` turns the codes of
  one failed attempt into the one decision a worker takes (wait for
  recovery, wait for the allowance, stop the route, or fail the cell) with
  precedence and an optional attempt ceiling that bounds every wait, so a
  campaign cannot re-run a cell without bound against a wrong credential
  or a spent allowance. Eleven checks, including that the codes the
  gateway emits for representative provider messages all have a class and
  that its failover-forbidden codes stop the route here too.
- Laboratory guard: a layering level in the systematic catalog may be
  marked installed only if the address it implies executes today under
  the runtime's availability projection, with and without the adapter
  declaring the control; a level whose address no executor runs stays
  planned whatever its label says.
- Module size: the stage store's thirty-nine offline checks moved to
  `core/stage_store_checks.py` (the store's `self_test` delegates to
  them), taking the module from the 800-line cap to 505 lines; the SQLite
  stage-evidence projection, which also sits at the cap, carries a
  declared size exception with a split plan for its validation methods.
- Task-database campaign runner: the two high findings of its review are
  fixed. After a trial the engine ended as provider unavailable, the
  worker decides through the provider failure vocabulary: a configuration
  or contract fault stops the worker with the status `route_stopped`, an
  allowance or an outage waits at most `--wait-attempt-ceiling` times
  (default 3) before the cell is recorded as failed and the campaign
  advances, and outage attempts, failed cells, and stopped routes are
  counted apart from completed trials. An interrupted trial is reconciled
  on restart (recorded as interrupted, evidence kept, attempt moved on;
  the refusal stays behind `--refuse-interrupted`, and a `reconcile`
  operation exposes it), an existing trial cell is reported rather than
  crashed into, a failed trial keeps its error message, and `SIGTERM`
  unwinds through the trial's `finally` blocks. Three new tests.
- Task-database campaign runner, second batch: the readiness probe
  defaults the port by scheme (80 for `http`, 443 for `https`), reads the
  listing path the product adapter uses for the wire (`/api/tags` for
  Ollama, `/models` otherwise), accepts a listed model with the implicit
  `latest` tag, reads an empty listing as an outage and a listing without
  the configured model as a configuration fault, and classifies an HTTP
  refusal through the gateway's own classifier, so the worker stops with
  `route_stopped` on a wrong credential or a missing route instead of
  waiting forever. Per-step checkpoints keep `checkpoint_retention`
  revisions (default 2) of the append-only ledger instead of every prefix,
  and record the revision, the retention, and the event count. Two new
  tests.
- Configuration setters and preferences, after a same-day probe-verified
  review ([report](docs/verification/CONFIGURATION-MODULES-REVIEW-2026-09-13.md)).
  An abstained proposal is refused before resolution instead of rewriting
  the setting to a default; a change whose value is decided by a
  higher-precedence source is reported as `applied_by_precedence` with the
  governing source named, never as the requester's own change; a
  constructor that clamps or rounds is refused as `constructor_coerced_value`
  with both digests; any constructor exception and an absent declared
  field are typed refusals; the report states that the boundary made no
  model call and whether a proposal was supplied; constraint values are
  type-checked at spec construction; fact expiry is typed and normalized
  to one spelling; qualification is invalidated only by settings that
  affect it; setting records are JSON-plain; and a proposal the record
  contract refuses inside `rank` is an invalid proposal, not an engine
  crash. Sixteen new setter checks and one preference check.
- Task-database campaign runner, third batch: the engine identity (every
  package source and every executable a harness manifest launches) is
  digested at prepare and checked at worker start, refusing a changed
  engine unless `--allow-engine-change` records the change; a
  `population-index.json` whose digest a reader can reproduce is exported
  beside the private population, without this machine's directories; and
  a task awaiting source admission is recorded once instead of on every
  round. Two new tests.
- Boundary registry: every row's `test` reference is now resolved by the
  registry's own self-test, without importing or running code: a
  `module.function` form resolves through the architecture map like an
  envelope, and a `module:check_name` form must name a check spelled out
  in that module or a check module of its package. Eleven rows named
  tests that did not exist (two check modules without a `self_test`, three
  check names found nowhere) and now cite the checks that cover them.
- Configuration records read back: `ConfigurationFact`,
  `ConfigurationSettingSpec`, and `ConfigurationTargetSpec` have `from_dict`
  readers that rebuild a record with the same digests and refuse unknown
  or missing fields, another record type, a changed definition or target
  digest, and a redacted (sensitive) setting record, which cannot honestly
  be rebuilt into a definition; the preference decision record is now
  plain JSON. Six new setter checks and one preference check.
- Task-database campaign runner: one trial now runs end to end offline in
  a laboratory test, through a fixture gateway whose only endpoint answers
  from a canned transport, with a fabricated task directory. It proves the
  trial path records its sources, applied configuration, step history, and
  terminal state and ends in a recorded state rather than an exception,
  before a real provider is spent on it; it claims nothing about solving.
- [Trial evidence report](devtools/embodiment_lab/trial_evidence.py): for
  one campaign trial cell, whether each evidence link is present (the
  trial state, the task sources and their digests, the configuration
  applied per model call, the step-history checkpoints, the outcome with
  an intact Run History, physical model calls counted against the calls
  claimed, delivered artifacts, and an independent evaluation), the gaps
  by name, and a campaign-wide summary counting trials by completeness
  and by the gap that keeps them incomplete. It reads and runs nothing;
  the offline trial test proves it against a cell the runner wrote.
- [Layered harness wrappers and native control ownership](docs/components/core-architecture/HARNESS-FALLBACK.md#declare-wrapper-layers-and-native-control-ownership)
  as passive typed records (`core.harness_layering`): ordered wrapper
  compositions with single-owner transport and accounting, ordered fallback
  alternatives per failure kind (another wrapper, another order, a native
  session restart, or another registered harness) under one decider, read-only
  validated settings and ownership, a complete native control ownership matrix
  in which completion is never delegated, and a binding checked against the
  outer fallback policy before execution. `HarnessFallbackPolicy` gained the
  explicit `allow_native_retry` permission (off by default, recorded as
  `harness_fallback_policy/v3` only when set), so a native retry can never
  bypass an outer semantic-recovery restriction. `HarnessSemanticBinding`
  accepts the binding as `layering`, records `harness_layering_bound/v1`
  with the digests and the executor at invocation, stamps every attempt
  assessment with the same digests, and refuses at construction, with the
  exact reason, a composition with wrapper layers, a natively owned control
  the adapter does not declare in the new
  `HarnessExecutionCapabilities.native_controls` fact, or a declared control
  that no executor hands to the harness yet. No adapter executes a
  composition yet; the records are the
  declarations the
  [layered harness proposal](docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
  asks for, and the direct adapter remains the baseline.
- [Layering dimensions a configuration search can address](docs/components/core-architecture/HARNESS-FALLBACK.md#declare-wrapper-layers-and-native-control-ownership).
  `core.harness_layering_space` enumerates and indexes both dimensions: a
  `ControlPolicySpace` decodes any complete control policy from a mixed-radix
  index (256 policies for an adapter declaring nothing, 49,152 for one
  declaring every control), a `CompositionSpace` walks every valid ordered
  wrapper selection up to the caller's depth one sequence at a time with the
  direct adapter at index 0 and no invented ceiling, and a `LayeringSpace` is
  their product for one assignment, yielding validated bindings by index and
  reporting an index inadmissible when the outer policy refuses it. The
  spaces rebuild from their `harness_layering_space/v1` records under the
  run's own outer policy, and `load_layered_binding` reads a host-authored
  declaration file. `generation.layering_axes` turns the two spaces into two
  `integer_range` axes of a `ConfigurationSpace` bound to the layering
  space's digest, decodes any address to its binding, reports admissibility
  per address, walks a shard lazily over admissible addresses, and splits a
  proposal batch into a separate filter record, so every proposal adapter
  proposes layering addresses with the other dimensions of a search. The
  embodiment laboratory's systematic catalog carries both dimensions as
  factors (207,360 configurations per task, up from 51,840) with maturity
  labels a lab check holds to the code the tree has.
- [Layering availability](docs/components/core-architecture/HARNESS-FALLBACK.md#declare-wrapper-layers-and-native-control-ownership):
  `core.harness_layering_availability` projects every address of a layering
  space onto one of five states for one adapter (executable now, outer
  policy refuses, composition without executor, adapter does not declare,
  declared without executor) by the rule `HarnessSemanticBinding` applies at
  construction, which now calls the same function so the reasons cannot
  drift. `classify_address` gives one address's state and reason,
  `availability_summary` counts a whole space from its policies and its
  composition count without walking the compositions and lists the
  executable addresses exactly, and
  `generation.layering_axes.address_availability` answers for one
  configuration, so a search learns which addresses are declarations before
  proposing them.

- [Unseen novel-task campaign](docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md).
  Ten sealed novel tasks each completed on the first autonomous attempt
  through the frozen host machinery (283 real model calls, complete token
  accounting, one attempt per task, no repairs). An independent seeded
  random-input audit invalidated one accepted solution, and the later
  [execution-verified review](docs/verification/CODE-REVIEW-2026-09-07.md)
  confirmed three prompts contradicted their own oracles and the offline
  check was circular, so the campaign's 10/10 and 9/10 figures overstate
  correctness for the exact prompts. The population is burned as evidence;
  the [version 2 repair set](docs/implementation/IMPROVEMENT-PLAN-2026-09-07.md)
  and the [unseen-task handoff](docs/prompts/UNSEEN-TASK-WORK-HANDOFF.md)
  define the corrected instrument and the next steps.

- [Adaptive completion, dependencies, and restart checks](docs/verification/ADAPTIVE-COMPLETION-AND-PUBLICATION-2026-09-06.md).
  Hosts can require additional independent completion gates. Spawned
  Practitioner assignments can bind typed prerequisite outputs while retaining
  separate task acceptance. Reactive work distinguishes an unstarted expired
  lease from an unknown running effect, and can require durable canonical Run
  History before successful publication. Cancellation cannot become later
  acceptance. Examples include selected failure evidence, an exported-ticket
  review pilot, and local CSV competition preparation. Source and clean-wheel
  checks pass; broad unattended solving and the TrafficFlowBench harness
  comparison remain separate proof obligations.

- [Live tabular model portfolios](docs/verification/TABULAR-MODEL-PORTFOLIO-2026-09-06.md).
  One configurable host adapter trained engine-selected scikit-learn recipes
  on Titanic, house prices, and Iris. The three completed runs used 33 real
  model calls and produced 36 fitted pipelines. Validation selected candidates
  before separate sealed-holdout scoring. Downloads are explicit host
  preparation; these familiar-data local scores are not Kaggle submissions
  or unseen-task evidence. The example includes source digests, saved models,
  predictions, failure checks, and reproducible recipe records.

- [Host execution and source admission](docs/verification/HOST-ADOPTION-AND-GENERALIZATION-2026-09-05.md).
  Applications can pass a typed host binding to `SolveRequest` and use their
  registered operations and verification gates. Host results retain their
  own contract; final acceptance requires current host verification and task
  completion. Scoped permissions, explicit model disclosure, and exact effect
  approval remain separate. A seeded JavaScript project was repaired in two
  passes and 11 real model calls after protected tests exposed its defect.
  The earlier permission-refused attempt remains recorded. Source inspection
  admits UTF-8 text by content and records exclusions. Frozen verification
  passed 3,120 source tests, 3,075 applicable base-wheel tests, and 27
  conformance gates in each environment. Broad unseen-task reliability and
  automatic persistent promotion remain unproven.

- [Independent executable task feedback](docs/architecture/ADR-INDEPENDENT-TASK-FEEDBACK.md).
  Generated-project acceptance requires engine-created checks by default.
  Separate verifier Loops generate and review probes, compare actual output
  outside the candidate process, and feed failures into the existing repair
  loop without user feedback. Read-only Docker mounts protect the subject and
  checker. Operational failures can recheck unchanged artifacts; they do not
  invent new task criteria. Persistent self-modification and unrestricted
  general-purpose reliability are not established by this change.

- [External-caller and code-only delivery repairs](docs/verification/BRAIN-INTEGRATION-CODE-ONLY-2026-09-05.md).
  Code-only tasks can return verified modules and tests without inventing an
  extra command-produced file. Task-file text carries captured provenance,
  malformed project fields receive precise diagnostics, failed execution
  attempts retain their workspaces, and retries use fresh directories.
  Public `solve_outcome/v5` preserves unknown call totals and known subtotals.
  Real task and repair runs, independent checks, and remaining limits are
  recorded separately from offline runtime tests.

- A [live Kaggle pilot checkpoint](docs/verification/KAGGLE-LIVE-PILOT-2026-09-05.md)
  with an authorized Ollama probe, filtered population selection, and exact
  source/wheel verification. Source inspection derives content and digests from
  one read, and selected inputs cannot silently disappear or remap. Explicit
  no-total-token-ceiling probes remain distinct from strict token-bound calls.
  Independent review rejected a generated tool despite its passing tests;
  this checkpoint claims no Kaggle submission or score.

- **A primary-source long-horizon skills and recurrence review.** The dated
  report separates Agent Skills packaging, explicit execution state, recursive
  inference, neural recurrence, test-time learning, and persistent memory. It
  compares SKILL.state, ReasoningBank, Recuris, SkillGLoW, PILOT, Recursive
  Language Models, agent-system scaling, Mamba, RecurrentGemma, TTT, Titans,
  Miras, Nested Learning, and official OpenAI runtime features. It also defines
  state sufficiency, rate-distortion, residual predictive information, three
  meanings of surprise, and ten falsifiable Loop Engine experiments. Reported
  paper results remain unreproduced.

- **Offline predictive-state and procedural-control evidence.** New passive
  records distinguish unissued Shannon and Bayesian surprise calculations,
  empirical predictive information, and paired context compression with task
  loss. Those records use typed validity records, declared populations and
  evaluators, minimum coverage, exact source identities, and an absolute
  treatment-loss ceiling.
  Separate procedural assessments test initiation, termination, interruption,
  outcome devaluation, negative transfer, fresh control, and deliberative
  fallback candidates for one named procedural-memory version. Their strongest
  result is candidate support pending canonical reference resolution. The
  records cannot select context, retrieve or execute a procedure,
  mutate state, or authorize promotion. Product integration, held-out quality,
  causal credit, and cost benefit remain unproven.

- **A byte-bounded Agent Skills registry and passive state-context candidate.**
  New manifests use standard frontmatter plus namespaced Loop Engine metadata.
  Startup cards omit complete instructions, paths, and tool requests. A
  separate offline candidate binds an admitted skill, exact JSON Schema,
  trusted state, latest observation, selected history, scope, privacy, and byte
  limits without entering the product prompt. Registry checks pass 21 of 21
  and state-context checks pass 17 of 17. No live quality or cost result is
  claimed.

- **Unknown model usage remains unknown through reporting.** Model-call events
  now distinguish positive, missing, partial, and real-zero provider usage with
  `model_usage/v2`. Run History preserves the distinction through projection,
  digesting, JSONL save and load, analytics, quality reports, and playback.
  Mixed known and missing attempts produce an unknown aggregate instead of a
  fabricated zero or a partial total.

- **A private, staged Kaggle access campaign.** A read-only preflight froze 120
  entered competition identifiers and received 120 readable file-list
  responses. A total of 117 lists contain rows, 3 are empty, and 49 have more
  pages. This is metadata evidence, not source qualification or competition
  solving. An adversarial review found and fixed pagination parsing, authority
  bypass, secret-preview retention, effect ownership, path confinement, and
  result-to-history binding defects. A fresh three-competition canary then
  recorded four exact approvals, tool records, and retrievals in an intact
  151-event Run History. No dataset, model call, or submission was used.

- **A fail-closed Kaggle source-qualification layer.** An exact preflight and
  population digest now bind page retrieval, private content-addressed source
  artifacts, legal and data-use candidates, deadline assessment, evaluator
  candidates, completeness, and a passive download plan. Thirty-one offline
  checks pass. A live read-only canary covered the three active candidates in
  the frozen 120-member population, made three page reads, stored 27 private
  artifacts, and preserved an intact 1,227-event Run History. None reached
  `QUALIFIED`; no data was downloaded and no model or submission was used.

- **An explicit-only GPT-6 Astra Responses adapter and route quarantine.** The internal adapter
  binds the exact model, official output maximum, supported reasoning efforts,
  request fields, response status, and provider-reported usage. It omits
  unsupported sampling fields, refuses tool-call output, hashes private prompt
  text in summaries, and excludes raw provider error messages. A separate
  typed demand, candidate paid-use envelope, pricing, availability, locality,
  capability, and complete request digest fails closed before route
  construction. The adapter passes 21 offline checks and the quarantined policy
  passes 38. No executable route can be built. It remains outside default
  routes and made no credential read or live call.

  A separate authorized one-call Ollama Cloud canary succeeded through the
  existing model-neutral path with 66 input, 130 output, and 196 total
  provider-reported tokens. It proves that configured provider path only. It
  is not an Astra call or an assisted-versus-fresh experiment.

- **Logical model-call correlation through Run History.** One semantic call ID
  now survives across its physical provider attempts, while every attempt
  retains its own Loop ID and the semantic owner Loop. An injected adaptive
  fixture retained seven logical calls, seven physical attempt Loops, and an
  intact 497-event Run History with no provider call.

- **Fail-closed Kaggle tabular admission.** The current narrow executor now
  rejects multi-output submissions, duplicate headers, absent or test-visible
  targets, unexplained train-only columns, and preprocessing that leaves no
  usable feature. A local cross-validation number is described as a diagnostic,
  not an official competition metric.

- **Fail-closed stage credit and advisory plumbing.** The earlier product path
  applied one pass verdict to every stage, treated admission as help,
  contaminated a nominal fresh control, and suppressed missing evidence. The
  current offline product path requires an exact assistance decision before
  downstream use, records exposure only after a physical attempt, counts
  failover attempts and cumulative tokens, keeps contradicted credit unknown,
  and leaves run-only contribution unknown. Canonical paired outcomes and
  causal benefit remain unproven.

- **The architecture as a typed model, rendered rather than drawn.** A diagram
  drawn by hand starts accurate and drifts, because nothing makes it wrong
  when the code moves. `code_nodes.architecture_diagram` holds C4-style
  context, container, component, dynamic, fingerprint-lattice, experiment,
  and deployment views. Every code-backed element names a module that must
  exist. Each element also says whether it is implemented, partial, shadow,
  or target behavior. A self-test fails after a module rename or a stale
  generated page. Mermaid and Structurizr DSL are renderings, not architecture
  authorities.
  `docs/ARCHITECTURE-DIAGRAMS.md` is generated from the models.

- **A stage-assistance evidence foundation on the public offline solve path.** New
  passive records separate Loop activation identity, semantic-call identity,
  and similarity signatures. A paired-trial contract assigns one advisory and
  one fresh occurrence, binds packet and evaluation events, and refuses prior
  references in the fresh arm. An idempotent SQLite/WAL projection accepts
  only committed intact Run History and remains a rebuildable index rather
  than evidence authority. The public `SolveRequest` accepts an explicit
  experiment binding. Advisory candidates require digest-bound hydrated
  material, and that body enters the rendered selected-intelligence section;
  fresh receives neither candidate nor material. The prompt-sensitive fixture
  binds logical and physical request digests, the admitted response, the
  semantic payload, and one selected action through exact selection,
  execution, and verification occurrence references. Foreign, stale,
  duplicate, changed-result, or unpersisted joins cannot create local credit.
  Every active arm carries a pre-run control manifest; the fixture labels its
  six unresolved controls as `mechanism_only`. The provider responses remain
  injected. The verifier uses the same Practitioner model path and attribution
  confidence remains unknown. Canonical per-stage pairs, live model behavior,
  causal benefit, exact control freezing, and campaign-safe shared storage
  remain unproven.

- **Cross-run stage recording and shadow consultation are connected.**
  Prior stages are loaded once at the start of a run, and shadow mode consults
  the model ladder for each shape. The ladder's recommendation is written down
  and not followed: below its evidence floor it declines to advise, and
  even above it a recommendation about a stage shape is a hypothesis rather
  than a fact about this stage. Recording it now is what makes checking it
  possible later; acting on it now would make the check impossible, because
  the record would only ever confirm what it already said.

  Demonstrated across two consecutive runs of the same task. The first loaded
  0 priors, wrote 14 stages over 7 motifs, and its convergence measure
  reported 12 nominal offered assignments against 2 nominal control
  assignments. Those labels did not change packet exposure. The second loaded
  those 14 priors and consulted the ladder 15 times, every consultation
  correctly declining:
  "2 observations of this shape is too few to fit a ladder to; the caller's
  default stands". The machinery works and says, accurately, that it does not
  yet know anything.

- **The fingerprint stack is live, and runs now accumulate stages.** Every
  model step names its cognitive situation. Its experiment arm is assigned
  from the experiment, semantic signature, occurrence identity, and campaign
  seed before anything is offered to the call. Admission and local verification
  are recorded separately. A pass-wide outcome is an unattributed boundary,
  not stage credit, and run outcome remains contextual evidence only. A stage
  that already failed is not relabelled by a run that later succeeds. Naming a
  stage cannot fail a run: a situation that cannot be described is simply not
  named. First live reading on a verified
  run: 19 observations collapsing to 7 motifs and 7 shapes, with 17 nominal
  offered assignments and 2 nominal control assignments. The product path
  did not apply those assignments to template exposure.

- **Fingerprint contracts name several scales; production emits one.** The
  contract names operation, Loop, segment, and run scopes. Production stage
  recording currently emits the default Loop scope only. `compose_segment()`
  and `sliding_segments()` demonstrate ordered cross-domain segment signatures
  in offline checks; no product path composes or persists them. Transition,
  episode, subgraph, branch, campaign, and linked physical-call fingerprints
  remain target behavior.

- **Somewhere to keep them.** `core.stage_store` indexes observations three
  ways: semantic situation signature, motif, and shape. It returns every level
  rather than only the strongest, because one signature match against four
  hundred shape matches is a different thing from the reverse. A single
  blended score hides which evidence you hold. Matches carry counts and
  outcomes, never a rate: two of three and two hundred of three hundred are
  not the same claim. Storage is append-only newline JSON, and a store that
  cannot write degrades to in-memory rather than failing the run.

- **An advisory model ladder fitted to recorded outcomes.**
  `core.model_demand` reads prior stages of the same shape and recommends an
  order to try routes in, cheapest first where the evidence supports it. It
  does not select or execute a route. Below twelve observations of a shape it
  recommends nothing and says so: a ladder fitted to four rows is a guess with
  provenance, which is worse than an honest guess because it looks like data.
  Routes with no known outcome never lead. Where evidence ties, the cheaper
  route leads in the advisory order.

- **The cognitive situation, as a unit smaller than the task.** A task
  fingerprint identifies the problem and is too coarse to learn what a
  response should contain: one competition holds inferring an output
  contract, testing for leakage, comparing candidates and diagnosing a failed
  command, which share a task and almost nothing else.
  `core.stage_fingerprint` names the smaller unit, what this call is
  responsible for, where it sits between the ultimate goal and the immediate
  step, what it knows and does not, what its answer is for, with a digest
  that deliberately excludes run, loop and branch references so the same
  situation in another run is the same situation. Its coarser `motif` is the
  cross-domain shape derived from the phase and populated situation fields.
  This creates a retrieval key. It does not prove that two matched stages are
  compatible or should use the same response.

- **Occurrence-based exposure exists in the public offline product path.**
  `core.convergence` assigns an occurrence from the experiment, semantic
  signature, occurrence identity, and campaign seed, so a retry cannot walk
  that occurrence into another arm. An explicit advisory binding can expose
  compatible prior-stage candidates with hydrated material, while a fresh
  binding performs no prior retrieval and exposes neither. Exposure is
  recorded only after a physical attempt and binds the work packet, prompt,
  gateway request, and provider request. The current request-wide fixture is
  not a canonical per-stage paired trial and does not estimate an assistance
  effect.

- **Decisions are joined forward to what became of them.** A decision record
  says what was chosen and who chose it, which supports one finding, how
  often something was picked, and not the one that matters. A corpus of
  choices without outcomes teaches that models compacted context 63% of the
  time; a corpus with outcomes teaches that compaction succeeded 72% of the
  time here and cost rework 31% of the time there. Only the second can become
  policy. `core.decision_outcome` follows each decision through proposed,
  admitted, executed, observed, verified and contributed, and refuses to
  flatter itself: a decision whose outcome never arrived is unresolved rather
  than successful, a decision that passed its check inside a run that then
  failed is not counted as having helped, and a later invalidation overrides
  an earlier success rather than being edited away. `DecisionOutcome`
  verification remains joined at run level and says so. The committed
  `OutcomeVector` can separately carry stage-local verification, downstream
  use, branch contribution, later invalidation, and task outcome. The product
  path does not yet populate every stage-local signal.

- **A response shape a caller may argue with.** A schema handed to a model is
  a hypothesis about how an answer should look, and it is sometimes wrong: a
  template asking for one root cause forces a single answer from evidence
  supporting three, and one asking for a single next action discards the
  topology of a task needing two experiments and a join. A caller that fills
  such a template obediently has produced a well-formed misrepresentation
  that nothing downstream can detect. `core.template_negotiation` defines a
  passive contract through which a reply may accept, extend, modify, simplify,
  compose, replace, or ignore a shape. The adaptive product path still uses
  fixed per-step schemas and does not invoke this negotiation contract.

  What stays fixed is narrow and load-bearing. Fields are classed by how
  negotiable they are, and two classes are not: identity and provenance,
  because a reply nobody can attribute or replay is not an answer; and
  authority, because the escape hatch must never become the route by which a
  reply grants itself a permission, widens an effect, or rewrites what counts
  as success. Those are refused whatever disposition is claimed, and the
  attempt is recorded rather than dropped. Adversarially checked: widening
  permissions, redefining acceptance, rewinding state revision, and all three
  at once are each refused with authority intact. A consumer field dropped by
  a departure is reported as unreconciled rather than silently lost, and a
  natural result and its lossy consumer projection are kept together so a
  graph need not be destroyed to satisfy a consumer wanting one scalar.

- **Recovery is chosen by reasoning, with the table demoted to continuity
  behaviour.** The retry policy added earlier the same day decided which
  failures were worth another attempt, how many, and how long to wait,
  task-conditioned choices frozen from a handful of runs. It now says only
  what is cheap to try while a route is merely busy. At the point where it
  would give up, which is the moment the run is otherwise lost,
  `core.recovery` puts the decision to a reasoning route through the standard
  choice contract: the runtime supplies the mechanical facts (which routes
  have credentials, what each window holds, what work is already verified)
  and reasoning selects among them, adjusts named settings within bounds, or
  proposes something nobody enumerated.

  The bootstrapping problem is handled narrowly rather than ignored. Something
  must decide what to do when the thing that decides is what failed, so the
  ask goes straight to the gateway and can never recurse into another recovery
  decision. When nothing answers, the result is
  `NO_REASONING_ROUTE_AVAILABLE` and the caller raises as before, the honest
  end of a run whose reasoning could not be reached, not a licence to finish
  the task another way. Every recovery is recorded with its true owner, so a
  choice made by the table when no reasoner could be reached is never counted
  as a reasoned one.

- **One shape for every task-conditioned choice, and a count of who made
  them.** `core.choice` is a single typed interface, standardised input,
  standardised output, for any decision the runtime puts to a model: choose
  among options, adjust named settings within stated bounds, or propose
  something nobody enumerated. The runtime supplies only mechanical facts
  (this route has no credential, that window cannot hold the request) and the
  model chooses among them. `core.semantic_decision` records each such
  decision with its owner and computes `semantic_autonomy_coverage`, the share
  attributable to reasoning rather than to a table. An empty run reports no
  coverage rather than perfect coverage, and a decision taken with no second
  alternative open is counted but flagged, because both are ways the figure
  can flatter itself.

  The uniform shape is the point. Recovery policy written as a table freezes
  task-conditioned decisions from a handful of runs and never says why, so
  nothing accumulates that could justify a better table later. Decisions
  recorded identically everywhere can be counted and compared, and a narrow
  region may eventually be distilled into deterministic policy that reproduces
  what reasoning actually did rather than what someone guessed it would do.

  Measured against the retry tables added earlier the same day: given the real
  failure those tables were written for, a provider finishing normally and
  returning only private reasoning, the table says retry the same route six
  times. Asked the same question through this interface with the same
  mechanical facts, the model selected a different model on the same provider,
  lowered temperature, named an exit condition, and kept compaction in
  reserve. It never reached for either provider lacking a credential.

- **A budget that can be asked for less.** `compacted_policy()` returns a
  context budget tightened for another attempt at a packet that did not fit:
  text budgets halve per level, retained history shortens by one attempt, and
  both stop at a floor rather than shrinking to a packet that fits and says
  nothing. Refusing an oversized packet is honest but final, and throws away
  the work that produced it. This is the primitive for putting the same call
  again in less space; the gateway now uses the same idea for output ceilings.

- **Cases written under guidance, instead of three frozen fixtures.** Three
  fixed cases can only measure three things, and they measure them
  repeatedly: the same trap, in the same words, in the same file, so a run
  that does well on them has been shown to do well on them.
  `benchmarks/task_families/generator.py` describes the *shape* of each trap,
  a misattribution, a quietly superseded instruction, a list whose structure
  is not what it looks like, and asks a model to invent the particulars,
  through a Loop. Each case carries its own judging criterion, so a generated
  trap is gradeable by the same observation judge as a written one.
  Generation is not trusted: structural checks reject a case with no real
  choice of options, an empty file, a path escaping its directory, or a right
  and wrong reading that are the same text. Live, those rejected a third to
  two thirds of candidates per round, which is the point of having them.

- **A judge that reads the work, in the same Loop runtime the work ran in.**
  The task-family graders decided a semantic question with a keyword list:
  `grade_jira` accepted a root cause only if it contained "exclusive",
  "inclusive", "off-by-one", "end" or "last", so a run writing "the upper
  limit is one too small" was marked wrong for saying the right thing in
  unenumerated words, and it read the run's own `answer.json`, never the
  code, grading a claim rather than a change. `benchmarks/task_families/judge.py`
  reads the artifacts and reasons about them through a Loop, never seeing the
  run's case for itself, with deterministic facts handed to it as findings it
  may not contradict.

  Building it surfaced something worth recording. Asked outright whether a
  criterion was met, the judge described a patch that *concealed* a defect,
  accurately, in its own evidence, and then answered that the criterion was
  met. Asked whether that evidence supported that conclusion, it explained
  that it did not and answered that it did. The prose was right both times
  and the boolean wrong both times: a judgement field invites agreement. So
  it is no longer asked for one. It reports which of several neutrally worded
  options matches what it read, and the verdict is derived from the letter.
  On two adversarial cases, a correct fix described in unusual words, and a
  wrong fix described in the right vocabulary, the keyword grader scores
  0 of 2 and the observation judge 2 of 2, with an independent second reading
  agreeing on both.

- **A deployment can name the sandbox image.** `LOOP_ENGINE_SANDBOX_IMAGE`
  selects the image generated projects run in; the default is unchanged. The
  bare interpreter that was hardcoded is the right floor for a runtime that
  must not assume what a task needs, and the wrong ceiling for a machine
  asked to do data work: every attempt at a modelling task refused honestly
  for want of a library it was forbidden to install, having burned its passes
  to discover that. Naming the image is how a deployment states what its
  sandbox can do, instead of each task finding out that it cannot.

- **A run now states which questions it is eligible to answer.** Six live runs
  were used to reason about behaviour; every one had transport failures and
  three had zero completed model calls, yet all six were read as evidence
  about task difficulty. Nothing recorded said they were ineligible, so
  nothing stopped it. `core.run_validity` classifies a finished run as
  `INFRASTRUCTURE_INVALID`, `INFRASTRUCTURE_UNCERTAIN`,
  `SEMANTICALLY_ANALYZABLE`, or `MIXED_OR_MULTI_CAUSAL` from its own record
  and event stream, matching on typed event kinds rather than provider error
  text. An invalid run stays first-class evidence about infrastructure and is
  excluded only from the questions it cannot answer; comparison is the
  strictest gate, because comparing a contaminated run against a clean one
  measures the contamination. Every exclusion carries its reason, since a
  filter nobody can see is how a corpus quietly becomes the runs that happened
  to agree. Applied to the six: 6 of 6 eligible for infrastructure analysis,
  3 of 6 for semantic analysis, 0 of 6 for comparison.

- **A terminal code may only name a layer the run actually reached.** Three
  live runs terminated `VERIFICATION_FAILED` having verified nothing: their
  own records said `verification.method` was "not completed", every recorded
  failure was transport, and zero model calls completed. The two states are
  different work for whoever reads the code next, and the runtime already held
  the evidence to tell them apart. `core.terminal_layer` derives the deepest
  layer a run reached from its own record, orientations and decisions mean
  semantic work, project attempts mean execution, a verdict or a completed
  method means verification, and absent all of it the run reached transport
  and the code says `PROVIDER_UNAVAILABLE`. An explicit failure code still
  wins; this is the fallback that decides what to say when nothing else did.

- **`docs/TROUBLESHOOTING-LADDER.md`**: seven questions every error gets, in
  order, before a fix is written, with three worked examples from live runs.
  It records why infrastructure defects are fixed before any claim that a
  prompt, context policy or cycle is better: such a claim is about a
  distribution of tasks and needs evidence across many thousands of runs on
  novel work, while a boundary that admits nothing or a code that names the
  wrong layer is wrong on every task and needs none.

- **Multi-domain and multi-competition benchmarks.** `benchmarks/
  kaggle_competitions` reads each competition's contract independently of any
  run and grades discovery apart from execution; `benchmarks/task_families`
  adds Jira, email and to-do cases, each built around a trap that produces a
  well-formed wrong answer, with graders that never reach the run.

- **The cognitive vocabulary is now explicit, and so is what it lacks.**
  `core.cognitive_grammar` derives an operator catalog of 45 entries from the
  live kernel nodes, action kinds and capabilities rather than restating them,
  names five versioned cycle profiles as skip sets over optional nodes only,
  and maps all 28 transitions a Loop network would need: 18 realized, each
  naming its mechanism, and 13 not, each with the reason. Naming a transition
  realizes nothing, and the map says so. A caller may now report an
  `operator_gap`, what it needed, what it tried, what the runtime refused
  with, which is admitted, marked with whether it names an operator that
  already exists, counted apart from a missing portfolio option, and carried
  into saved history. That is the record a live run could not make while it
  restated the same correct repair for twenty passes. Measured: skipping four
  of thirteen nodes changed model calls not at all and packet bytes by 0.1%,
  because every optional node is served by a deterministic default that makes
  no model call. The profile lever is close to inert; the cost lives in the
  six model-calling nodes and in what each packet carries.

- **The Kaggle working root holds the submission and nothing to search.**
  A submission that verified was reachable only at
  `loop-engine-solutions/attempt-<stamp>/submission.csv`, beside five other
  root entries, a source checkout, a logs tree, a solutions tree, a settings
  file and a task file, none of which a person submitting a competition
  entry needs. Everything a cell writes now lives under one `loop-engine/`
  directory, leaving the root with `submission.csv` and that directory. A
  self-test asserts the root holds nothing else, because this is the
  directory Kaggle's own submit dialog lists. Stale workspaces are still
  cleaned at the start of a run and nothing else is ever removed: a previous
  run's solutions directory can hold the only copy of a verified submission.

- **Each Kaggle output now sits where its reader is.** A run that produced a
  submission and a run that produced nothing looked nearly the same in the
  notebook: the same wall of log lines, the file buried under a timestamped
  attempt directory, and nothing at `/kaggle/working/submission.csv` where
  Kaggle's own submit flow looks. `loop_engine.kaggle_report` ends every run
  by writing the competition file to the working root, a dated copy under
  `submissions/`, a self-contained HTML report and the same report as
  Markdown, one JSON record per attempt plus `LATEST.json`, and a console
  block that says the outcome, the submission's shape and the file to submit
  without scrolling. Only one run can hold the root filename, so promotion is
  explicit and recorded in `submissions/root-submission.json`: a verified run
  always takes it, an unverified run takes it only while no verified run has.
  The reports state a submission's rows, distinct values and range rather
  than calling it good, and a submission whose predictions never vary is
  published with that named, this repository has shipped that exact failure,
  and a reader needs to see it rather than be reassured. The offline harness
  gained a static name check across each whole cell, because the publishing
  code runs only at the end of a live run: a cell referring to a name it does
  not define now fails in under two seconds instead of raising `NameError`
  after four hours, which is precisely what one of these three cells would
  have done.

- **A run can read back a file it produced.** A live Kaggle run generated a
  Python file with an unterminated string literal at line 131, was told so
  exactly, reached the right conclusion immediately, and then could not read
  the file. `core.source.inspect` refused because a generated file is not in
  the supplied source manifest; `core.generated_project` refused a `cat`
  because commands must run the registered Python executable over reviewed
  authored files. Neither refusal was wrong, and between the input boundary
  and the execution boundary there was no way to observe the run's own
  output, so the model spent twenty passes correctly restating a repair it
  had no means to perform. `core.workspace.read` is that missing observation:
  it lists what the run has produced, returns any of it with interpreter line
  numbers so a reported line can be looked up directly, and refuses by name
  any path resolving outside the workspace. It reads and never executes;
  supplied inputs stay with `core.source.inspect`.

- **A much larger universe of options, and three more steps to reason in.**
  The portfolio grew from 17 perspectives to 42 and from 14 guidance records
  to 30, and every step now carries persona affinities, `orient` previously
  had none, so all 42 perspectives read as unmatched on the first call of
  every run. Nothing was removed and nothing was gated: affinity is advisory
  metadata, and every perspective, question set and guidance record still
  ships on every call for the model to select from.
  The canonical kernel gains three optional nodes: `frame_alternatives` holds
  the competing readings of a request before anything commits to one,
  `forecast_outcome` states what the chosen method will cost and produce
  before it runs, and `calibrate` compares that forecast against what
  happened. Each is skippable per pass, and each default reports absence
  rather than agreement, a run that never predicted anything has not shown
  good judgement, it has shown none. `_CORE_STEP_IDS` is now derived from
  `KERNEL_NODES` instead of restating it, so a node can no longer be added to
  the kernel and silently arrive with no questions, no contract, and an empty
  portfolio that looks exactly like a full one.

- **The portfolio is now judged on use, not on intent.** Every packet offers
  the model a portfolio it may draw on, with selection authority its own and
  the active step only a hint. Nothing recorded which options it actually
  used, so a perspective carried by every solved run and one nobody has ever
  picked were indistinguishable, and any addition to the portfolio was a
  guess. `core.option_selection` adds one uniform ask to every packet's
  output contract, captured and removed at the single point every model
  response passes through, so no step's typed schema knows it exists. A
  reference to an option the packet never offered is recorded as exactly
  that rather than counted as use, and a step that called without reporting
  stays visible beside one that did. `core.task_region_statistics` folds the
  per-run tally into each task region, keeping solved and unsolved use apart
  because summing them away destroys the only signal worth having, and
  `option_evidence()` reads the result back with its counts, its thin-evidence
  warning, and its own statement that it never narrows what a later call is
  offered. What a caller says it needed and was not offered is kept verbatim,
  because a portfolio can only learn what is missing if something records the
  asking.

- **A prompt block carries its own slice of the packet, and no other block's.**
  The practitioner renderer mapped thirteen canonical blocks onto ten packet
  fields, so `[PERSONA]` and `[PERSPECTIVES]` rendered the same 5,120 bytes,
  `[CAPABILITIES AND LIMITS]` and `[AVAILABLE CAPABILITIES]` the same runtime
  facts, and `[DIRECTIVE]`, `[CURRENT OBJECTIVE]` and `[FINAL DIRECTIVE]` the
  same directive three times. Measured on a real rendered packet, 7,423 of
  39,075 bytes were byte-identical repeats: 19.0% of every model call, on
  every step, for the life of a run. `BLOCK_SOURCES` now assigns each block a
  disjoint set of keys, so the same prompt carries the same information in
  31,656 bytes with nothing dropped, and a label predicts its contents. Three
  self-tests hold the line: no key backs two blocks, no two rendered blocks are
  byte-identical, and the thirteen canonical blocks appear once each in order.
  `core.primitive.record.select` is the new intrinsic that takes a named subset
  of a record; a key the record does not hold is reported as
  `absent_from_packet` rather than dropped, because a thin packet is a reason
  to reason with less, not to stop rendering.

- **What a supplied file is, is a model call, not a rule.**
  `core.source_role_orientation` asks one bounded model call to state what
  each supplied file is, in its own words, citing the bytes it read. The
  runtime admits the reading only against facts it holds exactly (the manifest
  digest and the admitted path set), refuses a claim about a path it never
  admitted, and refuses a manifest entry left silently unaccounted for: an
  unknown role is a state to record, not a file to omit. The reading is saved
  per manifest digest and stated on every later call as `runtime_facts`
  `source_roles`, so a run pays for it once. No file name, layout, or role
  vocabulary is written into the runtime, and a self-test scans this module's
  own executable code to keep it that way.

- **The runtime states what a field holds, not just what it is called.**
  `core.source.profile` now reports, per field and over a bounded row sample,
  how many distinct values appeared, some of them, how many were empty, and
  whether every one parses as a number. A live run read a column of `Yes` and
  `No` as a continuous target, chose a regressor, and reported a root mean
  squared error it could not have computed; the header allowed that and the
  values would not have. The same profile is the evidence one orientation
  call reads, and a reading must name the fields it rests on: a field name
  the runtime never profiled is refused, because it was not observed.
  Delimited files are parsed with `csv.reader`, so a quoted value containing
  the delimiter no longer shifts every field after it.

### Changed

- **Durable rules moved out of the Kaggle task text and into the runtime.**
  The cells no longer explain the manifest, the sandbox paths, the difference
  between a header and a value, or which files may be authored. Every one of
  those is now stated by the runtime that enforces it, `sandbox_paths_usage`
  and `byte_counts` in runtime facts, `usage` on the source profile, the
  project contract on authored files against expected artifacts, so an
  unfamiliar task inherits them instead of needing them written down again.
  What a task text explains, the next task will not.

- **Generated-project assembly is its own module.**
  `core.adaptive_practitioner_project` now owns input placement, the project
  candidate, the authored-file repair loop, and checkpoint reuse, leaving
  `core.adaptive_practitioner_capabilities` to dispatch. It takes the
  Practitioner state and the selected plan rather than the capability
  request, so nothing below dispatch depends on a name defined above it.

### Fixed

- **A control arm that controlled for nothing.** Arms were assigned from the
  stage signature alone, so a region landed in the same arm forever: the
  treated and control arms could never contain the same kind of work, and the
  one question worth asking, what happens to *this* region with help and
  without, was unanswerable by construction. `experiment_arm()` now hashes
  the experiment, the signature, the occurrence and a campaign seed together.
  Independent occurrences of one region fall on both sides (measured: 51
  control of 400), while every retry of a single occurrence stays put, so a
  failing run cannot walk itself into the other arm. Separate experiments
  assign independently, so a stage may be treated in one and control in
  another.

- **Evidence could vanish without saying so.** Write failures were suppressed
  and unreadable rows skipped, which kept a degraded store from failing a run
  and also made "no prior stages" indistinguishable from "the recorder
  broke". Those call for opposite responses. The store now counts write
  failures and unreadable rows, keeps the last error, and reports itself
  degraded.

- **`BY_EXACT` did not mean exact.** It matched the same normalised
  situation, not the same activation; two runs meeting the same situation are
  separate occurrences. Calling that "exact" invited reading it as identity
  and would have corrupted later deduplication and credit assignment. It is
  `BY_SIGNATURE`.

- **Motifs were four rules I wrote from no data.** The vocabulary was
  whatever their author had thought of, asked in order so the first match
  won, with everything unanticipated collapsing into `unclassified`, a
  closed taxonomy presented as an open one, deciding cross-domain retrieval.
  Motifs are now derived from which of the record's own fields are engaged:
  every combination is named, including ones nobody anticipated, and adding a
  situational field widens the vocabulary with no list to update. The
  cross-domain matches this was built for survive the change, a provider
  failover and a non-reproducing test still meet at
  `failure_diagnosis/incoming_observation+unknowns`.

- **A run that fails hard no longer loses its stages.** Stage persistence was
  wired into the normal completion path only, and three failure exits return
  before it. Those are the runs most worth learning from, where recovery,
  model demand and response shape are actually tested, and an email run that
  died with nine transport failures and zero completed model steps wrote
  nothing at all. Every exit now closes the stage record with the outcome it
  actually had: a cancelled run leaves them unknown rather than failed,
  because cancellation says nothing about whether the work was going well.
  The defensive wrapper around the close had hidden this: it swallowed the
  absence as readily as it would have swallowed an error.

- **A bound the model is shown is now a bound admission enforces.** The choice
  interface rendered "SETTINGS YOU MAY ADJUST (bounds are enforced)" above
  ranges written as prose, `"between 512 and 65536"`, while admission checked
  only that the setting's name had been offered. Any value at all was
  admitted, and the sentence promising otherwise was false. `ParameterSpec`
  carries the bound as a value: type, minimum, maximum, enum members, unit,
  and whether the setting may change for this call at all. A proposal outside
  it is refused with the reason, never clamped, and the refusal is counted
  rather than dropped. Nine cases are held by test, above maximum, below
  minimum, wrong type, a float where an integer was asked for, a boolean
  where a number was, outside the enum, an immutable setting, and removing
  the enforcement fails them. Settings still described in prose are rendered
  as explicitly unenforced instead of borrowing the language of a bound.

- **A route no longer refuses every request because of a ceiling nobody
  asked for.** When a caller names no output ceiling the gateway defaults to
  the model's declared maximum. One configured route declares 1,048,576
  output tokens against a 131,072 context window, so every request through it
  was refused by the context preflight before the provider was contacted,
  the route could never succeed. A ceiling the gateway chose for itself now
  fits the window it is aimed at. A ceiling the *caller* named is still
  refused when it does not fit, because that number is the caller's and
  shrinking it silently is the truncation the preflight exists to prevent.
  Found by turning provider failover on: the fallback route was reached
  correctly and then refused itself.

- **A run that was asked to reason and could not now says so.** When no model
  execution is configured the solve silently became a deterministic run, and
  the outcome recorded only the mode it used, so a demoted run and a run
  nobody ever asked to reason produced identical records. The outcome now
  carries `requested_mode` beside `selected_mode`, and a demotion carries the
  reason it happened. This does not prevent the demotion, which is correct
  behaviour when there is no model to call; it stops the demotion from being
  invisible to whoever reads the result afterwards. Provider failover is a
  different thing entirely and is untouched: failing over between providers
  keeps the reasoning alive, and is the behaviour you want.

- **A verified Kaggle solve no longer ends with its results unpublished.** The
  notebook cells run the solve as a subprocess and put the engine on that
  subprocess's `PYTHONPATH`, then import `loop_engine` in their own process to
  publish the run's outputs. Installing with pip makes that second import work
  as a side effect; the `pythonpath` fallback did not, so a solve that reached
  `COMPLETED_VERIFIED` ended with `ModuleNotFoundError` at the publish step and
  no `submission.csv` at the working root, the one file the submit dialog
  looks for. That fallback exists so the cell stays testable outside Kaggle,
  which means the solve-stage harness could never reach the publishing path it
  is there to check. All three cells now put the source tree on `sys.path` as
  well, so both install modes behave the same from the cell's point of view.

- **Every record parsed from a model now treats surplus as information.** The
  same exact-set validation that ended runs on `selection_report` also guarded
  the model's statement of which supplied file plays which role, every file it
  generates for a project, and its review of a compiled task, all three on the
  path a competition run takes. A caller with more to say than the schema names
  had its whole reply discarded, orientation and work together. Absence is now
  the defect in each, the refusal names the missing fields, and a guard holds
  the rule in both directions. Records parsed from storage keep exact-set
  validation, because both sides of those are code; so does the web search
  response, where a closed contract against untrusted external input is the
  guard rather than rigidity.

- **What a run reports is heard, whether or not anyone named it first.** Four
  layers each kept only what they already knew about, and the loss compounded
  in silence. The progress writer was a permission list, so
  `practitioner.options.selected` travelled across whole campaigns with every
  field of its content stripped, 219 events over twelve competitions saying a
  choice had been made and never what it was. It is now a denial: credential-
  shaped names and raw payload carriers are withheld, values are bounded, and
  everything else travels, so a field nobody wrote down in advance still
  arrives. `admitted_selection()` kept five channels and dropped the rest;
  unrecognised keys are now carried as bounded observations, counted nowhere,
  and the contract invites them outright, because a channel nobody thought to
  offer is the most useful thing the report can carry. The typed records
  rejected any answer with an extra field: absence is now the defect, extras
  are information, and the caller reports them rather than refusing the work
  that came with them. The tally reaches the caller too, `option_selection`
  was built every run and left inside run history, where the cross-run
  question it exists to answer could not reach it.

- **An empty answer and an unreachable provider no longer share a retry
  budget.** They say opposite things. A network error says the provider could
  not be reached, and a fourth call into a dark socket is waste. A response
  that arrived carrying no answer says it was reached, answered on time and
  under its ceiling, and spent the whole budget on private reasoning, so the
  next sample is likely to answer. One shared count of three served the first
  case and starved the second: on a twelve-competition campaign one run saw
  five empty answers in ten calls and never got past orientation. Empty
  answers now get their own budget of six; every other retryable code keeps
  three, and each attempt is still a published, counted model call.

- **A run is told the machine its code will actually run on.** The runtime
  facts reported `execution_isolation: host_process` whenever local execution
  was authorised, but execution prefers Docker whenever Docker is available
  and treats the local backend only as a fallback for when it is not. On a
  machine with Docker the model was therefore told it was running as a host
  process while its code ran in a container, and learned otherwise from an
  import error several minutes later. The fact is now decided the way
  execution decides it, and the self-test compares the two rather than
  asserting a written-down answer, the old check asserted `host_process`,
  which is to say it pinned the defect in place.

- **A finished record no longer archives whole datasets.** One competition run
  wrote a 113 MB `adaptive-result.json`, of which 80 MB was the verbatim
  content of the `train.csv` it had inspected, beside the `path`,
  `byte_count` and `digest` that already identify that file, which is
  read-only and still on disk. Three such runs writing into a RAM-backed
  temporary filesystem exhausted the machine, and every reader of run history,
  playback and analytics had been parsing those bytes back. The model view was
  already bounded and the run still holds the full body in memory for
  deterministic project inputs; only what is written to disk afterwards is
  bounded now, and an elided body says that it was elided and where the file
  is, so a later reader can tell that apart from a file that was empty.

- **A response that arrived carrying no answer is now tried again.** The
  provider finished normally, `stop`, under its output ceiling, no transport
  error, and returned only private reasoning with no final answer. The
  gateway rightly refused it, but `output_validation_failed` was outside the
  retryable set, so the refusal escaped as fatal and ended whole runs at their
  first step over a single unlucky sample. Nothing about the request was
  wrong and nothing in the run's state had changed, which is exactly the
  condition under which another attempt is worth making. Format repair does
  not cover this: repair feeds a malformed answer back, and here no answer
  arrived to repair. `rate_limited` was fatal for the same reason and is now
  retried too, on a longer wait, because what is being waited for is a limit
  clearing rather than a connection settling. Two self-tests hold the line in
  both directions, since a fatal code discards a run and a retryable one
  spends three calls to earn the same refusal, and neither shows up in any
  other gate, both merely produce a run that ends.

- **An optional record no longer kills the run it was attached to.** Packets
  ask every call to report what it drew on, presented as
  `selection_report: {keys: {...}}`. Models answered in both shapes the
  contract invites, the five keys flat, or one object under the container
  name, but only the flat keys were stripped before typed validation, so a
  nested answer reached `TaskOrientationResult.from_mapping`, failed its
  exact-set field check, and ended the run at orientation with nothing
  produced. Four of the first competition runs in a twelve-competition
  campaign died this way. The record is documented as optional and
  `affects_validation: False`; it was neither. `SELECTION_KEYS` is now derived
  from the contract rather than restated beside it, covers the container name,
  and `admitted_selection()` reads either shape.

- **A refusal now names the fields it refused.** `TaskOrientationResult fields
  do not match version 1` told a reader that something was wrong and nothing
  about what, and it was fed verbatim to the repair attempt as the whole of
  its guidance, so the second attempt was as blind as the first. The message
  now names the unexpected and missing fields, which is how the cause above
  was found rather than guessed.

- **Three copies of one field list became one.** The 30-field orientation
  schema shown to the model, the `required` set enforced against it, and the
  selection keys stripped before it were each hand-maintained. `required` is
  now derived from the record's own dataclass fields (as is
  `NextActionDecision`'s), and a self-test parses the schema literal shown to
  the model and fails if it drifts from the record enforced on it, the one
  copy that must stay hand-written because it documents a type per field.

- **A diagnostic now arrives saying what it found.** The solve progress writer
  copies a fixed field allowlist, so every typed diagnostic's payload was
  silently discarded: a campaign produced `orientation_invalid` on four
  competitions and the published event carried neither the attempt nor the
  findings, leaving nothing to diagnose but the name of the problem. The
  screened payload now travels as one named field, bounded and marked when
  truncated, so any writer that carries that field delivers the whole detail.
  This is the "refusals carried no reason" defect, fixed once for capabilities
  and surviving in the diagnostic path.

- **A Python exception class name is not a failure layer.** The terminal-code
  mapping sent `AdaptivePractitionerError` straight to `VERIFICATION_FAILED`,
  so a live run that produced two invalid orientations and verified nothing
  still reported a verification failure, the same defect the layer inference
  was built to remove, surviving one level up. A class name says which module
  raised, not which layer failed, so generic names now defer to the evidence.

- **A provider that answered proves transport succeeded.** The layer inference
  read only admitted orientations and decisions, so a run whose every
  orientation was rejected left no record and looked identical to one the
  provider never reached, two failures needing entirely different repairs.
  `model_usage` carries typed `provider_responded` and `ok` fields; a recorded
  response now establishes the semantic layer whether or not anything the
  model said was admitted. The live run this was found on now reports
  `NO_PROGRESS`, which is what it did.

- **A model could type the results it claimed to have produced.** A generated
  project could declare the same path as both an authored file and an
  expected artifact, which made the artifact check vacuous: the bytes existed
  before any command ran. A live run declared `submission.csv`,
  `metrics.json`, `report.md` and `verification.json` that way, typed
  cross-validation scores it never computed and a submission it never
  predicted, and passed the artifact check on all four. The two sets must now
  be disjoint. Authored files stay fully evidenced by the write record; they
  simply are not evidence of an execution. The repository's own fixtures
  carried the same shape and were corrected, which is why the gap survived.

- **A refused call reported the wrapper instead of the reason.** A failure
  inside a governed Loop arrives wrapped, and the untyped fallback described
  the wrapper: the model read "deterministic check validate generated project
  input use raised inside loop 1470 (evidence on the ledger)" twenty times
  while the sentence naming the wrong path sat two links down `__cause__`.
  `rejection_from_exception` now reports the deepest cause and names the
  wrappers it travelled through, for every capability. The input-use refusal
  also names the literal the code opened, the path that literal should have
  been, and the whole admitted set, so the repair is a substitution rather
  than a diagnosis.

- **Every capacity on the path from task to data to model call is now
  measured.** `core.runtime_capacity` is the one place a limit comes from, and
  it derives each from something real: memory and disk this machine reports,
  the byte allowance this run's own context budget already declares, or the
  length of the paths actually present. The declared figures it replaced are
  gone, the supplied-input ceiling, the sixty-four-path manifest cut, the
  orientation's evidence and role budgets, the two-hundred-row profile sample,
  the selected-content byte caps. Each answer carries its measurement, so a
  refusal quotes the number that caused it instead of asserting a rule, and a
  self-test refuses any capacity-shaped integer reintroduced into those
  modules, proving itself by planting one and catching it.

  This is the same defect as the sixteen-megabyte cap below, stated generally.
  Raising a number moves a wall; measuring removes it. On this machine the
  input ceiling is now about twenty gigabytes rather than five hundred
  megabytes, it moves with the hardware, and the row sample grows with the
  run's context instead of stopping at a number nobody chose for this data.

- **A real competition could not be placed in the workspace at all.** The
  generated-project workspace capped every file at a flat 16 MB. Against the
  real playground-series-s6e9 files a live run placed only the 7.7 MB
  submission template and refused the 18.3 MB prediction rows and the 44.7 MB
  training rows, so no amount of model reasoning could reach a result. The
  limit now grows to the largest input the runtime itself admitted, refusing
  to place a file the runtime chose to supply is the runtime contradicting its
  own decision, with a stated ceiling that bounds one read, checked by size
  during selection rather than discovered halfway through a copy. Runtime
  facts state `byte_counts` and `placement_limit_bytes` beside the paths, so
  a size refusal is foreseeable rather than surprising.

- **Closed vocabularies were enforced without stating themselves.** A refused
  next-action kind said only "NextActionDecision kind is invalid", naming
  neither the rejected value nor the admitted set, and a live run spent seven
  passes proposing semantic step ids as action kinds because the packet's
  question portfolio names those far more prominently than the schema string
  does. Both that refusal and the ambiguity-state refusal now name the
  rejected value and the admitted vocabulary.

- **The action fence never saw the most expensive capability fail.** Three
  `core.generated_project` refusal paths returned a result packet without
  telling the fence, so the model-visible fence view stated
  `recent_failures: []` while a run refused the same construction on twenty
  consecutive passes. All three now record. An attempt is identified by its
  manifest digest rather than by the empty argument set every
  generated-project call shares, so an identical failed project is refused
  before it costs anything while a corrected one stays admissible, and a
  project that executed but failed its own deterministic checks is remembered
  as failed rather than cleared.

- **Two path spaces for one file, never reconciled.** Runtime facts stated a
  supplied file at its admitted manifest path while `core.generated_project`
  materialized it under an `inputs/` prefix, so generated code opened the path
  the runtime had told it about and found nothing. The prefix is now one rule
  (`project_input_path`) that both the materializer and the facts projection
  call, and runtime facts state `sandbox_paths` beside `paths` with which is
  which.

- **OpenCode as a Loop realization.** `OpenCodeProcessAdapter` runs one
  bounded headless `opencode run --format json` inside the canonical external
  harness Loop: version and model-listing handshake, default starting
  instructions from a versioned prompt resource, isolated working directory,
  raw events stored by digest, model turns with tokens and cost, tool events
  with effect classes and no bodies, changed files as artifact references,
  and wall-clock cancellation. Completion is not acceptance; the spawning
  Loop verifies.
- **Region evidence and self-tuning in solve.** Before the first model call,
  `solve_task` projects saved runs in the task's region into region
  statistics and an advisory shortcut decision, chooses the context budget
  variant from recorded prompt experiments with a seeded exploration rate
  (`core.self_tuning`), records the decision on the outcome, and hands the
  evidence to the Practitioner as one advisory context block.
- **Kaggle harness competition kinds.** `kaggle/check_cells.py` builds a
  synthetic binary, regression, or multiclass competition
  (`--competition-kind`), so each cell is proved against three target shapes
  offline before any live run. The notebook settings a Kaggle user must set
  are documented in `kaggle/README.md`.
- **Context pack manifests.** Every assembled work packet now records a
  `ContextPackManifest`: each context block and trimmed state item with its
  digest, decision (included, compacted, excluded, deduplicated), trust class,
  byte counts, the estimated input tokens, and the operator ceiling verdict.
  The manifest is stored as an artifact and summarized on the owner Loop's
  ledger as `context_pack_compiled`.
- **Supervision policy.** The runtime's non-progress guards are one typed,
  versioned `SupervisionPolicy` (identical failures before stop, non-progress
  passes before escalation, the escalation ladder, the spawn depth guard)
  carried by `LoopConfig` and `KernelRunRequest`, round-tripped through Loop
  definitions when declared, and recorded on every Loop's init event.
- **Checklist Practitioner.** A `practitioner.checklist` profile and
  `gated_checklist` template run ordered deterministic checks against typed
  facts; a clean gate completes with zero model calls and a failed blocking
  item records the gate firing and escalates to a spawned Loop.
- **Cross-process Loop handoff.** `LoopHandoffRequest` ships one Loop's exact
  definition to another process; `LoopHandoffEnvelope` returns its namespaced
  events with a digest and idempotency key; the parent verifies, refuses
  duplicates and tampering, merges the events into one hash-chained history,
  and records the spawned return.
- **Task frontier, prompt experiments, and region statistics.** Saved
  adaptive results project into digest-chained per-pass `FrontierSnapshot`
  records (questions, hypotheses, experiments, recovery actions with typed
  statuses), one `PromptExperimentRecord` per model call (task region, stage,
  prompt and context identities, provider, tokens, estimate calibration, pass
  verdict), and rebuildable `TaskRegionStatistics` with an advisory
  `ShortcutDecision` that states its thresholds and negative evidence.
- **Bounded model context.** A typed `ContextBudgetPolicy` bounds command
  output, fetched text, and older attempt history before the Practitioner
  state enters a model packet, records every trim with its digest, and the
  model gateway refuses a request whose estimated input plus requested output
  exceeds the route context window before contacting the provider. New solve
  flags: `--context-budget-tokens` and `--allow-local-execution`.
- **LLM-first open-task solving.** Public solve preserves an unbound typed task,
  gives templates and prior solutions to the model as optional candidates, and
  requires the model to select the next action. Task words and fingerprint
  scores cannot select a solution branch.
- **Model-selected source inspection.** Repository and dataset runs can inspect
  a manifest, select exact text bodies with digests, then use those same inputs
  in a later build or repair pass.
- **Answerable material questions.** A blocked solve returns typed question and
  answer-slot records. A later activation accepts feedback without changing the
  original task.
- **Optional work ceilings.** Pass, model-call, token, recursion, spawned-work,
  candidate, and provider-attempt ceilings are unset unless an owner, provider,
  or policy supplies one. Exact repeated state, action, evidence, and failure
  still triggers diagnosis instead of no-op churn.
- **Model-selected context and portfolios.** Step affinity, retrieval scores,
  evaluation metrics, and generation templates now produce passive candidates.
  The consuming model selects perspectives, questions, Intelligence refs,
  Solution candidates, recovery routes, and generation strategies. Runtime
  code validates those selections but does not calculate a semantic winner.
- **Reusable Capability Flywheel.** Accepted generated code can emit an
  asynchronous reuse opportunity, remain isolated as a candidate, pass exact
  independent qualification and promotion, enter a rebuildable search view,
  and execute on a future exact task with zero model calls. Bounded hybrid
  profiles support normalization, reranking, adaptation, diagnosis, repair,
  and composition without adding run modes.
- **Transactional semantic Loop contracts.** An exact `LoopDefinition` can bind
  a complete implementation-independent behavior contract. Qualified direct or
  hybrid interpretation produces an untrusted candidate. Independent
  verification, effect authorization, and compare-and-swap commit control
  trusted state. Stable behavior can enter the existing capability flywheel and
  return as a promoted zero-model deterministic realization for a declared
  input region.
- **Self-orienting abstraction governance.** The Development Assurance Plane
  can build a digest-bound live authority map and run a contextual
  whole-repository hardcoding audit. Typed parameter inputs distinguish
  omission, null, empty, false, and zero. Versioned prompt bundles carry slot,
  trust, provenance, and render identities without adding another runtime or
  settings authority.
- **Optional descriptive Code Intelligence graph evaluation.** A scoped
  `.graphifyignore` keeps generated evidence and schema-governed JSON records
  out of Graphify's optional source graph. The evaluated graph remains passive
  evidence and cannot replace Loop, Code Intelligence admission, or capability
  resolution authority.
- **Context Intelligence outage fallback.** The full Practitioner portfolio is
  now stored under Context Intelligence. A separate minimum packaged portfolio
  keeps basic task interpretation available only when an outage is declared
  and the selected fallback policy permits it.
- **Artifact-producing `loop-engine solve` command.** Text, task-file, dataset,
  and repository inputs can now run through the canonical Practitioner,
  generated-project capability, confined Docker workspace, artifact inspection,
  and Run History. Results use an honest terminal vocabulary and include exact
  workspace, artifact, verification, model, tool, and inspection details.
- **Governed semantic and strict atomic granularity profiles.** Public solve
  uses one governed assembly Loop per model packet. Strict atomic assembly
  remains available when logical value-operation history is required.
- **Optional dependency groups.** The default install supports the solve path
  without downloading the full ML and GPU stack. `data`, `integrations`, and
  `all` extras retain the larger adapters.
- **Product quickstart acceptance.** Four changed tasks create a utility,
  transform local data, index documents, and reproduce and repair a failing
  Python package through real Docker execution.
- **Saved product outcomes.** Each completed or blocked solve now binds its
  typed terminal result, verification, artifacts, workspace, limitations, and
  selected Canvas to the saved Run History manifest by digest. Reports,
  playback, the runs command, and Studio read the same verified bundle.
- **Product-first CLI and Studio.** Concise `configure`, `doctor`, `solve`,
  `runs`, `report`, and `studio` commands support the complete first-user
  journey. Studio is read-only, isolates corrupt runs, and renders result,
  tree, runtime, Canvas, playback, and call views on desktop and mobile.
- **Added-file extensions.** Reviewed provider routes, capability candidates,
  skills, plugins, and intelligence can be discovered from extension folders
  without editing the package. OpenRouter and OpenCode Zen resolve current
  compatible zero-cost catalog entries at invocation time.
- **Downloadable task library.** Plain text tasks and sample inputs can be
  downloaded from GitHub. A task instruction file can now be combined with one
  dataset, repository, or URL source.
- **One recursive `Loop` runtime.** Search, advice, model calls, adapters,
  validators and whole solutions all execute inside the same envelope, with
  `deterministic`, `hybrid`, and `non_deterministic` modes configured per loop.
  A loop's own modes are separate from its spawned-delegation authority.
- **Provider gateway.** Ollama Cloud, Mistral, and OpenRouter adapters behind
  `ModelGateway`, plus `CustomEndpoint`, a parameterized adapter for any
  OpenAI-compatible or Ollama-native server (vLLM, LM Studio, llama.cpp,
  LiteLLM, an internal gateway).
- **Provider and model failover** with one model loop per physical attempt,
  provider pinning, output validation, split token usage, attempt ceilings,
  output ceilings, and total token ceilings.
- **Typed runtime settings** with YAML and environment precedence for loop
  defaults, search backends, provider references, model tiers, bounded
  escalation, operating policy, and Run History paths.
- **Separate model thinking power** with `small`, `medium`, `high`, `max`, and
  `specialized` tiers. Provider failover and tier escalation remain separate
  recorded decisions.
- **Versioned Loop profile ontology** with one shared Loop profile, Practitioner,
  Intelligence, and Solution branches, explicit semantic relationships, typed
  binding, required capabilities, and semantic-version handshakes.
- **Typed loop connections** that validate producer output roles and consumer
  input roles before execution. Different roles require a named Adapter Loop.
- **Typed API conformance** that refuses new public interfaces above the
  parameter cap unless they use an approved compatibility plan.
- **Benchmark candidate registry** with 144 cataloged tracks across ten task
  families. Every track remains not run and ineligible for comparison.
- **Model classification** from vendor-declared price, context, and reasoning
  support. Catalog classification itself makes no model calls. Provider
  verification uses small real calls and must be authorized.
- **`configure()`** gives one statement of which loop
  modes this installation can run, verified by real calls.
- **Loop reports** in text, Markdown, HTML, and JSON, projected from the run's
  own ledger, with a CLI: `--runs`, `--report`, `--format`, `--out`.
- **Hash-chained Run History** over a closed vocabulary of canonical event
  families.
- **Five-problem campaign CLI** with frozen inputs and evaluators, deterministic,
  hybrid, and model-led arms, provider pinning, Run History storage, live console
  events, and Studio playback.
- **Four dedicated intelligence guides** for Context, Code, Runtime History and
  Solution, and User Feedback Intelligence.
- **Zero-tolerance conformance gates** and a built-in behavior suite.
- Seventeen documented example folders.

Defects found by running against live models, each now carrying a regression
test:

- A live run could propose the same rejected capability call for twenty
  passes. The runtime now keeps a per-run repeated-action fence
  (`core.action_fence`): once one exact (capability, arguments) identity has
  failed the policy count, the identical call is refused with the last typed
  rejection attached, for every capability without naming any task.
- Capability refusals reached the model as prose. Every refusal is now a typed
  `CapabilityRejection` (closed reason codes, rejected arguments, bounded
  admitted values with a total, runtime-authored repair hint) recovered
  through exception chains, so the next decision reads the runtime's exact
  facts instead of re-diagnosing an error string.
- Facts the runtime knew exactly (the admitted source manifest, workspace
  root, execution isolation, granted permissions, the fence view) were left
  for the model to guess. Every model packet now carries a `runtime_facts`
  context block projected by `core.practitioner_runtime_facts`; the manifest
  block states the exact admitted relative paths before any reasoning is
  spent on them.
- A run could end `BLOCKED_MATERIAL_INPUT` on model text that was not a
  question ("None for this orientation step...") after dozens of calls.
  `code_nodes.material_questions` screens blocking entries: only text
  phrased as a question a person can answer may pause the run; everything
  else is kept as a recorded limitation.
- Every Kaggle cell assumed a competition data layout and named the input file
  names in its task text, so a differently mounted dataset, a different slug,
  or a competition using other file names sent an unreadable path into the
  solve and spent the time budget on nothing. The cells no longer guess. Each
  hands the attached input root to the solve, enumerates and reports what is
  actually there, and stops at the solve stage when the root is missing or
  empty. The task text now instructs the Practitioner to request the manifest,
  read the admitted paths the runtime states, and decide from the observed
  schemas which files hold training rows, which hold rows to predict, and
  which defines the submission contract. An explicit
  LOOP_ENGINE_KAGGLE_DATASET_DIR narrows the root when an operator wants that.
- The Kaggle cell headers named a commit that had moved on. Each cell now
  states that it installs the current `main` archive, which is what it does.
- The canonical Loop could fabricate a `recovered` step outcome when a failed
  step's fallback mode was deterministic. The fallback now re-runs the handler
  under the requested mode and keeps the failure visible.
- A Loop with `accepted_success` and no ceiling iterated forever on an
  identical failure. The runtime now stops with a typed `BLOCKED` terminal
  after repeated identical failed outcomes and records the stop.
- Unbounded spawn recursion surfaced as a misleading "role profile is not
  registered" error. Profile lookup now catches only profile errors, and a
  typed depth guard refuses runaway nesting when no `max_depth` is declared.
- A compatibility rewrite of a contract's role or execution mode was silent.
  Init and spawn events now carry `contract_coerced_from` and
  `contract_coerced_to`.
- Owner-Loop steps around the Practitioner pass loop were labelled
  `complete`; they are now labelled `structural_boundary`, and the kernel
  records that its passes run inside the owner's `act` step.
- Command stdout and stderr from every prior attempt entered every later model
  packet without bound; one run averaged 122k input tokens per call.
- Format repair retried without bound on novel invalid output; it is bounded
  and fails with a typed repair-exhausted result.
- A missing provider key classified as `authentication_failed`, which stopped
  failover. It now classifies as `missing_credential`.
- The post-run workspace copy into Run History followed symlinks created by
  generated code. It now preserves symlinks and skips entries that resolve
  outside the workspace.
- Host execution when Docker is absent was automatic and labelled
  `no_network_host_execution`. It now requires `--allow-local-execution` and
  is labelled `host_process_network_unenforced`.
- Custom endpoints gain `tls_verification: ca_file` with `tls_ca_file`
  pinning; the TLS policy appears in provider descriptions, settings
  summaries, and the run's model-routing events.
- `--compile-provider` accepts a settings-declared provider id and resolves
  its key variable from that provider's `credential_env` instead of raising
  `KeyError`.
- Generated command timeouts must be finite and bounded, and pip setup
  arguments are limited to requirement specifiers and reviewed options.
- A Loop spawned directly with `spawn()` was not counted in its parent's
  result; spawn counts now include direct spawns and fold descendants in
  transitively when each spawned Loop returns.
- A `steps_complete` Loop whose final step failed still stopped as ACCEPTED.
  It now stops as `done_failed` with terminal code VERIFICATION_REJECTED, and
  `accepted` is false.
- A solved Practitioner run whose last orientation still listed blocking
  questions was refused by the typed outcome contract and reported as
  VERIFICATION_FAILED. Solved runs now carry those as `open_questions` on the
  result; only unsolved runs return BLOCKED_MATERIAL_INPUT. A contract
  refusal is labelled as such in the CLI failure record.
- A hand-built or copied DECIDED approval state passed `restore()` and
  `consume()` in any fresh `EffectApprovalService`. Decisions now carry a
  service-key HMAC (`decision_authority`) that restore, store load, and
  consume verify; the key never enters serialized state or the ledger.
- The hardcoding audit Loop treated a failed verify step as accepted; it now
  returns the report with the rejected terminal recorded.
- A step handler that raised left its Loop with no terminal event. The Loop
  now records the exception type and message digest, stops as
  `handler_exception` (INTERNAL_PROTOCOL_ERROR), and re-raises.
- The Kaggle check harness can write binary, regression, or multiclass
  synthetic competitions (`--competition-kind`), and the cells no longer
  carry stale commit references in their headers.

- OpenRouter zero-price selection could choose a non-text or extremely wide
  route merely because it advertised the largest completion maximum. Live
  validation returned an invalid-request failure. Selection now requires text
  output, honors an explicit run capacity cap without truncation, and prefers
  native structured output before generic response formatting.
- A bounded parameter Intelligence Loop allowed hybrid execution but did not
  delegate the one non-deterministic model call it required. The live runtime
  correctly refused before contacting a provider. Its delegation contract now
  permits the one budgeted model invocation.
- The parameter inference prompt named output fields but did not state their
  types. A real provider returned strings where arrays were required and null
  where a string was required. Deterministic validation rejected the proposal;
  the versioned resource now includes the exact field-type contract.

- A generic structured-data solve could report success after whitespace
  normalization even when the requested transform and output artifacts were
  not produced. An exact deterministic resolver may run only when explicitly
  selected and independently verified.
- The package exported a second heuristic `solve()` function that guessed
  tabular roles from filenames and task words. It was removed. `SolveRequest`,
  `solve_task()`, and `loop-engine solve` are the only solve authorities.
- The task compiler selected the nearest template even for weak lexical
  matches. Default compilation now returns an open task and advisory candidates.
- The base wheel self-test treated optional data, MCP, telemetry, and vector
  adapters as missing required dependencies. It now verifies the base product
  and reports absent optional adapter suites as not tested.
- The default wheel pulled large benchmark, ML, and GPU dependencies before a
  new user could run `doctor` or `solve`. Those packages are now optional.
- Broad package-data patterns could include ignored local Run History and
  Studio state in a distribution. Wheels and source distributions now exclude
  local run state and check the built archive before clean installation.
- Saved run IDs were used as path components without a portable segment check.
  Save, load, report, playback, and Studio now reject traversal-shaped IDs
  before filesystem access.
- Compatibility Loop construction derived output-port names from human goal
  prose. It now uses a stable `result` port unless a typed contract supplies a
  more specific role.

- `advice_function` used the global provider order instead of the providers the
  caller's own `configure()` verified. Configuring only a self-hosted
  server produced a callable that contacted and billed a different provider.
- `estimator_from_moves` took the first match, so *"Use **LightGBM**
  (gradient-boosted trees)"* selected a different estimator: the model's
  recommendation was overridden by a word inside its own explanation. Now ranks
  by specificity rather than position.
- `_engineer_features` recognised only patterns from one dataset shape, so
  advice proposing a named-column ratio engineered nothing.
- `studio_server.self_test` indexed a saved run that does not exist on a fresh
  clone. It passed only because earlier runs were lying around on disk.
- Semantic mode labels were counted as model calls even when no provider was
  contacted. Run History and reports now use explicit provider events for
  physical model-call accounting.
- A model-output validator exception escaped the gateway and stopped provider
  fallback. It now becomes a typed validation failure.
