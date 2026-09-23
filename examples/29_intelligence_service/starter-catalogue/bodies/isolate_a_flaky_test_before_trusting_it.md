# Isolate a test that passes and fails without a code change

Find why a test gives different results on the same code, and repair the cause instead of running the suite again.

## When to use it

Use it as soon as a test fails once and passes on a rerun. A test that is ignored because it is unreliable protects nothing, and it hides real defects behind noise.

## Steps

1. Stop treating the failure as noise. Record the failing output, the machine, the time and the order the tests ran in.
2. Run the single test on its own, many times. Count the failures.
3. If it never fails alone, run it after the suite that preceded it. Shared state between tests is the most common cause.
4. Look for the four usual causes: the current time or date, a random value without a fixed seed, an ordering that the language does not promise, and work that continues in the background after the test returns.
5. Look for shared resources: one database row, one temporary path, one port, one environment variable.
6. Change one suspected cause and measure the failure rate again over the same number of runs.
7. Repair the cause. Fix the test if the test was wrong, fix the code if the code was wrong, and say which it was.
8. Keep the repeated run as a check until the failure rate is zero over a stated number of runs.

## Checks

- The failure rate before the repair and after it are both measured over the same number of runs.
- The cause is named, not guessed.
- The test no longer depends on time, order, a free port or an unseeded random value.
- The suite passes in a different test order.

## Known-wrong example

A team marks a failing test as one to retry automatically three times. It goes green and stays green for a year. The cause was a cache written after the response was returned, so a reader could see stale data. The same cause produced wrong balances for customers, and the automatic retry hid the only signal anyone had.

## What to record

- The measured failure rate before and after.
- The named cause and the evidence for it.
- What was changed: the test, the code or the environment.

## Source

- `src/loop_engine/core/run_validity.py`: this repository decides whether a run may be reasoned about at all, and separates a failure of the infrastructure from a result that can be compared with other results.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
