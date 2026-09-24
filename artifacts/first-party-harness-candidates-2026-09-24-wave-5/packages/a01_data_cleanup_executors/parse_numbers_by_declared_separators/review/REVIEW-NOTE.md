# Review note: parse_numbers_by_declared_separators

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a01_data_cleanup_executors, family anthropic, repaired by the a01 repairer of the same family after an independent critic review. This note is never delivered to a harness.

## Method

One focused step turns one CSV column of numeric text into exact decimal text with a tested script. The task declares the decimal mark, the grouping mark and style, the spellings of the column's one currency, the percent rule, and whether parentheses mean a negative number. The script reads each value only with those rules and holds everything else with a named reason. When the declared marks are the period and comma pair, it also reads every value with the two marks swapped. A value that only the swapped reading accepts is held as `other_convention` with that reading shown. One such value is evidence that the column mixes conventions: the report then sets `column_mixes_conventions`, and every value that both readings accept with different results, such as 2,500 (2500 or 2.500), is held as `convention_sensitive` with both readings and left empty in the copy. Without that evidence, such values are parsed and counted as `convention_sensitive_parsed`, or held when the task passes `--hold-convention-sensitive`. Numbers are computed with Python `decimal`, never binary floating point, and keep the scale as written (1,234.50 becomes 1234.50).

## Authoring basis and sources

Original text and code written for this wave from general knowledge of number notation and the Python standard library. No outside text or code was copied. Sources at revision `a1fc7432`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` (the measured cost of prose rules and the phone item whose incomplete written rule made a cheap model worse, which is why every rule here is executable and every uncovered case is held), `docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (skill folders), and the wave 1 candidates `trace-numeric-rounding` and `audit-measurement-units`.

## Inputs and outputs

Inputs: a UTF-8 CSV under `--root` (at most 64 MiB, header row), one column, `--decimal-mark` and `--grouping-mark` (both required), and optional `--group-style`, `--currency` (repeatable), `--percent-sign`, `--negative-parentheses`, `--allow-leading-zeros`, `--hold-convention-sensitive`, `--delimiter`, `--output` and `--output-column`. Output: one JSON object with counts, per-reason counts, `column_mixes_conventions`, the convention-sensitive count, currency spellings seen, distinct held values with counts, row numbers, offending characters or both readings, and the input SHA-256. With `--output`, a new CSV copy gains one column of canonical decimals (period mark, no grouping); held values stay empty. Exit 0: all parsed; 1: values held; 2: refused, nothing written.

## Effects

`reads_fs`: the input file. `writes_fs`: only with `--output`, one new file opened in exclusive mode; an existing path, the input itself, `..` and symbolic links leaving `--root` are refused, and a partial copy is removed on failure. `spawns_process`: the harness runs the script with `python3`; tests start it with the running interpreter and write only inside a temporary directory. No network, model call, secret or subprocess inside the script.

## Closest existing items

- `trace_numeric_rounding` (wave 1): reviews where rounding changes a total. It assumes values are already numbers; it parses nothing.
- `audit_measurement_units` (wave 1): checks units and conversions, not separators or currency marks.
- `detect_malformed_values_by_dominant_pattern` (served): would flag `1.234,56` in a column of `1,234.56` values by shape, but cannot convert either or say which reading is meant.
No first-party or staged item parses numeric text with declared separators.

## Positive example

Declared comma decimal mark, period grouping and the euro sign as the one currency spelling: `1.234,56` gives 1234.56, `0,5` gives 0.5, `12,50` followed by the euro sign gives 12.50 and `-3,00` gives -3.00, while `1,234.56` is held as `other_convention` and none of the parsed values has a second reading (`test_declared_european_marks`).

## Known-wrong example

Declared period decimal mark and comma grouping, value `1.234,56`. Deleting commas gives 1.23456. The script holds it as `other_convention` with `other_reading` 1234.56 (`test_known_wrong_other_convention_is_held_not_stripped`). In the same column, `2,500` and `3,000` are no longer read as 2500 and 3000: the column mixes conventions, so both are held as `convention_sensitive` with both readings and stay empty in the copy (`test_known_wrong_mixed_column_holds_values_both_conventions_read`). The pre-check log records a mutant for each of these guards; each makes its named test fail.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/parse-numbers-by-declared-separators/` (Claude Code, observed class basis), `.agents/skills/...` (Codex, observed), `.opencode/skills/...` (OpenCode, observed), `.pi/skills/...` (Pi, observed) and `.gemini/skills/...` (Gemini CLI, documented only). Native loading of this exact package was not probed; generators and repairers do not run harness binaries. Unverified: that each harness shows the skill folder path so the model can fill in `SKILL_DIR` (the first action now names the five placement folders to look in when it does not), that `python3` on `PATH` is a trusted interpreter (the host must bind one), and Gemini CLI discovery of `.gemini/skills/`. The independent critic noted that the native review criterion treats unknown loading behavior as a reason to reject until a native discovery probe records it; that probe belongs to the integrator and has not run.

## Customer requests

- "The amount column mixes 1,234.50 and 1.234,50. Convert it to real numbers and show me which rows you could not read safely."
- "Strip the dollar signs and thousands separators from price, and treat (45.00) as negative."
- "Our discount column says 12.5% in some rows; turn it into fractions like 0.125."

## Limits

No exponent notation, no trailing minus sign, no unit suffixes such as `kg`, and one currency per run. Letters in currency spellings match in any case; symbols must match exactly. A space may follow a leading currency but not a sign, so `- $5` is held as `space_after_sign`. The accounting layout `$(1,234.56)`, with the currency outside the parentheses, is held as `parentheses_misplaced`; `($1,234.56)` is read. One value written the other way is enough to hold every convention-sensitive value of the column; a column without such a value parses 1,000 as 1000 unless the task passes `--hold-convention-sensitive`. In a file with more than one column, one blank line refuses the run, and `detail` says why.

Checks that failed before they passed: the first test run expected `-(5)` to be held as `sign_repeated`, but it was held as a parentheses fault; the reason was split into `parentheses_not_declared` and `parentheses_misplaced`, and `(-5)` now covers `sign_repeated`. An earlier draft of the script and test also held literal non-ASCII characters (a minus sign the vocabulary check refuses); they are now written as named escapes. The independent critic then found a blocking defect in version 0.1.0 that every pre-check had passed: a column with `1,234.56`, `1.234,56`, `2,500`, `3,000` and `12,5` held the two values written the other way but still wrote 2500 and 3000 into the copy, and no step told the model to add the flag. A known-wrong check for that column failed on version 0.1.0 before the repair and passed after it. Version 0.2.0 also names two causes that 0.1.0 reported as `undeclared_character`: `space_after_sign` and `currency_misplaced`. A pass of the wave pre-checks is not a native loading result, a usefulness measurement or an approval.
