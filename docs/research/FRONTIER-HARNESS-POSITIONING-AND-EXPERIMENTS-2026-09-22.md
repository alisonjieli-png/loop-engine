# Frontier harness positioning and experiments

Kind: dated primary-source competitor research and proposed comparisons.
Reviewed September 22, 2026. This is read-only research for the owner and
Claude Code. It changes no runtime contract, public claim or roadmap status.
The [roadmap](../roadmap/roadmap.yaml) remains the work authority. The
[cross-functional launch review](CROSS-FUNCTIONAL-HARNESS-AND-LAUNCH-REVIEW-2026-09-22.md)
holds the current release-gate audit. Vendor descriptions below are labeled
as such; none is a Loop Engine benchmark.

## The product thesis being tested

The owner's north star is to make customer-run coding harnesses and
multi-agent systems as capable and efficient as possible on unseen tasks.
For each governed step, the intended system chooses sufficient context,
qualified reusable code, tools, a decision method, and a permitted model
strategy within the customer's quality, budget and permission constraints.
A fresh, separate harness is the default design for each focused step so its
context does not grow into the whole task history. The step can seek more
information when needed; fewer tokens or steps are not a universal objective.
Accepted work under the customer's constraints is the success condition.
Reusable solutions, lower total cost, overnight work and deterministic
execution are potential benefits to establish on real tasks.

