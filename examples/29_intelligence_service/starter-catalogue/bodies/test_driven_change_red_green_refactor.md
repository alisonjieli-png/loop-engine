# Make a test driven change: red, green, refactor

Implement one bounded software requirement by first proving that it is not satisfied, then making the smallest change, then refactoring while the test passes, and finally running the full verification.

## When to use it

Use it only for a slice of software work that has four things: an exact contract for verifying the requirement, a confined workspace, a permitted write scope and an available way to run the tests.

## Steps

1. Preserve the original requirement and the current baseline.
2. Run or add the smallest test that proves that the requirement is not satisfied.
3. Record the exact failing signature.
4. Make the minimum implementation change inside the write scope of the assignment.
5. Run the focused test and require that it passes.
6. Refactor only while the focused test stays green.
7. Run the required interaction suites and the full verification suites.
8. Return the changed artifacts, the test outputs, the limits and the exact evidence.

Do not commit, push, publish, widen permissions or change unrelated files. Do not report completion from the text of a test alone. The requested artifact must exist, and independent verification must pass when the task contract requires it.

## Checks

- The new test failed before the change, and the failing signature is on record.
- The same test passes after the change.
- The change stays inside the permitted write scope. Unrelated files are untouched.
- The full suites ran after the refactoring, and their output is attached.

## Known-wrong example

An agent writes the implementation first and then writes a test that passes. The test was never seen to fail, so nothing shows that it can detect the missing behaviour. It passes even when the new code is removed. A test that was red first and green afterwards proves both that the test works and that the change works.

## What to record

- The requirement, word for word, and the baseline revision.
- The failing signature before the change and the passing output after it.
- The list of changed files and the outputs of the full suites.
- The limits: what was not tested, and why.

## Source

- `src/loop_engine/skills/software-tdd-red-green-refactor/SKILL.md`: the packaged skill with the eight steps and the closing restrictions.

Licence: MIT. Compiled from revision e2898c7.
