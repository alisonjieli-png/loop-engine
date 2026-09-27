# Agent meta-layers: Omnigent, the Agent Client Protocol and other ways to swap coding agents

Kind: dated research record for September 27, 2026. Every page, repository,
registry and package count below was read on September 27, 2026, United
States Eastern time. The [roadmap](../roadmap/roadmap.yaml) remains the only
task authority. Nothing in this record adopts an engine, installs a product,
changes a contract or makes a public claim.

This record builds on the [agent stack landscape](AGENT-STACK-LANDSCAPE-2026-09-24.md)
of September 24, which checked the Agent Client Protocol, Harbor, Deep Agents,
Tessl and 26 other entries, on the
[frontier harness positioning record](FRONTIER-HARNESS-POSITIONING-AND-EXPERIMENTS-2026-09-22.md),
the [ZCode market review](ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md)
and the [agent-harness record](AGENT-HARNESS-MADEBYWILD-2026-09-23.md). It does
not repeat their findings. It adds the products that orchestrate or swap
whole coding agents, and compares them with Baltor's plan.

## 1. The owner's question and the short answer

The owner, September 27, 2026:

> "can you do more research on this, omniharness / omniagent and other meta
> layers are becoming very similar to what I am putting together OMG... you can
> swap the whole agent underneath and not rewrite anything? Omnigent sits on top
> of Claude Code, Codex, Cursor and your own agents, so switching between them
> is just a config change instead of a rebuild. That's actually clever."

The short answer:

1. **The product in the quotation is Omnigent**, an open-source "meta-harness"
   built by people at Databricks and announced on June 13, 2026. It is
   Apache-2.0 and marked alpha. "Omniharness" and "omniagent" are names that
   several small, unrelated projects use; none of them is the product the
   quotation describes. Section 4 separates them.
2. **Yes, swapping the whole agent without rewriting is real, and it is now
   common and free.** In Omnigent, one field of an agent file,
   `executor.harness`, moves an agent between Claude Code, Codex, Cursor,
   OpenCode, Pi and about ten other named agents, or any Agent Client
   Protocol agent. The Agent Client Protocol does the same one level lower:
   its public registry lists 41 agents that any compatible client starts the
   same way. JetBrains Air, Zed, Harbor,
   OpenHands, Goose and Omnigent all use that protocol.
3. **None of these layers decides what each harness receives for one step.**
   That means the files, skills, tools and reusable code, chosen from a
   reviewed library, placed where that harness reads them, with loading
   checked, and the result accepted by a check that is not the agent. That is
   Baltor's product and it is still open ground. The evidence that it improves
   results does not exist yet (experiment E02 of the agent stack record).
4. **Recommendation.** Keep the Agent Client Protocol as the first tool-using
   engine behind Baltor's harness executor slot, drive it from the registry,
   and write native adapters only where the protocol loses control Baltor
   needs. Make Baltor a capability and context source that
   Omnigent and protocol clients call. Do not build a multi-agent interface:
   at least ten products already offer one, three of them from platform
   companies, and the company behind the most-starred free one, Vibe Kanban,
   is sunsetting it.

## 2. Summary

1. **Omnigent is large and fast-moving.** The repository was created on June
   11, 2026 and has 10,286 stars, 1,633 forks and 1,519 open issues and pull
   requests. Its package had 32,633 downloads in the last month. It wraps
   twelve agents as native terminal sessions and runs others through their
   vendors' libraries or the Agent Client Protocol. It adds policies
   (approval, tool-call caps, spend caps), an operating-system sandbox with an
   egress proxy that keeps real credentials outside the sandbox, twelve cloud
   sandbox providers, sessions shared across devices, and a "harness bench"
   that tests each harness's declared capabilities against live behavior. No
   price and no hosted paid service is published.
2. **Omnigent's unit of work is a conversation, not a step.** Each harness runs
   as a per-conversation process that can be resumed, shared and forked. What
   the agent receives comes from an agent directory the author writes:
   instructions, skills, tools and sub-agents. There is no catalogue, no
   search and no per-step selection of material. Acceptance is a sub-agent
   reviewer or the person who merges.
3. **The Agent Client Protocol has become the common executor interface.**
   Version 1.9.1 was released on September 18, 2026. The registry lists 41
   agents, and its quarantine file names 7 of them as failing a check. The
   protocol's Python library had 20,458,193 downloads in the last month.
   Claude Code and Codex are reached through adapters that the protocol's own
   organization now maintains; Cursor, Gemini CLI, GitHub Copilot, Goose,
   OpenCode, Junie, Kimi, Qwen Code and Devin are registered directly.
4. **Harbor now runs any registry agent** with `acp:<id>@<version>`, added on
   June 10, 2026, beside about 40 named agents. Baltor's chosen measurement
   backend can therefore run exactly the agents Baltor's executor would run.
5. **Platform companies have entered this layer.** GitHub Agent HQ was
   announced on October 28, 2025; Claude and Codex agents have been in public
   preview there since February 4, 2026, at one premium request per session.
   JetBrains Air entered public preview on March 9, 2026 and launched as a
   system with Air Teams and Air Governance on September 22, 2026. Databricks
   ships Omnigent. Anthropic sells Claude Managed Agents (April 8, 2026) at
   standard token rates plus 0.08 dollars per session-hour.
6. **The layer for people is crowded and hard to charge for.** Vibe Kanban,
   with 28,203 stars, has been sunsetting since April 10, 2026 because "the
   vast majority are free users and we couldn't find a business model that we
   could get excited about". Terragon shut down (open-source snapshot of
   January 16, 2026). Crystal was replaced in February 2026. Coder deprecated
   and archived `agentapi` and built its own agent. Mozilla.ai put `any-agent`
   into soft deprecation. The money that does flow goes to team seats and
   cloud workspaces: Conductor raised a 22 million dollar Series A (March 30,
   2026) and sells Teams at 60 dollars per user a month; Superset sells Pro at
   20 dollars per user a month.
7. **The vendors' own libraries already expose the per-step controls Baltor
   needs.** The Claude Agent SDK takes `setting_sources=[]` (no filesystem
   settings), a `skills` list that its own documentation calls "a context
   filter, not a sandbox", `max_budget_usd` and `output_format`. The Codex SDK
   takes a JSON schema for each turn's output. `opencode serve` takes a model
   and an agent for each message.
8. **Baltor is behind on execution and on reach.** On `main` (revision
   `923453a4`) the executor slot's contract exists, but no Agent Client
   Protocol client does, and the engine selector and step executor build were
   held out of `main` on September 25 until their own checks pass. Baltor had
   no paying subscriber on September 25.
9. **Baltor is different on what goes into each step and on acceptance.** It
   has a reviewed, licence-checked library searched for each step; native
   placement into OpenCode, Claude Code and Codex layouts on `main`; a fresh
   instance per step with decoy files that test whether only the selected
   material loaded; brokered model accounting; and acceptance only by an
   independent evaluator. No product read for this record documents that combination.
10. **An outside opinion supports that focus.** An Omnara post by Kartik
    Sarangmath (September 1, 2026) argues that harnesses have converged and
    that "All that matters is the system prompt and tools you give the
    harness, as well as the interface." That is an argument, not evidence.

## 3. How this was checked, and its limits

