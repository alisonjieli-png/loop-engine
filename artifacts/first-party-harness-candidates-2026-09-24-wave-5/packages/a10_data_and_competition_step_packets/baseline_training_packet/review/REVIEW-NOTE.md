# Review note: baseline training step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a10_data_and_competition_step_packets, model family anthropic, September 23, 2026, against the pinned revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`. This note is never delivered to a customer's harness.

## Method

One focused step: train one simple baseline on a fixed fold file and record it. `train_baseline.py` supports three baselines written with the Python standard library only: `constant` (the training mean), `group_mean` (the target mean of one column, pulled toward the overall mean by a smoothing weight of 10) and `ridge` (closed-form ridge regression on standardized numeric columns with alpha 1; for a 0 or 1 target the score becomes a probability through a two-parameter logistic fit with a fixed slope penalty). For every fold it fits on the other folds, predicts the held-out fold and the test set, and averages the test predictions over folds. It supports the metrics rmse, mae and rmsle for regression and log_loss, auc and accuracy for binary targets; with rmsle the models fit log1p of the target. The constant baseline is always scored as a reference. Two flags mark results a person should look at: `worse_than_constant` and `suspiciously_perfect`. The script writes the out-of-fold and test prediction files and appends one `experiment_record/v1` line with digests of every file and of the script itself. There is no randomness. The model runs a check-only pass, the full run, and reports the record's own numbers.

## Authoring basis and sources

