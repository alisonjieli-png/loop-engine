---
description: "Record one finished competition experiment with its fold scores, seed, data version and code revision. The script computes the mean and spread."
---

# Experiment note

## Purpose

Record one finished experiment so later sessions can compare runs and the
pre-submission gate can link a submission file to it. The script checks the
note against the competition brief and computes the cross-validation mean and
standard deviation itself. Never type a mean or a spread yourself.

## First action

Find the per-fold scores in your experiment's own output: one score per fold,
in fold order. If you cannot find them, go to "Stop and report when".

## Steps

1. Collect the fields: a new lower case `experiment_id`, `hypothesis`,
   `change`, `metric`, `fold_scores`, `seed`, `data_version` and
   `code_revision` (the output of `git rev-parse --short HEAD`).
2. If the experiment wrote a submission file, add `submission_file` with its
   path relative to the workspace root. Add `outcome_note` if useful.
3. With your shell tool, from the workspace root, send the note on standard
   input:

```bash
python3 -I -B .baltor/plugins/competition-plugin/scripts/experiment_note.py <<'NOTE'
{"experiment_id": "exp-005", "hypothesis": "ONE SENTENCE", "change": "ONE SENTENCE", "metric": "METRIC", "fold_scores": [0.0, 0.0], "seed": 0, "data_version": "VERSION", "code_revision": "REVISION"}
NOTE
```

4. Exit 1: read `failures`. Fix only your own typing mistakes and send once
   more.
5. Exit 0: the note is stored.

## Output

One line: experiment id, `cv_mean`, `cv_std`, `fold_count` and `notes_total`
exactly as the script printed them, plus `submission_sha256` when present.

## Stop and report when

- `metric_differs_from_brief` or `data_version_differs_from_brief`: the
  experiment did not follow the brief. Report it; do not change the metric
  name to pass.
- `fold_count_differs_from_brief`: a fold is missing or extra.
- `experiment_id_already_recorded`: pick a new id. Never overwrite a note.
- Exit 2, or the brief is missing.
