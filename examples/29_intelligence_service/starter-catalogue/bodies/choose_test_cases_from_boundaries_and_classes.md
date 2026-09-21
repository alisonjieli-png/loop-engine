# Choose test cases from boundaries and equivalence classes

Pick a small set of test inputs that covers the behaviour, instead of many inputs that all exercise the same path.

## When to use it

Use it when you have a function, an endpoint or a form field with a range, a format or a set of allowed values, and you have to decide which inputs to test.

## Steps

1. Write down every rule the input must satisfy: type, range, length, format, allowed set, required or optional.
2. Split the input space into groups where every member should behave the same way. One valid group, and one group for each way the input can be wrong.
3. Take one ordinary value from each group.
4. For each numeric or length rule, take the value just below the limit, the limit itself and the value just above it.
5. Add the empty value, the missing value and the largest value the interface promises to accept.
6. Add one value that is valid in shape but wrong in meaning, such as an end date before its start date.
7. Write the expected result for each case before running anything.
8. Run them, and add a case for every behaviour you discover that none of the cases covered.

## Checks

- Every rule in step one has at least one case that breaks it.
- Every numeric or length limit has a case below, at and above it.
- Each case has a written expected result that came from the rules, not from the output.
- Two cases from the same group were merged rather than both kept.

## Known-wrong example

A team tests an age field with the values 20, 25, 30, 35 and 40. All pass. The field rejects anything under 18 and over 120, but nobody tested 17, 18, 120 or 121, and the code used a greater than sign where it needed greater than or equal. An 18 year old is refused in production. Three boundary cases would have found it in a second.

## What to record

- The rules you derived the groups from.
- The groups, the chosen value for each and the expected result.
- Any behaviour found during the run that no group predicted.

## Source

- `src/loop_engine/core/evaluation_suite.py`: this repository grades work against a frozen set of cases with registered graders and an exact denominator, so that two reports can be compared.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision eb757bc.
