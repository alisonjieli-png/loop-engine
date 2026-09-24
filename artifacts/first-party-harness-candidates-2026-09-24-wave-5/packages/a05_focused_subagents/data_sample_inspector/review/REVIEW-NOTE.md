# Review note: Data sample inspector

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a05_focused_subagents, model family anthropic, repaired on September 24, 2026 by the a05 repairer of the same family after the a05 critic's review. This note is never delivered to a customer.

## Method

A subagent definition for a read-only helper that judges what the values of a data sample mean. For a CSV or TSV file it reads lines 1 to N+1, the header and N rows, where the caller's N is 50 by default and at most 200; for a JSON Lines file, which has no header line, it reads lines 1 to N and takes every key seen as a column. It never reads past line 201. It returns one JSON object with one entry per column: the likely type, each distinct format with one example, and suspicious values with their line numbers. It rereads every cited line before replying. The reply shape is fixed in `contracts/reply.schema.json`, so a caller or host can check it with any JSON Schema 2020-12 validator.

The judgment the helper adds is naming formats and spotting values that look wrong for a column: placeholders such as N/A, -999 or 0000-00-00, mixed decimal marks or units, unclear day and month order, values that break the type, and repeated identifiers. It does not count cells; that is a job for code. Stray spaces are invisible when reading, so in a delimited file it searches with line numbers for a space beside a separator or at a line end and keeps only matches within the lines it read. It never copies a value that looks personal or secret and writes its shape instead, such as `<email>`; with the caller option `values: masked` it writes only shapes, and the reply records which mode was used.

## Authoring basis and sources

Original text written for this wave. No outside text was copied. Sources at revision a1fc7432:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the file contract this package follows.
- `docs/guides/native-client-material-loading.md`: records the OpenCode project agent folder `.opencode/agents/<name>.md` as documented and observed with version 1.18.31.
- `examples/29_intelligence_service/starter-catalogue/bodies/profile_text_column_before_cleaning.md`: a starter body, described below.

The closest first-party candidates were read at `origin/main`: `artifacts/harness-intelligence-format-pilot-2026-09-22/context/profile-one-csv/` and `tools/audit-csv-structure/`, and the wave 5 package `packages/a07_local_data_tool_servers/csv_profile_server/` in this wave folder. Harness facts come from the installed Claude Code 2.1.281 and OpenCode 1.18.32 program text, read and not run, and from GitHub's custom agents documentation, read on September 24, 2026.

## Inputs and outputs

Input: one file path relative to the repository root, an optional row count (50 by default, at most 200) and the optional `values: masked`. Output: one JSON object matching the schema, or `{"refused": "..."}`. During the repair, the body example, the refusal and a masked JSON Lines reply validated against the schema with the `jsonschema` library, and five known-wrong replies were rejected: `rows_read` 500, a column with the removed count field `empty_in_sample`, a reply without `values`, a suspicious value on line 202, and an unknown `values` mode.

## Effects

`reads_fs` only. The helper reads the first lines of one file, searches that file for spaces next to separators, and rereads cited lines. The search tool scans the whole file, so its output can hold later lines, which the helper discards. It runs no command and writes nothing. Claude Code gets Read, Grep and Glob; OpenCode denies edit, bash, web, task, outside-folder access and reading `.env`, `.pem` and `.key` files; Copilot lists the documented `read` and `search` aliases. The reply carries format examples and suspicious values from the file into the main step, except values that look personal or secret, which are replaced by shapes, and every value when `values: masked` is given. Whether a small model recognizes every personal value is unmeasured, so a step that handles personal data should pass `values: masked`.

## Closest existing items

