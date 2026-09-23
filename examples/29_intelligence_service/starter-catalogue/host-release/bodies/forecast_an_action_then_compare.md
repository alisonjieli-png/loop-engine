# Forecast an action before running it, then compare

Say what an action should produce and what it will cost before it runs. Afterwards compare the outcome with the forecast and keep the difference.

## When to use it

Use it before any action that is slow, costly or hard to undo: a long computation, a migration, a large test run or a series of model calls.

## Steps

1. Before the action runs, state what should be observable when the method works.
2. State what would be observable when it fails, and how that differs from a partial success.
3. Estimate the cost in time, calls, memory and irreversible change. For every number give the unit, the basis, a range and the sensitivity to the assumptions.
4. Mark which parts of the forecast rest on measurement and which rest on assumption.
5. Name the observation during execution that would mean the forecast is already wrong. Stop early when it appears.
6. Record the expected observation before reading the actual result.
7. After the action, compare. Keep four outcomes distinct: the observation matched, it was unexpected but compatible, it was incompatible, or it was unavailable.
8. Ask whether the difference is larger than the noise of the measurement. Ask whether the forecast was wrong about the cost, the outcome or both. Ask what would have had to be known beforehand.
9. Keep the error. Decide how far the next forecast can be trusted.

## Checks

- The forecast carries a time earlier than the start of the action.
- Every estimate has a unit and a range.
- An estimate is never reported as a measurement.
- The comparison exists even when the action succeeded.

## Known-wrong example

A three hour job starts without a forecast. It ends with a score of 0.81 and a bill. Nobody can say whether 0.81 is good, whether three hours is normal, or whether the job should have been stopped after ten minutes. With a forecast of 0.85 to 0.90 in forty minutes, the slow progress in the first ten minutes would already have shown that the forecast was wrong.

## What to record

- The forecast: expected observation, failure observation, cost estimate and early warning sign.
- The observed outcome and cost.
- The difference, its likely cause, and the change to the next forecast.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the forecast and calibrate steps, and the guidance record about forecasting and then comparing.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work functions for estimating and calibrating, and for observing and comparing.

Licence: MIT. Compiled from revision 40fce69.
