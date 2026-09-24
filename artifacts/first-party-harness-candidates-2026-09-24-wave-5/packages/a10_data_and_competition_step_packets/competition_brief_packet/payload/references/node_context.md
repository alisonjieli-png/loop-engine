# Competition brief step packet: context

## Objective

Turn the saved competition pages into one structured brief that later steps can trust: every fact is quoted from a page, or it is an open question.

## Relevant context

- Later steps build folds, train a baseline and assemble the submission from this brief. A wrong target or a wrong metric direction wastes every later step.
- The check reads the data file headers. Each target column must be a training column that the test file lacks. The id column must be in the test file and in the sample submission. The sample submission must hold exactly the id column and the prediction columns.
- The check also compares values with the data and the quotes. `target_type` must fit the distinct training values of the target columns; `prediction_value_type` must fit the values of the sample submission; every number of `deadline` must be in its quote; and `yes` for outside data cannot rest on a quote such as "is prohibited". A warning marks wording that may not fit a value.
- The check knows the direction of each listed metric, so a wrong direction fails.

## Current state

The pages and the data files are saved in the workspace. The start command writes a brief in which every fact is null.

## Contracts and input

Allowed values:

- `target_type`: `binary`, `multiclass`, `regression`, `multilabel`, `ranking`, `other`. Use `multilabel` for several 0 or 1 target columns, or for one column that holds several labels.
- `metric`: `rmse`, `mse`, `mae`, `rmsle`, `log_loss`, `mape`, `smape`, `auc`, `accuracy`, `f1`, `macro_f1`, `map_at_k`, `quadratic_weighted_kappa`, `r2`, `other`.
- `metric_direction`: `maximize` or `minimize`. The metric's quote may also serve as its source.
- `prediction_value_type`: `probability`, `class_label`, `real_number`, `integer`, `text`, `other`.
- `external_data_allowed`: `yes`, `no`, `with_conditions`.
- `daily_submission_limit` and `team_size_limit` are whole numbers. `target_columns` and `prediction_columns` are lists of column names.

A quote must contain the column name for a column fact, the file name for a file fact and the number for a count fact. The rendered input values follow `.baltor/step/contracts/input.schema.json`.

## Acceptance

- The check passes.
- No fact carries a guessed value, and every empty fact has one question in `unknowns`.
- No page and no data file was changed.
