# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0]: unreleased

First public release.

### Added

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
  layer a run reached from its own record — orientations and decisions mean
  semantic work, project attempts mean execution, a verdict or a completed
  method means verification — and absent all of it the run reached transport
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
  `operator_gap` — what it needed, what it tried, what the runtime refused
  with — which is admitted, marked with whether it names an operator that
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
  root entries — a source checkout, a logs tree, a solutions tree, a settings
  file and a task file — none of which a person submitting a competition
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
  published with that named — this repository has shipped that exact failure,
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
  to 30, and every step now carries persona affinities — `orient` previously
  had none, so all 42 perspectives read as unmatched on the first call of
  every run. Nothing was removed and nothing was gated: affinity is advisory
  metadata, and every perspective, question set and guidance record still
  ships on every call for the model to select from.
  The canonical kernel gains three optional nodes: `frame_alternatives` holds
  the competing readings of a request before anything commits to one,
  `forecast_outcome` states what the chosen method will cost and produce
  before it runs, and `calibrate` compares that forecast against what
  happened. Each is skippable per pass, and each default reports absence
  rather than agreement — a run that never predicted anything has not shown
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
  those is now stated by the runtime that enforces it — `sandbox_paths_usage`
  and `byte_counts` in runtime facts, `usage` on the source profile, the
  project contract on authored files against expected artifacts — so an
  unfamiliar task inherits them instead of needing them written down again.
  What a task text explains, the next task will not.

- **Generated-project assembly is its own module.**
  `core.adaptive_practitioner_project` now owns input placement, the project
  candidate, the authored-file repair loop, and checkpoint reuse, leaving
  `core.adaptive_practitioner_capabilities` to dispatch. It takes the
  Practitioner state and the selected plan rather than the capability
  request, so nothing below dispatch depends on a name defined above it.

### Fixed

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
  still reported a verification failure — the same defect the layer inference
  was built to remove, surviving one level up. A class name says which module
  raised, not which layer failed, so generic names now defer to the evidence.

- **A provider that answered proves transport succeeded.** The layer inference
  read only admitted orientations and decisions, so a run whose every
  orientation was rejected left no record and looked identical to one the
  provider never reached — two failures needing entirely different repairs.
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
  gone — the supplied-input ceiling, the sixty-four-path manifest cut, the
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
  limit now grows to the largest input the runtime itself admitted — refusing
  to place a file the runtime chose to supply is the runtime contradicting its
  own decision — with a stated ceiling that bounds one read, checked by size
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
