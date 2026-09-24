# Review note: Treat raw data files as read-only

Candidate only. Not approved, staged, served or published.

Identity `raw_data_stays_read_only`, native name `raw-data-stays-read-only`, wave 5 assignment `a08_path_scoped_rules`, file class `rules_file`, version 0.1.0. Producer: the Claude Code wave 5 generator for this assignment, model family `anthropic`. This text is the repaired version of round 2, written after the wave critic's findings of 2026-09-23. This note is for reviewers. It is never delivered to a harness.

## Method

One path-scoped rule, rendered in four native rule formats that share one identical body. The rule loads when the harness works in a raw data folder, and it covers data files only: source code that happens to sit in a folder named `raw` is outside it. It forbids editing, overwriting, sorting, renaming or deleting raw data files. The four steps:

1. Record one checksum of the whole raw folder, subfolders included: `find data/raw -type f -exec sha256sum {} + | sort -k 2 | sha256sum`, with the task's raw folder, such as `input`, in place of `data/raw`, and `shasum -a 256` in both places on macOS. The result is one line, so a small model compares one value even when the folder holds thousands of files.
2. Write each result to a new file in the output folder the task names, else in `data/processed/`, and never overwrite a file the step did not create.
3. Beside each output, write a change log such as `changes.jsonl`, one line per change with its `rule`: a changed cell has `row`, `column`, `before` and `after`; a dropped row has `"change": "row_removed"` and `row`. Rows count from 1 after the header.
4. Run the checksum command again; it must print the first result. Report both results.

The rule tells the model to stop and report when the task asks for a change to a raw file itself, when a raw file is missing or unreadable or the checksum changed, when no output folder may be written, and when a needed tool can only change files in place.

The failure it targets: a small model cleans a table by writing the result back to the path it read, for example with a data frame's save call on `data/raw/train.csv`. The original values are gone, and a wrong cleaning rule found later cannot be repaired from the source.

## Authoring basis and sources

Original text written for this package from general data handling practice. No text or code was copied from an outside project.

Repository grounding at revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `src/loop_engine/code_nodes/database_copy.py`: the repository copies a table with corrections and never in place. It refuses a target that is the source or that already exists, and it compares the source digest before and after the copy. The rule's checksum check and its instruction never to overwrite a file the step did not create carry that behavior into any step, whatever tool does the cleaning.
- `examples/29_intelligence_service/starter-catalogue/bodies/copy_a_table_with_corrections_never_in_place.md`: the served item that describes that function (see Closest existing items).

Placement basis: the same research files as the other four rules in this assignment (`docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`, `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`, section 6 of the wave specification), plus the official pages the repairer read on 2026-09-24: Claude Code's memory page (code.claude.com/docs/en/memory), Cline's rules page (docs.cline.bot/features/cline-rules), Cursor's rules page (cursor.com/docs/context/rules) and GitHub's page on repository custom instructions (docs.github.com). These were documentation reads, not observations of native loading.

## Inputs and outputs

Input: the path the harness is working on. Four patterns, the same in every variant: `**/raw/**`, `**/raw_data/**`, `**/data/external/**` and `input/**` (a top-level input folder only, because a nested `input/` folder is often source code, such as a user interface component). Round 2 changed no pattern.

Output: behavior. A step that follows the rule writes new output files, a change log beside each, and a final report with the two checksum results.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The steps tell the model to read raw files, to write outputs and change logs to new paths, and to run `find`, `sort` and `sha256sum` (or `shasum -a 256` on macOS). The package holds no code. The checker detects the shell block; the file read and write effects are declared from the text of the steps.

## Closest existing items

- `copy_a_table_with_corrections_never_in_place` (served starter item, named in the assignment): a procedure that restates one repository function. It applies declared corrections and an accepted dedupe proposal while copying a delimited file or SQLite table, and returns a manifest with source digests and outcome counts. Difference: this package is a short path-scoped rule that loads whenever the harness touches a raw folder, in any step and with any cleaning tool. It defines no corrections, no dedupe and no manifest; it forbids in-place changes, names where outputs go, requires a change log and gives a folder checksum a small model can compare.
- Wave 5 neighbors, kept distinct as section 14 of the specification requires: `cleaning_apply_packet` (a10) is a whole step that applies the accepted rules of a cleaning plan to a copy; `verify_cleaned_copy_change_log` (a15) is a check that compares source, copy and change log by row key; `data_step_scoped_write_settings` (a13) protects raw data at the permission level. This rule applies no rules, verifies no log and sets no permission.
- Change log alignment, confirmed in round 2: the a10 step writes one JSON line per changed cell with `row` (counted from 1 after the header), `column`, `before`, `after` and `rules`. The a15 verifier, written after the producer's round, reads `row` or `key`, `column`, `before` and `after`, allows other members such as `rule`, and needs `"change": "row_removed"` for a dropped row. The predecessor's step 3 described a dropped row as a line with row, column, before, after and a reason; a line written that way (`"column": null` and the row values in `before`) made the a15 verifier refuse the whole log with exit 2 (`log_invalid`). Step 3 now names the `row_removed` shape, and the same verifier passed a log written as step 3 says (exit 0, status `pass`).
- Outside staged rules: none of the 445 rule titles concerns raw or input data; the nearest are data engineering and data modeling conventions for named products.
- Duplicate check after round 2: the highest five-word shingle similarity of this package's model-facing text with the 225 first-party bodies and the other 74 wave 5 packages is 0.005 (with `applied_migrations_stay_unchanged`). The checker warns at 0.5 and refuses at 0.8.

