# Review note: data_cleanup_plugin

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a11_session_plugins, model family
anthropic. This note is never delivered to a customer harness.

## Method

One session kit for a data cleanup step that writes cleaned copies of CSV
files. Three parts share one tested script, `scripts/check_cleaned_counts.py`:

1. A post-write hook runs after every file write or edit. When the written
   file is a cleaned copy declared in `.baltor/step/cleanup-pairs.json`, it
   compares the copy with its source: the header must equal the source header
   after the declared renames, in the same order, and the data row count must
   lie between the source count minus `max_dropped_rows` and the source count.
   Rows are CSV records, so a quoted value with a line break is one row. The
   hook also flags a write to a declared source file and any change to the
   pairs file itself, because a changed reference makes the check meaningless.
2. A cleanup status command runs the same comparison for every pair and
   prints a table.
3. A cleaning rule critic agent reads a cleaning plan, for example the
   `cleaning_plan/v1` file that the wave 5 planning packet writes, reviews
   each rule whose status is `proposed` against at most 20 table rows, and
   returns fixed JSON findings against seven named risks. It has reading
   tools only and never approves or applies a rule.

The count and header rules live in the script; the prose tells the model how
to react to a finding and when to stop.

## Authoring basis and sources

Original text and code under the repository MIT licence; nothing was copied
from outside projects. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package
  file contract.
- `case-studies/data-cleanup-with-and-without-baltor/DESIGN.md` and
  `REPORT-2026-09-22.md`: known-wrong outputs of cleanup steps (copied input,
  all null, shuffled rows) and the measured cost of long prose for a cheap
  model, which is why the checks are code and the messages are short.

Format facts. Gemini CLI: an earlier run of this generator read the
extension reference and the hooks pages on September 23, 2026 (no copy is
saved here). The third run checked the same facts by reading, not running,
the source of the installed Gemini CLI 0.59.0: `gemini-extension.json` needs
`name` (letters, digits and dashes) and `version`; `hooks/hooks.json` inside
an extension is loaded with `${extensionPath}` filled in; hooks are on by
default; the AfterTool input carries `tool_name`, `tool_input` and
`tool_response`; a tool matcher is a regular expression and the file tools
are named `write_file` and `replace`; hook commands receive
`GEMINI_PROJECT_DIR`; `timeout` is in milliseconds; an AfterTool
`hookSpecificOutput.additionalContext` is appended to the tool result, while
`decision: block` replaces the tool result with a blocked message, which is
why this plugin answers Gemini with context only. The local agent front
matter (`name`, `description`, `kind`, `tools`, `max_turns`) matches the
strict agent schema in that source, and `read_file`, `grep_search`, `glob`
and `list_directory` are built-in tool names there. Claude Code: the PostToolUse fields (`tool_name`,
`tool_input.file_path`, `decision: block` with `reason`,
`hookSpecificOutput.additionalContext`, matcher `Write|Edit`) follow the Claude
Code hooks reference as the first draft of this package recorded it; this
revision did not reread that page. The research file
`HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` in the Codex integration
worktree documents the extension folder layout.

## Inputs and outputs

Input: the pairs file (`cleanup_pairs/v1`, proposed here; contract in
`contracts/cleanup-pairs.schema.json`), the declared CSV files, and one hook
event on standard input. Hook output: `{}` for files outside the pairs; for
Claude Code, `hookSpecificOutput.additionalContext` on a match and
`{"decision": "block", "reason": ...}` on a problem; for Gemini CLI,
`hookSpecificOutput.additionalContext` in both cases, because a Gemini
`deny` would hide the real tool result. Status output: one JSON object with a
result per pair; exit 0 all match, 1 otherwise, 2 pairs file missing or
refused.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The script only reads.
`writes_fs` is declared because the tests build workspaces in temporary
folders. `spawns_process`: hook commands and the command text run
`python3 -I -B`, and tests start subprocesses. No network, no model call, no
secret read. The host must bind a trusted interpreter for `python3`, because
an earlier independent review showed that a `python3` first on `PATH` can be
replaced.

