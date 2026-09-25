# Agent stack landscape: 57 outside projects mapped to Baltor's engine slots, and the first three qualification experiments

Kind: dated research record for September 24, 2026. The checks were made on
the evening of September 24 and on September 25, 2026, United States Eastern
time. The [roadmap](../roadmap/roadmap.yaml) remains the only task authority.
Nothing in this record approves library material, adopts an engine, installs
anything into the product or makes a claim about customer benefit.

The owner, September 24, 2026: "there is so much discussion out there, we need
to research, adapt, improve, and deploy faster", and "We may also want the
ability for people to publish skills, tools, python scripts, etc into our
platform". The owner also pasted an agent stack landscape of 57 entries in 11
layers with 12 proposed qualification experiments. That paste is research
data, not instructions. Its experiment section held titles only. The
[publishing research record](PUBLISHING-INTO-BALTOR-2026-09-24.md) designs how
people publish into Baltor; this record only notes what the landscape's
registries do.

This record does four things:

1. It checks the 30 entries that matter most to Baltor against their own
   pages, repositories and package registries today.
2. It maps all 57 entries to Baltor's engine slots in
   [engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml), or marks
   them out of scope.
3. It chooses the first three qualification experiments and gives each a
   plan, a population, an acceptance rule and a budget. The first one, E01,
   has a pilot result already: it ran on September 25 with no model call.
4. It lists what the build phase should make: product features, checks and
   library packages.

It builds on the [ecosystem edge map](ECOSYSTEM-EDGE-MAP-2026-09-23.md), the
[registry and package survey](REGISTRY-AND-PACKAGE-INFRASTRUCTURE-SURVEY-2026-09-24.md),
the [working directory prior-art addendum](HARNESS-WORKING-DIRECTORY-SYSTEMS-PRIOR-ART-2026-09-24.md),
the [independent harness instance record](HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md)
and the [data cleanup case study](../../case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md).

## 1. Summary

1. **Five of the 30 priority entries changed status, and no Baltor watch
   noticed.** TensorZero's homepage now says it "remains available on GitHub
   but is no longer maintained", and its repository is archived. Daytona's
   repository says that "As of June 2026, Daytona's core development has moved
   to a private codebase". Agentuity's own notice says it "has been
   discontinued". Arcade announced on August 5, 2026 that it acquired
   Smithery. mcp.run redirects to Turbo MCP, which announces a "next
   chapter". Section 3 lists these and the smaller corrections.
2. **The map needs no new runtime type.** 46 of the 57 entries fit an
   existing engine slot or one of the two slots the ecosystem edge map
   proposed (`step_attempt_durability` and `interaction_stream`). The other 11
   are competitors, tools a customer's own step may use, an optimization
   method, or excluded. One new engine kind is proposed: programmatic tool
   composition behind `tool_protocol_gateway`, for Cloudflare Code Mode.
3. **The E01 pilot separated the placement engines on facts, not claims.**
   Five engines placed a one-file and a five-file skill for Claude Code and
   Codex, offline, in fresh folders with an empty home folder, twice in each of
   two sessions. Only Baltor's own confined writer, Microsoft APM and Sentry
   dotagents kept every byte. Rulesync and OpenPackage rewrote every
   `SKILL.md`; Rulesync also removed Baltor's identity and digest metadata from
   the Codex copy. Baltor's writer dropped the script's executable mode.
   dotagents needed the network to start and wrote 284 files into the home
   folder. Every engine produced the same tree in all four roots. Codex 0.155.1
   and Claude Code 2.1.282 listed every placement, and listed neither
   known-wrong control.
4. **Tessl is the closest competitor.** It combines a registry, governance,
   with-and-without evaluations and an activation view. Its evaluation uses a
   model judge on generated scenarios, three by default. Its headline numbers
   are self-reported. Baltor's measurable difference has to be what E02
   measures: loaded as an observed fact per step, deterministic independent
   scorers, a fresh harness per step and review by other model families.
5. **Composio hands out guidance that cannot be pinned.** Its skills arrive
   inside tool search results, derived from platform usage, with "no opt-out
   today" and "no API for listing or reading skills", and "Sessions read the
   latest published version of each tool." A repeatable evaluation must save
   the search response itself.
6. **Deep Agents' permission rules do not cover every path.** They apply only
   to the built-in file tools; custom tools, protocol server tools and sandbox
   command execution are outside them. When Deep Agents runs a Baltor step,
   Baltor's own process confinement stays the boundary.
7. **The first three experiments are E01, E02 and E03.** E01 (reproducible
   step materialization) is the base for everything else and needs no model.
   E02 (installed versus loaded versus useful) measures the product's core
   claim with the scorer, meter and claim rules the data cleanup study
   already built. E03 (reuse versus repeated model work) measures the second
   core claim on the same population. Section 7 gives each plan.

## 2. How this was checked, and its limits

- **Pages.** 84 addresses were fetched on September 25, 2026 from 08:06:33 to
  08:06:41 UTC, with redirects followed and recorded. 81 answered 200; the Morph
  pricing page answered 429, Smithery's `llms.txt` answered 404 and
  `agentuity.com/docs` answered 404. An earlier attempt of this research line
  fetched 63 pages on the evening of September 24; the facts used here come
  from the September 25 copies.
- **Metadata.** Repository metadata for 48 distinct repositories came from the
  GitHub interface: licence, last push, archived flag and latest release.
  Package metadata for 30 packages came from PyPI and npm. The Agent Client
  Protocol registry file and the Agent Skills client showcase were counted.
- **Runs.** The E01 pilot and a listing probe ran on this workstation with no
  model call (section 7.2).
- **Not done.** No account was created with any vendor. No hosted service
  received data. No model was called. Nothing was bought. No organization was
  contacted.
- **Coverage.** Of the 57 entries, 30 were checked against primary pages (four
  of them also ran in the pilot), 20 against repository or package metadata
  only, and 7 were not rechecked. Each row of the
  [catalogue](../../artifacts/agent-stack-landscape-2026-09-24/catalogue-2026-09-24.json)
  says which.
