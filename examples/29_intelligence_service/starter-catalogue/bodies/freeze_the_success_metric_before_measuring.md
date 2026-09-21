# Freeze the success metric, threshold and population before measuring

Decide what success means before any number exists. A score is evidence only when the metric, its direction, the threshold and the population were fixed first.

## When to use it

Use it at the start of any task that ends in a measured claim: a model score, a speed improvement, an error rate or a cost saving.

## Steps

1. Write down the acceptance metric, its direction, the threshold and the population. Do this before the first measurement.
2. Name the simplest approach that could work and measure it as the baseline. Compare against a naive or majority baseline and against the method in use today. Beating nothing is not evidence.
3. Decide on the cross-validated or holdout number. The training number is optimistic and is never the decision number.
4. Never compute the deciding number on the observations that shaped the method. A number from the data that produced the method is not evidence about other data.
5. Count how many candidates were tried. The best of many candidates, compared with a baseline that ran once, overstates skill. Correct for the breadth of the selection, and report outcomes that include the failures.
6. Treat a score that is nearly perfect as suspicious before it is impressive. Check for leakage, for a proxy of the target, for answers that were visible, and for duplicated rows.
7. When the scores differ a lot between folds, report the interval. Do not trust the mean alone.

## Checks

- The metric, direction, threshold and population carry a date earlier than the first result.
- The report shows the baseline, the number of candidates that were tried and the failed candidates.
- The deciding number comes from data that did not shape the method.

## Known-wrong example

A team tries forty configurations, reports the best cross-validated score and compares it with a baseline that ran once with default settings. The threshold is chosen after seeing the results. The gain can be selection noise. The honest comparison fixes the threshold first, gives the baseline the same tuning effort, and confirms the final pick on a holdout set that no candidate has seen.

## What to record

- The frozen definition of success, with its date.
- The baseline results, the number of candidates and every excluded or failed attempt.
- The data that was used for selection and the data that was used for the final number.

## Source

- `src/loop_engine/code_nodes/measurement.py`: the task success and generalization gap statements in `measurement_pack`.
- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the guidance records about stating the baseline first and about a metric computed on the data that shaped the method.

Licence: MIT. Compiled from revision 0cf19eb.
