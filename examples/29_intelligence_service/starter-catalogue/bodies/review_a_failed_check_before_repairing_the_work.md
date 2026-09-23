# Review a failed check before repairing the work

Decide whether the work, the check or the environment is wrong, and never make a check weaker so that it passes.

## When to use it

Use it every time an automated check fails, especially when the failure is inconvenient and a small change to the check would clear it.

## Steps

1. Read the failure text and write down what the check expected and what it saw.
2. Choose one of four explanations: the work is wrong, the check expects something the task never asked for, the check is stricter than the task, or the environment is at fault.
3. Ground the choice in the task wording and the produced thing, quoting both. A feeling that the check is unfair is not grounds.
4. If the work is wrong, repair the work and leave the check alone.
5. If the check is wrong, change it, and then show that the changed check still fails on a known wrong version of the work.
6. If the environment is at fault, repair the environment and run the check again unchanged.
7. Never delete a case, lower a threshold or mark a test to be skipped as a way of passing. Record any such change as a finding with an owner.
8. Record the explanation you chose and the evidence for it, so a repeated failure is not explained differently each time.

## Checks

- The explanation names one of the four and quotes the task and the produced thing.
- A changed check still fails on a known wrong version.
- No case was removed, skipped or loosened to pass.
- The explanation is recorded with the failure.

## Known-wrong example

A test asserts that a report has twelve columns. A change adds a column, the test fails, and a developer updates the number to thirteen. Two months later a different change silently drops a column and the same test is updated again. The test now records whatever the code does. Deciding that the check was right and asking why a column vanished would have found a real defect.

## What to record

- The failure text, the expectation and the observation.
- The chosen explanation with quotations as evidence.
- Any change made to a check, and the known wrong case it still fails on.

## Source

- `src/loop_engine/strings/verification_prompts.py`: this repository keeps the governed texts that instruct a separate review of a failed check, so classifying the failure and confirming a claim that the check is at fault are done deliberately rather than by the producer.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.
