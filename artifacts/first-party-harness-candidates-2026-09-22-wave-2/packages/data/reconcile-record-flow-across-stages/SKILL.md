---
name: reconcile-record-flow-across-stages
description: Reconcile logical records through an ingest, validation, and publication flow. Use when a batch total looks complete but records may be rejected, duplicated, or missing between stages.
---

# Reconcile record flow across stages

## When to use

Use this to explain where a bounded set of logical records went during one pipeline run. A stage's attempt count is not its count of distinct records.

## Inputs

- The run identity, source population, stage sequence, and cutoff used for the comparison.
- Record identities and stage observations, including retries, rejection reasons, and any declared fan-out or collapse rule.
- The expected transition rule for each stage, including whether rejected records may later re-enter.

## Procedure

1. State the counting unit and population at each stage. Keep attempts, distinct logical records, and output artifacts in separate columns.
2. For each transition, partition incoming identities into accepted, explicitly rejected, still pending, and unexplained. Apply a supplied fan-out or collapse rule before comparing different units.
3. Match accepted identities to the next stage. Flag missing, unexpected, repeated, and cross-run identities. Do not count a retry as a new source record.
4. Reconcile each edge with its declared accounting equation. Carry unresolved identities forward as exceptions rather than making totals balance by assumption.
5. Give the first stage at which each unexplained identity diverges, with the observations that support it.

## Completion check

Return the run and cutoff, per-stage counts by counting unit, per-edge reconciliation, keyed exceptions, and unresolved categories. Every source identity must have a supported disposition at each reached stage.

## Stop conditions

Stop a completeness claim if record identity, run scope, stage semantics, or the rule for fan-out, collapse, or retries is missing. Do not repair data or rerun a pipeline from this skill.
