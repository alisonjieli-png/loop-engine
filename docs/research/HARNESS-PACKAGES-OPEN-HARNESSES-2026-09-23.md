# Task packages across open harnesses

Research date: September 23, 2026. This extends the
[native placement report](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md),
[independent instance experiment](HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md)
and [focused assignment packets](../../artifacts/focused-step-packet-2026-09-23/README.md).
The existing roadmap, especially S-6.44 and S-6.40, remains the task authority.
This report creates no product contract or approval.

## Findings that change the implementation choice

1. **Use a native launcher and a native entrypoint together.** The launcher sends
   the current task explicitly. The instruction entrypoint carries the bounded
   objective, first actions and important constraints. A companion state file is
   a referenced input, not a universal native session format.
2. **OpenCode should be the first additional full integration after the existing
   Codex and Claude work.** It already has a recorded isolated loading experiment,
   an Agent Client Protocol interface, native Model Context Protocol integration,
   and a programmatic server. Pi is a strong parallel test target for explicit
   context and typed tools, with a version-specific adapter.
3. **Do not flatten everything into SKILL.md.** OpenCode has executable plugins
   and tools; Pi has executable extensions and complete packages; Qwen has native
   extensions; ZCode has plugins and process hooks; OpenHands has plugins, hooks,
   tools and typed conversation configuration. A skill describes a procedure. It
   does not replace all those interfaces.
4. **A package standard is not a capability guarantee.** Qwen currently consumes
   the portable Agent Plugins v1 core but ignores its client namespaces. OpenHands
   also consumes its own namespace for hooks, agents and commands. The same
   portable package can therefore install in both while providing different
   behavior. Required capabilities must be checked before a step starts.
5. **Pin versions and test precedence.** Installed Pi is 0.73.1. Current upstream
   source declares 0.87.1 and has changed instruction discovery, trust and run
   lifecycle details. A newer documentation page cannot qualify the older binary.

These priorities are engineering recommendations based on integration fit and
existing evidence, not benchmark rankings or claims that another harness is bad.

## Runtime ownership

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The native harness remains an adapter used by its owning Loop. A package, session
identifier, transport, file or plugin is not a new executable graph vertex. The
existing assignment composer, trusted state snapshot and harness executor edge
are the integration points. Extend those instead of adding a second task runtime.

## Evidence scope and exact sources

| Project | Source inspected | Local execution in this research |
| --- | --- | --- |
| OpenCode | `anomalyco/opencode` revision `18ef3cc7c5a25b82114c953a80ccc09f4988f74e` and current official documentation | None. Earlier loading experiment used 1.18.32. |
| Pi | `earendil-works/pi` revision `8d897edaa69bf810fa6d14f854ce0cf101f11093`, package version 0.87.1 | Installed 0.73.1 resource-loader functions only, seven checks, no model calls. |
| Qwen Code | `QwenLM/qwen-code` revision `69622ba7492b7f87d839385ab96abb7f057e45cc` | None. Documentation/source findings only. |
| ZCode | `zai-org/ZCode` revision `328c1a0c0ffaa5a4f65e8fa199af5e4c20706e5f` | None. Source reading only. |
| OpenHands | Backend `OpenHands/software-agent-sdk` revision `880043bdd62a0b54252985311128b81ba3e1a362`; frontend `OpenHands/OpenHands` revision `1c5fb85fa71f8b63227dfd217b9f909d167bebe0` | None. Documentation/source findings only. |
| Aider | Official conventions, scripting and option pages read September 23 | None. Documented explicit-file route only. |

The [source manifest](../../artifacts/harness-package-interoperability-2026-09-23/open-harnesses/source-manifest.json)
records immutable raw URLs, fetch times, byte lengths and SHA-256 values. Snapshots
are research input, not admitted intelligence or executable dependencies. Current
branch revisions are not claims about released package versions.

## How the assignment reaches each harness

