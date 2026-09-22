# Harness landscape and forks for Baltor

Kind: dated research record, prepared by a Claude Code research agent on September 22, 2026 and reviewed before commit. The roadmap remains the only task authority.

Research date: 2026-09-22. Every fact below was read on the page or repository file named beside it on that date, unless marked otherwise. Repository metadata (licence, stars, last push, latest release) came from the GitHub API on 2026-09-22. The web search tool was out of budget for this session, so pages were reached through the GitHub API and direct page fetches instead. Nothing in the Loop Engine repository was changed.

Roadmap step: S-6.42, "Harness landscape: forks of Pi and OpenCode, and independent instances in every supported harness" (`docs/roadmap/roadmap.yaml`, read 2026-09-22).

## 1. Answer first

1. **NVIDIA's Pi work is SoL-Pi from NVlabs.** It is not a hard fork that customers run. The public release is a standalone Pi extension (MIT) that installs on an unmodified Pi. Its own compatibility document says the research started on "the original Pi fork" based on Pi 0.81.1, and that the release replaced "fork-only" methods with public extension events. The lesson for Baltor: do research on a fork, ship through the extension surface.
2. **Pick Pi over OpenCode if Baltor forks anything.** Pi has an in-process SDK in which the host can supply its own resource loader, an in-memory session, a JSON-over-stdio RPC mode, a single-run print and JSON mode, and a rich extension API. NVIDIA, oh-my-pi and senpi all built on it. The largest OpenCode plugin project (oh-my-openagent) has started shipping a Pi-based engine as well.
3. **Do not start with a hard fork.** Nearly everything Baltor needs for a fresh harness per step can be done with Pi's SDK, extensions, and command-line flags, and with OpenCode's inline configuration, plugins and server. A hard fork costs real, ongoing merge work. Kilo, which forks OpenCode, runs a watcher every 30 minutes, keeps a merge-tooling folder, a merge agent, and a continuous integration check that every changed upstream line carries a marker.
4. **Recommended shape:** a "Baltor for Pi" Pi package (extension plus skills) and a thin distribution wrapper. Keep a research fork of Pi only for experiments, as NVIDIA did. Promote each proven change either into the extension or as an upstream proposal. Support OpenCode through a plugin plus inline configuration, not a fork.

## 2. NVIDIA's Pi work: SoL-Pi

