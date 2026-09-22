# Compare a smaller model against the larger one honestly

Run a comparison that could actually change your mind, and report what it cost as well as what it scored.

## When to use it

Use it before moving a step to a cheaper model, before moving it to a more expensive one, and whenever a provider releases a version you are tempted by.

## Steps

1. Freeze the case set before you look at any result. Draw the cases from real traffic, including the awkward ones, and keep a part of them unseen until the end.
2. Fix the grader first: an exact comparison where one exists, and a written rule for a human or an independent judge where it does not.
3. Keep everything else the same: the same prompt parts, the same answer shape, the same temperature setting and the same retry behaviour.
4. Run each model on the whole set, and record every failure, refusal and unparseable answer as a result rather than dropping it.
5. Report the score with the number of cases behind it, and the disagreements between the models grouped by kind.
6. Report the cost and the time beside the score. A one percent loss for a tenth of the cost is a decision, not a defeat.
7. Check the unseen part once, at the end, and report it separately.
8. Record the exact model versions and the date. This result is about these versions on this task, and nothing more.

## Checks

- The case set was frozen before any result was seen.
- Failures and unparseable answers are counted, not dropped.
- Cost and time are reported beside the score.
- The unseen part was used once and reported separately.

## Known-wrong example

An engineer tries a cheaper model on twenty cases picked while developing, sees the same answers, and switches. In production the cheaper model fails on long inputs, which were not in those twenty cases, and returns an unparseable answer for four percent of requests. Those are retried against the expensive model, so the bill rises. A frozen set drawn from real traffic would have contained the long inputs.

## What to record

- The frozen cases, the unseen part and the grader.
- The scores, failures and disagreements for each model.
- The cost, time, model versions and date.

## Source

- `src/loop_engine/core/model_demand.py`: this repository builds its preference for which model a step needs from recorded observations of what worked on that kind of step, and marks a route as unproven until there is enough evidence.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