| Harness | Required assignment delivery | Reusable resources | State and freshness recommendation |
| --- | --- | --- | --- |
| OpenCode | Explicit prompt over Agent Client Protocol, CLI or server; root `AGENTS.md`; `opencode.json` can list exact additional instruction paths | `.opencode/skills`, `.opencode/plugins`, `.opencode/tools`, native agent/command declarations, configured protocol servers | Create a fresh session for each step. A resumed or forked session carries native history and must be an explicit alternative. |
| Pi | Explicit RPC `prompt` or SDK `session.prompt`; native `AGENTS.md`, or explicit appended prompt with context discovery disabled | `.pi/skills`, `.pi/extensions`, prompt templates and Pi package resources | Use an in-memory or explicitly isolated session. Keep task state separate from Pi's session entry tree. |
| Qwen Code | Explicit headless prompt; project `QWEN.md` or compatible `AGENTS.md`; bounded imports where needed | `.qwen/skills`, native extension directories and portable Agent Plugins core | Isolate home/project memory; do not use continue/resume for a fresh step. Qualify memory controls for the exact version. |
| ZCode | Source supports root/ancestor `AGENTS.md`; actual launch binding still needs qualification | `.zcode/skills`, `.agents/skills`, configured plugin directories, process hooks and protocol servers | Confirm startup versus resume hooks, memory roots and exact native session binding before admitting an adapter. |
| OpenHands | Load project context into `AgentContext`; send the task to a configured conversation/workspace | Agent Skills, registered tools, plugins, hooks and subagent definitions | A new conversation is distinct from a restored conversation. Protocol delegation must qualify the delegated harness separately. |
| Aider | Explicit `--message-file` plus selected `--read` context files | Read-only context and selected editable files; no native skill/plugin equivalence established here | New history paths and no restored chat by default; the host owns task state and independent result checks. |

The following sections supply the exact behavior and its limits. No row asserts
that arbitrary `node_context.md`, `run-state.json` or `agents.state` automatically
loads, advances state, grants authority or validates a result.

## OpenCode: broad integration, specific discovery rules

### Instruction discovery and references

