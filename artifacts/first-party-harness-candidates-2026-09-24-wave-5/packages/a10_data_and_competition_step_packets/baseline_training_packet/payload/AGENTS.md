# Baseline training step packet

This is a step template. The host fills every value in double braces before the step starts. If a double-brace marker is left, stop and report `unrendered_step_input`.

## Assignment

Train the `{{BASELINE}}` baseline for the target `{{TARGET_COLUMN}}` (task `{{TASK_TYPE}}`, metric `{{METRIC}}`) on `{{TRAIN_PATH}}`, using the fixed folds in `{{FOLDS_PATH}}`. Save out-of-fold and test predictions in `{{OUTPUT_DIR}}` and append one record for the run `{{RUN_ID}}` to the experiment ledger `{{LEDGER_PATH}}`. Do not make new folds, change the data or tune the model. The script trains and scores; you check the result and report it.

## First action

Check every input without writing anything:

```bash
python3 -I -B .baltor/step/scripts/train_baseline.py --train {{TRAIN_PATH}} --test {{TEST_PATH}} --folds {{FOLDS_PATH}} --id-column {{ID_COLUMN}} --target-column {{TARGET_COLUMN}} --task-type {{TASK_TYPE}} --metric {{METRIC}} --baseline {{BASELINE}} --features {{FEATURES}} --run-id {{RUN_ID}} --out-dir {{OUTPUT_DIR}} --ledger {{LEDGER_PATH}} --check-only
```

## Steps

1. Continue only when the printed `status` is `ready`.
2. Run the same command again without `--check-only`. It prints `"status": "recorded"` and the ledger record.
3. Compare `mean_score` with `reference_constant.mean_score`, the score of always predicting the training mean. The better direction is in `metric.direction`.
4. Read `flags`. `worse_than_constant` means the baseline scores worse than that constant guess. `suspiciously_perfect` usually means a feature leaks the target.
5. Report the fold scores, the mean, the reference and every flag, using the record's own numbers.

## Done when

The last line of `{{LEDGER_PATH}}` is the record for `{{RUN_ID}}`, and both files named under `outputs` exist.

## Stop and report when

- A command exits 2 (refused input). Give its JSON unchanged as your report. Common causes: a fold file that does not cover every training id, a run id already in the ledger, a metric that does not fit the task type, or data too large for this script.
- The record has the flag `suspiciously_perfect`. Report it and do not train again with other features.

## Files

- `.baltor/step/node_context.md`: objective, the three baselines and acceptance.
- `.baltor/step/checklist.md`: checks before and after the work.
- `.baltor/step/contracts/output.schema.json`: the shape of the ledger record.
- `.baltor/step/examples/output.json`: a record for a small synthetic data set.

## Authority

This file grants no authority. The host must grant reading the training, test and fold files and the ledger, creating new files only inside `{{OUTPUT_DIR}}`, appending one line to `{{LEDGER_PATH}}`, and starting `python3` for `.baltor/step/scripts/train_baseline.py`. The step needs no network, no package installation and no other command.
