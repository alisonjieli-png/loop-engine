# Independent harness instances for one step

Kind: dated research record, prepared by a Claude Code research agent on September 22, 2026 and reviewed before commit. The roadmap remains the only task authority.

Hands-on test, September 22, 2026. Workstation run by the owner. No model was called.

## 1. Question and answer

The question: can Baltor start a fresh, independent instance of a standard harness for one
step, holding only that step's instruction file, skill and protocol server, without inheriting
the user's global settings?

Short answer, observed on September 22, 2026:

| Harness | Version tested | Classification | Instruction file | Skill | Protocol server |
|---|---|---|---|---|---|
| Codex CLI | 0.155.1 | Supports an isolated per-step instance: **proven** | loaded | loaded | loaded |
| OpenCode | 1.18.32 | Supports an isolated per-step instance: **proven** | loaded | loaded | loaded |
| Claude Code | 2.1.280 | Supports an isolated per-step instance: **proven**, with two required settings | loaded through `CLAUDE.md` with `@AGENTS.md` | loaded | loaded after approval setting |
| Pi | 0.73.1 (`@mariozechner/pi-coding-agent`) | Proven for instruction files and skills. **Does not** support protocol servers without an extension | loaded | loaded | not supported natively |

"Proven" here means proven at the loading level: the harness put the step's material into the
exact request it would send to a model, and put nothing from the decoy global files there. It
does not yet prove that a model uses the material. That is what the one-call test in section 8
proves. Loaded and used are separate facts.

The main finding for Baltor: the documented configuration variable alone is not enough for
three of the four harnesses. Codex, OpenCode and Pi still read skills from `$HOME/.agents/skills`
(OpenCode also reads `~/.claude/CLAUDE.md` and `~/.claude/skills`). Setting `HOME` to an empty
per-step directory closed every leak we measured. Claude Code and Pi also read instruction files
from directories above the step folder; the step folder must sit under a clean root, or the
harness needs an extra flag (section 6).

## 2. Method

### 2.1 Layout per harness

Everything ran under
`a scratch folder of the research session (the logs are kept privately, not in this repository)`:

```text
<harness>/
├── home/        fake HOME filled with DECOY files at every global location
│                (~/.codex/AGENTS.md and config.toml, ~/.agents/skills, ~/.codex/skills,
│                 ~/.claude/CLAUDE.md, ~/.claude/skills, ~/.claude.json,
│                 ~/.config/opencode/AGENTS.md, opencode.json and skills,
│                 ~/.pi/agent/AGENTS.md and skills)
├── emptyhome/   empty HOME, the production recipe
├── iso/         the isolated configuration and data directory for this step
└── work/        the step folder, its own git root
    ├── AGENTS.md                         marker BALTOR-PROBE-AGENTS-7f3a
    ├── <skill dir>/baltor-probe-skill/SKILL.md   marker BALTOR-PROBE-SKILL-7f3a
    └── protocol server configuration     stub tool baltor_probe_echo, marker BALTOR-PROBE-MCP-7f3a
```

Every decoy carries a `DECOY-GLOBAL-...` marker. A decoy appearing in any listing or request is a
leak. The decoys stand in for the user's real global files, so the real ones were never touched.

Shared files in `harness-tests/common/`:

- `setup.sh` builds the layout above.
- `mcp-stub.js` is a 30-line protocol server over standard input and output. It answers
  `initialize`, `tools/list` and `tools/call`, has no network access, and appends each start and
  each request to a log, so a start is observable.
- `capture-stub.py` is a local HTTP endpoint on 127.0.0.1. It is not a model. It writes each
  request body to disk (authorization headers redacted) and answers HTTP 400. Pointing a harness
  at it shows the exact system prompt, tool list and skill list the harness would send, with no
  model behind it and no credential (the key was the literal string `not-a-real-key`).
