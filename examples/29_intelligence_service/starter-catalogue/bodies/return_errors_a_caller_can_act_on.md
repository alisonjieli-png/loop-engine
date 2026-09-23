# Return errors a caller can act on

Make a failure carry a stable code, a message for a developer and a clear statement of what to do next.

## When to use it

Use it for every interface that other code calls, and for every command line tool whose output another program reads.

## Steps

1. Decide, for each failure, who can fix it: the caller, the operator, or nobody right now.
2. Give each failure a stable code that never changes its meaning. Callers branch on the code, never on the message text.
3. Say in the message what was wrong, using the caller's own words: which field, which value, which limit.
4. Add a remedy sentence for the codes an operator can act on, such as which setting to change or which permission to grant.
5. Say whether repeating the same call could succeed. A caller cannot decide to retry without that.
6. Keep secrets, internal paths and stack details out of the message the caller sees, and keep them in your own log with an identifier the caller can quote.
7. Separate one failure per call from many: for a batch, return the list of failures with the item each belongs to.
8. Group the codes so a caller can handle a whole group it does not know in detail.

## Checks

- Every failure has a stable code and a message that names the field or limit.
- The message contains no secret, no internal path and no stack text.
- Each failure says whether repeating could succeed.
- A caller can handle an unknown code by its group.

## Known-wrong example

A service returns the same general failure with the text "request failed" for a missing field, an expired key and a database outage. The caller can only give up or retry forever. Retrying the missing field wastes the service's capacity and never succeeds, and the expired key is never renewed because nobody knows that is the cause. Three codes with three remedies would have made each case obvious.

## What to record

- The code list with meanings, remedies and whether repeating may succeed.
- The identifier that ties a caller's report to your own log entry.
- Any code whose meaning changed, and when.

## Source

- `src/loop_engine/core/model_token_preflight.py`: this repository pairs each refusal code with a stable message and a separate sentence saying what an operator can do about it, and keeps provider and prompt text out of the refusal.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision d893bba.
