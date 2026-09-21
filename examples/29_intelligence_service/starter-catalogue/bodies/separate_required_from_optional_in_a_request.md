# Separate what is required from what is preferred

Sort a request into the parts that must hold, the parts that are preferences and the parts that are only assumptions, so a tradeoff can be made without guessing.

## When to use it

Use it whenever a request carries more conditions than can all be satisfied, or whenever an agent must decide between two acceptable results.

## Steps

1. List every condition you can find in the request, including the ones implied by the words used.
2. Sort each into three groups: a hard condition that must hold, a preference that improves the result, and an assumption that nobody has confirmed.
3. For each hard condition, write the observation that shows it holds.
4. For each preference, say which direction is better and roughly how much it is worth against the others.
5. For each assumption, say what would happen if it is false and how cheaply it could be checked.
6. Write the rule for a tie, so a choice between two acceptable results does not need another conversation.
7. Show the three groups to the person who asked. People correct a misplaced hard condition immediately.
8. Keep the groups with the work, so a later reviewer can see which conditions were binding.

## Checks

- Every condition sits in exactly one group.
- Each hard condition has an observation that shows it holds.
- The preferences have a direction and a rough weight.
- The tie rule is written before the work starts.

## Known-wrong example

A request asks for a fast, cheap and complete report. A developer treats completeness as a hard condition, spends the budget on it, and delivers something too slow to use in the meeting it was for. The deadline was the hard condition, and completeness was a preference. Sorting the conditions in ten minutes would have produced a useful partial report on time.

## What to record

- The three groups with their sources in the request.
- The observations for the hard conditions.
- The tie rule and any assumption that was later found false.

## Source

- `src/loop_engine/core/parameter_resolution.py`: this repository resolves a value from several possible sources with a declared order of precedence, and records which source supplied the value and why it was selected.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 381efec.
