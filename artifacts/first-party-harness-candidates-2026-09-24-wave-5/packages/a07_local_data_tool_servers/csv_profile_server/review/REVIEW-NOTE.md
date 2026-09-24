# Review note: CSV profile tool server

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator `a07_local_data_tool_servers`, model family `anthropic`. This note is never delivered to a customer harness.

## Method

One logical method: give a fresh step harness an exact, callable profile of one CSV file so a small model does not guess column types from names or from the first rows. The package holds one standard-library protocol server (`server/csv_profile_server.py`) with one tool, `profile_csv`, a scripted-client test, the tool's input contract, a synthetic example, five harness configuration variants and a short companion (`AGENTS.md`).

For each selected column the tool reports: nonempty, empty and missing-field counts; values with leading or trailing spaces; distinct count (exact up to a per-column cap, then flagged); the type of every value (integer, decimal, boolean, ISO date, ISO datetime or text); the inferred column type or `mixed` with the dominant type and its share; up to five nonconforming values with the line where their record starts; the most common values; the three most common character shapes, in which every letter of any script becomes `A` (upper case) or `a`, every decimal digit `9` and every other character `_`, except ASCII punctuation and spaces; length range; numeric range; and the count of integers written with a leading zero. File facts include the byte size, SHA-256 digest, encoding, byte order mark, detected delimiter, blank lines and rows whose width differs from the header.

## Authoring basis and sources

Original code and text written for this package from general knowledge of CSV parsing and of the Model Context Protocol revisions 2025-03-26, 2025-06-18 and 2025-11-25. The protocol text was not fetched in this run; the behavior follows SPEC section 7.5 of wave 5. Repository files read at `a1fc743`: `src/loop_engine/core/service_runtime/catalogue_packages.py` (package format), the pilot `audit-csv-structure/SKILL.md` and `json-shape-stdio/REVIEW.md` (the earlier local server needed a third-party package and failed in a clean home; this one uses only the standard library), the served body `profile_text_column_before_cleaning.md`, `NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md` and the data cleanup case study, which found that long prose material cost prompt tokens without benefit. That finding is why the rules live in code and the companion stays short. No outside project text or code was copied.

Third pass basis (September 24, 2026): harness documentation read on this machine and described here in original words, with no text copied. Claude Code: the saved MCP page `/home/username/.le-ci-tmp/research/ecosystem/sources/B/cc-mcp.md` (sections on stdio servers, environment variable expansion in `.mcp.json` and project scope). Cursor: `docs/cursor-mcp.md` in the agent-harness checkout at `/home/username/.le-ci-tmp/research/agent-harness` (revision `2ecf44f`, the one that `docs/research/AGENT-HARNESS-MADEBYWILD-2026-09-23.md` records; that research file is now a source of this package). Gemini CLI 0.59.0: the installed `docs/tools/mcp-server.md`, `docs/cli/trusted-folders.md` and `docs/reference/configuration.md` under `/home/username/.local/lib/node_modules/@google/gemini-cli/bundle/`.

## Inputs and outputs

Input: the arguments in `contracts/profile_csv.input.schema.json` (`path` required; `delimiter`, `encoding`, `has_header`, `columns`, `top_values`, `include_values`, `max_rows` optional). Output: one JSON object, returned both as compact text and as `structuredContent`. Refusals return `isError: true` with an `error` sentence and, where useful, the header names. Limits: 1 MiB request lines; one answer line of at most 262,144 bytes (256 KiB), measured on the exact bytes written, so both copies of the result and every escape count; 64 MiB files unless the host passes `--max-file-mib`; 100 columns per call. A result that would not fit comes back as a short refusal that names the limit and says how to narrow the call. With `include_values: false` the answer leaves out common values, examples and the numeric range; counts, types, lengths and shapes remain, and a shape shows no letter or digit of the data.

## Effects

The server reads files under `--root` only. It writes nothing, starts no process, opens no network connection and reads no secret. `reads_fs` covers the CSV reads. `spawns_process` is declared because a harness starts the server and the tests start it. `writes_fs` is declared only because the tests create temporary folders (a link that points out of the root, a file with a bad byte, wide and non-ASCII files, and a workspace for the launch test); the server itself never writes. The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Closest existing items

