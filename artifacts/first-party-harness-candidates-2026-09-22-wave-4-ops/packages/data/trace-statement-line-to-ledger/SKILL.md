---
name: trace-statement-line-to-ledger
description: Trace one financial-statement line through a supplied mapping to ledger balances and adjustments. Use when a reported total lacks explainable lineage.
---

# Trace a statement line to the ledger

## When to use

Use for one entity, statement line and reporting period. This method tests traceability and arithmetic; it does not express an audit opinion or certify the statement.

## Inputs

- Statement version and line definition, period, entity scope, currency and sign convention.
- Versioned account-to-line mapping, trial balance or ledger extracts, consolidation entries, permitted adjustments and source references.
- Supplied materiality, rounding and foreign-currency rules, if any; do not invent them.

## Procedure

1. Identify every included account and entity under the mapping effective for the statement version. Mark mapping gaps, overlapping assignments and excluded accounts.
2. Recompute the line from account balances with the correct debit or credit sign and period cutoff. Record source extract digests or other stable identities where available.
3. Apply each named adjustment once, distinguishing posted, consolidation-only and proposed entries. Keep reversals and elimination pairs visible.
4. Reconcile the computed amount to the displayed line, showing rounding and conversion separately. A zero difference is not enough if a source balance is missing or assigned twice.
5. State whether the line is traced, mismatched or indeterminate and which ledger evidence would resolve the gap.

## Completion check

Return a line-to-account bridge, source identities, adjustments, excluded or duplicate mappings, recomputed amount and difference. Preserve the statement and mapping versions.

## Known-wrong case and stop

Two accounts each map to a revenue line, but one is included twice through a consolidation map. Matching the displayed total after an offsetting manual adjustment does not prove lineage. Hold a traced claim when mapping, ledger scope, cutoff or adjustment support is absent. Do not edit the statement or ledger.
