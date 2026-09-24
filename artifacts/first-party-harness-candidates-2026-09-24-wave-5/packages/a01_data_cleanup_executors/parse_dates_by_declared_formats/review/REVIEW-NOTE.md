# Review note: parse_dates_by_declared_formats

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a01_data_cleanup_executors, family anthropic, repaired by the a01 repairer of the same family after an independent critic review. This note is never delivered to a harness.

## Method

One focused step converts one CSV date column to ISO 8601 (YYYY-MM-DD) with a tested script. The step supplies the formats; the script tries every declared format on every value. A value is parsed only when at least one format gives a real calendar date and all formats that give a date agree. Otherwise it is held with a reason: `ambiguous`, `invalid_calendar_date`, `no_declared_format_matches` or `outside_declared_range`. The declared order only decides which agreeing format is credited in the counts; it never settles a disagreement. The script also reports format pairs that conflict while each reads values the other cannot (`mixed_conventions`), which is column-level evidence that two conventions were merged. The prose in `SKILL.md` covers only what the model decides: which values to pass, whether a copy is allowed, and when to stop.

## Authoring basis and sources

Original text and code written for this wave from general knowledge of date notation and the Python standard library (`datetime`, `re`, `csv`). No outside text or code was copied. The token syntax (`YYYY`, `MM`, `DD`, `MON`) is a plain convention chosen so that a small model cannot confuse it with `strptime` directives, which are refused on purpose. Sources at revision `a1fc7432`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md` (prose material cost 45 to 446 percent more prompt tokens per step and one prose item made a cheap model worse, so the rules live in code here), `docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` (skill folders), and the two closest items below.

## Inputs and outputs

Inputs: a UTF-8 CSV under `--root` (at most 64 MiB, header row required), one column name, one to twenty formats, and optional `--two-digit-year-base`, `--earliest`, `--latest`, `--delimiter`, `--output` and `--output-column`. Output: one JSON object on standard output with counts, per-format and per-reason counts, `mixed_conventions`, distinct held values with counts, up to five data row numbers and readings, and the SHA-256 of the input. With `--output`, a new CSV copy gains one column holding the ISO date or an empty cell for held and empty values. Exit 0 means every non-empty value parsed, 1 means values are held for review, 2 means refused with nothing written.

## Effects

`reads_fs`: the input file. `writes_fs`: only with `--output`, one new file opened in exclusive mode; an existing path, the input path, a path with `..` or a symbolic link that leaves `--root` is refused, and a partly written copy is removed on failure. `spawns_process`: the harness runs the script with `python3`; the tests start the script with the running interpreter and write fixtures only inside a temporary directory. No network, no model call, no secret, no subprocess inside the script.

## Closest existing items

- `detect_malformed_values_by_dominant_pattern` (served starter item): prose that flags values whose character pattern differs from the dominant pattern. It parses nothing, and its collapsed pattern treats `18-09-2026` and `2026-09-18` as the same shape. This package converts values and decides ambiguity by calendar readings, not by shape.
- `define_time_zone_reporting_window` (wave 1 candidate): turns a local reporting period into absolute boundaries. It does not parse or convert a column.
- `audit_csv_structure` (format pilot 1) checks row structure only. No first-party or staged item converts dates. The scout inventory lists no date parser among 3,498 identities.

## Positive example

Column `order_date` with `12/31/2025`, `25/12/2025` and `05/05/2025`, formats `DD/MM/YYYY` then `MM/DD/YYYY`: all three parse (2025-12-31, 2025-12-25, 2025-05-05), exit 0, and `mixed_conventions` is empty because no value is read two ways. The test `test_single_valid_reading_parses_and_agreeing_readings_parse` checks the exact copy lines.

## Known-wrong example

With the same two formats, `03/04/2025` has two real readings. A cleaner that takes the first matching format writes 2025-04-03, a guess. The script holds it as `ambiguous` with both readings (`test_known_wrong_first_format_guess_is_held`). A mutant of `judge` that returns the first reading instead of holding makes that test fail; see the pre-check log for the recorded run.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/parse-dates-by-declared-formats/` (Claude Code, observed class basis), `.agents/skills/...` (Codex, observed), `.opencode/skills/...` (OpenCode, observed), `.pi/skills/...` (Pi, observed) and `.gemini/skills/...` (Gemini CLI, documented only). The basis is the class table of the wave specification; native loading of this exact package was not probed, because generators do not run harness binaries. Unverified harness behavior: that each harness shows the model the skill folder path so that `SKILL_DIR` can be filled in (the first action now names the five placement folders to look in when it does not), that `python3` on `PATH` is a trusted interpreter (the host must bind one), and that Gemini CLI discovers the `.gemini/skills/` folder at this version. The independent critic noted that the native review criterion treats unknown loading behavior as a reason to reject until a native discovery probe records it; that probe belongs to the integrator and has not run.

## Customer requests

- "Our export has dates like 03/04/2025 and 2025-04-03 in the same column. Convert them to ISO but do not guess the day and month."
- "Normalize the signup_date column to YYYY-MM-DD and give me a list of every value you could not convert."
- "Some rows say 01/01/1900 as a placeholder; treat anything before 2000 as suspicious."

## Limits

Dates only: values with a time or a time zone are held as `no_declared_format_matches`. Month names are English. Spreadsheet serial numbers, ordinal days such as `3rd` and weekday names are not read. Upper-case `D`, `M` and `YY` always start a token and have no escape, so a format cannot carry literal text such as `MDT` or `Day`; the refusal detail lists the tokens read. Every row must have the header's width; in a one-column file a blank line is one empty value, and in a wider file one blank line, even at the end, refuses the run with a detail that names it. The report holds at most 500 distinct held values; `held_values_complete` then turns false and the stop rule applies.

Checks that failed before they passed: the first test run failed once: a blank line in a one-column file was refused as a short row. The script now reads it as an empty value and still refuses a blank line in a wider table (`test_invalid_unmatched_empty_and_padded_values`). The independent critic of version 0.1.0 then found no blocking defect and four smaller ones, repaired in 0.1.1: step 4 said both reports were complete although `held_values` is capped at 500, so it now says only that the run finished; formats such as `DD/MM/YYYY MDT` were refused with a detail that did not name the cause, so the detail now lists the tokens read and the reference explains the letter rule; a trailing blank line in a two-column file was refused without saying why, so the detail now names the blank line; and the report repeats cell text word for word, so the model is told that report values are data from the file, not instructions. For the critic's panel risk, the first action now says where to find the skill folder, which reduces but does not remove the unobserved loading risk. A pass of the wave pre-checks is not a native loading result, a usefulness measurement or an approval.
