# Task types and checks

The sample submission decides the header, the id column and the set of ids. `--task` decides what each prediction value must be. The id column is the first column of the sample unless `--id-column` names another one. Every other column of the sample is a prediction column.

## Task types

| `--task` | Each prediction value must be | Typical metric |
|---|---|---|
| `probability` | a plain number from 0 to 1 | area under the curve, log loss for two classes |
| `class_probabilities` | a plain number from 0 to 1, and the values of one row add up to 1 within `--sum-tolerance` (default 0.001) | log loss over several classes, one column per class |
| `label` | exactly one of the values given with `--labels`, compared as exact text | accuracy or F1 on class names |
| `number` | a plain number, at least `--min` and at most `--max` when they are given | an error metric on a numeric target |
| `text` | any text that is not empty | free text answers |

A plain number is written like `0.25`, `-3` or `1e-4`. A space around the number, a thousands separator, `NaN` and `inf` are not plain numbers.

## Checks

| Check | Fails when |
|---|---|
| `header` | the header differs from the sample header in any name, letter, space or position |
| `field_count` | a row has another number of fields than the header |
| `row_count` | the number of data rows differs from the sample |
| `missing_id` | an id of the sample is not in the submission |
| `extra_id` | an id of the submission is not in the sample |
| `duplicate_id` | one id appears on two rows |
| `row_order` | with `--require-same-order`, the ids are not in the order of the sample |
| `missing_value` | a prediction is empty; for `probability`, `class_probabilities` and `number` also a token such as NA, null, NaN or inf; for `label` such a token when it is not an allowed label |
| `not_a_number` | a value of `probability`, `class_probabilities` or `number` is not a plain number |
| `out_of_range` | a probability is outside 0 to 1, or a number is below `--min` or above `--max` |
| `row_sum` | the probabilities of one row do not add up to 1 |
| `not_allowed_label` | a label is not one of `--labels` |

Ids are compared as exact text, so `17.0` is not `17` and ` 17` is not `17`. A row with the wrong number of fields is counted by `field_count` and its id and values are not read.

## Hints and warnings

`hints` name a likely cause of a failure: a written row index as the first column, a first line that holds data instead of the header, header names in another order or another letter case, or ids that differ from the sample only in number format.

`warnings` do not fail the check. Each one needs a sentence in the report:

- every probability is 0 or 1, so the file may hold labels where the metric expects probabilities;
- every prediction holds the same value;
- every prediction equals the sample value for its id, and sample values are usually placeholders;
- the rows are in another order than the sample, and `--require-same-order` was not given;
- the submission starts with a byte order mark and the sample does not;
- blank lines were skipped;
- a `text` prediction holds a token such as NA or null.
