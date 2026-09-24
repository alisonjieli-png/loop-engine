---
name: "verify-cleaned-copy-change-log"
description: "Compare a source table, its cleaned copy and the change log by row key, and fail when a row appears or disappears or a cell changed without a matching log entry."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---

# Verify a cleaned copy against its change log

The script `scripts/verify_change_log.py` compares every row and cell of the source table with the cleaned copy, and checks each difference against the change log. It reads the three files and writes nothing. In each command, `SKILL_DIR` is the folder that holds this file. Run commands from the workspace root. Paths are relative to it.

## When to use it

Use it after a cleaning step and before anyone uses the cleaned copy, whenever that step says its log lists every change. You need the source table, the cleaned copy, the log and the key columns that identify a row. The log format and every check are in `references/log-format.md`.

## First action

```bash
python3 -I -B SKILL_DIR/scripts/verify_change_log.py --source data/raw/customers.csv --cleaned data/clean/customers.csv --log data/clean/changes.jsonl --key customer_id
```

## Steps

1. Take the three paths and the key columns from your task. Give one `--key` for each key column.
2. If the task gives the digest of the source recorded before cleaning, add `--source-sha256` with it.
3. Run the command. Read `status`, `failed_checks` and `summary`.
4. For each failed check, quote up to three items of `violations` with their `rule`, `key`, `column` and values.
5. Answer every item in `references/checklist.md`.

## Checks

- Exit code 0 and `status` `pass`: every changed cell, removed row and added row has a matching entry, and every entry matches both tables.
- Exit code 1 and `status` `fail`: the counts in `checks` are complete, even when `violations` lists only examples.
- `summary.rows_matched` plus `summary.rows_removed` equals `source.rows`.

## Done when

The report gives the status, the three `sha256` values, `summary`, each failed check with its count, and the checklist answers.

## Stop and report when

- Exit code 2: report `reason` and `detail`. A source key that is empty or repeats is refused, because rows cannot be matched.
- The task names no key column or no log.
- The copy or the log seems wrong. This step only checks. Do not edit the tables or the log to make the check pass.

## Known-wrong example

A step logs three spelling and spacing fixes. It also drops the repeated row `C-0042` and turns `N/A` in `phone` into an empty cell for `C-0007`, and logs neither. The log looks complete. The script reports `row_removed_without_log` for `C-0042` and `cell_changed_without_log` for `phone` of `C-0007`. Run `examples/known-wrong-bundle.json` with `--bundle` and `--key customer_id` to see it.