| Fact | Source, read 2026-09-22 |
|---|---|
| Repository `NVlabs/SoL-Pi`, MIT, created 2026-09-02, about 2,890 stars, not a GitHub fork | GitHub API |
| "This repository contains the open-source version of SoL-Pi, a standalone extension for Pi. It is not an official distribution of Pi." | [README](https://github.com/NVlabs/SoL-Pi) |
| "SoL-Pi installs on top of an unmodified Pi release. Every mechanism is opt-in and disabled by default." Rule: "No Pi patches." | README |
| Tested against `@earendil-works/pi-coding-agent` 0.85.1 and 0.84.2. "Previous checks covered the public API surface of Pi 0.81.1, the base used by the original Pi fork." Online Context Compact "uses ordinary public `context` and `before_provider_request` handlers instead of fork-only post-transform observer methods." | [docs/compatibility.md](https://github.com/NVlabs/SoL-Pi/blob/main/docs/compatibility.md) |
| Paper: "SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness", Liu, Ye, Gao and others including Song Han, submitted 2026-09-17, arXiv 2609.20519 | [arXiv abstract](https://arxiv.org/abs/2609.20519) |
| Blog | [nvlabs.github.io/SoL-Pi](https://nvlabs.github.io/SoL-Pi/) (no publication date shown on the page) |

**The four mechanisms** (README and compatibility document):

| Mechanism | What it changes | Pi surface used |
|---|---|---|
| Action Fusion | An edit or write can run its follow-up check command in the same tool call, saving a model round trip | Replaces the built-in `edit` and `write` tool definitions through `registerTool` |
| ObservationPack | Large repeated tool results become stable handles with exact paged recall (`obs_recall`) | `context` event projection; original bytes archived per session |
| Evidence-Preserving Reducer | A cheaper model reduces long logs to short evidence records; every kept quotation must match the archived source, otherwise the original result stays | `tool_result` event and the model registry |
| Online Context Compact | Completed plan steps become compaction points when the saving repays the cache rewrite cost | `update_plan` tool, native compaction, `agent_settled` |

**Measured results as reported by the authors** (not reproduced by Baltor):

- Blog, EdgeBench 51 tasks: about 94 percent of Pi's average score with 45 to 49 percent fewer tokens and about one third lower cost than Pi.
- Paper HTML, Table 1 (GPT-5.6 Sol): efficiency configuration 1.10 billion tokens (49.0 percent fewer than Pi), 894 dollars (33.2 percent lower), score 42.0 (93.7 percent of Pi). Performance configuration: 6.1 percent fewer tokens and a 5.3 percent higher score. Transfer to Opus 5: 44.7 percent fewer tokens, 33.5 percent lower cost.
- Blog, Terminal-Bench 4 (63 tasks): SoL-Pi solved 15 tasks for 211.12 dollars; Pi 18 for 286.45 dollars; Codex 18 for 272.35 dollars. So the efficiency comes with fewer solved tasks on that benchmark.
- Blog, method: 152 proposed ideas, 4 survivors; a separate reviewer agent checked each implementation; held-out results never fed back into repair. "Humans ... refactor[ed] discovered mechanisms into maintainable code."

**Related NVIDIA work:** `NVIDIA-NeMo/ProRL-Agent-Server` ("Polar: Agentic RL on Any Harness at Scale", arXiv 2605.24220) ships launcher presets for `claude_code`, `codex`, `gemini_cli`, `opencode`, `openhands_sdk` and `pi`, routing each through a model proxy by environment variables or configuration keys ([agent README](https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/main/src/polar/agent/README.md), read 2026-09-22). `NVIDIA/NemoClaw` runs agents inside NVIDIA OpenShell, which Pi's own README lists as a sandbox pattern.

**What this means for Baltor.** SoL-Pi attacks the same waste Baltor's north star names: context replay, oversized observations, and frontier-model turns spent on reading. It is MIT and composes with other Pi extensions. Baltor already pins Pi 0.85.1 in `embodiments/pi/`, the exact version SoL-Pi tests. Baltor can list SoL-Pi as a library item and measure it as one configuration in its own per-step runs. The author claims above are not Baltor evidence.

## 3. Harness comparison

All rows read 2026-09-22 from the named docs.

| Harness | Licence | Latest release | Instruction files | Skills | Extension points | Headless and server | Agent Client Protocol |
|---|---|---|---|---|---|---|---|
| Pi (`earendil-works/pi`, formerly `badlogic/pi-mono`) | MIT | v0.87.0, 2026-09-21 | `AGENTS.override.md`, `AGENTS.md`, `CLAUDE.md` in agent dir, working dir and parents; `SYSTEM.md`, `APPEND_SYSTEM.md`; `--no-context-files` | `~/.pi/agent/skills`, `.pi/skills`, `~/.agents/skills`, `.agents/skills` up to repo root; `--skill`, `--no-skills` | TypeScript extensions (tools, events, providers, commands, context transforms, compaction), Pi packages via npm or git | `--print`, `--mode json`, `--mode rpc`, in-process SDK, `--no-session` | Community adapter `svkozak/pi-acp` (692 stars); listed in ACP registry as `pi-acp` |
| OpenCode (`anomalyco/opencode`, formerly `sst/opencode`) | MIT | v1.18.32, 2026-09-21 | `AGENTS.md` walking up, else `CLAUDE.md`; global `~/.config/opencode/AGENTS.md`; `instructions` array with files, globs and URLs | `.opencode/skills`, `.claude/skills`, `.agents/skills` walking up to git worktree, plus global | Plugins with hooks (`tool.execute.before`, `experimental.chat.system.transform`, `experimental.chat.messages.transform`, `tool.definition`, compaction), custom tools, agents, MCP local and remote | `opencode run --format json`, `opencode serve` (OpenAPI 3.1), JS SDK, `--attach` to a warm server | Native: `opencode acp` |
| Codex CLI (`openai/codex`) | Apache-2.0 | rust-v0.155.1, 2026-09-18 | `CODEX_HOME/AGENTS.override.md` or `AGENTS.md`, then repo root to cwd, one file per directory, 32 KiB cap (`project_doc_max_bytes`); no switch to disable discovery | `.agents/skills` walking up, `$HOME/.agents/skills`, `/etc/codex/skills`, bundled | Hooks (`SessionStart` can add context), plugins, MCP | `codex exec --json --ephemeral --output-schema --ignore-user-config --ignore-rules`, app-server | Registry entry `codex-acp` |
| Claude Code (`anthropics/claude-code`) | Proprietary ("All rights reserved", Commercial Terms) | not checked | `CLAUDE.md` managed, user, project, walking up; `AGENTS.md` read only when no `CLAUDE.md` (v2.1.277+); `.claude/rules`; `@imports` | `.claude/skills`, plugins | Hooks, plugins, subagents, MCP | `claude -p --bare --output-format json --json-schema --settings --mcp-config --plugin-dir --append-system-prompt`; Agent SDK | Registry entry `claude-acp` |
| Goose (`aaif-goose/goose`, formerly `block/goose`) | Apache-2.0; Linux Foundation AAIF project | v1.51.0, 2026-09-17 | `.goosehints` and `AGENTS.md` at each level, `CONTEXT_FILE_NAMES` | `~/.agents/skills`, `.agents/skills`, plus `.claude/skills` for compatibility | MCP extensions, recipes, subagents, hooks, plugins, custom distributions | `goose run --recipe --no-session --output-format json --with-extension --with-streamable-http-extension` | Native: `goose acp` |
| Crush (`charmbracelet/crush`; successor to archived `opencode-ai/opencode`) | FSL-1.1-MIT (source available; becomes MIT later) | v0.96.1, 2026-09-21 | `CRUSH.md`, `AGENTS.md`, `context_paths` | `$CRUSH_SKILLS_DIR`, `~/.config/agents/skills`, `~/.agents/skills` | MCP (http, stdio, sse), LSP, preliminary hooks | `crush run` single non-interactive prompt | not in registry list |
| Kilo CLI (`Kilo-Org/kilocode`) | MIT | not checked | Inherits OpenCode | Inherits OpenCode | Inherits OpenCode | Inherits OpenCode | Registry entry `kilo` |
| Gemini CLI, Qwen Code, Cline, OpenHands | Apache-2.0, Apache-2.0, Apache-2.0, MIT | not checked | not checked in depth | | | | Gemini and Qwen in the ACP registry |

Sources: Pi docs in `packages/coding-agent/docs/` (configuration, skills, extensions, sdk, rpc, cli, packages); OpenCode docs in `packages/web/src/content/docs/` (rules, config, skills, plugins, server, acp, sdk, cli) and `packages/plugin/src/index.ts`; Codex [AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [skills](https://learn.chatgpt.com/docs/build-skills), [hooks](https://learn.chatgpt.com/docs/hooks) and `codex-rs/exec/src/cli.rs`; Claude Code [headless](https://code.claude.com/docs/en/headless) and [memory](https://code.claude.com/docs/en/memory); Goose `documentation/docs/guides/`; Crush README and `internal/cmd/run.go`; ACP registry repository `agentclientprotocol/registry` folder list.

**Convergence to note.** Pi, OpenCode, Codex, Goose and Crush all read `~/.agents/skills` or `.agents/skills`. OpenCode and Goose also read `.claude/skills`. Pi and Codex both honour `AGENTS.override.md`. A Baltor install that writes skills to `.agents/skills/<name>/SKILL.md` and instructions to `AGENTS.md` reaches every open harness above without a per-harness layout. Claude Code is the exception: it needs `.claude/skills` and a `CLAUDE.md` (or no `CLAUDE.md`, so that `AGENTS.md` loads).

## 4. One fresh instance per step: how each harness does it

The goal: start a new process (or new session) per step that sees only that step's files, with no leakage from the user's home configuration.

| Harness | Fresh isolated instance, verified flags | Leakage to block |
|---|---|---|
| Pi | `pi --print` or `--mode json` with `--no-session`, `--no-context-files`, `--no-skills` plus explicit `--skill <path>`, `--no-extensions` plus explicit `-e <path>`, `--system-prompt` or `--append-system-prompt`, `--tools`, `--offline`; `PI_CODING_AGENT_DIR` to a per-step agent directory. SDK: `SessionManager.inMemory()` and a custom `ResourceLoader` that "owns resource storage and discovery completely". | Project `.pi` loads only after trust; context files do not need trust. Pi has no permission system; sandbox it (its README names Gondolin, Docker, OpenShell). |
| OpenCode | `opencode run --format json --dir <step dir>`; `OPENCODE_CONFIG_CONTENT` inline JSON; `OPENCODE_CONFIG_DIR`; `OPENCODE_DISABLE_CLAUDE_CODE=1`; `OPENCODE_DISABLE_MODELS_FETCH`, `OPENCODE_DISABLE_LSP_DOWNLOAD`, `OPENCODE_DISABLE_AUTOUPDATE`; `--pure` "run without external plugins". Or one warm `opencode serve` and a new session per step via `--attach --dir`. | Global `~/.config/opencode` and remote `.well-known/opencode` configuration merge in; managed settings override everything. No documented switch turns off `AGENTS.md` walk-up; point `HOME` and `XDG_CONFIG_HOME` at the step folder and keep the step folder outside any parent repository. |
| Codex | `codex exec --json --ephemeral --ignore-user-config --ignore-rules --sandbox workspace-write -C <dir> --output-schema`; `CODEX_HOME` per step ("auth still uses `CODEX_HOME`"). | AGENTS.md discovery cannot be disabled; it walks from the git root. Use a step folder that is its own root. |
| Claude Code | `claude -p --bare` skips hooks, skills, plugins, MCP, auto memory and `CLAUDE.md`; add back exactly what the step needs with `--append-system-prompt-file`, `--settings`, `--mcp-config`, `--plugin-dir`, `--add-dir` (skills load from its `.claude/skills`). Bare mode needs `ANTHROPIC_API_KEY`, not a subscription login. | Without `--bare`, `-p` runs project hooks and `.mcp.json` servers with no trust prompt. |
| Goose | `goose run --no-session --recipe <file> --output-format json --with-extension ... --with-streamable-http-extension <url>` | Global `.goosehints` and `~/.agents/skills`; use a per-step `HOME`. |
| Crush | `crush run -q -m <model>` | `CRUSH_GLOBAL_CONFIG` and a per-step `HOME`. |

These flags are documented, not yet exercised by Baltor in this session. The next step (Section 7) is to run each one against a canary file in the parent directory and in `HOME` and record whether the model saw it.

## 5. Notable forks and derivatives

| Project | Base | Licence | What it shows |
|---|---|---|---|
| `can1357/oh-my-pi` (omp), about 32,700 stars | "Fork of Pi" (README) | MIT | Heavy fork: about 80k lines of Rust core, 31 tools, LSP and debugger, subagents in isolated worktrees with schema-checked results, ACP for Zed, and it "reads the eight formats already on disk" (Cursor MDC, Cline rules, Codex AGENTS.md, Copilot). Shows what a fork buys: native tools and speed. It also shows the cost: a separate product that drifts from upstream. |
| `code-yeongyu/senpi`, 443 stars | "opinionated, in-flight fork" of pi-mono | MIT | "Core source modifications are minimised and tracked in `changes.md` files alongside every modified subdirectory so upstream merge commits stay reviewable." Adds a permission system, nested AGENTS.md, dynamic system prompt as built-in extensions. |
| `code-yeongyu/oh-my-openagent` (formerly oh-my-opencode), about 69,300 stars | OpenCode plugin; now also "OmO Native", "pinned senpi engine" | custom licence file | A large OpenCode plugin project moving its native edition onto a Pi fork. |
| Kilo CLI (`Kilo-Org/kilocode`) | "Kilo CLI is a fork of OpenCode" (README) | MIT | The best documented fork-maintenance system (Section 6). Its newest changeset adopts OpenCode v1.18.19 to v1.18.20 while upstream released v1.18.32 on 2026-09-21. Other merges may lack changesets, so treat that lag as inferred. |
| Crush | Continuation of the original Go OpenCode (`opencode-ai/opencode`, archived) | FSL-1.1-MIT | Not the same code as today's TypeScript OpenCode. |
| Other Pi forks | `yc-software/pi`, `lee101/pi-infinity`, `philo-groves/pire` (reverse engineering), `october-dev/october-harness`, ports to Rust and Python | mostly MIT | Many small forks; few stay current. |
| Other OpenCode forks | `shuvcode`, `opencode-vim`, `opencode-sentinel` (private servers only), `mammouth-ai/code` | MIT | Mostly branding or single-feature forks. |

Pi ecosystem items relevant to Baltor: `nicobailon/pi-mcp-adapter` (1,529 stars, "Token-efficient MCP adapter"; Pi has no built-in MCP client in its docs), `svkozak/pi-acp`, several subagent extensions. The Pi README says: "New issues and PRs from new contributors are auto-closed by default. Maintainers review auto-closed issues daily." Upstreaming to Pi therefore needs a maintainer relationship or an RFC ([rfc.earendil.com](https://rfc.earendil.com/keyword/pi/) is linked from the README).

## 6. What a fork would let Baltor do that configuration cannot

**Already possible without a fork.**

- Pi SDK: a custom `ResourceLoader` hands a step exactly the skills, context files, extensions and prompt templates Baltor retrieved, from memory, with no files written and no discovery.
- Pi extension: register a `baltor_search` and `baltor_load` tool; transform context through the `context` event; record run data through `pi.appendEntry()` and session events; add a model provider.
- OpenCode: `OPENCODE_CONFIG_CONTENT` for inline config, `instructions` with remote URLs, a remote MCP server with headers, and plugin hooks that rewrite the system prompt and messages.

**Needs a fork (or an upstream change).**

1. **Verified loading.** A loader that refuses any skill or context file whose digest does not match a signed Baltor manifest, and reports "loaded" as a first-class event. Extensions can observe discovery but do not own the built-in discovery path in the command-line build. The SDK path avoids this for Pi.
2. **Turn-off switches that do not exist.** OpenCode and Codex have no switch to stop `AGENTS.md` walk-up. A fork can add a strict mode that loads only the manifest.
3. **Deep tool and compaction changes.** NVIDIA needed "fork-only post-transform observer methods" before porting to public events. Hashline edits and native LSP in oh-my-pi are core changes.
4. **Startup cost per step.** A fresh process per step pays startup every time. A fork can ship a single prebuilt binary with lazy loading, no model catalogue refresh and no update checks. Pi's `--offline` and OpenCode's disable flags cover part of this. Measure before forking.
5. **Built-in run records.** A stable per-step telemetry schema (steps, tokens, tools, which library items were offered, loaded and used), on by default in the Baltor build and consent-gated. Pi now ships a `pi-telemetry` package, so check it first.
6. **Permissions.** Pi has no permission system. senpi added one in core. Baltor can rely on an operating-system sandbox instead.

## 7. Recommendation

**Fork decision.** Do not hard-fork either harness now. If a fork becomes necessary, fork Pi, not OpenCode. Reasons:

- Pi exposes the host-owned `ResourceLoader`, in-memory sessions, RPC and SDK: the exact surfaces a fresh-harness-per-step engine needs.
- Pi's extension API was enough for NVIDIA's four mechanisms. Baltor already pins the same 0.85.1 release.
- Pi is smaller and SDK-first. OpenCode is a client and server application with a web UI, desktop, LSP and a much larger surface to merge (27,600 GitHub forks, releases several times a week).
- Kilo's tooling shows the true price of an OpenCode fork: a merge agent, a 30-minute release watcher, transform scripts, codemods, and a continuous integration check on every changed upstream line.

**What to build, in order.**

1. **`baltor-pi` Pi package** (extension plus skills, installed with `pi install`): tools `baltor_search` and `baltor_load` that return small typed references first and load bodies after selection; a context hook that records offered, fetched, loaded and used as separate events; SoL-Pi as an optional dependency, off by default.
2. **Per-step launcher on the Pi SDK.** One `createAgentSession()` per step with `SessionManager.inMemory()`, a custom `ResourceLoader` fed from the Baltor manifest, explicit tools, and an operating-system sandbox. This is the default engine for "a unique harness per step".
3. **OpenCode plugin plus inline config.** `OPENCODE_CONFIG_CONTENT` with Baltor's remote MCP server and instruction URLs, `--pure` unless the step needs Baltor's plugin, and `opencode serve` with a new session per step when startup cost matters.
4. **Isolation test matrix** (S-6.42): for Pi, OpenCode, Codex, Claude Code, Goose and Crush, plant a canary line in a parent `AGENTS.md`, in `HOME`, and in a global skill. Launch each with the Section 4 flags and record whether the canary reached the model, cold start time, and tokens in the first request. Write the result to the roadmap evidence, not to prose.
5. **Research fork of Pi, never shipped to customers.** Use it the way NVIDIA did. Every change ends as one of three things: an extension, an upstream RFC, or a discarded record.

**If a shipped fork becomes necessary, keep it maintainable.**

- Fork only `packages/coding-agent`; consume `pi-ai`, `pi-agent-core` and `pi-tui` as upstream npm packages.
- Put Baltor code in its own folder and mark every changed upstream line (Kilo's `kilocode_change` marker and annotation check), with a `changes.md` beside each modified folder (senpi).
- Watch upstream releases on a schedule and open a merge branch automatically (Kilo's `watch-opencode-releases.yml` pattern). Pin the Pi version the fork is tested against, as SoL-Pi does, and keep the previous version for rollback.
- Keep a ratchet in continuous integration on the number of changed upstream lines. It may only fall.
- Run the SoL-Pi style public-API check (`check-pi-compat.mjs`) against each new Pi release, so an extension-only fallback always exists.

## 8. Facts not verified and open questions

- The SoL-Pi blog carries no date. The claim that the research used a Pi fork rests on SoL-Pi's compatibility document, not the paper. The paper HTML does not mention a fork.
- Whether OpenCode's `.well-known/opencode` remote config can be served by a non-model-provider service like Baltor. The docs say it is "fetched automatically when you authenticate with a provider that supports it". Not tested.
- Kilo's real upstream lag. The changeset evidence is inferred.
- Startup time per harness, and whether `--pure` and the disable flags leave OpenCode's project `AGENTS.md` walk-up active. Documented behaviour only; Baltor must measure it (Section 7, item 4).
- Claude Code licence forbids forking. It can only be driven through flags, plugins and the Agent SDK.
