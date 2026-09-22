# Make a write safe to repeat with an idempotency key

Let a caller repeat a request after a timeout without creating a second charge, a second order or a second message.

## When to use it

Use it for any write a caller might send twice: a payment, an order, an email, a transfer, a job submission, or any call behind a network that can time out.

## Steps

1. Have the caller generate a key for the attempt, unique to that attempt, and send it with the request.
2. Store the key with the result of the first completed request, in the same transaction that performs the write.
3. When a request arrives with a key you have already completed, return the stored result rather than doing the work again.
4. Store the important request fields beside the key. If the same key arrives with different content, refuse it instead of returning the old result.
5. Handle the request that is still in progress: hold, or return a clear "in progress" answer, so two copies never do the work at once.
6. Decide how long keys are kept, and tell callers. A key that is forgotten too early brings the duplicate back.
7. Give the operation its own identifier in the result, so the caller can check the state later by that identifier.
8. Test three cases: the same key twice, the same key with different content, and two copies arriving at the same moment.

## Checks

- The key and the result are stored in the same transaction as the write.
- The same key with different content is refused.
- Two requests with one key, arriving together, produce one write.
- The retention period for keys is stated and longer than the caller's retry window.

## Known-wrong example

A payment endpoint checks for a recent identical charge before writing, to avoid duplicates. Two copies of the same request arrive in the same second. Both checks run before either write, both find nothing, and the customer is charged twice. A key stored in the same transaction as the charge, with a uniqueness rule in the database, would have made the second write fail and return the first result.

## What to record

- The key, the stored result and the request fields it was bound to.
- The refusals where the same key carried different content.
- The retention period for keys.

## Source

- `src/loop_engine/catalog/protocol.py`: this repository applies writes as one batch with preconditions and returns an acknowledgement carrying the digest of the batch, so a caller can tell an applied batch from a repeated one.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