Original text and code written for this wave under the MIT licence. The ridge solver, the logistic fit and the rank-based AUC are standard textbook methods written from general knowledge. The package follows `src/loop_engine/core/service_runtime/catalogue_packages.py`, and `contracts/task.json` holds exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`.

## Inputs and outputs

Input: the rendered values in `contracts/input.schema.json`, whose patterns keep paths, column names, feature lists and run ids safe inside the shell command. The training, test and fold CSV files are read as UTF-8, with a comma delimiter. Output: `RUN_ID.oof.csv` (id, fold, target, prediction), `RUN_ID.test.csv` (id, prediction) and one ledger line following `contracts/output.schema.json`.

## Effects

`reads_fs` for the data files, the fold file and the ledger. `writes_fs` for two new prediction files and one appended ledger line; existing prediction files are refused. `spawns_process` because the model starts `python3` for the script. There is no network use, no package installation, no model call from code and no secret. `contracts/task.json` lists only `reads_fs` and `writes_fs` because the delivered-file vocabulary rule refuses the word in the name `spawns_process`; the host adds that effect.

## Closest existing items

The scout found no existing item for this step. Related wave 5 packages stay distinct: a02 `build_group_stratified_folds` and `build_time_ordered_splits` make the fold file this step consumes, a02 `rank_experiments_by_fold_scores` compares ledger records, a15 `recompute_claimed_cv_score` recomputes a score independently (the out-of-fold file carries the target for that purpose), and a08 `reproducible_competition_notebooks` is a rule for notebooks. This packet trains nothing beyond one baseline and never picks between runs.

## Positive example

On the deterministic 40-row synthetic customer data in the tests, the ridge baseline on two numeric columns scores fold AUCs of 1.0, 0.96, 0.9166666667 and 0.8333333333, a mean of 0.9275 against the constant reference of 0.5, with no flag. The record equals `examples/output.json`.

## Known-wrong example

A feature that copies the target produces a perfect cross-validation score, and a hurried step would report it as progress. The script flags the run `suspiciously_perfect`, and the step stops and reports instead of training again. Other tested refusals: a fold file that misses a training id, a run id already in the ledger, a metric that does not fit the task type, features given to the constant baseline, a test file that holds the target, a text column given to ridge, and a fold with one class under AUC.

In the second pass a probe showed that the first script read the ledger with replacement characters, so a damaged ledger that is not UTF-8 passed the duplicate-run check silently and received a new line. The script now refuses such a ledger and appends nothing. The test `test_ledger_that_is_not_utf8_is_refused` was written first and failed on the old script; it passes now, and restoring the lenient decoding makes it fail again (mutant check in the log). The change moved the script digest recorded in `examples/output.json`, which was regenerated from a real run.

The third pass, on September 24, 2026, found two more gaps with a producer probe of extreme values. A target of `1e200` made the squared error overflow, so the script printed a Python traceback and exited 1 instead of printing one JSON object, which leaves a small model with nothing to act on. A test value of `1e308` made ridge predict infinity, and the old script wrote `inf` into the test prediction file and recorded the run. The script now computes every number, flags included, before it writes any file, turns an arithmetic error into a JSON refusal, and refuses any prediction or score that is not finite, so a failed calculation leaves no partial output that would block a rerun. The test `test_numbers_too_large_to_compute_are_refused_as_json` was written first and failed on the old script. `test_prediction_that_is_not_finite_is_refused` was written together with the repair, so its known-wrong evidence is the mutant run in the log. Removing either guard makes its test fail. The change moved the script digest in `examples/output.json` again; it was regenerated from a real run, and no score or prediction changed.

## Harness placement and verification state

`AGENTS.md` is composed into the step root for Codex, OpenCode and Pi (observed in recorded probes) and Kimi CLI (unverified). `CLAUDE.md` holds `@AGENTS.md` for Claude Code (file observed, import documented). `GEMINI.md` is a byte copy for Gemini CLI (documented). Step files go to `.baltor/step/`, the licence to `.baltor/baseline-training-packet/LICENSE`, and the test file is deliberately not placed. No harness binary was run, so native loading is unobserved. The command starts `python3 -I -B`; the host must bind a trusted interpreter.

A producer-side host walkthrough placed the packet by each of the six placement maps, took the target, id column, metric, task type and file names from a brief made by the wave 5 `competition_brief_packet`, ran the rendered check-only command and then the same command without `--check-only`. The record equalled `examples/output.json`, the ledger's last line was that record, and the wave 5 `submission_assembly_packet` accepted the ledger line and prediction file. It is a script-level probe, not a native harness run and not a model run. The third pass repeated it on the final bytes: the record again equalled the regenerated `examples/output.json`.

## Customer requests

- "Give me a first cross-validated score on our folds so we know what to beat."
- "Train a quick baseline and keep the out-of-fold predictions for later comparison."
- "Log this run in the experiment ledger with its fold scores."

## Limits

- Binary and regression targets only; multiclass, ranking and multi-target tasks are out of scope.
- Ridge work is capped at 60 million units (training rows times the square of features plus one); larger jobs are refused rather than run slowly.
- Features for ridge must be numeric; empty cells and nan are filled with the training-part mean.
- The logistic fit uses training-part scores, so probabilities can still be somewhat overconfident on small data.
- The flag thresholds are fixed heuristics: AUC or accuracy of at least 0.9999, log loss of at most 0.001, or a regression error at most one thousandth of the target spread. A leak that gives a high but not perfect score is not flagged.
- Values whose squares or sums leave the range of a 64-bit float are refused, not rescaled; the reason names the failed calculation.
- Check history: the first pass left one passing report and no failing report. The second pass, on September 23, 2026, logged its runs in `packages/baseline_training_packet/PRECHECKS.txt` beside the assignment folder (the layout check refuses extra entries in the package folder), including the failing known-wrong test, a failed first mutant attempt and its successor. It changed the payload after its last checker run and ended before `fill` and `check` ran again, so its newest report described older bytes. Producer probes of that pass also left `__pycache__` folders in the payload (their times match the walkthrough), which the layout check refuses. The third pass, on September 24, 2026, saved a snapshot of the earlier state beside the assignment folder, removed the generated folders, added the tests and repairs above, and ran `fill`, `check` and `check-all` on the final bytes; its runs are appended to the same log. Each check also saved a `precheck-*.json` report beside this note, and `review/PRECHECKS.txt` keeps the first pass's log.
- The cited sources are unchanged between the pinned revision and `origin/main` at `e8069610` (checked on September 24, 2026).
