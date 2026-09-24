# Toolsmith, Router and Coach patterns for tool-calling agents, mapped onto Baltor

Kind: dated research record, September 24, 2026. It reports what was read
and what each source shows. It implements nothing, approves no material and
qualifies no engine. The [roadmap](../roadmap/roadmap.yaml) remains the task
authority. The proposals in this record entered the roadmap as steps S-6.91
to S-6.98.

Source state: Baltor was read on `main` at `e6346075`. Outside sources were
read on September 24, 2026.

## Summary

- **Laya** is an open-weight typed-decision model from Convai Innovations,
  released on September 18, 2026. It answers closed questions (choice,
  score and yes-or-no) in one forward pass. It does not make tools.
- **The "Laya/Toolsmith approach"** in the owner's table could not be traced
  to a published project, paper or product. Upstream Laya has no Toolsmith,
  Router of tools, Coach or Cloud component. This record therefore treats the
  table as a design proposal and researches each of its 18 rows.
- **Baltor already holds most of the table as rules or records**: a tool
  written during a run is a candidate, each step runs in its own harness
  instance, engines sit behind fixed edges, withdrawals are durable, and
  learned routing waits for one million recorded runs. Several of the
  supporting modules have their checks parked since the in-process execution
  path was parked on September 21 (roadmap S-6.28).
- **The gaps** are on the harness path: no typed path from a step that lacks
  a tool to a qualified tool, no per-step tool menu with a size budget and an
  abstention answer, no run contract for long tools, no per-tool outcome
  counts, no failure fingerprints or known fixes, and no record that joins a
  tool decision to its later outcome.
- **Laya fits one narrow place**: a candidate engine behind the existing
  `system_one` typed-decision engine, for closed decisions such as "does any
  tool apply" or "which of these five tools". It needs held-out qualification
  first, because its author reports near-chance zero-shot accuracy on typed
  decisions.

## The owner's question

The owner, September 24, 2026: "Been messing around with Laya and
tool-calling. I believe this doc has some real insight! What about these
comments and document, they deserve more research". The owner shared this
comparison table.

| Row | Traditional approach | Laya/Toolsmith approach |
|---:|---|---|
| 1 | The programmer predicts every tool | Tools are created when a capability is actually needed |
| 2 | A huge static tool catalogue | A router exposes only a small relevant subset |
| 3 | A new task needs a new code release | A Toolsmith creates, tests and registers a capability dynamically |
| 4 | A tool bug needs a developer | The Toolsmith repairs, retests, versions and retries |
| 5 | Every tool schema costs model context | The primary model sees only routed tools |
| 6 | Tool errors enter the conversation history | Repair and debug chatter stays behind a context wall |
| 7 | A fixed timeout per tool | Tools carry task-appropriate timeout and polling semantics |
| 8 | A long process blocks the agent | Start, status, log and stop tools allow asynchronous work |
| 9 | Tool quality is binary | Tools gain ratings, reliability, benchmark history and lifecycle states |
| 10 | Old tools remain forever | Unused or degraded tools are hidden, repaired, quarantined or removed |
| 11 | Routing is keyword or static | The router learns from actual usage and outcomes |
| 12 | Tool authoring quality is not measured | A Coach scores Toolsmith decisions and eventual outcomes |
| 13 | The same mistakes recur | Issue fingerprints feed known fixes back into the Toolsmith |
| 14 | Changing models means redesigning orchestration | Chat, Toolsmith, Router, Coach and Cloud evolve independently |
| 15 | Failure recovery is scripted beforehand | The system changes strategy dynamically |
| 16 | Agent context grows with execution history | Hidden execution gets summarized or compacted |
| 17 | Testing is manual | Benchmarks produce automatic deterministic evidence |
| 18 | Logs are debugging artifacts | Logs become training examples |

## What Laya is

Laya is identified with confidence from its own repository and model pages.

