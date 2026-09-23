# Write a regression test that pins a defect

Turn a reported bug into a small test that fails today, passes after the repair, and keeps failing if anyone removes the repair later.

## When to use it

Use it for every defect you fix, however small. Use it before you write the fix, not after. If you cannot reproduce the defect in a test, you do not yet know what the defect is.

## Steps

1. Write down the report word for word: the input, the environment and the wrong result.
2. Reproduce the wrong result by hand once, so you know the report is true.
3. Write the smallest automated test that shows the wrong result. Use the real interface a caller uses, not an internal helper.
4. Run the test against the unrepaired code and save the exact failure text.
5. Make the repair.
6. Run the same test again. It must pass without any change to its expectations.
7. Remove the repair for one run, or return the old value from the repaired function, and confirm that the test fails again.
8. Put the repair back, run the full suite, and keep the new test beside the tests of the code it covers.

## Checks

- The test failed before the repair and the failure text is saved.
- The test passes after the repair with unchanged expectations.
- With the repair removed, the test fails again.
- The test names the reported defect in its name or its first comment.

## Known-wrong example

A developer fixes a rounding defect and then writes a test that asserts the new, correct total. The test passes on the first run. Nobody ever saw it fail, so nothing shows that it can detect the defect. Six months later the rounding code is rewritten, the defect returns, and the test still passes because it was written against the repaired behaviour by copying the observed output. A test that was seen to fail first would have caught it.

## What to record

- The original report and the exact failing output before the repair.
- The test name and where it lives.
- The result of removing the repair once, which proves the test can fail.

## Source

- `src/loop_engine/core/independent_failure_review.py`: this repository builds a known wrong version of a subject, with the produced files emptied, and requires the check to fail on it before the check is treated as sound.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 565e133.
