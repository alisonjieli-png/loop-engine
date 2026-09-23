---
name: trace-field-lineage-to-a-measure
description: Trace one reported measure to source fields and transformation versions. Use when a report cell needs an explainable path through filters, joins, derivations, or overrides.
---

# Trace field lineage to a measure

## When to use

Use this for a named output measure and population, not for an entire warehouse at once. A diagram of table names alone does not explain how a value was produced.

## Inputs

- The output measure, report version, grouping grain, filter scope, and selected example cell.
- Source identities and versions, field definitions, transformation definitions, and the run or snapshot that produced the output.
- Any supplied rules for overrides, exclusions, and late corrections.

## Procedure

1. Start at the selected output cell. Record its value, unit, grain, filters, run identity, and source cutoff.
2. Walk backward through each transformation. For every edge, state the input fields, join or filter condition, derived expression, and exact version that was used.
3. Identify each point where rows were removed, multiplied, grouped, or overridden. Record counts or keyed examples that could confirm the effect without inferring it from a diagram.
4. Recompute a small example from the cited source values only when those values and rules are available. Keep an unverified dependency visible if they are not.
5. Separate a path observed in run records from a path inferred from current code. Mark any difference between the two.

## Completion check

Return an ordered source-to-output map with field meanings, versions, transformations, sample contributing records, and unresolved links. The map must explain the selected cell's value or state exactly why it cannot.

## Stop conditions

Stop before claiming verified lineage if a source version, transformation version, join rule, filter, or run identity needed for the path is missing. Do not substitute today's pipeline definition for a past run.
