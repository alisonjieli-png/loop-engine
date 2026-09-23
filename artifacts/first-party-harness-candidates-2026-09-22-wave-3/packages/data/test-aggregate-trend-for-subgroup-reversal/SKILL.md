---
name: test-aggregate-trend-for-subgroup-reversal
description: Challenge an aggregate trend by checking comparable subgroup rates and changing group weights. Use when the total moves opposite to every subgroup.
---

# Test an aggregate trend for subgroup reversal

## When to use

Use for a proposed relationship or trend where the population mix may change. A subgroup reversal can refute the stated aggregate explanation; it does not by itself identify a cause.

## Inputs

- The exact claim, outcome and predictor definitions, compared periods or conditions, and counting unit.
- Outcome numerators and eligible denominators by comparable subgroup, with source identities and missingness counts.
- A supplied reference mix when a fixed-composition comparison is requested.

## Procedure

1. Recompute each aggregate from its subgroup numerators and denominators. Check that groups are mutually exclusive and sufficiently cover the claimed population under a supplied overlap rule.
2. Compare outcome rates within the same defined groups across periods or predictor conditions. Flag group redefinitions, empty cells, and unequal observation windows.
3. Show each group's weight in each aggregate. If the total moves in a direction that every comparable group contradicts, identify a composition reversal rather than repeating the aggregate explanation.
4. Where supplied reference weights are valid, calculate a fixed-mix comparison. Show both actual and fixed-mix results, including sparse cells and uncertainty that may affect interpretation.
5. List plausible confounders or selection changes that the supplied data cannot settle. Keep association and causation separate.

## Completion check

Return the claim, aggregate and subgroup count tables, weight changes, reversal verdict, optional fixed-mix result, and unresolved comparability limits. All displayed rates must be reproducible from shown numerators and denominators.

## Stop conditions

Hold a reversal or causal verdict if subgroup identity, denominators, outcome definitions, overlap handling, or observation windows are incompatible. Do not invent missing groups, weights, or outcomes.
