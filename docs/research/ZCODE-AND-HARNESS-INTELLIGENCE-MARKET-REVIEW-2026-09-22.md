# ZCode and the market for harness intelligence

Kind: primary-source research and proposed product improvements. Reviewed
September 22, 2026 against local `main` revision `e80cf41b0e553cd250410abe350d70c5ef90d033`.
No competitor was installed, no model was called, and no paid or hosted customer
journey was run for this review. Claude Code's existing edits and worktrees were
left alone. This record changes no product contract or runtime authority.

This review extends the [September 19 competitor comparison](../../artifacts/continuation-research-2026-09-19/competitors.md)
and [September 20 website review](WEBSITE-JOURNEY-REVIEW-2026-09-20.md).
Those records already cover the broader market and Baltor's first-use gaps.
The new findings here are ZCode's published harness, newly documented
temporary skill loading and free documentation retrieval, and specific tests
for the existing [roadmap](../roadmap/roadmap.yaml). The roadmap remains the
task authority.

## What the evidence means

| Label | Meaning in this record |
|---|---|
| Published documentation | The vendor describes a feature or price. We did not test its account, client, model, or production behavior. |
| Inspected source | The named public revision contains the described code. This does not qualify a packaged binary or a deployed service. |
| User report | A person filed an issue. The reported behavior was not reproduced here. |
| Local observation | A file or roadmap entry in this checkout was read. It is not proof of a live customer journey. |
| Proposal | A candidate improvement with an owning roadmap step and a test that could reject it. |

## ZCode: a client candidate and a complete competing workspace

