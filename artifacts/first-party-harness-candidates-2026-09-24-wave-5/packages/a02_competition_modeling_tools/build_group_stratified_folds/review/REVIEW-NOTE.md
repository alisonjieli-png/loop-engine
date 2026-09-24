# Review note: Build group-aware stratified folds

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a02_competition_modeling_tools (model family anthropic), repaired in round 2 by the Claude Code repairer of the same assignment (same family). This note is never delivered to a harness.

## Method

One method: give every training row one fold number from 0 to K-1 so that all rows of a group share a fold and the label shares of each fold stay close to the whole file. Group values are compared after removing surrounding spaces; the fold file keeps the original text. The script orders groups by size (largest first, equal sizes in a seeded shuffled order) and puts each group into the fold whose counts of the group's labels are furthest below their targets. Each label's shortfall is divided by its per-fold target (at least 1), so a rare label weighs as much as a common one. Ties go to the fold with fewer rows, then the lower fold number.

A numeric label can be cut into at most N bins of about equal rows with `--label-bins N`. Equal values always share a bin, and a value that holds at least one bin's share of the remaining rows gets a bin of its own, such as all the zeros of a mostly zero target. With at most N distinct values, each value is its own bin.

Before writing, the script checks seven facts: every row assigned once, no group in two folds, no empty fold, at least two label strata, each label in every fold, the largest label share gap and the fold size ratio. Every class label must reach every fold, except that `--allow-missing-labels` lets a class label held by fewer groups than folds miss some folds, with a warning. A numeric bin must reach every fold only when at least K groups hold it. A failed check carries a `hint`, and nothing is written. After writing, the script reads its own file again and confirms rows, groups and folds.

## Authoring basis and sources

Original text and code written for this package from general knowledge of cross-validation. No outside text or code was copied or adapted. The package format follows `src/loop_engine/core/service_runtime/catalogue_packages.py` at revision a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4. The repository's competition executor `src/loop_engine/code_nodes/kaggle_executor.py` uses plain row-level stratified folds with a fixed seed, which is the gap this package addresses. The starter item body `audit_data_splits_for_errors_and_leakage.md` states the check that no entity appears in more than one split.

## Inputs and outputs

Input: a UTF-8 CSV with a header row, the group column, the label column, K, the seed and a new output path, all relative to `--root`. Output: a CSV with `row`, `group` and `fold`, one line per data row in input order, and one JSON report on standard output (`group_folds_report/v2`) with the checks, their hints, warnings, fold sizes, label shares, the rarest label's rows per fold, labels missing from folds, bin ranges and the output digest. Exit 0 pass, 1 check failed, 2 refused. The report version moved from v1 to v2 in round 2 because fields changed (`label_values` became `label_strata`, `label_bin_edges` became `label_bin_ranges`, and new checks and fields were added).

## Effects

`reads_fs` (the training file), `writes_fs` (one new file, created with exclusive mode; missing parent folders under the root are created), `spawns_process` (the reader runs the script). No network, no secrets, no model calls. Paths with `..`, absolute paths and symbolic links are refused. The tests write only inside temporary folders. The entry commands start the script with `python3 -I -B`: isolated mode ignores user site packages, `usercustomize` and `PYTHON*` environment variables, and no bytecode is written.

## Closest existing items

- Starter `audit_data_splits_for_errors_and_leakage`: a question set that asks whether an entity crosses splits. It builds nothing and runs no check.
- Wave 5 `verify_fold_group_separation` (assignment a15): checks any given fold file. This package builds folds and checks only its own output. The two stay distinct: one creates, one verifies. The fold file keeps the original group text, so that verifier's comparison of the fold file's group copy with the training file still matches.
- The repository executor's row-level folds: no group awareness.

## Positive example

A synthetic file of 60 customers with one to four visits each (150 rows) and a label share near 25 percent gives five folds of 30 rows, twelve customers per fold, no customer in two folds and a largest label share gap of 0.02 at seed 42; label 1 has 7, 7, 8, 7 and 8 rows in the five folds. The same seed gives the same bytes on a second run. A sales column of 400 stores by 10 weeks with about 93 percent zeros and `--label-bins 10` gives a zero bin of 3,718 rows and nine bins of 30 to 33 rows for the other values.

## Known-wrong example

