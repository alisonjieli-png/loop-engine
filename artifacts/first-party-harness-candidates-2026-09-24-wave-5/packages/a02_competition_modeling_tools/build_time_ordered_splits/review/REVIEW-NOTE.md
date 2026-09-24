# Review note: Build time-ordered validation splits

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a02_competition_modeling_tools (model family anthropic), repaired in round 2 by the Claude Code repairer of the same assignment (same family). This note is never delivered to a harness.

## Method

One method: cut the distinct times of the training file into N + 1 blocks of about equal row counts, never splitting rows that share a time, and build N forward-moving splits. Split i validates on block i and trains on the earlier blocks (or on the M blocks before it with `--train-blocks`), keeping only training rows whose time is at least the declared gap before the first validation time. Rows in the gap are marked `gap`. The gap is given in days, or in hours, minutes or seconds with `--gap-unit`; numeric times use their own unit. Every gap comparison is made in seconds (or in the column's unit) before any rounding for display. With a test file, the script reports the time between the last training row and the first test row. When validation starts closer to training than the test does, it warns and fills `suggested_gap` with the gap that matches the test and the exact arguments to use: the largest unit that states the gap exactly in at most 6 decimals, preferring a value of at least 1, and otherwise a value rounded up, never down. Checks run before writing, including a check that each validation window starts after the previous one ends, computed from the assigned rows. After writing, the script rebuilds every split from the file and the times and confirms the order and the gap.

## Authoring basis and sources

Original text and code written from general knowledge of forward-chaining validation. No outside text or code was copied or adapted. The package format follows `src/loop_engine/core/service_runtime/catalogue_packages.py` at revision a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4. The starter body `audit_data_splits_for_errors_and_leakage.md` states the check that every training row is earlier than every test row for data with a time order. The repository executor `src/loop_engine/code_nodes/kaggle_executor.py` only has shuffled row folds.

## Inputs and outputs

Input: a UTF-8 CSV, the time column, `--time-kind iso` (dates and date-times, with or without a zone offset, never mixed) or `number`, a required `--gap`, an optional `--gap-unit` for iso times, the number of splits, an optional test CSV and a new output path. Output: a CSV with `row` and `split_1` to `split_N` holding `train`, `validation`, `gap` or `unused`, and one JSON report (`time_splits_report/v2`). Displayed gaps are in the chosen unit with at most 9 decimals. Exit 0 pass, 1 check failed, 2 refused. The report version moved from v1 to v2 in round 2 because gap values are now shown in the chosen unit and `suggested_gap` was added.

## Effects

`reads_fs` (training and optional test file), `writes_fs` (one new file in exclusive mode; missing parent folders under the root are created), `spawns_process`. No network, no secrets, no model calls. Paths with `..`, absolute paths and symbolic links are refused. Tests write only in temporary folders. The entry commands start the script with `python3 -I -B`: isolated mode ignores user site packages, `usercustomize` and `PYTHON*` environment variables, and no bytecode is written.

## Closest existing items

- Starter `audit_data_splits_for_errors_and_leakage`: a question set; it asks about time order and builds nothing.
- Wave 5 `build_group_stratified_folds`: group folds without time order. This package is the time-ordered counterpart and writes per-split membership, not one fold per row.
- No existing item builds time splits or checks a declared gap.

## Positive example

60 synthetic days with two rows per day, `--gap 7 --splits 3`: every split has `gap_observed` 7 days, gap rows are marked, and each validation window starts after the previous one ends. With a test file that starts 8 days after training and `--gap 0`, the report warns and `suggested_gap.arguments` is `--gap 8 --gap-unit days`; with `--gap 8` the warning disappears. With 200 hourly training rows and a test that starts 2 hours after training, `--gap 0` gives the arguments `--gap 2 --gap-unit hours`, and one more run with them ends with no warning and `gap_observed` 2 hours in every split.

## Known-wrong example

- A random 4-fold split of the same days puts validation rows before training rows (`test_known_wrong_random_split_validates_on_the_past`); in the script's splits every validation row is later than every training row.
- A gap of 40 days leaves split 1 without training rows, the check fails and no file is written.
- A 2-hour gap written in days and rounded to 6 decimals (0.083333) is below 7,200 seconds, so comparing it with the unrounded test gap never clears the warning; `test_known_wrong_hourly_gap_rounded_in_days_never_clears_but_suggested_gap_does` asserts that shortfall and then shows that the suggested arguments clear the warning in one run.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/build-time-ordered-splits/`, `.agents/skills/` (Codex), `.opencode/skills/`, `.pi/skills/` and `.gemini/skills/`. Basis: observed for Claude Code, Codex, OpenCode and Pi, documented for Gemini CLI (wave specification section 6; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`). Unverified: native loading of this package in any harness; Gemini CLI discovery on this machine; whether each harness shows the model the folder that holds `SKILL.md`, which the model needs to replace `SKILL_DIR`. The entry gives two example folders (`.agents/skills/...` and `.claude/skills/...`). The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Customer requests

