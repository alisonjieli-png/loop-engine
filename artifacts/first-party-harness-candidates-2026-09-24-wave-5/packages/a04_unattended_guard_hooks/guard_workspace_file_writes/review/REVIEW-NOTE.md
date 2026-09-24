# Review note: guard_workspace_file_writes

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a04_unattended_guard_hooks (model family anthropic), September 23, 2026. Repaired on September 24, 2026 by the wave 5 repairer of the same assignment and model family, after the findings of an independent critic. This note is never delivered to a customer harness.

## Method

One method: before each file write, edit or delete made with the harness's file tools, resolve the target the way the operating system would and refuse the call when the real target is outside the workspace root. The hook also refuses a target inside version control metadata (`.git`, `.hg`, `.svn`, `.bzr`, at any depth and in any letter case) or inside the harness and step folders (`.baltor`, `.claude`, `.cursor`, `.github/hooks`). It refuses a target on a protected pattern that the step policy declares, and any existing target that is not a regular file or has other hard links. Both the typed path and the resolved path are checked, so a symbolic link cannot carry a write into `.git` or out of the workspace. A path that starts with `~` is refused, because some tools expand it to the home folder. The built-in folders are protected because an agent that can edit its own hook registration or policy can switch the guard off. A policy may reopen single paths inside those folders with `writable_globs`, for example a handoff file.

Claude Code worktrees: Claude Code keeps `CLAUDE_PROJECT_DIR` at the main checkout while the `cwd` field of the hook input follows the session or a subagent into `.claude/worktrees/<name>/`. The first version refused every write there as "inside .claude". Now, when the event's `cwd` lies inside such a folder, and the folder and its parents are real folders (not links) and it holds a `.git` regular file as a git worktree does, that folder is the workspace root for the check. The policy is still read from the main checkout, and its patterns apply relative to the worktree. The worktree's own `.git` file and `.claude` folder stay protected, and a write from the worktree into the main checkout is refused as outside the worktree. A folder the agent made up has no `.git` file, because the hook refuses `.git` targets. This rule applies to Claude Code only.

Answers: Claude Code and Copilot get the empty object `{}` for an allowed call, which leaves the decision to the harness's own permission settings. Cursor's hook page requires `permission` in every answer and blocks the action on an answer that does not match its schema, so in Cursor an allowed call gets `{"permission": "allow"}`.

The package places a default policy at `.baltor/step/guard-workspace-file-writes.json`. It protects files that widen a later session's authority: `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` and `GEMINI.md` at any depth, `.cursorrules`, `.mcp.json`, `.vscode/**`, the `.agents`, `.codex`, `.gemini` and `.opencode` folders, `opencode.json`, the Copilot instruction, prompt, agent and skill files under `.github`, `.github/workflows/**`, `.gitattributes`, `.gitmodules`, `.pre-commit-config.yaml` and `.husky/**`. It reopens `.baltor/step/handoff.md`. The host replaces the file with the step's own policy before launch and should keep these entries unless the step's task is to change one of those files.

## Authoring basis and sources

Original code and text. Sources at the pinned revision: `catalogue_packages.py` (package format), `workspace_local.py` and `WORKSPACE-BACKENDS.md` (this repository confines file operations to one resolved root), and the starter item `review_file_paths_for_traversal_and_link_escape` (resolve before checking containment; refuse links). Claude Code event and answer fields follow https://code.claude.com/docs/en/hooks. The worktree behavior follows https://code.claude.com/docs/en/worktrees and the hook reference, read on September 24, 2026: worktrees are created under `.claude/worktrees/<name>/`, `${CLAUDE_PROJECT_DIR}` stays at the project root, and `cwd` follows Claude. The Cursor names `preToolUse`, `tool_name` values `Write` and `Delete`, `failClosed` and `permission` were read from a snapshot of Cursor's hook page in the locally cloned outside project madebywild/agent-harness (`docs/cursor-hooks.md`, revision 2ecf44f), for names only, and checked against Cursor's hook page on September 24, 2026. Neither documents the Cursor `Write` input field that holds the path; the hook reads `file_path`, then `path`, and refuses when neither exists. Copilot `preToolUse`, `toolName`, `toolArgs`, `create`, `edit` and `permissionDecision` match GitHub's hooks configuration reference as read on September 24, 2026; the `path` field inside `toolArgs` is the producer's reading.

