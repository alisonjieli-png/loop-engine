# Read a profile and find the dominant cost

Turn a profile into one sentence about where the time or the memory goes, before deciding what to change.

## When to use it

Use it once you know an operation is too slow or too heavy and you need to know which part is responsible.

## Steps

1. Profile the operation as it really runs, with realistic data, not a shortened version.
2. Decide which measure you are reading: time spent inside a function, time including everything it calls, allocations, or bytes held.
3. Sort by total time including calls first. That shows which path matters.
4. Then sort by time inside the function alone. That shows where the work happens.
5. Look for the three usual shapes: one slow call, many calls that are each fast, and work repeated because a result was not kept.
6. Check the call counts. A function taking thirty percent because it is called two million times is a different problem from one called twice.
7. Separate waiting from computing. Waiting for a database or a service does not appear in a processor profile at all.
8. Write one sentence naming the dominant cost and the change you expect to fix it, before editing anything.

## Checks

- The profile was taken on realistic data.
- Both views were read: including calls and inside the function alone.
- Call counts were read, not only durations.
- Waiting time was accounted for separately.

## Known-wrong example

A profile shows a date formatting function at the top of the list. An engineer replaces it with a faster one and gains almost nothing. The function was called four hundred thousand times inside a table render that only needed twelve dates. Reading the call count would have pointed at the caller instead of the callee.

## What to record

- The profile, the data used and the measure read.
- The dominant cost in one sentence.
- The expected effect of the planned change, written before the change.

## Source

- `src/loop_engine/core/operation_cost_records.py`: this repository records what each implementation of an operation cost, phase by phase, so the cheapest implementation that still satisfies the contract can be chosen from observation.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
