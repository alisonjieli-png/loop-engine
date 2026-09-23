# Harness model use with one call per instance

Kind: dated verification record, prepared by a Claude Code verification agent on September 22, 2026 for roadmap step S-6.42. The roadmap remains the only task authority.

Real model calls, run between 23:14 and 23:22 Eastern time on September 22, 2026, on the owner's workstation. 30 model requests were used against a ceiling of 60.

## 1. Question and short answer

The [independent instances record](../research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md) proved, with no model call, that a fresh instance of four standard harnesses loads one step's `AGENTS.md`, skill and protocol server and nothing from decoy global files. It left one question open, and this record answers it: does a real model actually use that loaded material?

The test gives each fresh instance three random codes, each in exactly one place, and asks the model to repeat them. A code in the answer can only have come from the step's material.

| Harness and version | Cloud model `glm-5.3-flash:cloud` | Local model `qwen2.5-coder:7b` |
|---|---|---|
| OpenCode 1.18.32 | **Pass**. Also passed as two instances at the same time. | **Fail**. The local server cut the 7,116-token prompt to 2,050 tokens. |
| Claude Code 2.1.280 | **Pass** | **Fail**. The local server cut the 13,513-token prompt to 2,050 tokens. |
| Pi 0.73.1 | **Pass** for the instruction file and the skill. Pi has no protocol client, so the tool code does not apply. | **Pass** for the instruction file and the skill. The 1,146-token prompt fits. |
| Codex 0.155.1 | **Fail** with its own settings: the skill code never reached the model. **Pass** only with a diagnostic change to the route (section 8.1). | **Fail**. The local server cut the 4,991-token prompt to 2,050 tokens. |

Every failure happened between the harness and the model, not in harness isolation. In every failed run the harness had placed the codes in its request. The local Ollama server then refused the request, dropped part of it or cut it before the model saw it (section 8).

## 2. Offered, loaded, used and accepted are separate facts

```text
One step's material
├── Loaded:   the harness read the file (the loading test, no model)
├── Offered:  the code is in the request body the harness sent (captured by the counting proxy here)
├── Used:     the code is in the model's answer (this record)
└── Accepted: an independent check accepts task work built on the material (not tested here)
```

This record proves "used" at the level of one answer to one question. The model read the material and repeated it. That is not accepted task work, and it does not show that the model follows the material's instructions or that the material improves results.

## 3. Method

### 3.1 One fresh step per run

Each run built a new step under a clean root, a scratch folder under `/tmp` whose parent folders were checked to hold no `AGENTS.md`, `CLAUDE.md`, `.claude`, `.agents`, `.pi`, `.opencode`, `.codex` or `.git`. The owner's home folder was not used as the root, because it holds the real `.claude`, `.agents` and `.pi` folders. Claude Code and Pi read instruction files from parent folders ([loading record, section 7](../research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md#7-cross-harness-finding-instruction-files-above-the-step-folder)).

```text
<run>/
├── emptyhome/   HOME for the production recipe: empty
├── home/        fake home: decoy code D at every global location
│                (.codex/AGENTS.md and AGENTS.override.md, .codex/config.toml with a decoy
│                 protocol server and decoy developer instructions, .claude/CLAUDE.md,
│                 .claude.json with a decoy protocol server, .config/opencode/AGENTS.md and
│                 opencode.json, .pi/agent/AGENTS.md and CLAUDE.md, and a decoy skill in
│                 .agents/skills, .claude/skills, .codex/skills, .config/opencode/skills
│                 and .pi/agent/skills)
├── iso/         the harness's own configuration folder for this step
├── tmp/         TMPDIR for this step
├── mcp-stub.js  the protocol server stub of the loading test, tool description "Tool code M"
└── work/        the step folder, its own git root
    ├── AGENTS.md                                  "Project code: A"
    ├── <skill folder>/baltor-probe-skill/SKILL.md description "Skill code S."
    └── the harness's protocol server setting (Codex and Claude Code keep it outside work/)
```

Each code is a capital letter and eight random hexadecimal characters, new for every run. The protocol server stub (`common/mcp-stub.js` from the loading test) has no network access and logs each start and each request, so a `tools/list` from this instance is observable.

