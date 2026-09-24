# Review note: step_status_plugin

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a11_session_plugins, model family
anthropic. This note is never delivered to a customer harness.

## Method

One kit for a focused step in Gemini CLI or Cursor. The host has placed the
step packet under `.baltor/step/` and written a manifest of its files. The
kit answers one question before work starts and again at handoff: is this
still exactly the packet the host placed? Three parts:

1. A context file, `STEP-STATUS.md`, named by the Gemini CLI extension's
   `contextFileName`; Cursor gets the same text as an always-applied rule.
   It stays under 150 words, makes the packet check the first action, says
   to stop on exit 1 or 2, and says to keep `.baltor/step/` unchanged.
2. A packet manifest check, `scripts/check_step_packet.py`. It compares
   every listed file with its SHA-256 and size, recomputes the digest of the
   whole file map, binds that digest to the one in the first message when
   `--expect-content-sha256` is given, compares the manifest `step_id` with
   the `node_id` in `task.json`, and fails on any file in the packet folder
   that the manifest does not list.
3. A step status command running `scripts/step_status.py`. It prints a card:
   node id, kind, mode, objective, effects and model call authority from
   `task.json`; the output contract refs and the output schema's required
   fields; the Before handoff items; the packet check result; and one next
   action, either go on or stop.

The check judges identity only. Whether the packet is complete and ready,
for example unfilled markers or missing sections, is a separate readiness
check, and this kit does not repeat it.

## Authoring basis and sources

Original text and code under the repository MIT licence; nothing was copied
from outside projects. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:
`src/loop_engine/core/service_runtime/catalogue_packages.py` (package file
contract) and `src/loop_engine/core/node_provisioning.py` (the
`node_assignment/v3` fields and the `task.json` file name).

The manifest fields are those of `focused_step_packet_candidate/v1`, which
the Codex packet renderer writes (`render_packet.py` in the Codex review
worktree `artifacts/focused-step-packet-2026-09-23/`, not on `main`). Two
differences are stated in `contracts/packet-manifest.schema.json`: a file
path may hold folders, because these packets live under `.baltor/step/`, and
any short harness style name is read. The content digest rule is the same.
As a cross-check, the check was run read-only on both Codex example packets
with `--manifest packet-manifest.json`: both passed (8 and 9 files), and the
incident packet matched the digest recorded in Codex `fixture-bindings.json`.

Format facts: the research file `HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`
(Codex integration worktree) documents the Gemini CLI extension layout, the
Cursor `.cursor-plugin/plugin.json` and Cursor rules in `.mdc` form. The
source of the installed Gemini CLI 0.59.0 was read, not run: an extension
name uses letters, digits and dashes, `contextFileName` names the context
file, extension commands load from `commands/**/*.toml` under their file
name with the extension name shown in the description, and commands are not
loaded in an untrusted folder when folder trust is on.

## Inputs and outputs

Inputs: the manifest (default `.baltor/step/packet-manifest.json`), the
files it lists, the names in its folder, `task.json`, `checklist.md` and
`contracts/output.schema.json`. Optional input: the digest from the first
message. Outputs: one JSON object on standard output from each script. The
check exits 0 on pass, 1 on a failed check and 2 for a missing or refused
manifest. The status card exits 0 or 1 with the packet result and 2 when the
step folder or `task.json` cannot be read.

## Effects

Declared: `reads_fs`, `spawns_process`. Both scripts only read; a test
walks their syntax trees and refuses any writing call or a process, network
or file-copy import. The command runs the status script and `git status
--porcelain`. Tests are read-only and start the scripts as subprocesses. No
network, no model call, no secret read. Commands start `python3 -I -B`; the
host must bind a trusted interpreter, because an earlier independent review
showed that a `python3` found first on `PATH` can be replaced.

## Closest existing items

`assignments.json` lists none for Gemini CLI. Nearest found:
`focused_step_packet_example_incident_timeline` and
`focused_step_packet_example_inventory_reconciliation` (Codex example
packets, not library items) are the packets this check can verify;
`supply_the_files_and_facts_an_assignment_needs` and
`state_the_permissions_and_limits_of_an_assignment` (starter text skills)
advise a host on what to put in an assignment, with no check.

Wave 5 boundaries: `focused_step_packet_rules` is a root fragment whose
script checks that the packet is ready (markers, sections, first action);
this kit checks that the bytes are the ones the host placed. The a09 and a10
packets are the packets; `interrupted_step_resume_packet` resumes a step;
`write_step_handoff` writes the handoff note. None is restated here.

## Positive example

With `examples/packet/` as the root, the check exits 0 with five files and
`packet_content_sha256` `08433bab...`. The status card shows node
`list-failing-tests`, kind `reason`, mode `deterministic`, required field
`failing_tests`, three handoff items and the next action to go on
(`test_example_card_names_step_output_and_handoff`).

## Known-wrong example

A small model relaxes the acceptance line in `node_context.md` to finish
sooner. The file's SHA-256 no longer matches the manifest, so the check
fails with `digest_differs` for that path and the status card says to stop
(`test_packet_file_edited_after_the_manifest_is_caught`). A leftover file in
the step folder gives `unlisted_file`
(`test_leftover_file_in_the_packet_folder_is_caught`), and a packet whose
manifest was rewritten with it fails `not_the_expected_packet` when the
first message carries the host digest.

## Harness placement and verification state

- Gemini CLI: extension folder at `.baltor/plugins/step-status-plugin/`
  (plugin_directory_binding) with the `variants/gemini_cli/` files, activated
  with `gemini extensions link .baltor/plugins/step-status-plugin` and a new
  session. Listed in `unverified_targets`: activation and the command run were
  not observed; the formats come from the research file and the installed
  source.
- Cursor: same folder with the `variants/cursor/` files. Listed in
  `unverified_targets`: rule and command discovery inside a plugin folder,
  the command name, the command front matter and local activation.
- Both use workspace-relative script paths, which assume the shell starts in
  the workspace root. No harness binary was run for this package.

## Customer requests

- "Before my agent starts a step, make sure nobody changed the step files."
- "Give the model a one-screen status of the step: what it must do, what
  its answer must contain and what is left before handoff."
- "My Gemini CLI steps should refuse to start on a stale packet."

## Limits

A manifest proves nothing on its own: without the host digest in the first
message, a rewritten manifest and packet pass together. The check reads at
most 64 files, 1 MiB each and 8 MiB in total, and scans at most 2,000 names
in the packet folder. It does not follow links; a linked file counts as
missing. Link handling is covered by code review only, because the tests
are read-only. The status card reads `task.json` as given and does not
validate it. The manifest record is a Codex candidate, not on `main`; the
nested paths need the integrator's decision before any other reader relies
on them.

### Pre-check history

The first run of this generator left a partial draft of this package with
no manifest and no review note. Its check also looked for unfilled markers
and invalid task fields, which the `focused_step_packet_rules` package
already checks, and read a manifest with any subset of fields. The third
run cut the check down to identity, made unlisted files a failure, required
every manifest field, added the manifest contract, and removed an invented
`results/` folder from the status card. Six mutants, each removing one guard
in a scratch copy, were caught by the tests. Reports stay in
`review/precheck-*.json`.
