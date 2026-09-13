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
├── embodiment_lab/        independent experimental placements using canonical Loop
├── src/loop_engine_devtools/
│   ├── assurance/          review Loop definitions and operations
│   ├── intelligence/core/  shipped review rules, presets, proof obligations
│   └── cli/                loop-dev command
└── pyproject.toml
```

`qualification_lab` has no Loop Engine import. It can be copied into a separate
repository and used as an independent reference and falsification harness.

## Harness layering and development instructions

Read [ASTRA.md](../ASTRA.md) for the main comments and suggestions and
[the scoped development instructions](AGENTS.md) before changing experiments.
The local [CLAUDE.md](CLAUDE.md) imports those scoped instructions for Claude
Code; repository rules remain authoritative.

The [layered harness design](../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
explicitly permits an outer Loop around native harness iteration. Compare
wrapper compositions and native control ownership while preserving shared
authority, cancellation, exact outputs, and independent acceptance. More
layers, steps, prompts, and intelligence are possible treatments, not proof
of improvement or permission to enable native features automatically.

## Bootstrap rule

A small deterministic verifier must run without importing Loop Engine.
It checks syntax, forbidden Node classes, forbidden paths, and the
devtools/runtime dependency direction. A broken Loop runtime must
never be able to disable all review.

Repository assurance blocks current architecture, structure, semantic, and
portability violations. The staged three-parameter API migration is reported
as warnings by default because it is not a product-path release gate. Use
`loop-dev --assurance --strict` when working that migration; strict mode makes
every unapproved call-boundary finding blocking.

## Self-orientation and abstraction audit

Repository orientation and hardcoding review are Development Assurance Plane
operations. They run through deterministic Practitioner Loops. Their scanners
remain outside the product package and never run on a normal Loop invocation.

```bash
PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli \
  --orientation \
  --output artifacts/verification/repository_orientation_snapshot.json

PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli \
  --validate-orientation \
  artifacts/verification/repository_orientation_snapshot.json

PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli \
  --hardcoding-audit \
  --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json \
  --fail-on-new high
```

The material audit omits low-risk findings from its output but still counts
every parsed literal candidate. Use `--include-low-risk` for intentional-local
sampling and exact allowlist review. A finding is grouped by text only for
review. Matching text does not prove matching semantics.

The allowlist can also exclude whole files that are not this project's
source: an `excluded_paths` entry names one exact repository-relative file
(no globs, no directories), its owner, a written rationale, a classification
of `UPSTREAM_RECORD_COPY` or `GENERATED_EVIDENCE_RECORD`, a creation date,
and an optional expiry. An excluded file is reported in the audit summary's
`skipped_files` with `excluded_by_allowlist:<classification>`, so the
exclusion stays visible; an expired, glob, or misclassified entry is
reported as an allowlist problem and not applied. Excluding a file removes
only that file's findings and moves no other finding id, so the delta gate
keeps its meaning.

Run planted canaries without writing repository evidence:

```bash
PYTHONPATH=src:devtools/src python3 -m loop_engine_devtools.cli --self-test
```
