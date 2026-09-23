# Review a change for correctness

Read a proposed change against the requirement it claims to satisfy, and decide whether it is right, not whether it looks tidy.

## When to use it

Use it for every change before it is merged, including a change written by an agent. Do it before any style comment, because style comments crowd out correctness comments.

## Steps

1. Read the request or ticket first, then the change. Write one sentence saying what the change is supposed to do.
2. Read the new tests before the new code. Ask what wrong behaviour each test would catch.
3. Walk the happy path with one concrete input and predict the output by hand.
4. Walk the same path with an empty value, a very large value and a value at each boundary.
5. Check every branch that was added or altered, and ask which input reaches it.
6. Check the values that cross a boundary: arguments, return values, database columns, message fields. Are units, time zones and currencies stated?
7. Look for behaviour the change removes by accident: a default, an early return, a validation that no longer runs.
8. Write findings as a question plus the input that would show the problem, so the author can reproduce it.

## Checks

- The reviewer stated the intended behaviour in their own words before reading the code.
- Each new branch has a named input that reaches it.
- Each finding names a concrete failing input, not a feeling.
- Tests were read and judged, not counted.

## Known-wrong example

A reviewer approves a change because the suite is green and the code is clean. The change swapped two arguments of a function whose parameters are both strings, so the city and the country are stored the other way round. No test passed both, because every fixture used the same value for each. Predicting one concrete output by hand would have shown it immediately.

## What to record

- The one sentence statement of intent.
- Each finding with the input that demonstrates it.
- What the reviewer did not check, so the gap is visible.

## Source

- `src/loop_engine/strings/decision_schemas.py`: this repository shapes a review request so that the reviewer must answer specific questions, such as what is missing and why this is the right moment, rather than returning a free opinion.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 9cec9d7.
