# Classify a failure before deciding to retry

Decide what kind of failure you are looking at, because the right answer differs completely between kinds.

## When to use it

Use it whenever a call to another service, a database or a model provider fails, and before you write any automatic retry.

## Steps

1. Put the failure into one of these kinds: the other side is temporarily unavailable, your allowance is used up, your settings or credentials are wrong, your request is wrong, the answer broke the agreed contract, or the cause is unknown.
2. Retry only the first kind, and only when repeating the call is safe.
3. For an exhausted allowance, wait for the stated reset time or stop. Retrying sooner makes it worse for everyone.
4. For wrong settings or a wrong request, do not retry at all. Report it so a person or the caller can change it.
5. For a broken contract, repair the shape once if a deterministic repair exists, and otherwise treat it as a failure. Never invent the missing answer.
6. For an unknown cause, treat it as not safe to retry until it has been classified.
7. Keep these apart in your code and in your reports: another attempt on the same route, another provider, a repair of the format, and giving up.
8. Record the kind with every failure, so the report shows which kinds actually happen.

## Checks

- Every failure is recorded with its kind.
- Only temporary failures are retried automatically.
- A wrong request or wrong credential is never retried in a series.
- A failed call is never replaced by an invented result.

## Known-wrong example

A worker retries every failure five times with a short wait. The credential has expired, so each job makes five refused calls instead of one, the provider treats the traffic as an attack and blocks the address, and the outage spreads to the jobs that would have worked. Classifying the refusal as a settings problem would have stopped after the first call and named the cause.

## What to record

- The kind of each failure and the code that came back.
- What was decided: retry, wait, stop or report.
- The number of attempts actually made and their results.

## Source

- `src/loop_engine/core/provider_failure_classes.py`: this repository sorts provider failures into a closed set of classes, such as an outage, an exhausted allowance, a settings problem or a bad request, and decides whether to wait, wait for the allowance or stop using that route.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 7ed4e85.