- **Vendor statements.** A number or a quality claim that a vendor makes about
  its own product is marked self-reported. None was reproduced here.
- **Unknowns stay unknown.** Where a page does not document something, this
  record says it is not documented in the pages read. It does not infer
  absence.

## 3. What changed, and corrections to earlier records

| Entry | Earlier statement | Observed on September 25, 2026 | Effect for Baltor |
|---|---|---|---|
| TensorZero | The owner's input: a model gateway and improvement backend candidate | Homepage: "TensorZero remains available on GitHub but is no longer maintained." Repository archived; last push June 11, 2026; last release 2026.6.0 on June 4 | Excluded from adoption. Its design stays a reference for `model_access` and `model_call_strategy` |
| Daytona | [Ecosystem edge map](ECOSYSTEM-EDGE-MAP-2026-09-23.md): Daytona 0.216.1, Apache-2.0 | The Apache-2.0 licence belongs to the client libraries (now in `daytona/clients`). The platform core moved to a private codebase in June 2026; the last public release, v0.190.0, is AGPL-3.0 | A hosted service with an open client library, not open infrastructure. The edge map row is corrected here |
| Agentuity | The owner's input: conflicting official surfaces, hold | `agentuity.dev` redirects to a notice: "Agentuity has been discontinued. Agentuity and its services are no longer available." `agentuity.com/docs` answers "Page not found" | Excluded |
| Smithery | The owner's input: a discovery and distribution input | "Smithery is now a part of Arcade.dev" (announced August 5, 2026). Its command line repository moved to `arcadeai-labs/smithery-cli` (AGPL-3.0) | Re-ingestion held until its terms under the new owner are read. The September 23 ingestion already refused Smithery-hosted copies |
| mcp.run | The owner's input: redirects to Turbo MCP | Confirmed. Turbo MCP's page: "Stay tuned for Turbo MCP's next chapter" | Held |
| Cloudflare Code Mode | The owner's input: experimental documentation | The reference, updated July 22, 2026, carries no experimental label. The package is `@cloudflare/codemode` 0.5.2 | Treated as a pre-1.0 package |
| OpenPackage | The owner's input: an adapter candidate | Last push May 29, 2026. The README names the platform `claudecode`; version 0.11.3 placed nothing for it and reported "Unknown platform: claudecode" | Not for served bytes (section 7.2) |
| Pi, Harbor | Repository addresses in earlier records | `badlogic/pi-mono` now resolves to `earendil-works/pi`; `laude-institute/harbor` to `harbor-framework/harbor` | Update source addresses in the watch |
| AgentFS | The owner's input: benchmark next | GitHub detects no licence; last push June 3, 2026 | Held |

## 4. The distinctions this record keeps

The owner's input made three distinctions that change the architecture. This
record keeps them and adds the rungs Baltor already measures:

- A fabric is not one product. Enterprise cataloguing and policy, physical
  execution, durable scheduling and task coordination are different problems.
- Code is not one layer. Retrieving source, applying an edit, composing tools
  in code, running an interpreter and reusing a verified function need
  different acceptance checks.
- Installed is not accepted. Baltor keeps each rung a separate fact:

```text
Served material for one step
├── Offered: search returned its reference
├── Fetched: the exact bytes arrived and matched their digest
├── Installed: the bytes sit at the harness's native path (E01)
├── Listed: the harness put its name and description in the model request (E01, E02)
├── Loaded: the full body reached a model request (E02)
├── Used: the step's output follows a rule only the item prescribes (E02)
├── Useful: the independent scorer's result is better than without it (E02)
└── Accepted: an independent check accepted the step's result
```

One capability may have several bindings (a function, a command, a protocol
server tool, an HTTP call, a WebAssembly plugin), as the edge map records. A
logical step, an attempt, a harness session and a physical machine are four
different things.

## 5. The map: 57 entries and their slots

The 11 layers of the owner's input land on Baltor's slots like this:

```text
Outside projects (57 entries)
├── Governance and fabrics (5): tool_protocol_gateway, or none
├── Tools and authorization (4): tool_protocol_gateway, local_credential_source, catalogue_search_policy
├── Code and programmatic tools (6): model_access, typed_decision, model_call_strategy,
│   tool_protocol_gateway, workspace_backend, process_confinement, custom_plugins_port
├── Harnesses and agent systems (6): step_executor, typed_decision
├── Packages and context delivery (7): material_install_layout, library_ingestion_source,
│   catalogue_qualification_resolver, response_evaluator, library_safety_scan
├── Execution and sandboxes (6): process_confinement, workspace_backend, response_evaluator
├── Durable execution (4): step_attempt_durability (proposed by the edge map)
├── Memory and retrieval (5): similarity_candidate_source, or a tool the customer's step uses
├── Browser and research (3): web_research_port
├── Evaluation and optimization (6): response_evaluator, run_history_export, or none
└── Protocols (5): protocol_endpoint, tool_protocol_transport, step_executor,
    material_install_layout, library_format_validation, interaction_stream (proposed)
```

Decision words: an **engine candidate** fits a slot and waits for a concrete
requirement; **trial next** is qualified in E01 now; a **competitive
benchmark** is compared with, not adopted; a **customer-side tool** is
something a customer's own step may call with the customer's own key, served
as a library package and never a Baltor intelligence layer; **hold** waits for
a lifecycle question to be answered; **exclude** is out.