- A row-level random 5-fold assignment of the 60-customer file puts more than ten customers in two folds (`test_known_wrong_row_level_random_split_mixes_groups`); the script's report for the same data shows `groups_in_two_folds` 0.
- Quantile edges that are deduplicated and applied with a right bisection put every row of the mostly zero sales column into one bin, so no label balancing happens. The test `test_known_wrong_zero_heavy_label_gets_a_zero_bin_and_bins_for_the_rest` computes those edges, shows one bin, and then shows ten strata from the script.
- A label held by 3 of 200 groups cannot reach 5 folds. The script fails `each_label_in_every_fold`, names the label and its 3 groups, writes nothing, and its hint names `--folds` and `--allow-missing-labels`; with `--folds 3` each fold gets 4 of the 12 label rows.
- A file where one customer holds 400 of 549 rows fails `fold_size_ratio` and `label_share_gap`, and no file is written.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/build-group-stratified-folds/`, `.agents/skills/` (Codex), `.opencode/skills/`, `.pi/skills/` and `.gemini/skills/`. The skill folder class is recorded as observed for Claude Code, Codex, OpenCode and Pi and as documented for Gemini CLI in the wave specification section 6 and `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`; the critic also found these paths in the official documentation of Claude Code, Codex, OpenCode and Gemini CLI. Unverified: native loading of this package in any harness (no probe was run); Gemini CLI discovery of `.gemini/skills` on this machine; whether each harness tells the model the folder that holds `SKILL.md`, which the model needs to replace `SKILL_DIR` in the commands. The entry now gives two example folders (`.agents/skills/...` and `.claude/skills/...`) instead of only the Claude Code one. Scripts are started as `python3`; the host must bind a trusted interpreter, because a `python3` found first on `PATH` can be replaced.

## Customer requests

- "Make me 5 CV folds where the same customer never lands in two folds."
- "My patients have several visits each; split the training data so validation is honest."
- "Create a fold column for train.csv grouped by store and balanced on the target."

## Limits

The greedy assignment is not optimal; with a few very large groups the limits can be unreachable, and the script then refuses to write rather than loosen them. A label held by fewer groups than folds cannot reach every fold; that needs fewer folds or `--allow-missing-labels`. Numeric bins held by fewer groups than folds may miss folds; the report counts them in `small_bins_not_in_every_fold`. At most 100 class labels without bins. Group values are compared after removing surrounding spaces, and letter case is kept, so `A1` and `a1` stay two groups. The whole file is read into memory (64 MiB default input bound). On 300,000 synthetic rows and 40,000 groups the build took about 1.5 seconds and 180 MB, and 1.9 seconds with 10 label bins.

## Pre-check history

Round 1: `fill` and `check` passed on the first run; every run is kept in `review/PRECHECKS.txt` and the dated `review/precheck-*.json` reports. Mutants run on a copy of the payload: assigning folds by row, and dropping the label cost from the assignment, each made the tests fail. A first version of the second mutant also shortened the tie-break tuple, crashed the script and so tested nothing; it was replaced by one that keeps the tuple shape.

## Repair round 2

The independent critic of 2026-09-23 recommended a repair. Each finding and its change:

1. Blocking, tied values in `--label-bins`: 400 stores by 10 weeks with about 93 percent zero sales passed with one stratum. Reproduced before the change. Bins are now built from sorted distinct values so that equal values share a bin and a heavy value gets its own bin, a new check `at_least_two_label_strata` fails a label with one value or one bin, and a zero-heavy test was added.
2. Blocking, rare label missing from folds: label 1 in 3 of 200 groups at K = 5 passed with label 1 absent from two folds. Reproduced before the change. The new check `each_label_in_every_fold` fails it with a hint, and the assignment cost is now relative to each label's target. On synthetic data where 5 to 8 of 200 equal groups hold one positive row, the earlier cost wrote files with a fold missing the label in 7 of 10 sets; the relative cost missed none, and across 60 sets of six data families no set failed a check and the worst share gap and size ratio did not grow. A raw-cost mutant fails `test_rare_label_in_few_groups_reaches_every_fold`.
3. Non-blocking, group values with surrounding spaces: `g0` and `g0 ` became two groups. They are now one group, with a warning and a count; the fold file keeps the original text.
4. Non-blocking, group column choice: step 1 now asks for a column that names an entity and repeats across rows, and says that a category such as city is not a group.
5. Unverified placement and `SKILL_DIR`: unchanged facts, restated above; the entry gives a harness-neutral example.

Evidence, all under `repair-a02_competition_modeling_tools/round-2-20260924T0501Z/` in the wave folder: `evidence/probe-before-round-2.txt` and `evidence/probe-after-round-2.txt` (the critic's cases before and after), `evidence/rare-few-groups-old-vs-new.txt`, `evidence/group-folds-families-old-vs-new.txt`, `evidence/zero-heavy-bins-new.txt`, `evidence/mutants-round-2.txt` (six mutants of this script, each caught by its named test) and `evidence/scale-probe-round-2.txt`. The first draft of the round 2 entry file had 458 words and was cut to 446 before packaging. The first written pre-check of round 2 (run 4 in `review/PRECHECKS.txt`) was refused on `layout`, `inventory`, `text_hygiene` and `placements`, because a repairer probe had imported the test module without `-B` and left a bytecode cache in `payload/tests/`. The cache was removed and run 5 passed with the same package digest; the refused report is kept.
