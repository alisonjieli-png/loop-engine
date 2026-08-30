# Seed space Context Intelligence

This example gives a self-improvement task to a Practitioner Loop. It prepares candidate Context
Intelligence for space projects. It covers job roles, project types, task
types, and multiple thinking styles.

## Why use a loop

Domain seeding has several bounded stages: define scope, map work, prepare
research questions, generate reusable context, classify it, remove duplicates,
verify the candidate shape, and stage the result for review.

The seed does not claim to know the important people, organizations, standards,
or current facts in space. It prepares questions for a separate source-aware
research loop.

## Run settings

| Setting | Value |
|---|---|
| Loop role | Practitioner, with the self-improvement task profile |
| Run mode | Deterministic |
| Step profile | `context_intelligence_seed` |
| Intelligence layer | Candidate Context Intelligence |
| Runtime Memory | Not used |
| Run History | Event log kept in memory for this example |

## Install

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

## Run it

```bash
python examples/11_seed_space_context/run.py
```

## Expected result

The output lists:

- 240 deterministic candidate Context records;
- coverage across five space-related job roles;
- thinking styles such as first principles, analogy, gap analysis, and
  adversarial review;
- a stable candidate manifest; and
- six questions that a source-aware research loop should answer.

All records remain candidates. Normal intelligence retrieval excludes them
unless a caller explicitly requests candidate review.

## What this example does not prove

It does not perform web research, identify authoritative people or
organizations, validate domain facts, install a Context Pack, or promote any
candidate.
