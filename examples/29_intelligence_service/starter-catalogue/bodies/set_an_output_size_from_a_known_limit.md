# Set an output size from a known limit

Take the maximum answer size from a source that states it for the exact model, and treat an unknown limit as unknown rather than picking a number.

## When to use it

Use it whenever you call a model with a setting for how long the answer may be, and whenever a long answer is being cut off.

## Steps

1. Find the stated maximum output size for the exact model and the exact interface you are calling. Record where the number came from.
2. If no source states it, record the limit as unknown and refuse to guess. A guess that is too small silently truncates every long answer.
3. Keep three numbers apart: what the model can produce, what you chose to allow for this call, and what the whole task may spend.
4. Choose the allowance for the call from the work, not from the maximum. Ask for what the answer needs.
5. Tie the allowance to the route it was chosen for. A different model or interface needs its own number.
6. Detect a truncated answer and treat it as a failure of the call, not as a short answer.
7. On truncation, either raise the allowance within the known maximum or split the work, and say which you did.
8. Re-check the recorded maximum when the model version changes.

## Checks

- Every allowance traces to a recorded source for that exact model.
- An unknown maximum produces a clear unknown, never a default number.
- A truncated answer is reported as a failure.
- The allowance is bound to the route it was chosen for.

## Known-wrong example

A service sets the answer limit to a round two thousand tokens, because that seemed generous. A model that can produce far more is asked for a long document, and the answer stops in the middle of a sentence. The code treats it as the finished answer, and the document is published incomplete. Reading the stated maximum and detecting truncation would have caught both mistakes.

## What to record

- The stated maximum, its source and the date.
- The allowance chosen for the call and why.
- Every truncation and what was done about it.

## Source

- `src/loop_engine/core/model_capabilities.py`: this repository separates a limit a provider states or has been observed to have from a limit a caller chose, refuses to start generating when the maximum for the selected model is unknown, and reports a mismatch between a chosen allowance and the known maximum.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.
