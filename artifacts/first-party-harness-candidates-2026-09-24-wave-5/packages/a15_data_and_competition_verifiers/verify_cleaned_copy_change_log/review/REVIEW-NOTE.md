# Review note: Verify a cleaned copy against its change log

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a15_data_and_competition_verifiers, model family anthropic. This note is never delivered to a harness.

## Method

One verifier method. The script `scripts/verify_change_log.py` reads the source table, its cleaned copy and the change log that the cleaning step wrote. It matches rows by the key columns named with `--key`, compares every cell of the columns both tables have as exact text, and checks each difference against the log in both directions: every changed cell, removed row, added row, removed column and added column needs a matching entry, and every entry must match both tables (`before` equals the source cell, `after` equals the cleaned cell, a removed row is really gone, an added row is really new). A logged change of a key column moves the match to the new key. Seventeen named checks, plus an optional digest check of the source, give one JSON verdict. Exit 0 is pass, 1 is fail, 2 is refused input. A source key that is empty or repeats is refused, because rows cannot be matched. The checklist asks what code cannot judge: whether each logged change was allowed.

## Authoring basis and sources

Original text and code written for this wave, MIT like the repository. No outside text or code was copied. The package continues an interrupted earlier attempt of the same generator assignment, which wrote the script, the tests and the documents and stopped before its manifest and this note. That attempt is kept byte for byte in `packages/verify_cleaned_copy_change_log/earlier-attempt-20260924T0102Z.tar.gz`. This run reviewed every line, added two tests, extended a third, and wrote the manifest and this note.

Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `examples/29_intelligence_service/starter-catalogue/bodies/copy_a_table_with_corrections_never_in_place.md` and `src/loop_engine/code_nodes/database_copy.py`: the repository copies a table with corrections and returns a manifest with digests, row counts, dropped identities and outcome counts per column. It records no per-cell log, and nothing checks a copy that another tool made. This package is that independent check.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: the study graded cleanup with an independent deterministic scorer; this package gives a customer a comparable check on their own cleanup, and keeps the entry text short because the study measured the cost of long material.

## Inputs and outputs

Inputs: `--source`, `--cleaned` and `--log` below `--root` (default the current folder), or `--bundle` with the members `source`, `cleaned` and `log`; one `--key` for each key column; optional `--source-sha256` with the digest recorded before cleaning, `--delimiter`, `--max-examples`, `--no-values` and `--max-bytes` (default 64 MiB, refused above it). The log may be JSON Lines, one JSON array or a CSV file; `references/log-format.md` defines the members. Output: one JSON object with `status`, the three SHA-256 digests, `summary` (rows matched, removed and added, cells compared and changed, column and row order), `checks`, `failed_checks`, bounded `violations` and two warning counts.

## Effects

`reads_fs`: the script reads the three named files and refuses `..`, paths outside `--root` (also through a symbolic link), non-regular files, one file given as both source and copy, and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples, send other inputs on standard input and write no file.

## Closest existing items

- `copy_a_table_with_corrections_never_in_place` (served, prose restating repository code): produces a corrected copy and a summary manifest. This package produces nothing; it checks a copy and a per-change log after the fact, cell by cell.
- `apply_hold_or_escalate_each_correction` (served, prose): decides each correction. No check of the result.
- `reconcile_snapshot_changes` (first-party wave candidate, prose): classifies added, removed and changed records between two complete snapshots. It has no executable part and checks no change log.
- Wave 5 neighbours, kept distinct as the specification asks: `raw_data_stays_read_only` (a08) is a rule, `cleaning_apply_packet` (a10) is the step that applies approved rules, and this package is the check that runs after it.

## Positive example

`examples/cleaning-bundle.json` with `--key customer_id`: three logged cell fixes (two trimmed spaces and one reviewed country name) and one logged removal of the repeated row `C-0042`. The verdict is pass with 5 rows matched, 1 removed and 3 cells changed.

## Known-wrong example

`examples/known-wrong-bundle.json` holds the same source and a copy that also lost `C-0042` and turned `N/A` into an empty `phone` cell for `C-0007`, with a log that names only the three cell fixes. The script fails `row_removed_without_log` for `C-0042` and `cell_changed_without_log` for `phone` of `C-0007`. Further known-wrong cases in the tests: log values that match neither table, claims about rows that do not hold, wrong column claims, repeated log entries, colliding key changes, repeated or empty keys in the copy, and a source digest that differs.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/verify-cleaned-copy-change-log/`, `.agents/skills/verify-cleaned-copy-change-log/` (Codex), `.opencode/skills/verify-cleaned-copy-change-log/`, `.pi/skills/verify-cleaned-copy-change-log/` and `.gemini/skills/verify-cleaned-copy-change-log/`. Basis: specification section 6 marks the first four skill folders observed on this machine and the Gemini CLI folder documented in `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`. No harness binary was run for this package. Unverified: whether each harness tells the model the folder path it needs for `SKILL_DIR`, and whether a harness asks for permission before `python3` runs from a skill folder. The command starts the first `python3` on `PATH`; a host that runs unattended should bind a trusted interpreter.

## Customer requests

- "Prove that the cleaning step changed only what its log says it changed."
- "Did any rows disappear from the customer table during cleanup without a reason?"
- "Compare the raw file and the cleaned file and list every unlogged change."

## Limits

Cells are compared as exact text, so a change of number format (`12.50` to `12.5`) is a change that needs a log entry. Key values in a JSON log are strings; a numeric key is refused rather than guessed. Both tables must have a consistent number of fields per row. A CSV log can name rows of a key with several columns only by row number. A matching entry shows that a change was written down, not that it was right; the checklist carries that question. Checks that failed before they passed: the first mutation pass ran 36 changes of the script against the earlier tests and 4 were not caught (a repeated column entry, a repeated added-row entry, the size bound on a named file, and the specific message for a CSV key of several columns). Two tests were added and one was extended, and each of the 36 changes now fails a named test. The new repeated-entry test first failed in the test itself, because it sorted `None` beside text; the test was corrected, not the script. The suite holds 24 tests and passes under Python 3.14 and 3.10.