## Inputs and outputs

Input: one hook event as JSON on standard input (at most 1 MiB) and the policy file `.baltor/step/guard-workspace-file-writes.json` (record `workspace_write_guard/v1`). Arguments: `--harness`, optional `--root` and `--policy`, and `--check-policy` for the host (exit 0 valid, 1 refused). Output: one JSON object, exit 0: the allowed answer of the harness or its refusal naming the path and the rule.

## Effects

The hook reads standard input, the policy and file metadata (`stat` and link resolution). It writes nothing. Declared: `reads_fs`, `spawns_process`, and `writes_fs` only because the tests build small workspaces with links inside temporary folders. The host must bind a trusted `python3`.

## Closest existing items

The starter item `review_file_paths_for_traversal_and_link_escape` is code review prose for application code that joins paths; this package is a hook that enforces containment on the agent's own writes. `workspace_local.py` confines typed file operations inside this repository's runtime, not a customer harness. The Codex `focused_brief_plugin` hook refuses nothing. The wave 5 rule `raw_data_stays_read_only` asks the model to leave raw data alone; this hook enforces any declared protected pattern, raw data included. The wave 5 settings fragments `workspace_write_no_network_settings` and `data_step_scoped_write_settings` express fixed write scopes as native harness permission rules with no hook process; this hook reads a per-step policy and checks the resolved target, links and hard links included.

## Positive example

A `Write` to `/work/src/app.py` gets `{}`. A write to `.baltor/step/handoff.md` passes when the policy lists it in `writable_globs`. In a Claude Code worktree session whose `cwd` is `.claude/worktrees/feature-a`, a write to `.claude/worktrees/feature-a/src/app.py` passes.

## Known-wrong example

`src/settings.txt` is a symbolic link to `.git/config`. A guard that checks only the typed path passes it, and the write changes the repository configuration. This hook refuses it. The critic found two more wrong cases, both tested now: every write in a Claude Code worktree session was refused, and with the example policy `.mcp.json`, `.vscode/settings.json`, `AGENTS.md` and `CLAUDE.md` were writable.

## Harness placement and verification state

Claude Code: `.claude/settings.json`, `PreToolUse` with matcher `Write|Edit|MultiEdit|NotebookEdit`, merged; documented, not observed here. The current tools reference no longer lists `MultiEdit`; the name is kept for older versions and matches nothing in newer ones. Cursor: `.cursor/hooks.json`, `preToolUse` with matcher `Write|Delete` and `failClosed: true`; unverified, including the `Write` path field and whether an allow answer also skips Cursor's own approval. Copilot: `.github/hooks/guard-workspace-file-writes.json`, `preToolUse`; documented, unverified. The default policy goes to `.baltor/step/guard-workspace-file-writes.json` for all three. No harness binary was run. The samples use the checker's sandbox path `/work`; the tests rewrite it to a temporary folder.

## Customer requests

- "Make sure the agent can never edit files outside the repo, even through a symlink."
- "Keep the overnight agent out of .git and out of my raw data folder."
- "Stop the agent from changing its own hook settings or its instruction files."

## Limits

Only the harness's file tools are checked. Writes made by shell commands, `PowerShell`, `Monitor` commands, protocol server tools or programs the agent starts are not seen; pair this hook with the shell command allowlist of this wave and an operating system sandbox. A link changed between the check and the write is a race this hook cannot close. Protected patterns match without regard to case, so they can refuse more than intended on a case-sensitive file system. A worktree placed outside `.claude/worktrees/` by a `WorktreeCreate` hook is not recognised, so writes there are refused as outside the workspace. Check history: every checker run is recorded in `review/PRECHECKS.txt`; the critic's probe is `critic-a04_unattended_guard_hooks/probe_others.py`, and the repair's probe results, mutant runs and the failing run of the new tests against the earlier hook are kept in `repairer-a04_unattended_guard_hooks/successor-work/` of the wave folder.
