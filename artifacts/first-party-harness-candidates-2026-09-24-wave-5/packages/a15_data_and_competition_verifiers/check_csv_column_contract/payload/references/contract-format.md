# Column contract format

A contract is one JSON object with `"record_type": "column_contract/v1"`. The script refuses a key it does not know, so a misspelled rule is reported instead of skipped.

## Top-level keys

| Key | Default | Meaning |
|---|---|---|
| `columns` | required | A list of column rules, described below. |
| `empty_values` | `[""]` | Cell texts that count as empty, for example `["", "NA"]`. |
| `extra_columns` | `"allowed"` | `"not_allowed"` makes every header column that the contract does not list a violation. |
| `column_order` | `"any"` | `"as_listed"` requires the listed columns to appear in the contract's order. |
| `row_count` | none | `{"min": 1, "max": 100000}`; either bound may be left out. |
| `unique_together` | `[]` | Lists of 2 to 10 column names whose combined values may not repeat. A row with an empty part is skipped. |
| `description` | none | Free text for people. |

## Column keys

| Key | Applies to | Meaning |
|---|---|---|
| `name` | all | Exact header text, compared with letter case and spaces. |
| `type` | all | `string`, `integer`, `decimal`, `boolean`, `date` or `datetime`. |
| `required` | all | Default `true`. A missing optional column is listed in `contract_columns_not_checked`. |
| `empty` | all | `"allowed"` (default) or `"never"`. |
| `max_empty_share` | all | Largest share of empty cells, from 0 to 1. |
| `allowed` | all but boolean | A list of exact texts. Other values are violations. |
| `min`, `max` | integer, decimal, date, datetime | Inclusive bounds. Dates are written in the column format. |
| `min_length`, `max_length` | string | Bounds on the number of characters. |
| `unique` | all | No value may repeat. Typed columns compare values, so `7` and `007` repeat in an integer column. |
| `trimmed` | string | `true` makes a value with spaces at the start or end a violation. |
| `format` | date, datetime | A strptime format. Defaults: `%Y-%m-%d` and `%Y-%m-%dT%H:%M:%S`. A value must be written exactly as the format writes it, so `2024-7-30` fails `%Y-%m-%d`. |
| `true_values`, `false_values` | boolean | Defaults `["true"]` and `["false"]`. |

## Types

- `integer`: optional sign and digits only. No spaces, separators or decimal point.
- `decimal`: digits with an optional point and exponent, such as `12.5` or `1e3`. `1,200.50` is not a decimal; convert it in a cleaning step first.
- Empty cells skip every rule except `empty` and `max_empty_share`.

## Output fields

- `checks` maps each check that the contract uses to its violation count. Zero means the check passed.
- `violations` lists up to three examples for each column and rule, and at most `--max-examples` in total.
- `row` counts data rows from 1 without the header. `line` is the file line where the record starts.
- `--no-values` replaces each value with its length, for data that must not reach a report.