- `env-base.sh` defines the minimal environment for every run: `env -i` (no inherited API keys),
  `PATH`, `TERM=dumb`, and `HTTP_PROXY`, `HTTPS_PROXY` and `ALL_PROXY` set to the closed port
  `127.0.0.1:9`, so any accidental outside network call fails locally. Claude Code's debug log
  confirms it: `fetchBootstrapData failed: Error: connect ECONNREFUSED 127.0.0.1:9` and
  `1P event logging: 106 events failed to export (code=ECONNREFUSED ...)`.

A network namespace would have been a stronger block, but `unshare -rn` is refused on this
machine (`write failed /proc/self/uid_map: Operation not permitted`).

### 2.2 Variants

- **A**: `HOME` = decoy home, plus the harness's documented isolation variable. This shows what
  leaks if Baltor sets only the documented variable.
- **B**: `HOME` = empty directory, plus the isolation variable. This is the recommended recipe.

### 2.3 Safety record

- No command sent a request to any model provider. Every request went to `capture-stub.py`, and
  every other outside connection was refused by the closed proxy.
- No real credential was read. `env -i` removed every key from the environment, and every `HOME`
  and configuration directory was a fresh temporary one.
- The user's global configuration did not change. Modification times and sizes of
  `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.config/opencode/*`,
  `~/.local/share/opencode/auth.json`, `~/.pi/agent/auth.json`, `~/.pi/agent/models.json`,
  `~/.claude/settings.json` and `~/.agents/skills/humanizer/SKILL.md` were identical before and
  after (`common/global-mtimes-before.txt` and `common/global-mtimes-after.txt`, `diff` empty).
- Every process started was stopped. The final `pgrep` for the stubs, `opencode serve` and
  `pi --mode rpc` returned nothing. One unrelated process, `opencode --auto --model
  ollama/glm-5.2:cloud` (PID 245426), belongs to the user and was not touched.
- **Disclosure.** `harness-tests/` already held files from an earlier attempt, made between
  15:01 and 15:39 (`_evidence/`, `_helphome/`, `_shared/`). They are preserved. But `setup.sh`
  runs `rm -rf harness-tests/<harness>` before building each tree, and it did not check first.
  Any earlier-attempt files inside `codex/`, `opencode/`, `claude/` or `pi/` were removed and
  cannot be recovered. Future runs should write to a new folder name each time.

## 3. Codex CLI 0.155.1

### 3.1 Documented controls (sources in section 9)

- `CODEX_HOME` holds configuration, authentication and state; the default is `~/.codex`.
- AGENTS.md: global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md`, then every directory from
  the project root (normally the git root) down to the working directory. The combined limit is
  `project_doc_max_bytes`, 32 KiB by default.
- Skills: `$CWD/.agents/skills` and its parents up to the repository root, `$HOME/.agents/skills`,
  `/etc/codex/skills`, and skills bundled with Codex.
- Protocol servers go in `[mcp_servers.<name>]` tables in `config.toml`. A project
  `.codex/config.toml` loads only when the project is trusted.
- Headless: `codex exec` (`--ephemeral`, `--json`, `--ignore-user-config`, `--skip-git-repo-check`).
  There is also an experimental `codex app-server`.

### 3.2 Commands and output (no model call)

The step folder `work/` holds `AGENTS.md`, `.agents/skills/baltor-probe-skill/SKILL.md` and
`.codex/config.toml` (server `baltor_probe_project`). The isolated `iso/config.toml` holds server
`baltor_probe` and marks `work/` as trusted.

```text
$ env -i <base> HOME=<decoy home> CODEX_HOME=<iso> codex mcp list
Name                  Command  Args ...                        Status   Auth
baltor_probe          node     .../mcp-stub.js codex-iso       enabled  Unsupported
baltor_probe_project  node     .../mcp-stub.js codex-project   enabled  Unsupported
```

The decoy server in `<decoy home>/.codex/config.toml` is absent. `CODEX_HOME` replaced it.

`codex debug prompt-input "probe"` renders the exact model-visible input as JSON. It also starts
the configured protocol servers and lists their tools; the stub log shows
`start ... argv=codex-project`, `start ... argv=codex-iso`, then `recv initialize` and
`recv tools/list` for each.

Variant A (decoy home), skill roots in the rendered input:

```text
- `r0` = `.../codex/home/.agents/skills`          <- LEAK: decoy-agents-skill listed
- `r1` = `.../codex/iso/skills/.system`           <- bundled skills, installed into CODEX_HOME
- `r2` = `.../codex/work/.agents/skills`          <- the step skill
```

Instruction text: `# AGENTS.md instructions for .../codex/work <INSTRUCTIONS> BALTOR-PROBE-AGENTS-7f3a ...`.
The decoy `DECOY-GLOBAL-CODEX-AGENTS` was not present.