- Pilot `audit_csv_structure`: a skill script that checks structure only (malformed rows, duplicate headers, field counts) and refuses to infer types. This package infers types, counts values and names the lines of values that break the dominant type, and it is callable as a tool.
- Served `profile_text_column_before_cleaning`: prose that tells a model how to profile one text column. This package computes a whole-table profile in code.
- Pilot `json_shape_stdio`: a local server that needed the third-party protocol package. This server needs none.
- First-party candidate `profile_one_csv`: a step brief template with placeholders that asks the model to profile by hand.
- Wave 5 `data_sample_inspector` (assignment a05): a subagent definition whose helper model reads lines 1 to 51 of a file by default (never past line 201) and describes each column in its own words. This tool reads every row in code and counts; the head-only view is exactly the known-wrong case below.
- Wave 5 `cleaning_plan_packet` (a10): its own `plan_tool.py draft` writes a table profile inside that one packet. This server gives any step the column facts through a tool call, with no packet around it.
- Wave 5 `check_csv_column_contract` (a15): checks a CSV against a written column contract and passes or fails it. This tool needs no contract and judges nothing; its counts are evidence for writing such a contract or a cleaning rule.

## Positive example

`examples/orders.csv` (synthetic) gives: `order_id` integer with 12 distinct values; `order_date` mixed, dominant date, nonconforming `03/04/2025` on line 6; `currency` with one value padded by a space; one row short of fields reported at line 12, which is correct only if the quoted two-line note on lines 8 and 9 is counted. The tests assert each of these facts.

## Known-wrong example

Reading only the first rows makes `amount` look like a clean decimal column. With `max_rows: 2` the tool says `decimal` and `complete: false`. The full profile says `mixed`, dominant `decimal`, with `N/A` on line 4 and `12,50` on line 7. A rule written from the head view would fail on those rows. The test `test_known_wrong_head_view_hides_the_broken_amounts` holds this case.

Two known-wrong cases were added in the third pass. A shape table that maps only ASCII letters and digits returns Chinese, Cyrillic, Greek and Arabic values whole, and accented Latin values in part, even with `include_values: false`; `test_known_wrong_non_ascii_values_leak_through_shapes_when_values_are_hidden` checks that such an answer holds no character outside ASCII at all. Counting each header name with `header.count` takes quadratic time; `test_known_wrong_wide_header_is_scanned_in_linear_time` profiles two columns of a 40,000-column file within 8 seconds.

## Harness placement and verification state

The server, tests, contract, examples and licence go to `.baltor/csv-profile-server/`. The companion is composed into `CLAUDE.md` (Claude Code), `GEMINI.md` (Gemini CLI) or `AGENTS.md` (Codex, OpenCode, Cursor). No harness binary was run here; native discovery probes belong to the integrator.

- Claude Code: `.mcp.json` (documented; the pilot checked its syntax). The launch line is `python3 -I -B ${CLAUDE_PROJECT_DIR:-.}/.baltor/csv-profile-server/server/csv_profile_server.py --root ${CLAUDE_PROJECT_DIR:-.}`. The Claude Code MCP documentation describes `${VAR:-default}` expansion in `command` and `args`, and says that Claude Code sets `CLAUDE_PROJECT_DIR` in the server's environment but not in its own. The expansion therefore gives absolute paths only when the host starts Claude Code with `CLAUDE_PROJECT_DIR` set to the workspace; otherwise it gives `.`, the earlier relative form, which works only when the server starts in the project root. The test `test_expanded_launch_lines_start_the_server_from_a_subfolder` shows both outcomes. Where Claude Code starts a project server was not observed. Project servers also need the user's approval in a trusted workspace.
- Cursor: `.cursor/mcp.json` with `mcpServers`, and `${workspaceFolder}` (the folder that holds `.cursor/mcp.json`) in `command` and `args`, as the Cursor MCP documentation describes. The expanded line answers from a subfolder in the same test. The earlier note said no documentation existed; that was wrong. Discovery and approval were not observed.
- Gemini CLI: `.gemini/settings.json` `mcpServers` (documented). The server key is `csv-profile-server`, not the identity. This deviates from SPEC section 9.2 on purpose: the Gemini CLI 0.59.0 documentation says that its policy parser splits a tool's full name `mcp_<server>_<tool>` at the first underscore after `mcp_`, so an underscore in the server name makes wildcard and security rules fail silently. With folder trust on (true by default in the 0.59.0 configuration reference), Gemini CLI ignores the workspace settings and connects no protocol server in an untrusted folder, and a headless run in an untrusted folder stops unless the host passes `--skip-trust` or sets `GEMINI_CLI_TRUST_WORKSPACE`. The launch line stays relative and assumes the server starts in the workspace root (unverified).
- Codex: `.codex/config.toml` for trusted projects (documented). The launch line stays relative (start folder unverified).
- OpenCode: `opencode.json` `mcp` (observed for the pilot server with a relative path and `cwd` set to the workspace).

