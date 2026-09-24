---
name: "validate-submission-file"
description: "Check a submission against the sample submission for exact header, identifier set, row count, missing values and value ranges for the task type, before any upload step."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---

# Validate a submission file against the sample

The script `scripts/validate_submission.py` compares a submission with the sample submission of the competition and checks every prediction value for the task type. It reads the two files, writes nothing and uploads nothing. In each command, `SKILL_DIR` is the folder that holds this file. Run commands from the workspace root. Paths are relative to it.

## When to use it

Use it after a submission file is written and before any upload step. The sample submission decides the header, the id column and the ids. The rules of the competition decide the task type. The task types and every check are in `references/task-types.md`.

## First action

```bash
python3 -I -B SKILL_DIR/scripts/validate_submission.py --submission submission.csv --sample data/sample_submission.csv --task probability
```

## Steps

1. Choose `--task` from the rules: `probability` for one probability column, `class_probabilities` for one probability column per class, `label` for class names, `number` for a numeric target, `text` for free text.
2. For `label`, add `--labels` with every allowed value. For `number`, add `--min` and `--max` when the rules give a range.
3. When the id is not the first column of the sample, add `--id-column`. When the rules ask for the sample row order, add `--require-same-order`.
4. Run the command. Read `status`, `failed_checks`, `hints` and `warnings`.
5. For each failed check, quote up to three items of `violations`.
6. Answer every item in `references/checklist.md`.

## Checks

- Exit code 0 and `status` `pass`: the header equals the sample header, every sample id appears once, no other id appears, and every value is valid for the task type.
- Exit code 1 and `status` `fail`: the counts in `checks` are complete, even when `violations` lists only examples.
- Every warning has one sentence in your report.

## Done when

The report gives the status, the `sha256` of the submission, each failed check with its count, every hint and warning, and the checklist answers.

## Stop and report when

- Exit code 2: report `reason` and `detail`.
- The rules do not say what each prediction value must be. Do not guess the task type from the sample values; they are often placeholders.
- The check fails. Do not upload the file. This step only checks; a fix is a separate step.

## Known-wrong example

A notebook writes the predictions together with the row index of its table and reads the ids as numbers. The file starts with an unnamed index column, and id `1001` became `1001.0`. The row count and every probability look right. The script reports `header`, all 12 ids under `missing_id` and `extra_id`, and one hint for each cause. Run it with `--bundle examples/known-wrong-bundle.json --task probability` to see it.
