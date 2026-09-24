# Review note: Validate a submission file against the sample

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a15_data_and_competition_verifiers, model family anthropic. This note is never delivered to a harness.

## Method

One verifier method. The script `scripts/validate_submission.py` compares a submission file with the sample submission of the competition and returns one JSON verdict before any upload step. The sample is the authority on the header, the id column (its first column unless `--id-column` names another) and the set of ids. The script checks the exact header, the field count of every row, the row count, missing, extra and repeated ids, optionally the sample row order, and every prediction value for the task type given with `--task`: `probability` (a plain number from 0 to 1), `class_probabilities` (also a row sum of 1 within `--sum-tolerance`), `label` (exactly one of `--labels`), `number` (optionally within `--min` and `--max`) or `text` (not empty). Hints name a likely cause of a failure, such as a written row index or ids written as `1001.0`. Warnings name files that pass but look wrong, such as probabilities that are all 0 or 1, or predictions equal to the placeholder values of the sample. Exit 0 is pass, 1 is fail, 2 is refused input. Nothing is uploaded; the output says so.

## Authoring basis and sources

Original text and code written for this wave, MIT like the repository. No outside text or code was copied. The package continues an interrupted earlier attempt of the same generator assignment, which wrote the script and the two examples and stopped before the skill text, the references, the tests, the manifest and this note. That attempt is kept byte for byte in `packages/validate_submission_file/earlier-attempt-20260924T0102Z.tar.gz`. This run reviewed every line of the script and changed it in three places: a sample without data rows is refused (`sample_has_no_rows`), a first line that holds data gets its own hint, and an empty value in `--labels` is refused, because an empty cell is a missing value and not a label. It then wrote `SKILL.md`, `references/task-types.md`, `references/checklist.md`, the 23 tests, the manifest and this note.

Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `src/loop_engine/code_nodes/kaggle_executor.py`: its rule that the submission template is the authority on output fields, never a guessed column name. This package applies the same rule to a finished file.
- `examples/25_host_runtime/competition_prediction.py`: the host example checks its own predictions before it writes its submission and reads the header and ids back afterwards. This package checks any submission file on disk, whoever wrote it.
- `docs/verification/KAGGLE-TWELVE-COMPETITION-CAMPAIGN-2026-09-03.md`: in 2 of 12 recorded competitions the run wrote hard `0` and `1` labels where the metric wanted probabilities, and the files passed every structural check. That record is the reason for the warning on probabilities that are all 0 or 1.

## Inputs and outputs

Inputs: `--submission` and `--sample` below `--root` (default the current folder), or `--bundle` with the members `submission` and `sample`; `--task`; `--labels` for `label`; optional `--min`, `--max`, `--sum-tolerance`, `--id-column`, `--require-same-order`, `--delimiter`, `--max-examples` and `--max-bytes` (default 64 MiB, refused above it). Output: one JSON object with `status`, the SHA-256 digests of both files, the id column and the prediction columns, `checks` with a count for every check of the task type, `failed_checks`, bounded `violations`, `hints`, `warnings` and `upload: not attempted`.

## Effects

`reads_fs`: the script reads the two named files and refuses `..`, paths outside `--root` (also through a symbolic link), non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, uploads nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples, send other inputs on standard input and write no file.

## Closest existing items

- No existing item checks a finished submission file. `closest_existing` in `assignments.json` says none found. A search of `scout/existing-inventory.tsv` found no identity or title with the word submission; the three rows with the word upload are remote protocol server links for unrelated services.
- `submission_assembly_packet` (wave 5, a10): the step that assembles a submission. This package is the independent check after it and before any upload.
- `recompute_claimed_cv_score` (wave 5, this assignment): checks a local score claim. This package checks the file format only and says nothing about the score.

## Positive example

`examples/submission-bundle.json` with `--task probability`: 12 ids from `1001` to `1012` with probabilities, the exact header `id,target`, no warnings. The verdict is pass.

## Known-wrong example

`examples/known-wrong-bundle.json` holds the same predictions written with the row index of the table as an unnamed first column and the ids read as numbers (`1001.0`). The row count and every probability look right. The script fails `header`, `missing_id` for all 12 ids and `extra_id` for all 12, and gives two hints: a written row index, and ids that differ only in number format. Further known-wrong cases in the tests: a missing header line, header names in another order or letter case, repeated and unknown ids, rows with an extra field, probabilities outside 0 to 1, `NaN`, empty cells, a number with a trailing space, class probabilities that do not add up to 1, labels in another letter case or with a leading space, numbers outside a declared range, empty text, and rows in another order when the order is required.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/validate-submission-file/`, `.agents/skills/validate-submission-file/` (Codex), `.opencode/skills/validate-submission-file/`, `.pi/skills/validate-submission-file/` and `.gemini/skills/validate-submission-file/`. Basis: specification section 6 marks the first four skill folders observed on this machine and the Gemini CLI folder documented in `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`. No harness binary was run for this package. Unverified: whether each harness tells the model the folder path it needs for `SKILL_DIR`, and whether a harness asks for permission before `python3` runs from a skill folder. The command starts the first `python3` on `PATH`; a host that runs unattended should bind a trusted interpreter.

## Customer requests

- "Check my submission.csv against sample_submission.csv before the overnight run uploads it."
- "Why was my submission rejected? The ids look right to me."
- "Make sure every row has a probability between 0 and 1 and no id is missing."

## Limits

The task type must come from the rules; the script cannot read the rules or tell from the sample values whether a metric wants probabilities or labels. Ids and labels are compared as exact text, and a number with spaces around it is not a plain number. Compressed files are refused; unpack and check the CSV inside. A competition that accepts extra columns or another header is outside this check. A valid file can still score badly. Checks that failed before they passed: the first run of the new tests failed one case, where the test passed an empty value in `--labels` and expected a missing value; the script now refuses an empty label and the test was corrected to match that decision. The first mutation pass ran 28 changes of the script and 1 was not caught (the size bound on a named file, which the bundle test did not reach); the test was extended, and each of the 28 changes now fails a named test. The first wave pre-check refused `text_hygiene`, because the byte order mark test held the invisible character itself instead of its escape `﻿`; the source now holds the escape and the test is unchanged in meaning. The suite holds 23 tests and passes under Python 3.14 and 3.10.
