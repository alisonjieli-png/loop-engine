# Review note: Target-encode categories out of fold

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a02_competition_modeling_tools (model family anthropic), with round 2 changes by the Claude Code repairer of the same assignment (same family). This note is never delivered to a harness.

## Method

One method: replace each category with a smoothed mean of the target, computed so that no training row sees its own label. For a training row in fold f the value is (target sum of the category in the other folds + m times the other folds' target mean) divided by (their row count + m). Test rows use all training rows the same way. A category missing from those rows gets their mean; an empty cell is its own category. The fast path subtracts each fold's sums from the whole-file sums. Before anything is written, an independent second count rebuilds the sums from scratch for every fold, skipping that fold, and both paths must agree within a relative 1e-9. After writing, both files are read again and compared with the computed values. At most 100 folds are accepted. With `--check-group-column NAME`, the `group` column of a fold file must match the training column NAME row by row, after removing surrounding spaces.

## Authoring basis and sources

Original text and code from general knowledge of target encoding and additive smoothing. No outside text or code was copied or adapted. The package format follows `src/loop_engine/core/service_runtime/catalogue_packages.py` at revision a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4. The repository executor `src/loop_engine/code_nodes/kaggle_executor.py` fits one-hot encoders on training data and drops high-cardinality text columns, so it has no target encoding. The starter body `audit_data_splits_for_errors_and_leakage.md` names target proxies as a leakage path.

## Inputs and outputs

Input: a training CSV with a numeric target, one or more `--column` names, exactly one of `--fold-column` or `--fold-file` (columns `row` and `fold`; extra columns such as `group` are allowed, so the output of `build_group_stratified_folds` works directly), an optional `--check-group-column`, the smoothing, an optional test CSV and new output paths. Output: one CSV per input file with `row` and one `<column>_te` column per encoded column, values written as exact round-trip decimals, and one JSON report (`out_of_fold_target_encoding_report/v1`; round 2 only added `fold_source.group_column_checked` and two refusal reasons, so the version stays). Exit 0 pass, 1 check failed, 2 refused.

## Effects

`reads_fs` (training, test and fold files), `writes_fs` (one or two new files in exclusive mode; missing parent folders under the root are created), `spawns_process`. No network, no secrets, no model calls. Paths with `..`, absolute paths and symbolic links are refused. Tests write only in temporary folders. The entry commands start the script with `python3 -I -B`: isolated mode ignores user site packages, `usercustomize` and `PYTHON*` environment variables, and no bytecode is written.

## Closest existing items

The scout found no first-party or staged item that computes target encodings. The nearest are the starter question set on split leakage, which builds nothing, and the executor's one-hot encoding. Within wave 5, `build_group_stratified_folds` supplies folds this package can consume; it does not encode.

## Positive example

Six hand-checked rows in two folds with no smoothing give 0.5, 1, 1, 1, 1 and 2/3; the last row's category exists only in its own fold, so it gets the other fold's mean. Test values are 2/3 for a seen category, 0 for a one-row category and 4/6 for an unseen one. With smoothing 2, the first row gives 7/12. A fold file whose `group` column matches the training column `customer` passes `--check-group-column customer` and exits 0.

## Known-wrong example

- A whole-file mean gives a one-row category exactly its own label. `test_known_wrong_full_data_mean_copies_the_label_but_out_of_fold_does_not` flips every label in fold 0 of a 200-row file and shows that the encodings of fold 0 rows do not change, while the whole-file mean of each one-row category in fold 0 equals that row's label.
- A fold file made for the same training rows in another order joins by row number and is accepted without a warning. `test_known_wrong_fold_file_for_other_rows_is_caught_by_the_group_check` shows that silent acceptance, then shows `--check-group-column` refusing the same file with `fold_file_group_mismatch` and writing nothing.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/target-encode-out-of-fold/`, `.agents/skills/` (Codex), `.opencode/skills/`, `.pi/skills/` and `.gemini/skills/`. Basis: observed for Claude Code, Codex, OpenCode and Pi, documented for Gemini CLI (wave specification section 6; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`). Unverified: native loading of this package in any harness; Gemini CLI discovery on this machine; whether each harness shows the model the folder that holds `SKILL.md`, needed to replace `SKILL_DIR`. The entry gives two example folders (`.agents/skills/...` and `.claude/skills/...`). The host must bind a trusted `python3`. The review panel's native loading criterion may hold this package until an integrator probe runs.

## Customer requests

- "Target-encode the city and device columns without leaking the label."
- "I want mean encoding for a high-cardinality ID feature that is safe for cross-validation."
- "Encode categories using my existing folds file and apply the same mapping to test."

## Limits

Numeric targets only; a class label with more than two values needs one 0 or 1 column per class first. At most 50 columns and 100 folds per run. The default smoothing of 20 is a starting value, not a tuned choice. The recount costs one pass per fold. Encodings are as leak-free as the folds are: folds that let a group cross (for example repeated customers split by row) still leak through the group. When the same folds serve the encoding and the model's cross-validation, a validation fold's encodings never use its labels, but the training rows of that model carry encodings that did; the entry states this and names encoding inside each training split as the strict choice. Without `--check-group-column`, a fold file is joined by row number only.

## Pre-check history

Round 1: `fill` and `check` passed on the first run; every run is kept in `review/PRECHECKS.txt` and the dated reports. Mutants run on a copy of the payload: a fast path that includes the row's own fold is caught by the recount check; a mutant where both paths include the own fold, so that the recount agrees, is caught by the label-flip test and the hand-computed values.

## Repair round 2

The independent critic of 2026-09-23 recommended forwarding this package to the panel and listed only non-blocking findings. Three were applied because each was small and testable:

1. No cap on fold values: a mistaken fold column with 300 distinct values was accepted (reproduced before the change). More than 100 folds are now refused with `too_many_folds`, matching `build_group_stratified_folds`.
2. Fold files joined by position only: `--check-group-column` was added, and the known-wrong test above shows what it catches.
3. The second-order effect of sharing folds between encoding and cross-validation is now stated in one line of the entry.

Unchanged: the unverified harness behaviors listed above. On a synthetic file of 300,000 rows with a 100,000-row test file, three columns with a fold file and `--check-group-column` took about 8.4 seconds and 323 MB. Evidence, all under `repair-a02_competition_modeling_tools/round-2-20260924T0501Z/` in the wave folder: `evidence/probe-before-round-2.txt`, `evidence/probe-after-round-2.txt`, `evidence/mutants-round-2.txt` (two mutants of this script, each caught by its named test) and `evidence/scale-probe-round-2.txt`. The first draft of the round 2 entry file had 461 words and was cut to 433 before packaging.