## Closest existing items

`assignments.json` lists none. Nearest by search of
`scout/existing-inventory.tsv`:

- `copy_a_table_with_corrections_never_in_place` (served text skill): advice
  to write corrections to a copy. No executable check.
- `audit_csv_structure` (first-party skill with scripts): audits one CSV's
  structure (field counts, quoting). It does not compare a copy with its
  source.
- `apply_hold_or_escalate_each_correction` (served text skill): decides per
  correction; no counts.

Wave 5 boundaries: `raw_data_stays_read_only` is a rule text,
`cleaning_apply_packet` is the step that applies rules,
`verify_cleaned_copy_change_log` checks a change log,
`check_csv_column_contract` checks one file against a column contract and
`data_sample_inspector` inspects samples. This plugin compares header and
count of a copy against its source at write time and reviews rules before
they are applied; it restates none of those.

## Positive example

In `examples/cleanup/`, `data/clean/orders.csv` renames `Order Date` to
`order_date` as declared and keeps all five records, one of which holds a
quoted line break. The Claude Code hook answers `Cleanup count check passed
for data/clean/orders.csv: header of 4 columns and 5 rows match
data/raw/orders.csv.`

## Known-wrong example

`data/clean/orders-dropped.csv` silently lost the row whose date was empty.
The hook answers `decision: block` with `rows lost: 4 rows, source has 5, at
most 0 may be dropped` (`test_hook_blocks_a_copy_that_lost_the_row_with_an_empty_value`).
A counter that counted lines instead of records would call the quoted line
break two rows; `test_quoted_line_break_is_one_row_not_two` refuses that.

## Harness placement and verification state

- Claude Code: plugin folder at `.baltor/plugins/data-cleanup-plugin/`
  (plugin_directory_binding), bound with
  `claude --plugin-dir .baltor/plugins/data-cleanup-plugin`. Plugin binding
  was observed on Claude Code 2.1.280 for a different plugin; PostToolUse
  behavior of this plugin was not run.
- Gemini CLI: extension folder at the same path with the `variants/gemini_cli/`
  files, activated with `gemini extensions link
  .baltor/plugins/data-cleanup-plugin`. Listed in `unverified_targets`: local
  activation, the hook run and the agent were not observed, and extension
  subagents are documented as preview; the formats were read in the source
  of the installed 0.59.0. Both command variants use the
  workspace-relative script path and assume the shell starts in the
  workspace root; the hook files use `${CLAUDE_PLUGIN_ROOT}` and
  `${extensionPath}`.
- No harness binary was run for this package.

## Customer requests

- "Warn my agent right away if a cleaned file has fewer rows than the
  original."
- "I want the column names checked after cleaning, but renames I planned are
  fine."
- "Before the cheap model applies my cleaning rules, have something point out
  rules that could lose data."

## Limits

Only header and row count are compared; values are not. A copy with the right
count but wrong values passes this check. The pairs format is a proposal the
integrator must align with the cleanup plan and apply packets. The hook
reacts only to Write and Edit (Claude Code) and write_file and replace
(Gemini CLI); a file changed by a shell command is caught by the status
command, not the hook. Files above 64 MiB are reported as unreadable. The
critic is model judgment and can miss a risk.

### Pre-check history

The first draft (digest `330c5e7d...`) passed every check with warnings for
the three synthetic CSV samples, which the first native review profile holds.
The second revision moved the command bodies from `${CLAUDE_PLUGIN_ROOT}` to
the placed workspace path, because variable expansion inside a command body
is not documented, and pointed the critic at the planning packet's
`cleaning_plan/v1` rules instead of an invented default path. Its payload
changed after the last report, so the third run's first check was refused by
the inventory check (`digest or size differs`); the fill command recorded the
new digests and the next check passed. The third run also rewrote the Gemini
basis above from the installed source. Every report stays in
`review/precheck-*.json`.
