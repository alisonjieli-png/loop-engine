---
name: reconstruct-causality-across-clock-skewed-records
description: Reconstruct a defensible partial order from clock-skewed logs and traces. Use when a cross-service incident has timestamps that disagree or events that arrive out of order.
---

# Reconstruct causality across clock-skewed records

## Use

Use this when records from several machines appear to disagree about event order. Work only from records the caller has authorized you to inspect. Produce an analysis, not a corrected log or an incident cause claim.

## Inputs

- Records with their source, timestamp, whether the timestamp marks event time or record time, time zone, and any trace, request, message, or parent identifier.
- Known clock-offset and logging-delay bounds or synchronization evidence for each source, when available.
- The event or failure whose predecessors matter.

## Procedure

1. Keep each source record unchanged. Identify duplicate delivery and missing identifiers before ordering anything.
2. Convert each timestamp to a common time basis. Express uncertain clock offset as an interval; do not invent a precise correction.
3. Draw a causal edge only from an explicit producer-consumer relation such as parent and child spans, a message send and its matching receive, or a documented input-output dependency.
4. Use non-overlapping adjusted event-time intervals or a declared monotonic event sequence to establish only that one event occurred before another. A record-time interval establishes only record order unless logging delay is bounded. Treat overlapping or unbounded intervals as unordered. Temporal order alone never creates a causal edge.
5. For each proposed cause, name the path of observed edges to the effect. Name a competing explanation and the missing record that would distinguish them.
6. Return a partial-order table: event, source, time interval, explicit causal predecessors, temporal-before constraints, unresolved relations, and evidence reference.

## Completion check

Every claimed causal predecessor has an explicit observed relation. A non-overlapping time interval may establish temporal order but never causation. Contradictory records and unresolved orderings remain visible. The conclusion says whether the supplied records support a cause, only a sequence, or neither.

## Stop

If clock offset, timestamp meaning, or logging delay cannot be bounded and no causal identifiers exist, report the ambiguity. Do not reorder events by raw record timestamps or treat temporal proximity as proof of cause.
