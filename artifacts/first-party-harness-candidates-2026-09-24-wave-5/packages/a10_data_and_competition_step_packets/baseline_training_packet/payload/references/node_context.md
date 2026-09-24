# Baseline training step packet: context

## Objective

Record one honest baseline score for the competition, computed on the fixed folds, with out-of-fold and test predictions that later steps can reuse.

## Relevant context

- The fold file fixes which rows are held out. Every experiment uses the same folds so that scores stay comparable; new folds made here would break that.
- The three baselines:
  - `constant` predicts the training mean. For a 0 or 1 target, that is the share of 1.
  - `group_mean` predicts the target mean of each value of one column, pulled toward the overall mean for rare values.
  - `ridge` is ridge regression on numeric columns. For a 0 or 1 target, its score becomes a probability through a penalized logistic fit on the training rows.
- With the metric `rmsle`, the models are fitted on log1p of the target. Test predictions are the mean of the fold models.
- The constant baseline is always scored as well, as the floor to beat.

## Current state

The training file, the test file and the fold file exist. The run id is new. The ledger may already hold other runs; this step only appends one line.

## Contracts and input

- The rendered input values follow `.baltor/step/contracts/input.schema.json`. `features` is `none` for `constant`, one column for `group_mean`, and one or more numeric columns for `ridge`.
- The fold file has exactly two columns: the id column and `fold`, a whole number.
- The record follows `.baltor/step/contracts/output.schema.json`.

## Acceptance

- The record's digests name the exact training, test, fold and prediction files.
- The report quotes the fold scores, the mean, the reference and the flags as the record gives them.
- No data file and no earlier ledger line changed.
