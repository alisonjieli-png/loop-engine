# Review note: standardize_missing_value_tokens

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a01_data_cleanup_executors, family anthropic, repaired by the a01 repairer of the same family after an independent critic review. This note is never delivered to a harness.

## Method

One focused step empties the cells that hold a declared missing-value token, in declared columns only, with a tested script. A cell matches only when, trimmed of outer spaces, it equals a whole token, exactly or in any case with `--ignore-case`. Three guards carry the method. First, a token that could be real data (any digit, or a true or false word) is refused unless `--allow-value-token` names it a second time, so 0, false and -999 cannot be erased by one careless flag. Second, only named columns are touched unless the task asks for `--all-columns`. Third, cells that look like missing markers but were not declared, such as `NA` in a country column or `N/A` under a case-sensitive rule, are listed with counts and never changed. The prose leaves the model one decision: which tokens and columns the task declared.

## Authoring basis and sources

Original text and code written for this wave from general knowledge and the Python standard library. No outside text or code was copied. The look-alike list is a plain list of common spellings written for this package. Sources at revision `a1fc7432`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` (measured cost of prose rules), `docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (skill folders), the starter item `handle_missing_values_without_inventing_them`, and `src/loop_engine/code_nodes/text_conformance_operations.py`, whose `is_null_sentinel` detects a packaged sentinel list case-insensitively in order to skip those cells rather than to blank them.

## Inputs and outputs

Inputs: a UTF-8 CSV under `--root` (at most 64 MiB, header row), one or more `--column` names or `--all-columns`, one to fifty `--token` values, and optional `--ignore-case`, `--blank-whitespace-cells`, `--allow-value-token`, `--delimiter` and `--output`. Output: one JSON object with the rules as applied, per-column counts (cells, blanked by each token, whitespace blanked or kept, already empty, kept), totals, undeclared look-alikes with counts and row numbers, and the input SHA-256. With `--output`, a new CSV copy where only matched cells are empty. Exit 0: done, nothing to review; 1: done, look-alikes or space-only cells listed; 2: refused, nothing written.

## Effects

`reads_fs`: the input. `writes_fs`: only with `--output`, one new file opened in exclusive mode; existing paths, the input itself, `..` and symbolic links that leave `--root` are refused, and a partial copy is removed on failure. `spawns_process`: the harness runs the script with `python3`; tests start it with the running interpreter and write only inside a temporary directory. No network, model call, secret or subprocess inside the script.

## Closest existing items

- `handle_missing_values_without_inventing_them` (starter candidate): a prose method about keeping absent, empty and zero apart through a whole pipeline. This package executes one narrow rule of that method and adds the refusals that make it safe to run unattended.
- `profile_text_column_before_cleaning` (served): counts null markers as part of a profile and changes nothing.
- `apply_hold_or_escalate_each_correction` (served): thresholds for proposed corrections; there is no confidence here, only declared tokens.
No first-party or staged item blanks declared tokens.

## Positive example

Column `note` with `n/a`, an empty cell, `  N/A ` and a cell of three spaces, token `n/a`, `--ignore-case` and `--blank-whitespace-cells`: two cells are blanked by the token, one by the space rule, one was already empty, exit 0 (`test_ignore_case_and_whitespace_cells`).

## Known-wrong example

A cleaner treats 0, false and NA as missing in every column. The script refuses `0`, `false`, `FALSE`, `-999` and `1900-01-01` as tokens without the second declaration, leaves the undeclared `country` column alone, and lists `N/A` in `score` as a look-alike under a case-sensitive rule (`test_known_wrong_real_values_survive`). Mutants that drop the value-like guard, fold case always, or clean undeclared columns each make a named test fail; the pre-check log records them. The protection of the code NA holds only while NA is not declared for the country column: a declared token applies to every column the run cleans, so `--all-columns` with the token NA blanks both country codes, which `columns[].blanked_by_token` then shows (`test_a_declared_token_applies_to_every_cleaned_column`). The SKILL's known-wrong example and the reference now say so.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/standardize-missing-value-tokens/` (Claude Code, observed class basis), `.agents/skills/...` (Codex, observed), `.opencode/skills/...` (OpenCode, observed), `.pi/skills/...` (Pi, observed) and `.gemini/skills/...` (Gemini CLI, documented only). Native loading of this exact package was not probed; generators and repairers do not run harness binaries. Unverified: that each harness shows the skill folder path so the model can fill in `SKILL_DIR` (the first action now names the five placement folders to look in when it does not), that `python3` on `PATH` is a trusted interpreter (the host must bind one), that each harness passes `--token=-` to the script unchanged, and Gemini CLI discovery of `.gemini/skills/`. The independent critic noted that the native review criterion treats unknown loading behavior as a reason to reject until a native discovery probe records it; that probe belongs to the integrator and has not run.

## Customer requests

- "Blank out n/a, NULL and dashes in the survey answers, but do not touch zeros."
- "Our sensor file uses -999 for missing temperature readings. Clear those in the temperature column only."
- "Which columns still have things like unknown or N/A after cleaning?"

## Limits

Whole-cell matches only; a token inside longer text is left alone. The look-alike list is English and short by design. Tokens apply to every declared column in one run, and with `--all-columns` to every column; run again for columns with other tokens. In a file with more than one column, one blank line refuses the run, and `detail` names it. Checks that failed before they passed: on reviewing the fixture before the first run, one test expected exit 0 for `--all-columns`, but the two `NA` country codes are listed as look-alikes, so exit 1 is the intended result and the test was corrected; a whole-cell test was added after I noticed no test guarded substring matching. The independent critic of version 0.1.0 found no blocking defect and three smaller points: the known-wrong text did not say that NA is protected only while it is not declared for that column, report values were not marked as data, and nobody has observed a harness loading the package or passing `--token=-` unchanged. Version 0.1.1 adds the NA sentence to the SKILL and the reference with a test that shows the behavior, tells the model that report values are data from the file and not instructions, names the placement folders for `SKILL_DIR`, and names a blank line in a multi-column file in the refusal detail. One expectation of the new test was corrected before its first run: the `note` column holds look-alikes and a cell of spaces, so a run on it ends with exit 1; the first half of the test now uses the `id` column. A pass of the wave pre-checks is not a native loading result, a usefulness measurement or an approval.
