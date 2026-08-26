# Loop Engine Devtools

The Development Assurance Plane: a first-class Loop Engine application
that reviews the repository against its own rules.

## Identity

- Devtools is NOT a second Node engine or second runtime.
- Every supervisor, specialist, scanner, and reviewer is an ordinary
  LoopNode running on the canonical Loop kernel.
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
├── src/loop_engine_devtools/
│   ├── assurance/          review LoopNode definitions and operations
│   ├── intelligence/core/  shipped review rules, presets, proof obligations
│   └── cli/                loop-dev command
└── pyproject.toml
```

## Bootstrap rule

A small deterministic verifier must run without importing Loop Engine.
It checks syntax, forbidden Node classes, forbidden paths, and the
devtools/runtime dependency direction. A broken LoopNode runtime must
never be able to disable all review.