Variant B (empty home): skills `['imagegen', 'openai-docs', 'plugin-creator', 'skill-creator',
'skill-installer', 'baltor-probe-skill']`, the step AGENTS.md present, no decoy.

Variant B with the bundled skills turned off. The key name came from the binary's
`BundledSkillsConfig` structure, then checked by this run:

```text
$ ... codex debug prompt-input -c skills.bundled.enabled=false "probe"
skills: ['baltor-probe-skill']
roots:  ['.../codex/work/.agents/skills']
```

Trust check. With the trust entry removed from `iso/config.toml`, `codex mcp list` showed only
`baltor_probe`, so the project `.codex/config.toml` was ignored, as documented.

Parallel check. Two instances ran at the same time with different `CODEX_HOME` and step folders.
The first listed `['baltor-probe-skill']`, the second `['baltor-second-skill']`.

### 3.3 Classification

**Proven.** Recipe: `HOME=<empty>`, `CODEX_HOME=<per-step dir>` holding `config.toml` with
`[mcp_servers.*]` and `[skills.bundled] enabled = false`, and the step folder as its own git root.
Leak without an empty `HOME`: `$HOME/.agents/skills`.

## 4. OpenCode 1.18.32

### 4.1 Documented controls

- Configuration is merged from remote, global `~/.config/opencode/opencode.json`,
  `OPENCODE_CONFIG`, project `opencode.json`, `.opencode` folders, `OPENCODE_CONFIG_CONTENT` and
  managed files. `OPENCODE_CONFIG_DIR` is searched like a `.opencode` folder.
- Rules: `AGENTS.md` or `CLAUDE.md` found by walking up from the working directory, then
  `~/.config/opencode/AGENTS.md`, then `~/.claude/CLAUDE.md` unless disabled.
  `OPENCODE_DISABLE_CLAUDE_CODE`, `..._PROMPT` and `..._SKILLS` switch off the `.claude` reading.
- Skills: `.opencode/skills`, `.claude/skills` and `.agents/skills` up to the git worktree, plus
  `~/.config/opencode/skills`, `~/.claude/skills` and `~/.agents/skills`.
- Headless: `opencode run`, `opencode serve` (HTTP), `opencode acp`.

### 4.2 Commands and output (no model call)

Isolation variables: `OPENCODE_CONFIG_DIR=<iso>/config`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`,
`XDG_CACHE_HOME` and `XDG_STATE_HOME` under `<iso>/xdg`, plus `OPENCODE_DISABLE_AUTOUPDATE=1` and
`OPENCODE_DISABLE_MODELS_FETCH=1`.

```text
$ opencode debug paths
home    .../opencode/home
data    .../opencode/iso/xdg/data/opencode
config  .../opencode/iso/xdg/config/opencode
state   .../opencode/iso/xdg/state/opencode
cache   .../opencode/iso/xdg/cache/opencode
tmp     /tmp/opencode              <- shared across instances, not isolated
```

`opencode debug skill`:

```text
Variant A (decoy home):
  customize-opencode | <built-in>
  decoy-claude-skill | home/.claude/skills/...      <- LEAK
  decoy-agents-skill | home/.agents/skills/...      <- LEAK
  baltor-probe-skill | work/.opencode/skills/...
