# Cross-functional harness and launch review

Kind: dated primary-source research, local readiness audit, and proposed work.
Reviewed September 22, 2026. Local `main` revision at the start was
`e80cf41b0e553cd250410abe350d70c5ef90d033`, with existing concurrent
edits. This record extends the earlier [ZCode and market review](ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md).
The [roadmap](../roadmap/roadmap.yaml) remains the only task authority. The
product stages and experiments below are proposals, not implementation
status, a release forecast, or permission for a model call, purchase,
publication, or provider change.

## Readout

The immediate product test is one person outside engineering completing a
real task with approved material in their own harness, with the offered,
fetched, loaded, used, and independently verified states kept separate.
Current research finds strong free substitutes for documentation retrieval
and temporary skill loading. A large count of generated files would show
production capacity, not usefulness, safety, or willingness to pay.

The engineering base is substantial, but the current release evidence does
not support a public paid launch. The generated status has eight unverified
public release gates. On September 22 at 21:39 UTC, read-only requests found
all four public hostnames answering a homepage request. The
[health response](https://app.baltor.ai/api/v1/health) said `healthy: true`,
`readiness_checked: false`, and `deployed_provider_qualification: false`.
The [capabilities response](https://app.baltor.ai/api/v1/capabilities) said
`registration_available: false`, accepted only Model Context Protocol
`2025-11-25`, and reported browser identity and client access as available.
Its billing capability flags do not establish a completed customer payment:
an unauthenticated read of `/api/v1/billing/plans` was refused, and the
roadmap records no completed test checkout and webhook lifecycle. A `HEAD`
request to the root hostname returned 404 while `GET` returned 200, matching
an already recorded S-6.33 repair.

The latest GitHub `main` at the audit was `2d8bc9f28422d0decaf1cd2630b2601140a56d8d`.
Its [continuous integration run](https://github.com/alisonjieli-png/loop-engine/actions/runs/35774159081)
failed on Python 3.10, 3.11, and 3.12. The logged failures included one
unresolved documentation link on all three versions and an additional
removed-nesting-limit control on 3.12. Local `main` was one commit ahead and
had concurrent edits; 126 local branch refs existed. The branch count alone
does not say how many changes remain to merge. S-6.29 owns reconciliation
before a release. These observations are a point-in-time audit, not a claim
about what Claude Code's pending repairs will achieve.

## Runtime boundary used for this review

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

A harness, protocol adapter, skill, plugin, source harvester, search engine,
and reviewer are components or mechanics used by a classified Loop. They do
not create another executable graph vertex. A new engine belongs behind an
existing versioned edge with eligibility, evidence, and effect authority
kept distinct. The [harness-first decision](../architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
governs what the current main line serves and how steps are delegated.

## How much remains before launch

The [generated continuation status](../roadmap/CONTINUATION-STATUS.md)
contains 59 continuation steps: 23 marked building, 35 proposed, and one
offline verified at this audit. Those are planning states, not a percentage
of finished product. All eight public release gates still say not verified.
The narrower D-17 invited beta is a separate milestone. It requires a
committed checked release, personal keys, an approved starter catalogue,
native client loading, two people outside engineering, and rollback practice.
Its stated authority excludes live charges and model calls. The opening
[repository instructions](../../AGENTS.md) also describe a checked step in
the customer's own harness as a private-beta target. The D-17 acceptance
cases explicitly test native loading but do not by themselves demonstrate a
model-backed useful task. Resolve that difference with a deterministic checked
step under existing authority or a separately authorized model-backed proof;
do not report a download or file listing as the stronger result.

| Gate or near-term dependency | Current evidence | Completion evidence still needed |
|---|---|---|
| Main line and release | GitHub continuous integration is red; local and remote main differ; consolidation is running. | Restore the missing link and removed-guard checks, merge or prove contained every branch change, pass continuous integration on the committed revision, deploy by digest, and check every hostname. S-6.29, S-6.35. |
| Invitation and account | Public registration is off; browser identity and client access are advertised by the live capability record. | Working invitation request, operator invite, personal key issue/revoke, disabled-account refusal, and two outside-user journeys on the same deployed release. D-17, S-6.33. |
| Approved useful library | Local starter review records 123 candidates and 43 approved items. The live authorized body population was not counted in this unauthenticated audit. | Serve the approved bytes with exact grants, licence and digest; verify a selected item in a native client and withdraw a changed or rejected item. S-6.10, D-17. |
| Harness execution | OpenCode has a recorded connection and discovery. The local installer can inspect a native listing. | A fresh, confined harness profile loads selected material, performs one checked step, records all physical calls when a model is used, and survives cancellation and refused effects. S-6.31, S-6.42. |
| Search and relevance | The [local search-quality report](../components/intelligence-layers/SEARCH-QUALITY.md) says all ten unanswerable queries in its 354-query population returned references under the current default. | A served relevance floor and held-out no-result controls that measure false references and lost valid hits together. S-6.32. |
| Billing and customer lifecycle | The owner chose $29 monthly with no launch overage; the monthly included download allowance is unpublished. Local checkout and signed-event checks exist, but the roadmap records no completed provider test lifecycle. | Real sandbox checkout, signed events, reconciliation, cancellation, renewal, expired-access refusal, export/deletion, public terms and privacy text, then separate live-charge authority. S-4.5, S-6.21, S-6.38. |
| Operations and security | A pilot answers publicly; release 12 reportedly needed manual grants and a key reissue. Health does not assert readiness or provider qualification. | Automated grants, current-release restore and rollback, hosted checks on every hostname, multi-process request-limit policy, tenant isolation, retention, and outage drills. S-6.13 through S-6.16, S-6.35. |
| Benefit claims | The [benefit guide](../guides/launch-benefits-and-evidence.md) labels overnight, token, and expertise benefits as drafts. | Matched task populations with and without Baltor, no-skill and raw-source controls, complete calls and cost, independent evaluator, failures, and exact run records before comparative publication. D-07 through D-09, S-6.37, S-6.47. |

The critical path is a checked main line, a complete invited-user journey,
native loading and checked work, then a reconciled paid lifecycle and
operational release. Component counts do not give a defensible calendar
estimate while the current main line is red and provider journeys are open.
Record elapsed time for each completed vertical slice before forecasting a
date. A scheduled launch date should be an output of those measurements.

## Proposed product stages

These are product stages for discussion, not new contract versions. Changing
the existing public release gates requires an explicit owner decision in the
roadmap. Each stage should advance only when its stated customer and evidence
conditions hold.

| Stage | Customer promise | Required proof and existing owner |
|---|---|---|
| V1: invited beta | A person with a supported harness signs in, finds reviewed material, loads an exact item, and finishes a checked step under declared permissions. They can inspect usage and revoke access. | D-17 and D-18: two outside users, one exact native profile, current-source release, rollback, and a recorded result. No live charge. A model-backed task needs its own authority. |
| V2: paid self-service | A person can register, connect, try a bounded free allowance, subscribe to the $29 plan, understand every measured download, manage the account, and cancel or export without operator help. | All eight existing public gates plus D-11 and D-13 through D-16: tested payment lifecycle, durable access, content rights, clean installation, security, support, restore, and independent customer-value evidence. Publish no benefit number without its run record. |
| V3: interchangeable intelligence and execution | Several qualified harnesses and engine choices serve different tasks within customer authority; reviewed material improves from consented outcomes and remains portable across clients. | D-19 through D-23: versioned engine slots, native formats, matched upstream and no-Baltor comparisons, team controls if demanded, role demonstrations, scale triggers, and independent candidate promotion. |

Continuous improvement after any stage follows one loop: observe a real
failure or task gap, preserve it, propose a candidate or engine change,
compare on frozen and held-out work, independently review the result, then
promote only an exact version that passed. The owner decides when a new
family, paid tier, public claim, or effect authority is offered. Research
outputs never approve themselves.

## Why a harness is still unqualified

Qualification belongs to an exact installed version, configuration, model
route, workspace boundary, and task population. A repository, a protocol
listing, or a successful process exit cannot establish all of them.
[Agent Client Protocol version 1](https://agentclientprotocol.com/protocol/v1/initialization)
negotiates capabilities. Its [new-session operation](https://agentclientprotocol.com/protocol/v1/session-setup)
creates a conversation, which need not be a fresh process. Its
[tool-call specification](https://agentclientprotocol.com/protocol/v1/tool-calls)
makes permission requests optional. The [registry checks](https://github.com/agentclientprotocol/registry/blob/main/CONTRIBUTING.md)
check schema and authentication methods, not operating-system confinement,
loaded intelligence, or accepted work.

| Evidence level | Exact check | What may be claimed |
|---|---|---|
| Source candidate | Pin upstream commit, package and binary digest, licence, dependencies, official interface and credential paths. | A candidate exists. |
| Offline compatible | Start a cold process with private home, configuration, cache and workspace. Negotiate protocol and capabilities, refuse unknown versions, probe unlisted instructions and denied file, shell, network, secret and subprocess effects, then cancel. | The exact profile passed the named offline checks. |
| Native material loaded | Offer, fetch, install and ask the client what it listed; then distinguish material loaded into a model turn from material the model used. Bind each observation to the body digest. | One selected item reached the declared stage. |
| Executor qualified | Under separately declared real-model authority, count every physical primary, retry, compaction and auxiliary call. Enforce the outer budget and effects, inject faults, and require an independent evaluator to accept the task output. | One exact executor profile completed a checked task. |
| Customer journey supported | Repeat from a clean customer environment, then compare frozen tasks with the same upstream harness and a no-Baltor arm. Recheck after version or configuration drift. | A supported journey for the tested population and versions. |

The [Agent Client Protocol Python library](https://github.com/agentclientprotocol/python-sdk/blob/main/docs/quickstart.md)
is a reusable typed client/process starting point. A protocol adapter still
needs an external effect boundary because a harness may execute a tool without
asking through the protocol's optional permission path. The current
[TypeScript library](https://github.com/agentclientprotocol/typescript-sdk/blob/main/README.md)
labels version 2 experimental, so an unqualified revision should not be
silently selected.

| Harness or fork | Published path | Qualification decision on this checkout |
|---|---|---|
| [OpenCode](https://dev.opencode.ai/docs/acp/) | Native Agent Client Protocol command. Its [version 2 permission model](https://opencode.ai/v2/docs/permissions) does not automatically make a custom subagent's permission a subset of its parent's. | The pilot has a recorded connection and discovery, not selected-body use or a checked step. Pin the major version and test inherited effects. |
| [Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/security.md) and [SoL-Pi](https://github.com/NVlabs/SoL-Pi) | Pi has extension and process interfaces; its project trust is not a sandbox. SoL-Pi is an optional extension, not a fork. | A narrow text profile has local evidence. Native tools and new-instance isolation remain separate tests. SoL-Pi's published efficiency results cannot be transferred to Baltor. |
| [Codex](https://developers.openai.com/blog/codex-as-a-platform) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code/cli-usage) | Each has a documented scripted path and a community Agent Client Protocol adapter ([Codex](https://github.com/agentclientprotocol/codex-acp), [Claude](https://github.com/agentclientprotocol/claude-agent-acp)). | Existing fixture or documented interfaces do not prove a selected body was loaded in an independently checked step. |
| [Gemini command line tool](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md) | Native Agent Client Protocol, headless output, and an optional sandbox. [Skill documentation](https://geminicli.com/docs/cli/skills/) separates discovery from activation. | The local version/help probes do not qualify a provider route or task result. |
| [ZCode](https://github.com/zai-org/ZCode/tree/872ad960de7ec172591f7e1952f7849229f94521) | Official `app-server`; independent [Rust bridge](https://github.com/jpalmae/zcode-acp/blob/42fe149d4b501469343c01f23ba3801832306d53/README.md) and [TypeScript bridge](https://github.com/william0wang/zcode-acp/blob/d23459a21fb93e29a1aeb6862fc0b71b9d2c1511/README.md). | No Loop Engine native run or exact-effect test. The `--prompt` default mode found in source cannot be assumed to govern `app-server`; test each path independently. |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/ade4814466f9b535d0cb549da893d3517b6f9b2b/website/docs/user-guide/features/acp.md) and [OpenClaw](https://docs.openclaw.ai/tools/acp-agents) | Hermes documents native Agent Client Protocol and separate auxiliary usage. OpenClaw runs external agents and serves the protocol itself. | Their exact current client and executor profiles need new native tests. OpenClaw's [session visibility defaults](https://docs.openclaw.ai/gateway/config-tools/sessions-and-subagents) require a cross-user isolation control. |
| [Kilo](https://github.com/Kilo-Org/kilocode/blob/27cb2de314017ca26d25f1e9f2df7ba79fba7c6a/AGENTS.md) and [OpenHands Agent Canvas](https://github.com/OpenHands/docs/blob/main/openhands/usage/agent-canvas/overview.mdx) | Kilo is an OpenCode fork whose worktree sessions may share a backend process. Agent Canvas is a current interface and protocol client reference; [OpenHands-CLI](https://github.com/OpenHands/OpenHands-CLI/blob/954f2ba646e8d749261a8f2b2b7e3031fa39be9f/README.md) says it is no longer maintained. | A worktree or session identifier is not evidence of fresh process state. Prefer a measured adapter before carrying a permanent fork patch set. |

The earlier [ZCode review](ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md)
said no official Agent Client Protocol implementation was found. The two
community bridges above are real candidate paths. Neither is official Z.ai
support or a Loop Engine qualification. The exact `app-server` effect and
context behavior remains to be tested.

### Adapter, extension, fork or a Baltor harness

The [branch decision](../architecture/BRANCH-STRATEGY-2026-09-21.md) directs
the current main line to delegate every executable step to a standard
harness, with the older custom execution path frozen for possible later use.
The owner's S-6.50 direction also asks for OpenCode and Pi forks. Those forks
should be measured against their pinned upstream versions rather than being
assumed better. [Kilo's fork instructions](https://github.com/Kilo-Org/kilocode/blob/27cb2de314017ca26d25f1e9f2df7ba79fba7c6a/AGENTS.md)
show a concrete upstream-sync and shared-process-state burden.

| Choice | Benefit for Baltor and a customer | Cost and admission rule |
|---|---|---|
| Native adapter to upstream harness | Fastest path to the customer's existing interface, updates and model integrations. It can carry exact material and outer Loop authority through one edge. | An upstream change can alter permissions, context loading or usage records. Qualify each version/profile with the ladder above. |
| Optional extension or plugin | Adds material search, load or context behavior with a smaller patch than a fork. The customer keeps familiar upstream releases. [SoL-Pi](https://github.com/NVlabs/SoL-Pi/blob/1559b5cb12c72da4a485bc50fe326586b216fb19/README.md) illustrates an opt-in Pi extension. | It inherits the host's limitations and its own data flows. Record the extension set and compare with plain upstream on the same tasks. |
| Maintained fork | Can change process lifecycle, context loading, model handling and native presentation when the public extension surface cannot. | Baltor owns security fixes and upstream merges. Require a specific unmet contract, a small recorded patch set, a merge procedure and matched accepted-work improvement. S-6.50 owns the planned OpenCode and Pi experiments. |
| Baltor-built harness | Could eventually give exact per-step bootstrap, native context accounting, tool mediation and instrumentation without another project's release schedule. Customers could keep models and files under their control. | This is the largest maintenance and security commitment. Implement it later as one executor engine behind the existing `HarnessProcessSpec` edge, with the same Loop authority and evaluator. It must beat or serve a gap the qualified upstream options cannot. It creates no new Loop runtime type. |

A minimal future Baltor harness engine would need a cold process with scoped
home and workspace, typed assignment and selected files, a versioned model
route, a tool and effect broker outside model text, bounded resource and
network policy, cancellation, checkpoint and exact output/usage records.
The independent task evaluator and candidate promotion remain outside that
harness. A customer's benefit is conditional: lower cost, better recovery or
stronger privacy must be shown on matched tasks, including the extra process,
retrieval and verification overhead. [SoL-Pi's paper](https://arxiv.org/abs/2609.20519)
reports lower token traffic in its own tested configuration; it does not
qualify a Loop Engine fork or customer saving.

## Computer science and external evaluations worth reusing

The theory supplies questions to test, not an automatic routing rule.
[Information Bottleneck](https://arxiv.org/abs/physics/0004057) and
[rate-distortion theory](https://ieeexplore.ieee.org/document/5311476)
depend on a declared target and loss. There is no task-independent exact
context length. [Blackwell's comparison of experiments](https://projecteuclid.org/journals/annals-of-mathematical-statistics/volume-24/issue-2/Equivalent-Comparisons-of-Experiments/10.1214/aoms/1177729032.full)
lets an ideal decision maker ignore free extra information. A bounded model
may instead be distracted, slower, or more expensive. Compare empty, selected,
compressed, and full context under the same executor and independent task
check, including cases where adding information helps.

| Source and evidence limit | Discriminating Loop Engine study |
|---|---|
| [Selecting Computations](https://arxiv.org/abs/1207.5879) and [Pandora's AI Model Routing Box](https://arxiv.org/html/2608.20316) price the act of inspection. The newer paper's estimator assumptions need validation here. | Compare never inspect, always inspect, and staged inspection where a diagnostic changes the best action, cannot change it, or is too costly. Include the diagnostic's own model calls and time. S-6.30, S-6.58. |
| [Doubly Robust Policy Evaluation and Learning](https://arxiv.org/abs/1103.4601) addresses partial feedback from only the chosen action. | Record eligible alternatives and assignment probabilities in an authorized comparison. Use the same independent evaluator. Mark an untried task region unknown rather than estimating a winner from chosen-route history. S-6.30, S-6.41. |
| [Optimal Skill Selection](https://arxiv.org/html/2608.19993) proves a set-selection guarantee under a fitted monotone-submodular benefit, fixed executor, bounded fitting error, and linear token penalty. Real success may need two complementary items together. | Compare an empty set, singletons, a useful pair, a redundant pair and a distractor before using a set-aware selector. A strict two-skill dependency is a negative control for assuming diminishing returns. S-6.32, S-6.47. |
| [Agent Retrieval Bench](https://arxiv.org/html/2607.24882) includes natural no-gold and wrong-repository controls. Its [MIT evaluator](https://github.com/eyuansu62/agent-retrieval-bench/tree/07014c986f3deadb1548c62b32c0ffbe6a81465d) leaves source-corpus licences with upstream owners. | Measure false references, missed valid items, repository-macro relevance, and useful spans by query family. A raw top-score threshold alone is not a qualified abstention rule. S-6.32. |
| [ContextBench](https://arxiv.org/html/2602.05892) finds cases where an agent inspected relevant code without using it in its patch. Its [code](https://github.com/EuniAI/ContextBench/tree/1436c28a8eb95496da4ea69ad458b9f8a8eb7d61) is Apache 2.0. | Record retrieved, viewed, retained, used and verified separately, then test accepted patches. S-6.41, S-6.47. |
| [Agent Skill Security](https://arxiv.org/html/2607.13987) studies attacks across admission, retrieval, selection, execution and updates. | Inject misleading metadata, changed body under an old digest, unsafe effects, and malicious composition. Each existing gate must refuse its own known-wrong case. S-6.45. |
| [Same Signal, Opposite Meaning](https://arxiv.org/html/2605.06908) reports that uncertainty can predict helpful or harmful extra work in different settings. | Randomize extra compute under declared authority across task and executor strata. Learn the sign of later accepted-work improvement; do not make high uncertainty a universal continue rule. S-6.58. |
| [Managing Procedural Memory in LLM Agents](https://arxiv.org/html/2606.23127) distinguishes local skill improvement from transfer across roles and model backbones. | Compare no skill, original skill, and revised skill on source and held-out tasks, roles, and models. Retain negative transfer. S-6.47. |
| [Scaling Discovery through Test-Time Communication](https://arxiv.org/html/2609.21032) compares independent attempts and shared progress under task-specific feedback. | Compare one worker, independent attempts, and typed shared discoveries at matched total calls, tokens, time and evaluator access. Include low-feedback tasks where communication can lose. D-19. |
| [RoadmapBench](https://github.com/UniPat-AI/RoadmapBench/tree/9bbc3432d9cd36061c0286ac16a786c4e3bafe52), [ProgramBench](https://github.com/facebookresearch/ProgramBench/tree/b08d8621031f5f5abc4d3ffc2950256c83fbfe42), and [AgentCompass](https://github.com/open-compass/AgentCompass/tree/eb7dd3d222504a4f12a0323b6280ed2480354baa) offer external long-horizon and evaluator code. Package and task-artifact rights differ. | First audit hidden-answer access, task licences, known-wrong patches and evaluator identity. Use a preregistered subset; never translate a published score into a Loop Engine result. D-07 to D-09. |

All paper outcomes above are author-reported. Different tasks, models,
harnesses, budgets and evaluators prevent a cross-paper ranking. Reuse the
published code only after its exact revision, dependency and data licences
pass the project review. [Agent Retrieval Bench](https://github.com/eyuansu62/agent-retrieval-bench),
[ContextBench](https://github.com/EuniAI/ContextBench),
[AMA-Bench](https://github.com/AMA-Bench/AMA-Bench), and
[Harbor](https://github.com/laude-institute/harbor) are candidate external
evaluation tools, not admitted runtime dependencies.

## Competition and commercial positioning

Published prices compare different units. They are useful for a buyer's
alternatives, not a head-to-head outcome claim. On September 22,
[Context7](https://context7.com/plans) listed 1,000 public-documentation
calls free and $10 per seat monthly for 5,000 included calls;
[Mintlify Index](https://www.mintlify.com/blog/mintlify-index) described a
free beta for documentation retrieval;
[Vercel Skills](https://github.com/vercel-labs/skills/blob/7407f3893ad4dceab546ac002c3ef806e4000c73/README.md)
documented temporary skill use without installation. [Tessl](https://tessl.io/pricing)
already sells skill review and evaluation credits. [Cursor](https://cursor.com/en-US/pricing)
includes model access in plans and offers [private team plugin distribution](https://prod.cursor.com/docs/plugins).
The first Baltor plan charges for reviewed material delivered to the
customer's own harness, while the customer pays separately for model use.
The owner's $29 monthly price therefore needs an observed task benefit and
a visible included download allowance. A directory or format validator alone
is unlikely to demonstrate that value. This is an inference, not a measured
purchase decision.

The [official Model Context Protocol Registry](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/about.mdx)
publishes public server metadata and delegates code security review. It is a
discovery source for a public connector, not a private body store or an
independent qualification badge. [Claude Code community marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
support pinned plugin sources and authenticated archives; automatic
[plugin recommendations](https://code.claude.com/docs/en/plugin-hints)
have a narrower curated-partner route. [GitHub Marketplace](https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app)
requires a verified organization and an existing installation population
before a paid app listing. These facts favor a source-visible connector and
entitlement-bound private material, with marketplace distribution qualified
after the native journey works. [Apify](https://docs.apify.com/actors/publishing/monetize)
already monetizes executable creator items, so a later creator marketplace
would enter an existing category.

## Stakeholder questions that should shape decisions

| Lens | Decision this person must make | Evidence to bring to the decision |
|---|---|---|
| Chief executive | Which first buyer and repeat task will the product serve well enough to earn return use? | Choose one real task family from overnight tickets, data cleanup, or another observed demand. Show a customer using it twice with accepted results before widening the public promise. |
| Chief technology officer | Can a fresh harness actually receive only its selected inputs and remain within cumulative authority? | Exact-version process, home, cache, network, credential and subprocess isolation; optional protocol permissions challenged with denied-effect controls; independent acceptance and cancellation. |
| Chief financial officer | Does the $29 plan cover delivery, review, support and acquisition costs? | Per-account monthly contribution equals collected revenue less payment and refund loss, identity and email, search/storage/egress, support, and amortized item review and refresh. Customer-paid inference is separate from Baltor-paid qualification calls. At a $29 domestic card charge, [Stripe's published standard fee](https://stripe.com/pricing) alone is about $1.14, leaving about $27.86 before all other costs, taxes, discounts or disputes. Measure the actual payment mix. The [Fly price schedule](https://fly.io/docs/about/pricing/) lists machine, volume and outbound-data charges; no account margin is inferred from its list prices. |
| Chief marketing officer | Which channel brings people who reach accepted work and return? | Track visitor, invitation, key, exact native load, independently accepted result, repeated result, and paid renewal as separate funnel events. Consent is required before local task details enter hosted analytics. S-6.59 already owns human-approved replies; do not count clicks as utility. |
| Product and interface designer | Can a first-time person predict the next step, understand the status and recover from failure? | Observe outside users at the live site. Show delivery states and unknown outcomes clearly, explain one key name and one charge unit, and keep advanced engine choices behind a clear next step. [Nielsen Norman Group's status and error guidance](https://www.nngroup.com/articles/ten-usability-heuristics/) and [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) are design references, not evidence that the present page passes usability tests. |
| Security and privacy reviewer | What crosses the customer's boundary, who can authorize it, and how does a revoked or changed item stop? | Exact source and destination, scope, consent, retention, credential references, body digests, licence and effect declarations; withdrawal, tenant isolation and malicious-skill controls. Unknown source rights block redistribution. |
| Individual developer | Can the supported harness use one helpful item without setup surprises or an extra model bill from Baltor? | Clean install, versioned instructions, one visible item, native loading and checked output; explicit model-provider cost and local-file boundary. The person can revoke a key and inspect the measured download. |
| Team buyer | Can access, sharing, updates, spend and offboarding be governed without leaking one member's work? | Team and tenant permissions, account export, deletion, audit records, per-user keys and expiry, shared-item policy, and actual demand for a team pool before a second plan is proposed. |
| Investor or venture fund | Why can a free directory, model vendor or harness not provide the same value? | Repeat accepted work, a measured no-Baltor and free-source comparison, conversion and cohort renewal at the actual price, fully loaded content and support cost, and the exact defensible data rights. File count, benchmark headlines and a broad market estimate are insufficient. |
| Y Combinator reviewer | What does the company do today, who wants it, and what has the founder learned? | [Y Combinator's application guide](https://www.ycombinator.com/howtoapply) asks for clarity, concrete founder work and a credible first foothold. Its [frequently asked questions](https://www.ycombinator.com/faq) do not require revenue before applying. The [Winter 2027 on-time deadline](https://www.ycombinator.com/apply) is November 2, 2026 at 8 p.m. Pacific. The honest present account is a live operator-key pilot with the invited beta and native task proof pending. S-6.36 need not wait for paid launch. |
| Partner or source maintainer | Is the integration useful, attributed, maintainable and safe for their users? | A pinned source-visible connector or original co-authored item, exact licences and update route, one verified native load, a no-item comparison and a person responsible for breakage. A logo or registry entry does not prove partnership or benefit. |
| Operator | Can an outage, billing event, bad catalogue item or rollback be resolved without guessing? | Current release/image identity, deployment checks on each hostname, durable usage reconciliation, known unknown-commit behavior, item withdrawal and customer support path. |

For customer discovery, use a person's last real task, their current method,
the failure or cost, and the decision they would change before showing a
demonstration. Watch them connect and work with little help. Ask for a
purchase decision against actual terms only after use. This follows
[Y Combinator's guidance to build and talk to users](https://www.ycombinator.com/blog/ycs-essential-startup-advice/).
The first two outside users are already part of D-17; their obstacles should
be recorded in the roadmap. A broader design-partner cohort follows a
working first-use path, with all refusals and abandonments retained.

## Acquisition, partnerships and evidence sequence

1. Publish one honest, runnable task story: exact harness and model versions,
   permitted material, checked result, cost state, failure cases, and a matched
   no-Baltor arm. D-23 and S-6.37 already own demonstration pages and their
   records. The page should speak to one developer job, with internal runtime
   terms kept in technical documentation.
2. Make a public connector and sample material easy to inspect and install in
   compatible harness channels. Keep premium bodies behind authenticated
   retrieval. Measure channel visits through verified native load, repeated
   accepted work, and eventual renewal. Official registries and marketplaces
   distribute metadata or plugins; each has its own review and listing rules.
3. Contribute compatibility fixes and original licensed examples to the
   harness or domain communities whose users actually complete a task. A
   possible partnership begins with a recorded interoperability result and
   maintained update path. Do not infer endorsement or sales from an issue,
   listing or contribution.
4. Use S-6.59's human-approved, useful replies and role-specific pages after
   the site provides a working invitation and clear next step. A person
   approves and posts every message. Delay paid acquisition estimates until
   the first cohort's contribution and renewal are measured.

The founder can describe the long-term frontier fabric ambition to an
investor as research direction. Public task, savings and overnight claims
remain bounded by the [benefit evidence guide](../guides/launch-benefits-and-evidence.md).

## A candidate factory for thousands of harness intelligence files

The right initial scale target is a thousand **review-only candidates** with
measured provenance, duplicate rate, format quality and review workload.
It is not a thousand served or useful items. The current starter folder
records 123 candidates and 43 approved bodies. Three independent reviewers
judged the initial 49. The [release builder](../../tools/build_host_catalogue_manifest.py)
reads their exact decisions and body digests before serving anything.

| Existing path | What it actually does | Limit that a factory must preserve or repair |
|---|---|---|
| [Candidate staging](../../tools/stage_intelligence_candidates.py) | Atomically stages at most 50 records into a new isolated database and proves normal search excludes candidates. | It stages four-layer review records, not hosted harness publication, and the command cannot resume a partly staged population. |
| [Starter refresh](../../examples/29_intelligence_service/starter-catalogue/refresh.py) | Recomputes body-derived digests and 50-row population files. | `items.json` pins every cited source to one exact Loop Engine revision. An external repository cannot be represented as though it were a file in that revision. |
| [Harness reference](../../src/loop_engine/core/harness_intelligence.py) | Defines a typed item with family, kind, source, licence, effects, tags, digest, size and lifecycle. | A reference and a text body are not a multi-file executable skill package. |
| [Native installer](../../tools/install_selected_material.py) | Builds an Agent Skills frontmatter file from a served plain-Markdown body and checks OpenCode's native listing. | Validate the rendered `SKILL.md`, not only the stored body. Other file kinds and scripts/assets need their own typed package and native placement. |
| [Occupation seeds](../../src/loop_engine/core/seeded_generation.py) | Emits candidate questions, facts and code seed specifications from declared occupations. | It is parked on the harness-first main line and does not generate complete native skills. Restore only behind an approved boundary. |

The proposed source-to-review procedure belongs to S-6.40, S-6.45, S-6.53
and S-6.54. It uses the current catalogue and review builder as authorities:

```text
Source discovery and inventory
  -> licence and exact-version record
  -> bounded fetch into quarantine
  -> extraction and source-grounded original candidate
  -> exact and near-duplicate review
  -> typed harness-item reference and rendered native file
  -> format, safety, contract and task tests
  -> independent review of exact bytes
  -> existing approved host manifest
  -> native load and accepted-work measurement
```

For discovery, prefer the [official Model Context Protocol Registry interface](https://modelcontextprotocol.io/registry/about)
and [GitHub's versioned contents interface](https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28)
to scraping rendered pages. Save repository, commit, path, source digest,
fetch date and provenance for every body. A website fetch needs a declared
source permission and [robots policy](https://www.rfc-editor.org/rfc/rfc9309.html),
bounds on bytes, time, requests and redirects, and an honest failed-fetch
state. Discovery and fetch do not execute source code. GitHub's
[licence interface](https://docs.github.com/en/rest/licenses/licenses)
identifies a repository licence file but explicitly does not cover dependency
or every per-file licence. Unknown or incompatible rights block verbatim
redistribution. Scan results can help triage, but a licence decision must
preserve the exact evidence and attribution.

For normalization, use a stable candidate key derived from source origin,
source revision, path, source digest and normalizer version. Keep fetched
bytes separate from authored body bytes and record both digests. A changed
source creates a new review subject. Batch writes are at most 50 items,
with a cursor advanced only after an acknowledged atomic write and readback.
A rerun of identical input should make no new record; a changed record or an
unknown commit must refuse automatic continuation. A new per-source
provenance contract is required before external material can flow into the
current `starter_catalogue_candidate_items/v2`, which assumes one local source
revision. Do not place an outside commit into that local field.

For output, begin with text-only `SKILL.md` candidates and run the official
[Agent Skills specification](https://agentskills.io/specification) and its
`skills-ref` validator on the **rendered file**. The specification requires
frontmatter name and description with exact naming and size rules; a skill
may also contain scripts, references and assets. The current served body and
OpenCode installer do not establish those additional files' delivery or
execution. Instruction files, plugin bundles, protocol server settings and
reusable code likewise need versioned package contracts and client-specific
load tests before being listed as supported. A linter checks names, paths,
links, source identity, declared effects, secret patterns, dependency and
licence evidence, exact duplicates, near duplicates, malicious instructions,
and whether the description routes a real task to the right item. Scanner
output is triage for independent reviewers, never approval. The
[Agent Skill Security study](https://arxiv.org/html/2607.13987) motivates
controls across admission, retrieval, selection, execution and updates.

For the first throughput test, construct twenty temporary populations of
fifty synthetic, locally owned proposals. Stage them through the existing
candidate contract, confirm each acknowledgment and readback, rerun without
creating duplicates, change one source byte to require a conflict, and show
normal search never serves the candidates. The test should report elapsed
time, bytes, duplicate findings, refused rows and unresolved writes. It
proves batching, not useful intelligence. Task-value tests then compare each
reviewed item with no item and its raw source on frozen tasks; include cases
where it hurts. S-6.47 owns that comparison.

### Titles, dimensions and generated systems

Use a title of the form **verb + object + practical scope**, such as
"Profile a text column before cleaning." The description names the trigger,
result and important limit. A role label alone must not create a new item
when the method and checks are the same. A generated candidate needs one
grounded source or an explicit original-work rationale, a typed task, a
known-wrong example, a testable check and a declared effect list. Those
requirements should reject a polished but generic file.

The current [tag set](../../src/loop_engine/core/intelligence_tagging.py)
has role, domain, geography, language, sensitivity, authentication and
lifecycle. S-6.53 proposes seniority, company, time period, skill level and
model axes. Keep different kinds of dimension in their owning records:

| Dimension family | Examples | Owning decision and test |
|---|---|---|
| Applicability | Task, role, domain, geography, language, seniority, relevant time period. | Search and coverage may filter on declared values; an item general on an axis stays general. An occupation-specific title with no occupation-specific behavior fails the specificity check. |
| Compatibility | Harness and version, operating system, package dependencies, model capability, file kind, native layout. | A client may receive only a format it actually loads at an exact tested version. A documented format is not a successful load. |
| Authority | File, command, network, secret, external mutation and spending permission. | Typed policy controls effects; tags and prose never grant authority. A skill claiming broader permission must be refused. |
| Source and rights | Origin, immutable revision, path, body digest, attribution, licence and update cadence. | Changed or unknown source evidence returns the item to candidate review. Repository-wide licence detection cannot stand in for a conflicting file notice. |
| Evaluation | Task population, model, harness, verifier, no-item and raw-source arms, failure, token and cost state. | A score belongs to its exact tested context; unmeasured stays unmeasured and negative transfer remains visible. |

The full Cartesian product of occupations, countries, models and seniority
levels would manufacture duplicates and consume review effort. The proposal
is sparse generation ordered by observed task demand, missing coverage,
licence availability and measured benefit, with a separate queue for unknown
demand. [Optimal Skill Selection](https://arxiv.org/html/2608.19993) is a
reason to test useful sets and interactions, not permission to infer that
every generated combination is valuable. The owner-specified dimension
inventory in [the configuration requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
remains a baseline. Any new runtime choice needs an initial setting, ordered
fallbacks, owning boundary and a test that distinguishes it from a label.

## Repeatable developer research

The repository already has dated research records, a generated
[records index](../RECORDS-INDEX.md), a single roadmap and reproducible
status views. A source watcher can add change detection without becoming a
second task list: validate a list of primary URLs and pinned repository
revisions offline; on an explicit bounded online run, record changed,
unchanged, inaccessible and uncertain sources in a **new dated report**.
Human review decides whether a changed page alters a fact, experiment or
roadmap evidence. A paper, repository star count, vendor price or registry
listing never auto-promotes an engine, intelligence item or public claim.

The source record should hold the URL, retrieval date, immutable revision or
page validator, code and data licence state, exact author claim, task
population, model and evaluator, applicability inference, Loop Engine owner
step and a falsifying test. A scheduled scan may later queue offline checks
for changed versions. It needs bounded requests and no credentials, model
calls, publication or roadmap mutation. An exact live harness or provider
trial still needs its own declared authority. The new source-watch tool and
its limits are documented in the companion guide once its checks pass.

### Tools prepared during this review

The new [research source watcher](../../tools/refresh_research_sources.py)
uses a [ten-source manifest](../../tools/research_source_watch.json). It
validates offline by default. `--online` makes bounded read-only requests to
an explicit host allowlist and writes a new dated report without replacing a
prior result. Its [guide](../guides/research-source-watch.md) explains that a
changed page hash is a review signal, not a changed product fact. The first
[online report](../../artifacts/research-source-watch/RESEARCH-SOURCE-WATCH-2026-09-22T215538.253225Z.json)
checked all ten sources with no request failure. The tool does not collect
repository bodies or automatically alter the roadmap.

The new [offline candidate preparer](../../tools/prepare_harness_candidates.py)
accepts authored, source-grounded proposals for **committed local repository
files** at the current full revision. It checks exact source and root licence
bytes, confines paths, refuses duplicate identities and an existing output,
and writes candidate Markdown bodies, typed item references and population
files of at most fifty items. It writes no approval or host release. Its
[procedure](../../tools/PREPARE-HARNESS-CANDIDATES.md) gives the input
contract. A temporary synthetic fixture prepared and staged 1,000 candidates
in twenty populations; the existing refresh reader found no stale derived
fields. This is throughput and contract evidence, not a thousand useful or
approved skills. External source import, file-level rights, semantic quality,
multi-file packages and independent review remain unqualified work.

## Homepage review and local repair

The user identified the right-hand example-workflow panel as a break in the
homepage flow. A read-only comparison found the live homepage HTML matched
the local source before this repair, apart from the service-name substitution.
The hero then held about 186 words of left-side explanation and a separate
customer-import illustration on the right. That illustration described a
broader workflow than the live search and selected-download path, with its
"not a live execution" qualification at the bottom. Its visual weight
competed with the working Get started action. This is a direct page
observation and design judgment, not a conversion measurement.

The local repair removes the right-hand panel, shortens the opening copy,
uses one centered text column and moves the three currently available steps
ahead of the capability cards and broader benefits. It retains the owner's
headline and category line, explains the word harness, keeps the price and
customer-owned model-key boundaries visible, and sends the larger illustrative
task to How it works. The new browser check
`homepage_starts_with_the_current_customer_path` failed on the old page
with `hasWorkflowRail: true`, `startBeforeOffer: false` and
`offerBeforeBenefits: false`. The local repair passed 318 of 318 browser
checks and 33 of 33 existing removed-guard controls. Preserve the
[known-wrong report](../../artifacts/architecture-audit-2026-09-19/homepage-layout-known-wrong-2026-09-22-1.json)
beside the [repaired report](../../artifacts/architecture-audit-2026-09-19/homepage-layout-repair-2026-09-22-1.json).
Desktop and mobile images were inspected beside the report in this workspace;
generated browser images are ignored by version control. No changed page was
deployed.

The design draws on [research about overlooked right rails](https://www.nngroup.com/articles/fight-right-rail-blindness/)
and [short first-page attention](https://www.nngroup.com/articles/how-long-do-users-stay-on-web-pages/).
Those sources are design inputs, not proof the new layout converts better.
The next live persona review should ask a first-time developer what Baltor
provides now, what $29 would pay for, which model costs remain theirs, and
what to click. Record errors and abandonment. The long lower page also needs
that observation before further removal or reordering.

The interactive browser control in this Codex session returned an empty app
and browser inventory, and its in-app browser could not open. The
[official OpenAI browser guidance](https://developers.openai.com/es-419/docs/browser?surface=app)
says that surface is available in the ChatGPT desktop application and web,
and is unavailable in Codex command line sessions. The website itself was
reachable, and the repository's existing headless Chrome browser suite ran
the local page successfully. Restoring interactive browser control requires
a supported ChatGPT browser session; this review did not change global browser
settings or install an extension.

## Pickup for the next Claude Code session

1. Preserve the unrelated dirty paths and the active consolidation work.
   Review the new research report, offline source watcher, candidate preparer
   and homepage repair as distinct changes. The roadmap retains the priority
   order and the release authority.
2. Land the main-line and continuous-integration repairs before publishing
   the homepage. Re-run the complete browser and hosted checks on the exact
   committed release, then repeat the persona review. A local browser pass
   does not close a live-site gate.
3. Put the harness qualification ladder into S-6.31 and S-6.42, with a
   pinned first Agent Client Protocol profile and a separate ZCode
   `app-server` trial. A documented bridge, session identifier or process
   exit never counts as native loading or independent task acceptance.
4. Use S-6.40 and S-6.45 for source discovery, rights and candidate quality.
   First qualify the local candidate-preparation path and a synthetic
   thousand-item batch, then design the versioned per-source provenance and
   multi-file package contracts needed for external material. Keep the
   existing independent review and host release builder as the only
   publication route.
5. For the business decision, finish D-17 with outside users, then test the
   exact $29 offer, actual renewal and fully loaded costs. Keep the Y
   Combinator application honest and ready on its own deadline. It need not
   claim that all paid-release gates have closed.

No outreach, purchase, live charge, model-backed competitor run, repository
publication, or live deployment was performed for this review.
