---
name: audit-as-of-data-visibility
description: Separate what was known at a past reporting cutoff from what later corrections say about that period. Use for reproducible historical reports.
---

# Audit as-of data visibility

## When to use

Use this when a historical report changes after a correction or late arrival. A question about the past can mean either the view available then or a revised view fixed at another declared cutoff.

## Inputs

- The business period, historical knowledge cutoff, revised-view knowledge cutoff or immutable snapshot identity, and the question's requested interpretation.
- Records with effective time, source-recorded time, reporting-system availability or observation time, identity, and correction linkage, where available.
- The rule or retained snapshot that establishes which record versions were visible in the reporting system by the knowledge cutoff.
- Source rules for supersession and any known gaps in the retained history.

## Procedure

1. State the period being measured, the historical knowledge cutoff, and the revised-view knowledge cutoff or immutable snapshot identity. Name the reporting system whose visibility matters.
2. For a historical known-then view, include only versions demonstrably available to the relevant reporting system by the knowledge cutoff. A source-recorded timestamp alone does not prove that the reporting system had received a version then.
3. For the revised view, include only versions available by its declared knowledge cutoff or in its named immutable snapshot. Apply corrections according to the supplied supersession rule. Keep the earlier version visible in the explanation.
4. Compare the two results by record identity. Attribute each difference to a late record, a correction, or an unresolved history gap.
5. Label every number with its business period and the knowledge cutoff or snapshot that produced it.

## Completion check

Return the known-then and revised-as-of values, the records included in each, and a difference ledger. Both results must be reproducible from their declared knowledge cutoffs or immutable snapshots.

## Stop conditions

Stop if reporting-system visibility cannot be established for either view, the revised-view cutoff or snapshot is missing, or correction lineage is unavailable and required for the result. Do not silently substitute source-recorded time or an unbounded latest view for a historical view.