| Entry | Layer | Checked | Baltor engine slot | Decision |
|---|---|---|---|---|
| L01 MuleSoft Agent Fabric | Governance and fabrics | Not rechecked | None | Reference only |
| L02 Amazon Bedrock AgentCore | Governance and fabrics | Not rechecked | None | Competitive benchmark |
| L03 agentgateway | Governance and fabrics | Metadata only | `tool_protocol_gateway` | Engine candidate, later |
| L04 Turbo MCP (mcp.run) | Governance and fabrics | Primary pages | `tool_protocol_gateway` | Hold |
| L05 Agentuity | Governance and fabrics | Primary pages | None | Exclude |
| L06 Composio | Tools and authorization | Primary pages | `tool_protocol_gateway`, `catalogue_search_policy` | Competitive benchmark |
| L07 Nango | Tools and authorization | Metadata only | `local_credential_source`, `tool_protocol_gateway` | Customer-side connection, later |
| L08 Pipedream Connect | Tools and authorization | Metadata only | `local_credential_source`, `tool_protocol_gateway` | Customer-side connection, later |
| L09 Arcade | Tools and authorization | Metadata only | `tool_protocol_gateway` | Engine candidate, later |
| L10 Relace | Code and programmatic tools | Primary pages | `model_access` | Benchmark in E04 |
| L11 Morph | Code and programmatic tools | Primary pages | `typed_decision`, `model_call_strategy`, `model_access` | Benchmark in E04 |
| L12 Cloudflare Code Mode | Code and programmatic tools | Primary pages | `tool_protocol_gateway` | Engine candidate, later |
| L13 Riza | Code and programmatic tools | Not rechecked | `workspace_backend`, `process_confinement` | Engine candidate, later |
| L14 AgentFS (Turso) | Code and programmatic tools | Metadata only | `workspace_backend` | Hold |
| L15 Extism | Code and programmatic tools | Metadata only | `custom_plugins_port` | Watch |
| L16 Pi | Harnesses and agent systems | Metadata only | `step_executor` | In use |
| L17 Deep Agents (LangChain) | Harnesses and agent systems | Primary pages | `step_executor` | Competitive benchmark |
| L18 Mastra | Harnesses and agent systems | Metadata only | `step_executor` | Reference only |
| L19 Agno (AgentOS) | Harnesses and agent systems | Metadata only | `step_executor` | Reference only |
| L20 Pydantic AI | Harnesses and agent systems | Metadata only | `step_executor`, `typed_decision` | Engine candidate, later |
| L21 Letta | Harnesses and agent systems | Metadata only | `step_executor` | Competitive benchmark |
| L22 Tessl | Packages and context delivery | Primary pages | `catalogue_qualification_resolver`, `response_evaluator`, `library_safety_scan` | Competitive benchmark |
| L23 Microsoft APM | Packages and context delivery | Primary pages and pilot run | `material_install_layout` | Trial next (E01) |
| L24 Sentry dotagents | Packages and context delivery | Primary pages and pilot run | `material_install_layout` | Candidate with conditions |
| L25 Rulesync | Packages and context delivery | Primary pages and pilot run | None | Not for served bytes |
| L26 OpenPackage | Packages and context delivery | Primary pages and pilot run | None | Not for served bytes |
| L27 Docker MCP Catalog and Toolkit | Packages and context delivery | Primary pages | `library_ingestion_source`, `tool_protocol_gateway` | Engine candidate, later |
| L28 Smithery | Packages and context delivery | Primary pages | `library_ingestion_source` | Hold |
| L29 E2B | Execution and sandboxes | Primary pages | `process_confinement`, `workspace_backend` | Engine candidate, later |
| L30 Daytona | Execution and sandboxes | Primary pages | `process_confinement`, `workspace_backend` | Engine candidate, later |
| L31 Blaxel | Execution and sandboxes | Metadata only | `process_confinement`, `workspace_backend` | Engine candidate, later |
| L32 Runloop | Execution and sandboxes | Primary pages | `process_confinement`, `workspace_backend`, `response_evaluator` | Engine candidate, later |
| L33 Deno Sandbox | Execution and sandboxes | Not rechecked | `process_confinement` | Engine candidate, later |
| L34 Modal Sandboxes | Execution and sandboxes | Metadata only | `process_confinement` | Engine candidate, later |
| L35 DBOS | Durable execution | Primary pages | `step_attempt_durability` (proposed) | First candidate |
| L36 Restate | Durable execution | Primary pages | `step_attempt_durability` (proposed) | Engine candidate, later |
| L37 Inngest | Durable execution | Metadata only | `step_attempt_durability` (proposed) | Engine candidate, later |
| L38 Trigger.dev | Durable execution | Metadata only | `step_attempt_durability` (proposed) | Engine candidate, later |
| L39 Mem0 | Memory and retrieval | Primary pages | None | Customer-side tool |
| L40 Zep and Graphiti | Memory and retrieval | Primary pages | `similarity_candidate_source` | Reference only |
| L41 Hindsight (Vectorize) | Memory and retrieval | Metadata only | None | Customer-side tool |
| L42 Cognee | Memory and retrieval | Metadata only | None | Customer-side tool |
| L43 Supermemory | Memory and retrieval | Metadata only | None | Customer-side tool |
| L44 Browserbase | Browser and research | Not rechecked | `web_research_port` | Engine candidate, later |
| L45 Stagehand | Browser and research | Metadata only | `web_research_port` | Engine candidate, later |
| L46 Parallel Web Systems | Browser and research | Not rechecked | `web_research_port` | Engine candidate, later |
| L47 GEPA | Evaluation and optimization | Primary pages | None | Method for E09 |
| L48 Harbor | Evaluation and optimization | Primary pages | `response_evaluator`, `run_history_export` | Measurement backend |
| L49 Inspect | Evaluation and optimization | Primary pages | `response_evaluator` | Measurement backend |
| L50 Braintrust | Evaluation and optimization | Not rechecked | `run_history_export` | Engine candidate, later |
| L51 LangWatch | Evaluation and optimization | Metadata only | `run_history_export` | Engine candidate, later |
| L52 TensorZero | Evaluation and optimization | Primary pages | None | Exclude |
| L53 Model Context Protocol | Protocols | Primary pages | `protocol_endpoint`, `tool_protocol_transport` | Compatibility contract, in use |
| L54 Agent Client Protocol | Protocols | Primary pages | `step_executor` | Compatibility contract |
| L55 Agent2Agent | Protocols | Primary pages | `step_executor` | Compatibility contract |
| L56 AG-UI | Protocols | Primary pages | `interaction_stream` (proposed) | Watch |
| L57 Agent Skills | Protocols | Primary pages | `material_install_layout`, `library_format_validation` | Compatibility contract, in use |