- **Discovery.** The web search allowance of this session was used up before
  this work began, so discovery used GitHub repository search, the Hacker
  News search interface (for dates and attention) and the package
  registries. Product pages, blogs and documentation were then fetched
  directly. A product that none of these surfaces names may be missing.
- **Counts.** Stars, forks, creation dates and last-push dates come from the
  GitHub interface. Download counts come from the pypistats service and include
  automated and dependency installs, so they show reach, not users.
- **Code read.** Omnigent's README, agent YAML specification, agent image
  specification, harness registry, harness bench design, harness plugin
  interface and skill discovery source were read on its `main` branch (package
  version `0.16.0.dev0`). The Agent Client Protocol registry file was
  downloaded and counted. Baltor statements come from `origin/main` at
  `923453a4`.
- **Not done.** Nothing was installed or run. No account was created, no model
  was called, nothing was bought and nobody was contacted.
- **Labels.** "Observed" means read in a primary source on the date above.
  "Inference" is this record's reading of what was observed. "Self-reported"
  marks a vendor's statement about its own results. "Not verified" marks what
  could not be checked. Where a page does not document something, this record
  says so and does not infer that it is absent.

## 4. What "Omnigent", "omniharness" and "omniagent" refer to

```text
Names in the owner's question, as found on September 27, 2026
├── Omnigent (omnigent-ai/omnigent): the Databricks meta-harness the quotation describes
├── "omniagent": no product of that name wraps coding agents
│   ├── an informal plural for Omnigent agents ("Example of Omniagents")
│   ├── pi-omniagent-extensions: other coding agents appear as models inside Pi
│   └── OmniAgents (charles-azam): one tool set across three agent frameworks
└── "omniharness": several small projects, one close to the idea
    ├── danduma/omniharness: supervises coding agents over the Agent Client Protocol
    ├── archimedes-run/omniHarness: its own long-horizon agent, a DeerFlow fork
    ├── shipking-ai/omniharness: its own agent for the OmniRoute gateway
    └── ymauhn/omniharness and jhlee0409/omni-harness-kit: portable skill kits
```

