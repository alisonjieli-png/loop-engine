# Task package interoperability: Claude Code and editor harnesses

Research date: September 23, 2026. Scope: Claude Code, Gemini CLI, GitHub
Copilot, Cursor and Cline. Official documentation was retrieved on this date.
These are documented capabilities, not newly qualified Baltor integrations.
No model call, installation or user configuration change was made for this
research. Mutable documentation describes the retrieved state; qualification
must record the installed client version and configuration.

## Decision

Give every fresh harness its assignment through its native startup instruction
file **and an explicit launch prompt**. Keep reusable capabilities separately
addressable. A package should declare which files supply mandatory context,
which files are optional resources, and which files can execute code. An
arbitrary `node_context.md`, `run-state.json` or `agents.state` is not a
universal startup interface.

Use the existing [focused assignment packet](../../artifacts/focused-step-packet-2026-09-23/README.md)
as the starting point. It already places the objective, first actions, current
state and output requirements inside the native instruction entrypoint. Its
Codex 0.155.1 prompt-input probe established pickup, not accepted task results.
The [native plugin candidate](../../artifacts/harness-plugin-context-2026-09-23/README.md)
established Claude Code 2.1.280 plugin discovery and startup-hook execution
without a model call. Neither result qualifies another client.

## What loads first

| Surface | Initial package entrypoint | What follows later | First qualification priority |
| --- | --- | --- | --- |
| Claude Code CLI | `CLAUDE.md` with an explicit local `@AGENTS.md` import, plus launch prompt | Skills, scoped rules, agents and commands when selected; hooks at registered events | First in this report: builds on existing native plugin evidence |
| Gemini CLI | `GEMINI.md`, or host-configured `context.fileName`, plus launch prompt | Just-in-time directory context; skill activation; extension resources | Next: clear inspectable context and native headless interface |
| Copilot CLI | `AGENTS.md` or `.github/copilot-instructions.md`, plus launch prompt | Path rules, skills, selected agents and hooks | Next, separately from Copilot cloud and IDE |
| Cursor Agent | Root `AGENTS.md` or `.cursor/rules/*.mdc` with `alwaysApply: true`, plus submitted task | Relevant rules/skills and directory instructions | Editor qualification after CLI paths |
| Cline | Root `AGENTS.md` or unconditional `.clinerules/*.md`, plus submitted task | Conditional rules and skill activation | Plain packet first; executable hooks need more current source qualification |
| Copilot cloud agent | Repository instruction files in its cloned checkout, plus assigned task | Supported cloud skills/agents/hooks | Separate remote integration, not a local-directory adapter |
| Copilot in VS Code | Depends on selected harness: Copilot Agent Host, Claude, Codex or Local | Harness-specific activation | Test the selected harness, not only the editor version |

Paths and loading claims are supported in the product sections below. Priority
is an engineering recommendation based on existing evidence and interface
clarity, not market share or comparative quality.

## Claude Code

### Startup context and precedence

`CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md` supply project context;
user and managed files also contribute. Ancestor files concatenate from broad
to narrow scope; nested files load when their directories are read. An import
such as `@AGENTS.md` expands at startup; prose saying “read AGENTS.md” depends
on the model taking that action. Imports permit four recursive hops. Guidance
targets fewer than 200 lines per instruction file, not a hard file-size limit.

