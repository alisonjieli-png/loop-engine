# Review note: portable_step_packet_plugin

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a11_session_plugins, model family
anthropic. This note is never delivered to a customer harness.

## Method

One package in the Agent Plugins 1.0 layout for a focused step whose harness
is Copilot or Cursor. The host has placed the step packet in `.baltor/step/`.
Three parts:

1. `skills/read-step-assignment/` reads the packet: the `task.json` fields as
   given, every packet file with its size and SHA-256, the output schema's
   required fields and whether it allows other fields, and the results that
   earlier sessions wrote. With `--file` it returns one text file of the
   packet.
2. `skills/write-step-result/` checks a result against the top level of the
   packet's output schema (required fields, unknown fields when extra fields
   are forbidden, top-level JSON types, key-shaped text) and saves it as
   `result-NNN.json` with exclusive create, inside `portable_step_result/v1`
   with the node id and the SHA-256 of `task.json`. Earlier results stay, so
   a session can publish a better result and a reader names the file it used.
3. `server/step_packet_server.py`, a local standard-input protocol server
   with three tools, `read_step_assignment`, `read_step_file` and
   `write_step_result`. They call the two skill scripts by their exact paths,
   so a tool and a script give the same answer. The `initialize` answer
   carries short instructions that name the order of the tools.

A model that cannot run shell commands still gets its assignment and saves a
checked result through the tools; a model that can run them uses the scripts.
Each skill folder works alone when a client copies only the skills.

## Authoring basis and sources

Original text and code under the repository MIT licence; nothing was copied
from outside projects. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:
`src/loop_engine/core/service_runtime/catalogue_packages.py` (package file
contract) and `src/loop_engine/core/node_provisioning.py` (the
`node_assignment/v3` fields and the `task.json` name).

Format facts that are not on `main` at that revision: the research file
`HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` (Codex integration
worktree) documents that Agent Plugins 1.0 uses a root `plugin.json` with the
canonical `$schema`, `skills/<name>/SKILL.md` and a root `mcp.json`, that
Copilot reads it, and that Cursor reads the root `plugin.json` for skills and
protocol servers but does not fill in `${PLUGIN_ROOT}` in `mcp.json`. The
schema address and the `${PLUGIN_ROOT}` rule for standard-input servers
appear in the Qwen Code documentation snapshot and the OpenHands loader
snapshot under `artifacts/harness-package-interoperability-2026-09-23/`
in the shared checkout. The protocol behavior follows section 7.5 of the
wave 5 specification.

## Inputs and outputs

Inputs: `.baltor/step/task.json` (`node_assignment/v3`), the other packet
files, `contracts/output.schema.json` when present, and the result as one
JSON value (tool argument `result`, or standard input for the script).
Outputs: the assignment card `portable_step_assignment/v1`, one file's text
with its digest, and result files under
`.baltor/state/portable-step-packet-plugin/results/<node id>/`. Tool
contracts are in `contracts/<tool>.input.schema.json`. Scripts exit 0 done, 1
check failed (nothing written) and 2 refused input; the server answers
tool-level refusals with `isError: true` and protocol faults with the
JSON-RPC codes -32700, -32600, -32601 and -32602.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The read script and the
server read only below the workspace root and never follow a link out of it
or out of the step folder. The write script creates new files only below the
plugin's result folder. The harness starts the server; the skills show
shell commands; the tests start subprocesses and write only in temporary
folders. No network code (a test parses every script), no model call, no
secret read. Commands start `python3 -I -B`; the host must bind a trusted
interpreter, because an earlier independent review showed that a `python3`
found first on `PATH` can be replaced.

## Closest existing items

`assignments.json` lists none. Nearest found:
`focused_step_packet_example_incident_timeline` and
`focused_step_packet_example_inventory_reconciliation` (Codex example
packets) are packets of the kind this package serves, with no tools;
`supply_the_files_and_facts_an_assignment_needs` and
`state_the_permissions_and_limits_of_an_assignment` (starter text skills)
advise the host; `validate_focused_attempt_handoff` (planned Codex method)
checks a handoff, not a result.

Wave 5 boundaries: `focused_step_packet_rules` is a root instruction section
with a readiness check; this package serves packet files as protocol tools
and saves results. `json_schema_check_server` checks a document against a
supported subset of JSON Schema with paths for every violation; the write
tool checks only top-level required fields and types before saving and
leaves deeper rules to the host. `step_status_plugin` checks packet bytes
against a manifest, and `write_step_handoff` writes a handoff note. None of
them is restated here.

## Positive example

With `examples/workspace/` as the root, `read_step_assignment` names node
`newest-release` and the required fields `version`, `release_date` and
`change_count`. `write_step_result` with
`{"version": "2.4.1", "release_date": "2026-09-18", "change_count": 3}`
saves `result-001.json`, and a second good result becomes `result-002.json`
while the first file keeps its bytes
(`test_good_result_is_written_as_001_then_002_and_never_replaced`).

## Known-wrong example

A model that skipped the assignment answers `{"release": "2.4.1"}`. The
writer saves nothing and lists `missing_required_field` for all three fields
and `unknown_field: release`
(`test_known_wrong_result_is_refused_and_nothing_is_written`); through the
server the same answer comes back with `isError: true`.

## Harness placement and verification state

- Copilot: the whole folder at `.baltor/plugins/portable-step-packet-plugin/`
  (plugin_directory_binding) with the root `plugin.json` and the root
  `mcp.json`, which starts the server through `${PLUGIN_ROOT}`. The folder is
  given to Copilot's local plugin installation; the exact command was not
  checked here. Listed in `unverified_targets`: the `mcpServers` key,
  `${PLUGIN_ROOT}` filling, the server's working folder, activation and how
  the tools are shown.
- Cursor: the same folder, but `variants/cursor/mcp.json` replaces the root
  `mcp.json` and names the placed path, because Cursor leaves
  `${PLUGIN_ROOT}` unfilled. That path assumes the server starts in the
  workspace root. Activation and skill discovery are unverified.
- Without `--root`, the server and scripts take the folder that holds
  `.baltor` in their own placed path as the workspace root, else the current
  folder. No harness binary was run for this package.

## Customer requests

- "My Copilot agent should get its step instructions from a tool instead of
  guessing which file to read."
- "Save each step's answer as a file that nobody overwrites, and tell me
  which one the next step used."
- "Refuse an answer that misses a required field before the next step
  starts."

## Limits

Only the top level of the output schema is checked: patterns, formats and
nested rules are not, so a result can pass here and still fail the host's
acceptance. Key shapes are generic and cannot catch every secret. Text
values nested deeper than 64 levels are not scanned. `read_step_file` serves
UTF-8 text up to 32 KiB. The specification says Copilot and Cursor add no
review style, while the checker refuses an empty style list; this package
declares `copilot` and `cursor`, the checker warns, and the first native
review profile holds the package for these styles and for its roles. The
checker also warns about a URL in code: the layout test holds the canonical
schema address as a constant to compare with `plugin.json`, and nothing
fetches it.

### Pre-check history

The first run of this generator left only the licence file here. The third
run wrote the package. Before the first package check, 38 tests passed under
Python 3.14 and 3.10, and ten mutants, each removing one guard in a scratch
copy, were run. Nine were caught at once. The mutant that removed the name
check in `read_step_file` was not caught, because a later path check refuses
the same unsafe names; a non-text name was still unguarded there, so a test
for it was added, and the rerun caught the mutant. Reports stay in
`review/precheck-*.json`.
