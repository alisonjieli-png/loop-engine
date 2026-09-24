---
name: "recompute-claimed-cv-score"
description: "Recompute a declared metric from out-of-fold predictions and the fold file, and fail when the claimed mean score differs from the recomputed score beyond a stated tolerance."
license: MIT
compatibility: "Python 3.10 or later, standard library only."
metadata:
  version: "0.1.0"
---

# Recompute a claimed cross-validation score

The script `scripts/recompute_cv_score.py` computes the metric for each fold from the out-of-fold predictions and compares the result with the claim. It reads the files and writes nothing. In each command, `SKILL_DIR` is the folder that holds this file. Run commands from the workspace root. Paths are relative to it.

## When to use it

Use it before a cross-validation score goes into a report, a ranking of experiments or a choice of what to submit. You need the out-of-fold predictions, the fold of each row, the true labels, the metric and the claimed score. The metrics and their exact definitions are in `references/metrics.md`.

## First action

```bash
python3 -I -B SKILL_DIR/scripts/recompute_cv_score.py --predictions oof.csv --folds folds.csv --labels train.csv --metric roc_auc --claimed-score 0.8123
```

## Steps

1. Copy the claimed score exactly as the claim writes it, with all its decimals. Without `--tolerance`, the allowed difference is half a unit of its last decimal. Use `--tolerance` when the task states one.
2. Name the columns that differ from the defaults: `--id-column id`, `--prediction-column prediction`, `--label-column target`, `--fold-column fold`.
3. For `f1`, `roc_auc`, `log_loss` and `--threshold`, check `--positive-label`; the default is `1`.
4. When the claim is one score over all rows, add `--claim-kind pooled`. Add `--claimed-fold FOLD=SCORE` for each fold score the claim lists.
5. Run the command. Read `status`, `claim`, `recomputed`, `coverage` and `hints`, then answer every item in `references/checklist.md`.

## Checks

- Exit code 0 and `status` `pass`: every claim is within its tolerance, and every row has a fold, a prediction and a label.
- `coverage.rows_scored` equals `coverage.rows_expected`.

## Done when

The report quotes `claim.claimed`, `claim.recomputed`, `claim.difference` and `claim.tolerance`, lists the fold scores, and repeats every hint.

## Stop and report when

- Exit code 2: report `reason` and `detail`, for example a fold where the metric has no value because it holds one label value.
- The metric is not in `references/metrics.md`. Do not use a similar metric in its place.
- The task gives no claimed score. A score printed by this script is not a claim.

## Known-wrong example

A notebook prints "CV AUC 0.912", and a step copies it into the report. The out-of-fold file gives a mean fold AUC of 0.872, because the printed number came from the training folds. The script reports `claim_differs` with a difference of 0.040. The file `examples/oof-bundle.json` holds this case. A pass shows only that the claim matches the file; the checklist asks how the predictions were made.
