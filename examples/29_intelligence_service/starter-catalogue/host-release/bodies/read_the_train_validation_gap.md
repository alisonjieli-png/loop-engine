# Read the gap between the training score and the cross-validated score

Turn two scores into one named verdict. The reading knows the direction of the metric, scales the gap by the size of the score, and refuses to judge when the honest estimate is missing.

## When to use it

Use it after every model evaluation, before a score is reported or a model is selected.

## Steps

1. State whether the metric is maximized, such as accuracy, or minimized, such as root mean squared error.
2. When the training score or the cross-validated score is missing, or fewer than two folds were used, return `insufficient_evidence`.
3. Compute the gap in the direction of overfitting: training minus cross-validated for a maximized metric, and the reverse for a minimized metric. Divide the gap by the absolute cross-validated score to get the relative gap.
4. Return the first verdict that applies, in this order:
   - `too_perfect_suspect_leakage`: the metric lies between 0 and 1, is maximized, and the cross-validated score is within 0.005 of 1.0;
   - `cv_beats_train_suspect_leakage`: the cross-validated score beats the training score by a relative 5 percent or more;
   - `no_better_than_baseline`: a baseline was given and the cross-validated score does not beat it;
   - `high_variance_cv`: the spread between folds is at least as large as the gap;
   - `overfitting`: the relative gap is 10 percent or more;
   - `healthy`: none of the above applies. Leakage still needs its own check.
5. Return the numbers with the verdict, so a caller can apply its own policy. All thresholds are parameters.

## Checks

- Training 0.99 and cross-validated 0.80 give `overfitting`. Training 0.86 and 0.84 give `healthy`.
- Training 0.80 and cross-validated 0.88 give `cv_beats_train_suspect_leakage`.
- Training 0.85 and cross-validated 0.80 with a fold spread of 0.12 give `high_variance_cv`.
- Training 0.72 and cross-validated 0.70 with a baseline of 0.71 give `no_better_than_baseline`.

## Known-wrong example

An error metric is read with the default direction. Root mean squared error is 8.0 on training data and 12.0 in cross-validation. Read as a maximized metric, the verdict is `cv_beats_train_suspect_leakage`, which sends the team to look for leakage that is not there. Read as a minimized metric, the verdict is `overfitting` with a relative gap of 33 percent, which is correct.

## What to record

- Both scores, the metric, its direction, the fold count and the fold spread.
- The gap, the relative gap, the verdict, its reason and the thresholds that were used.

## Source

- `src/loop_engine/code_nodes/measurement.py`: `read_generalization_gap` and `GapReading`.

Licence: MIT. Compiled from revision f29bddc. The function is plain arithmetic. The module imports one text module of the same package.
