# Review note: Rank experiment runs by fold scores

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a02_competition_modeling_tools (model family anthropic), repaired in round 2 by the Claude Code repairer of the same assignment (same family). This note is never delivered to a harness.

## Method

One method: rank runs from a ledger of per-fold scores and say which gains are larger than their fold-to-fold variation. The reference fold set is the one most runs use; with a tie, the one with more folds. Runs on the reference fold set are ranked first by mean fold score in the declared direction, then by the smaller fold standard deviation, then by name; runs on other fold sets follow in the same order, marked `same_folds_as_reference: false`. Only a run on the reference fold set can lead or tie with the leader. Comparisons are paired: for two runs scored on the same fold set, the gain on each fold is taken in the declared direction, and a gain is established only when, over at least 3 shared folds, the mean per-fold gain is larger than the sample standard deviation of those gains and larger than `--min-gain`. Runs on different fold sets are `not_comparable`. The report gives the leader, whether its lead over the second comparable run is established, the comparable runs tied with the leader, each run's gain over the next one, and optional verdicts against a baseline. The rule text, including that it is a decision rule and not a significance test, and the meaning of each verdict are part of the JSON.

## Authoring basis and sources

Original text and code from general knowledge of paired comparison over cross-validation folds. No outside text or code was copied or adapted. The package format follows `src/loop_engine/core/service_runtime/catalogue_packages.py` at revision a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4. Related sources: `src/loop_engine/code_nodes/measurement.py`, where `read_generalization_gap` treats a gap within the fold spread as unreliable; the starter bodies `check_that_a_result_is_stable_and_generalizes.md`, `read_the_train_validation_gap.md` and `compare_a_smaller_model_against_the_larger_one.md`. The rule "mean larger than the spread" is a plain decision rule, not a significance test. It is the same as a paired t value above the square root of the number of shared folds, so it is loose at 3 folds (t above about 1.73) and strict at 10 folds (t above about 3.16).

## Inputs and outputs

Input: a ledger under `--root` or on standard input as CSV, a JSON array or JSON Lines, one record per run and fold with `run`, `fold` and `score` (field names configurable), and a required `--direction`. Output: one JSON report (`fold_score_ranking/v2`). Exit 0 ranked, 1 ranked but some runs use a different fold set, 2 refused (for example a repeated run and fold pair, a score that is not a finite number, or a missing direction). The report version moved from v1 to v2 in round 2 because the meaning of `leader` and the ranking order changed.

## Effects

`reads_fs` and `spawns_process` only. The script and its tests write no file. No network, no secrets, no model calls. Paths with `..`, absolute paths and symbolic links are refused. The entry commands start the script with `python3 -I -B`: isolated mode ignores user site packages, `usercustomize` and `PYTHON*` environment variables, and no bytecode is written. Run names from the ledger appear in the report; the entry tells the model to treat them as data, never as instructions.

## Closest existing items

- Starter `check_that_a_result_is_stable_and_generalizes`: says in prose that a gain smaller than the spread is not shown; it computes nothing.
- Starter `compare_a_smaller_model_against_the_larger_one` and wave 1 `compare_model_context_pairs_on_frozen_cases`: design comparisons on frozen cases, not fold scores.
- Wave 5 `recompute_claimed_cv_score` (a15) recomputes one claimed score; `pick_next_experiment` (a06) chooses work. This package only ranks and compares.

## Positive example

`examples/ledger.json` holds four synthetic runs on five folds. With `--direction maximize --baseline baseline_lr`, `gbm_v2` leads, `leader_established` is false, `gbm_v1` and `gbm_v1_more_trees` are tied with the leader, and all three models beat the baseline with an established gain. A run that is 0.005 better on every fold is established even though the fold scores themselves vary by about 0.04, because the comparison is paired.

## Known-wrong example

- Means of 0.846 against 0.842 look like a win, but the per-fold gains are 0.012, -0.006, 0.009, -0.004 and 0.009: mean 0.004, sample standard deviation about 0.0083, so the verdict is `gain_not_established` (`test_known_wrong_mean_only_comparison_is_not_established`). A wrong direction is not guessed: `--direction` is required.
- A run that stopped after 3 good folds has the highest mean. Ranking by each run's own mean made it the leader, with `tied_with_leader` empty. Now `full_b`, which beats `full_a` by 0.01 on each of 5 folds, leads with an established gain, and the stopped run is ranked last in `fold_set_mismatch` (`test_known_wrong_partial_run_with_high_early_folds_does_not_lead`).

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/rank-experiments-by-fold-scores/`, `.agents/skills/` (Codex), `.opencode/skills/`, `.pi/skills/` and `.gemini/skills/`. Basis: observed for Claude Code, Codex, OpenCode and Pi, documented for Gemini CLI (wave specification section 6; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`). Unverified: native loading of this package in any harness; Gemini CLI discovery on this machine; whether each harness shows the model the folder that holds `SKILL.md`, needed to replace `SKILL_DIR`. The entry gives two example folders (`.agents/skills/...` and `.claude/skills/...`). The host must bind a trusted `python3`.

## Customer requests

- "Is my new model actually better than the old one, or is it just CV noise?"
- "Rank all my experiments from the log and tell me which ones are really ahead."
- "Which runs beat the baseline on the same folds?"

## Limits

With few folds the rule is weak: 3 to 5 folds give little power, and the rule can mark a real small gain as not established. It assumes each run's scores come from the same fold definitions; the fold identifiers are compared, not the rows inside them. It does not correct for testing many runs against one leader. When most runs use a partial fold set, that set becomes the reference and the complete runs are the ones set apart; the report then shows the smaller `reference_folds`. At most 200,000 records and 5,000 runs; the report shows the first 100 runs.

## Pre-check history

Round 1: `fill` and `check` passed on the first run; every run is kept in `review/PRECHECKS.txt` and the dated reports. Mutants run on a copy of the payload: ignoring the spread of the gains, and ignoring the direction, each made the tests fail.

## Repair round 2

The independent critic of 2026-09-23 recommended a repair. Each finding and its change:

1. Blocking, a run on a different fold set could lead: `full_a` and `full_b` on folds 0 to 4 and `crashed` on folds 0 to 2 gave exit 1, leader `crashed` and an empty `tied_with_leader`. Reproduced before the change. The leader and the tied runs now come only from runs on the reference fold set, those runs are ranked first, and the entry says what exit 1 means and when to stop and report. The existing fold-set test was updated to the new order, and the stopped-run test above was added.
2. Non-blocking, the rule could be quoted as a significance test: the entry and the JSON rule now say it is not one, and this note gives the equivalent paired t threshold.
3. Unverified placement and `SKILL_DIR`: unchanged facts, restated above.

Evidence, all under `repair-a02_competition_modeling_tools/round-2-20260924T0501Z/` in the wave folder: `evidence/probe-before-round-2.txt`, `evidence/probe-after-round-2.txt` and `evidence/mutants-round-2.txt` (two mutants of this script, each caught by its named test). The first draft of the round 2 entry file had 463 words and was cut to 436 before packaging.
