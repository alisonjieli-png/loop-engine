---
name: "check-csv-column-contract"
description: "Validate a CSV file against a JSON column contract of required columns, types, allowed values, ranges, uniqueness and empty-cell rules, and report violations by row and column."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---

# Check a CSV against a column contract

The script `scripts/check_column_contract.py` does every check. It reads the two files and writes nothing. In each command, `SKILL_DIR` is the folder that holds this file. Run commands from the workspace root. Paths are relative to it.

## When to use it

Use it when a table must follow written column rules: after a cleaning step, before a hand-off, or when the task says the output must follow a contract. The script applies only the rules in the contract. The format is in `references/contract-format.md`, and `examples/column-contract.json` is a complete contract.

## First action

```bash
python3 -I -B SKILL_DIR/scripts/check_column_contract.py --csv data/clean/customers.csv --contract contracts/customers.json
```

## Steps

1. If the task names no contract file, stop and report. Do not write a contract from the table you are checking.
2. Run the first action with the task's paths. For a tab or semicolon file, add `--delimiter tab` or `--delimiter semicolon`.
3. Read `status`, `failed_checks` and `violations_by_column`.
4. For each failed check, quote one or two items of `violations` with their `row`, `column`, `rule` and `value`.
5. Answer every item in `references/checklist.md`.

## Checks

- Exit code 0 and `status` `pass`: every contract rule held on every row.
- Exit code 1 and `status` `fail`: the counts in `checks` are complete, even when `violations` lists only examples.
- `contract_columns_not_checked` is empty. A name listed there did not appear once in the header, so its rules did not run.

## Done when

The report gives the status, the CSV path and its `sha256`, each failed check with its counts per column, and the checklist answers.

## Stop and report when

- Exit code 2: report `reason` and `detail`. An unknown contract key or type is refused on purpose, so a typing error cannot switch a rule off.
- The contract and the task disagree about a column.
- The table seems to need fixing. This step only checks. It never edits the table or the contract.

## Known-wrong example

A model looks at a few rows of a cleaned customer table, sees two-letter country codes and reports that the file follows the contract. The table still holds `Germany` in `country`, and customer `C-0002` appears twice after a merge. The script reads every row and reports both with their row, line and column. Run it with `--bundle examples/known-wrong-bundle.json` to see these two and five more violations.
