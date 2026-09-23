---
name: reconstruct-service-clock-from-status-intervals
description: Reconstruct elapsed and chargeable service time from start, pause, resume, and completion records. Use when a support or operations service clock disagrees with wall time.
---

# Reconstruct a service clock from status intervals

## When to use

Use this for one case and one supplied service-time policy. Wall time, working time, and policy-counted time can differ.

## Inputs

- Case identity and ordered status events with event identities, authoritative timestamps, and cutoff.
- The versioned policy defining start, pause, resume, completion, calendar, and treatment of missing or corrected events.
- Named time zone and calendar version if the policy counts only working intervals.

## Procedure

1. Confirm event identity, authoritative order, and cutoff. Keep superseded or repeated events visible until the supplied rule resolves them.
2. Build non-overlapping status intervals from consecutive events. Mark gaps, impossible transitions, and an open interval at the cutoff.
3. Intersect each interval with the supplied working calendar when required. Classify it as counted, paused, excluded, or unresolved under the policy version.
4. Add counted durations without counting overlaps twice. Report wall duration and policy-counted duration separately.
5. Compare the reconstructed value with any displayed timer and explain each difference by interval or unresolved event.

## Completion check

Return the event sequence, policy and calendar versions, classified intervals, counted duration, wall duration, and difference ledger. Each counted unit of time must be traceable to one interval.

## Stop conditions

Stop a compliance or threshold verdict if policy, event order, time zone, calendar, or treatment of an open or corrected interval is missing. Do not invent a pause rule or change a case status.
