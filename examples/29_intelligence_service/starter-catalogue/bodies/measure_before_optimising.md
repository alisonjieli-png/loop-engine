# Measure before optimising

Find out where the time actually goes before changing any code for speed, because the guess is usually wrong.

## When to use it

Use it before every performance change, and whenever someone says that a part of the system is slow without a number.

## Steps

1. State the goal as a number: which operation, at which size, measured how, and what value would be good enough.
2. Measure the current value on realistic data. A measurement on a small test set answers a different question.
3. Break the time down by phase: waiting for the database, waiting for another service, computing, serialising, waiting for a lock.
4. Find the phase that holds most of the time. Work only there, and ignore the rest until it becomes the largest.
5. Estimate the best possible gain from removing that phase entirely. If the whole phase is five percent, the change cannot help much.
6. Make one change. Measure again with the same method and the same data.
7. Keep the measurement, both values and the change together, so the gain is evidence rather than a claim.
8. Stop when the goal is reached. Further work has a cost and no stated benefit.

## Checks

- A number existed before the first change.
- The measurement uses realistic sizes and the same method both times.
- The change was made in the phase that held most of the time.
- The gain is reported with the measurement that shows it.

## Known-wrong example

A team rewrites a sorting routine in a faster style and reports a large improvement in a small test. In production the page is no faster, because ninety two percent of its time is one database query that returns the whole table. A breakdown by phase would have pointed at the query on the first day.

## What to record

- The goal number and the measurement method.
- The phase breakdown before and after.
- The change made and the measured difference.

## Source

- `src/loop_engine/core/operation_cost_capture.py`: this repository times the declared phases of an operation with a steady clock while the real work runs, and keeps as unknown anything it did not observe.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 565e133.
