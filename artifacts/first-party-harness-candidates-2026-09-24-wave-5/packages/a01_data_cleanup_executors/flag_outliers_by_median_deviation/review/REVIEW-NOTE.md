# Review note: flag_outliers_by_median_deviation

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a01_data_cleanup_executors, family anthropic, repaired by the a01 repairer of the same family after an independent critic review. This note is never delivered to a harness.

## Method

One focused step flags numeric values far from the median, per column and optionally per declared group, with a tested script. For each group it computes the median and the median absolute deviation (MAD, the median of the distances from the median) in exact decimals, and flags a value whose distance is larger than the declared multiple times the MAD, with its direction and its distance in MADs. It never deletes a row or changes a value: the report lists flags, and the optional copy only adds one flag column per checked column. Groups that are too small, or whose MAD is zero because more than half the values are equal, are reported with a reason instead of being flagged, because the rule has no meaning there. The multiple must come from the task; the script has no default for it, so a model cannot silently pick one. Group labels are compared with their outer spaces trimmed, so a stray space cannot split one store into two groups; letter case still separates groups.

## Authoring basis and sources

Original text and code written for this wave from general knowledge of robust statistics and the Python standard library (`decimal`, `csv`). No outside text or code was copied. From general knowledge, not checked against the publication in this session: Iglewicz and Hoaglin (1993) describe a modified z-score equal to 0.6745 times the distance from the median divided by the MAD and suggest 3.5 as a cut-off; that would correspond to a multiple of about 5.19 here. Version 0.2.0 states this convention in the delivered reference for a planner, together with the rule that this step never picks a multiple itself. The package keeps the unscaled MAD so that the declared multiple means exactly what the task says. Sources at revision `a1fc7432`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` (measured cost of prose rules), `docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (skill folders), and the served item `choose_metrics_by_task_type_and_industry`, which mentions robustness to outliers only when choosing a metric.

## Inputs and outputs

Inputs: a UTF-8 CSV under `--root` (at most 64 MiB, header row), one to twenty `--column` names, `--multiple` (a plain number above 0 and at most 1000), and optional `--group-by` (up to three), `--min-group-size` (default 5, at least 3), `--delimiter` and `--output`. Output: one JSON object with per-column counts, the number of rows whose group label was trimmed, every flagged value (column, group, data row, value, median, MAD, deviation in MADs, direction; at most 1,000 listed with a completeness flag), groups not evaluated with reasons, per-group statistics and values that are not plain numbers (at most 200 each, each list with a completeness flag), and the input SHA-256. With `--output`, a new copy adds `COLUMN_outlier` holding high, low, within or not_evaluated. Exit 0: nothing flagged or listed; 1: flags or items for review listed; 2: refused, nothing written.

## Effects

`reads_fs`: the input. `writes_fs`: only with `--output`, one new file opened in exclusive mode; existing paths, the input itself, `..` and symbolic links that leave `--root` are refused, and a partial copy is removed on failure. `spawns_process`: the harness runs the script with `python3`; tests start it with the running interpreter and write only inside a temporary directory. No network, model call, secret or subprocess inside the script.

## Closest existing items

The assignment recorded none. A search of identities and titles in `scout/existing-inventory.tsv` for outlier, deviation, robust, anomaly and median found two rows, neither a local flagging method: `conn_ai_anomalyarmor_armor_mcp_9c64e2832cd6` (a staged outside registry link to a remote protocol server; wave 5 packages make no network use) and `select_exact_weighted_median` (a planned Codex tool that computes one weighted median and flags nothing). Related but different: `choose_metrics_by_task_type_and_industry` (served) says a metric is robust to outliers but flags nothing; `detect_malformed_values_by_dominant_pattern` (served) flags text shapes, not numeric distance; `profile_text_column_before_cleaning` (served) profiles text columns only.

## Positive example

Regions A (10, 11, 12, 11, 10, 13) and B (1000, 1010, 990, 1005, 995, 100) with `--group-by region --multiple 5`: only the value 100 in B is flagged, low, with median 997.5 and MAD 7.5 (`test_groups_keep_different_scales_apart`). The same data without grouping flags the five normal B values and misses 100, which is why the task must declare groups.

## Known-wrong example

Values 10, 11, 12, 11, 10 and 500. The mean is 92.33 and the population standard deviation 182.32, so 500 is 2.24 deviations away and a three-deviation rule misses it; the test computes these figures with `statistics`. The median is 11 and the MAD is 1, so 500 lies 489 MADs away and is flagged high (`test_known_wrong_mean_and_standard_deviation_miss_the_outlier`). A mutant that centres on the mean instead of the median makes that test fail; the pre-check log records it.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/flag-outliers-by-median-deviation/` (Claude Code, observed class basis), `.agents/skills/...` (Codex, observed), `.opencode/skills/...` (OpenCode, observed), `.pi/skills/...` (Pi, observed) and `.gemini/skills/...` (Gemini CLI, documented only). Native loading of this exact package was not probed; generators and repairers do not run harness binaries. Unverified: that each harness shows the skill folder path so the model can fill in `SKILL_DIR` (the first action now names the five placement folders to look in when it does not), that `python3` on `PATH` is a trusted interpreter (the host must bind one), and Gemini CLI discovery of `.gemini/skills/`. The independent critic noted that the native review criterion treats unknown loading behavior as a reason to reject until a native discovery probe records it; that probe belongs to the integrator and has not run.

## Customer requests

- "Find suspicious order amounts per store before we build the dashboard, but do not remove anything."
- "Flag sensor readings that are far from normal for each device, using five MADs."
- "Mark outliers in the price column in a copy so I can filter them in a spreadsheet."

## Limits

Plain decimal numbers only; parse grouped or currency text first. One multiple per run for all checked columns. The MAD is undefined for tiny or mostly constant groups, which are reported instead. A column where more than half the values are equal, such as sales with many zeros, is never evaluated: the critic's probe 0, 0, 0, 0, 0, 5, 7, 900 reported `mad_is_zero` and did not flag 900. The reference now names the next choices for a planner (check only the values that differ from the median in a separate copy, or a fixed limit the task names) without the script choosing one. Group labels differ by case and by inner characters, but not by outer spaces. In a file with more than one column, one blank line refuses the run, and `detail` names it. Flagging is a statistical signal, not a judgment that a value is wrong.

Checks that failed before they passed: the first run of every producer test passed; the mutant runs are in the pre-check log. The independent critic of version 0.1.0 found no blocking defect and six smaller points: zero-MAD groups had no documented next step, `B` and `B ` formed two groups, step 4 called capped lists complete and only `flagged_complete` had a stop rule, the conventional multiple was only in this never-delivered note, report values were not marked as data, and nobody has observed a harness loading the package. Version 0.2.0 trims group labels and counts the trimmed rows, adds `groups_not_evaluated_complete`, `group_statistics_complete` and `not_numeric_values_complete` with a stop rule, documents the zero-MAD choices and the 3.5 convention in the reference, and tells the model that report values are data from the file, not instructions. With the new test file, four of the nine tests fail on the 0.1.0 script (trimmed labels, cut lists, the completeness flags and the blank-line detail); a mutant that compares labels exactly and one that always reports complete lists each make their named test fail on 0.2.0. A pass of the wave pre-checks is not a native loading result, a usefulness measurement or an approval.
