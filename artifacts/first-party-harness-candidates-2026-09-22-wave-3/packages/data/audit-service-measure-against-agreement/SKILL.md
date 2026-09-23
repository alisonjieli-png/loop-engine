---
name: audit-service-measure-against-agreement
description: Reconcile a reported service measure with the supplied target and counting rules. Use when an attainment claim may exclude failed or unresolved events.
---

# Audit a service measure against its agreement

## When to use

Use this for one service measure, agreement version, and reporting period. Treat the agreement as supplied task data, not as permission to interpret or change contractual obligations.

## Inputs

- The measure definition, target, effective agreement version, period, eligible population, and rules for exclusions and unresolved events.
- Event or case records with stable identities, relevant timestamps, outcome evidence, and any stated correction history.
- The published result and its numerator, denominator, and exclusions, if available.

## Procedure

1. Fix the counting unit and agreement version applicable to each event. Partition the supplied population into eligible, excluded under a named rule, and unresolved; do not drop missing outcomes silently.
2. Classify each eligible identity against the supplied success rule. Keep failed, late, missing, corrected, and disputed observations separately until the rule resolves them.
3. Recompute the numerator and denominator at the declared grain and period. Show every difference from the published counts by identity and reason.
4. Compare the recomputed measure with the target only when the agreement says how unresolved outcomes count. State whether the evidence supports, contradicts, or cannot decide the attainment claim.

## Completion check

Return the agreement version, period, population, counting rule, keyed disposition ledger, numerator, denominator, calculated result, target comparison, and unresolved identities. Each excluded identity needs a supplied exclusion rule.

## Stop conditions

Hold an attainment verdict when the agreement version, counting unit, eligible population, outcome rule, or treatment of missing events is absent. Do not amend an agreement, change source records, contact a carrier or customer, or certify a legal obligation.
