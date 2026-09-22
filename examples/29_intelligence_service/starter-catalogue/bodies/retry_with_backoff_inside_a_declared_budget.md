# Retry with growing waits inside a declared budget

Give a retry a total budget, grow the wait between attempts, and add a random part so that many callers do not return together.

## When to use it

Use it after you have classified a failure as temporary and confirmed that repeating the call is safe.

## Steps

1. Set the total budget first: how long the whole operation may take, including every attempt. Derive the attempt count from that, not the other way round.
2. Start with a short wait and multiply it after each attempt.
3. Add a random amount to each wait. Without it, every caller that failed at the same moment returns at the same moment.
4. Cap the single wait, so the last attempt does not sit for an hour.
5. Honour a wait time the other side sends. It knows more than your formula.
6. Stop early when the failure kind changes to one that is not temporary.
7. Track failures per destination. When a destination keeps failing, stop calling it for a period rather than retrying each request.
8. Report the attempts, the waits and the final result, so a slow success is visible and not silent.

## Checks

- The total budget is declared and observed, and the attempt count follows from it.
- Waits grow, carry a random part and have a maximum.
- A wait time sent by the other side is used instead of the formula.
- A repeatedly failing destination is left alone for a period.

## Known-wrong example

Two thousand workers fail at the same second during a brief outage and all retry after exactly one second, then two, then four. Each wave arrives together and keeps the recovering service down. The outage lasts twenty minutes instead of twenty seconds. A random part added to each wait would have spread the waves out and let the service recover.

## What to record

- The total budget, the waits used and the number of attempts.
- Any wait time supplied by the other side.
- The periods during which a destination was left alone.

## Source

- `src/loop_engine/core/recovery.py`: this repository decides what should happen after a failure from the situation rather than from a fixed table of attempt counts and waits, and records the decision with its reason.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision e2898c7.
