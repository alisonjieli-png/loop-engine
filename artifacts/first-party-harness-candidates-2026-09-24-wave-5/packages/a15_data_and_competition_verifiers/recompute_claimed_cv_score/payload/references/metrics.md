# Metrics, claims and checks

Each fold score uses the rows of that fold that have a prediction and a label. The claim is compared with one of three results, chosen with `--claim-kind`:

- `mean`, the default: the plain mean of the fold scores;
- `weighted_mean`: the mean of the fold scores weighted by their rows;
- `pooled`: the metric computed once over all rows.

## Metrics

| Metric | The prediction column holds | Definition |
|---|---|---|
| `accuracy` | a label, or a probability with `--threshold` | the share of rows where the prediction equals the label |
| `balanced_accuracy` | as for accuracy | the mean, over the label values present in the fold, of the share of rows with that label predicted correctly |
| `f1` | as for accuracy | 2 TP / (2 TP + FP + FN) for the positive label |
| `roc_auc` | a score; a higher score means the positive label | the chance that a positive row scores above a negative row, where a tie counts one half |
| `log_loss` | the probability of the positive label | the mean of minus the natural logarithm of the probability given to the true label; probabilities are kept between 1e-15 and 1 minus 1e-15 |
| `rmse` | a number | the square root of the mean squared difference |
| `mae` | a number | the mean absolute difference |
| `r2` | a number | 1 minus the sum of squared differences divided by the sum of squared distances of the labels from their fold mean |
| `rmsle` | a number of 0 or more | rmse computed on log(1 + value) |

## Values

- A label and a prediction that both read as numbers are compared as numbers, so `1` equals `1.0`.
- `--positive-label` names the positive label; the default is `1`. With `--threshold T`, a prediction of T or more means the positive label.
- `f1`, `roc_auc`, `log_loss` and `--threshold` need exactly two label values.
- A fold where the metric has no value, such as `roc_auc` for a fold with one label value, is refused, because no mean of the fold scores exists.

## Tolerance

Without `--tolerance`, a claim written as 0.8123 allows a difference of 0.00005, half a unit of its last decimal. A claim written as 0.81 allows 0.005. A claim with few decimals is therefore a weak claim, so the report names the tolerance and where it came from.

## Checks

| Check | Fails when |
|---|---|
| `claim_differs` | `--claimed-score` differs from the recomputed result by more than the tolerance |
| `fold_claims_differ` | a `--claimed-fold` score differs from its fold score |
| `rows_without_fold` | an expected row has no fold |
| `rows_without_prediction` | an expected row has no prediction |
| `rows_without_label` | an expected row has no label |
| `predictions_for_unknown_rows` | the predictions hold ids that are not expected rows |
| `fold_column_differs` | the predictions file holds a fold column whose value differs from the fold file |

The expected rows come from the fold file when `--folds` is given, else from the label file, else from the predictions file.

## Hints

When a claim fails, `hints` say what it matches instead, if anything: the pooled score instead of the mean, the opposite sign, 1 minus the AUC, or the squared error instead of rmse.
