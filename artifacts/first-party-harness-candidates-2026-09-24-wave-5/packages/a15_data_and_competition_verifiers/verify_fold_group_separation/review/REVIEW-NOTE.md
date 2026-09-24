# Review note: Verify fold assignments keep groups apart

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a15_data_and_competition_verifiers, model family anthropic. This note is never delivered to a harness.

## Method

One verifier method. The script `scripts/verify_folds.py` reads a fold assignment file that some other step made, and optionally the training table it belongs to, and returns one JSON verdict. It checks that every training row has exactly one fold record (`row_without_fold`, `row_in_two_folds`, `row_listed_twice`, `unknown_row`), that no group named by `--group-column` has rows in two folds (`group_in_two_folds`, `row_without_group`), that a copy of the group or label in the fold file agrees with the training table, that the share of each label value in each fold stays within `--label-tolerance` of its share over all rows (`label_share_gap`, with `--label-bins` for a numeric label), and optionally that the number of folds equals `--expected-folds`. Three layouts are accepted: the fold column inside the training file, a fold file joined by an id column, and a fold file that holds training row numbers. Exit 0 is pass, 1 is fail, 2 is refused input. The checklist asks what code cannot judge, such as whether the named column is the real entity.

## Authoring basis and sources

Original text and code written for this wave, MIT like the repository. No outside text or code was copied. The package continues an interrupted earlier attempt of the same generator assignment, which wrote the script, the tests and the documents and stopped before its manifest and this note. That attempt is kept byte for byte in `packages/verify_fold_group_separation/earlier-attempt-20260924T0102Z.tar.gz`. This run reviewed every line, added one test, extended three, and wrote the manifest and this note.

Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `examples/29_intelligence_service/starter-catalogue/bodies/audit_data_splits_for_errors_and_leakage.md`: the served prose method whose first check is that no entity appears in more than one split. This package turns that check, and the label balance of each fold, into code that any fold file can be run through.

## Inputs and outputs

Inputs: `--folds` and optionally `--train` below `--root` (default the current folder), or `--bundle` with the members `folds` and `train`; `--group-column`; `--id-column` or `--row-column` when a training file is given; optional `--fold-column` (default `fold`), `--label-column`, `--label-tolerance` (default 0.05), `--label-bins`, `--expected-folds`, `--delimiter`, `--max-examples`, `--no-values` and `--max-bytes` (default 64 MiB, refused above it). Output: one JSON object with `status`, the SHA-256 digest of each file, `summary` (rows per fold, groups, groups in two folds, rows in split groups, groups per fold, the largest label share gap), label shares by fold, `checks`, `failed_checks` and bounded `violations`.

## Effects

`reads_fs`: the script reads the named files and refuses `..`, paths outside `--root` (also through a symbolic link), non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples, send other inputs on standard input and write no file.

## Closest existing items

- `build_group_stratified_folds` (wave 5, a02): builds folds and checks its own output. This package builds nothing and checks any fold file independently, whoever made it, as the specification asks for this pair. A cross-check on this machine, in a scratch folder outside the package: the a02 builder made 5 group folds for a synthetic table of 181 rows and 60 customers, and this script passed them with no group in two folds and a largest label share gap of 0.021; the same rows with random folds failed with 47 customers in two folds.
- `audit_data_splits_for_errors_and_leakage` (served, prose): the question set behind the check. No executable part.
- `leakage_reviewer` (wave 5, a05): a read-only subagent that reads feature and validation code for leakage and cites file and line. This package reads no code; it checks the fold file that the code produced and answers with counts.

## Positive example

`examples/group-folds-bundle.json` with `--id-column id --group-column patient --label-column target --expected-folds 3`: 24 visits of 12 patients in three folds of 8 rows, each patient in one fold, and the label share 3 of 8 in every fold. The verdict is pass with a largest label share gap of 0.

## Known-wrong example

`examples/known-wrong-bundle.json` holds the same visits split by a plain stratified assignment. The label share is 3 of 8 in every fold, so the folds look balanced, but 11 of the 12 patients have visits in two folds. The script fails `group_in_two_folds` for 11 groups. Further known-wrong cases in the tests: rows without a fold, rows in two folds, unknown rows, a fold record with an empty id, a gap in row numbers, an empty group, a group copy that differs, a label share gap, numeric labels whose bins sit in one fold, fold values `1` and `1.0` counted as two folds, and a wrong fold count.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/verify-fold-group-separation/`, `.agents/skills/verify-fold-group-separation/` (Codex), `.opencode/skills/verify-fold-group-separation/`, `.pi/skills/verify-fold-group-separation/` and `.gemini/skills/verify-fold-group-separation/`. Basis: specification section 6 marks the first four skill folders observed on this machine and the Gemini CLI folder documented in `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`. No harness binary was run for this package. Unverified: whether each harness tells the model the folder path it needs for `SKILL_DIR`, and whether a harness asks for permission before `python3` runs from a skill folder. The command starts the first `python3` on `PATH`; a host that runs unattended should bind a trusted interpreter.

## Customer requests

- "Make sure no customer ends up in both training and validation in my five folds."
- "Check this folds.csv from last night's run before I trust the cross-validation score."
- "Are the label shares in each fold close to the whole data set?"

## Limits

The script checks the one group column it is given. Two columns that describe one entity need two runs, and a link through a third table is invisible to it. It does not check time order. Fold values are compared as exact text. A label with more than 50 values is refused unless `--label-bins` is given, and bins over tied values can be uneven. Label shares count rows with a label; empty labels are counted apart. Checks that failed before they passed: the first mutation pass ran 25 changes of the script against the earlier tests and 4 were not caught (a fold record with an empty id, the bin edges of a numeric label, row number 0, and the size bound on a named file). One test was added and three were extended, and each of the 25 changes now fails a named test. The suite holds 19 tests and passes under Python 3.14 and 3.10.
