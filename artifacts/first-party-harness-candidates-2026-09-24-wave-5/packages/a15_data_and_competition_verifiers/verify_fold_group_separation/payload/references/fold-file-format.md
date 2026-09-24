# Fold file layouts and checks

A fold file is a CSV file with a header row and a fold value for each training row. Fold values are compared as exact text, so `1` and `1.0` are two different folds.

## Three layouts

| Layout | Options | Group and label are read from |
|---|---|---|
| The fold column is in the training file | `--folds train.csv` | that file |
| A fold file with an id column | `--folds folds.csv --train train.csv --id-column id` | the training file, or the fold file when only it has the column |
| A fold file with training row numbers | `--folds folds.csv --train train.csv --row-column row` | as above; `row` counts training data rows from 1 without the header |

Without `--train`, only the fold file is checked: `--id-column` finds repeated ids, `--row-column` finds missing row numbers, and the group and label columns must be in the fold file.

When both files hold the group or the label column, the training file is used, and a different value in the fold file is reported as `group_copy_differs` or `label_copy_differs`.

## Checks

| Check | Fails when |
|---|---|
| `row_without_fold` | a training row has no fold record, or its fold value is empty |
| `row_in_two_folds` | one row has records in two different folds |
| `row_listed_twice` | one row has two records in the same fold |
| `unknown_row` | a fold record names no training row |
| `row_without_group` | the group value of a row is empty |
| `group_in_two_folds` | one group has rows in more than one fold |
| `group_copy_differs`, `label_copy_differs` | the fold file's copy of the group or the label differs from the training file |
| `label_share_gap` | a label's share in a fold differs from its share in all rows by more than the tolerance |
| `fold_count` | the number of folds differs from `--expected-folds` |

## Label shares

Shares count the rows that have a label. `summary.rows_without_label` counts the others. With `--label-bins N`, a numeric label is cut into N bins that hold about the same number of rows over the whole file, and the bins are compared instead of single values. A label with more than 50 values is refused without `--label-bins`.

A group split is judged on the named column only. Two columns that describe one entity, such as a customer number and an email address, need two runs.
