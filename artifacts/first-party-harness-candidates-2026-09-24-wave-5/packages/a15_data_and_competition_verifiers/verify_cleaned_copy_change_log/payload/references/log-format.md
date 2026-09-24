# Change log format and checks

The log names every difference between the source table and the cleaned copy. The script reads three forms:

- JSON Lines: one JSON object on each line;
- one JSON array of objects;
- a CSV file with a header row and comma separators.

An empty log file means that nothing changed.

## Entry members

| Member | Used by | Meaning |
|---|---|---|
| `change` | every entry | `cell` (the default when it is missing), `row_removed`, `row_added`, `column_added` or `column_removed` |
| `key` | cell, row_removed, row_added | The row key: its text for one key column, or a list or an object for several key columns. For `cell` and `row_removed` it is the key in the source. For `row_added` it is the key in the cleaned copy. |
| `row` | cell, row_removed | Instead of `key`: the data row number in the source, counted from 1 without the header |
| `column` | cell, column_added, column_removed | The exact column name |
| `before`, `after` | cell | The exact cell text in the source and in the cleaned copy, as JSON strings; `null` means an empty cell |

Other members, such as `rule` or `reason`, are allowed and not checked. A CSV log names the rows of a key with several columns only through `row`.

```json
{"key": "C-0001", "column": "city", "before": "Lyon ", "after": "Lyon", "rule": "trim_spaces"}
{"change": "row_removed", "key": "C-0042", "reason": "repeat of C-0041, reviewed"}
{"change": "column_added", "column": "city_code"}
```

## How rows and cells are compared

- Rows are matched by key. A logged change of a key column moves the match to the new key.
- In the columns that both tables have, every cell is compared as exact text, so a removed space is a change.
- The cells of an added column need no entries.
- Row order and column order may change; `summary` reports whether they did.

## Checks

| Check | Fails when |
|---|---|
| `row_removed_without_log` | a source row is missing from the copy and no `row_removed` entry names it |
| `row_added_without_log` | a row of the copy has no source row and no `row_added` entry |
| `cell_changed_without_log` | a cell differs and no entry names that row and column |
| `column_removed_without_log`, `column_added_without_log` | a column is missing or new and no column entry names it |
| `empty_key_in_cleaned`, `duplicate_key_in_cleaned` | a key of the copy is empty or repeats |
| `log_before_mismatch`, `log_after_mismatch` | an entry's `before` is not the source cell, or its `after` is not the cell of the copy |
| `log_row_not_in_source` | an entry names a key or row number that the source does not have |
| `log_removed_row_still_present` | a `row_removed` entry names a row that is still in the copy |
| `log_added_row_not_new`, `log_added_row_missing` | a `row_added` entry names a row that came from the source, or a row the copy does not have |
| `log_column_claim_wrong` | a column entry names a column that was not removed or added |
| `log_column_not_in_both_tables` | a cell entry names a column that one of the tables lacks |
| `duplicate_log_entry` | two entries name the same cell, row or column |
| `logged_keys_collide` | logged key changes give two source rows the same key |
| `source_digest_differs` | with `--source-sha256`, the source bytes have another digest |

`warnings` counts entries whose `before` equals their `after`, and cell entries on rows that are not in the copy. They do not fail the check.