The official project is [Z.ai's `zai-org/ZCode`](https://github.com/zai-org/ZCode/tree/872ad960de7ec172591f7e1952f7849229f94521),
reviewed at commit `872ad960de7ec172591f7e1952f7849229f94521` from
September 20. Its root package says version 3.14.0. The first-party source is
Apache 2.0, while bundled third-party material has its own notices.
[Repository overview](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/README.en.md),
[notice](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/NOTICE.md).

| Subject | Published or inspected finding | Consequence for Loop Engine |
|---|---|---|
| Product shape | Desktop, browser, terminal, server, and agent runtime live in one repository. `zcode --web` opens a local workspace; nonlocal binding gets an access token by default. [Repository overview](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/README.en.md). | Compare setup, context choice, visibility, and accepted work, not only a model answer. |
| Model access | The application is described as free. The customer supplies a model plan or application programming interface key. The agent favors GLM but documents other provider connections. [Frequently asked questions](https://zcode.z.ai/en/docs/qa), [model configuration](https://zcode.z.ai/en/docs/configuration). | The customer-run harness and customer-paid model split is familiar. Baltor must explain that its $29 plan pays for material access, not model use. |
| Context | The agent reads global and workspace `AGENTS.md`, offers file and conversation references, and has optional project memory. Its source has compaction and old-tool-result clearing policies. [Agent guide](https://zcode.z.ai/en/docs/agents), [compaction policy](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/apps/zcode-cli/packages/core/src/compact/policy.ts). | A fair comparison keeps task, model, provider, tools, and evaluator fixed while comparing a continuing session with a fresh harness for each focused step. The record must include lost constraints as well as tokens and time. |
| Long work | Goal Mode describes a persisted objective, checks after each round, a next action, pause and resume, and a usage budget. This is a vendor description, not an independently checked outcome. [Goal Mode](https://zcode.z.ai/en/docs/goal). | Show objective, current work, next action, remaining authority, and stop reason from the existing Run History. Do not create a second task state. |
| Extensions | Plugins may bundle skills, commands, subagents, hooks, and Model Context Protocol servers. The detail view lists components before installation. [Plugin guide](https://zcode.z.ai/en/docs/plugin), [command line source guide](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/apps/zcode-cli/README.md). | Include ZCode in the format and native-load review. A bundle preview should name exact source, components, effects, licence, version, and digest before selection. |
| Independent instances | Separate-context subagents are documented. Source also exposes `--prompt`, `--target`, `app-server`, and `agent-server` paths. We found no official Agent Client Protocol implementation; [a request for one](https://github.com/zai-org/feedback/issues/571) is open in the vendor feedback repository. [Subagent guide](https://zcode.z.ai/en/docs/subagents), [command line source guide](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/apps/zcode-cli/README.md). | ZCode is an external harness candidate under S-6.31 and S-6.42. Do not list it as a qualified Agent Client Protocol engine. |
| Permission behavior | The interface has four confirmation modes. The noninteractive `--prompt` path defaults to `yolo` in the inspected source, and ordinary tools can pass its permission service in that mode. The notice says the shared agent adapter has no default operating-system sandbox. [Run source](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/apps/zcode-cli/packages/cli/src/run.ts), [permission source](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/apps/zcode-cli/packages/core/src/permission/service.ts), [notice](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/NOTICE.md). | Any adapter needs the existing typed effect authority, confined workspace, budget, cancellation, and independent acceptance outside ZCode. Its mode cannot grant Loop Engine authority. |
| Qualification limit | [A September 20 user issue](https://github.com/zai-org/feedback/issues/744) reports a `--prompt` model-selection failure. It was not reproduced here. | A versioned handshake, real provider call under separate authority, cancellation, usage accounting, and checked output must pass before claiming native executor support. |

ZCode's subagents and Goal Mode remain harness behavior inside a Loop-owned
assignment. A separate, governed semantic assignment uses the canonical
`Loop` runtime and existing executor edge. The vendor's advertised model
performance and long-context capacity are claims, not results measured by
this review.

One exact-context test follows from ZCode's [instruction-file rules](https://zcode.z.ai/en/docs/agents):
it reads `~/.zcode/AGENTS.md` and the current workspace's root `AGENTS.md`,
but does not walk nested instruction files. A candidate fresh-instance
adapter must isolate or declare the global instruction file and optional
project memory, place selected instructions where the client reads them, and
prove that an unlisted sentinel instruction cannot enter the step. A file in
the correct folder is still only an offered or installed file until native
loading and use have been observed.

### A bounded privacy finding

[Users reported](https://github.com/zai-org/feedback/issues/707) broad
workspace snapshot uploads in earlier desktop releases even with indexing
turned off. This review did not reproduce the report. Z.ai's
[version 3.14.0 change log](https://zcode.z.ai/en/changelog) says it fixed
abnormal repository wiki uploads. A read-only search of the inspected public
source under `apps` and `packages` found no `repoSnapshotIndexingEnabled`,
`/snapshot/upload-credential`, or `repo_snapshot_manifest` identifiers.
That search says nothing conclusive about earlier
binaries, server retention, deletion, or the deployed fix. Current official
[wiki documentation](https://zcode.z.ai/en/docs/repo-wiki) says selected code
context is sent to a model service. The [notice](https://github.com/zai-org/ZCode/blob/872ad960de7ec172591f7e1952f7849229f94521/NOTICE.md)
also says requests to two listed official Anthropic-compatible model endpoints
are routed through a ZCode gateway with their body and most headers. The
published client source does not establish that gateway's retention policy.

The product lesson is a proposal: before a customer-authorized transfer, show
the destination, file or artifact scope, purpose, and data policy. Afterward,
record the actual transfer identity and amount. Bind approval to the exact
effect through Loop Engine's existing authority boundary. This is especially
useful for a product that promises customers control over their harness and
model. It is not a claim that Baltor currently offers that interface.

## What competing products already offer

These rows are deliberately different product categories. Their prices are
published terms observed on September 22, not equivalent units of value or
evidence of successful customer outcomes.

| Product | Published offer and price | Meaning for Baltor |
|---|---|---|
| [Context7](https://context7.com/plans) | Versioned documentation through Model Context Protocol. Free plan: 1,000 calls monthly. Pro: $10 per seat monthly with 5,000 calls per seat and $10 per 1,000 additional calls. Private parsing has a separate token charge. | Generic documentation retrieval has a free and lower-priced baseline. The September 19 comparison already records its private-source and trust features. |
| [Mintlify Index](https://www.mintlify.com/blog/mintlify-index) | Announced August 6 as a free beta for documentation search, token-budgeted context, and selected-page retrieval, with web search fallback. | A public-documentation search demonstration alone is weak evidence for a paid plan. Its published evaluation concerns planning tasks, not accepted coding work. |
| [Vercel Skills command line tool](https://github.com/vercel-labs/skills/blob/7407f3893ad4dceab546ac002c3ef806e4000c73/README.md) | Search and installation across several harnesses. `npx skills use <source>@<skill>` temporarily materializes a skill and starts a supported agent. [skills.sh](https://www.skills.sh/docs) ranks by anonymous installation telemetry; [unlisted packs](https://www.skills.sh/docs/packs) can be opened by anyone with their address. No paid access price was found in the consulted documentation. | Just-in-time skill loading already exists. Installation counts are popularity signals, not task-quality evidence. Protected paid bodies need authenticated retrieval rather than an unlisted pack. |
| [Official Model Context Protocol Registry](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/about.mdx) | Public server metadata and publisher namespace checks. The registry delegates code security review and does not host private servers. | It is a discovery source for S-6.40, with its source identity preserved, not a substitute for independent item admission. |
| [Tessl](https://docs.tessl.io/evaluate/evaluate-skill-quality-using-scenarios) | A direct paid skills and evaluation comparison already documented in the [September 19 report](../../artifacts/continuation-research-2026-09-19/competitors.md). Its scenario evaluation can be skipped at publication. | Evaluation tooling is not the same as mandatory independent admission of each item. Baltor must demonstrate its own stronger gate and accepted-work benefit. |
| [Augment Code](https://www.augmentcode.com/pricing) | $20 or $100 monthly team pools for model, Context Engine, and compute usage, for up to 50 seats. | The listed price includes services Baltor does not sell. A simple price comparison would mislead. |
| [Composio](https://composio.dev/pricing) | Hosted tool connection and action service. Free tier lists 100,000 tool calls monthly; Pro lists $29 monthly with usage credit and a standard tool-call overage. | Its unit is an executed tool call. Baltor's first paid unit is a delivered intelligence body. Show the distinction clearly. |

The current [roadmap entry S-4.5](../roadmap/roadmap.yaml) records the owner's
chosen Baltor Pro plan at $29 per month, one downloaded item as the measured
unit, and no overage billing at launch. The included monthly allowance remains
to be published. The first product does not run the customer's model or task.
The [packaging guide](../guides/packaging-tiers-and-hosted-service.md) explains
why a service that only delivers material cannot charge for an independently
verified task completion it did not observe. Its older sentence that prices
are unset is now stale and belongs to S-6.34's documentation cleanup.

The first commercial hypothesis is that reviewed, versioned material helps a
customer complete a real task often enough to justify the $29 plan alongside
their own model costs. That remains unmeasured. Ask invited users about the
actual quoted plan after a checked task, record acceptance or refusal and the
reason, then compare repeated use with the same harness without Baltor. The
model, task population, permissions, budget, and evaluator must match. A
future team pool may be worth testing if several people share one library, but
it is a separate proposal from the owner's single launch plan. The first
dashboard should explain each counted body delivery and the monthly allowance
before considering another billing unit.

## What the Baltor interface already does

A static read of the current [page](../../src/loop_engine/core/service_runtime/web_assets/index.html)
and [browser script](../../src/loop_engine/core/service_runtime/web_assets/service.js)
found task-needs search, a search-policy selector, source and digest details,
licence, declared effects, harness scope, qualification basis, size, access,
and an exact-revision fetch action. Get started already has a supported-client
selector, secret-free configuration, a protocol check, a client check command,
and a first-retrieval walkthrough. Recreating these controls would add little.
This source read does not establish that the live site or a native harness
completed the journey.

Three interface gaps remain useful candidates:

1. The Account view currently renders usage as raw JavaScript Object Notation.
   Render a readable delivery log with item identity, version or digest, time,
   measured unit, and delivered or uncertain outcome. Do not label a body
   download as model use or task success.
2. Turn the current written warning about loading into a visible progress
   record: configured, service connected, search answered, exact body fetched,
   native client reported the file, material loaded into a model turn,
   material used, and task independently verified. Unknown is distinct from
   false. The [native material guide](../guides/native-client-material-loading.md)
   already separates these observations. A hosted service cannot infer local
   loading or task acceptance from a download; local details stay local unless
   the customer explicitly exports them.
3. When the approved library grows, add typed filters and comparison for kind,
   exact client compatibility, qualification, licence, effects, and size. The
   existing cards contain much of this data, but the inspected page does not
   provide a filter or side-by-side comparison. A declared harness style does
   not prove a successful client load.

[GitHub's agent session view](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/manage-and-track-agents),
[Claude Code's web view](https://code.claude.com/docs/en/claude-code-on-the-web),
and [Cursor's cloud-agent records](https://cursor.com/docs/cloud-agent)
show progress, logs, changes, or environment identity for runs they host.
They are useful interface references. Baltor's hosted service does not host
customer runs, so any equivalent task view must read a customer-authorized
local Run History export and show missing observations honestly.

## Proposed work within the existing roadmap

These are review candidates, not accepted changes or another task list. The
owners and release order remain in `roadmap.yaml`.

| Priority | Owning work | Smallest next study or change | Discriminating check |
|---|---|---|---|
| 1 | S-6.31, S-6.42, S-6.44 | Add ZCode to the harness compatibility inventory at its pinned revision. Try a separate process and folder, native material listing, and explicit cancellation without a model call first. A model-backed task needs separate owner authority. | A candidate must fail qualification if it sees unlisted files, takes an undeclared effect, cannot cancel, fails to report the exact loaded body, or cannot complete an independently checked task. The reported headless failure remains open until reproduced or disproved. |
| 1 | S-6.17, S-6.24, S-6.38 | Present one continuous first-use progress record, using existing service and local install reports. Render the Account usage log in plain language. | A body download cannot mark `loaded`, `used`, or `verified`; an uncertain delivery cannot be shown as successful; revoking a key ends its future use. Test with an invited user outside engineering. |
| 1 | S-6.32, S-6.47 | Freeze real queries by material kind and compare Baltor with relevant free or paid baselines. Keep documentation, skills, and server metadata in separate denominators. | Count top-result relevance, exact version, permission fit, body load, and accepted work. Include poor matches, failures, and token and cost unknowns. A ranking change must pass the existing relevance floor before serving. |
| 2 | S-6.33, S-6.36, S-6.39 | Explain the $29 material plan, customer-paid model access, included allowance, free trial boundary, and absence of overage billing in one first-use path. Interview invited users after a real task, with the quoted plan visible. | Record whether the person can explain what pays whom and whether they would accept actual terms. A sign-up click or a hypothetical compliment is not willingness to pay. |
| 2 | S-6.40, S-6.44, S-6.45 | Use public registries as source inventories, test native layouts and temporary loading, and preview bundle contents before installation. Preserve source, licence, digest, and effect declarations. | An unapproved, unlicensed, changed, or client-incompatible item must be refused before delivery. Public samples must not expose protected paid bodies through URL-only access. |
| 2 | S-6.41, S-6.51 | Sketch an explicit data-transfer preview and metadata-only outcome feedback. Allow a customer to flag a poor item without sending raw task content. | A disabled content-sharing setting cannot send a file or raw prompt; a changed destination or file scope requires a new authorization; a flag alone cannot promote or demote an item below the evidence threshold. |
| 3 | S-6.37, S-6.48, S-6.55 | Compare one recorded overnight local-model task against the same task without Baltor. Show the machine, model, budget, intermediate failures, verified result, and stop reason. | A page with no saved run, mismatched task populations, missing usage, or an unverified result cannot claim an improvement. |

For the first commercial question, the test is whether useful, approved
material reaches a customer's harness and helps it finish accepted work. A
large catalogue, a successful connection, and a delivered file are separate
facts. This is an inference from the published alternatives and Loop Engine's
own product contract, not a measured market advantage.

## Pickup for the next Claude Code session

1. Read this record with S-6.22, S-6.31, S-6.32, S-6.36, S-6.38, and S-6.42
   through S-6.45 in the roadmap. The current consolidation, release, and
   website repairs keep their existing priority.
2. Add ZCode to the harness comparison inventory as **unqualified**. Preserve
   the pinned source revision and the separate user-report status. Test the
   exact command line, isolation, permission, and native-load paths before
   listing support.
3. Choose one interface refinement from the existing first-use path: readable
   usage, explicit observation states, or bundle preview. Keep customer-run
   evidence local unless the customer authorizes export.
4. Use the baseline products in this report when S-6.36 makes a market claim.
   A product page is evidence of a published offer, not a verified comparison
   or proof that Baltor improves a task.

No customer outreach, purchase, competitor account use, model call, live
experiment, deployment, or publication was performed in this review.