Direct `AGENTS.md` loading starts at version 2.1.277, but normally only when
no project/ancestor Claude instruction file exists. Feature-flag availability,
provider, telemetry configuration, first session after upgrade and the built-in
plugin can change this. `AGENTS.override.md` is not read. The explicit
`CLAUDE.md` import remains documented and is deduplicated. Direct AGENTS loading
does not emit `InstructionsLoaded`; imports do. Do not use auto memory's
200-line/25-KB startup limit as a limit on the assignment packet.
[Claude Code memory reference](https://code.claude.com/docs/en/memory).

### Capabilities and execution

Project skills use `.claude/skills/<name>/SKILL.md`; scripts and resources can
remain beside it. Skill metadata is initially listed; invocation adds the
body. The current listing budget scales with context size, and descriptions
can be shortened. Importantly, `allowed-tools` pre-approves listed tools for
the invoking turn; it does **not** restrict the available tool set. A package
with that field needs an effects review, even if its prose sounds read-only.
[Claude Code skill reference](https://code.claude.com/docs/en/skills).

The existing plugin candidate demonstrates `.claude-plugin/plugin.json`,
`commands/`, `agents/`, `hooks/hooks.json`, tools and contracts. Its contracts
are resources used by an explicit checker; their presence does not make the
harness enforce them. Native plugin layouts and standalone project layouts
are different. Keep installation or explicit plugin binding in the adapter.
[Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference).

CLI `-p` supplies the actual request. `--json-schema` validates structured
final output in print mode, with `format` treated as an annotation; the host
still needs semantic acceptance. `--strict-mcp-config` scopes selected MCP
configuration. `--no-session-persistence` and explicit session identifiers
control transcript persistence. `--safe-mode` disables customizations, so it
cannot prove packet loading. `--settings` overrides specified keys but keeps
unspecified file-derived settings; it is not complete configuration isolation.
[Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference).

### SDK difference

Current Agent SDK documentation says default `query()` includes project and
user setting sources. Explicit `settingSources`/`setting_sources` determines
which instruction files load; an empty list suppresses them. This loading is
independent of choosing the `claude_code` prompt preset. Pin the setting
sources, working directory and permissions instead of relying on defaults.
The SDK also documents an optional stable system-prompt layout for caching
across working directories, with version requirements. That is a possible
efficiency experiment for fresh harnesses, not measured Baltor savings.
[Agent SDK system-prompt documentation](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts).

## Gemini CLI

### Context and skills

`GEMINI.md` content is concatenated from user, workspace and relevant directory
sources. Directory context can load just in time when tools access files.
`/memory show` displays the combined content and `/memory reload` rescans it.
`@file.md` imports support modular context. `context.fileName` can explicitly
select `AGENTS.md` or a list; the default filename remains `GEMINI.md`. The
retrieved page does not specify a universal hard context-file size ceiling.
[Gemini context files](https://geminicli.com/docs/cli/gemini-md/).

Skills are discovered in `.gemini/skills/` and `.agents/skills/`, with user
equivalents. Workspace wins over user, which wins over extensions and built-ins;
`.agents/skills/` wins over `.gemini/skills/` within the same tier. Startup
loads names/descriptions. `activate_skill` requests activation, then the body
and folder structure enter context after consent; bundled resources become
readable. That is a meaningful difference from assuming a skill is immediately
active because its directory exists.
[Gemini skills](https://geminicli.com/docs/cli/skills/).

### Extension, launch and state interfaces

Installed extensions live under `~/.gemini/extensions/` and use a root
`gemini-extension.json`. They can supply context, MCP servers, `commands/*.toml`,
`hooks/hooks.json`, `skills/`, `agents/*.md` and `policies/*.toml`. Subagents
are documented as preview. Extension policies cannot self-grant `allow` or
`yolo`. Extension management changes require a restarted session. Referenced
environment variables require the declared settings allowlist.
[Gemini extension reference](https://geminicli.com/docs/extensions/reference/).

`gemini -p` supplies a headless request. JSON output contains a response and
statistics; that transport envelope does not prove the task response matches
our own schema. Streaming output offers initialization, tool and result events.
The host must validate its own result contract.
[Gemini headless reference](https://geminicli.com/docs/cli/headless/).

`--resume` reloads prior conversation state; native history is stored by project
under `~/.gemini/tmp/<project_hash>/chats/`. A new focused step should use the
host's selected state snapshot, not blindly resume the last transcript.
[Gemini session management](https://geminicli.com/docs/cli/session-management/).

Folder trust is documented as disabled by default. When enabled, an untrusted
headless workspace fails rather than displaying a prompt. Project settings,
environment loading and MCP behavior depend on trust. A temporary directory
alone therefore does not establish isolation or trust.
[Gemini trusted folders](https://geminicli.com/docs/cli/trusted-folders/).

## GitHub Copilot: separate the three surfaces

### CLI instruction behavior

Copilot CLI reads repository `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md` and applicable `.github/instructions/**/*.instructions.md`.
User sources and additional configured directories can contribute. Applicable
instructions combine; the CLI guide does not define a general precedence
order. The guide says `@` imports in AGENTS, Claude and Copilot instruction
files must stay inside their repository/custom-instruction root, and imports
are not expanded in GEMINI or path-specific instruction files. Restart or
resume is required to pick up changed files.
[Copilot CLI instruction guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions).

The CLI reference has a conflicting statement permitting absolute imports.
Treat external import behavior as **disputed**, use confined relative paths,
and test the installed release. More consequentially, custom subagents do
not inherit repository instructions unless `include-custom-instructions: true`;
the default session agent and general-purpose subagent do, while several
specialized built-ins do not. `--no-custom-instructions` suppresses them.
`-p` provides programmatic tasks. `--continue` can fall back to a globally
recent session, making it unsuitable for selecting the next independent step.
Use an exact session identity only when resuming that same authorized step.
[Copilot CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference).

### Skills, plugins and agents

Project skills can live in `.github/skills/`, `.claude/skills/` or
`.agents/skills/`; personal locations include `~/.copilot/skills/` and
`~/.agents/skills/`. Scripts and examples are supported resources, and the
entry file must be exactly `SKILL.md`.
[Copilot CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).

Agent Plugins 1.0 uses a root `plugin.json` with the canonical `$schema`,
portable `skills/<name>/SKILL.md` and root `mcp.json`. Copilot-specific agents,
hooks and other extensions live under `com.github.copilot/`. The separately
supported older Copilot manifest allows configurable component paths. Thus a
Claude plugin manifest is not a universal package manifest.
[Copilot plugin authoring](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating).

Custom agent prompts have a documented 30,000-character maximum. An empty
`tools` list disables tools; omission permits all available tools. Unknown
tool names are ignored. `mcp-servers` in the profile is not used by IDE custom
agents, and GitHub cloud does not honor IDE `handoffs` or `argument-hint`.
Profile compatibility must include the target surface and actual tool
inventory, not just successful YAML parsing.
[Copilot custom-agent configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration).

### Cloud and IDE differences

Copilot on GitHub supports repository-wide and path-specific instructions;
its agent instructions give precedence to the nearest `AGENTS.md`. Root
`CLAUDE.md` or `GEMINI.md` are alternatives. This is a different documented
resolution description from the CLI's additive behavior.
[Copilot on GitHub instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions).

Cloud hooks come from `.github/hooks/*.json` in the clone and run in an
ephemeral Linux sandbox with restricted networking. The cloud job does not
ship local user configuration or installed plugins. CLI additionally loads
user, policy and plugin hooks. Hook event coverage differs, and CLI-only
`exec`/`args` avoids shell parsing. Neither successful local discovery nor a
local endpoint proves reachability from the cloud job.
[Copilot hook reference](https://docs.github.com/en/copilot/reference/hooks-reference).

VS Code now distinguishes Agent Host harnesses from its Local agent. Agent
Host follows the selected harness's rules. Local supports instruction settings;
nested AGENTS support is experimental and off by default. It also supports
file-pattern, task-relevance and explicit-attachment activation. Native
instruction support does not apply to inline suggestions. Record editor,
extension and selected harness versions separately.
[VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions).

## Cursor

Root and nested `AGENTS.md` are supported. Project rules require
`.cursor/rules/*.mdc`; plain `.md` files there are ignored. `alwaysApply: true`
loads every chat; other rules activate by glob, relevance description or
manual mention. Nested AGENTS instructions combine with parents and the more
specific instructions take precedence. Team, project and user rule guidance
has its own precedence. Under 500 lines is a recommendation, not a documented
universal hard byte limit. Rules do not govern Cursor Tab.
[Cursor rules](https://prod.cursor.com/docs/rules).

Skills use `.agents/skills/` or `.cursor/skills/`, plus supported compatibility
locations. Discovery is at startup; the agent or user invokes a skill. A
manual invocation attaches to one message; Custom Mode keeps it for a session.
Local `~/.agents/skills/` files are not automatically sent to Cloud Agents.
Only the documented personal Cursor-skill sync path is synced; a remote worker
needs repository or image-provided material.
[Cursor skills](https://prod.cursor.com/docs/skills).

Cursor supports root Agent Plugins `plugin.json` for portable skills and MCP,
and `.cursor-plugin/plugin.json` for richer rules, agents, commands, hooks and
variables. It explicitly does not expand the standard `${PLUGIN_ROOT}` and
`${PLUGIN_DATA}` in `mcp.json`. Secret variables are declared by schema and
configured separately. That is a concrete portability gap requiring adapter
rendering and an endpoint probe.
[Cursor plugin reference](https://prod.cursor.com/docs/reference/plugins).

Native `.cursor/hooks.json` hooks exchange JSON over standard input/output.
**`sessionStart` is fire-and-forget and cannot block startup**, including when
`continue` is false. Cloud agents run a documented subset of command hooks,
and hooks do not run in their early read-only environment. Mandatory assignment
validation must precede launch rather than depend on this event.
[Cursor hooks](https://prod.cursor.com/docs/hooks).

Third-party imports can load `.claude/settings.json` hooks and map event/tool
names. The compatibility page describes mappings and failed-hook behavior,
but its generic priority statement differs from the main hook page's
field-specific merge description. It also says Claude lacks `SubagentStart`,
which is stale relative to current Claude documentation. Treat compatibility
as a tested subset, not blanket equivalence.
[Cursor third-party hooks](https://prod.cursor.com/docs/reference/third-party-hooks),
[Claude hook events](https://code.claude.com/docs/en/hooks#hook-events).

Cursor also has a headless CLI: `agent -p` submits the request, and JSON or
streaming JSON exposes results. Its guide says print mode proposes changes
unless `--force` enables direct modification. This is a separate launch
binding from an editor chat, and its actual tool permissions still need a
versioned probe. Do not insert `--force` simply to make a loading test pass.
[Cursor headless CLI](https://prod.cursor.com/docs/cli/headless).

## Cline

Current documentation supports `.clinerules/` and `.cline/rules/` across
VS Code, Desktop and CLI; root `AGENTS.md` and global `~/.agents/AGENTS.md`
are also recognized. Global and workspace rules combine, with workspace
precedence for conflicts. `paths` frontmatter conditions rules; rules without
it are always active. Both native rule directories are searched, so copying
the same rule into both is unnecessary.
[Cline rules](https://docs.cline.bot/customization/cline-rules).

Skills live at `.cline/skills/<name>/SKILL.md` or `~/.cline/skills/`. Startup
loads metadata; `use_skill` or an explicit slash command loads the body.
Descriptions have a 1,024-character maximum. The documentation describes
roughly 100 metadata tokens and bodies under 5,000 tokens; these are guidance,
not proof of runtime truncation limits. Supporting documents/scripts are
accessed as needed. The retrieved page does not promise `.agents/skills/`
discovery, so do not assume it.
[Cline skills](https://docs.cline.bot/customization/skills).

The CLI documents `--cwd`, isolated `--data-dir`, `--config`, `--id` for
resume, `--hooks-dir`, JSON output and an Agent Client Protocol mode. It
also documents auto-approval defaulting to true for prompt runs. An adapter
must explicitly bind permissions, timeout and state location rather than
inherit that default. JSON output is a transport format, not our result
acceptance contract.
[Cline CLI reference](https://docs.cline.bot/cli/cli-reference).

The official November 2025 version 3.36 announcement specifies executable
hook files such as `.clinerules/hooks/TaskStart` and `TaskResume`. The current
hook documentation route returned only a shell page during this research,
while the current CLI exposes a different additional hook-directory setting.
These observations establish a historical feature and a current option,
not current cross-surface layout parity. Qualify hooks against pinned current
source and client versions before shipping a Cline executable variant.
[Cline 3.36 hook announcement](https://cline.bot/blog/cline-v3-36-hooks).

## Improvements to the Baltor package interface

These are proposed changes at existing materialization and harness executor
boundaries. They are not new runtime types or an admission decision.

1. **Declare launch requirements.** Record native entrypoint, working directory,
   client/version range, surface, operating system, required configuration,
   prompt binding and startup-loading expectations. Separate required features
   from optional components. Refuse required unsupported features.
2. **Render one target at a time.** Keep one content identity, then produce
   target-specific layout variants with exact digests. Avoid installing every
   compatibility filename, skill alias and hook registration into one workspace.
   Otherwise two clients can silently activate duplicate hooks or contradictory
   instructions.
3. **Validate before launch.** Check assignment identity, state/context version,
   exact package bytes, relative resource closure, executable dependencies,
   environment references and output contract before any startup hook executes.
   Keep the expected binding outside model-writable files.
4. **Use explicit first-turn input.** The initial request should name the current
   objective, expected packet identity and first action. Native instructions
   supply the details without requiring the model to guess which JSON file is
   its assignment. Do not overwrite a user's existing repository instructions.
5. **Separate state from memory.** A host-issued read-only state snapshot is
   input. Model edits are proposed state changes. Only validated host transitions
   become the next snapshot. Native transcript resume, compacted memory and a
   workflow checkpoint remain distinct operations.
6. **Count packages honestly.** The same skill rendered for five clients is one
   logical capability with five variants. A newly composed task packet is run
   context, not another persistent intelligence package.
7. **Measure the selection stage.** A huge installed skill list itself consumes
   context and can hide descriptions. Retrieve a bounded eligible subset before
   launching the step; measure missed relevant items and harmful false matches.
8. **Bind executable effects.** A script, startup hook or MCP process can execute
   before the model reasons about the assignment. Keep credentials out of bodies,
   references to credentials in typed host configuration, and working-directory
   confinement independent from prompt text. Folder trust is not an operating
   system sandbox.
9. **Record actual delivery.** Save selected item, materialized path/digest,
   native discovery, input inclusion, activation, tool execution and task result
   as separate facts using existing records. A hooks inventory is not evidence
   of use; a hook success is not evidence of useful context.

## Discriminating qualification cases

| Case | Expected distinction |
| --- | --- |
| Remove the native entrypoint but keep `node_context.md` | Objective marker disappears from startup input, unless an independently declared launch attachment supplied it |
| Keep only a prose pointer versus a native import | Native input inspection distinguishes immediate inclusion from possible later reading |
| Add an ancestor Claude instruction file | Direct AGENTS discovery changes according to the configured mode; explicit import remains present |
| Launch with user, project and local sources disabled in turn | Report exactly which source disappears; never call a minimal HOME complete policy isolation |
| Invoke a Copilot custom subagent with and without opt-in | Required context is either explicitly supplied or omission is detected |
| Rename Cursor `.mdc` to `.md` | Native rule discovery fails; file existence alone must not pass |
| Install a skill at the wrong client path | Discovery is absent, even though the skill validates structurally |
| Register the same hook in native and compatibility locations | Count executions and reject unintended double effects |
| Delay Cursor startup hook or return `continue: false` | The host's pre-launch validation still controls mandatory task readiness |
| Swap output schema or state after host validation | Refuse stale binding before effects, or create an explicit new authorized transition |
| Resume another session or change working directory | Reject session/run mismatch; do not rely on a global latest-session shortcut |
| Move a local package to a remote/cloud worker | Resolve package, interpreter, tool and endpoint there; localhost denotes that worker |
| Add a malformed rule, unknown agent tool or unsupported manifest field | Refuse required semantic loss even when a permissive native parser ignores it |
| Produce schema-valid but wrong output | Independent task acceptance fails while structural validation remains correctly reported as passed |

Start with deterministic/native no-model discovery probes. Then perform a
bounded real-model task under the existing explicit authority, recording model,
usage, effects and all attempts. Compare no packet, assignment only, assignment
plus selected resources, and assignment plus executable support on identical
tasks. The winning configuration maximizes accepted work within constraints;
it need not use the fewest files or shortest instructions.

## Research limits and handoff

Only Claude Code 2.1.280 and Codex 0.155.1 have relevant local observations in
the linked prior artifacts. This report did not observe Gemini, Copilot,
Cursor or Cline executing these candidate packets. Documented size guidance is
kept separate from enforced bounds; undocumented limits remain unknown.

Use this report as input to S-6.40 and S-6.44 and the existing harness executor
qualification work. The authoritative task state remains the roadmap. Do not
create a new approval store from this comparison or promote any package from
documentation compatibility alone.
