# Review note: Recompute a claimed cross-validation score

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a15_data_and_competition_verifiers, model family anthropic. This note is never delivered to a harness.

## Method

One verifier method. The script `scripts/recompute_cv_score.py` joins out-of-fold predictions, the fold of each row and the true labels by row id, computes the declared metric for each fold, and compares the claim with the plain mean of the fold scores (the default), the mean weighted by rows, or one pooled score over all rows. The claim fails when it differs by more than `--tolerance`, or, without it, by more than half a unit of the last decimal the claim was written with. Coverage is part of the verdict: rows without a fold, a prediction or a label, predictions for unknown rows and a fold column that differs between files each fail the check, even when the number matches. Nine metrics are defined in `references/metrics.md`: accuracy, balanced accuracy, F1, area under the curve, log loss, root mean squared error, mean absolute error, the coefficient of determination and root mean squared log error. When a claim fails, `hints` say whether it matches the pooled score, the opposite sign, one minus the area under the curve or the squared error. Exit 0 is pass, 1 is fail, 2 is refused input, including a fold where the metric has no value.

## Authoring basis and sources

Original text and code written for this wave, MIT like the repository. No outside text or code was copied. The package continues an interrupted earlier attempt of the same generator assignment, which wrote the script, the tests and the documents and stopped before its manifest and this note. That attempt is kept byte for byte in `packages/recompute_claimed_cv_score/earlier-attempt-20260924T0102Z.tar.gz`. This run reviewed every line, cross-checked the metrics, added seven tests, extended one, and wrote the manifest and this note.

Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `examples/29_intelligence_service/starter-catalogue/bodies/read_the_train_validation_gap.md` and `src/loop_engine/code_nodes/measurement.py`: the repository reads the gap between a training score and a cross-validated score and takes both numbers as given. This package checks the cross-validated number first.
- `examples/29_intelligence_service/starter-catalogue/bodies/choose_metrics_by_task_type_and_industry.md`: the served method for choosing a metric. This package recomputes the chosen metric and refuses a metric it does not define.
- `examples/29_intelligence_service/starter-catalogue/bodies/check_that_a_result_is_stable_and_generalizes.md`: asks for the spread over folds; the report gives the fold scores, their minimum, maximum and standard deviation.

Metric cross-check, observed on this machine and kept outside the package: on 200 random rows in 5 folds, every metric of the script matched scikit-learn 1.9.0 on Python 3.14.4 to 8 decimals, for the pooled score and for the mean of fold scores. The package itself depends on no third-party library.

## Inputs and outputs

Inputs: `--predictions`, and optionally `--folds` and `--labels`, below `--root` (default the current folder), or `--bundle` with the members `predictions`, `folds` and `labels`; `--metric`; `--claimed-score` copied as written, and optional `--claimed-fold FOLD=VALUE`; column names (`--id-column`, `--prediction-column`, `--label-column`, `--fold-column`); `--positive-label`, `--threshold`, `--claim-kind`, `--tolerance`, `--delimiter` and `--max-bytes` (default 64 MiB, refused above it). Output: one JSON object with `status`, `claim` (claimed, recomputed, difference, tolerance and its source), `recomputed` (mean, weighted mean, pooled, fold minimum, maximum and spread), the score of each fold, `coverage`, `checks`, `failed_checks`, `hints` and the SHA-256 digest of each input.

## Effects

`reads_fs`: the script reads the named files and refuses `..`, paths outside `--root` (also through a symbolic link), non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped example, send other inputs on standard input and write no file.

## Closest existing items

- `read_the_train_validation_gap` (served, prose restating repository code): judges the gap between two given scores. This package recomputes one of them from the predictions.
- `choose_metrics_by_task_type_and_industry` and `freeze_the_success_metric_before_measuring` (served, prose): choose and freeze a metric. No recomputation.
- `reproduce_the_evidence_a_report_claims` (starter candidate, prose): the general practice. This package is one executable case of it.
- Wave 5 neighbours: `rank_experiments_by_fold_scores` (a02) ranks runs from fold scores written in a ledger and takes them as given, and `pick_next_experiment` (a06) chooses the next run. This package checks that a score in the ledger or a report follows from the saved predictions.

## Positive example

`examples/oof-bundle.json` holds 50 out-of-fold rows in 5 folds with the fold and the label inline. With `--metric roc_auc --claimed-score 0.872` the verdict is pass: the fold scores are 0.9167, 1.0, 0.8, 0.8095 and 0.8333, their mean is 0.87190, and the tolerance from the written claim is 0.0005.

## Known-wrong example

The same file with `--claimed-score 0.912`, the kind of number a notebook prints when it scores the training folds, fails `claim_differs` with a difference of 0.0401. The pooled area under the curve is 0.8591, so a claim of 0.859 fails as a mean and gets the hint to use `--claim-kind pooled`. Further known-wrong cases in the tests: a claim with the opposite sign, a squared error reported as root mean squared error, a reversed area under the curve, a fold claim that differs, missing predictions, labels or folds, predictions for unknown rows, and a fold column that differs between files.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/recompute-claimed-cv-score/`, `.agents/skills/recompute-claimed-cv-score/` (Codex), `.opencode/skills/recompute-claimed-cv-score/`, `.pi/skills/recompute-claimed-cv-score/` and `.gemini/skills/recompute-claimed-cv-score/`. Basis: specification section 6 marks the first four skill folders observed on this machine and the Gemini CLI folder documented in `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`. No harness binary was run for this package. Unverified: whether each harness tells the model the folder path it needs for `SKILL_DIR`, and whether a harness asks for permission before `python3` runs from a skill folder. The command starts the first `python3` on `PATH`; a host that runs unattended should bind a trusted interpreter.

## Customer requests

- "The overnight run says cross-validated AUC 0.91. Recompute it from the out-of-fold file before we trust it."
- "Check that the RMSE in the experiment log matches the saved predictions."
- "Is this CV score the mean over folds or one score over all rows?"

## Limits

A pass shows only that the claim follows from the files; it cannot see whether each prediction came from a model that never trained on its row, which the checklist asks. Metrics outside the nine are refused, including variants such as macro F1 and weighted log loss. Ids are joined as exact text. Log loss is for two classes, with probabilities kept between 1e-15 and 1 minus 1e-15. The standard deviation of the fold scores divides by the number of folds. A claim with few decimals is a weak claim, and the report names its tolerance. Checks that failed before they passed: the first mutation pass ran 40 changes of the script against the earlier tests and 8 were not caught (rows without a label, the log loss clip, the absolute value in mean absolute error, F1 against precision, a prediction equal to the threshold, the weights of the weighted mean, the size bound on a named file, and an explicit `--tolerance` on the main claim). Seven tests were added and one was extended, and each of the 40 changes now fails a named test. The suite holds 28 tests and passes under Python 3.14 and 3.10.