## Positive example

Repairer trial R-pos, round 2, in a Bubblewrap sandbox with no network (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-output-1.txt` in the wave folder). `data/raw/customers.csv` holds three rows, one with the city value `  lima` and one test account row, and `data/raw/2024/orders.csv` sits in a subfolder. The model records the folder checksum, writes `data/processed/customers.csv` with the city trimmed and title-cased and the test row dropped, and writes `data/processed/changes.jsonl` with one cell line and one `row_removed` line. The second checksum equaled the first (`9ae94874...`), and the `shasum -a 256` form gave equal results as well. The a15 verifier, bound read-only, read the three files with `--key customer_id` and passed them (exit 0).

## Known-wrong example

- R-kw1, the critic's case R1: a file in `data/raw/2024/` is edited in place. The predecessor's command, `sha256sum data/raw/*`, printed "Is a directory" for the subfolder and equal results before and after, so the old check passed. The repaired folder checksum differs, so the rule sends the model to a stop report.
- R-kw2, the critic's case R2: a competition layout `input/demo-competition/train.csv` is sorted in place. `sha256sum input/*` checksummed no file at all and passed. The repaired checksum differs.
- The producer's round showed why the check uses checksums and not git: with `data/raw/` listed in `.gitignore`, as raw data often is, `git status --porcelain -- data/raw` printed nothing after an in-place change. The transcript is in `review/PRECHECKS.txt`.

## Harness placement and verification state

| Harness | Destination | Activation front matter | Basis |
|---|---|---|---|
| Claude Code | `.claude/rules/raw-data-stays-read-only.md` | `paths` list | documented: research file, and the official memory page read on 2026-09-24 |
| Cline | `.clinerules/raw-data-stays-read-only.md` | `paths` list | documented: research file, and the official rules page read on 2026-09-24 |
| Cursor | `.cursor/rules/raw-data-stays-read-only.mdc` | `description`, `globs`, `alwaysApply: false` | documented: official rules page read on 2026-09-24; kept in `unverified_targets` |
| Copilot | `.github/instructions/raw-data-stays-read-only.instructions.md` | `applyTo` | documented: official GitHub page read on 2026-09-24; kept in `unverified_targets` |

The licence goes to `.baltor/raw-data-stays-read-only/LICENSE` for every harness. `wave5.unverified_targets` keeps Cursor and Copilot, now with reasons that cite the official pages and say what stays unverified.

Unverified harness behaviors:

1. Native loading was not observed for any of the four harnesses. No harness binary was run.
2. Cursor's documented example puts a space after each comma in `globs`; this package writes none. How Cursor splits the value was not tested.
3. On GitHub.com, only Copilot cloud agent and Copilot code review read path-specific instruction files, according to GitHub's page.
4. When each harness loads a rule. This matters more here than for code rules. Claude Code documents a load when Claude reads a matching file, so a data step that reads raw files only through a script it runs in a shell may never load the rule. A permission setting such as the a13 fragment stays the enforcement.
5. Whether a leading `**/` matches zero folders in each harness's glob engine. Python 3.14 `PurePath.full_match` matched all 6 intended sample paths and kept all 5 unrelated paths out (for example `src/rawhide.py` and `src/components/input/Input.tsx`).

## Customer requests

- "My agent overwrote the original CSV while cleaning it. Make it always write a cleaned copy."
- "Keep data/raw read-only for Claude and Cursor and log every change it makes."
- "Rule for our data folder: never touch the input files, outputs go to processed with a change log."

## Limits

- The rule is guidance, not enforcement. Pair it with a write guard or with read-only permissions on the raw folder.
- The folder checksum takes time on very large raw folders. It covers every file, including hidden files that an operating system may add, such as `.DS_Store`; such a file changes the checksum without any data change, and the rule then stops and reports.
- The patterns still match a code folder named `raw`; the body now says that code there is outside the rule, but the rule text is loaded.
- The change log shape follows the a10 step and the a15 verifier as they stand in this wave; both are candidates, so the integrator should keep the three in step.
- The rule does not decide what counts as source data beyond the patterns and the task's own words.
- The commands assume a POSIX shell such as bash or zsh.

### Pre-check and review history

- Producer round: the first draft held 253 words, over the 250-word limit, and was tightened; after checker run 1 had passed, the change log example was aligned with a10 and the package was filled and checked again. Checker runs 1 to 3 passed the wave gate with one warning: `reads_fs` and `writes_fs` are declared from the text of the steps and are not found in code.
- Critic round (2026-09-23, recommendation repair): (1) `sha256sum data/raw/*` does not descend into subfolders, so an in-place edit of a nested file passed; (2) with `input/<dataset>/train.csv` the command checksummed no file; (3) `**/raw/**` also matches code folders; (4) not blocking: Claude Code loads a path rule only when Claude reads a matching file; (5) minor: the Cursor and Copilot keys are documented officially.
- Repair round 2 (2026-09-24): one recursive folder checksum with its macOS form (findings 1 and 2), a data-files-only scope sentence (finding 3), the loading note kept above with the documented trigger (finding 4), and reasons that cite the pages read on 2026-09-24 (finding 5). The repairer also aligned the dropped-row line with the a15 verifier, as described under Closest existing items. The first round 2 draft held 289 words; it was tightened to 250 without removing a step, a check or a stop case. Every checker run of both rounds is listed in `review/PRECHECKS.txt`, and every report is kept as a `precheck-*.json` file beside this note.
