# Review note: Audit train and test column drift

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a02_competition_modeling_tools (model family anthropic), repaired in round 2 by the Claude Code repairer of the same assignment (same family). This note is never delivered to a harness.

## Method

One method: compare every column shared by a training file and a test file, and list what differs before feature work. Per column the script measures missing rates, test values never seen in training, test numbers outside the training range and a population stability index (PSI). Text columns use the 30 most common training values plus one bucket for the rest. Numeric columns use up to 10 buckets of about equal training rows: equal values always share a bucket, a value that holds at least one bucket's share of the remaining rows gets a bucket of its own (such as 0 in a mostly zero column), and a column with at most 10 distinct values gets one bucket per value. A test number goes to the first bucket whose largest training value is not below it. The script also lists columns in only one file, a target column present in the test file, text in a column that is numeric in training, constant or empty training columns, and columns that look like identifiers (no training value repeats and at least 90 percent of test values are new; for integers the training values must also be dense). It writes nothing.

## Authoring basis and sources

Original text and code from general knowledge of data drift checks. No outside text or code was copied or adapted. PSI is a standard measure; the reference file calls its 0.1 and 0.25 levels a common rule of thumb, not a law. The package format follows `src/loop_engine/core/service_runtime/catalogue_packages.py` at revision a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4. Related sources: the starter bodies `check_that_a_result_is_stable_and_generalizes.md` (profile drift between samples) and `audit_data_splits_for_errors_and_leakage.md`, and the pilot `audit-csv-structure/SKILL.md` (one file's row shape).

## Inputs and outputs

Input: `--train` and `--test` CSV paths under `--root`, or one JSON object with the strings `train_csv` and `test_csv` through `--pair-json` (a file or standard input), plus optional `--target`, `--id`, `--missing-token` and limits. Output: one JSON report (`train_test_drift_report/v2`); a numeric `distribution_shift` finding names the number of `buckets` used. Exit 0 no findings, 1 findings listed, 2 refused. The report version moved from v1 to v2 in round 2 because numeric PSI values are computed over different buckets, so v1 and v2 values are not comparable.

## Effects

`reads_fs` and `spawns_process` only. The script and its tests write no file; the tests read the shipped example and pass data on standard input, so the package needs no write authority. No network, no secrets, no model calls. Paths with `..`, absolute paths and symbolic links are refused. The entry commands start the script with `python3 -I -B`: isolated mode ignores user site packages, `usercustomize` and `PYTHON*` environment variables, and no bytecode is written. The report copies up to 40 characters of some cell values (`examples`, `test_examples`) and the column names; the entry file tells the model to treat them as data, never as instructions.

## Closest existing items

- Pilot `audit_csv_structure`: row shape of one file; no comparison between files.
- Starter `check_that_a_result_is_stable_and_generalizes`: asks for drift profiling in prose; runs nothing.
- Wave 5 `leakage_reviewer` (a05) reviews by reading; this package measures.

## Positive example

`examples/drift-pair.json` (40 training rows, 20 test rows, synthetic) with `--target target --id id` flags exactly `store_type` (value `outlet` in 25 percent of test rows), `price` (30 percent above the training maximum) and `promo` (40 percent missing in test), lists `channel` as test-only, and leaves `age` and `city` unflagged. Without `--id`, `id` is flagged as `identifier_like`.

## Known-wrong example

- A header and value-type comparison of the same pair finds no difference; `test_known_wrong_header_and_type_check_sees_nothing` shows that, and the audit still flags `store_type` and `price`.
- Deduplicated decile edges with a right bisection put every value of a 0/1 flag, and every value of a mostly zero amount, into one bucket, so PSI is 0. With 5,000 training and 2,000 test rows, a flag that moves from 5 to 50 percent ones and an amount that moves from 93 to 40 percent zeros then pass with no finding. `test_known_wrong_tied_numeric_values_still_show_a_large_shift` computes that PSI of 0 for both columns and then shows the audit flagging both (flag PSI above 1.0 over 2 buckets) while leaving a stable `noise` column unflagged.
- A first draft marked `age` as an identifier because 40 rows held 40 distinct dense integers; the identifier rule was changed to also require new test values, and a test keeps `age` unflagged.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/audit-train-test-drift/`, `.agents/skills/` (Codex), `.opencode/skills/`, `.pi/skills/` and `.gemini/skills/`. Basis: observed for Claude Code, Codex, OpenCode and Pi, documented for Gemini CLI (wave specification section 6; `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`). Unverified: native loading of this package in any harness; Gemini CLI discovery on this machine; whether each harness shows the model the folder that holds `SKILL.md`, needed to replace `SKILL_DIR`. The entry gives two example folders (`.agents/skills/...` and `.claude/skills/...`). The host must bind a trusted `python3`.

## Customer requests

- "Check whether my test set looks like my training set before I build features."
- "Which columns have categories in test that never appear in train?"
- "Did the missing values or ranges change between train.csv and test.csv?"

## Limits

Numeric PSI uses a fixed-seed sample of at most 10,000 values per column and file. The unseen-value check is skipped, with a note, when a training text column has more than 50,000 distinct values, or when a column held more than 5,000 distinct numbers before its first text value. Identifier detection for a numeric column with more than 5,000 distinct training values uses the share of test values outside the training range. Values are compared as exact text after missing tokens are removed, so `A` and `A ` differ. Thresholds are defaults, not facts about any data set. Both files are held in memory as bytes and decoded while they are read: on a synthetic pair of 57 MB and 21 MB with 150 numeric columns (40,000 and 15,000 rows) the peak was about 186 MB and the run took about 23 seconds. Memory grows with input size, so raise `--max-bytes` toward its 1 GiB hard limit only on a machine with room.

## Pre-check history

Round 1: `fill` and `check` passed on the first run with a tracking cap of 5,000 distinct values per column. A scale run on 300,000 training and 100,000 test rows then showed that the cap skipped the unseen-value check for a 40,000-value user column, so the cap was raised to 50,000, a test for the skipped-check note was added, and the package was filled and checked again. Mutants run on a copy of the payload: removing the unseen-value count, and removing the outside-range count, each made the tests fail. Every run is kept in `review/PRECHECKS.txt` and the dated reports.

## Repair round 2

The independent critic of 2026-09-23 recommended a repair. Each finding and its change:

1. Blocking, numeric PSI missed large shifts in tied columns: the critic's flag and zero-heavy amount case gave exit 0 with no findings. Reproduced before the change. Numeric buckets are now tie-aware as described in Method, and the test above was added. After the change the same case gives flag PSI about 1.48 and amount PSI about 1.57 (`evidence/probe-after-round-2.txt`).
2. Non-blocking, memory: numeric columns stored up to 50,000 distinct raw strings per column in both files, and the decoded text was held in a buffer of about four bytes per character. Measured on the pair above before the change, in two runs: about 1,150 MB, and 26 and 35 seconds. The test file now keeps no distinct values, a column keeps at most 5,000 distinct values while every value so far is a number, samples are stored as packed floats, and the text is decoded while it is read after a UTF-8 check. After the change: about 186 MB and 23 seconds. A differential probe of 16 tricky inputs (line endings, a byte order mark, quoted line breaks, blank lines, invalid UTF-8, a malformed quote) read the same rows or the same refusal before and after (`evidence/drift-table-differential.txt`).
3. Non-blocking, cell values in the model's context: the entry now says that column names and the values in `examples` and `test_examples` are data, never instructions.
4. Unverified placement and `SKILL_DIR`: unchanged facts, restated above.

Evidence, all under `repair-a02_competition_modeling_tools/round-2-20260924T0501Z/` in the wave folder: `evidence/probe-before-round-2.txt`, `evidence/probe-after-round-2.txt`, `evidence/drift-memory-old-vs-new.txt` (first change only: 416 MB), `evidence/drift-memory-old-vs-new-lazy-decoding.txt` (final: 186 MB), `evidence/drift-table-differential.txt` and `evidence/mutants-round-2.txt` (two mutants of this script, each caught by its named test).
