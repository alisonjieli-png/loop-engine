# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0]: unreleased

First public release.

### Added

- **One recursive `Loop` runtime.** Search, advice, model calls, adapters,
  validators and whole solutions all execute inside the same envelope, with
  `deterministic`, `hybrid`, and `non_deterministic` modes configured per loop.
  A loop's own modes are separate from its child-delegation authority.
- **Provider gateway.** Ollama Cloud, Mistral, and OpenRouter adapters behind
  `ModelGateway`, plus `CustomEndpoint`, a parameterized adapter for any
  OpenAI-compatible or Ollama-native server (vLLM, LM Studio, llama.cpp,
  LiteLLM, an internal gateway).
- **Provider and model failover** with one model loop per physical attempt,
  provider pinning, output validation, split token usage, attempt ceilings,
  output ceilings, and total token ceilings.
- **Typed runtime settings** with YAML and environment precedence for loop
  defaults, search backends, provider references, model tiers, bounded
  escalation, operating policy, and Chronicle paths.
- **Separate model thinking power** with `small`, `medium`, `high`, `max`, and
  `specialized` tiers. Provider failover and tier escalation remain separate
  recorded decisions.
- **Versioned Loop profile ontology** with one Loop root, Practitioner,
  Intelligence, and Solution branches, explicit parent relationships, typed
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
- **Hash-chained Chronicle** over a closed vocabulary of canonical event
  families.
- **Five-problem campaign CLI** with frozen inputs and evaluators, deterministic,
  hybrid, and model-led arms, provider pinning, Chronicle storage, live console
  events, and Studio playback.
- **Four dedicated intelligence guides** for Context, Code, Previous Run and
  Solution, and User Intelligence.
- **Zero-tolerance conformance gates** and more than 1,000 built-in tests.
- Fifteen documented example folders.

### Fixed

Defects found by running against live models, each now carrying a regression
test:

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
  contacted. Chronicle and reports now use explicit provider events for
  physical model-call accounting.
- A model-output validator exception escaped the gateway and stopped provider
  fallback. It now becomes a typed validation failure.
