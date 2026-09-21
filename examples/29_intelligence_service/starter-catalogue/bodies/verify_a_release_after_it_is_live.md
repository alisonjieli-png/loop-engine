# Verify a release after it is live

Prove that the new version is doing the right thing for real users, rather than that it started without crashing.

## When to use it

Use it immediately after every deployment, and again after the first full traffic period such as a business day.

## Steps

1. Check that the running version is the one you released, by asking the service which revision it is.
2. Do the real thing once. Place a test order, run a real query, send a message through the whole path, and look at the result.
3. Check the path the change touched, not only a health endpoint. A health endpoint that answers says almost nothing.
4. Compare the counts that should not have changed: requests, errors, writes per minute, items produced. A silent drop to a lower number is the common failure.
5. Watch the queue depths and the delay of anything that follows the database. These break later than the request path.
6. Look at the failures that are being handled quietly. An increase in retries is a release problem even while the totals look normal.
7. Write down the values you observed with the times, not the word fine.
8. Keep watching for a stated period, and only then treat the release as finished.

## Checks

- The running revision matches the released revision.
- One real end to end action was performed and its result inspected.
- The counts that should be unchanged were compared with the previous period.
- Observations are written with values and times.

## Known-wrong example

A deployment finishes, the health endpoint answers, and the team closes the release. The change broke the writing of one field, so orders are accepted and saved without a delivery address. Nothing fails, and the error count does not move. The first complaint arrives three days later. Placing one real order and reading the stored row would have shown it in a minute.

## What to record

- The revision confirmed and the end to end action performed.
- The counts compared and the values observed with times.
- The period watched before the release was treated as finished.

## Source

- `src/loop_engine/core/artifact_constraints.py`: this repository checks what a produced artifact means rather than only that it exists and parses, because a file that is well formed and empty passed the older check.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 381efec.
