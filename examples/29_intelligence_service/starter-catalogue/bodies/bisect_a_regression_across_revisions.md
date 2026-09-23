# Find the revision that introduced a regression by halving

Use a repeatable test and a halving search over the revision list to name the exact change that broke something.

## When to use it

Use it when something worked before and does not work now, you have the history, and reading the changes has not found the cause. It is fastest when the test is quick and reliable.

## Steps

1. Write a test that returns a clear pass or fail for the broken behaviour, with no human judgment.
2. Find one revision where the test passes and one where it fails. Confirm both by running the test.
3. Take the revision halfway between them and run the test there.
4. Keep the half that still contains the change from pass to fail.
5. Repeat until two neighbouring revisions differ.
6. Read the change between those two revisions and explain how it produces the failure.
7. If a revision cannot be built or tested, mark it as unusable and take its neighbour rather than guessing its result.
8. Confirm the cause by reversing that one change on the current revision and running the test again.

## Checks

- The good revision and the bad revision were both confirmed by running the test, not assumed.
- The test gives the same result when run twice on the same revision.
- The named change explains the failure, and reversing it repairs the behaviour.
- Unusable revisions were recorded as unusable, not counted as passing.

## Known-wrong example

An engineer assumes the last release is good because nobody complained, and halves between it and today. The search names an unrelated formatting change. The defect had been present for three releases and was only noticed when traffic grew. Running the test on the assumed good revision first would have shown that it already failed, and the search would have started further back.

## What to record

- The test, the first good revision and the first bad revision.
- The revisions tried and the result at each one.
- The named change and the result of reversing it.

## Source

- `src/loop_engine/core/run_validity.py`: this repository records when a run cannot answer the question being asked, so an unusable result is excluded instead of being counted as evidence.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9a483df.
