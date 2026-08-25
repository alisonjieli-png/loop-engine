# Changelog

All notable changes to this project are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0]: unreleased

First public release.

### Added

- **One recursive `Loop` runtime.** Search, advice, model calls, adapters,
  validators and whole solutions all execute inside the same envelope, with
  `deterministic` / `hybrid` / `non_deterministic` modes granted by permission.
- **Provider layer.** Ollama Cloud, Mistral, and OpenRouter adapters behind one
  contract, plus `custom_endpoint`, a single parameterized adapter for any
  OpenAI-compatible or Ollama-native server (vLLM, LM Studio, llama.cpp,
  LiteLLM, an internal gateway).
- **Failover** that records every attempt including refusals, and reports total
  failure as failure rather than degrading to a non-model answer.
- **Zero-model-call model discovery.** Live catalogs classified into roles from
  vendor-declared price, context, and reasoning support, stamped
  `basis="declared", measured=False`.
- **`configure()`** gives one statement of which loop
  modes this installation can run, verified by real calls.
- **Loop reports** in text, Markdown, HTML, and JSON, projected from the run's
  own ledger, with a CLI: `--runs`, `--report`, `--format`, `--out`.
- **Hash-chained Chronicle** over a closed vocabulary of canonical event
  families.
- **Zero-tolerance conformance gates** and more than 900 built-in tests.
- Ten documented example folders.

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
