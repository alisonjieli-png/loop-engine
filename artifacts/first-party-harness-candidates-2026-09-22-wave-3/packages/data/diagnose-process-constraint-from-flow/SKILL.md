---
name: diagnose-process-constraint-from-flow
description: Locate a candidate flow constraint from arrivals, completions, and queues. Use when a slow-looking stage is called the bottleneck without throughput evidence.
---

# Diagnose a process constraint from flow

## When to use

Use for a repeating process over a stable, declared observation window. This is a diagnosis from observed flow, not a schedule feasibility check or a guarantee that changing one stage will improve the whole process.

## Inputs

- Ordered stages, routing and rework rules, counting unit, time window, and queue boundaries.
- Time-stamped arrivals, completions, starting and ending work in process, and known corrections or censored cases.
- Supplied stage capacity and availability observations when a capacity explanation is requested.

## Procedure

1. Put arrivals, completions, and work in process on the same identity, unit, stage, and time basis. Separate new work from retries and rework.
2. Reconcile each queue: opening count plus arrivals minus completions and supplied adjustments equals closing count. Show gaps instead of forcing the balance.
3. Compare queue change and throughput across adjacent stages over comparable intervals. Mark stages with sustained accumulation or starvation and check whether upstream releases or downstream blocking could explain them.
4. Compare the candidate stage with its supplied capacity, downtime, variability, and routing evidence. Treat long service time alone as insufficient to name a system constraint.
5. Return a candidate constraint, competing explanations, and the smallest additional observation that would distinguish them.

## Completion check

Return per-stage flow balances, comparable intervals, candidate location, supporting and contradicting observations, unresolved records, and a confidence limit. Every bottleneck claim must identify a growing queue or constrained throughput path under the supplied routing rule.

## Stop conditions

Hold a single-cause verdict if queue boundaries, routing, identity, observation window, or relevant arrivals and completions are missing. Do not change staffing, priorities, capacity, or live work routing.