The [repository instructions](../../AGENTS.md) and
[complete behavior](../../ASTRA.md#complete-behavioral-explanation)
already state this direction. The current hosted service searches and
delivers selected material. The complete fresh-harness-per-step execution
and independently checked customer task have not been qualified on the main
line. A public page should distinguish those facts.

## Runtime classification before the comparison

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

Harnesses, providers, skills, model strategies and protocol servers remain
adapters or typed mechanics used by a classified Loop. A different harness
engine does not become a new executable graph type. A fresh context window,
a fresh operating-system process, a confined workspace, and a verified
loaded-material manifest are four different properties.

## What competitors already document

This matrix records the inspected official surface. It does not imply that
an omitted feature is absent from a product. Prices, benchmarks and client
behavior can change; each cited page is the source for its own row.

| Product | Published overlap with the north star | Exact comparison Baltor still needs |
|---|---|---|
| [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) | Specialized subagents get separate context and can use their own model and tools. | Separate-context delegation is already an offered feature. Test process and global-configuration isolation, exact material loaded, and accepted work rather than treating a clean context alone as differentiation. |
| [Cursor subagents](https://prod.cursor.com/docs/subagents) | Subagents start with clean context, can run in parallel, use specialized models and tools, and return a condensed result. [Worktrees](https://cursor.com/docs/configuration/worktrees) can isolate files. | Its documentation distinguishes subagent context from worktree isolation. Compare the full environment and observed resource loading, not the presence of a subagent. |
| [OpenCode](https://opencode.ai/v2/docs/agents) and [Pi](https://github.com/earendil-works/pi) | Configurable agents or extensions, model choice, and reusable skill or tool surfaces. OpenCode version 2 describes fresh-context subagents. | They are upstream harnesses and possible Baltor engines. Measure a versioned adapter, then an extension, then a fork against the same task and evaluator. |
| [ZCode](https://zcode.z.ai/en/docs/agents) | Customer-run desktop harness with built-in browser and terminal tools, project instructions, skills, subagents, Goal Mode and model choice. Its [pinned source](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/README.en.md) also describes a command line path. | The [pinned-source review](ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md) has no Loop Engine native load or checked task. Its source review is not an integration claim. |
| [Devin Fusion](https://cognition.com/blog/local-fusion) | A persistent frontier lead delegates focused work to a persistent cheaper sidekick with its own context and tools. Both keep prompt caches, exchange briefs and results, and the lead reviews. [Devin CLI](https://devin.ai/cli) offers local work, model choice, skills, subagents and cloud handoff. | This is the strongest current counterexample to assuming a fresh process always saves money. Compare fresh per-step harnesses with persistent dual contexts at the same model routes, task population, effects and evaluator. Cognition's published score and cost table is not a Baltor result. |
| [Augment Context Engine](https://www.augmentcode.com/blog/context-engine-mcp-now-live) and [Auggie](https://www.augmentcode.com/blog/auggie-cli-harness-rebuild-53-percent-cheaper) | Context retrieval is offered through Model Context Protocol to other coding agents; its own Pi-based harness and compaction have published cost and task results. [Prism](https://www.augmentcode.com/blog/augment-prism-model-routing-to-reduce-cost-and-maintain-quality) routes model turns. | It overlaps context selection, customer-chosen agents, model routing and harness efficiency. Compare exact source, task, model and evaluator controls, including context-engine fees and cache behavior. Vendor-reported gains cannot be transferred to Baltor. |
| [OpenSquilla](https://github.com/TokenRhythm/opensquilla) | An Apache 2.0 local agent with a model router, memory, sandbox and several provider adapters. Its [technical paper](https://arxiv.org/html/2607.11399) proposes step-level choice of one or several models conditioned on harness state, with outcome records used to train a better router. | This is direct prior art for the owner's proposed model-call strategy and feedback loop. Its reported benchmark frontier is author-reported and does not qualify the same policy for Baltor's tasks or authority model. |
| [Google Agent Executor](https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime) | Preview open-source runtime for bring-your-own harness, models and compute, with task/workspace/gateway manifests, sandboxing, event logs, snapshots and resumption. The [repository](https://github.com/google/ax) warns of breaking changes before stable release. | Customer-owned execution and declared workspaces are already offered. Compare exact per-step selection and actual loaded-material proof; inspect it as a possible infrastructure engine, not a qualified replacement. |
| [Tessl](https://docs.tessl.io/) | Versioned skill and package context, registry distribution, review scores and skill scenario evaluation. Its [evaluation guide](https://docs.tessl.io/improving-your-skills/evaluate-skill-quality-using-scenarios) compares with and without a skill; publication can skip evaluations. | A registry with review scores and evaluation tools already exists. Baltor must show whether mandatory independent admission and exact use evidence improve accepted customer work. |
| [Vercel Skills](https://github.com/vercel-labs/skills/blob/7407f3893ad4dceab546ac002c3ef806e4000c73/README.md) | Cross-harness search and install; `skills use` temporarily stages one skill and can start a supported agent. | Just-in-time file delivery is already free. Compare useful selection, effect control, source identity and independently checked outcomes. |
| [Context7](https://context7.com/plans) and [Mintlify Index](https://www.mintlify.com/blog/mintlify-index) | Documentation retrieval, selected context and a free entry point. Context7's paid tier adds private sources; Mintlify describes a free beta. | Generic public documentation search is a weak premium claim. Compare version correctness, abstention, actual client use and accepted work for the right material category. |

The [Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents/)
now compares coding-agent variants on its declared benchmark set with
quality, cost, time and token measures. [Cognition's article](https://cognition.com/blog/local-fusion)
names Artificial Analysis and Vals as evaluation partners for Fusion.
Those published comparisons are useful external evidence only with their
exact task population, versions, model routes and evaluator. They cannot be
presented as a controlled head-to-head result for Loop Engine.

## Positioning that survives this comparison

Fresh subagent context, model routing, smaller workers, skill review tools,
temporary skill loading, overnight work and context-aware retrieval are each
already offered or documented elsewhere. The testable Baltor combination is
more specific: customer-run harnesses receive an exact, permission-bound
package for one governed step; the step may use qualified code as well as
guidance; the system records what was offered, fetched, loaded and used;
the complete task is independently accepted; and the next engine choice can
use the verified outcome within customer authority. That combination is a
product hypothesis. No present evidence establishes it as unique or better.

| Audience and stage | Defensible present wording | Stronger wording needs |
|---|---|---|
| New visitor | Baltor serves reviewed material to a customer's own coding tools through authenticated search and selected downloads. | A current library count, supported-client list and working sign-up path from the live release. |
| Invited developer | An exact item can be installed and observed in one native client under a personal key, once D-17's outside-user proof passes. | A client-observed load, a checked step, version and digest record, and an honest error path. |
| Investor or technical partner | The intended fabric uses one focused harness per governed step by default, typed authority and interchangeable engines. | Matched task evidence showing its quality, total cost, recovery or privacy advantage against persistent and fresh-context competitors. |
| Broad public claim | A verified benefit on a named task population, model and release. | No-skill, raw-source and leading-product baselines, complete physical calls and independently accepted results, with failures equally visible. |

The repository's [roadmap S-6.31](../roadmap/roadmap.yaml) and S-6.42 still
mark the executor slot and fresh-instance qualification as proposed. The
website or handbook may state the default design with a planned label;
neither should imply that the full path is already live.

## The comparison that can distinguish the architecture

[Cognition's Fusion design](https://cognition.com/blog/local-fusion)
keeps a frontier lead and cheaper sidekick in separate **persistent**
contexts. It argues that switching models mid-task can lose prompt-cache
benefits and that a cheap worker can cause expensive review and rework.
[Augment's Prism review](https://www.augmentcode.com/blog/augment-prism-model-routing-to-reduce-cost-and-maintain-quality)
also accounts for cache eviction and reports a routing arm that cost more
than its fixed-model comparison. These are strong counterfactuals to the
assumption that a fresh harness per small step always saves money.

Freeze a population of real tasks before choosing a configuration. Hold the
repository snapshot, model routes, evaluator, allowed effects, budget and
acceptance standard constant where the products permit it. Preserve failed,
inconclusive and excluded attempts. Compare these arms in order:

| Arm | Configuration | Question this comparison can answer |
|---|---|---|
| A | Pinned upstream harness in one persistent session. | Reference for the task, model and tool population. |
| B | The same binary's native fresh-context subagent in one continuing host process. | B against A estimates the effect of context reset without necessarily resetting process state. |
| C0 | A cold, independently initialized instance of the same harness for every governed step, given the same allowed context and files as B. | C0 against B estimates process restart and handoff overhead when material is held fixed. |
| C1 | C0 with an exact, narrowed resource manifest, without Baltor-selected intelligence. | C1 against C0 estimates the effect of context and resource narrowing, including omitted necessary facts. |
| D | C1 with Baltor-selected, independently reviewed context or reusable code. | D against C1 estimates the marginal value and harm of selection and reviewed material. Add a raw-source arm to test whether the authored item helps more than its source. |
| E | A persistent lead-and-sidekick pair on the same allowed model routes, when a faithful local configuration exists. | E is a whole-system competitor to D. It changes topology and persistence together, so a difference cannot be assigned to cache or process alone. A vendor run with different routes or evaluator is external evidence, not a causal arm. |

To isolate cache reuse within a two-agent topology, add matched persistent
and freshly initialized lead-and-sidekick arms with the same briefs,
selected material and routes. C0 and C1 similarly keep their binary and
model fixed so process restart is not conflated with a different harness.

Balance task types that benefit from selected context, need a late historical
fact, favor a deterministic code component, require cross-step state, or
should refuse an effect. Measure accepted task outcomes first. Then report
all physical model calls, route and Jev decisions, retrieval and bootstraps,
provider-reported cache reads and writes, tokens, elapsed time, monetary cost
where known, omitted requirements, duplicate work, denied effects, process
failures and recovery. Unknown usage remains unknown. Report the quality and
cost frontier rather than one score that rewards an incomplete cheap answer.
This follows the [benefit evidence guide](../guides/launch-benefits-and-evidence.md)
and the [configuration comparison guide](../guides/configuration-grid-search-and-optimization.md).

[Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/)
found position-sensitive failures in its long-input retrieval and question
answering tasks. A [2026 selective-context study](https://arxiv.org/abs/2606.10209)
reports benefits from pruning or summarization in a narrower enterprise
tool-use population. These support evaluating focused context. Neither
proves a new operating-system process is necessary or that context reduction
always preserves a constraint. Include required facts planted early and
late; a handoff that drops one must fail acceptance.

## Google state and context work beside Baltor's default

I found no primary Google publication titled exactly “Agent.State.” The
owner's “all” direction calls for reading the related work as several
mechanisms. None of the following by itself establishes that a newly
started harness process for **every** focused step is superior.

| Google primary source | Exact mechanism | Relationship and limit for Baltor |
|---|---|---|
| [Agent Development Kit sessions and state](https://adk.dev/sessions/state/) and [Google's state article](https://cloud.google.com/blog/topics/developers-practitioners/remember-this-agent-state-and-memory-with-adk) | Session history, serializable working state with different scopes, and searchable cross-session memory are distinct. | Keep Run History, current step state and reusable intelligence separate. A durable state service does not prove a fresh harness process, an exact input manifest or independent task acceptance. |
| [SKILL.state](https://arxiv.org/html/2608.26263v3), Google and Purdue affiliated researchers | Each **model turn** receives an immutable procedure, current structured state and latest observation. The model proposes a patch and action; a deterministic runtime validates the patch and keeps the updated state, omitting prior reasoning from future prompts. | This can be a state-visibility policy within a Loop and can compose with a fresh process for the next Loop. It does not itself start a new operating-system process each turn. The [existing v3 review](LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md) and [cache-economics note](SKILL-STATE-EXECUTION-AND-CACHE-ECONOMICS.md) already cover the paper, so this record adds the process-versus-state comparison rather than repeating its full survey. |
| [CAFE(S)](https://research.google/pubs/cafes-your-agent-is-only-as-good-as-its-context/) | Clarity, actionability, fidelity, efficiency and security define desirable context quality. | It is explicitly a definition, not a measurement system. Turn each dimension into a task-specific review question and negative example before using it to compare packages. |
| [Google Agent Executor](https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime) and [source](https://github.com/google/ax) | Declarative task, workspace, gateway and model resources; sandboxing, event log, snapshot/resume, single-writer state, connection recovery and branching. | Strong substrate and competitor for customer-owned execution. Its preview status and cluster requirements make it a design or future engine candidate, not a currently qualified Loop Engine executor. It does not document the complete per-focused-step selection and loaded-material proof being proposed here. |
| [ReasoningBank](https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/) | Extracts lessons from successful and failed agent experience. | A source of learning ideas. Self-assessed lessons must remain candidate intelligence until an independent Loop Engine process approves exact bytes and validity scope. |
| [EnvHarness](https://arxiv.org/abs/2608.19880) and [source](https://github.com/google-research/envharness) | Composes Setup, Rule and Link wrappers at an environment's reset and step boundary while retaining the original evaluator. | A reusable evaluation pattern for fresh rollouts and altered tool environments, not evidence about process-per-step execution. |
| [Agentic retrieval with a sufficient-context check](https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/) | Iterative search and a later check that gathered evidence suffices for a query. | A comparator for Baltor's proposed search relevance floor and honest no-result answer. It does not settle native loading or complete task acceptance. |

The [SKILL.state paper](https://arxiv.org/html/2608.26263v3#S5)
reports, for its 100-turn warehouse task with Gemini-3-Flash over five seeds,
0.94 action accuracy and 65,408 cumulative tokens against 0.91 and 1,062,387
for its transcript-plus-state prompt baseline. Its measure is action accuracy,
not a completed customer task, and the baseline is a prompt construction
used by the authors, not a benchmark of the LangGraph product. The paper
does not report provider cache reads, cache writes, dollars, process start-up
or direct latency. Its own [limitations](https://arxiv.org/html/2608.26263v3#S7)
include unknown schemas, information found important only later, history
itself as the task, and untested concurrent writes. At 25 turns in its
simulated repository, state-only scores below the transcript-plus-state
comparator. These facts support testing state visibility; they do not prove
universal token, quality or small-model savings for Baltor.

One further inference deserves a negative control: the paper's published
algorithm validates and applies a proposed state patch before executing its
action. If the action fails or has an unknown external effect, intended state
could lead observed world state. Keep proposed transition, effect result and
trusted state revision distinct; commit a trusted revision only after the
required reconciliation and check. This is a question for an experiment,
not a reproduced paper defect.

A clean comparison crosses **process lifecycle** (continuing or freshly
started harness) with **model-visible state** (full transcript, verified
state only, or verified state with selected evidence-backed history). Use
the same task, model, tools, permissions and evaluator. Include facts that
become relevant late, an unseen task needing a new state field, a task whose
output is an audit of its history, a failed or uncertain external effect,
conflicting state patches and adversarial observations. Count accepted and
false-accepted work, cache and fresh tokens, all calls, process bootstrap,
elapsed time and cost per accepted task. Retain complete immutable Run
History even when the next harness sees only a narrow reference or state.
The existing [passive state-context compiler](../../src/loop_engine/core/skill_state_context.py)
recognizes state-insufficiency cases; its current product prompt integration
is explicitly unqualified in [architecture.yaml](../../architecture.yaml).

## Handbook and public explanation handoff

No tracked file in this checkout was titled “Baltor System Handbook” or
contained an “At a glance” section at this review. Claude Code may have that
artifact in an active, uncommitted session. The exact handbook prose needs
the artifact before line-by-line review. The following is proposed summary
copy, not a replacement for the required
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation):

> Baltor combines a hosted library of approved harness material with a local
> engine that coordinates the customer's harnesses and models. It is for
> developers, teams and agentic systems. In the default design, the engine
> divides work into focused steps and starts a new harness for each step.
> Each harness receives the context, instructions, skills, tools, reusable
> code and working files selected for its assignment. Typed contracts,
> budgets, permissions and Run History carry work between steps without
> carrying the whole conversation into every harness. The hosted service
> currently supports authenticated search and exact downloads; complete
> per-step native execution is still being qualified.

The proposed north-star paragraph is:

> Make coding harnesses and multi-agent systems as capable and efficient as
> possible on unseen tasks. The long-term ambition is a frontier harness or
> multi-agent fabric for software, research, data and other domains.
> Efficiency means independently accepted results within the customer's
> quality, budget and permission constraints. For each focused step, the
> system aims to select sufficient context, qualified reusable code, tools,
> a decision method and the right model or models, so smaller customer-run
> models can finish more work, including long runs overnight. Reusable
> solutions, lower costs and overnight completion are benefits to measure.

The [repository instructions](../../AGENTS.md) carry this north star. The
[README](../../README.md) was updated during this research and now opens
with the corrected north star and a section on one fresh harness for each
step. The exact handbook artifact remains to be compared with that new
source. Claude should still verify the README's current quickstart against
the [harness-first retirement decision](../architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
before making a current-behavior claim. The local
[How it works source](../../src/loop_engine/core/service_runtime/web_assets/index.html)
is under concurrent development; check its latest text and release before
deciding whether it clearly labels the planned separate coding-tool run for
each step, scopes today's connector claim, and separates present and future
benefits. S-6.33 and S-6.34 own that editorial and release work.

An outside-reader test should show only the summary or homepage first.
Ask the reader to explain who runs the model, what Baltor provides today,
what fresh per-step harnessing means, what remains planned, and the next
setup action. Preserve misunderstandings as findings before observing a
real client setup. [Google's People + AI Guidebook](https://pair.withgoogle.com/chapter/mental-models/),
[Nielsen Norman Group's progressive-disclosure guidance](https://www.nngroup.com/articles/progressive-disclosure/)
and [Y Combinator's pitch guide](https://www.ycombinator.com/blog/how-to-pitch-your-company/)
support a clear user path and correct mental model. None substitutes for
observing Baltor's own readers.

## Research decision for Claude Code

The immediate comparison priority is fresh per-step process versus a native
fresh-context subagent and a persistent lead-and-sidekick, under the same
accepted-work standard. The commercial baseline must also include Tessl,
Vercel Skills and Augment Context Engine for material delivery. A versioned
model-call strategy is a related, separate study in the companion
`MODEL-CALL-STRATEGY-AND-DISAGREEMENT-2026-09-22.md` record. No competitor
account, model call, publication or file transfer was performed here.