### 3.2 The question

Every harness received the question from section 8 of the loading record, unchanged:

> Do not call any tool. Reply on one line with every code you can see: the project code in your instructions, the code in the description of skill baltor-probe-skill, and the code in the description of tool baltor_probe_echo. Write NONE for a code you cannot see.

### 3.3 Pass rule

A production-recipe run passes when all of these hold:

1. codes A and S are in the model's answer, and code M too, except for Pi;
2. decoy code D is not in the answer;
3. the stub log shows `recv tools/list` from this instance (not for Pi);
4. the harness made no tool call.

The judge reads only the model's answer text, parsed from the harness's own event stream. It does not search the whole output. In the dry runs no harness printed any code by itself, so a whole-output search would not have given a false pass with these versions and settings. Codes are matched without regard to letter case.

Every run also records which codes were in the request body (offered), from the counting proxy's capture. That keeps offered and used apart.

### 3.4 Recipes

Every run used a clean environment holding only `PATH=/usr/bin:/bin`, `TERM`, `LANG`, `HOME`, `TMPDIR` and the proxy variables. `HTTP_PROXY`, `HTTPS_PROXY` and `ALL_PROXY` pointed at the closed local port 9, and `NO_PROXY` allowed only `127.0.0.1` and `localhost`. So a harness could reach the counting proxy and nothing else. Each binary was started by absolute path.

