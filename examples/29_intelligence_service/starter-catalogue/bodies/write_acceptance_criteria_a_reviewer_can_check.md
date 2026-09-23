# Write acceptance criteria a reviewer can check

Write the conditions for "done" so that two people reading them reach the same verdict without asking the author.

## When to use it

Use it before work starts on any task given to another person, another team or an agent, and before you agree to deliver anything.

## Steps

1. Write each criterion as a statement that is true or false about the delivered thing, not about the effort.
2. Name the observation that decides it: which command, which screen, which file, which query, and what the result must be.
3. Give the exact input for each criterion, and the exact expected output or the rule the output must satisfy.
4. Say who judges it and whether the judge may be the producer. For anything that matters, the answer is no.
5. Include the negative conditions: what must not happen, what must not change, what must still work afterwards.
6. Include the non functional conditions that are real requirements: response time at a stated size, a permission that must not widen, a limit that must hold.
7. For a criterion that needs judgment, write the rule the judge applies and ask for quotations from the delivered thing as evidence.
8. Have someone who did not write them read them and say what they would check. Repair every difference.

## Checks

- Every criterion can be answered true or false from a named observation.
- Every criterion has an input and an expected result or rule.
- A second reader reaches the same verdict without asking questions.
- The judge is named and is not the producer where it matters.

## Known-wrong example

A task says the import must be fast and handle errors gracefully. The work is delivered, the author declares it done, and the reviewer disagrees about both. Two weeks of argument follow. Stating that a file of one hundred thousand rows imports in under two minutes on the test machine, and that a malformed row is written to a rejects file while the rest continue, would have settled it before the work started.

## What to record

- The criteria with their inputs, observations and expected results.
- The named judge for each.
- The differences found when a second reader tested the wording.

## Source

- `src/loop_engine/core/independent_judgment.py`: this repository lets a separate judge decide one written criterion about a deliverable, and requires the judgment to quote the deliverable itself rather than assert a verdict.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.