Variant A2 (decoy home + OPENCODE_DISABLE_CLAUDE_CODE=1):
  customize-opencode, decoy-agents-skill (LEAK), baltor-probe-skill
Variant B (empty home):
  customize-opencode, baltor-probe-skill
```

`opencode debug config` listed only the step's server under `mcp`. The decoy in
`home/.config/opencode/opencode.json` was absent because the XDG variables moved the global
folder. `opencode mcp list` showed `✓ baltor_probe connected`, and the stub log shows
`initialize` and `tools/list`.

Capture run. A provider pointing at the capture endpoint was supplied through
`OPENCODE_CONFIG_CONTENT`, then:

```text
$ opencode run --pure -m capture/probe "probe"
Error: capture stub: no model behind this endpoint
```

Request 1 is the title generator. Request 2 is the step request:

- Variant A tools: `baltor_probe_baltor_probe_echo, bash, edit, glob, grep, read, skill, task,
  todowrite, webfetch, write`. Markers: the three step markers, plus the leaks
  `DECOY-GLOBAL-CLAUDE-MD`, `DECOY-GLOBAL-CLAUDE-SKILL` and `DECOY-GLOBAL-AGENTS-SKILL`.
- Variant B: the three step markers only. The system prompt contains
  `Instructions from: .../opencode/work/AGENTS.md BALTOR-PROBE-AGENTS-7f3a ...`.

Headless server. `opencode serve --pure --port 18750` with variant B answered:
`GET /mcp` gave `{"baltor_probe":{"status":"connected"}}`; `GET /skill` listed customize-opencode
and baltor-probe-skill; `GET /path` gave the empty home and the isolated state and config folders.

Parallel check. Two servers ran at once, on ports 18791 and 18792, each with its own folders.
Their skills were `['customize-opencode','baltor-probe-skill']` and
`['customize-opencode','baltor-second-skill']`, and their servers were `{"baltor_probe":connected}`
and `{}`.

One anomaly. The first variant B capture run hung and hit the 90 second timeout without sending
a request. The rerun, with `--print-logs`, finished in 2 seconds. The cause is not known. The
log also reports `version=1.17.9` inside a session record, while `opencode --version` prints
1.18.32; this looks like a record schema field, but it is not confirmed.

### 4.3 Classification

**Proven.** Recipe: `HOME=<empty>`, `OPENCODE_CONFIG_DIR` and all four `XDG_*` under the step's
isolated folder, the step's `opencode.json` for protocol servers, and `--pure` to skip external
plugins. Leaks without an empty `HOME`: `~/.agents/skills` always, and `~/.claude/CLAUDE.md` plus
`~/.claude/skills` unless `OPENCODE_DISABLE_CLAUDE_CODE=1`. One built-in skill,
`customize-opencode`, always appears. `/tmp/opencode` is shared between instances.

## 5. Claude Code 2.1.280

### 5.1 Documented controls

- `CLAUDE_CONFIG_DIR`: "Claude Code then stores your settings, session history, and plugins there
  instead" (settings page). The binary also places `.claude.json` inside it; we observed
  `iso/.claude.json` created.
- AGENTS.md is read directly only from v2.1.277 on, and only when the session can fetch feature
  flags from Anthropic. It is not read on a first session after an install, with telemetry
  disabled, or on a third-party provider. The documented workaround is a `CLAUDE.md` containing
  `@AGENTS.md`.
- Skills: `~/.claude/skills`, `.claude/skills` from the start folder up to the repository root,
  `--add-dir` folders, plugins and managed folders.
- Headless: `-p` / `--print`, `--output-format json|stream-json`, `--no-session-persistence`,
  `--mcp-config` with `--strict-mcp-config`, `--settings`, `--setting-sources`, and `--bare`
  (skips `CLAUDE.md` discovery entirely).

### 5.2 Commands and output (no model call)

```text
$ env -i <base> HOME=<decoy home> CLAUDE_CONFIG_DIR=<iso> claude mcp list
baltor_probe: node .../mcp-stub.js claude-project - ⏸ Pending approval (run `claude` to approve)
```

The decoy server in `<decoy home>/.claude.json` was not listed. After writing
`{"enableAllProjectMcpServers": true}` to `<iso>/settings.json`:

```text
baltor_probe: node .../mcp-stub.js claude-project - ✔ Connected
```

The stub log shows `initialize`, `notifications/initialized` and `tools/list`.

Capture runs. The command was `claude -p "probe" --no-session-persistence --debug-file ...`,
with `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>` and `ANTHROPIC_API_KEY=not-a-real-key`. Output:
`API Error: 400 capture stub: no model behind this endpoint`.

| Run | HOME | Step files | Markers in request | Leaks |
|---|---|---|---|---|
| A | decoy | AGENTS.md only | SKILL, MCP (tool `mcp__baltor_probe__baltor_probe_echo`) | none: decoy `~/.claude/CLAUDE.md`, `~/.claude/skills` and `~/.claude.json` all absent |
| B | empty | AGENTS.md only | SKILL, MCP | none. **AGENTS.md not loaded** |
| C | empty | `CLAUDE.md` = `@AGENTS.md` | AGENTS, SKILL, MCP | none |

Run C request text: `Contents of .../claude/work/CLAUDE.md ... @AGENTS.md  Contents of
.../claude/work/AGENTS.md (project instructions ...): BALTOR-PROBE-AGENTS-7f3a ...`.

Debug log for run C:

```text
Loading skills from: managed=/etc/claude-code/.claude/skills, user=<iso>/skills, project=[<work>/.claude/skills]
Loaded 1 unique skills (... managed: 0, user: 0, project: 1 ...)
getSkills returning: 1 skill dir commands, 0 plugin skills, 40 bundled skills, 0 builtin plugin skills
MCP server "baltor_probe": Successfully connected (transport: stdio) in 173ms
Sending 13 skills via attachment (initial)
```

So `CLAUDE_CONFIG_DIR` alone moved the user skill folder, user `CLAUDE.md` and user server list.
No `HOME` leak was observed for Claude Code. The listing still carries bundled skills. We found no
switch that removes the bundled skills while keeping the step's skill; `--disable-slash-commands`
removes every skill.

### 5.3 Classification

**Proven, with two required settings**: a `CLAUDE.md` holding `@AGENTS.md`, and protocol servers
through `--mcp-config <file> --strict-mcp-config`, or `enableAllProjectMcpServers` in the isolated
settings. Recipe: `CLAUDE_CONFIG_DIR=<per-step dir>`, `HOME=<empty>` for safety, and
`DISABLE_TELEMETRY=1` or `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`. The run tried to export
telemetry until the closed proxy refused it.

## 6. Pi 0.73.1

### 6.1 Documented controls

- `PI_CODING_AGENT_DIR` overrides `~/.pi/agent`, which holds settings, `models.json`, `auth.json`,
  `AGENTS.md`, skills and extensions. `PI_OFFLINE=1` or `--offline` stops startup network work.
- Context files: `AGENTS.md` or `CLAUDE.md` from the agent folder, the working folder and every
  parent folder. `--no-context-files` turns this off, and `--append-system-prompt <file>` adds a
  file's text.
- Skills: `~/.pi/agent/skills`, `~/.agents/skills`, `.pi/skills` and `.agents/skills` from the
  working folder up. `--no-skills` and `--skill <path>` control them.
- "**No MCP.**" (installed README). Protocol servers need an extension.
- Headless: `-p`, `--mode json`, `--mode rpc` (commands `get_commands`, `get_state` and others),
  and a TypeScript SDK.
- Upstream moved: the project is now `github.com/earendil-works/pi`, package
  `@earendil-works/pi-coding-agent`. Its current configuration page names `<agent-dir>/skills` and
  `.pi/skills`. The installed package is still `@mariozechner/pi-coding-agent` 0.73.1.

### 6.2 Commands and output (no model call)

RPC listing, with no prompt sent:

```text
$ (printf '{"id":"1","type":"get_commands"}\n{"id":"2","type":"get_state"}\n'; sleep 4) | \
  env -i <base> HOME=<decoy home> PI_CODING_AGENT_DIR=<iso> PI_OFFLINE=1 PI_TELEMETRY=0 \
  pi --mode rpc --no-session --offline