The [catalogue](../../artifacts/agent-stack-landscape-2026-09-24/catalogue-2026-09-24.json)
holds, for every row, what was observed, the question that must be answered
before adoption and the source addresses.

## 6. The 30 priority entries, checked

Each row states what the entry's own pages or repository say today, then what
it means for Baltor. Quotations are from those pages. "Self-reported" marks a
vendor's claim about its own product.

### 6.1 Packages, context delivery and the closest competitors

| Entry | What its primary sources say today | For Baltor |
|---|---|---|
| Tessl | Six components: registry and package manager; governance with Snyk security scoring and role-based access; evaluations "with and without the context"; a view of "where skills actually activate across agent sessions"; context and findings across repositories; the Tessl Agent, in open beta. An evaluation runs each scenario twice and a judge scores a per-scenario rubric; scenario generation targets 3 by default. Publishing is private by default and runs lint and review automatically; a minimum review score policy blocks a version skill by skill, with no averaging; making a plugin public needs approval and cannot be undone. Free at 0 dollars, Team at 100 dollars a month, Enterprise; "Publishing and installing plugins is always free". Self-reported: "74% of findings are real defects" and "94% task success, up from 67%, Fastify". The mechanism behind activation is not documented in the pages read. | The direct benchmark. Its publish flow (private first, review on publish, a per-item score gate, irreversible public listing) is a design input for the Community tier and for the owner's wish that people publish into Baltor, which the [publishing research record](PUBLISHING-INTO-BALTOR-2026-09-24.md) designs |
| Microsoft APM | 0.31.0 (MIT, September 15). One `apm.yml`; the lockfile "pins exact versions and content hashes so a fresh clone resolves the same package content byte-for-byte"; every install scans for hidden Unicode and blocks transitive protocol servers unless they are declared or trusted; `apm-policy.yml` applies at install. Targets include Claude Code, Codex, OpenCode, Cursor, GitHub Copilot, Gemini, Windsurf, Kiro and Grok Build | The first upstream engine to qualify behind `material_install_layout` (E01) |
| Sentry dotagents | 3.1.0 (MIT). The quick start is titled "Global by Default"; `--project` selects project scope. A trust policy restricts sources before any network operation | A candidate only with conditions (E01) |
| Rulesync | 18.0.0 (MIT, September 24). A supported mark means the feature works "in at least one mode (project, global, or simulated)". It imports and converts configuration between tools | Rewrites served bytes (E01). Useful as a reference for importing a customer's existing configuration |
| OpenPackage | 0.11.3 (Apache-2.0, May 11); last push May 29 | Rewrites served bytes (E01) |
| Docker MCP Catalog and Toolkit | "300+ verified servers" (self-reported) as container images with versioning, provenance and bill of materials metadata; custom catalogs; profiles; a gateway; Dynamic MCP, where `mcp-find` searches only the configured catalog. "MCP Gateway as part of Docker AI Governance is an invite-only feature." | An ingestion source for protocol server packages and a customer-side gateway, later |
| Smithery | Now part of Arcade (section 3). It lists protocol servers and skills with usage counts and accepts publishing | Held |
| Agent Skills | Required `name` (up to 64 characters of lowercase letters, numbers and hyphens) and `description` (up to 1,024); optional `license`, `compatibility` (up to 500), `metadata` (a string to string map) and `allowed-tools` (experimental). The client showcase listed 46 clients on September 25 | Baltor keeps its identity and body digest in `metadata`, which the specification allows. E01 showed one engine removes it |

### 6.2 Tools, code and protocols

| Entry | What its primary sources say today | For Baltor |
|---|---|---|
| Composio | A session scopes the user, tool access ("all toolkits by default"), authentication and execution state, and includes a remote sandbox that is "not billed today". Skills are derived "from real usage across the platform", arrive inside `COMPOSIO_SEARCH_TOOLS` results with plan steps and pitfalls, and have "no opt-out today" and "no API for listing or reading skills". "Sessions read the latest published version of each tool." Tools carry read-only, create, update and destructive tags | A benchmark for guidance attached to search results. A replay must save the full response in Run History. Its four effect tags map onto Baltor's effect classes |
| Relace | Trace compaction (">50k tok/s", self-reported), instant apply (">10k tok/s", self-reported), a code reranker, fast agentic search run one turn at a time with the caller supplying the harness (also as a protocol server), hosted open-weight models, repositories with scoped tokens, sandboxes | Customer-side tools and a model route; compared in E04 |
| Morph | Fast Apply ("10,500 tok/s, 98% accuracy", self-reported); Compact, where "every surviving line is byte-for-byte identical to the original" and the response lists the removed line ranges; WarpGrep code search (about 6 seconds per query, self-reported); classifiers; a model router at 0.005 dollars per request; hosted open-weight models | Compact's deletion-only output with removed ranges is the auditable shape to require of any context reduction. The router classify call fits `typed_decision` |
| Cloudflare Code Mode | A runtime can execute, search, describe, approve, reject and roll back. Execution records carry the states running, paused, completed, error, rejected and rolled_back. A connector method can require approval; the run pauses and resumes by replay; "It does not roll back earlier actions" when one action is rejected; rollback calls revert functions in reverse order. `globalOutbound` null "blocks access"; the default timeout is 60,000 milliseconds | Approval per connector method matches Baltor's rule that an approval binds one exact effect. Rollback is only as good as each revert function |
| Deep Agents | 0.7.19 (MIT). Permissions cover the built-in file tools only: "Custom tools and MCP tools that access the filesystem are not covered", nor are sandbox backends that run commands. The first matching rule wins and no match allows the call. Subagents inherit the parent's rules unless their own rules replace them entirely. Skills follow the Agent Skills specification with progressive disclosure. Served over the Agent Client Protocol by `deepagents-acp` | An executor only inside Baltor's confinement. Its progressive disclosure is why listed and loaded are separate rungs |
| Model Context Protocol | Revision 2026-07-28 is stateless: no initialize handshake, the version and client capabilities travel on every request, protocol-level sessions are removed, servers must answer `server/discover`, and tasks moved into an official extension | Already negotiated beside 2025-11-25 (roadmap step S-6.43) |
| Agent Client Protocol | Version 1 defines stdio; Streamable HTTP is a "draft proposal in progress". A version 2 tracking proposal lists remote transports, a new prompt lifecycle and permission requests among its breaking changes. The public registry listed 41 agents on September 25, including adapters for Claude Code, Codex, OpenCode, Pi, Goose, Gemini CLI and Deep Agents | The registry is a ready inventory of `agent_protocol_harness` candidates for `step_executor` |
| Agent2Agent | "communication and interoperability between opaque agentic applications"; agents interact "without needing to share internal memory, tools, or proprietary logic". Specification v1.0.1 (May 28, 2026) | External delegation only (`remote_agent` kind), never the Loop graph. A remote completion state is not acceptance |
| AG-UI | An "open, lightweight, event-based protocol" between agents and user-facing applications, distinct from the A2UI generative interface specification. Python package 1.0.0 (September 17) | Watched for the proposed `interaction_stream` slot |