- "Set up time-based validation for my sales forecast so the model never trains on the future."
- "I need walk-forward CV folds with a one-week gap before each validation window."
- "The test set starts two hours after train ends; make validation look like that."

## Limits

Blocks have about equal row counts, not equal durations. ISO values without a zone are compared as given; values with offsets are compared in UTC; the two kinds cannot be mixed. Month or business-day gaps are not supported; give the gap in days, hours, minutes or seconds. When no unit states a test gap exactly, the suggestion is rounded up, which can make validation start one time step later than the test. The script warns only when validation starts closer to training than the test does, not when it starts further away. The whole file is read into memory (64 MiB default bound). A synthetic file of 300,000 rows at 3-minute steps with a 100,000-row test file took about 2 seconds and 234 MB with `--gap 1 --gap-unit hours`.

## Pre-check history

Round 1: `fill` and `check` passed on the first run; every run is kept in `review/PRECHECKS.txt` and the dated `review/precheck-*.json` reports. Before packaging, the entry file had 480 words and was cut to fit the 450-word limit, and a known-wrong paragraph that blamed a trailing rolling mean for leakage was corrected. Mutants run on a copy of the payload: ignoring the gap, and training on later blocks, each made the tests fail.

## Repair round 2

The independent critic of 2026-09-23 recommended a repair. Each finding and its change:

1. Blocking, the test-gap warning never cleared for intraday data: the observed gap was rounded to 6 decimals of a day and compared with the unrounded test gap, and the suggestion was rounded down. Reproduced before the change: after a first run with `--gap 0`, two more runs with the suggested `--gap 0.083333` repeated the same warning. Gaps are now compared in seconds before rounding, `--gap-unit` was added, `suggested_gap` gives exact arguments or a value rounded up, and the entry tells the model to run once more with those arguments and to stop and report if a warning remains. The hourly test above was added.
2. Non-blocking, the displayed `gap_observed` could look smaller than the chosen gap: values are now shown in the chosen unit with 9 decimals, and the entry relies on the check results instead of asking the model to compare decimals.
3. Non-blocking, `validation_windows_move_forward` was true by construction: it is now computed from the assigned rows. A mutant that marks every later block as validation now fails this check before anything is written (`evidence/time-forward-check-mutant.txt`).
4. Unverified placement and `SKILL_DIR`: unchanged facts, restated above.

Evidence, all under `repair-a02_competition_modeling_tools/round-2-20260924T0501Z/` in the wave folder: `evidence/probe-before-round-2.txt`, `evidence/probe-after-round-2.txt`, `evidence/mutants-round-2.txt` (three mutants of this script, each caught by its named test) and `evidence/scale-probe-round-2.txt`. The first draft of the round 2 entry file had 461 words and was cut to 443 before packaging.
