# Repository organization

Loop Engine keeps runtime code, contracts, explanations, examples, measured
runs, and presentation assets in separate directories.

```text
loop-engine/
├── src/loop_engine/     Python package and executable runtime
├── docs/
│   ├── contracts/       Index of implemented contract objects and gaps
│   ├── components/      One guide for each architecture component
│   └── guides/          Task-focused setup and operating instructions
├── examples/            Small runnable examples with one README per example
├── benchmarks/          Frozen benchmark tasks, runners, and evaluators
├── case-studies/        Reports from complete measured Loop Engine runs
└── showcase/            Editable slides, browser player, video, and QA records
```

## Directory ownership

| Directory | Owns |
|---|---|
| `src/loop_engine/` | Runtime classes, typed contracts, adapters, validation, CLI code, and tests shipped with the package. |
| `docs/contracts/` | A short index to canonical contract objects. It does not duplicate their definitions. |
| `docs/components/` | Architecture explanations organized by Loop, Practitioner, Intelligence, Solution Canvas, the three Static Architecture capability groups, and self-improvement as a Practitioner task. |
| `docs/guides/` | Instructions for installing, configuring, running, viewing, and verifying Loop Engine. |
| `examples/` | Useful runnable tasks that teach one boundary at a time. |
| `benchmarks/` | Reproducible task populations, fixed evaluators, run controls, and raw benchmark outputs. |
| `case-studies/` | Plain-language reports that link a complete run to its evaluator, Run History, costs, and limits. |
| `showcase/` | The current architecture presentation and exported video package. |

`/home/username/taedri.dev` is external reference material only. Loop Engine
never imports it, depends on it at runtime, or copies it in bulk. A developer
may inspect one Taedri idea, verify that it fits the Loop ontology, and then
implement a small Loop Engine contract in this repository.

Read [reference sources](context/REFERENCE-SOURCES.md) before consulting an
older folder.

Read the [taxonomy, ontology, and class map](architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
for the exact role profiles, relationship kinds, capability groups, and code
classes used in this repository.