- First-party pilot candidate `profile_one_csv` is a step brief for a bounded CSV quality report: header duplication, inconsistent row widths and blank cells, other missing-value markers only when a supplied schema defines them, and disclosure levels (`aggregates_only`, `column_names_allowed`) that forbid row values. It writes a report file under a separately authorized output path. This helper writes no file, also reads JSON Lines, and names the meaning of values, such as a placeholder or an unclear date order, which that brief leaves to a schema.
- First-party pilot candidate `audit_csv_structure` is a tested script that audits the structure of a whole CSV or TSV file: malformed rows, duplicate headers and inconsistent field counts, with no row values. It explicitly does not infer types or meaning. This helper infers types and meaning on a sample and does not check structure.
- Wave 5 `csv_profile_server` (a07) is a local protocol server whose tool computes, in code, inferred types, empty and distinct counts, the most common values, character shapes and the values that break the dominant type, with an option that hides every data value. It is the better tool for counts and type checks, and this helper leaves counting to such a tool. What this helper adds is judgment that type checks do not make: a value such as -999 or 0000-00-00 passes an integer or date check but is a placeholder, 04/03/2025 is a valid date whose day and month order is unclear, and mixed units or decimal marks are named as formats with examples. It also works in a step that has only reading tools and no protocol server, and it reads JSON Lines.
- Starter `profile_text_column_before_cleaning` profiles one text column with counts and proposes cleaning rules. This helper describes every column of a bounded sample with cited examples and proposes no rules. Wave 5 `cleaning_plan_packet` (a10) plans rules for one table; this helper only observes.

## Positive example

`data/orders.csv` has an `order_date` column with `2025-03-04` on most lines, `04/03/2025` on line 9 and `0000-00-00` on line 17. The reply lists two formats with examples, `likely_type: date`, and line 17 as a placeholder date. For `data/events.jsonl`, whose lines have the keys `id`, `email` and, on some lines only, `coupon`, the reply has three columns, and with `values: masked` every example is a shape such as `<email>`.

## Known-wrong example

A small model reads the first ten lines, sees integers in `amount`, and reports `likely_type: integer` with no suspicious values. Line 23 holds `12,50` and line 31 holds `-999`. Reading the requested 50 rows and citing each suspicious value by line catches both. A second wrong case: the model reports `rows_read: 50` for a file it read to line 20; the rows count must be the rows actually read. A third: a JSON Lines file refused because it "has no header line"; the refusal now applies only to delimited files.

## Harness placement and verification state

- Claude Code: variant to `.claude/agents/data-sample-inspector.md`. Documented folder; the keys `name`, `description`, `tools`, `model`, `maxTurns` and `omitClaudeMd` were checked against the agent parser in the installed Claude Code 2.1.281 program text, read and not run. `omitClaudeMd: true`, which that program text's change list adds in 2.1.271, keeps the user, project and local CLAUDE.md files out of the helper's context; managed policy files still load. Discovery of this file was not observed.
- OpenCode: variant to `.opencode/agents/data-sample-inspector.md`. The wave specification names `.opencode/agent/` as unverified; the plural folder is recorded as documented and observed in the guide above, and the installed OpenCode program text (it embeds version 1.18.32) scans both. Keys and last-match permission rules were read from that program text, not run. Unverified.
- Copilot: variant to `.github/agents/data-sample-inspector.agent.md`. GitHub's custom agents documentation names `.github/agents/NAME.agent.md` and documents the `read` and `search` aliases and that unknown tool names are ignored. Discovery was not observed. Unverified.
- `contracts/reply.schema.json` and `LICENSE` go under `.baltor/data-sample-inspector/`.

## Customer requests

- "Look at the first rows of this CSV and tell me what's weird in each column."
- "What types are these columns before I write the cleaning rules?"
- "Check this export for placeholder values and mixed date formats, but don't show me any customer data."

## Limits

A sample of at most 200 rows can miss problems that appear later in the file. Quoted CSV fields that contain the separator or a line break are hard to split by eye, and the helper may misplace such a value; the cited line lets a caller check it. Very long lines may be cut by a harness reading tool. A value shape written by the model is a description, not a check. The first body draft had 361 words and was shortened to fit the 350 word limit before the first package check, which passed. A later reading found that the Job sentence could be read as one JSON object per column; it was clarified then.

The September 24 repair answered the a05 critic: JSON Lines has its own first action and column rule and is exempt from the header refusal; the first action now uses the caller's row count N instead of a fixed 50; the empty-cell count, which a model counts unreliably, was removed from the reply and the schema; the helper searches for invisible spaces instead of looking for them; a masking rule and the `values` option were added; `omitClaudeMd: true` was added to the Claude Code variant; the closest items above were added. The body is 349 words after the repair.
