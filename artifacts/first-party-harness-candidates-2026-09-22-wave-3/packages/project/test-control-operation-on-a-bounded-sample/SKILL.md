---
name: test-control-operation-on-a-bounded-sample
description: Separate a stated transaction control's design from evidence that it actually operated on an authorized sample.
---

# Test control operation on a bounded sample

## Use

Use for an internal control review with a supplied control rule and an authorized transaction sample. Produce a read-only design and operation finding, not an audit opinion or legal compliance conclusion.

## Inputs

- Control identity, version, effective period, required actors, timing, and evidence rule.
- Population boundary, sample selection rule, sampled transaction identities, and authorized evidence.
- Known exceptions, overrides, and any permitted treatment of missing records.

## Procedure

1. State what the control requires before seeing the sample result. Separate a design gap in the rule from a failure to follow a workable rule.
2. Check that each sampled transaction belongs to the defined population and period. Preserve excluded and unavailable items with reasons.
3. For each included transaction, compare independent records of the required action, actor, and time with the rule. A policy document alone is not operating evidence.
4. Mark each case `met`, `exception`, or `unresolved`; cite the exact records. Keep an approved override distinct from an undocumented absence.
5. Return the sample selection, case findings, design observations, exception count, unknown count, and limits on any population inference.

## Completion check

Every `met` case has transaction-level evidence for each required condition. A dual-approval policy with no sampled approval records cannot support an effective-operation claim.

## Stop

If the rule, sample authority, population, or required evidence is absent, hold the operating conclusion. Do not alter records, approve transactions, accuse anyone of misconduct, or extrapolate beyond the sample design.
