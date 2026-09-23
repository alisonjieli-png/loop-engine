# Turn a vague request into a testable statement

Take a sentence like "make the dashboard better" and turn it into something you can be wrong about.

## When to use it

Use it at the start of any task whose request does not say what would count as finished, and before spending effort on a guess.

## Steps

1. Keep the original wording. Every later statement sits beside it, never replaces it.
2. Name the person who will use the result and the decision or action it should support.
3. Ask what they would do differently if the work were finished. The answer usually contains the real requirement.
4. Write two or three materially different readings of the request, and say what each one would produce.
5. Find the cheapest observation that separates the readings, such as one question, one example or one small sample of data.
6. Write the chosen reading as a statement with a subject, a measurable property and a value or a rule.
7. Add what is out of scope, so the boundary is written rather than assumed.
8. Show the statement to the person who asked, beside the original wording, and repair it until they agree.

## Checks

- The original wording is preserved next to the statement.
- At least two readings were written before one was chosen.
- The chosen statement can be shown to be unsatisfied by a named observation.
- The person who asked has agreed to the wording.

## Known-wrong example

A request says the search should be more relevant. A team spends a month changing the ranking. The person who asked actually meant that searching for a product code returns nothing, which was a missing field in the index and a day of work. One question about what they would do differently would have found it.

## What to record

- The original wording, unchanged.
- The readings considered and the observation that separated them.
- The agreed statement and what is out of scope.

## Source

- `src/loop_engine/core/development_planning.py`: this repository keeps planning records passive and typed, holding the open clarification items and the verification contract for each requirement beside the plan itself.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 390643e.