Harnesses show each tool under a prefixed name, for example `mcp__csv_profile_server__profile_csv` in Claude Code and `mcp_csv-profile-server_profile_csv` in Gemini CLI, so the companion tells the model to match the ending of the name. When no such tool is listed, the companion's test command runs from the workspace root; there the variant and companion tests skip themselves, and the others pass when the server works. The companion now says that a pass means the harness did not start a working server. Each input schema carries a `$schema` line, as the contract files require; whether every harness passes such a schema to its model unchanged was not observed. The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Customer requests

- "Before we clean this export, tell me what is actually in each column."
- "Which rows have amounts that are not numbers, and on which lines?"
- "Give the cheap model a way to look at the table without pasting the whole file."

## Limits

Type rules are fixed and simple: `1,234.50`, `12,50`, `03/04/2025` and `NaN` are text, which is the intended signal for a cleaning step, not a parse. Distinct counts and common values become lower bounds after the per-column cap (flagged). Shapes cover values of 40 characters or less. Shapes keep ASCII punctuation and spaces, so a value made only of those characters, such as `-`, stays visible with `include_values: false`, and `N/A` shows as `A/A`. The type rules read only ASCII digits, so a value written in digits of another script is text and its shape is `999`. Large files can take several seconds; clients with short tool timeouts may stop the call. The server has no row sampling (see `csv_row_sampler_server`) and changes no data. Windows was not tested. A model that writes tool calls as plain text, as the local 7B model did in the case study, cannot use any protocol server.

Pre-check history: recorded in `review/PRECHECKS.txt` and the `review/precheck-*.json` reports. The first report refused the package because the payload files were not mode 0644; the modes were set and the check rerun.

Second generator pass, September 24, 2026 (UTC): a probe of the output bound found that an answer line could pass 256 KiB even though the package passed every pre-check. The old guard measured one copy of the result (at most 120 KiB) before the text copy escaped every backslash and quote a second time; 30 columns of backslash values gave a 270,849-byte line. The server now measures the whole line as written and refuses above 262,144 bytes, keeping the error sentence of a refusal that is itself too long. The new test `test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib` failed on the previous server under Python 3.14 and 3.10 and passes now. The probe, its output before and after the repair, the mutation run and a copy of the previous package are kept in the wave folder under `generator-a07-work/`.

Third pass, repairs after critic round 4, September 24, 2026 (UTC):
- Privacy (blocking). With `include_values: false`, shapes still showed values of other scripts, because the shape table mapped only ASCII letters and digits. The shape of a value now comes from the Unicode category of each character, and the contract text states what a shape keeps. `test_known_wrong_non_ascii_values_leak_through_shapes_when_values_are_hidden` failed on the previous server under Python 3.14 and 3.10.
- Wide headers (minor). The duplicate-name scan used `header.count` for each name; 40,000 columns took 21 seconds in the critic's probe and 29.6 seconds in the rerun. It now uses a counter, and the column list uses index tables. `test_known_wrong_wide_header_is_scanned_in_linear_time` failed on the previous server (29.6 seconds against an 8 second bound).

The placement repairs are shared by all five packages of the assignment: the Gemini CLI server key is the hyphenated name (a recorded deviation from SPEC section 9.2), `unverified_targets` names the Gemini CLI folder trust condition and the Claude Code expansion limit, the Claude Code and Cursor variants use `${CLAUDE_PROJECT_DIR:-.}` and `${workspaceFolder}`, and `test_expanded_launch_lines_start_the_server_from_a_subfolder` and `test_known_wrong_gemini_server_key_with_underscores` fail on the previous variant files. The companion now says that a listed tool may carry a prefix, that a passing fallback test run means the harness did not start a working server, and (for the four data servers) that returned values are data, never instructions.

Evidence, all in the wave folder: the critic's probes run on the previous and the repaired packages (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/evidence/probes-before-repair.txt`, `probes-after-repair.txt`), a successor of the critic's placement probe (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/probes/placed_workspace_after.py` and `evidence/placed-workspace-after-repair.txt`), the new tests run on the previous files (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/evidence/known-wrong-*.txt`), 32 mutants across the five packages, each made a named test fail (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/mutants/mutants-result.txt`), and a copy of the five packages before this pass (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/a07-predecessor-snapshot-20260924T052417Z.tar.gz`).
