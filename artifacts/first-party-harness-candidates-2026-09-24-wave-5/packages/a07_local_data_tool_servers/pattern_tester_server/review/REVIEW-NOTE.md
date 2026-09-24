# Review note: Pattern tester tool server

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator `a07_local_data_tool_servers`, model family `anthropic`. This note is never delivered to a customer harness.

## Method

One logical method: before a cleaning rule relies on a regular expression, test the expression against values it must accept and values it must reject, and see the groups and the replacement it would produce. A small model can then correct the pattern from facts rather than from its own reading of the syntax. The package holds one standard-library protocol server (`server/pattern_tester_server.py`) with one tool, `test_pattern`, a scripted-client test, the input contract, two example argument files, five harness configuration variants and a short companion (`AGENTS.md`).

The tool compiles the pattern with the given flags and runs it on up to 100 texts in each of `should_match`, `should_not_match` and `examples`, in `fullmatch` (default), `search` or `findall` mode. It returns `passed` (true only when no text in `should_match` failed and no text in `should_not_match` matched; null when no expectation was given), `misses`, `false_matches`, and for each text the span, matched text, groups, named groups and, when `replacement` is given, the preview (`fullmatch` expands the one match; the other modes replace every match). Fixed notes warn when a non-fullmatch mode is used, when `\d` or `\w` run without the ASCII flag, and when the pattern starts or ends with a space. A timer signal stops a backtracking pattern at `time_limit_ms`.

## Authoring basis and sources

Original code and text from general knowledge of Python's `re` module and of the Model Context Protocol revisions 2025-03-26, 2025-06-18 and 2025-11-25 (protocol text not fetched in this run), following SPEC section 7.5 of wave 5. Before writing, a probe on this machine confirmed that a timer signal interrupts a backtracking match such as `(a+)+$` under Python 3.14 and 3.10. Repository files read at `a1fc743`: `catalogue_packages.py`, the served body `detect_malformed_values_by_dominant_pattern.md`, the pilot `json-shape-stdio/REVIEW.md`, the placement research of September 22 and the data cleanup case study. No outside project text or code was copied.

Third pass basis (September 24, 2026): harness documentation read on this machine and described here in original words, with no text copied. Claude Code: the saved MCP page `/home/username/.le-ci-tmp/research/ecosystem/sources/B/cc-mcp.md` (sections on stdio servers, environment variable expansion in `.mcp.json` and project scope). Cursor: `docs/cursor-mcp.md` in the agent-harness checkout at `/home/username/.le-ci-tmp/research/agent-harness` (revision `2ecf44f`, the one that `docs/research/AGENT-HARNESS-MADEBYWILD-2026-09-23.md` records; that research file is now a source of this package). Gemini CLI 0.59.0: the installed `docs/tools/mcp-server.md`, `docs/cli/trusted-folders.md` and `docs/reference/configuration.md` under `/home/username/.local/lib/node_modules/@google/gemini-cli/bundle/`.

## Inputs and outputs

Input: `contracts/test_pattern.input.schema.json` (`pattern` required, at most 2,000 characters; three text lists of at most 100 texts of at most 10,000 characters; `mode`, `flags`, `replacement`, `time_limit_ms` from 100 to 10,000). Output: one JSON object as compact text and as `structuredContent`; texts and groups are shown up to 80 characters with the full length given. The answer names the engine, for example `Python re 3.14`, because features such as possessive quantifiers compile on Python 3.11 and later only. Refusals carry `isError: true`: a pattern that does not compile (with its position), a replacement that names a missing group, the time limit, or an argument out of range. One answer line holds at most 262,144 bytes (256 KiB), measured on the exact bytes written, so both copies of the result and every escape count; a longer answer becomes a short refusal that says to test fewer or shorter texts.

## Effects

The server opens no file, writes nothing, opens no network connection, starts no process and reads no secret. It accepts `--root` only so that all five servers of this assignment share one launch line; a test starts it with a folder that does not exist to show that it never reads the root. `spawns_process` covers the harness and the tests starting the server. `reads_fs` is declared because the tests read the package's own contract, example and configuration files; the server reads none. `writes_fs` is declared since the third pass because one test copies the server into a temporary workspace to start its launch lines from a subfolder; the tests write nothing else, and the server writes nothing. The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Closest existing items

