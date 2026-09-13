# Embodiment comparison lab

This development application implements the independently launchable experiments in [embodiments](../../embodiments/README.md). It imports the canonical Loop runtime; the existing standalone `qualification_lab` remains independent and unchanged.

The implementation contains three separate boundaries:

```text
Experimental application
├── Frozen task and work-packet contracts
├── Independent placement adapters
│   └── each calculation executes as canonical Loop
└── Controller-owned evaluation and recording
    ├── independent verifier Loops
    ├── canonical Run History
    └── canonical reactive output portfolios
```

The current backend is trusted deterministic code, not a fake model. It measures process placement, packet integrity, bounded concurrency, state separation, activation persistence and output visibility. It does not qualify OpenCode, prefix caching, provider performance, or untrusted-code containment.

Run `PYTHONPATH=src:devtools python3 -m embodiment_lab list` from the repository root. Each visible embodiment folder has a standalone launcher. No implementation imports another implementation. Common code contains contracts, process transport, independent evaluator and canonical storage adapters.

Tests run with `PYTHONPATH=src:devtools python3 -m unittest discover -s devtools/embodiment_lab/tests -v`.

## Development guidance and nested control

Read [the development instructions](../AGENTS.md),
[the harness instructions](../../embodiments/AGENTS.md), and
[ASTRA.md](../../ASTRA.md) for current advisory comments. The
[layered harness design](../../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
supports an outer Loop around native harness iteration as a configuration
choice. Compare both control layers explicitly; do not infer that native
goals, tools, or session continuation are enabled by a documentation change.

## Live configuration comparisons

The [configuration grid search guide](../../docs/guides/configuration-grid-search-and-optimization.md)
describes how to extend comparisons to additional steps, prompts, intelligence,
resources, and fallback policies. Run the offline enumeration example with
`PYTHONPATH=src:devtools .venv/bin/python -m embodiment_lab.configuration_grid_example`.
It generates proposed configuration records through the canonical Loop,
without executing those configurations or calling a model.

The separate `configuration_study` entry point compares explicit response
admission policies through a configured real provider. `configuration_matrix`
compares context delivery, Context Intelligence, Markdown instructions,
independently reviewed skills, registered tool declarations, Practitioner
steps, temperature, and changed inputs on a frozen component population.
These entry points make real model calls. The original mechanism commands
above retain their deterministic backend.

Both applications use the existing Loop runtime, harness registry, provider
authority, Run History, artifact store, and DuckDB experiment projections.
They create new phase and attempt directories. Model responses remain
proposals until the separate evaluator checks the executed result.

Read the [configuration and native initialization report](../../docs/verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
for the completed September 12 study, exact counts, retained failures,
reproduction commands, and the full terminology explanation.