### 6.3 Execution, durability, memory and evaluation

| Entry | What its primary sources say today | For Baltor |
|---|---|---|
| E2B | Sandboxes pause with memory, resume, snapshot and fork; templates carry tags and versions. "Every sandbox has outbound internet access by default", with an off switch and allow and deny lists. Secrets are injected into outbound HTTPS requests outside the sandbox. Hobby: 100 dollars of one-time credit, sessions up to 1 hour; Pro: 150 dollars a month, sessions up to 24 hours | A remote kind for `process_confinement`. The open default network must be closed by Baltor's policy |
| Daytona | A hosted service since June 2026 (section 3). Billing per second; 200 dollars of free compute; sandboxes stop, archive and delete themselves on timers; "sub 90ms" creation (self-reported) | A remote kind, hosted only |
| Runloop | Devboxes, blueprints, snapshots, an event stream, a broker that speaks the Agent Client Protocol, a model gateway that proxies calls "without exposing credentials to agents", benchmarks with custom scorers and egress policies | Its credential-hiding gateway is the pattern roadmap step S-6.61 chose for the broker |
| DBOS | 3.1.0 (MIT, September 24). Durable workflows "built on top of Postgres"; a page on converging concurrent executions on one recorded outcome. The September 23 trial: an interrupted step ran again and charged twice until an idempotency key and a ledger check were added | First candidate for the proposed `step_attempt_durability` slot, as the edge map decided |
| Restate | The server is under the Business Source License 1.1; its grant forbids offering a "Public Restate Platform Service" to third parties | Internal use only, if ever adopted |
| Mem0 | A managed platform and a self-hosted library; memories filtered by `user_id`, with an optional `run_id` for session recall; deletion one by one or for a whole user; Hobby 1,000 retrieval requests a month, Starter 19 dollars, Pro 249 dollars | A tool a customer's step may use. Baltor's Runtime Memory stays per run and its persistent layers stay reviewed |
| Zep and Graphiti | Zep: "the unified context layer for enterprise data", on its own graph database service. Graphiti (Apache-2.0): temporal validity windows on facts and the ingested episodes kept as provenance | A reference for facts that expire |
| GEPA | Optimizes any text parameter by model reflection and Pareto-efficient search against a metric, with training and validation sets and a `max_metric_calls` budget; `optimize_anything` takes any text artifact. 0.1.4 (MIT) | A method for the self-improvement Practitioner task in E09, staging candidates for independent review. The judge must stay outside its reach |
| Harbor | "Harbor is a framework for running any agent with any model on any task in any sandbox in parallel." Separate verifiers, datasets, trajectories in the Agent Trajectory Interchange Format, and the official harness for Terminal-Bench 2.0. 0.23.0 (Apache-2.0) | Measurement backend for with-and-without runs, as the edge map decided |
| Inspect | The agent bridge routes the model calls of Claude Code, Codex CLI and Gemini CLI through the current Inspect model provider. 0.3.268 (MIT) | Measurement backend. The bridge counts every call a harness makes |
| TensorZero | No longer maintained (section 3) | Excluded |
| Agentuity, Turbo MCP | Discontinued, and announcing a next chapter (section 3) | Excluded, held |

## 7. Qualification experiments

### 7.1 The twelve, and why three go first

The owner's input named twelve experiments and said to choose the smallest
that resolves a real gap and not to start all twelve. The order below follows
dependency: an experiment that needs another's apparatus waits for it.

| Order | Experiment | Question | Why this position |
|---|---|---|---|
| 1 | E01 Reproducible step materialization | Does every engine place the exact package, with its modes and identity, in every harness, every time, without touching anything else? | Every later experiment measures a working directory. Needs no model |
| 2 | E02 Installed versus loaded versus useful | How often is a served skill listed, loaded, used and useful, and at what cost? | The product's core claim. Reuses the data cleanup scorer, meter and claim rules |
| 3 | E03 Reuse versus repeated model work | Does handing over verified code beat having the model rewrite it? | The second core claim (paying to rewrite code that exists). Reuses E02's apparatus |
| 4 | E07 Fine-grained steps versus physical overhead | What does a fresh harness per step cost in time and tokens, against what it saves? | Tests the default design of one harness per step; needs E01 and E02 |
| 5 | E12 Provider lifecycle and exit drill | Can each adopted engine be replaced when its provider changes? | Five status changes in section 3. The watch is built first (section 8); the drill follows |
| 6 | E06 Durability without duplicate effects | Does a resumed attempt avoid repeating an external effect? | The September 23 DBOS trial answered part of it |
| 7 | E09 Optimization with independent promotion | Does an optimized item hold on held-out tasks with the judge out of reach? | Needs E02's measurement |
| 8 | E04 Specialized search and patch engines | Do apply and search engines keep unrelated code and pass held-out tests? | Matters for code tasks; needs customer keys and a code population |
| 9 | E05 Tool backend and guidance attribution | Which part of a tool backend's result came from its own guidance? | Needs a replayable capture of search responses |
| 10 | E10 Tool policy and tenant isolation | Do two tenants' tools, approvals and effects stay separate? | Follows roadmap step S-6.61 |
| 11 | E08 Memory accuracy, scope and deletion | Can a memory be traced, corrected and deleted? | No memory engine is planned inside Baltor |
| 12 | E11 Creative workflow environment portability | Do rendering steps reproduce across environments? | Follows the media work in roadmap step S-6.116 |

