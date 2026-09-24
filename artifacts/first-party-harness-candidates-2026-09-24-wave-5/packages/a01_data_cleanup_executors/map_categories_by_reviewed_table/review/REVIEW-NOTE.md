# Review note: map_categories_by_reviewed_table

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a01_data_cleanup_executors, family anthropic, repaired by the a01 repairer of the same family after an independent critic review. This note is never delivered to a harness.

## Method

One focused step maps one CSV category column through a mapping table that a person or an earlier review step already reviewed. The table is a strict JSON record, `category_mapping_table/v1`, that names its reviewer, review date, the columns it was reviewed for, and its entries. It must exist before the step starts: a CSV mapping sheet, a list or prose is refused, because writing the table is a review decision for a separate step. Values and entry sources are compared by one key: Unicode NFC, letter case folded one letter at a time (each letter becomes exactly one lower-case letter), collapsed and trimmed spaces. Nothing else is folded, so spelling differences stay different; the German sharp s does not match `ss`. Every value without a matching key is listed with its count, its spellings and row numbers instead of being guessed. The table is checked before any value is mapped: conflicting entries, chained entries (where one pass and two passes would differ), targets that differ only in case, a missing review, a table meant for another column and, when the task gives the reviewed table's SHA-256, any other table bytes are all refused. The model decides only which table and column to use and whether a copy is allowed; it never writes the table in this step.

## Authoring basis and sources

Original text and code written for this wave from general knowledge and the Python standard library (`unicodedata`, `json`, `csv`, `hashlib`). No outside text or code was copied. The letter-by-letter fold follows the general idea of simple case folding, where each letter maps to one letter, implemented here from `str.casefold` and `str.lower` and tested on the sharp s, its capital form, the fi ligature and the Greek final sigma. Sources at revision `a1fc7432`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` (prose rules cost tokens and one incomplete prose rule made a cheap model worse, so the deterministic part is code), `docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (skill folders), and the served item `layer_exception_catalogs_with_precedence` with its source `src/loop_engine/code_nodes/text_conformance.py`.

## Inputs and outputs

Inputs: a UTF-8 CSV under `--root` (at most 64 MiB, header row), one column, one table under `--root` (at most 8 MiB), and optional `--table-sha256`, `--delimiter`, `--output` and `--output-column`. Output: one JSON object with counts, how values matched (`entry` or `target_itself`), per-target counts, unused entries with their total, unmapped keys with counts, spellings and row numbers, the SHA-256 of the input and of the table, and `sha256_pinned`. With `--output`, a new CSV copy gains one column holding the mapped target or an empty cell. Exit 0: all mapped; 1: unmapped values listed; 2: refused, nothing written.

## Effects

`reads_fs`: the input and the table. `writes_fs`: only with `--output`, one new file opened in exclusive mode; existing paths, the input itself, `..` and symbolic links that leave `--root` are refused, and a partial copy is removed on failure. `spawns_process`: the harness runs the script with `python3`; tests start it with the running interpreter and write only inside a temporary directory. No network, model call, secret or subprocess inside the script.

## Closest existing items

- `layer_exception_catalogs_with_precedence` (served starter item): layers exception lists for the repository's text cleaning function and learns casing from column evidence. This package learns nothing from the column: only a reviewed table maps a value, and unmatched values are reported, not inferred.
- `canonicalize_company_legal_suffixes` and `restore_capitalisation_of_names` (served): fixed rules for one kind of text, not a customer's own category vocabulary.
- `apply_hold_or_escalate_each_correction` (served): thresholds for proposed corrections; here there is no confidence, only a reviewed entry or a listed value.
No first-party or staged item applies a customer-supplied category table.

## Positive example