Official documentation supports project `AGENTS.md`, global OpenCode instructions
and a Claude-compatible fallback. Additional paths belong in the `instructions`
array of `opencode.json`. A textual `@node_context.md` mention in `AGENTS.md` is not
a native import. Use the explicit array when the entire file must be loaded, or
make reading it a deliberate first action. For a remote reference, fetch and bind
the approved bytes before launch rather than depend on a changing URL at startup.
[OpenCode rules](https://opencode.ai/docs/rules/)

Source is more precise than the documentation's short precedence summary. The
inspected `Instruction.systemPaths()` tries the **filename category** `AGENTS.md`
first, then `CLAUDE.md` when compatibility is enabled. `findUp()` returns every
matching path from the working directory through the worktree root. Once one
category has matches, subsequent categories are skipped. Thus a parent
`AGENTS.md` can suppress a closer `CLAUDE.md`. Paths are deduplicated by resolved
path, not by content digest. Nested instruction injection when a file is read
also tracks paths already loaded in messages. Baltor should reject ambiguous
selected entrypoints rather than depend on this subtle priority.
[Instruction source](https://github.com/anomalyco/opencode/blob/18ef3cc7c5a25b82114c953a80ccc09f4988f74e/packages/opencode/src/session/instruction.ts),
[filesystem traversal](https://github.com/anomalyco/opencode/blob/18ef3cc7c5a25b82114c953a80ccc09f4988f74e/packages/core/src/fs-util.ts)

### Skills, tools and executable activation

Skills expose metadata first, with the body available through the skill tool.
Supported native and compatibility locations include `.opencode/skills`,
`.claude/skills` and `.agents/skills`, plus corresponding global directories.
Project discovery reaches the worktree root. Unsupported frontmatter is ignored;
permissions can hide and reject a skill. Do not rely on an ignored metadata field
to enforce an effect constraint.
[OpenCode skills](https://opencode.ai/docs/skills/)

Local JavaScript or TypeScript plugins in `.opencode/plugins` load at startup.
Named npm plugins can be installed automatically by Bun. A generated plugin
declaration can therefore cause installation and execution, unlike a passive
Markdown reference. Resolve dependencies, pin packages and authorize these
effects before placing them in a discovery location.
[OpenCode plugins](https://opencode.ai/docs/plugins/)

Custom tools use JavaScript/TypeScript definitions in `.opencode/tools`, with Zod
argument schemas. A wrapper can call a Python implementation. The filename and
export determine native names; a custom name can override a built-in tool.
Reserve native names unless a reviewed override is explicitly selected. A
downloaded `bash.ts` can therefore change a core capability. The live documentation
page returned 503 during this research; the pinned official source supplied this
detail.
[Custom tools source documentation](https://github.com/anomalyco/opencode/blob/18ef3cc7c5a25b82114c953a80ccc09f4988f74e/packages/web/src/content/docs/custom-tools.mdx)

### Control and result collection

`opencode acp` offers JSON-RPC over standard input/output and preserves native
rules, tools and configured protocol servers. This aligns with the repository's
Agent Client Protocol first executor direction. Compatibility still requires
initialization negotiation and a tested cancellation/permission path.
[OpenCode Agent Client Protocol](https://opencode.ai/docs/acp/)

The native HTTP server exposes session creation, messages, events, abort and
forking. Its OpenAPI endpoint is useful for generating a pinned client. A remote
server's workspace paths refer to the server's filesystem, so uploading a file
and setting the correct workspace are separate operations.
[OpenCode server](https://opencode.ai/docs/server/)

CLI source has separate new, continued and forked session paths and explicit file
attachments. Remote attachment rejects a local directory when no shared
filesystem exists. Prefer a complete materialization manifest over an accidental
mixture of local paths and remote references.
[CLI run source](https://github.com/anomalyco/opencode/blob/18ef3cc7c5a25b82114c953a80ccc09f4988f74e/packages/opencode/src/cli/cmd/run.ts)

## Pi: explicit resources and a material version difference

### New observation against installed 0.73.1

The new [seven-case observation](../../artifacts/harness-package-interoperability-2026-09-23/open-harnesses/pi-loader-observation-2026-09-23.json)
invoked the installed discovery functions against temporary synthetic files.
Every check passed:

- `node_context.md` and `run-state.json` alone were ignored.
- `AGENTS.md` won over `CLAUDE.md` in the same directory.
- `AGENTS.override.md` was ignored by this installed version.
- An ancestor `AGENTS.md` above a synthetic git root still loaded.
- Selected global context preceded ancestor context and working-directory context.
- Removing `AGENTS.md` activated the `CLAUDE.md` fallback.
- Two explicitly supplied skills with the same name kept the first and emitted
  a collision diagnostic.

This is direct native loader evidence. It does not prove a model request, a
complete CLI launch, hook execution, task use or accepted output. The source
module digest is in the observation. No package was installed and no provider or
model was called. The earlier experiment separately captured Pi prompt loading.

### What current upstream adds

Current 0.87.1 documentation names `AGENTS.override.md` before `AGENTS.md` and
`CLAUDE.md`. The override applies only within its own directory; it does not
erase other ancestor context. Project `.pi` configuration now requires project
trust, while context-file discovery does not. `SYSTEM.md` replaces the normal
system prompt; `APPEND_SYSTEM.md` extends it. They are powerful configuration
inputs, not innocuous filenames to scatter through a packet.
[Pi configuration](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/docs/configuration.md)

The current resource loader still traverses ancestor context to the filesystem
root, with a special case preventing duplicated main-worktree instructions for a
nested linked worktree. This special case is not a general isolation boundary.
Its reload path rebuilds resource discovery while preserving the resolved trust
state. Use an explicit resource allowlist or the existing clean-root strategy.
[Pi resource loader](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/src/core/resource-loader.ts)

### Complete packages and typed tools

Pi packages group extensions, skills, prompt templates and themes using
conventional directories or explicit `package.json` paths. Local paths can load
resources without copying; npm/git sources can install dependencies. Distribution
should preserve the complete reviewed package and its dependency binding. A
local symlink or mutable directory is not an immutable approved release.
[Pi packages](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/docs/packages.md)

Extensions execute inside Pi's process. They can register typed tools and lifecycle
handlers, modify context and persist session entries. Current tool definitions use
TypeBox parameter schemas; result `details` can support state reconstruction.
Extension state stored with `appendEntry()` is excluded from model context, while
`sendMessage()` can store model-visible content. These are different channels.
Do not place a state value into one and assume it appeared in the other. Branch
state should be reconstructed from the active branch, not abandoned entries.
[Pi extensions](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/docs/extensions.md)

For a TypeScript host, the SDK can supply `cwd`, session manager, resource loader,
tools and model runtime explicitly. `SessionManager.inMemory()` avoids persistent
session files. This is a cleaner selection boundary than filling a real user's
home with packages. Replacing a session runtime requires rebinding subscriptions;
writing directly to an agent's message array does not replace authoritative
persisted context.
[Pi SDK](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/docs/sdk.md)

For the Python engine, use the qualified version's subprocess RPC adapter.
Current RPC uses strict newline-delimited JSON, request identifiers and streamed
events. A successful `prompt` response means acceptance or queuing, not completion.
Current docs distinguish `agent_end` from final `agent_settled`, because retries
and queued work can follow. These exact events must be negotiated by version;
never wait forever for a newer event an older binary does not produce.
[Pi RPC](https://github.com/earendil-works/pi/blob/8d897edaa69bf810fa6d14f854ce0cf101f11093/packages/coding-agent/docs/rpc.md)

Pi remains a good small-model experiment target. Native Model Context Protocol
support was absent in the tested 0.73.1 instance. A bridge extension is a separate
engine with its own process, credential, cancellation and tool-schema checks.
Neither a `.mcp.json` file nor a skill pretending to configure it supplies that
bridge.

## Qwen Code: compatible files, explicit enablement, portable subset

Current documentation says project `QWEN.md` and compatible `AGENTS.md` are read.
`@path` imports resolve relative to the containing instruction file. Local
`.qwen/QWEN.local.md` follows shared project instructions. Automatic memory has
its own per-project storage and is enabled by default; optional team-memory sync
can perform git operations. A fresh Baltor step needs explicit memory and sync
settings in its isolated configuration, with no inference from an empty task
directory alone.
[Qwen memory](https://github.com/QwenLM/qwen-code/blob/69622ba7492b7f87d839385ab96abb7f057e45cc/docs/users/features/memory.md)

Native project skills use `.qwen/skills`. Skills from extensions have registered
owner-prefixed names, and enabled/disabled settings must address the registered
identity. Qwen's native name validator is more permissive than the portable
Agent Skills convention. Baltor should keep portable names conservative and
store exact native registered identities separately from package identity.
[Qwen skills](https://github.com/QwenLM/qwen-code/blob/69622ba7492b7f87d839385ab96abb7f057e45cc/docs/users/features/skills.md)

Native extensions use `qwen-extension.json`, context, skills, commands and other
resources. Interactive extension changes can reload immediately, while separate
CLI management changes reach existing sessions on restart. Configuration wins
over an extension when both name the same protocol server. Cross-format conversion
is a transform that needs a new rendered digest and compatibility evidence.
[Qwen extensions](https://github.com/QwenLM/qwen-code/blob/69622ba7492b7f87d839385ab96abb7f057e45cc/docs/users/extension/introduction.md)

Agent Plugins v1 preserves portable files instead of generating a native manifest.
Its Qwen implementation supports skills in immediate subdirectories plus standard input/output
and Streamable HTTP protocol servers. It ignores commands, agents, hooks,
workflows and client namespaces; legacy Server-Sent Events servers are skipped.
The experimental `allowed-tools` string grants no pre-approved Qwen tools.
Therefore admission of a portable package must state whether ignored content is
optional. Refuse the run when an ignored hook enforces a required contract.
[Qwen portable plugin support](https://github.com/QwenLM/qwen-code/blob/69622ba7492b7f87d839385ab96abb7f057e45cc/docs/users/extension/agent-plugins.md)

Headless mode supports explicit prompts, structured output and resume controls.
Budget semantics differ by interface: current docs say wall-time/tool-count
settings cover single-shot and stream-JSON input, but not daemon Agent Client
Protocol sessions. Stream input resets these budgets per message. A host-level
ceiling remains necessary across messages and retries. Safe mode disables the
customizations a package may need, so it is a diagnostic control rather than a
complete package launch recipe.
[Qwen headless](https://github.com/QwenLM/qwen-code/blob/69622ba7492b7f87d839385ab96abb7f057e45cc/docs/users/features/headless.md)

## ZCode: real source, still needs native qualification

The official `zai-org/ZCode` repository now exposes the CLI implementation.
Earlier absence of a Baltor adapter should be described as **unqualified for this
integration**, not as evidence that ZCode cannot consume packages.

The pinned context adapter defaults to `AGENTS.md`, searches from the working
directory to the detected project root and picks the nearest matching file. It
also merges `~/.zcode/AGENTS.md` before workspace instructions. The default
100 KiB limit is per source and reports truncation. Instruction loading happens
when `userInstructions` is supplied in the request; the complete launcher binding
still needs observation. Do not claim `CLAUDE.md`, all ancestor rules or an
arbitrary state filename work by default.
[ZCode context adapter](https://github.com/zai-org/ZCode/blob/328c1a0c0ffaa5a4f65e8fa199af5e4c20706e5f/apps/zcode-cli/packages/adapters/src/context/index.ts)

Skill roots include `.zcode/skills` and `.agents/skills`. Native and compatible
roots are combined, not mutually exclusive fallbacks. The inspected resolver
orders explicit roots, user roots and then working-directory-to-worktree roots.
The scanner handles the root skill and one subdirectory level. It does not
make arbitrary deep category nesting portable. Plugin scanning refuses symlinks;
ordinary user skill roots can follow them. These differences belong in the
placement profile and known-wrong tests.
[ZCode skill roots](https://github.com/zai-org/ZCode/blob/328c1a0c0ffaa5a4f65e8fa199af5e4c20706e5f/apps/zcode-cli/packages/adapters/src/skills/roots.ts),
[skill scanning](https://github.com/zai-org/ZCode/blob/328c1a0c0ffaa5a4f65e8fa199af5e4c20706e5f/apps/zcode-cli/packages/adapters/src/skills/scan.ts)

ZCode's CLI guide documents `.zcode-plugin/plugin.json`, configured local plugin
directories, skills, commands and protocol servers. Standalone `.mcp.json` outside
an enabled plugin is not auto-discovered. Hooks use the main configuration and
are disabled by default. `SessionStart` can add context; process hooks use JSON
input/output and argv execution. Most malformed output, timeouts and nonzero
exits are recorded as failures without terminating the turn; exit code 2 is an
explicit block. A hook failure must therefore not be the sole enforcement of a
Baltor prerequisite. The host should validate required state before launch.
[ZCode CLI guide](https://github.com/zai-org/ZCode/blob/328c1a0c0ffaa5a4f65e8fa199af5e4c20706e5f/apps/zcode-cli/README.md)

Recommended next proof: build or install a separately pinned approved binary,
isolate all roots, disable unselected bundled plugins, render a small task packet,
capture its native model input without a provider, then test one bounded task
under existing model authority. No installation or execution of ZCode occurred
in this research.

## OpenHands and Aider: two useful, different interfaces

### OpenHands

Current OpenHands separates frontend from its Software Agent SDK. The backend
owns conversation, tools, skills and plugin semantics. `load_project_skills()`
loads working-directory and repository-root material with working-directory
precedence and names `.agents/skills` before legacy OpenHands locations. Nested
instruction files become directory-scoped rules. Use the actual pinned API:
the inspected function parameter is `work_dir`, even where a documentation
example shows another spelling.
[OpenHands project skill loader](https://github.com/OpenHands/software-agent-sdk/blob/880043bdd62a0b54252985311128b81ba3e1a362/openhands-sdk/openhands/sdk/skills/skill.py)

Always-loaded context, keyword activation, progressive skills and path-triggered
rules are distinct mechanisms. File-touch rules are injected after a matching
tool action, not at initial assignment time. Current documentation says those
rules do not fire for Agent Client Protocol delegated conversations because the
remote agent owns tool execution. Do not rely on a parent OpenHands rule to
enforce a delegated native harness's behavior.
[OpenHands skill guide](https://docs.openhands.dev/sdk/guides/skill)

The portable plugin loader places OpenHands-only hooks, agents and commands under
`dev.openhands/`, with corresponding manifest namespace metadata. Other client
namespaces are ignored. This offers a model for one immutable package with
declared optional client components, while preserving a small portable core.
Its existence does not make those components work in Qwen's portable loader.
[OpenHands portable format source](https://github.com/OpenHands/software-agent-sdk/blob/880043bdd62a0b54252985311128b81ba3e1a362/openhands-sdk/openhands/sdk/plugin/format/agent_plugins.py)

Native plugins are useful for packaging hooks, skills and protocol servers.
Conversation persistence is a separate API. Restore native conversations only
when resumption is explicitly selected and the package/state binding still
matches. A fresh conversation plus bounded task state is the initial Baltor
choice.
[OpenHands plugins](https://docs.openhands.dev/sdk/guides/plugins),
[conversation persistence](https://docs.openhands.dev/sdk/guides/convo-persistence)

### Aider

The supported documented route is explicit: `--read node_context.md` adds
read-only context, while `--message-file` supplies the task and exits after the
reply. `.aider.conf.yml` can list read-only files. This can consume a useful task
packet without native Agent Skills discovery. Avoid claiming native plugin,
hook or Agent Client Protocol equivalence from this evidence.
[Aider conventions](https://aider.chat/docs/usage/conventions.html),
[scripting](https://aider.chat/docs/scripting.html)

Read-only chat treatment does not establish operating-system confinement.
Editable files, git commits, history restoration and shell effects need separate
host policy. Explicit `--no-auto-commits`, `--no-dirty-commits` and
`--no-restore-chat-history` choices are useful for a controlled candidate adapter.
`--load` executes slash commands from a file and must not be used for an arbitrary
reference document.
[Aider options](https://aider.chat/docs/config/options.html)

## Suggested improvements to the existing packet design

These are proposals for the existing owning boundaries, not approved schemas.

| Boundary | Initial choice | Ordered fallback and reason | Discriminating test |
| --- | --- | --- | --- |
| Assignment composer | Objective, first actions, output location and bounded acceptance criteria in the native entrypoint and explicit launch request | Add a small exact instruction file through the native explicit mechanism; otherwise choose another qualified adapter | Leave all auxiliary files but remove the entrypoint/launch task. Required markers must disappear or launch must refuse. |
| Materialization | One immutable source package, one selected rendering, exact relative paths and hashes | Another qualified rendering of the same logical package; otherwise report incompatibility | A required hook ignored by the chosen format must make the package ineligible, even when skills load. |
| Discovery | Isolated home, configuration and clean ancestor root; explicit selected resources where supported | Clean native project discovery with captured inventory; otherwise another adapter | Plant global/ancestor decoys and same-name resources. Neither may silently become the selected capability. |
| State binding | Host-owned expected run/step identity, context version and state version; read-only snapshot in task packet | Host-validated new snapshot; then explicit qualified native resume only when requested | Supply a newer package with an older session/state binding. Refuse before any model or tool effect. |
| Output contract | Host validation of schema plus independent acceptance | Bounded repair through the existing repair path; no silent coercion | Schema-valid but wrong result fails acceptance; invalid output cannot become success because the CLI exited zero. |
| Engine selection | Pin binary identity/version, package format, load mechanism and required capabilities | Next eligible engine in declared order | Switch to a version that ignores override files, changes completion events or lacks a hook. Negotiation must refuse or select a qualified alternative. |
| Credentials and tools | Brokered handles or process-scoped credentials outside package bodies | Approved local protocol/tool bridge with the same authority; otherwise unavailable | A downloaded package cannot widen tool scope, choose a secret path or select a new provider merely by declaring metadata. |

### Proposed package loading record

Extend the existing placement record with observed facts, rather than add another
state store:

- Which required resources were materialized, discovered, loaded and activated.
- Exact native tool, skill, command and agent names after namespaces are applied.
- The initialization protocol and capabilities negotiated for that process.
- Context source order, bytes before truncation, bytes actually included and
  unselected built-ins that remain present.
- Declared reload policy: frozen for one step, restarted process, or explicit
  qualified reload with a new binding.
- Native session identifier and whether it was new, resumed, forked or restored.
- Completion evidence separate from accepted task output.

Default to a frozen package per step. Hot updates may be useful for interactive
sessions, but should create a new manifest binding and rerun discovery checks.
Do not rewrite context halfway through a tool action and call it the same task.

### Qualification ladder

1. Parse and validate exact package bytes, paths, dependencies and rights.
2. Verify native discovery and collision behavior without a model.
3. Capture native prompt/tool inputs without sending to a provider.
4. Execute a bounded deterministic hook/tool and prove its negative controls.
5. Run a bounded model task and record actual use and usage.
6. Independently accept the result against the same task contract.

The first four stages can establish loading and effects. Only the final stages
can support customer claims that a harness used the material successfully. A
library of millions does not require injecting millions of descriptions into
every process; central search selects a small, measured subset before launch.

## Specific compatibility checks to add

| Check | Known-wrong setup | Expected result |
| --- | --- | --- |
| OpenCode filename precedence | Ancestor `AGENTS.md`, nearer `CLAUDE.md`, distinct markers | Record the native selection; reject a placement plan that expected the nearer marker without an explicit binding. |
| Native import difference | `@node_context.md` in OpenCode instructions versus a Qwen instruction file | OpenCode needs explicit configured loading; qualify Qwen's import separately. No common import assumption. |
| Pi version handshake | Require `AGENTS.override.md` on installed 0.73.1 | Refuse unsupported requirement; the existing seven-case observation proves the marker is absent. |
| Completion semantics | Treat successful RPC prompt acknowledgment as accepted work | Check must fail before final native events and host acceptance arrive. |
| Portable plugin subset | Put a required hook only in `dev.openhands/`; choose Qwen portable loader | Refuse capability mismatch, even if the skill is visible. |
| State freshness | Reuse native session history after task identity or input digest changes | Refuse implicit resume and render a new task packet. |
| Truncation | Place a required exit condition beyond a native context limit | Refuse incomplete assignment; do not silently accept a truncated instruction. |
| Resource topology | Hide a selected ZCode skill beneath two category folders | Discovery must fail; keep its native placement shallow or declare a qualified explicit root. |
| Duplicate names | Global skill and selected project skill share a registered name | Collision policy must be explicit and observed; no silent first/last-wins promotion. |
| Native tool replacement | A selected OpenCode tool exports the built-in name `bash` without declared override authority | Refuse admission or placement before native discovery replaces the built-in. |
| Hook failure behavior | Mandatory prerequisite hook times out or returns malformed JSON | Host blocks launch/continuation even when the native harness would record a warning and proceed. |
| Reload boundary | Replace package bytes during an active tool action | Refuse changed digest or finish under the frozen binding; never infer an approved hot reload. |
| Local endpoint meaning | Remote/container harness receives `127.0.0.1` provider URL | Diagnose endpoint locality; negotiate a scoped bridge instead of assuming the user's host is reachable. |

No model experiments, installations, customer configuration changes or live
service mutations were performed in this research. New findings should be
incorporated into the existing roadmap and adapter qualification records.