### 7.2 E01: reproducible step materialization

**Question.** Does a placement engine put the exact package bytes, the
declared file modes and Baltor's identity metadata at each harness's native
path, the same way on every run, without writing anywhere else and without the
network, so that the harness lists the item?

**Pilot, September 25, 2026 (no model call).** Two packages, frozen before the
run: P1 is one `SKILL.md` for `find-duplicate-records-with-blocking-keys`
with Baltor's identity and body digest in `metadata`; P2 is a five-file skill
for `split-address-lines-into-components` with an executable script (mode
0755), a reference file, a CSV file with Windows line endings and non-ASCII
text, and a 256-byte binary file. Each engine placed each package for Claude
Code (`.claude/skills/<name>/`) and Codex (`.agents/skills/<name>/`) in a fresh
git project with an empty home folder, the package at a different absolute
path each time, and every outbound connection sent to a closed local port.
Each cell ran twice, in two separate sessions: four roots in all. The second
session ran the committed scripts.

| Engine and version | Offline | Files identical to the package (P1, P2) | Script mode 0755 kept | Identity metadata kept (Claude Code, Codex) | Files added to the project | Files written in the home folder | Same tree in all four roots |
|---|---|---|---|---|---|---|---|
| Baltor confined writer (`tools/install_selected_material.py`) | Yes | 2 of 2, 10 of 10 | No: 0644 | Yes, yes | None | 0 | Yes |
| Microsoft APM 0.31.0 | Yes | 2 of 2, 10 of 10 | Yes | Yes, yes | `apm.yml`, `apm.lock.yaml` (with the absolute source path), an `apm_modules` copy, `.gitignore` | 3 | Yes |
| Sentry dotagents 3.1.0 | No: `init` clones `github.com/getsentry/dotagents` for its own default skill and exits 1 offline; `add` and `install` of the local package then work offline | 2 of 2, 10 of 10 | Yes | Yes, yes | `agents.toml`, `agents.lock`, two `.gitignore` files, and `.claude/skills` made a link to `../.agents/skills` | 284 | Yes |
| Rulesync 18.0.0 | Yes | 0 of 2, 8 of 10: every `SKILL.md` rewritten, the description folded onto new lines | Yes | Yes, no: the Codex copy lost the whole `metadata` map | None beyond its own source copy | 0 | Yes |
| OpenPackage 0.11.3 | Yes | 0 of 2, 8 of 10: a blank line inserted after every `SKILL.md` header | Yes | Yes, yes | Three files under `.openpackage/` | 1 | Yes |

The Baltor row is the pilot's own loop around the repository's confined
writer: the shipped tool serves one body at a time and does not walk a package
folder yet.

**Listed rung, same day, no model call.** For each engine's first run of each
package, a copy of the project went to two harnesses. Codex 0.155.1 rendered
its model-visible input with `codex debug prompt-input`. Claude Code 2.1.282
sent its first request to a capture server on 127.0.0.1 that saves the request
and answers HTTP 400, with the key set to the literal `not-a-real-key`. All 20
placements were listed by name and description: in Codex's skills section and
in Claude Code's list of skills "available for use with the Skill tool". Claude
Code's debug log read "Loaded 1 unique skills (... project: 1 ...)" each time,
including through dotagents' link. Two known-wrong controls, an empty project
and the same skill under `.skills/`, were listed by neither harness, and Claude
Code's log read "Loaded 0 unique skills". So the listing check can fail.

**Two more observations.**

1. Baltor's confined writer refused to place into a project where dotagents had
   made `.claude/skills` a link, with the refusal `symbolic_link_refused`. The
   refusal is correct, since the writer never follows a link. It is also an
   interoperability gap: the compiler needs a typed state for a link between
   two native roots inside one project.
2. Rulesync's rewritten files were still listed. A change of bytes does not
   stop discovery, which is exactly why a digest check at the placement edge
   has to catch it.

**Full run plan.**

- **Population, frozen before the run:** P1 and P2 as above; P3, a skill with
  a protocol server configuration for a local stub server and an instruction
  file, to test whether an engine adds, enables or widens a server; P4, a
  known-wrong package with a name that tries to leave the project and a link
  inside the package that points outside it.
- **Engines:** the Baltor writer with declared modes and package walking
  (build item F1), Microsoft APM 0.31.0 wrapped as an engine (F3), dotagents
  3.1.0 with a prepared `agents.toml` and no `init`, madebywild agent-harness
  2.1.0 (the September 23 candidate), and Rulesync and OpenPackage as negative
  references.
- **Harnesses for the listed rung:** Codex, Claude Code, OpenCode (its
  `debug skill --pure` listing) and Pi (the capture method of September 22).
- **Runs:** two fresh roots per session, two sessions, offline.
- **Acceptance rule:** an engine is eligible behind `material_install_layout`
  for a package kind only if, for every package and target, every file is
  byte-identical, every declared mode is kept, the identity metadata is kept,
  the normalized tree is identical in all four roots, nothing is written
  outside the project and the step's own home folder, a local package needs no
  network, every harness lists the item, and P4 is refused or contained with
  no file outside the project. One failure excludes the engine for that kind,
  recorded with the tested version.
- **Budget:** no model call, no spending, about 30 minutes of machine time;
  network only to install the pinned tool versions.

### 7.3 E02: installed versus loaded versus useful

**Question.** When an approved item is placed as a native skill instead of
being forced into the instruction file, how often is it listed, loaded and
used, does it change the independently scored result, and what does it cost?

**Why it is needed.** The September 22 data cleanup run put each item into
`AGENTS.md`, so loading was never the model's choice. There the cheap model
was clearly worse with the phone item (0.842 against 0.991 without it) and
spent 45 to 446 percent more prompt tokens per step. Native skills load by
progressive disclosure: the name and description are always sent, the body
only when the model asks for it. Whether that keeps the benefit and removes
the cost is not known.