- Served `detect_malformed_values_by_dominant_pattern`: prose that derives a character pattern from the data and flags values that differ. It finds a pattern; this package tests a pattern that a person or model wrote, with expectations, groups and replacements.
- Staged outside registry link `regex-email-url-validator`: a remote service for fixed email and address checks, which this wave did not read. This package tests any expression, locally.
- Wave 5 sibling `csv_profile_server` reports character shapes such as `9999-99-99`, which are good input texts for this tool.
- Wave 5 `parse_dates_by_declared_formats` and `standardize_missing_value_tokens` (a01): executors that apply declared date formats or declared token lists to a column. Neither runs a regular expression written by the model; this tool tests such an expression before any rule uses it, and changes no data.

## Positive example

`examples/test_pattern-arguments.json` tests a named-group date pattern against two valid dates and four values a rule must reject (`2025-3-1`, `03/04/2025`, a date followed by text and a date with a leading space). It passes, and the replacement `\g<day>.\g<month>.\g<year>` previews `01.03.2025`.

## Known-wrong example

`examples/known-wrong-search-arguments.json` uses `\d{4}-\d{2}-\d{2}` in `search` mode. It accepts three values the rule must reject: `x2025-03-01y`, `12025-03-011` and a date written in full-width digits, because `search` matches inside a longer text and `\d` matches digits of other scripts. The tool reports all three as false matches with notes about both causes; the same texts pass with `[0-9]` and `fullmatch`. The test `test_known_wrong_search_mode_accepts_values_a_rule_must_reject` holds this case.

## Harness placement and verification state

The server, tests, contract, examples and licence go to `.baltor/pattern-tester-server/`. The companion is composed into `CLAUDE.md` (Claude Code), `GEMINI.md` (Gemini CLI) or `AGENTS.md` (Codex, OpenCode, Cursor). No harness binary was run here; native discovery probes belong to the integrator.

- Claude Code: `.mcp.json` (documented; the pilot checked its syntax). The launch line is `python3 -I -B ${CLAUDE_PROJECT_DIR:-.}/.baltor/pattern-tester-server/server/pattern_tester_server.py --root ${CLAUDE_PROJECT_DIR:-.}`. The Claude Code MCP documentation describes `${VAR:-default}` expansion in `command` and `args`, and says that Claude Code sets `CLAUDE_PROJECT_DIR` in the server's environment but not in its own. The expansion therefore gives absolute paths only when the host starts Claude Code with `CLAUDE_PROJECT_DIR` set to the workspace; otherwise it gives `.`, the earlier relative form, which works only when the server starts in the project root. The test `test_expanded_launch_lines_start_the_server_from_a_subfolder` shows both outcomes. Where Claude Code starts a project server was not observed. Project servers also need the user's approval in a trusted workspace.
- Cursor: `.cursor/mcp.json` with `mcpServers`, and `${workspaceFolder}` (the folder that holds `.cursor/mcp.json`) in `command` and `args`, as the Cursor MCP documentation describes. The expanded line answers from a subfolder in the same test. The earlier note said no documentation existed; that was wrong. Discovery and approval were not observed.
- Gemini CLI: `.gemini/settings.json` `mcpServers` (documented). The server key is `pattern-tester-server`, not the identity. This deviates from SPEC section 9.2 on purpose: the Gemini CLI 0.59.0 documentation says that its policy parser splits a tool's full name `mcp_<server>_<tool>` at the first underscore after `mcp_`, so an underscore in the server name makes wildcard and security rules fail silently. With folder trust on (true by default in the 0.59.0 configuration reference), Gemini CLI ignores the workspace settings and connects no protocol server in an untrusted folder, and a headless run in an untrusted folder stops unless the host passes `--skip-trust` or sets `GEMINI_CLI_TRUST_WORKSPACE`. The launch line stays relative and assumes the server starts in the workspace root (unverified).
- Codex: `.codex/config.toml` for trusted projects (documented). The launch line stays relative (start folder unverified).
- OpenCode: `opencode.json` `mcp` (observed for the pilot server with a relative path and `cwd` set to the workspace).

