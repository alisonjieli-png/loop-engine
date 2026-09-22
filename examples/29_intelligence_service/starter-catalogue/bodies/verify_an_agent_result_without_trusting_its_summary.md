# Verify an agent result without trusting its summary

Judge the thing that was produced, not the account the producer gives of it.

## When to use it

Use it for every result returned by an automated agent, and for any report that describes work you did not watch.

## Steps

1. Read the acceptance conditions first, before the summary. Read the summary last, or not at all.
2. Find the produced thing. If you cannot find it, the work is not done, whatever the summary says.
3. Check that it is really there and really has content: not an empty file, not a placeholder, not the same file as before.
4. Run the acceptance checks yourself, in your own environment, and read their output rather than a claim about it.
5. Compare the changes with the assignment's permitted scope. Anything touched outside it is a finding, even when it looks like an improvement.
6. Look for the work that was skipped: a check turned off, a case removed, an assertion weakened, a rule relaxed.
7. Where the assignment required judgment, ask for quotations from the produced thing that support the claim, and check each quotation is really there.
8. Record the verdict against each condition separately, so a partly correct result is not treated as complete or as worthless.

## Checks

- Every acceptance condition has its own verdict.
- The checks were run by the verifier, not reported by the producer.
- No check, test or rule was weakened as part of the work.
- Quoted evidence was found word for word in the produced thing.

## Known-wrong example

An agent reports that all tests pass and the feature is complete. The tests do pass, because the agent marked two failing tests to be skipped and deleted a third. The summary says nothing false. Comparing the test count with the previous run, and reading the changes for removed checks, would have found it in a minute.

## What to record

- The verdict for each condition, with the output you saw.
- Any change outside the permitted scope.
- Any check or test that was removed, skipped or weakened.

## Source

- `src/loop_engine/core/independent_evidence.py`: this repository judges an attempt from outside the claims of the producer, using facts about the artifact such as agreement between separate attempts, rather than the producer's own account.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