skill:baltor-probe-skill  scope=project  path=.../pi/work/.pi/skills/baltor-probe-skill/SKILL.md
skill:decoy-agents-skill  scope=user     path=.../pi/home/.agents/skills/decoy-agents-skill/SKILL.md   <- LEAK
state: model=unknown (no provider configured, so nothing could be called)
```

Variant B (empty home) listed only `skill:baltor-probe-skill`. With the decoy home and
`--no-skills --skill <work>/.pi/skills/baltor-probe-skill`, the listing was only
`('skill:baltor-probe-skill','project')`.

Capture run. `<iso>/models.json` defined a provider `capture` at the capture endpoint, then:
`pi --offline --no-session --model capture/probe -p "probe"` gave
`400 capture stub: no model behind this endpoint`.

- Variant A request markers: AGENTS, SKILL, and the leak `DECOY-GLOBAL-AGENTS-SKILL`. The decoy
  `~/.pi/agent/AGENTS.md` was absent.
- Variant B: AGENTS and SKILL only. Context text: `## .../pi/work/AGENTS.md BALTOR-PROBE-AGENTS-7f3a`.
- Tools: `read, bash, edit, write`. No protocol tool, as documented.

### 6.3 Classification

**Proven for instruction files and skills. Does not support protocol servers natively.** Recipe:
`HOME=<empty>`, `PI_CODING_AGENT_DIR=<per-step dir>` with its own `models.json`, `--offline`,
`--no-session`, and preferably `--no-skills --skill <path>` and
`--no-context-files --append-system-prompt <file>` for explicit delivery. For protocol servers a
Pi extension would be required; none was installed or tested.