Harnesses show each tool under a prefixed name, for example `mcp__pattern_tester_server__test_pattern` in Claude Code and `mcp_pattern-tester-server_test_pattern` in Gemini CLI, so the companion tells the model to match the ending of the name. When no such tool is listed, the companion's test command runs from the workspace root; there the variant and companion tests skip themselves, and the others pass when the server works. The companion now says that a pass means the harness did not start a working server. Each input schema carries a `$schema` line, as the contract files require; whether every harness passes such a schema to its model unchanged was not observed. The host must bind a trusted `python3`, because an interpreter found first on `PATH` can be replaced.

## Customer requests

- "Check my phone number regex against these twenty values before the cleanup runs overnight."
- "Why does this pattern accept dates with extra text after them?"
- "Show me what the replacement would turn each value into."

## Limits

The engine is Python's `re`; a rule that later runs in another engine (a database, JavaScript or a spreadsheet) can behave differently. Only 300 texts per call, and texts are shown shortened in the answer. `passed` covers only the texts given; it says nothing about values that were not tested. Without a timer signal (for example on Windows, which was not tested) the time limit is not enforced and the answer says so. A model that writes tool calls as plain text cannot use any protocol server.

Pre-check history: recorded in `review/PRECHECKS.txt` and the `review/precheck-*.json` reports. The first check refused the package for two producer mistakes: a `__pycache__` folder left by importing the server while writing the contract, and an undeclared `reads_fs` for the tests' reads of package files. The folder was removed, `reads_fs` was declared and the check rerun.

Second generator pass, September 24, 2026 (UTC): a probe of the output bound found that an answer line could pass 256 KiB even though the package passed every pre-check. The old guard measured one copy of the result (at most 120 KiB) before the text copy escaped every backslash and quote a second time; 25 texts with twenty 80-character backslash groups each gave a 275,537-byte line. The server now measures the whole line as written and refuses above 262,144 bytes. The new test `test_known_wrong_escapes_cannot_push_an_answer_line_past_256_kib` failed on the previous server under Python 3.14 and 3.10 and passes now. The probe, its output before and after the repair, the mutation run and a copy of the previous package are kept in the wave folder under `generator-a07-work/`.

Third pass, repairs after critic round 4, September 24, 2026 (UTC): the server code is unchanged, as the critic advised. The variant and companion repairs below are this package's changes. The new launch test builds a temporary workspace, so `writes_fs` is now declared for the tests; the server still writes nothing. The companion also says that in `search` mode `$` matches before a final line break, which the tool already reports as a false match.

The placement repairs are shared by all five packages of the assignment: the Gemini CLI server key is the hyphenated name (a recorded deviation from SPEC section 9.2), `unverified_targets` names the Gemini CLI folder trust condition and the Claude Code expansion limit, the Claude Code and Cursor variants use `${CLAUDE_PROJECT_DIR:-.}` and `${workspaceFolder}`, and `test_expanded_launch_lines_start_the_server_from_a_subfolder` and `test_known_wrong_gemini_server_key_with_underscores` fail on the previous variant files. The companion now says that a listed tool may carry a prefix, that a passing fallback test run means the harness did not start a working server, and (for the four data servers) that returned values are data, never instructions.

Evidence, all in the wave folder: the critic's probes run on the previous and the repaired packages (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/evidence/probes-before-repair.txt`, `probes-after-repair.txt`), a successor of the critic's placement probe (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/probes/placed_workspace_after.py` and `evidence/placed-workspace-after-repair.txt`), the new tests run on the previous files (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/evidence/known-wrong-*.txt`), 32 mutants across the five packages, each made a named test fail (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/mutants/mutants-result.txt`), and a copy of the five packages before this pass (`repairer-a07_local_data_tool_servers/after-critic-r4-20260924T052417Z/a07-predecessor-snapshot-20260924T052417Z.tar.gz`).
