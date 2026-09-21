# Choose a smaller model for a bounded decision

Use the cheapest thing that can answer the question, and reserve the expensive model for the work that really needs judgment.

## When to use it

Use it at every step that calls a model, especially a step that runs thousands of times: a classification, a route, a yes or no, a field extraction, a short rewrite.

## Steps

1. Ask first whether the step needs a model at all. A lookup table, a rule or a search answers many questions exactly and for nothing.
2. Write the question as a bounded decision: a choice from a named set, a number in a range, or a short field, with the allowed answers listed.
3. Ask for the answer in a declared shape, and refuse an answer that does not fit rather than guessing what it meant.
4. Try the smallest available model first on a frozen set of cases with known right answers.
5. Compare it with the large model on the same cases and the same shape. Compare accuracy, cost and time together.
6. Route by the decision, not by the topic. Keep the large model for open work where the answer is not from a known set.
7. Where the small model is unsure, escalate that case only, and record how often escalation happens.
8. Repeat the comparison when either model changes, because the answer is about this pair of models on this task.

## Checks

- The step was checked for whether it needs a model at all.
- The allowed answers are listed and an answer outside them is refused.
- The comparison used the same frozen cases and the same answer shape.
- The escalation rate is measured, not assumed.

## Known-wrong example

A team routes every step to the largest model because it is the safest choice. A classification into three categories runs four hundred thousand times a month and costs more than everything else together. The small model, measured, agrees with the large one on ninety eight point four percent of a frozen set, and the disagreements are all one category that a simple rule catches. Nobody measured, so nobody knew.

## What to record

- The frozen cases and the right answer for each.
- Accuracy, cost and time for each model tried.
- The escalation rule and how often it fires.

## Source

- `src/loop_engine/core/typed_decision.py`: this repository has a route for a step that needs one bounded choice rather than prose, returning the selected candidate with a probability for each option and a confidence for the judgment, validated against a declared contract.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 0cf19eb.