| Repository | What it does (observed) | Licence | Stars | Created | Last push |
|---|---|---|---|---|---|
| [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | "The open-source meta-harness for all your AI agents" over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi and agents written in YAML | Apache-2.0 | 10,286 | June 11, 2026 | September 27, 2026 |
| [danduma/omniharness](https://github.com/danduma/omniharness) | "a local control plane for supervising ACP-backed coding agents": one runner owns history, supervision and agent processes; web, desktop, phone and Visual Studio Code interfaces; can itself be served as an Agent Client Protocol agent | AGPL-3.0 | 17 | April 20, 2026 | September 23, 2026 |
| [archimedes-run/omniHarness](https://github.com/archimedes-run/omniHarness) | A self-extending long-horizon agent that began as a fork of ByteDance's DeerFlow 2.0 on LangGraph; it does not wrap other coding agents | MIT | 7 | May 6, 2026 | September 23, 2026 |
| [shipking-ai/omniharness](https://github.com/shipking-ai/omniharness) | "The agent harness built for OmniRoute", a model gateway; npm package `omniharness-cli` | MIT | 5 | August 26, 2026 | September 17, 2026 |
| [ymauhn/omniharness](https://github.com/ymauhn/omniharness) | Portable skills that Claude Code, Codex and Hermes all read, with a human approval gate | MIT | 0 | September 10, 2026 | September 26, 2026 |
| [jhlee0409/omni-harness-kit](https://github.com/jhlee0409/omni-harness-kit) | Reads a repository and generates instructions, agents and a verify hook for Claude Code, Codex, OpenCode and oh-my-pi | MIT | 2 | June 25, 2026 | July 22, 2026 |
| [sathish316/pi-omniagent-extensions](https://github.com/sathish316/pi-omniagent-extensions) | Pi extensions that drive Cursor, Codex, Claude Code and Atlassian Rovo Dev "as if it were just another model in Pi's `/model` picker", over the Agent Client Protocol or Codex's app-server | none detected | 7 | May 23, 2026 | July 26, 2026 |
| [charles-azam/OmniAgents](https://github.com/charles-azam/OmniAgents) | "Write tools once, run them anywhere" across local, Docker and E2B backends and the smolagents, Pydantic AI and LangChain frameworks | none detected | 9 | October 16, 2025 | December 30, 2025 |
| [dmatrix/omnigent_examples](https://github.com/dmatrix/omnigent_examples) | Examples for Omnigent, described as "Example of Omniagents" | Apache-2.0 | 3 | June 1, 2026 | August 14, 2026 |
| [FrancescoStabile/omnigent](https://github.com/FrancescoStabile/omnigent) | An unrelated agent framework with the same name | MIT | 33 | February 11, 2026 | February 14, 2026 |
| [rugovit/omnigento](https://github.com/rugovit/omnigento) | Keeps instructions consistent across Cursor, Claude, Copilot, Codex and `AGENTS.md` from one source | Apache-2.0 | 9 | May 24, 2026 | May 24, 2026 |
| [OmniHarness/OmniHarness](https://github.com/OmniHarness/OmniHarness) | Code for a visual generation research paper; unrelated | Apache-2.0 | 70 | September 12, 2026 | September 21, 2026 |

Inference: the owner's wording matches Omnigent's own claim, "switch between
Claude Code, Codex, Pi, and your own agents with one-line changes"
(Databricks announcement, June 13, 2026). Of the "omniharness" projects, only
danduma/omniharness is a meta-layer over existing coding agents, and it is a
one-person project with 17 stars.

## 5. Omnigent in detail

### 5.1 Maker, dates and reach

| Fact | Observed |
|---|---|
| Maker | The website: "Built by the Databricks AI team, Neon and the Omnigent Contributors." The package metadata names "Databricks, Inc." as author. The announcement on the Databricks blog (June 13, 2026) is by Matei Zaharia, Kasey Uhlenhuth and Corey Zumar. Several of the most active contributors list Databricks as their employer |
| Releases | First package `0.0.1rc1` on June 9, 2026; `0.15.0` on September 22, 2026 (GitHub release on September 24); 38 package releases including candidates; `main` is at `0.16.0.dev0` |
| Reach | 10,286 stars, 1,633 forks, 1,519 open issues and pull requests, 46 watchers; package downloads of 714 in the last day, 8,508 in the last week and 32,633 in the last month |
| Attention | The announcement reached 15 points on Hacker News on June 13, 2026; later submissions drew fewer |
| Price | No plan, price or hosted paid service on the website, the README or the announcement |
| Status | "Omnigent is alpha and built in the open" |
| Telemetry | "Omnigent collects anonymized usage data (telemetry) by default", with a documented opt-out |
| Ecosystem | A Go client library (sei-protocol), a Cloudflare Containers sandbox provider, graph memory, an MLflow tracing adapter by a Databricks engineer, and a voice demo fork by Thomas Wolf of Hugging Face. MoonMind states: "Omnigent is to become MoonMind's primary runtime provider over time" |

Inference, not verified: Databricks benefits when agents use Databricks model
serving, its gateway or Databricks Apps. Databricks authentication is one of
four first-class credential kinds, and Databricks Apps is a documented deploy
target. No document read says this is the business plan.

### 5.2 How the swap works

Observed in the README, the agent YAML specification and the harness registry:

- An agent is a YAML file or an agent directory. `executor.harness` names the
  agent program, `--harness` overrides it for one run, and each sub-agent may
  name its own harness, "e.g. a `cursor` coder with a `claude-sdk` reviewer".
- Harnesses come in three families:
  - **headless harnesses** drive the agent through its vendor library or its
    headless mode: `claude-sdk` (the Claude Agent SDK), `openai-agents`,
    `codex`, `cursor`, `antigravity` (Google's Antigravity SDK), `copilot`
    (the GitHub Copilot SDK), `pi` and `goose`;
  - **native harnesses** wrap the vendor's own terminal program in tmux, so a
    person sees the real interface: Claude Code, Codex, Pi, OpenCode, Cursor,
    Kiro, Goose, Devin, Antigravity, Qwen Code, Kimi and Hermes;
  - **protocol harnesses**: `acp:<slug>` runs "any configured Agent Client
    Protocol server command"; Grok Build and Devin are reached this way, and
    Qwen Code through `qwen --acp`.
- Each harness runs as "per-conversation subprocesses that implement a subset
  of the Omnigent REST API", served over a Unix socket. The announcement
  describes the common shape as "messages and files in, text streams and tool
  calls out".
- A new harness registers as a Python entry point in the
  `omnigent.community.harness` group, so a separate package can add a harness
  without editing the core.

Adapted from the agent YAML specification:

```yaml
name: coding_pair
prompt: You are a careful coding agent.
executor:
  harness: claude-sdk          # or codex, cursor, opencode, pi, acp:<slug>, ...
tools:
  coder:
    type: agent
    executor:
      harness: cursor          # a sub-agent may run on a different harness
      model: gpt-5
```

### 5.3 Models and credentials

Omnigent accepts four credential kinds: a first-party vendor key; a subscription
(a Claude Pro or Max plan, or a ChatGPT plan, through the official command
lines); a gateway, meaning "Any OpenAI- or Anthropic-compatible `base_url` and
key (OpenRouter, LiteLLM, Ollama, vLLM, Azure)"; and a Databricks workspace.
Defaults are set per agent and `/model` switches the model during a session.
Some harnesses (Cursor, GitHub Copilot, Antigravity) talk only to their
vendor's backend and cannot use a gateway.

### 5.4 What an Omnigent agent receives

- An **agent image** is a directory with `config.yaml`, `AGENTS.md`,
  `skills/<dir>/SKILL.md`, `tools/python`, `tools/typescript`,
  `tools/mcp/*.yaml` and `agents/` for sub-agents. The server stores it as a
  tarball.
- Skills follow the Agent Skills limits (a name of up to 64 characters, a
  description of up to 1,024). For Claude harnesses the bundle's skills are
  exposed through Claude Code's plugin convention (`--plugin-dir` with
  `--setting-sources`). Skills already on the machine are discovered per
  vendor family (Claude plugins, `~/.codex/skills`, `~/.cursor`, Pi,
  Antigravity, Devin), and a skills filter selects all, none or a list.
- `instructions: AGENTS.md` shares one instruction file with other tools. For
  Pi, `context_files: false` stops automatic discovery of `AGENTS.md` and
  `CLAUDE.md`.
- Tools are Model Context Protocol servers (a command or a URL), Python
  functions and sub-agents.

Inference: material is authored per agent and loaded per conversation.
Nothing in the pages read chooses material for a step from a catalogue, and
nothing records whether a skill was listed, loaded or used.

### 5.5 Control and safety

- **Policies** inspect requests, responses, tool calls and tool results at
  three levels: server, agent and session. Built-ins ask before shell
  commands or file writes, cap tool calls per session, and enforce a cost
  budget (`max_cost_usd`, with warning thresholds). Inline rules use the
  Common Expression Language. The announcement: guardrails "at the
  meta-harness layer, not via prompts".
- **Sandbox**: Bubblewrap on Linux, Seatbelt on macOS, and a job object on
  Windows that "does not isolate the filesystem or network". Egress rules pass
  through an application-layer proxy, and a "secretless credential proxy" lets
  sandboxed tools authenticate "without the real secret ever entering the
  sandbox". Copy-on-write overlays exist for one harness.
- **Cloud sandboxes**: Modal, Daytona, Blaxel, Islo, E2B, Gensee, CoreWeave,
  Kubernetes, NVIDIA OpenShell, Boxlite, microsandbox and Databricks.

### 5.6 The harness bench

The harness bench is described as "shipped and in use". It has six `P0`
probes (basic turn, streaming, tool calling, policy deny, model override,
interrupt) and six `P1` probes (fork replay, reasoning, the Omnigent tool
relay, policy allow, policy ask, cost tracking). Each probe reads the
harness's declared flag and returns `DRIFT` when a live turn disagrees.
Offline conformance runs on every pull request and live probes run nightly.
The design record lists declarations the bench corrected, for example Kiro,
Cursor and Qwen Code declared as streaming although live turns showed no
streamed text.

Inference: this is the same idea as the qualification ladder of roadmap step
S-6.31 (declared is not observed), applied to control features. Baltor's
ladder applies it to material: listed, loaded and used.

### 5.7 What Omnigent does not document

Not found in the pages read, and not inferred absent:

- a fresh harness instance per step that holds only that step's material;
- selection among harnesses by recorded evidence;
- acceptance of a task result by an evaluator that is independent of the
  agent;
- a price, a hosted service or a service-level commitment.

## 6. The wider landscape, by layer

```text
Where a meta-layer changes the agent
├── Protocol: the client speaks one protocol; the agent is any registered program
│   └── Agent Client Protocol and its registry (41 agents)
├── Wrapper: one server or library translates each agent's own interface
│   ├── Omnigent harness processes (headless, native terminal, protocol)
│   ├── Rivet Sandbox Agent and AgentBox: an HTTP server inside a sandbox
│   └── coder/agentapi: terminal emulation (deprecated)
├── Platform: a vendor runs several agents under one account and policy
│   └── GitHub Agent HQ, JetBrains Air, OpenHands Agent Canvas, Goose
├── Workspace: a person's application starts any command-line agent in a git worktree
│   └── Conductor, Superset, Emdash, Claude Squad, Sculptor, Vibe Kanban
├── Evaluation: a benchmark runner installs any agent in a fresh container per trial
│   └── Harbor
├── Configuration: one source is copied into each agent's native files
│   └── ruler, rulesync, Microsoft APM, Sentry dotagents, agent-harness
└── Model: the agent stays; the model behind it changes
    └── Claude Code Router, ollama launch, gateway credentials
```

### 6.1 Protocols and their clients

| Project | What it abstracts and how (observed) | Licence and price | Reach | Dates and status |
|---|---|---|---|---|
| [Agent Client Protocol](https://github.com/agentclientprotocol/agent-client-protocol) | The connection between a client (an editor or an orchestrator) and an agent program: JSON-RPC over standard input and output; `initialize` negotiates capabilities; the client answers permission requests and may serve file and terminal requests | Apache-2.0, free | 4,335 stars; Python library `agent-client-protocol` 0.12.1 with 20,458,193 downloads last month; TypeScript library 1.5.0 | Repository from June 23, 2025; version 1.9.1 on September 18, 2026. Remote transport was still a draft on September 25 (agent stack record) |
| [Agent Client Protocol registry](https://github.com/agentclientprotocol/registry) | A curated list of agents that "support user authentication", verified in continuous integration for valid `authMethods`; versions update hourly; separate indexes for JetBrains | Apache-2.0 | 41 agents in `registry.json` version 1.0.0; 7 named in the quarantine file | Created December 17, 2025 |
| [claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp) and [codex-acp](https://github.com/agentclientprotocol/codex-acp) | Adapters: the first runs the Claude Agent SDK; the second "starts the Codex App Server, translates ACP requests into Codex operations". Both moved from Zed's organization to the protocol's own; `zed-industries/codex-acp` is archived | Apache-2.0 repositories; the registry marks the Claude entry "proprietary" | 2,587 stars for the Claude adapter | Active; Claude adapter version 0.81.2 and Codex adapter 1.13.1 in the registry |
| Clients | Zed; JetBrains development environments (December 2025) and JetBrains Air; Omnigent (`acp:<slug>`); Harbor (`acp:<id>@<version>`); OpenHands Agent Canvas; Goose; [acpx](https://github.com/openclaw/acpx), a headless command line from OpenClaw (MIT, 3,286 stars, "pre-1.0"); [Toad](https://github.com/batrachianai/toad), a terminal interface (AGPL-3.0, 3,450 stars); danduma/omniharness | Mostly free | See each project | Various |

Registered agents on September 27, 2026 include Amp, Auggie, Claude Agent,
Cline, Codex, Cursor, Deep Agents, Devin, Factory Droid, Gemini CLI, GitHub
Copilot, Goose, Grok Build, Junie, Kilo, Kimi CLI, Mistral Vibe, OpenCode,
Pi (through `pi-acp`), Poolside, Qwen Code and Google Antigravity.

### 6.2 Programmatic control of one agent

| Project | What it abstracts and how (observed) | Licence and price | Reach | Dates and status |
|---|---|---|---|---|
| [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) | Runs Claude Code as a library. Options include `setting_sources` ("Pass `[]` to disable filesystem settings"), `skills` (a list; "a **context filter**, not a sandbox"), `plugins`, `agents`, `sandbox`, `max_budget_usd`, `max_turns`, `fallback_model` and `output_format` | MIT repository; model use billed by Anthropic | 8,172 stars; 28,944,305 downloads last month | Version 0.2.160 |
| [Codex SDK](https://github.com/openai/codex/tree/main/sdk/typescript) | "wraps the `codex` CLI" and "exchanges JSONL events"; threads, streamed events and an `outputSchema` per turn; a Python folder sits beside it; the app-server is the JSON-RPC interface that `codex-acp` uses | Apache-2.0 | Codex repository 126,738 stars | TypeScript package 0.157.1 |
| [OpenCode server](https://opencode.ai/docs/server/) | `opencode serve` "runs a headless HTTP server" with an OpenAPI 3.1 description; sessions; model and agent chosen per message | MIT | OpenCode repository 210,370 stars | Active |
| [GitHub Copilot SDK](https://github.com/github/copilot-sdk) | Six languages talk JSON-RPC to the Copilot command line in server mode | MIT; needs a Copilot subscription unless the user brings a key; "each prompt being counted towards your usage allowance" | 10,523 stars | Created January 14, 2026 |
| [coder/agentapi](https://github.com/coder/agentapi) | An HTTP interface over terminal agents | MIT, free | 1,500 stars | "deprecated and no longer maintained"; archived. Coder now points to [Coder Agents](https://coder.com/docs/ai-coder/agents), whose loop runs in Coder's control plane: "It is not a wrapper around third-party agent tools like Claude Code or Codex" |
| [Rivet Sandbox Agent](https://github.com/rivet-dev/sandbox-agent) | A Rust server inside a sandbox with one HTTP interface for Claude Code, Codex, OpenCode, Cursor, Amp and Pi: "write your code once, swap agents with a config change"; a universal session schema | Apache-2.0 | 1,576 stars | Shown on Hacker News January 28, 2026; last push June 19, 2026 |
| [AgentBox SDK](https://github.com/TwillAI/agentbox-sdk) | TypeScript: "swap agents and infrastructure providers without changing your code" | No licence detected | 163 stars | Last push September 25, 2026 |

### 6.3 Meta-harnesses and agent platforms

| Project | What it abstracts and how (observed) | Licence and price | Reach | Dates and status |
|---|---|---|---|---|
| Omnigent | Section 5 | Apache-2.0; no price | 10,286 stars | Alpha, June 2026 |
| [OpenHands Agent Canvas](https://github.com/OpenHands/OpenHands) | "Run OpenHands, Claude Code, Codex, Gemini, or any ACP-compatible agent across local, remote, and cloud backends", through the OpenHands Agent Server | MIT; OpenHands Cloud is the commercial offering | 89,290 stars | Active |
| [Goose](https://github.com/aaif-goose/goose) | Its own agent, and also "ACP providers" for Claude, Codex, Amp and Pi that "pass goose extensions through to the agent as MCP servers"; session resume and fork are "not supported yet" for them | Apache-2.0; part of the Agentic AI Foundation at the Linux Foundation | 54,705 stars | Active |
| [JetBrains Air](https://blog.jetbrains.com/blog/2026/09/22/introducing-jetbrains-air/) | "one system for building software with agents": Air in JetBrains development environments, Air Teams and Air Governance; agents "Claude Agent, Codex, Junie, Copilot, OpenCode" plus "any you can connect via ACP" from the registry | Bring a subscription, key or base URL, or JetBrains credits "billed at public API rates" | 74 points on Hacker News on September 22, 2026 | Public preview March 9, 2026; system launch September 22, 2026; integration in the development environments is alpha |
| [GitHub Agent HQ](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/) | Agents from several vendors in GitHub, GitHub Mobile and Visual Studio Code, with an enterprise control plane to "control which agents are allowed" | Copilot Pro+ and Enterprise; "Each coding agent session consumes one premium request" | Not published | Announced October 28, 2025; Claude and Codex in public preview since February 4, 2026 |
| [Omnara](https://github.com/omnara-ai/omnara) | Began as remote control for Claude Code and Codex; now "The API for production-grade agents", "The open-source alternative to Claude Managed Agents", with its own loop over model interfaces | Apache-2.0; "$0 platform fee"; machines at 0.0414 dollars per GiB of memory per hour | 2,873 stars; 310 points on Hacker News (August 12, 2025) | A Y Combinator Summer 2025 company; launch post February 12, 2026 |
| [Claude Managed Agents](https://claude.com/blog/claude-managed-agents) | Anthropic runs "a built-in orchestration harness", sandboxing, sessions and memory | Standard token rates plus 0.08 dollars per session-hour | 169 points on Hacker News | April 8, 2026 |

### 6.4 Parallel workspace applications for people

| Project | What it does (observed) | Licence and price | Reach | Dates and status |
|---|---|---|---|---|
| [Conductor](https://conductor.build) | "Run parallel Claude Code, Codex, and Cursor agents in isolated workspaces on your Mac" | Closed source; Free, Pro 50 dollars a month, Teams 60 dollars per user a month, Enterprise; "Bring your own subscriptions and keys" | Self-reported adoption at Google, Meta, Amazon and others | Series A of 22 million dollars on March 30, 2026 (Spark Capital, Matrix, Y Combinator) |
| [Superset](https://github.com/superset-sh/superset) | Runs "Claude Code, Codex, or another CLI agent" in worktrees with review and previews | Elastic License 2.0 (source available); Free, Pro 20 dollars per user a month (15 dollars yearly), Enterprise | 14,671 stars | A Y Combinator company; launch post on Hacker News May 22, 2026 |
| [Emdash](https://github.com/generalaction/emdash) | Each task in its own worktree; Claude Code, Codex, Cursor, OpenCode, Amp, Devin, Qwen Code, Droid and GitHub Copilot; installs marker-tagged hooks in each agent's user configuration | Apache-2.0 | 5,850 stars | Y Combinator Winter 2026; shown on Hacker News February 24, 2026 |
| [Claude Squad](https://github.com/smtg-ai/claude-squad) | tmux and git worktrees for Claude Code, Codex, Gemini, Aider, OpenCode and Amp | AGPL-3.0, free | 8,537 stars | Last push August 20, 2026 |
| [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) | Kanban planning plus workspaces for "10+ coding agents" | Apache-2.0 | 28,203 stars | Sunsetting since April 10, 2026; the open-source project continues "community maintained" |
| [Terragon](https://github.com/terragon-labs/terragon-oss) | Cloud background agents for Claude Code, Codex, Amp and Gemini | Apache-2.0 snapshot | 259 stars | Shut down; snapshot of January 16, 2026 |
| [Crystal](https://github.com/stravu/crystal), now [Nimbalyst](https://github.com/nimbalyst/nimbalyst) | Parallel Codex and Claude Code sessions in worktrees; Nimbalyst adds visual editing of the agents' work | MIT | 3,122 and 1,786 stars | Crystal deprecated February 2026 |
| [Sculptor](https://github.com/imbue-ai/sculptor) | Parallel agents in isolated workspaces; integrated support for Claude Code and Pi, and "any terminal-based agents" | MIT; research preview | 232 stars; 176 points on Hacker News (September 30, 2025) | Active |
| [xum](https://github.com/coder/xum) | Coder's desktop application for parallel work; its own agent loop, with Ollama and OpenRouter models | AGPL-3.0 | 2,038 stars | Renamed from mux after a trademark concern |
| [Agent Deck](https://github.com/asheshgoplani/agent-deck) | One terminal view of many Claude, Gemini, OpenCode and Codex sessions | MIT | 960 stars | Active |

### 6.5 Evaluation, frameworks and configuration

| Project | What it abstracts and how (observed) | Licence | Reach | Dates and status |
|---|---|---|---|---|
| [Harbor](https://github.com/harbor-framework/harbor) | Evaluates "arbitrary agents like Claude Code, OpenHands, Codex CLI, and more" in containers; about 40 named agent modules plus a generic Agent Client Protocol agent that reads the registry | Apache-2.0 | 5,637 stars | Registry agents added June 10, 2026; the official harness for Terminal-Bench 2.0 |
| [any-agent](https://github.com/mozilla-ai/any-agent) | One interface over Agno, Google ADK, LangChain, LlamaIndex, the OpenAI Agents SDK and smolagents | Apache-2.0 | 1,238 stars | "in soft deprecation"; its core became `mozilla-ai-tinyagent` |
| [Flue](https://github.com/withastro/flue) | A TypeScript framework for building an agent harness (model, sandbox, skills, tools); not a layer over existing agents | Apache-2.0 | 8,379 stars | Created February 7, 2026 |
| [ruler](https://github.com/intellectronica/ruler) | One `.ruler/` folder of instructions copied into each agent's files, with Model Context Protocol settings | MIT | 2,936 stars | "Beta Research Preview" |
| [rulesync](https://github.com/dyoshikawa/rulesync) | Imports and converts configuration between tools | MIT | 1,477 stars | The E01 pilot of September 25 found it rewrites served bytes |

Microsoft APM, Sentry dotagents and agent-harness are covered in the
[agent stack landscape](AGENT-STACK-LANDSCAPE-2026-09-24.md) and the
[agent-harness record](AGENT-HARNESS-MADEBYWILD-2026-09-23.md).

### 6.6 Model routing under an unchanged agent

- [Claude Code Router](https://github.com/musistudio/claude-code-router) (MIT,
  37,446 stars) is "a local model gateway and control plane for coding
  agents" that gives Claude Code, Codex, Grok CLI, Kimi CLI, Kilo Code,
  OpenCode, Pi and others "one stable local endpoint".
- [ollama launch](https://ollama.com/blog/launch) (January 23, 2026) "sets up
  and runs your favorite coding tools like Claude Code, OpenCode, and Codex
  with local or cloud models"; Droid is the fourth.
- Omnigent's gateway credentials do the same inside Omnigent (section 5.3).

This matters for Baltor's overnight proof: Claude Code, Codex and OpenCode
can already run on Ollama Cloud models through a documented command.

### 6.7 What the movement shows

Observed:

- Four agent-wrapping layers stopped or were retired in 2026: Terragon
  (January), Crystal (February), Vibe Kanban (April) and `agentapi`
  (archived). A fifth, `any-agent`, is in soft deprecation.
- Four platform companies now ship a layer above several agents: GitHub,
  JetBrains, Databricks and, for its own models, Anthropic.
- Investors fund the workspace layer: Conductor's Series A, and Superset and
  Emdash in Y Combinator.
- At least six other layers use the Agent Client Protocol or its registry:
  JetBrains Air, Omnigent, Harbor, OpenHands, Goose and acpx.

Inference:

- Swapping the agent is now a commodity. Nobody read here charges for the
  swap itself. Where money is charged, it is for team seats, cloud
  workspaces, governance and hosted compute.
- A layer that only swaps agents competes with free open-source projects and
  with the platforms developers already pay for.
- The part that is still open is what each agent receives and how its result
  is checked. Omnara's post argues the same from the other side: the harness
  loop has converged, so the prompt, the tools and the interface decide the
  result. That is an opinion, not a measurement.

## 7. Baltor compared point by point

### 7.1 Where the executor slot sits

The complete classification comes first:

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

Baltor's default design gives every step its own harness: each step is a
discrete cognitive or act step Loop node that runs in a freshly started
harness holding only the context that step needs. The
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
defines it. A harness, a meta-harness or a protocol client is an engine that a
Loop uses through the step executor slot; it is never a new runtime type.

```text
A step of an owning Loop
└── step executor slot: step_run_request/v1 in, step_run_result/v1 out
    ├── Agent Client Protocol client engine ──> any registered agent (planned)
    ├── vendor-native engines ──> Claude Agent SDK, Codex app-server, OpenCode server, Pi (planned)
    ├── meta-harness wrapper engine ──> Omnigent ──> its harness (proposed here, trial only)
    ├── text relay recipes ──> 18 command-line styles, text only (exists)
    └── framework kits ──> Pydantic AI, OpenAI Agents, Microsoft Agent Framework, Deep Agents (exist, in process)
```

What Baltor has on `main` at `923453a4`, observed:

- The slot record `step_executor` in
  [engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml):
  `implementation_state: candidate`, contract
  `external_harness_adapter/v2`, ten engine kinds, ranking by tokens,
  elapsed seconds and priced cost, and an evidence minimum floor of 10.
- The design in
  [Engines behind fixed edges, section 13](../architecture/ENGINES-BEHIND-FIXED-EDGES.md#13-the-step-executor-slot-s-631-phase-2-of-the-harness-first-plan):
  typed step request and result records, OpenCode through the Agent Client
  Protocol as the first tool-using engine and Goose second,
  `fresh_instance_per_step` recorded as `proven` or `unproven`, and a
  `delegated` flag computed by the envelope, never by the engine.
- Commit `e09d70bd` (September 25) held the engine selector and step executor
  build out of `main` until their own checks pass.
- No Agent Client Protocol client exists in the source; the protocol appears
  only in comments of `harness_recipes.py`.
- Present: text relay recipes run in Bubblewrap with model calls brokered by a
  relay whose "Real model authority stays in the parent broker"; fresh
  instance recipes that start a harness "with an empty home folder" and plant
  decoy files to check loading (roadmap S-6.42); native skill placement for
  OpenCode, Claude Code and Codex (commit `4ca0f568`, September 24); a Goose
  recipe; adapters for four agent frameworks.
- The hosted library is served through Baltor's Model Context Protocol
  endpoint. On September 25 it served 93 packages and had no paying
  subscriber ([ninety-day plan](../context/NINETY-DAY-PLAN-2026-09-25.md)).

### 7.2 The comparison

| Dimension | Meta-layers (observed) | Baltor (observed on `main`, then planned) | Verdict (inference) |
|---|---|---|---|
| Swapping the agent | Omnigent: one field or flag. Agent Client Protocol clients: any of 41 registered agents. Rivet Sandbox Agent: "a config change". Harbor: `--agent` | Text relay styles chosen by a host file; no tool-using harness engine. Planned: "a second harness can replace it by configuration" (S-6.31) | Done elsewhere and free. Adopt the protocol; build native adapters only where it loses needed control |
| A fresh harness per step | Omnigent: one process per conversation, with resume, share and fork. acpx: persistent sessions, or `exec` for "a stateless run". Harbor: a fresh container per trial | Fresh instance recipes with decoys exist. Planned: `fresh_process` by default and `fresh_instance_per_step` proven per engine | Different. No meta-layer read here optimizes for a fresh harness per step. Harbor's per-trial isolation is closest |
| Context and capability supply | Omnigent: an author-written agent image and per-vendor skill discovery. Vendor libraries: skills filters and setting sources. Protocol clients hand Model Context Protocol servers to each session. No catalogue or per-step selection | A reviewed, licence-checked hosted library with search and retrieval; native placement for three harnesses. Planned: per-step selection, the working directory compiler (S-6.44), weekly harness file profiles (S-6.80) | Different, and Baltor's product. Integrate: serve into Omnigent agent images and protocol sessions |
| Typed contracts and engines | Omnigent: `spec_version: 1` YAML, Pydantic models, declared capabilities per harness, plugins by entry point. The author picks the harness | Typed, versioned records, engine kinds and refusals. Planned: pinned, preferred and automatic selection by recorded evidence (S-6.74) | Different: evidence-ranked selection across harnesses is not documented elsewhere. Weaker today: the selector is not on `main` |
| Independent acceptance | Omnigent's Polly routes "each diff to a reviewer from a different vendor than the one that wrote it"; a person merges. Harbor has separate verifiers | The `response_evaluator` slot is derived from the evaluation contract; a planned check refuses an engine that evaluates its own output | Different. Harbor is the measurement engine; Polly's cross-vendor review is a useful pattern for Baltor's reviews |
| Cost and model routing | Omnigent: four credential kinds including subscriptions and gateways, a cost budget policy, per-harness model override. Claude Code Router and ollama launch route models under an unchanged agent | Model calls of confined harness processes are brokered through the relay; unknown usage stays unknown. Planned: routes per thinking power and a model call strategy slot | Baltor is stricter but weaker for subscription users: a command line signed in with a subscription cannot be pointed at Baltor's broker. The plan needs a "reported, not brokered" accounting mode for such engines, as the remote agent kind already has |
| Sandbox and credentials | Omnigent: Bubblewrap and Seatbelt, egress rules, a secretless credential proxy, twelve cloud sandbox providers | Bubblewrap confinement with a cleared environment; egress proxy and remote kinds planned | Omnigent is ahead. Adopt the secretless proxy pattern, which the agent stack record also noted at Runloop |
| Qualification | Omnigent's harness bench: declared versus observed, with `DRIFT` | A qualification ladder (connected, material listed, material loaded, step finished, independently accepted) with decoys; four text relay recipes qualified offline | Complementary. Omnigent checks control features, Baltor checks material. Adopt `DRIFT` as a verdict in Baltor's ladder |
| People-facing sessions | Omnigent: devices, sharing, co-driving, forks. Conductor, Superset, Emdash and others | None, and not a goal | Do not build |
| Distribution | Omnigent: 32,633 downloads a month. The protocol's Python library: over 20 million. Platforms: GitHub and JetBrains customers | 18 accounts and no paying subscriber on September 25 | Weaker. Reach their users through integrations |

## 8. Adopt, differ, weaker

### 8.1 Where these products already do what Baltor plans

Baltor should adopt or integrate these, not build them:

- **Starting and driving many agents through one interface.** The Agent Client
  Protocol, its registry and its maintained adapters for Claude Code and Codex
  cover much of what the engine design planned to reach through separate
  native adapters (the Codex app-server and Claude Code print mode).
- **A capability bench with declared-versus-observed verdicts.** Omnigent's
  bench is the model for the "harness handshakes" of roadmap step S-6.80.
- **Running the same agents under measurement.** Harbor runs registry agents
  directly, so experiment E02 needs no Baltor-specific runner.
- **Credentials that never enter the sandbox.** Omnigent's secretless proxy
  and Runloop's gateway both show the pattern for the `process_confinement`
  slot.
- **Model swapping under an agent.** Claude Code Router, ollama launch and
  gateway credentials already let Claude Code, Codex and OpenCode run on other
  models, including Ollama Cloud.

### 8.2 Where Baltor's design is different

- **The unit is a step, not a conversation.** A fresh harness per step, with
  a recorded proof that only the step's material loaded, is Baltor's default.
  The meta-layers keep long sessions and add compaction, resume and forks.
- **Material is chosen, not authored.** Baltor searches a reviewed,
  licence-checked library and places the chosen files where each harness reads
  them. The meta-layers load what the author put in the agent directory.
- **Loading and use are facts to record.** Offered, fetched, installed,
  listed, loaded, used, useful and accepted are separate rungs in Baltor. No
  meta-layer read here records whether a skill was loaded or used.
- **Acceptance is independent.** The engine's completion is never acceptance
  in Baltor; an evaluator derived from the evaluation contract decides.
- **Engines are chosen by evidence.** Baltor plans automatic selection above a
  minimum sample. The meta-layers leave the choice to the author or the
  person.

### 8.3 Where Baltor is weaker

- **Execution.** No tool-using harness engine is on `main`, and the step
  executor build is held back. Omnigent names about fifteen agents today and
  can start any registered Agent Client Protocol agent.
- **Breadth.** Omnigent covers subscriptions, gateways, twelve cloud sandbox
  providers, three operating systems and a desktop application.
- **Evidence.** Baltor has not yet measured that its material helps a step
  (E02 has not run). Omnigent's claims are also unmeasured, but it does not
  sell a benefit.
- **Reach and trust.** Omnigent carries the Databricks name and 10,286
  stars; JetBrains and GitHub carry their customers. Baltor had 18 accounts on
  September 25.
- **Subscription users.** Baltor's broker cannot account for a harness that
  talks to its vendor under a subscription sign-in.

## 9. Recommendations

### 9.1 Engines behind the harness executor slot, in order

1. **An Agent Client Protocol client engine** (`agent_protocol_harness`),
   built on the official Python library (Apache-2.0), as the first tool-using
   engine. Keep the planned order, OpenCode then Goose, and add the
   maintained Claude Code and Codex adapters third and fourth, because those
   two harnesses carry the largest audiences. Read the registry file as the
   inventory of candidate executor profiles (the agent stack record's F7):
   pin each agent's version and distribution, honour the quarantine file, and
   start no agent that has not climbed the qualification ladder. Reasons: one
   thin adapter reaches the agents that JetBrains Air, Zed, Omnigent, Harbor,
   OpenHands and Goose already use; the registry checks authentication in
   continuous integration; the library had over 20 million downloads last
   month. Keep the engine design's rule that the sandbox, not the protocol's
   file methods, is the effect boundary.
2. **Harbor as the measurement engine**, as already decided, now using the
   same registry agents (`acp:<id>@<version>`). E02 should compare each agent
   with and without Baltor's material on the same task population.
3. **Vendor-native engines where the protocol loses control Baltor needs.**
   The Claude Agent SDK maps the step request almost field for field: the
   step's skills to `skills=[...]`, isolation to `setting_sources=[]`, the
   budget to `max_budget_usd`, the output ports to `output_format`. The Codex
   app-server or Codex SDK maps output ports to `outputSchema`;
   `opencode serve` takes a model and agent per message; Pi has its remote
   control mode.
   This is already step 4 of the engine design.
4. **Omnigent as a wrapper engine, as a trial only**, under the rule of roadmap
   step S-6.75 that every adopted project runs behind the slot beside a
   Baltor-native engine. Use it for agents that neither the registry nor a
   native engine covers (for example Kiro and Hermes, which are not in the
   registry) and for customers who sign in with a vendor subscription. It must
   pass these gates first: a fresh instance per step with the decoy check;
   the process identity and sandbox digest the envelope needs; Omnigent's
   Bubblewrap working inside Baltor's; telemetry off; a pinned version; and
   model calls either brokered through a gateway credential that points at
   Baltor's relay or recorded as reported. Reason for trial only: it is alpha,
   and its server, runner and database would sit inside Baltor's envelope as a
   second control plane with its own policies and sandbox.
5. **Watch only.** Rivet Sandbox Agent (no push since June 19, 2026),
   AgentBox SDK (no licence), Claude Managed Agents and Omnara (hosted; a
   future `remote_agent` engine if a customer asks), Coder Agents (its own
   loop).
6. **Do not adopt.** `agentapi` (deprecated), `any-agent` (soft deprecation),
   and the workspace applications, which are products for people rather than
   engines.

### 9.2 Integrations that make Baltor the provider these layers call

1. **Omnigent.** Publish a quickstart and an agent image template: a
   `tools/mcp/baltor.yaml` that points at Baltor's hosted endpoint with the
   customer's key taken from the environment, and Baltor's installer placing
   the selected skills under `skills/`. Check before publishing: Omnigent's
   agent image says "Only the HTTP (SSE) transport is supported" for
   `tools/mcp`, and Baltor's endpoint must be tested against that (not
   verified). Test that Omnigent's skill tool lists the placed skills.
2. **Agent definition bundles as a library file kind.** Omnigent agent
   images, Goose recipes, OpenCode agents, Claude Code subagents and GitHub
   Copilot custom agents are files that a harness picks up, which is the
   owner's definition of harness intelligence. An Omnigent agent image runs on
   about fifteen named harnesses, so one reviewed package serves many
   customers.
3. **Agent Client Protocol clients.** Document how to add Baltor's Model
   Context Protocol server in Zed, JetBrains Air, OpenHands Agent Canvas and
   acpx. Goose deserves a page of its own: its "ACP providers pass goose
   extensions through to the agent as MCP servers", so one Baltor extension in
   Goose reaches Claude, Codex, Amp and Pi.
4. **Workspace applications.** Conductor, Superset, Emdash, Claude Squad,
   Nimbalyst and Sculptor start the customer's own command-line agent in a git
   worktree. Baltor's native placement already writes into a project folder;
   each application needs a short setup page. How each application runs a
   setup step per worktree was not verified here.
5. **Evidence pages.** Publish the Harbor with-and-without results per agent
   once E02 has run, and only what the saved evidence supports.

### 9.3 Positioning

- The layers above make the agent replaceable. Baltor makes what each step
  receives selectable, whichever agent runs it. A draft line for the site,
  evaluative and without numbers: "Swap agents with any meta-harness. Baltor
  supplies what each step needs, whichever agent runs it."
- Keep the owner's category phrase, harness and agent optimized operation.
- Name Omnigent, Zed, JetBrains Air or Goose on a public page only after a
  recorded test shows Baltor's material loading in them. "Works with" is a
  factual claim and needs evidence.
- Do not present Baltor as a meta-harness, a multi-agent interface or a
  session manager. Those markets have well-funded and free incumbents.

### 9.4 The ninety-day revenue plan

The [ninety-day plan](../context/NINETY-DAY-PLAN-2026-09-25.md) sets the
arithmetic: at 29 dollars a month, 10,000 dollars of monthly revenue is 345
subscribers and 100,000 dollars is 3,449. This research changes the plan in
four ways. None of them is a forecast.

1. **Channels.** Meta-layer users already run several agents and need the
   same material in each. Omnigent's 32,633 monthly downloads, JetBrains Air's
   launch of September 22 and Harbor's benchmark users are existing audiences
   that one integration page each can reach. Add Omnigent, Zed and JetBrains
   Air to the quickstarts planned for October 3 to October 25 (S-6.202).
2. **Pricing.** Tools that coordinate agents sell per seat: Superset at 20
   dollars (15 yearly) and Conductor Teams at 60 dollars per user a month. The
   planned Team plan should be priced per seat within that band, and its
   selling point for organizations should be the reviewed, licence-checked
   provenance of every item, which is a governance asset alongside GitHub's
   control plane and JetBrains Air Governance.
3. **Proof.** A Harbor comparison across three registry agents with and
   without Baltor is the cheapest route to the first measured benefit. Until
   it exists, public copy stays evaluative.
4. **Focus.** Spend none of the ninety days on orchestration features. Vibe
   Kanban's sunset shows that free users dominate that layer.

## 10. Decisions and reasons

These are engineering decisions recorded by this research. The roadmap
changes they imply are proposed in section 11 for the integrator.

| Decision | Reason |
|---|---|
| Baltor does not build a meta-harness, a session manager or a parallel worktree interface | At least ten products do this; GitHub, JetBrains, Databricks and Anthropic ship their own; Vibe Kanban could not find a business model |
| The first tool-using executor engine stays the Agent Client Protocol client, now registry-driven, with the Claude Code and Codex adapters after OpenCode and Goose | One adapter reaches 41 registered agents, and six other layers already rely on the protocol |
| Omnigent enters first as a host that calls Baltor, and only second as a trial wrapper engine | A second control plane inside the envelope, alpha status and a per-conversation session model; the protocol route gives most of its reach with a thin adapter |
| E02 runs on Harbor with registry agents | The same agents the executor will run, with Harbor's separate verifiers |
| Agent definition bundles become a candidate library file kind | They fit the owner's definition of harness intelligence, and one Omnigent image runs on about fifteen named harnesses |
| Adopt two patterns: `DRIFT` verdicts in the qualification ladder, and the secretless credential proxy in the confinement slot | Both are shipped and documented, and both answer known gaps in Baltor's plan |
| Subscription-signed harnesses get a "reported, not brokered" accounting mode | Customers bring their own model access, including subscriptions, and Baltor's broker cannot relay those calls |

## 11. Proposed roadmap changes

This record edits no roadmap entry. For the integrator:

- **S-6.31**: add registry-driven executor profiles, the Claude Code and Codex
  protocol adapters after Goose, a `DRIFT` verdict, and a "reported, not
  brokered" accounting mode for engines signed in with a subscription.
- **S-6.75**: record Omnigent as a candidate wrapper engine with the gates of
  section 9.1, item 4.
- **S-6.44**: add an Omnigent agent image layout profile, and propose agent
  definition bundles as a harness file kind.
- **S-6.202**: add quickstarts for Omnigent, Zed and JetBrains Air, and a Goose
  extension page.
- **E02** in the [agent stack landscape](AGENT-STACK-LANDSCAPE-2026-09-24.md):
  run on Harbor with `acp:<id>@<version>` agents.
- **`process_confinement` slot**: add the secretless credential proxy as a
  planned engine capability.

## 12. Sources

All read on September 27, 2026. Dates in parentheses are publication or
release dates where the source gives one.

Omnigent:

- [Omnigent repository and README](https://github.com/omnigent-ai/omnigent)
- [Omnigent website](https://omnigent.ai)
- [Introducing Omnigent, Databricks blog](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents) (June 13, 2026)
- [Agent YAML specification](https://github.com/omnigent-ai/omnigent/blob/main/docs/AGENT_YAML_SPEC.md)
- [Agent image specification](https://github.com/omnigent-ai/omnigent/blob/main/omnigent/spec/AGENTSPEC.md)
- [Harness bench design](https://github.com/omnigent-ai/omnigent/blob/main/docs/harness-bench-design.md)
- [Harness plugin interface](https://github.com/omnigent-ai/omnigent/blob/main/designs/harness-plugin-interface.md)
- [Harness registry source](https://github.com/omnigent-ai/omnigent/blob/main/omnigent/harness_plugins.py)
- [Skill discovery source](https://github.com/omnigent-ai/omnigent/blob/main/omnigent/spec/skill_sources.py)
- [Package metadata](https://github.com/omnigent-ai/omnigent/blob/main/pyproject.toml)
- [Omnigent on PyPI](https://pypi.org/project/omnigent/) (0.15.0, September 22, 2026) and [download counts](https://pypistats.org/packages/omnigent)
- [MoonMind](https://github.com/MoonLadderStudios/MoonMind)

The other "omni" projects: the repositories linked in the table of section 4.

Protocols, libraries and wrappers:

- [Agent Client Protocol](https://github.com/agentclientprotocol/agent-client-protocol) (1.9.1, September 18, 2026)
- [Agent Client Protocol registry](https://github.com/agentclientprotocol/registry) and [registry file](https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json)
- [Python library download counts](https://pypistats.org/packages/agent-client-protocol)
- [claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp) and [codex-acp](https://github.com/agentclientprotocol/codex-acp)
- [acpx](https://github.com/openclaw/acpx) and [Toad](https://github.com/batrachianai/toad)
- [Claude Agent SDK for Python](https://github.com/anthropics/claude-agent-sdk-python) (0.2.160)
- [Codex SDK](https://github.com/openai/codex/tree/main/sdk/typescript)
- [OpenCode server](https://opencode.ai/docs/server/)
- [GitHub Copilot SDK](https://github.com/github/copilot-sdk)
- [agentapi](https://github.com/coder/agentapi) and [Coder Agents](https://coder.com/docs/ai-coder/agents)
- [Rivet Sandbox Agent](https://github.com/rivet-dev/sandbox-agent) and [AgentBox SDK](https://github.com/TwillAI/agentbox-sdk)

Platforms and meta-harnesses:

- [OpenHands](https://github.com/OpenHands/OpenHands)
- [Goose](https://github.com/aaif-goose/goose) and [Goose providers over the Agent Client Protocol](https://goose-docs.ai/docs/guides/acp-providers)
- [Introducing JetBrains Air](https://blog.jetbrains.com/blog/2026/09/22/introducing-jetbrains-air/) (September 22, 2026), [Air public preview](https://blog.jetbrains.com/air/2026/03/air-launches-as-public-preview-a-new-wave-of-dev-tooling-built-on-26-years-of-experience/) (March 9, 2026) and [Air product page](https://www.jetbrains.com/air/)
- [Agent HQ announcement](https://github.blog/news-insights/company-news/welcome-home-agents/) (October 28, 2025) and [Claude and Codex on Agent HQ](https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/) (February 4, 2026)
- [Omnara](https://github.com/omnara-ai/omnara), [Omnara pricing](https://www.omnara.com/pricing) and [The Harness Doesn't Matter](https://www.omnara.com/blog/the-harness-doesnt-matter) (September 1, 2026)
- [Claude Managed Agents](https://claude.com/blog/claude-managed-agents) (April 8, 2026)

Workspace applications:

- [Conductor](https://conductor.build), [Conductor pricing](https://www.conductor.build/pricing) and [Conductor Series A](https://www.conductor.build/blog/series-a) (March 30, 2026)
- [Superset](https://github.com/superset-sh/superset) and [Superset pricing](https://superset.sh/pricing)
- [Emdash](https://github.com/generalaction/emdash)
- [Claude Squad](https://github.com/smtg-ai/claude-squad)
- [Vibe Kanban](https://github.com/BloopAI/vibe-kanban) and [its shutdown notice](https://www.vibekanban.com/blog/shutdown) (April 10, 2026)
- [Terragon snapshot](https://github.com/terragon-labs/terragon-oss) (January 16, 2026)
- [Crystal](https://github.com/stravu/crystal) and [Nimbalyst](https://github.com/nimbalyst/nimbalyst)
- [Sculptor](https://github.com/imbue-ai/sculptor), [xum](https://github.com/coder/xum) and [Agent Deck](https://github.com/asheshgoplani/agent-deck)

Evaluation, configuration and models:

- [Harbor](https://github.com/harbor-framework/harbor) and [its registry agent source](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/acp_registry.py) (added June 10, 2026)
- [any-agent](https://github.com/mozilla-ai/any-agent) and [Flue](https://github.com/withastro/flue)
- [ruler](https://github.com/intellectronica/ruler) and [rulesync](https://github.com/dyoshikawa/rulesync)
- [Claude Code Router](https://github.com/musistudio/claude-code-router)
- [ollama launch](https://ollama.com/blog/launch) (January 23, 2026)

Dates and attention on Hacker News came from its public search interface at
`hn.algolia.com`. Baltor facts come from `origin/main` at `923453a4`:
[AGENTS.md](../../AGENTS.md#north-star-and-current-initiatives),
[engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml),
[Engines behind fixed edges](../architecture/ENGINES-BEHIND-FIXED-EDGES.md),
the [roadmap](../roadmap/roadmap.yaml) and the
[ninety-day plan](../context/NINETY-DAY-PLAN-2026-09-25.md).
