# Carry earlier decisions forward without the whole transcript

Replace a long history with a short record of what was decided, while keeping the full text where it can still be fetched.

## When to use it

Use it in any task that runs over many steps, where the history grows until it crowds out the material the current step needs.

## Steps

1. Store the full output of each step by its digest, and keep the reference. Never let the only copy be the text inside a window.
2. After each step, write a short record: what was decided, on what evidence, what is still open, and the reference to the full text.
3. Carry those records forward instead of the raw history. Carry the original request unchanged beside them.
4. Keep failures and refused options in the record. A history that only holds successes causes the same wrong path to be tried again.
5. Decide a threshold: material above a certain size is kept only by reference, and material below it may also stay inline.
6. Let a step fetch the full text by reference when it needs it, with a check on size before it is loaded.
7. Do not summarise the original request or the acceptance rules. Those stay word for word.
8. Check that a step given only the short records can still reach the same decision.

## Checks

- Every summary carries a reference to the full text it came from.
- The original request and the acceptance rules are never summarised.
- Refused options and failures appear in the carried record.
- A step working only from the records reaches the same decision in a test.

## Known-wrong example

A long task keeps only the last ten exchanges. The rule that the customer refused a subscription was stated at the start, and is now outside the window. The next step proposes a subscription again, and the work is wasted twice. A short carried record naming that refusal, with a reference to where it was stated, would have cost twenty words.

## What to record

- The reference and digest of each stored output.
- The short record for each step: decision, evidence, open questions.
- The threshold above which material is kept only by reference.

## Source

- `src/loop_engine/core/context_artifacts.py`: this repository stores a large value first, returns a stable reference addressed by its digest, and keeps a smaller representation inline only while it is under declared limits.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
