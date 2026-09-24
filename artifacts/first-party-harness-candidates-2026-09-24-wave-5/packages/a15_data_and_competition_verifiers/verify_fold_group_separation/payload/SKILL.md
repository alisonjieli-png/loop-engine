---
name: "verify-fold-group-separation"
description: "Check a fold assignment file so that every row has exactly one fold, no group appears in two folds and label shares per fold stay within a declared tolerance."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---

# Verify fold assignments keep groups apart

The script `scripts/verify_folds.py` checks a fold file that some other step made. It reads the files and writes nothing. In each command, `SKILL_DIR` is the folder that holds this file. Run commands from the workspace root. Paths are relative to it.

## When to use it

Use it before any cross-validation score is trusted, when several rows can belong to one entity, such as a customer, patient, device or store. It checks any fold file, whoever made it. The accepted layouts and every check are in `references/fold-file-format.md`.

## First action

```bash
python3 -I -B SKILL_DIR/scripts/verify_folds.py --folds folds.csv --train train.csv --id-column id --group-column customer_id --label-column target
```

## Steps

1. Take the group column and the label column from your task. The group column names the entity that must never be in training and validation at the same time.
2. Say how fold rows match training rows: `--id-column` when both files hold an id, `--row-column` when the fold file holds training row numbers counted from 1. When the fold column is inside the training file, give only `--folds` with that file.
3. Add `--label-tolerance` when the task states one; the default is 0.05. For a numeric label, add `--label-bins 10`.
4. Add `--expected-folds` with the number of folds the plan asks for.
5. Run the command. Read `status`, `failed_checks` and `summary`, then answer every item in `references/checklist.md`.

## Checks

- Exit code 0 and `status` `pass`: every training row has exactly one fold, no group has rows in two folds, and every label share is within the tolerance.
- `summary.groups_in_two_folds` is 0 and `summary.max_label_share_gap` is at most `label_tolerance`.

## Done when

The report gives the status, the `sha256` of each file, `summary.rows_per_fold`, `summary.groups_in_two_folds`, the largest label share gap, and each failed check with its count.

## Stop and report when

- Exit code 2: report `reason` and `detail`.
- The task does not say which column identifies the entity. Do not guess it from the column names.
- The folds fail. This step only checks. Do not rebuild or edit the fold file here.

## Known-wrong example

A clinic table holds two visits for each of 12 patients. A plain stratified 3-fold split puts the two visits of patient `P-001` in folds 0 and 1, and does the same to 10 other patients. Every fold has the same label share, so a look at the shares says the folds are fine. The script reports `group_in_two_folds` for 11 patients. The file `examples/known-wrong-bundle.json` holds this case.