## 7. Cross-harness finding: instruction files above the step folder

A decoy `AGENTS.md` and `CLAUDE.md` were placed in the parent of each step's git root:

```text
codex     BALTOR-PROBE-AGENTS-7f3a                         (stops at the git root)
opencode  BALTOR-PROBE-AGENTS-7f3a                         (stops at the worktree root)
pi        BALTOR-PROBE-AGENTS-7f3a DECOY-PARENT-AGENTS     <- LEAK
claude    BALTOR-PROBE-AGENTS-7f3a DECOY-PARENT-CLAUDE     <- LEAK
```

Both leaks have a fix, and both fixes were tested:

- Pi: `--no-context-files --append-system-prompt <work>/AGENTS.md` gave AGENTS and SKILL, no decoy.
- Claude Code: `--settings '{"claudeMdExcludes":["<parent>/CLAUDE.md"]}'` gave AGENTS, MCP and
  SKILL, no decoy.

The simplest rule is to create step folders under a root with no instruction file above it, and
to make each step folder its own git root.

## 8. Test that would prove use with one model call (not run)

The script is `harness-tests/common/prove-loading-one-call.sh`. It passed `bash -n` and has not
been run. It refuses to start unless `OWNER_BUDGET_APPROVED=yes` is set. For each harness it:

1. builds a fresh step under a clean root with three random codes, each in one place only: code A
   in the `AGENTS.md` body, code S in the skill description, and code M in the protocol tool
   description. It plants a decoy code D at every global location in a fake home;
2. starts the harness once, headless, with the section 3 to 6 recipe, and asks: "Do not call any
   tool. Reply on one line with every code you can see ... Write NONE for a code you cannot see.";
3. passes only if A, S and M appear (M is not required for Pi), D does not appear, and the
   protocol stub log shows `tools/list` from this instance;
4. runs a known-wrong control first with `CONTROL=1`, which deletes `AGENTS.md`. Code A must then
   be absent, which shows the check can fail.

Commands per harness:

- Claude Code:
  `claude -p "$Q" --no-session-persistence --mcp-config mcp.json --strict-mcp-config --model haiku --max-turns 1 --max-budget-usd 0.05 --output-format json`
  with `CLAUDE_CONFIG_DIR`, `DISABLE_TELEMETRY=1` and `ANTHROPIC_API_KEY` for this run only.
- Codex:
  `codex exec --ephemeral --json -s read-only -m $CODEX_MODEL "$Q"`, after
  `printenv OPENAI_API_KEY | codex login --with-api-key` into the throwaway `CODEX_HOME`.
  There is a no-spend variant with `--oss --local-provider ollama`.
- OpenCode: `opencode run --pure --format json -m <model> "$Q"`, with the provider supplied
  through `OPENCODE_CONFIG_CONTENT`.
- Pi: `pi --no-session --mode json --tools read -p --model <model> "$Q"`, with a per-step
  `models.json`.

A local Ollama server is running on this workstation with `qwen2.5-coder:7b`. This was observed
through `/api/tags`, a listing that calls no model. It would make the OpenCode, Pi and Codex
`--oss` runs free of charge. It is still a model call, so it waits for the owner's approval like
the paid runs. Expected requests: one per harness, two for OpenCode, which also asks for a title.
A model that ignores "do not call any tool" could add one more; `--max-turns 1` prevents this for
Claude Code only.

## 9. Sources (each fetched September 22, 2026)

- Codex advanced configuration (CODEX_HOME, project config and trust): <https://learn.chatgpt.com/docs/config-file/config-advanced> (redirected from developers.openai.com/codex/config-advanced)
- Codex skills locations: <https://learn.chatgpt.com/docs/build-skills>
- Codex AGENTS.md discovery: <https://learn.chatgpt.com/docs/agent-configuration/agents-md>
- Codex protocol servers: <https://learn.chatgpt.com/docs/extend/mcp?surface=cli>
- OpenCode configuration: <https://opencode.ai/docs/config/>
- OpenCode skills: <https://opencode.ai/docs/skills/>
- OpenCode rules: <https://opencode.ai/docs/rules/>
- OpenCode command line and environment variables: <https://opencode.ai/docs/cli/>
- OpenCode protocol servers: <https://opencode.ai/docs/mcp-servers/>
- Claude Code memory and AGENTS.md: <https://code.claude.com/docs/en/memory>
- Claude Code settings (CLAUDE_CONFIG_DIR sentence): <https://code.claude.com/docs/en/settings>
- Claude Code skills: <https://code.claude.com/docs/en/skills>
- Claude Code environment variables (ANTHROPIC_BASE_URL): <https://code.claude.com/docs/en/env-vars>
- Pi configuration, current upstream: <https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/configuration.md>
- Pi skills, current upstream: <https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/skills.md>
- Pi installed documentation: `the installed Pi package's README.md`, `docs/rpc.md`, `docs/models.md`, `docs/sdk.md`
- Each tool's own `--help` output, captured on September 22, 2026.

Evidence files: everything under `harness-tests/<harness>/`: `A-*`, `B-*` and `C-*` outputs, the
`capture-*/req-*.json` request bodies (keys redacted, and fake anyway), `mcp-starts.log`, and the
debug logs.