**Plan.**

- **Population:** the frozen data cleanup population (143 synthetic rows in
  four families) and its scorer `score_step.py`, unchanged, with the five
  approved items of its design by digest.
- **Arms:** none; native skill (placed by an engine that passed E01, nothing in
  `AGENTS.md`); forced (the item bytes in `AGENTS.md`, as on September 22);
  native skill with the three other families' items placed beside it, to test
  selection among four listed skills.
- **Harnesses:** Pi 0.73.1 and OpenCode 1.18.32 behind the counting proxy
  (`runner/meter.py`). Codex joins in a second wave once its route through the
  proxy is qualified.
- **Models:** `glm-5.3-flash:cloud` on Ollama Cloud, which drove Pi's tools in
  12 of 12 steps on September 22; then `gemma-4-coding-abliterated` on the
  owner's Tactical server, only if one no-material step per harness produces an
  output file in a pre-check.
- **Rungs, each fixed before the run:** listed when the item's name and
  description appear in the first recorded request; loaded when a
  pre-declared sentinel line from the item body appears in any recorded
  request; used when the output follows a pre-declared per-item fingerprint
  (the rows where the item's rule and the September 22 no-material behavior
  differ); useful from the scorer's primary metric; cost as requests, prompt,
  cached and output tokens and seconds per step, with unknown usage kept
  unknown.
- **Repetitions:** three per cell, in rounds shuffled by a fixed seed.

**Acceptance rules, registered before any counted call.**

1. A harness passes the listed rung when listed is true in every native-skill
   step and false in every no-material step.
2. "The model loads served skills in this harness" needs loaded in at least 2
   of 3 repetitions in at least 3 of the 4 families.
3. "Native placement helps item I" needs the native arm to be clearly better
   than no material on I's family under the September 22 claim rule: every
   repetition of one arm above every repetition of the other.
4. "Native placement costs less than forcing" needs every native-skill
   repetition's prompt tokens per step below every forced repetition's, with
   the native arm not clearly worse on the primary metric.
5. Controls fail first: a skill at a wrong root must show listed false, an
   item with a mismatched digest must be refused before the step starts, and
   the scorer's known-wrong outputs must fail its existing tests.

**Known limit.** Without material the cheap model already scored 0.948 to
1.000 per family. Usefulness may not separate on this population. If it does
not, the record says so and the Tactical model and a harder population become
the next run.

**Budget.** 4 families by 4 arms by 3 repetitions by 2 harnesses is 96 steps
per model. The September 22 cheap-model arms used 3.7 to 6.7 requests per
step, so about 500 requests are expected. Ceiling: 800 physical requests on
Ollama Cloud through the proxy, a step cap of 8, one allowance probe request
first, and an eight-step pilot (the addresses family, every arm, both
harnesses) excluded from results. The Tactical route has its own ceiling of
800. No spending beyond the existing Ollama subscription. The run stops on a
spent allowance and resumes after the reset. E02 covers the no-skill arm of
roadmap step S-6.47; the raw-source arm stays there.

### 7.4 E03: reuse versus repeated model work

**Question.** When verified code for a step already exists, does handing it to
the step beat having the model write the same logic, on accepted results,
tokens, time and new code, and does the step need a model at all?

**Plan.**

