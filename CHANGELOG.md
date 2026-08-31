# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0]: unreleased

First public release.

### Added

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

### Fixed

Defects found by running against live models, each now carrying a regression
test:

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
