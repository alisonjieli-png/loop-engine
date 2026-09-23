---
name: validate-aggregate-grain
description: Check whether a measure can be summed across the requested grouping dimensions. Use when totals may double count entities or stock snapshots.
---

# Validate aggregate grain

## When to use

Use this before rolling detailed data into a summary. A correct join and row count do not prove that the measure is additive across every dimension.

## Inputs

- The source row meaning and key, target grouping dimensions, and requested measure.
- The measure's definition: flow, stock at a point in time, distinct entity count, or ratio.
- Any deduplication or allocation rule supplied by the data owner.

## Procedure

1. Write the grain of one source row and one result row in plain words. State the dimensions being removed by aggregation.
2. Classify how the measure behaves across each removed dimension. Sum a flow only over dimensions for which the records are disjoint and the measure is additive.
3. For a stock snapshot, choose the requested instant or a declared summary rule. For a distinct count, count identities at the target grain. For a ratio, recompute from compatible components.
4. Check a small group manually for repeated entities and repeated snapshots. Reconcile each output group to the source records it used.
5. Mark any group that needs an allocation rule or unresolved overlap.

## Completion check

Return source grain, target grain, measure classification, aggregation rule, a worked sample group, and unresolved overlaps. The reported total must be reproducible from the declared contributing records.

## Stop conditions

Stop if row meaning, entity identity, or allocation rule is missing where required. Do not add stock levels across dates or average ratios without their underlying weights.