- **Reusable code (a build item, F5):** four packages, one per data cleanup
  family, each with a typed command line contract (input CSV to output CSV in
  the scorer's columns), its own tests, held-out tests written by a different
  model family, a licence record and digests. Phones wrap `phonenumbers` 9.0.40
  (Apache-2.0), maintained code for exactly the trunk and exit prefixes the
  September 22 phone item got wrong. Emails wrap `email-validator` 2.3.0
  (Unlicense) with the approved item's domain typo map. Addresses use a
  rule-based splitter. Duplicates use blocking keys with `rapidfuzz` 3.14.6
  (MIT). Each stays a candidate until the review panel approves it.
- **Populations:** the frozen 143-row population, and a held-out population
  from the same generator with a new seed, disclosed and frozen before any
  call. Both are scored by the same scorer.
- **Arms:** repeat (the model writes the transformation, no material); skill
  text only (the approved item as a native skill); reuse (the code package
  placed with a skill that says how to run it); deterministic (a Solution
  Loop runs the package directly, with no model).
- **Harness and models:** Pi 0.73.1 behind the counting proxy, with the E02
  models.
- **Measures:** the primary metric on both populations, requests, tokens,
  seconds, lines of new code the model wrote in the step folder, and whether
  the package actually ran (from the harness's event stream).

**Acceptance rules.**

1. The deterministic arm runs first, with no model call. A package that fails
   its family's threshold on the frozen population is repaired and requalified
   before any model call, and the repair is recorded.
2. "Reuse beats repetition for family F" needs the reuse arm clearly better
   than the repeat arm on the held-out population, or not separated on the
   metric with every reuse repetition using fewer prompt tokens than every
   repeat repetition.
3. "The step needs no model for family F" needs the deterministic arm to pass
   F's threshold on both populations.
4. A reuse step whose package never ran counts as not reused. Every claim names
   the model, harness, population and scorer, and no claim is made beyond
   them.

**Budget.** The deterministic arm makes no model call. The model arms are 4
families by 3 arms by 3 repetitions by 2 models, 72 steps, with a ceiling of
600 physical requests per route, a step cap of 8 and a three-step pilot. No
spending beyond the existing subscription. Roadmap step S-6.114 applies the
same protocol to the owner's 24 tools.

## 8. What the build phase should make

### 8.1 Product features

| Item | What it does | Owner |
|---|---|---|
| F1 Package placement in the native engine | Walk a package manifest, write each file through the confined writer, keep each declared mode (0644 or 0755, taken from the manifest, never from the source file system), record every file's digest and mode | `material_install_layout`, `tools/install_selected_material.py` |
| F2 A typed state for linked native roots | Detect an in-project link such as `.claude/skills` to `../.agents/skills`, report both paths as one shared root, place once through the real folder, and refuse any link that leaves the project | `material_install_layout` |
| F3 Microsoft APM as the first upstream placement engine | A pinned wrapper (apm-cli 0.31.0) with the step's own home folder, targets from the layout profile, and the lockfile kept as evidence with its absolute source path normalized; eligible only after the E01 rule passes | `material_install_layout`, roadmap step S-6.75 |
| F4 The E02 runner | Native-skill arms, the OpenCode recipe behind the counting proxy, and extractors for listed, loaded and used from recorded request bodies | `case-studies/data-cleanup-with-and-without-baltor/runner` |
| F5 The E03 code packages and deterministic runner | Four data-work code packages with typed contracts and held-out tests, and a Solution run of a package with no model | Roadmap step S-6.54 |
| F6 The provider lifecycle watch | Extend `tools/research_source_watch.json` (17 sources today) and `tools/refresh_research_sources.py` with lifecycle fields for every engine candidate: archived flag, licence, last push, latest release, redirects and notice text; a fired signal holds the candidate | `tools/refresh_research_sources.py` |
| F7 The Agent Client Protocol registry as executor inventory | Read the registry file into candidate `agent_protocol_harness` profiles, each unqualified until the qualification ladder of roadmap step S-6.31 passes | `step_executor` |

### 8.2 Checks

Each check needs its known-wrong fixture and a removed-guard control, as the
working cycle requires. The E01 pilot outputs are the first fixtures.

| Check | Known-wrong case that must fail it |
|---|---|
| `placement_keeps_every_package_byte_and_declared_mode` | The Rulesync and OpenPackage `SKILL.md` outputs; a script placed with mode 0644 |
| `placement_keeps_served_identity_metadata` | The Rulesync Codex output without `metadata` |
| `placement_writes_nothing_outside_the_project_and_step_home` | An engine that writes into a second home folder |
| `placement_is_identical_across_roots_after_path_normalization` | A lockfile that differs by more than the root path |
| `a_linked_native_root_is_reported_and_never_followed_out_of_the_project` | A link from `.claude/skills` to a folder outside the project |
| `listed_needs_the_item_name_and_description_in_the_captured_request` | The empty-project and wrong-root controls |
| `an_archived_or_discontinued_provider_holds_its_engine_candidate` | TensorZero's archived flag ignored |

### 8.3 Library packages

Original writing from this record's checked facts, never copied from vendor
text. Each is a candidate for the independent review panel and carries its
sources with their fetch dates.

| Package | What a harness step gets |
|---|---|
| Check a model-merged edit before accepting it | Compare the edit's scope with the request, confirm unrelated code is unchanged, run the tests, refuse an edit with omitted sections (from the Relace and Morph question) |
| Make an interrupted step safe to retry | A stable effect key and a ledger check before any repeat of an external effect (from the September 23 DBOS trial) |
| Choose where untrusted code runs | Questions about network default, secret handling, session limit, pause and resume, and billing, with the dated facts of section 6.3 |
| Write a with-and-without evaluation for one skill | A deterministic scorer, a known-wrong control, a claim rule fixed before the run, and separate listed, loaded and used facts |
| Pin and verify an agent package install | Lockfile digests, an offline install, a separate home folder and a post-install digest check, for teams that use Microsoft APM |

## 9. Decisions and reasons

| Decision | Reason |
|---|---|
| Qualify Microsoft APM first behind `material_install_layout` | The only upstream engine in the pilot that kept every byte and mode, worked offline and wrote nothing but its own manifest, lockfile, module copy and three home-folder files |
| Keep Baltor's confined writer as the default placement engine, and add declared modes and package walking | It kept every byte, wrote nothing else, needed no network and never follows a link; its one gap is file modes |
| Do not use Rulesync or OpenPackage for served bytes | Both rewrote every `SKILL.md`; Rulesync removed the identity metadata for Codex |
| Admit dotagents only with a prepared `agents.toml`, the step's own home folder and the linked-root state | Its `init` fetches unselected material over the network into the home folder, and its link blocks Baltor's writer |
| Exclude TensorZero and Agentuity; hold Smithery, Turbo MCP and AgentFS | Their own pages or repositories show discontinuation, no maintenance, an ownership change, an announced change or no licence |
| Treat Daytona as a hosted service only | Its core moved to a private codebase; only the client libraries are open |
| Run a Deep Agents step only inside Baltor's confinement | Its own rules do not cover custom tools, protocol server tools or command execution |
| Record Composio search responses in full when a step uses it | Its guidance cannot be listed or pinned, and sessions read the latest tool versions |
| Run E01, then E02, then E03 | Each later experiment needs the earlier one's working directory or measurement apparatus |
| Build the lifecycle watch before the E12 drill | Five status changes went unnoticed; a watch is cheap and needs no model |

## 10. Evidence states

- **Ran here:** the E01 pilot in two sessions, the listing probe and its two
  controls, on September 25, 2026, with no model call.
- **Verified from primary sources:** the 30 priority entries, on the pages and
  repositories listed in the source register, September 25, 2026.
- **Metadata only:** 20 entries (licence, last push, archived flag, release).
- **Carried, not rechecked:** 7 entries, as the owner's input described them.
- **Self-reported:** vendor numbers and quality claims, marked where quoted.
- **Unknown:** how Tessl observes activation; whether any listed harness loads
  or uses a served skill body (E02); every price or limit not quoted above.
- **Disputed:** none open. Two earlier statements are corrected in section 3.

## 11. Files

All under
[artifacts/agent-stack-landscape-2026-09-24](../../artifacts/agent-stack-landscape-2026-09-24/README.md):

- `catalogue-2026-09-24.json`: the 57 entries with check state, slots,
  decision, observations, the question before adoption and sources.
- `source-register-2026-09-25.json`: every fetched address with status, final
  address, byte count and digest; repository and package metadata; the Agent
  Client Protocol registry count; the Agent Skills client list.
- `e01/`: the pilot, placement and listing scripts, and their results with
  local paths replaced by placeholders.
