# Loop Engine Devtools

The Development Assurance Plane: a first-class Loop Engine application
that reviews the repository against its own rules.

## Identity

- Devtools is NOT a second Node engine or second runtime.
- Every independently governed supervisor, specialist, scanner, and reviewer
  runs as an ordinary `Loop` through the canonical runtime.
- The root is the Repository Assurance Practitioner.

## Dependency direction

```text
loop_engine_devtools
        | imports public API from
        v
loop_engine

loop_engine must never import loop_engine_devtools.
```

## Structure

```text
devtools/
├── qualification_lab/     standalone Ollama and black-box qualification lab
├── src/loop_engine_devtools/
│   ├── assurance/          review Loop definitions and operations
│   ├── intelligence/core/  shipped review rules, presets, proof obligations
│   └── cli/                loop-dev command
└── pyproject.toml
```

`qualification_lab` has no Loop Engine import. It can be copied into a separate
repository and used as an independent reference and falsification harness.

## Bootstrap rule

A small deterministic verifier must run without importing Loop Engine.
It checks syntax, forbidden Node classes, forbidden paths, and the
devtools/runtime dependency direction. A broken Loop runtime must
never be able to disable all review.
