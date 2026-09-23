---
name: compare-distribution-paths-with-failure-costs
description: Compare candidate distribution paths using supplied cost, time and disruption evidence. Use when a cheapest quoted route may fail the delivery requirement.
---

# Compare distribution paths with failure costs

## When to use

Use for one shipment class and decision horizon with two or more feasible path designs. A path is the sequence of handoffs, not merely a carrier quote.

## Inputs

- Origin, destination, shipment constraints, promised arrival window and supplied evaluation weights or hard thresholds.
- For each path: handoffs, capacity, transport and handling charges, transit-time evidence, historical disruption observations, insurance or recovery terms, and data dates.
- Supplied rule for valuing lateness, damage, returns and recovery effort; unknown values stay unknown.

## Procedure

1. Draw each full path and name the party and evidence for each handoff. Exclude a path that violates a hard physical, regulatory, capacity or service constraint without inventing a waiver.
2. Normalize quoted charges to the same shipment quantity, currency and time basis. Identify charges omitted by one quote, including transfer and return legs.
3. Compute a range of total burden for each feasible path: known direct charges plus scenario-based late, damage and recovery consequences under the supplied valuation rule. Keep scenario assumptions visible.
4. Compare arrival evidence against the promise using the same start and end events. Report uncertainty and sample size rather than treating a single prior shipment as a reliable rate.
5. Identify a conditional choice or the missing observation that could reverse it. Do not present an unsupported point estimate as a measured failure cost.

## Completion check

Return path diagrams, eligibility reasons, cost and timing bases, burden ranges, unresolved terms, and a decision conditional on the supplied thresholds. Keep disqualified paths in the record.

## Known-wrong case and stop

A route with a lower line-haul quote but an unpriced transfer and a missed hard delivery window is not automatically cheaper or eligible. Stop a final selection when required handoffs, service evidence, valuation rules or authority to choose are missing. Do not book transport or alter a contract.