| Harness | Binary | Isolation settings | Model route | Command |
|---|---|---|---|---|
| Codex 0.155.1 | `~/.local/bin/codex` | `HOME` empty; `CODEX_HOME=<run>/iso` holding `config.toml` with the provider, `[mcp_servers.baltor_probe]`, `[skills.bundled] enabled = false`, a trust entry for `work/`, and `web_search = "disabled"` (section 8.1) | custom provider, `wire_api = "responses"`, `base_url` the counting proxy, `request_max_retries = 0`, `stream_max_retries = 0` | `codex exec --ephemeral --json --color never -s read-only -m <model> "<question>"` |
| OpenCode 1.18.32 | `~/.opencode/bin/opencode` | `HOME` empty; `OPENCODE_CONFIG_DIR` and all four `XDG_*` folders under `<run>/iso`; `OPENCODE_DISABLE_AUTOUPDATE=1`; `OPENCODE_DISABLE_MODELS_FETCH=1`; protocol server in `work/opencode.json`; skill in `work/.opencode/skills` | provider `@ai-sdk/openai-compatible` through `OPENCODE_CONFIG_CONTENT`, `baseURL` the counting proxy, a placeholder key | `opencode run --pure --format json --print-logs --log-level INFO --title "baltor model-use proof" -m baltorollama/<model> "<question>"` |
| Claude Code 2.1.280 | `~/.local/bin/claude` | `HOME` empty; `CLAUDE_CONFIG_DIR=<run>/iso`; `work/CLAUDE.md` holding `@AGENTS.md`; skill in `work/.claude/skills`; `DISABLE_TELEMETRY=1`; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`; `DISABLE_AUTOUPDATER=1`; `DISABLE_ERROR_REPORTING=1` | `ANTHROPIC_BASE_URL` the counting proxy, which forwards to the local server's Messages endpoint (`/v1/messages`); `ANTHROPIC_API_KEY` a placeholder string, not a credential | `claude -p "<question>" --no-session-persistence --mcp-config <run>/mcp.json --strict-mcp-config --model <model> --max-turns 1 --output-format stream-json --verbose --debug-file <run>/claude-debug.log` |
| Pi 0.73.1 | `~/.local/bin/pi` | `HOME` empty; `PI_CODING_AGENT_DIR=<run>/iso` holding `models.json`; `PI_OFFLINE=1`; `PI_TELEMETRY=0`; skill in `work/.pi/skills` | `models.json` provider with `api: "openai-completions"`, `baseUrl` the counting proxy, `compat` with the developer role and reasoning effort off | `pi --offline --no-session --mode json --tools read -p --model baltorollama/<model> "<question>"` |

Claude Code ran against the local server's Messages endpoint. The subscription login was not used, and no credential file was read, copied or printed. `--max-budget-usd` was not set, because no paid key was involved. The hidden `--max-turns 1` flag was accepted.

### 3.5 Counting proxy and ceiling

Every model request went through a counting proxy in front of the local Ollama server at `127.0.0.1:11434`. The proxy holds no credential, because the local server reaches the cloud models through the owner's own signed-in server. It:

- counted every request to a path that can run a model, in one ledger for all runs, protected by a file lock;
- refused requests without forwarding them past a hard stop of 56 (below the ceiling of 60), or past a cap per run (2 for Codex, Claude Code and Pi, 3 for OpenCode);
- refused any model outside the approved list, and every endpoint that changes the model store (pull, push, create, delete, copy, blobs);
- saved each request body and response body, with authorization headers redacted, and extracted the usage the provider reported.

A self-test against a fake local server checked streaming, usage extraction, the refusals, the per-run cap, the shared ceiling and dry-run mode: 15 of 15 checks passed. Three mutants, with the ceiling, model-list and per-run-cap guards removed, each failed named checks. The proxy refused no request during the test.

A dry run for each harness came first. The proxy recorded the request and answered status 400, so no model was called. Each dry run sent one request. The Codex, OpenCode and Claude Code requests offered codes A, S and M, and the Pi request offered A and S. None offered D, and none held a real-home marker.

## 4. Versions, models and route

| Item | Value |
|---|---|
| Codex | `codex-cli 0.155.1` |
| OpenCode | `1.18.32` (`~/.opencode/bin/opencode`). `~/.local/bin/opencode` is a second install, version 1.17.9 |
| Claude Code | `2.1.280 (Claude Code)` |
| Pi | `0.73.1` (`@mariozechner/pi-coding-agent`) |
| Node.js | `v22.22.1` |
| Local model server | Ollama `0.32.6`, one service for the whole workstation. It serves the cloud models through the owner's subscription |
| Cloud model | `glm-5.3-flash:cloud`, the same model for all four harnesses, so that harness differences are not model differences |
| Local model | `qwen2.5-coder:7b` on an NVIDIA GeForce RTX 3060 graphics card with 12 gigabytes of memory. The server ran it with a 4,096-token context slot and cut longer prompts to 2,050 tokens (section 8.2) |
| Endpoints used | Responses (`/v1/responses`) for Codex, Chat Completions (`/v1/chat/completions`) for OpenCode and Pi, Messages (`/v1/messages`) for Claude Code |

## 5. Requests used against the ceiling

| Phase | Runs | Model requests |
|---|---|---|
| Cloud model, control and production recipe, four harnesses | 8 | 8, of which the local server refused 2 Codex requests with status 400 |
| Codex again, with the web search tool turned off | 2 | 2 |
| Direct diagnostic: developer-role message on the Responses endpoint | 2 requests | 2 |
| Codex with the diagnostic route change | 1 | 1 |
| Local model, control and production recipe, four harnesses | 8 | 8 |
| Direct diagnostic: context size option on the Chat Completions endpoint | 1 request | 1 |
| Two OpenCode instances at the same time | 2 | 2 |
| Decoy home control, four harnesses | 4 | 4 |
| Broad question pair, OpenCode | 2 | 2 |
| Dry runs: four before the first model request, one after the Codex change | 5 | 0 |
| **Total** | | **30 of 60** |

Three independent counts agree:

- the proxy ledger holds 30 entries;
- the Ollama server log shows 30 model requests in the test window, 28 with status 200 and 2 with status 400;
- the harness's own output shows one model turn for each completed run. The two refused Codex runs show a failed turn.

The owner's other harness session on the same server made no request in the window. Each run's own log window matched its proxy count of 1, except the parallel pair, whose windows overlapped and so each held both requests.

## 6. Results for every run

Times are Eastern time on September 22, 2026. The answer column shows the first line of the model's answer. Token counts are what the provider reported for the request.

| Number | Start | Harness | Model | Variant | Requests (status) | Tokens | Answer | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | 23:14:31 | Codex | `glm-5.3-flash:cloud` | control: `AGENTS.md` deleted | 1 (400) | none reported | no answer: "the web_search tool is not supported" | fail (route) |
| 2 | 23:14:34 | Codex | `glm-5.3-flash:cloud` | production recipe | 1 (400) | none reported | no answer: "the web_search tool is not supported" | fail (route) |
| 3 | 23:14:38 | OpenCode | `glm-5.3-flash:cloud` | control: `AGENTS.md` deleted | 1 (200) | 7,265 in, 123 out | `NONE, Scffc347e, M29ecacec` | control holds |
| 4 | 23:14:46 | OpenCode | `glm-5.3-flash:cloud` | production recipe | 1 (200) | 7,371 in, 130 out | `A649d2b24 S1f4c1550 Mcebe07da` | **pass** |
| 5 | 23:14:55 | Claude Code | `glm-5.3-flash:cloud` | control: `AGENTS.md` deleted | 1 (200) | 14,571 in, 139 out | `NONE, S64cc4e1b, M5b01eda0` | control holds |
| 6 | 23:14:59 | Claude Code | `glm-5.3-flash:cloud` | production recipe | 1 (200) | 14,687 in, 87 out | `Ae7157bd3, S42199810, Me49424a0` | **pass** |
| 7 | 23:15:06 | Pi | `glm-5.3-flash:cloud` | control: `AGENTS.md` deleted | 1 (200) | 994 in, 187 out | `NONE S1e4c6f3b NONE` | control holds |
| 8 | 23:15:14 | Pi | `glm-5.3-flash:cloud` | production recipe | 1 (200) | 1,101 in, 162 out | `Adf7c4769 S0e79220b NONE` | **pass** (tool code not applicable) |
| 9 | 23:15:48 | Codex | `glm-5.3-flash:cloud` | control: `AGENTS.md` deleted, web search off | 1 (200) | 7,634 in, 478 out | `project code: NONE; skill baltor-probe-skill: NONE; tool baltor_probe_echo: M33412c2a` | control holds |
| 10 | 23:15:53 | Codex | `glm-5.3-flash:cloud` | production recipe, web search off | 1 (200) | 7,744 in, 102 out | `Ac419411c NONE M57c6eefd` | **fail**: skill code offered, not used |
| 11 | 23:17:28 | Codex | `glm-5.3-flash:cloud` | production recipe, diagnostic route change | 1 (200) | 8,029 in, 133 out | `Aa3062c1f Sfac50ff8 M4a37d688` | pass, diagnostic only |
| 12 | 23:17:50 | Pi | `qwen2.5-coder:7b` | control: `AGENTS.md` deleted | 1 (200) | 1,013 in, 28 out | `- Project code: NONE` | control holds |
| 13 | 23:18:14 | Pi | `qwen2.5-coder:7b` | production recipe | 1 (200) | 1,146 in, 44 out | `Project code: A0c2e22f6`, then the skill code and NONE for the tool on the next lines | **pass** |
| 14 | 23:18:22 | OpenCode | `qwen2.5-coder:7b` | control: `AGENTS.md` deleted | 1 (200) | 2,050 in, 19 out | a fenced block naming a tool called NONE | holds only trivially |
| 15 | 23:18:35 | OpenCode | `qwen2.5-coder:7b` | production recipe | 1 (200) | 2,050 in, 38 out | a fenced block with NONE for all three codes | **fail**: prompt cut |
| 16 | 23:18:46 | Codex | `qwen2.5-coder:7b` | control: `AGENTS.md` deleted | 1 (200) | 2,050 in, 6 out | a fenced block holding NONE | holds only trivially |
| 17 | 23:18:51 | Codex | `qwen2.5-coder:7b` | production recipe | 1 (200) | 2,050 in, 2 out | `NONE` | **fail**: prompt cut |
| 18 | 23:18:56 | Claude Code | `qwen2.5-coder:7b` | control: `AGENTS.md` deleted | 1 (200) | 2,050 in, 25 out | an invented `TaskStop` tool call written as text | holds only trivially |
| 19 | 23:19:02 | Claude Code | `qwen2.5-coder:7b` | production recipe | 1 (200) | 2,050 in, 27 out | an invented tool call written as text | **fail**: prompt cut |
| 20 | 23:20:04 | OpenCode | `glm-5.3-flash:cloud` | production recipe, parallel instance 1 | 1 (200) | 7,377 in, 119 out | `Ab9149b69 S798cf9e0 M51e0b649` | **pass** |
| 21 | 23:20:04 | OpenCode | `glm-5.3-flash:cloud` | production recipe, parallel instance 2 | 1 (200) | 7,380 in, 100 out | `A49a89576, S6899fa2c, M05db43cc` | **pass** |
| 22 | 23:20:32 | Codex | `glm-5.3-flash:cloud` | decoy home, diagnostic route change | 1 (200) | 8,161 in, 222 out | `Add785979 Sb47b9367 Ma79221be` | decoy offered, not in the answer |
| 23 | 23:20:41 | OpenCode | `glm-5.3-flash:cloud` | decoy home | 1 (200) | 7,648 in, 191 out | `A78effe3d S2cc888ba Md52c38c8` | decoy offered, not in the answer |
| 24 | 23:20:54 | Claude Code | `glm-5.3-flash:cloud` | decoy home | 1 (200) | 10,224 in, 104 out, 4,480 more read from the provider's prompt cache | `Ac7806c6d S02c40925 M5f73dfb0` | decoy not offered: no leak |
| 25 | 23:21:02 | Pi | `glm-5.3-flash:cloud` | decoy home | 1 (200) | 1,253 in, 188 out | `A60c21244 Sd03d0c66 NONE` | decoy offered, not in the answer |
| 26 | 23:21:57 | OpenCode | `glm-5.3-flash:cloud` | decoy home, broad question | 1 (200) | 7,659 in, 202 out | `D81690466 A019bc8ef Sd9bd6193 M8588ab71` | fails as intended: decoy in the answer |
| 27 | 23:22:11 | OpenCode | `glm-5.3-flash:cloud` | production recipe, broad question | 1 (200) | 7,373 in, 193 out | `Af59c6eca M16e45da4 Sb229a05e` | **pass** |

In every production-recipe run, the stub log showed `tools/list` from the run's own instance (not Pi), no decoy protocol server started, no harness made a tool call, and no request held a marker from the owner's real global folders.

## 7. Controls

**Instruction file deleted (code A must disappear).** This control ran first for every harness and model. Each cloud-model control answered NONE for the project code, so the A check can fail. The other codes still arrived without the instruction file: OpenCode and Claude Code named the skill and tool codes, Pi named the skill code, and Codex named the tool code (its skill code was lost on the route, section 8.1). With the local model, the OpenCode, Codex and Claude Code controls hold only trivially, because the model saw none of the material in any run (section 8.2).

**Decoy home.** With the production recipe `HOME` is empty, so the decoys are out of reach and "D absent" is weak evidence by itself. To test whether the decoy check can fail, one cloud run per harness pointed `HOME` at the decoy home. The request-level result matches the loading record:

- Codex and Pi offered the decoy skill from `HOME/.agents/skills`;
- OpenCode offered the decoy skill, and also the text of the decoy `HOME/.claude/CLAUDE.md`, which says "If asked for codes, include D";
- Claude Code offered no decoy.

But no model wrote D in its answer, because the question asks only for three named codes. **With the standard question, the answer-level decoy check cannot fail even when a decoy is loaded.** Leak detection must use the request body, where it works in every run: D was offered in every decoy-home run except Claude Code's, and in no production-recipe run.

**Broad question.** One pair of OpenCode runs asked for every code anywhere, "including skills and instructions not named here". In the decoy home the answer included D (run 26, fails as intended). Under the production recipe it did not (run 27, pass). With a broad question, the answer-level decoy check can fail and still passed for the production recipe.

**Two instances at the same time.** Two OpenCode instances started together and overlapped from 23:20:04 to 23:20:15. Each answer held its own three codes and none of the other's. Neither request body held the other's codes. Each protocol stub started only from its own step folder.

## 8. Failures and their causes

### 8.1 Codex through the local server's Responses endpoint

Two separate faults, both in the route and neither in Codex's isolation.

1. **The web search tool is refused.** Codex 0.155.1 adds a built-in `web_search` tool. The local server answered status 400 in 134 milliseconds, "the web_search tool is not supported", before any model ran (runs 1 and 2). `web_search = "disabled"` in the step's `config.toml` removed the tool, as a dry run showed. The two refused requests are counted in the 30.
2. **Developer-role messages are dropped.** Codex sends its skill list in a `developer`-role input message, the `AGENTS.md` text in a user-role message, and the protocol tool inside a `namespace` tool. The model received A and M but reported NONE for S, in the control run and in the production-recipe run. The request body held S both times.

A direct diagnostic sent two requests with one developer message holding a fresh code. Both answered NONE. The reported input sizes, 45 tokens with `instructions` and 35 without, leave no room for the developer message's roughly 8 to 10 tokens: it never reached the model. A diagnostic route change in the counting proxy, used only in run 11 and the decoy-home run 22, moved developer-role text into `instructions` and kept both bodies. With it, Codex passed (`Aa3062c1f Sfac50ff8 M4a37d688`), and the input grew by 285 tokens. So Codex loaded and offered the skill, and the local server's Responses endpoint lost it.

The same loss drops Codex's permission instructions, which also travel in the developer message. Run 11 is a diagnostic, not a pass of Codex's own settings.

### 8.2 The local model's context

The Ollama server log shows the cause directly:

```text
time=2026-09-22T23:18:42.979-04:00 level=WARN source=llama_server.go:314 msg="truncating input prompt" limit=2050 prompt=7116 keep=4 new=2050
slot operator(): id 0 | task 99 | new prompt, n_ctx_slot = 4096, n_keep = 4, task.n_tokens = 2050
```

For `qwen2.5-coder:7b`, the server used a 4,096-token context slot and cut each longer prompt to 2,050 tokens. It kept the first 4 tokens and the end, with no error to the harness. The prompts, counted by the local model's tokenizer, were 4,991 tokens for Codex, 7,116 for OpenCode and 13,513 for Claude Code, so the step's material was cut out before the model saw it. Pi's prompt of about 1,100 tokens fit, and Pi passed.

A direct diagnostic sent a 4,334-token prompt to the Chat Completions endpoint with `options.num_ctx = 8192` and `num_ctx = 8192` in the body. It was still cut to 2,050 tokens, so this endpoint ignores a context size in the request. Raising the context would need a server setting (`OLLAMA_CONTEXT_LENGTH`) or a model variant with a larger `num_ctx`. Both change the owner's shared Ollama service, one needs a restart, and this test did neither.

## 9. Other findings

- **The loading test ran OpenCode 1.17.9, not 1.18.32.** Its session records say `version=1.17.9`. Its `env-base.sh` puts `~/.local/bin`, which holds 1.17.9, ahead of `~/.opencode/bin`, which holds 1.18.32. This test started 1.18.32 by absolute path, and the loading results held for it.
- **One request per OpenCode run.** The loading record expected two, one of them for a session title. `--title` removed the title request in every OpenCode run.
- **Request sizes differ widely.** In the dry runs the requests were about 16,100 tokens for Claude Code (21 tools), about 9,700 for Codex (10 tools, 9 after web search was turned off), about 8,200 for OpenCode (11 tools) and about 1,000 for Pi (1 tool), estimated as characters divided by four. For a small local model this decides whether the step's material arrives at all.
- **Provider prompt cache.** Claude Code's decoy-home run reported 10,224 input tokens plus 4,480 read from the provider's prompt cache. The total matches the other Claude Code runs, so this was the cache, not a difference caused by `HOME`. A repeatable check should record cache reads beside input tokens.
- **The prepared script needs changes before reuse.** `common/prove-loading-one-call.sh` defaults its root to a folder under the owner's home, whose parent holds the real `.claude`, `.agents` and `.pi` folders. It asks for paid keys and a spending option. It searches the whole output instead of the answer. And its decoy condition cannot fail with its question. This test used a new runner instead (section 12).

## 10. What this proves and what it does not

Observed:

- Under the production recipe, with the cloud model, a real model repeated random codes that existed only in the step's `AGENTS.md`, skill description and protocol tool description, for OpenCode 1.18.32 and Claude Code 2.1.280. For Pi 0.73.1 the same holds for the instruction file and the skill. Two OpenCode instances at the same time each used only their own material.
- Deleting `AGENTS.md` removed the project code from every answer, so the check can fail.
- No production-recipe request held a decoy code or a marker from the owner's real global folders.
- With the local model `qwen2.5-coder:7b`, only Pi's material reached the model and was used.

Inferred, with the evidence in section 8.1: Codex's material would be used on this route if developer-role messages reached the model. Run 11 supports this, but only with a diagnostic route change.

Not shown:

- accepted task work;
- that a model follows the material's instructions, rather than only repeating a code from it;
- other models, other harness versions, long tasks or many turns;
- a repeatable repository check. That is separate work in progress.

## 11. Next step for the repeatable check

1. **Judge the decoy in the request body as well as the answer**, or use the broad question. The standard question's answer check cannot fail on a leak.
2. **Record offered and used separately for every code**, from a captured request body. A "fail" then says whether the harness, the route or the model lost the material.
3. **Check for truncation.** Compare reported input tokens with the request size, or read the server's truncation warning. Mark a cut run "material not delivered" instead of a model failure.
4. **For Codex on a local Ollama server**, set `web_search = "disabled"`. Treat skills and permission instructions as not delivered on the Responses endpoint of Ollama 0.32.6 until a route keeps developer-role messages. Such a route could be a hosted Responses service, or an adapter owned by an engine behind the harness executor edge, doing what the diagnostic change did. Both need their own review.
5. **For small local models**, decide the context size together with the harness. Either raise the context on a dedicated model server, which the owner's shared service is not, or prefer harnesses with compact prompts, such as Pi at about 1,100 tokens. The Chat Completions endpoint ignores a context size in the request.
6. **Start each harness by absolute path** and record its version from the same binary.
7. **Count every request through a proxy with a hard stop below the allowance**, and cross-check with the server log, as here.

## 12. Safety record

- Model authority: the owner's September 22, 2026 authorization for Ollama Cloud within the existing subscription. Every request went through the local Ollama server, and no paid key was used. Claude Code used a placeholder key against the local server, with no subscription login.
- Requests: 30 of the ceiling of 60, with the proxy's hard stop at 56. The per-run cap and the ceiling were never reached, and no request was refused by the proxy.
- The Ollama model store did not change. The proxy refuses every store change, and none was attempted.
- The owner's real global files were not changed. The modification times and sizes of the 10 existing files among `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.config/opencode/*`, `~/.local/share/opencode/auth.json`, `~/.pi/agent/*`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md` and the real skill files were identical before and after. The only reads of the real home were those metadata checks and a listing of skill folder names used as leak markers.
- Every process the test started was stopped. A final process search found no proxy, stub or harness from the test.
- No credential was read, copied or printed. A pattern scan of the saved evidence found no key-shaped string.

## 13. Evidence

- In this repository: [the machine-readable results](HARNESS-MODEL-USE-ONE-CALL-2026-09-22.json) for all 27 model runs, the 5 dry runs, the 2 direct diagnostics and the parallel cross-check. Each run lists its codes, its answer, what was offered and used, its tokens, its status, its counts and its verdict.
- Kept privately, not in this repository, in the private research folder `research-2026-09-22/harness-isolation-tests/model-use-one-call-2026-09-22/`:
  - the runner (`run_step.py`), the counting proxy (`ollama_counting_proxy.py`) and its self-test;
  - the diagnostics, the parallel cross-check and the summarizer;
  - for every run: the harness's raw output, captured request and response bodies with authorization redacted, the stub logs, the settings files and the result;
  - the request ledger;
  - the before and after metadata of the global files;
  - the Ollama server log lines for the window.
- The step folders themselves were built under a scratch folder and are not kept.