- Repository: [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya),
  created September 18, 2026, Apache 2.0 licence, 22,258 stars when read.
  The README ends with "Developed by Convai Innovations". The
  [project page](https://laya.convaiinnovations.com/) names Nandakishor
  Mukkunnoth, founder of Convai Innovations, as the author.
- What it does: "Laya evaluates typed questions (`choice`, `score`, `noul`)
  over any state (text, email, ticket or JSON document) in a single forward
  pass". It generates no text. The README reports 33 milliseconds for one
  question on a T4 graphics processor.
- Models: three checkpoints on Hugging Face,
  [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya)
  (ModernBERT-large, 421 million parameters, English), `laya-multilingual`
  (mmBERT-base, 322 million parameters, 100 or more languages) and
  `laya-typed-decisions`. A router picks the checkpoint by the script of the
  input text.
- Training: reinforcement learning against strictly proper scoring rules,
  which the author calls RLCD, with temperature calibration.
- Measured limits stated by the author: on the typed-decisions benchmark the
  base checkpoints score 0.36 and 0.35 against a random baseline of 0.318,
  and the fine-tuned checkpoint scores 0.766. The README says: "Treat Laya
  as a fast base to specialise, not as a zero-shot decision engine." It also
  states that `action.act_probability` "carries no usable signal yet" and
  that gating should use `confidence`.
- Wire protocol: `laya/serve.py` exposes "Laya over TypeSafe Jev's
  `/v1/systemone` wire protocol". `laya/mcp/` offers a Model Context Protocol
  server with `laya_predict`, `laya_route`, `laya_preset` and `laya_status`.
- Background: the launch post on Hacker News,
  ["I built non-autoregressive decision models with RL a year ago"](https://news.ycombinator.com/item?id=49765348),
  appeared on September 19, 2026 with 1,350 points. It presents Laya as an
  open counterpart to TypeSafe's hosted Jev model. The author's earlier paper
  is [SalesRLAgent](https://arxiv.org/abs/2503.23303) (March 30, 2025).
  Comments dispute zero-shot quality. One user reported 15 percent for Laya
  against 98 percent for Jev on a synthetic set of 1,000 items
  ([comment](https://news.ycombinator.com/item?id=49821344)). That is one
  unreviewed report.
- Community tool-calling uses: the
  [laya-agent-skill](https://github.com/HunterXing/laya-agent-skill) project
  uses typed decisions for "tool-call pre-screening before execution, with
  deterministic policy still in charge" and states that a decision model
  never authorizes a destructive operation. The
  [laya-agents](https://github.com/lesterppo/laya-agents) plugin has a model
  routing preset with a `needs_tools` question.

Baltor already has a typed-decision path for Jev, Circuit and any compatible
`system_one` endpoint: the [Jev integration record](JEV-TYPED-DECISION-INTEGRATION-2026-09-18.md)
and the [decision-tool guide](../guides/jev-and-harness-decision-tools.md).
`src/loop_engine/core/decisions/system_one.py` accepts an endpoint only on the
path `/v1/systemone`, with an exact model identity, a declared locality and a
declared provenance. Laya's own server speaks that wire, so Laya can be
declared as one more `system_one` engine on a loopback address. No new
adapter is needed.

## What the Toolsmith table is

No published source for the table was found.

- The upstream Laya repository (commit `23a17522`, September 24, 2026)
  contains no Toolsmith, Coach or Cloud component.
- GitHub repository and code searches for "toolsmith" with "laya", "coach"
  or "router" found only unrelated projects named toolsmith.
- An exact Hacker News search from August 29 to September 24, 2026 found no
  post or comment that mentions "toolsmith".
- The only arXiv title with "toolsmith" is
  [VLMgineer](https://arxiv.org/abs/2507.12644), which is about robotics.
- The owner's document and the comments the owner mentions were not
  available to this research.

The most likely reading: the table describes a design in which a fast
System 1 model such as Laya makes the cheap closed decisions (route, screen,
abstain), a model-led Toolsmith writes and repairs tools, and a Coach scores
both. The two older Baltor records that this task named do not use the word
toolsmith. The [Universal Loop standard](../reference/UNIVERSAL-LOOP-STANDARD.md)
says that a search, model call, validation, repair or external worker uses a
Loop envelope, and that a self-improvement task cannot approve its own
candidate. The [node context transport record](NODE-CONTEXT-TRANSPORT-AND-LEDGER-REFERENCES-2026-09-07.md)
recommends a host-brokered pull of material by named keys, a pull log as the
measurement, and the engine as the single ledger writer. Both ideas carry
into the proposals below.

## How this research was done, and its limits

- The session's web search allowance was already spent. The research read
  primary sources directly: the GitHub interface, the arXiv interface for
  titles, dates and abstracts, the Hacker News search interface, and the
  official documentation of the Model Context Protocol, Anthropic, OpenAI,
  Claude Code, Temporal and Sentry.
- Reddit threads linked from Hacker News refused automated reading.
- Every number from an outside source is reported by its authors and was not
  reproduced here.
- Baltor's state was read from source. "Checks parked" means the module's own
  checks are listed under `suite_collection_exceptions` in
  `src/loop_engine/forbidden_paths.json` and no longer run in the self-test.

## Where the three components would sit in Baltor

Nothing here adds a runtime type. Each component is work owned by a Loop or
an engine behind an existing kind of slot. Each step of a task runs in its
own freshly started harness instance, as the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
describes.

```text
Operational runtime type
└── Loop (the only executable graph vertex)
    ├── Role: Practitioner
    │   ├── Starting Practitioner Loop for the customer's task
    │   │   └── each step: one fresh harness instance (step_executor slot)
    │   │       ├── starts with a step tool menu (Router, proposed step_tool_menu/v1)
    │   │       └── may report a typed capability gap (Toolsmith trigger, capability_need/v1)
    │   ├── Spawned Practitioner Loop, profile: tool authoring (Toolsmith, proposed)
    │   │   ├── engines: harness recipes (Claude Code, Codex, OpenCode, Pi) and a Baltor-native template engine
    │   │   └── output: capability_candidate/v1 with its own tests; never a qualified tool
    │   └── Spawned Practitioner Loop, profile: verifier (held-out tool tests on another model route)
    ├── Role: Intelligence
    │   └── Queried Intelligence Loops: search before build, catalogue items, known fixes
    └── Role: Solution
        └── Connected Solution Loops: qualified deterministic tools invoked by exact contract
```

```text
Owner's component, and its home in Baltor
├── Chat: the primary model that works one step
│   └── step_executor, model_access, model_call_strategy (S-6.60)
├── Toolsmith
│   ├── trigger: capability_need/v1 in core/capability_needs.py (exists, no live caller); S-6.91
│   ├── work: tool authoring profile run by step_executor; S-6.92
│   └── qualification: held-out checks by another Loop, the review panel (S-6.63), a catalogue release (S-6.62)
├── Router
│   ├── eligibility: offer() in core/harness_intelligence.py (exists)
│   ├── ranking: catalogue_search_policy and the retrieval stages (S-6.32, S-6.52)
│   ├── closed decisions: typed_decision slot (Jev, Circuit, system_one; Laya as a candidate engine)
│   ├── exposure: tool_protocol_gateway (S-6.61) and the Harness Working Directory Compiler (S-6.44)
│   └── menu record: step_tool_menu/v1; S-6.93
├── Coach
│   ├── acceptance: response_evaluator slot, the only source of "accepted"
│   ├── joins: decision_outcome/v1 in core/decision_outcome.py (checks parked), extended to tool decisions; S-6.97
│   └── evidence: exact-scope ranking under the evidence rule; learned routing waits for heuristic adoption
└── Cloud: the hosted intelligence service
    └── catalogue, search, catalogue releases, durable withdrawals, usage records
```

## Row by row: the table against Baltor today

State words:

| State | Meaning |
|---|---|
| built | On `main`, and its own checks run in the main self-test |
| built, checks parked | On `main`, but its checks were retired from the self-test on September 21 |
| live | Running in the deployed service |
| planned | Named in a roadmap step, no code |
| missing | Neither built nor planned |

| Row | Baltor today | State | Owning component or slot | Proposal |
|---:|---|---|---|---|
| 1 | `core/capability_needs.py` defines `capability_need/v1` with the origin `failed_step` and the satisfier `tool`, and `assignment_for()` turns a need into a build assignment that carries its acceptance. Nothing outside the module calls it. The library factory (S-6.69, `tools/opencode_generation_lanes.py`) generates seven file kinds ahead of demand. Run-time tool writing (LE-SOLVE-003 in the [persistent solving record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)) lived in the parked in-process path. | partly built | capability needs, `step_executor`, library factory | S-6.91, S-6.92 |
| 2 | `offer()` in `core/harness_intelligence.py` filters by harness style, held effects, kind and tags, and names each withheld item with its reason. `core/node_provisioning.py` writes one folder per step with offered, withheld, offered bytes and exposed bytes. Hosted search orders references by the measured purpose-match policy; the relevance floor is planned (S-6.32). | partly built | `catalogue_search_policy`, retrieval stages, `tool_protocol_gateway` | S-6.93 |
| 3 | Catalogue releases publish approved items without a code release, and withdrawals are durable (`core/service_runtime/catalogue_releases.py`, live). The library has deterministic pre-checks and a three-family review panel (S-6.63, S-6.69). The run-time path from a generated tool to a promoted capability is the [Reusable Capability Flywheel](../components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md). | partly built; flywheel checks parked | library factory, `catalogue_qualification_resolver` | S-6.92 |
| 4 | `core/harness_fallback.py` switches engines only on declared failure kinds and never resets consumed authority. Tool repair as a new version with a new digest is designed in the flywheel profile `hybrid.execute_then_repair` and in `core/independent_failure_review.py`. | partly built; repair checks parked | `step_executor` fallback, flywheel | S-6.92, S-6.96 |
| 5 | Each step starts a fresh harness that holds only offered material (S-6.42). The gateway that lists only the tools a step may use is planned (S-6.61). Inside a harness, tool loading belongs to the harness: Claude Code defers tool definitions by default. | partly built | `step_executor`, `tool_protocol_gateway` | S-6.93 |
| 6 | The step boundary is already a wall: each step returns typed outputs to its owning Loop. In the parked path, failure classification ran in a Spawned verifier Loop with a fresh context. No typed summary returns from a tool repair to the step. | partly built | `step_executor`, Run History | S-6.92 |
| 7 | Each interaction declares a timeout policy class and a cancellation kind (`src/loop_engine/data/component_interactions.yaml`). `McpCallRequest` in `core/mcp_adapter.py` uses 60 seconds by default and refuses `timeout_not_enforced` for a synchronous handler. No tool declares its duration class, poll interval, heartbeat or idempotency. | partly built | `tool_protocol_transport` | S-6.94 |
| 8 | `core/local_resources.py` supervises harness instances with heartbeats, stall detection, pause, resume, hibernation and stop, with an append-only event log. The overnight journal is built. The reactive scheduler and worker have checks parked. `core/mcp_adapter.py` has no task handles. | partly built for processes; missing for tools | `tool_protocol_transport`, `protocol_endpoint` | S-6.94 |
| 9 | Engine records carry availability, qualification, lifecycle and the ladder connected, material listed, material loaded, step finished, independently accepted (`core/engines/records.py`). `core/intelligence_registry.py` has the lifecycle generated, staged, validated, served, superseded, retired. Each metered download writes a durable `service_usage/v1` row, summarized as `durable_tenant_usage/v1` (live). Per-item outcome counts are planned (S-6.41, S-6.51, S-6.83). | partly built | `catalogue_qualification_resolver`, `record_store` | S-6.95 |
| 10 | Withdrawals are live, and a release can never undo one. S-6.83 plans re-verification, near-duplicates, deprecation and withdrawal on evidence. The engine design treats an open circuit breaker as an expiring availability fact (planned). Quarantine exists only in the parked code asset lifecycle. | partly built | catalogue releases, S-6.83 | S-6.95 |
| 11 | The `ranking_strategy` slot keeps the declared order. Evidence ranking is planned and limited to an exact scope fingerprint with a minimum of 10 matched records and a rule that never lets a cheaper, worse engine win ([engines design](../architecture/ENGINES-BEHIND-FIXED-EDGES.md), sections 8.5 to 8.7). `core/heuristic_adoption.py` refuses a learned router or bandit below one million recorded runs, except an exact fingerprint at the atomic level. | planned, deliberately limited | `ranking_strategy` | S-6.97 feeds exact-scope evidence |
| 12 | `response_evaluator` is the only source of "accepted". The review panel scores library items (S-6.63). `core/decision_outcome.py` joins a decision forward through the stages proposed, admitted, executed, observed, verified and contributed. No record joins a tool decision to its outcome. | missing for tools; joins built, checks parked | `response_evaluator` | S-6.97 |
| 13 | `core/task_fingerprint.py` builds typed task fingerprints and refuses to treat text similarity as proof. `core/provider_failure_classes.py` classifies provider failures in a closed vocabulary. Failure classification and lessons with applicability and contraindications exist in `core/independent_failure_review.py` and `core/recovery_learning.py`. No failure fingerprint or known-fix record exists. | partly built | Run History and Solution Intelligence | S-6.96 |
| 14 | Engines behind fixed edges: the framework is being built (S-6.30), and `src/loop_engine/data/engine_slots.yaml` holds 45 slot records. The hosted service and the local engine are separate. The Toolsmith, Router and Coach have no slots. | partly built | engine framework | S-6.92, S-6.93, S-6.97 |
| 15 | The persistent solving record requires a typed next action after each failure and a changed approach when the same failure repeats; its implementation is in the parked path. On the harness path, `core/harness_fallback.py` changes engines on declared failures. S-6.60, S-6.86 and S-6.87 plan model strategies, decomposition and step expansion. | partly built | `step_executor`, `model_call_strategy` | S-6.96 |
| 16 | No step inherits another step's history. Runtime Memory is scoped to one run (`core/runtime_memory.py`). Compaction inside a harness belongs to the harness. The host-brokered pull of September 7 is not built. | partly built | `step_executor`, `runtime_memory` | S-6.92 |
| 17 | The self-test and conformance gates run removed-guard controls. The library factory runs parsers, the Agent Skills validator, every script against its own test in a sandbox, secret and network scans and a malicious-skill regression set (S-6.69). Review calibration uses frozen controls (S-6.63). No frozen population exists for tool authoring or tool menus. | partly built | self-test, library factory | S-6.92, S-6.93 |
| 18 | The OpenTelemetry exporter of `run_history_export` is parked. Trajectory export is planned. S-6.41 plans harness run records with consent and metadata only by default. S-6.88 plans when to train a typed-decision model. The [tool-use training research](TOOL-USE-TRAINING-LANDSCAPE-2026-09-11.md) ranks the training options. | planned | `run_history_export` | S-6.98 |

## Prior art and decisions

Each row names a primary source with its date, what it shows, and whether
Baltor adopts, adapts or rejects it.

### Tool making and skill libraries

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Voyager](https://arxiv.org/abs/2305.16291) | May 25, 2023 | A growing library of executable skills, retrieved by description and improved with execution errors and self-verification | Adapt | The library is Baltor's catalogue. Self-verification by the same model is replaced by held-out checks from another Loop |
| [Large Language Models as Tool Makers](https://arxiv.org/abs/2305.17126) | May 26, 2023 | A strong model makes a tool once, a light model uses it many times, and a dispatcher decides between reuse and making | Adopt the division of labor; adapt the dispatcher | Matches the north star of small models doing more. The dispatcher becomes search before build with a relevance floor (S-6.91) |
| [CREATOR](https://arxiv.org/abs/2305.14318) | May 23, 2023 | Separates abstract tool creation from concrete execution, with rectification after errors | Adopt | The authoring step and the using step are different steps with different harness instances |
| [CRAFT](https://arxiv.org/abs/2309.17428) | September 29, 2023 | Tool sets built from validated solutions, abstracted, deduplicated, then retrieved at inference | Adopt | The same order as the flywheel: validate, generalize, deduplicate, retrieve |
| [TroVE](https://arxiv.org/abs/2401.12869) | January 23, 2024 | A toolbox grown by use and periodically trimmed, 79 to 98 percent smaller | Adapt | Trimming becomes ranking down and archiving with history, never deletion (S-6.95) |
| [LLM Agents Making Agent Tools](https://arxiv.org/abs/2502.11705) | February 17, 2025 | Turns a paper's code repository into a tool with self-correction; 15 tasks, over 100 unit tests, 80 percent correct | Adopt the benchmark shape; adapt the source path | Unit tests per tool task fit the tool authoring benchmark. Repository sources pass the library licence gate |
| [Alita](https://arxiv.org/abs/2505.20286) | May 26, 2025 | Minimal predefined tools; generates Model Context Protocol servers for a task; 75.15 percent on GAIA validation | Adapt | A generated protocol server becomes a candidate plugin package. Serving it without independent qualification is rejected |
| [Live-SWE-agent](https://arxiv.org/abs/2511.13646) | November 17, 2025 | Starts from shell tools and evolves its own scaffold while it solves tasks | Adapt | Run-time tool creation inside one run is useful under LE-SOLVE-003. Self-modification of the harness without qualification is rejected |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | May 29, 2025 | Self-modifying coding agent; an archive of variants; each change validated on benchmarks | Adapt | The archive matches "archive, never delete". Benchmark validation by the modifying system is evidence, not independent acceptance |
| [Tool-Making in Low-Latency Systems](https://arxiv.org/abs/2607.08010) | July 9, 2026 | Repeated procedure steps compiled into validated, versioned tools before deployment, with code generation as fallback; in production, 42 percent lower median latency, and on 1,500 historical alarms up to 53 percent fewer end-to-end errors | Adopt | The clearest evidence for reuse over rewriting. It matches the flywheel and the owner's goal of turning non-deterministic work into deterministic solutions |
| [Tool-Genesis](https://arxiv.org/abs/2603.05578) | March 5, 2026 | A tool creation benchmark with three axes: interface compliance, functional correctness, downstream utility; one-shot creation is weak and small flaws grow | Adopt | The three axes become the tool authoring benchmark and the Coach's scoring axes |
| [ToolLibGen](https://arxiv.org/abs/2510.07768) | October 9, 2025 | Clusters many narrow tools, merges them into fewer general tools, and uses a reviewing agent to keep every function | Adapt | Fits the near-duplicate work of S-6.83. The reviewer must not be the merging process |
| [Schema-grounded Multi-task Iterative Tool Honing](https://arxiv.org/abs/2608.24571) | August 25, 2026 | Trains tool creation and use together, with separate rewards for schema, code and outcome failures | Adapt the axes; defer the training | Separate axes locate failures. Training waits for consented data (S-6.98) |

### Tool retrieval and routing

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Gorilla](https://arxiv.org/abs/2305.15334) | May 24, 2023 | Retrieval of current documentation lets a model write correct interface calls and follow documentation changes | Adapt | The Router retrieves the current tool description at step start. No fine-tuned model is needed |
| [ToolLLM](https://arxiv.org/abs/2307.16789) | July 31, 2023 | 16,464 real interfaces; a trained retriever recommends relevant ones | Adapt the retriever; reject its tree search as a default | Retrieval is needed at library scale. Depth-first search over tool calls is costly |
| [Retrieval Models Aren't Tool-Savvy](https://arxiv.org/abs/2503.01763) | March 3, 2025 | Strong general retrievers do poorly on 7,600 tool retrieval tasks over 43,000 tools | Adopt as a warning | Router quality must be measured on held-out Baltor phrasings |
| [RAG-MCP](https://arxiv.org/abs/2505.03275) | May 6, 2025 | Retrieving tools before the model call cut prompt tokens by over half and raised selection accuracy from 13.62 to 43.13 percent | Adopt | The Router runs before the step's model sees any tool |
| [MCP-Zero](https://arxiv.org/abs/2506.01056) | June 1, 2025 | The agent requests a tool it lacks; hierarchical routing over 308 servers and 2,797 tools | Adapt | A step can ask for more through one stable search tool; the Router answers the request |
| [Anthropic tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) and [advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use) | November 24, 2025 | Deferred tool definitions; tool choice degrades beyond 30 to 50 tools; over 85 percent less context; custom search can return `tool_reference` blocks | Adopt as an engine | Where the harness supports it, Baltor supplies the catalogue and a custom search instead of competing with it |
| [OpenAI tool search](https://developers.openai.com/api/docs/guides/tools-tool-search) | Read September 24, 2026 | Deferred tools with hosted or client-run search; namespaces of fewer than 10 functions | Adopt as an engine | Same reason as the Anthropic engine |
| [Model Context Protocol client best practices](https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices) | Revision 2026-07-28 | Progressive discovery in three layers (catalogue, inspect, execute); switch at 1 to 5 percent of context; changing the tool list mid-conversation breaks prompt caching | Adopt | Baltor's one harness per step makes the step start a natural place to choose tools |
| [ToolMenuBench](https://arxiv.org/abs/2606.15508) | June 13, 2026 | Filtering the visible tool menu raised task success from 32.1 to 85.7 percent and cut tokens by about 98 percent; it also measures risky-tool exposure | Adopt the metrics | Menu size, wrong-tool calls and risky exposure become Router measures |
| [CacheRouter](https://arxiv.org/abs/2608.22708) | August 24, 2026 | A fixed set of core tools for the main model and a separate routing channel for the long tail; 90.99 to 95.2 percent cache hits | Adapt | A fixed menu per step keeps the prefix stable. A sub-model that runs effectful tools without the step's authority checks is rejected |
| [Selection Is Retrieval, Abstention Is Not](https://arxiv.org/abs/2609.18672) | September 16, 2026 | Lexical retrieval selects well when words match, but cannot say "no tool applies"; a frozen encoder does better at abstention | Adopt | Abstention is its own decision in the Router. Laya's yes-or-no answer is a candidate engine for it |
| [Over-privileged tool selection](https://arxiv.org/abs/2606.20023) | June 18, 2026 | Agents often choose a higher-privilege tool when a lower one suffices, more often after a failure | Adopt | The Router orders a sufficient lower-privilege tool first, with a named check |
| [Laya](https://github.com/NandhaKishorM/laya) | September 18, 2026 | Fast typed decisions; near chance zero-shot on typed decisions; strong after fine-tuning; serves the `/v1/systemone` wire | Adapt | A candidate engine for closed Router decisions behind the existing `system_one` engine, after held-out qualification. Rejected as the only Router engine or as a zero-shot tool picker |
| [RouteLLM](https://arxiv.org/abs/2406.18665) and [FrugalGPT](https://arxiv.org/abs/2305.05176) | June 26, 2024; May 9, 2023 | Learned routers and cascades between strong and weak models | Defer | Model routing belongs to S-6.60. A learned router waits for heuristic adoption |

### Long-running tools

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Model Context Protocol 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/changelog) | November 25, 2025 | Experimental tasks with polling and deferred results (SEP-1686); input validation errors returned as tool execution errors so the model can self-correct (SEP-1303) | Adapt | Tasks moved to an extension in the next revision. The error rule informs the context wall decision |
| [Model Context Protocol 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) and the [tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview) | July 28, 2026 | Tasks as extension `io.modelcontextprotocol/tasks` (SEP-2663): `tasks/get` polling with a suggested interval, `tasks/update`, cooperative `tasks/cancel`; stateless requests; deterministic `tools/list` order; a feature lifecycle of Active, Deprecated and Removed | Adopt | Long tools use task handles when both sides declare the extension. The lifecycle policy informs tool states |
| [Claude Code tools reference](https://code.claude.com/docs/en/tools-reference) | Read September 24, 2026 | Background commands, a Monitor tool, `TaskStop`, and a per-call timeout that the model chooses within set ceilings; a timed-out command moves to the background | Adopt as harness behavior | Baltor's run contract tells the harness which duration class a tool has |
| [Temporal activity timeouts](https://docs.temporal.io/encyclopedia/detecting-activity-failures) | Read September 24, 2026 | Schedule-to-start, start-to-close, schedule-to-close and heartbeat timeouts; heartbeats carry progress | Adopt | A tested timeout vocabulary for the tool run contract |
| [Verified tool calls under non-atomic failures](https://arxiv.org/abs/2608.02645) | July 31, 2026 | Postcondition checks, verify-before-retry and idempotency keys reduce duplicate actions | Adopt | Matches Baltor's rule that an uncertain effect is never repeated silently |

### Reliability, lifecycle and learning routers

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [τ-bench](https://arxiv.org/abs/2406.12045) | June 17, 2024 | The pass^k measure of consistency over repeated trials | Adopt | Tool reliability counts repeated trials where they exist |
| [Circuit breaker](https://martinfowler.com/bliki/CircuitBreaker.html) | March 6, 2014 | Closed, open and half-open states stop calls to a failing dependency | Adopt | Already planned as an expiring availability fact |
| [Flaky tests at Google](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html) | May 27, 2016 | About 1.5 percent of test runs were flaky; a tool quarantines a flaky test and files a bug, which "could easily mask a real race condition" | Adapt | Quarantine is a hold that opens a repair need and keeps failures visible |
| [Invocation-level reliability](https://arxiv.org/abs/2608.26189) | August 23, 2026 | Exact-match scoring against one fixed trajectory can decide a reliability estimate before any data | Adopt as a caution | Reliability uses postconditions and state-conditioned scoring, not trajectory matching |
| [LinUCB](https://arxiv.org/abs/1003.0146), [Thompson sampling](https://arxiv.org/abs/1707.02038), [PILOT](https://arxiv.org/abs/2508.21141), [LLM Bandit](https://arxiv.org/abs/2502.02743) | 2010 to 2025 | Contextual bandits that learn routing from outcome feedback | Reject for now | The owner's one-million-run rule (September 18). Propensities are recorded now so that later [doubly robust off-policy evaluation](https://arxiv.org/abs/1103.4601) is possible |

### Failure fingerprints and known fixes

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Sentry fingerprint rules](https://docs.sentry.io/concepts/data-management/event-grouping/fingerprint-rules/) | Read September 24, 2026 | Groups events by error type, message, stack frames and variables | Adopt | A tested normalization for `failure_fingerprint/v1` |
| [Windows Error Reporting](https://www.microsoft.com/en-us/research/publication/debugging-in-the-very-large-ten-years-of-implementation-and-experience/) | October 2009 | Error reports are classified into buckets to prioritize work and "report fixes to users" | Adopt | The bucket to known-fix path |
| [Getafix](https://arxiv.org/abs/1902.06111) | February 16, 2019 | Learns fix patterns from past human fixes | Defer | Pattern learning is a heuristic that waits for adoption; exact fingerprints first |
| [ReasoningBank](https://arxiv.org/abs/2509.25140), [Agent KB](https://arxiv.org/abs/2507.06229), [ExpeL](https://arxiv.org/abs/2308.10144), [Reflexion](https://arxiv.org/abs/2303.11366) | 2023 to 2025 | Memories of strategies and fixes from successes and failures | Adapt | Lessons become candidates that an independent process qualifies |
| [Boundary-Aware Skill Memory](https://arxiv.org/abs/2608.22339) | August 23, 2026 | Skills distilled only from successes raised the wrong-tool margin by 47 percent; adding boundary fields (applicability, risk cues, avoidance rules, recovery notes) raised task success and cut wrong calls | Adopt | Every known fix carries applicability and contraindications, as Baltor's parked recovery learning already requires |
| [Self-healing orchestrators](https://arxiv.org/abs/2606.01416) | May 31, 2026 | Mapping failure signals to classes and targeted recovery beat retry-only on a fault-injection set | Adopt as support | Matches the failure classes of the persistent solving record |

### Coach and evaluator designs

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) | June 9, 2023 | Model judges show position, length and self-preference bias | Adopt as a caution | The Coach never shares the author's model family or route; its scores are observations |
| [Process and outcome feedback](https://arxiv.org/abs/2211.14275) and [Let's Verify Step by Step](https://arxiv.org/abs/2305.20050) | 2022; 2023 | Feedback on steps and on outcomes teach different things | Adapt | The Coach scores the authoring decision and the outcome separately |
| [Agent-as-a-Judge](https://arxiv.org/abs/2410.10934) | October 14, 2024 | An agent evaluates another agent's work | Adapt | An evaluator engine where no deterministic check exists, with route separation |
| [TextGrad](https://arxiv.org/abs/2406.07496), [GEPA](https://arxiv.org/abs/2507.19457), [DSPy](https://arxiv.org/abs/2310.03714) | 2023 to 2025 | Textual feedback from traces improves prompts and programs | Adapt | Coach feedback feeds the self-improvement Practitioner task, which stages candidates for independent review |
| [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | December 19, 2024 | Routing and evaluator-optimizer workflows; tools designed so that mistakes are hard | Adopt | The tool authoring guidance asks for arguments that make mistakes hard |
| [Magentic-One](https://arxiv.org/abs/2411.04468) | November 7, 2024 | An orchestrator with task and progress ledgers that replans when progress stalls | Adapt | Supports the rule that a repeated failure forces a changed approach |

### Traces to training

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Agent Lightning](https://arxiv.org/abs/2508.03680) | August 5, 2025 | Turns traces of any agent into training transitions without changing the agent | Adapt as an export engine | Only after consent records and independent labels exist |
| [AgentTuning](https://arxiv.org/abs/2310.12823), [FireAct](https://arxiv.org/abs/2310.05915), [SWE-Gym](https://arxiv.org/abs/2412.21139), [SWE-smith](https://arxiv.org/abs/2504.21798), [ToolRL](https://arxiv.org/abs/2504.13958) | 2023 to 2025 | Fine-tuning on agent trajectories and verifiable rewards | Defer | The September 11 research already ranks these; nothing trains before consented data exists |
| Laya fine-tuning notebook | September 2026 | Fine-tuning moves typed decisions from 0.36 to 0.766 on the author's benchmark | Adapt | The first training use of consented traces is a small typed-decision model for Router decisions, measured on held-out data |

### Context walls and compaction

| Source | Date | What it shows | Decision | Reason |
|---|---|---|---|---|
| [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | September 29, 2025 | Compaction, tool result clearing, notes outside the context, and sub-agents that return summaries of 1,000 to 2,000 tokens | Adopt | The tool repair summary has a declared size ceiling |
| [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | November 4, 2025 | Intermediate results stay in the execution environment; an example went from 150,000 to 2,000 tokens | Adapt | Qualified deterministic tools run as Connected Solution Loops outside the model's context |
| [Context engineering lessons from Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) | July 18, 2025 | Mask tools rather than remove them mid-task; keep failed actions in context so the model does not repeat them | Adopt both | The menu is fixed within a step, and a compact failure line stays in the step's own context |

## Proposals added to the roadmap

Each proposal is the smallest typed extension at an existing boundary. None
adds a runtime type. Each keeps four rules: one Loop runtime, a tool written
during a run is a candidate until independently qualified, discovery never
grants authority, and completion is never acceptance.

| Step | Proposal | Boundary | Discriminating test |
|---|---|---|---|
| S-6.91 | A step that lacks a tool reports an optional typed `capability_gap` in its step result. The owning Loop turns it into the existing `capability_need/v1` with origin `failed_step`, searches the library first, and creates a build assignment only when nothing eligible passes the relevance floor | `core/capability_needs.py`, the step result of S-6.31 | A gap with a matching approved item yields an offer and no build. Removing the search-first check yields a build, and the named check fails |
| S-6.92 | A tool authoring profile (the Toolsmith) run by `step_executor` writes `capability_candidate/v1`: interface schemas, declared effects, a run contract, its own tests, provenance and a digest. Another Loop on a different model route writes held-out tests. Use inside the run needs those tests to pass; use by other customers needs the review panel and a catalogue release. Only a typed `tool_repair_summary/v1` under a size ceiling returns to the step | `src/loop_engine/data/engine_slots.yaml`, `core/capability_needs.py`, `tools/candidate_review` | A candidate that passes its builder's tests and fails the held-out tests is not reused. With the requirement removed it would be, so the check is what refuses it (LE-SOLVE-003) |
| S-6.93 | A `step_tool_menu/v1` record at step start (the Router): the eligible set from `offer()`, ranked by the bound search engine, cut to a declared tool count and schema size, least privilege first, in a stable order, with an explicit "none applies" answer. The menu is fixed for the step; later needs go through one stable search tool. Engines: lexical purpose match, hybrid search, a typed-decision reranker over a shortlist (Laya, Jev or Circuit through `typed_decision`), and pass-through to a harness's own tool search | `core/node_provisioning.py`, `core/harness_intelligence.py`, `src/loop_engine/data/engine_slots.yaml` | An unrelated objective yields "none applies" instead of the best poor match. A sufficient lower-privilege tool ranks first. A menu over budget or changed mid-step is refused |
| S-6.94 | A `tool_run_contract/v1` on every tool: duration class, start-to-close timeout, heartbeat interval, poll interval, cancellation kind and idempotency. Long tools use the Model Context Protocol tasks extension when both sides declare it, otherwise a Baltor wrapper supervised by `core/local_resources.py` | `core/mcp_adapter.py`, `src/loop_engine/data/component_interactions.yaml` | A timed-out call to a non-idempotent tool is never retried without a postcondition check. A tool without a run contract is refused at serving |
| S-6.95 | A `tool_outcome_summary/v1` projection per tool version and exact scope: offered, fetched, loaded, invoked, postcondition passed, failed by class, accepted steps and repeated-trial consistency. Quarantine is a reversible hold with a reason, evidence and a minimum sample; unused tools are ranked down or archived with history | `core/service_runtime/catalogue_releases.py`, `tools/candidate_review` | A quarantine below the minimum sample is refused. Download counts cannot raise a success rate |
| S-6.96 | A `failure_fingerprint/v1` that normalizes a failure (tool identity and version, closed failure class, error type, message template without volatile values, contract references) and a `known_fix/v1` candidate with applicability and contraindications. Fixes match exact fingerprints only. A repeated fingerprint in one step forces the next attempt to change a declared dimension or end with a recorded reason | `core/task_fingerprint.py`, `core/provider_failure_classes.py` | Two failures that differ only in a path and a time share one fingerprint. A fix without contraindications is refused. A similar but different fingerprint gets no fix before heuristic adoption |
| S-6.97 | The Coach: `decision_outcome/v1` joins extended to tool decisions (build, reuse or abstain; menu composition; known-fix use). An independent evaluator scores separate axes: interface compliance, correctness on held-out tests, downstream utility and cost. Scores are evidence for the exact-scope evidence rule, never acceptance | `core/decision_outcome.py`, `src/loop_engine/data/engine_slots.yaml` | A score recorded as acceptance is refused. A scorer from the author's model family is refused. An unresolved join stays unresolved, never a success |
| S-6.98 | A `training_example_export/v1` engine of `run_history_export`: only runs whose consent record allows it, labels only from independent evaluators, a frozen held-out split, and no secrets or raw prompts without opt-in. The first use is to evaluate, and later fine-tune, a small typed-decision model for Router decisions | `src/loop_engine/data/engine_slots.yaml`, the S-6.41 run records | An export without consent is refused. An example labeled by the model that produced it is refused. A held-out example found in training data is refused |

## Decisions made and why

1. **Laya is a candidate engine for closed Router decisions, not the
   Router.** It already speaks the `/v1/systemone` wire that Baltor's
   `system_one` engine accepts. Its author reports near-chance zero-shot
   accuracy on typed decisions and a large gain after fine-tuning, so it is
   selected only after it beats lexical routing on a held-out Baltor set.
2. **Learned routing keeps waiting for one million recorded runs.** This is
   the owner's rule of September 18, 2026, recorded in
   `core/heuristic_adoption.py`. Exact-scope evidence ranking still lets
   recurring steps improve now. Propensities and outcomes are recorded from
   the start so that later off-policy evaluation is possible.
3. **The tool menu changes only at a step boundary.** The Model Context
   Protocol client guidance and the Manus lessons both show that changing
   tools mid-conversation breaks prompt caching. Baltor starts a fresh
   harness for each step, so the step start is the natural boundary.
4. **The context wall stands between tool repair and the step, not between a
   step and its own errors.** Model Context Protocol 2025-11-25 returns input
   errors to the model so it can correct itself, and Manus keeps failed
   actions in context. The step sees a compact failure line and a typed
   repair summary; the full repair transcript stays in Run History.
5. **A tool written during a run is used in that run only after held-out
   tests from another Loop pass, and by other customers only after the review
   panel and a catalogue release.** This is LE-SOLVE-003. Tool-Genesis shows
   that one-shot tool creation is weak, and self-verification is not
   independent.
6. **Quarantine is a reversible hold, and withdrawal is durable history.
   Nothing is deleted.** This follows the owner's "build out, never remove"
   rule and Google's warning that quarantine can hide a real defect.
7. **Known fixes match exact fingerprints only and carry applicability and
   contraindications.** An exact fingerprint at the atomic level is the one
   exception to the heuristic adoption rule. Boundary-aware skill memory
   shows that unconditional lessons raise wrong-tool confidence.
8. **Long tools use the Model Context Protocol tasks extension only by
   explicit negotiation.** Revision 2026-07-28 moved tasks into an official
   extension. Baltor never downgrades silently.
9. **Coach scores are evidence, never acceptance.** `response_evaluator`
   stays the only source of "accepted". Separate scoring axes locate the
   failing part, as Tool-Genesis and the joint creation-and-use training work
   show.
10. **Training on traces waits for consent and independent labels.** The
    privacy baseline in ASTRA.md records metadata only by default, and raw
    inputs need explicit opt-in (S-6.41).

## What this record does not establish

- It does not identify the author of the owner's table or the comments.
- It does not measure Laya, any router or any tool on Baltor's tasks.
- It reproduces no outside number.
- It does not qualify any engine, approve any package or change any runtime
  behavior. The eight roadmap steps are proposed work.