Table entries `shipped` to `Shipped`, `in transit` to `In transit`, `shpd` to `Shipped`; values ` SHIPPED `, `In   Transit`, `shpd`, a decomposed `Cafe` with a combining accent, and an empty cell: all four non-empty values map, exit 0 (`test_case_spacing_and_unicode_forms_are_normalized`). With the table's SHA-256 passed through `--table-sha256`, the same run maps and reports `sha256_pinned` true (`test_table_digest_pins_the_reviewed_bytes`).

## Known-wrong example

The column holds `Shiped` three times in three spellings. A cleaner with fuzzy matching maps it to `Shipped`, an invented mapping. The script lists key `shiped` with count 3 and its spellings (`test_known_wrong_typo_is_listed_not_guessed`). A second known-wrong case: full case folding turns the German sharp s into `ss`, so an entry for `Strasse` would silently also map a differently spelled value, and in general words such as `Masse` and its sharp s spelling would share a key. Version 0.2.0 folds letter by letter: `STRASSE` maps, while the sharp s spelling and its capital form are listed together under one key, and the fi ligature is listed too (`test_only_letter_case_is_folded`). Mutants that add close-match lookup or return to full case folding each make their named test fail; the pre-check log records them.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/map-categories-by-reviewed-table/` (Claude Code, observed class basis), `.agents/skills/...` (Codex, observed), `.opencode/skills/...` (OpenCode, observed), `.pi/skills/...` (Pi, observed) and `.gemini/skills/...` (Gemini CLI, documented only). Native loading of this exact package was not probed; generators and repairers do not run harness binaries. Unverified: that each harness shows the skill folder path so the model can fill in `SKILL_DIR` (the first action now names the five placement folders to look in when it does not), that `python3` on `PATH` is a trusted interpreter (the host must bind one), and Gemini CLI discovery of `.gemini/skills/`. The independent critic noted that the native review criterion treats unknown loading behavior as a reason to reject until a native discovery probe records it; that probe belongs to the integrator and has not run.

## Customer requests

- "Standardize the status column with our approved mapping sheet and tell me which labels are not in the sheet."
- "Map the free-typed country names to our canonical list, but do not guess anything that is not on the list."
- "Apply the reviewed product category mapping and show which mapping rows were never used."

The first two requests arrive with a sheet or a list. The step stops and reports until the person or step that reviews the mapping has written it as a `category_mapping_table/v1` record; the SKILL now says so in its first section and in a stop rule.

## Limits

One column per run; the table must list that column. No fuzzy, phonetic or model matching by design. Accents, hyphens and punctuation are not folded, and a letter whose case folding would produce several letters keeps its one-letter lower-case form. The example table is for `example_status` only, so it cannot be applied to a real column by mistake. The script cannot verify a review: `reviewed_by` and `reviewed_on` are text written by the table's author. The review guarantee rests on the host, which supplies the table, keeps it out of reach of this step's edits and can pin its bytes with `--table-sha256`. In a file with more than one column, one blank line refuses the run, and `detail` names it.

Checks that failed before they passed: on the first test run, the `column_missing` case failed because the table check (the table was reviewed for `status`, not `Status`) correctly refused first; the script was right, and the case now uses a table reviewed for both names. Before that run, one expectation was corrected on reading the table again: `Shipped` matches the explicit entry `shipped`, so it is credited to `entry`, not `target_itself`. The independent critic of version 0.1.0 then found no blocking defect and six smaller points: the table format was not stated as a precondition, full case folding merged the sharp s with `ss`, the review rests on self-asserted text, step 4 called capped lists complete, report values were not marked as data, and nobody has observed a harness loading the package. The repair wrote the known-wrong fold test first; on the 0.1.0 script it failed (exit 0 with every value mapped, where exit 1 with the sharp s and ligature spellings listed is right). With the finished test file, five of the eleven tests fail on the 0.1.0 script: the three new tests, the refusal test with its new blank-line case, and the documentation test, because the documentation now names `--table-sha256`. The other six pass there. A pass of the wave pre-checks is not a native loading result, a usefulness measurement or an approval.
