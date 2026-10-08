# Strategic feeds and customer discovery

Kind: dated primary-source research and an implementation proposal. Sources
checked October 8, 2026 UTC (October 7 in the owner's timezone). No competitor
account was purchased, application submitted, recipient contacted or catalogue
item admitted. Vendor documentation establishes advertised behavior, not a
Baltor head-to-head result. Recheck deadlines before using them.

## Product decision

Agent Feeds should help a customer decide what to build, which architecture
and providers to use, what it will cost, and what to reconsider later. Each
brief needs a concrete decision, constraints, dated sources, alternatives and
the conditions that would change its recommendation. News can trigger a
review; a list of new links is not the finished product.

Agent Feeds + Harness Files adds the tactical materials for that work: code,
tools, tests, configuration and editable projects. A brief can point to an
exact package and its observed checks. It must not turn a source claim into
an execution guarantee or grant a file entitlement merely by linking to it.
The [offering decision](../architecture/OWNER-DECISIONS.md#feeds-and-components-offerings-october-6-2026)
and the [delivery plan](../roadmap/DELIVERY-SEQUENCE.md) retain product and
implementation authority.

Start customer discovery with small teams building agent-assisted software.
Test two jobs: choosing an affordable, suitable stack before a project, and
reviewing an existing stack for maintenance, cost or capability changes.
This is a customer hypothesis, not evidence of demand. Keep creative studios
as a second cohort once an editable project survives revision and clean reopen.

## Competitors and adjacent products

The comparison below is bounded to five relevant products. It does not claim
that any product lacks an undocumented feature or that Baltor has a measured
advantage. Do not use directory size as a substitute for task usefulness.

| Product | Observed official offer | What the first Baltor comparison should measure |
| --- | --- | --- |
| [Feedly AI Feeds](https://docs.feedly.com/article/699-guide-to-ai-feeds-market-intel) | Topic/concept selection, source bundles, exclusions and saved feeds. Feedly also documents a [threat-intelligence MCP connection](https://docs.feedly.com/article/821-why-use-an-mcp-server-for-cti-feedly). | Give both products the same strategic question. Compare relevant evidence, source dates, explicit unknowns, time to a defensible decision and maintenance after a source changes. Do not repeat Feedly's relevance multiplier as an independently established result. |
| [Inoreader API](https://www.inoreader.com/developers/) | Content/feed access with application registration, OAuth and rate limits. Its developer page distinguishes public-app access from other uses, which require a Pro plan and sales quote. | Compare customer-controlled sources, inclusion/exclusion explanations, duplicate handling and a stable agent export. Do not assume its API permits resale of publisher content. |
| [Context7](https://context7.com/docs/overview) | Version-specific library documentation and examples supplied to a coding assistant. Its [API](https://context7.com/docs/api-guide) supports documentation search and context retrieval. | Compare one architecture decision and its implementation. Context7 is a focused documentation alternative, not merely a news feed. Baltor must show why a dated decision brief plus selected files helps beyond fetching docs. |
| [Smithery](https://smithery.ai/docs) | Tool discovery, published MCP integrations and managed connections, including OAuth/token handling. | Compare actual connection requirements, data/effect boundaries, revocation and a task result. Listing a compatible service does not prove that its operations work through Baltor. Consider distribution through its existing publishing route after compatibility tests. |
| [Skills](https://www.skills.sh/) | A skills directory with installation, topics, packs, official sources and audit navigation. | Compare the smallest useful package, provenance, installation, meaningful negative tests and task results. A large collection of Markdown files is an established category, not a differentiation claim. |

A useful paid brief should answer something such as: “For this ingestion
pipeline, which combination of hosting, storage and search meets these limits,
what tradeoffs remain, and what change should trigger another review?” Keep
the no-extra-material baseline and publish failures alongside successes.
The first comparison need not cover every market or every model.

## First decision collections to qualify

| Collection | Customer decision | Minimum evidence and useful output |
| --- | --- | --- |
| Agent stack review | Keep or change an existing provider, tool or architecture | Current operations, compatibility, costs and limits; decision card; change log; expiry/review date; a migration recipe only when tested. |
| Coding-model and evaluation review | Which model/harness deserves a bounded trial | Benchmark version, task population, harness, date and evaluator; cost separately; no combined ranking across incompatible tests. |
| Retrieval quality and cost | Which retrieval design to test for this corpus | Dataset/task, recall/precision or task metric, latency distribution, cost basis and failure cases; reproducible evaluation files. |
| Hardware fit | What can fit, then what runs acceptably | Memory assumptions, precision, context, runtime and hardware; estimates separate from measured throughput and quality. |
| Founder stack | Which email, hosting, storage and infrastructure setup fits the stage | Official limits, lock-in/recovery concerns, total-cost assumptions and account requirements; small setup/check packages. |
| Competition and positioning review | Which customer problem to emphasize next | Dated official offers, a bounded comparison task and unknown demand; interview plan, not an invented market-size number. |

Each collection needs a saved customer definition and a separate per-agent
binding. A source preference can narrow access; it cannot grant access.
Qualify previews, updates, stale states, revocation and two-account isolation
before selling personalized subscriptions. Public benchmark links are useful
discovery, but they are not a feed of independently reproduced results.

## Organization shortlist

These are organizations with relevant public routes, not customers, confirmed
partners or positive sales leads. The proposed fit and next action are our
hypotheses. Use each organization's public page, not an employee contact list.

| Organization and route | Observed opportunity | Proposed next step and dependency |
| --- | --- | --- |
| [Cloudflare for Startups](https://www.cloudflare.com/startups/) | Tier 3 advertises $10,000 for bootstrapped/self-funded startups. Higher partner-funded tiers reach $350,000. Credits last one year; R2 has a $10,000 cap and AI Gateway is temporarily excluded. The same page's general eligibility list also says funded within twelve months, which conflicts with the bootstrapped tier wording. | Prepare a Tier 3 application summary with the real architecture, company facts and cost estimate. Confirm the conflicting eligibility wording through the official application route. Approval, available credit and Baltor's eligibility remain unknown. Do not budget against unawarded credits. |
| [Y Combinator application](https://www.ycombinator.com/apply) | The current page names Winter 2027, an on-time deadline of November 2 at 8 p.m. Pacific, and a January-March in-person batch in San Francisco. | Work back from November 2, 2026. Engineering prepares a working demo, evidence and draft answers; the founder supplies accurate company/team facts and submits through their own account. Willingness and ability to attend remain founder facts, not assumed. |
| [Techstars New York City](https://www.techstars.com/accelerators/nyc) | The page lists November 18, 2026 as the deadline and March 8, 2027 as the start. | Compare programme requirements with the founder's constraints before choosing this cohort. Prepare the common application once; Techstars [says duplicate applications do not improve acceptance chances](https://www.techstars.com/application-preview). Investment terms need the founder's review. |
| [Ben Franklin CNP Big Idea Contest](https://cnp.benfranklin.org/programs-resources/bigidea/) | Applications close October 16, 2026. Eligibility includes its 32-county Pennsylvania region, no prior Ben Franklin funding or relevant competition prize, a commercialization plan and annual sales no higher than $1 million. The page says registration is not required to apply, but the applicant must plan to register in Pennsylvania. | Check the actual business county and those company facts immediately. Prepare a one-page problem/product/evidence summary if eligible. Do not treat a postal address as proof of company eligibility. |
| [Ben Franklin CNP funding](https://cnp.benfranklin.org/funding/) | Its process includes a cash match and payback obligation; the page describes a typical three-to-six-month process. It is not a general small-business grant. | Prepare the business summary and cash/runway model. Use the regional office route for a fit review before building a financing plan around it. This cannot fund next week's operating assumption. |
| [Happy Valley LaunchBox FastTrack](https://happyvalley.launchbox.psu.edu/fasttrackaccelerator/) | The public page describes a ten-week customer/business-model programme. Its visible dates say August 24/September 11 and do not give a year in that section. | Keep its “Let's Connect” route as a local mentorship option. Ask about a future cohort only after a source refresh; do not advertise the displayed application window as open. |
| [Latent Space](https://www.latent.space/about) | An AI-engineering publication/community with separate public routes for news pitches and sponsorship/partnership enquiries. | Prepare a technical result or useful open tool before a pitch. A distribution hypothesis is not editorial interest. No generic promotional blast. |
| [Changelog news submission](https://changelog.com/news/submit) | A public developer-news submission route. Its separate [sponsor page](https://changelog.com/sponsor) describes paid placement. | Submit-worthy material is a useful repository release or honest reproducible comparison. Keep editorial submission and advertising separate; no spend or submission in this research run. |
| [TLDR advertising](https://advertise.tldr.tech/) | Topic-specific technology newsletters and a quote-based advertising route. | Consider a small, owner-managed paid test only after attribution, activation and repeat use are measurable. No advertised audience size is a promised customer yield. |

The earliest listed deadline is October 16. That makes eligibility and a
small evidence pack more urgent than producing a long generic investor list.
Company incorporation, ownership, revenue, fundraising history and customer
claims must come from the founder's records. Leave missing values unknown.

## Cloudflare discovery workflow

Keep one research owner and the existing engine slots. Cloudflare is a
hosting choice for bounded adapters; the diagram does not introduce another
runtime or authorize a send.

```text
Existing research query planner and source contracts
├── Scheduled trigger: due questions, source limits and one logical run identity
├── Selected read engine: official API, permitted feed or allowed public page
├── Immutable observation: source identity, dates, hash, rights and failure state
├── Existing knowledge radar: decision evidence and private organization draft
└── Host review through existing managed records
    ├── Suppression and freshness checks
    ├── Agent-readable private JSONL or scoped record view
    └── Separately authorized exact communication, if a sender is later qualified
```

[Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
can schedule a bounded acquisition tick. Queues can carry small immutable job
references and Workflows can coordinate recoverable steps. Cloudflare documents
[at-least-once queue delivery](https://developers.cloudflare.com/queues/reference/delivery-guarantees/),
so every retry needs a stable identity and a recorded outcome. A Worker must
not reset source or account budgets when an engine changes. Shared API keys
for one provider account do not create extra quota.

Use R2 for permitted source bytes and immutable exports. Keep authority and
suppression in the existing managed-record boundary; a D1 projection or KV
cache is not a second approval system. Retain the custom search/index builder
on Fly where its runtime or measured resource needs justify it. Do not copy
raw prompts or contact data into a new provider's logs by default.

The offline export in
[`tools/knowledge_radar/opportunities.py`](../../tools/knowledge_radar/opportunities.py)
binds exact existing radar observations to an organization, selected facts,
a fit hypothesis, unknowns and an observed public page. It recomputes freshness
and always emits a private draft with no outreach authority. Suppression
comes from a separate host input and removes the contact route. It performs
no network request, model call, publication or sending. It does not establish
that an organization wants Baltor. A live Cloudflare collection/record-view
adapter and qualified communication integration remain unimplemented.

Qualification sequence:

- [ ] Freeze one organization-only source contract, permitted use and bounded query set.
- [ ] Run the same request through two declared engines; compare evidence and refusal semantics.
- [ ] Test expired evidence, wrong organization/domain, removed or changed source and partial coverage.
- [ ] Bind source observations, suppression records and output digest through the existing managed store.
- [ ] Deploy one read-only scheduled Worker within the recorded allowance and observe a complete run.
- [ ] Prove duplicate delivery, timeout recovery, quota exhaustion and cross-account isolation.
- [ ] Give an agent the private brief and verify that it cannot send, self-approve or expand its access.
- [ ] Qualify a sender separately only when exact recipient, message, identity and rules are authorized.

## Replit decision

Use Replit as an optional demonstration or customer-remix target, not another
production migration now. Its current [remix documentation](https://docs.replit.com/features/projects-and-artifacts/remix-an-app)
describes an independent copy with a new agent and database; deployments,
domains and connectors are not copied. Secret handling differs when remixing
one's own app, so a public example must start from a deliberately sanitized
project. That route could make one verified Baltor example easier to try.

Its [deployment guide](https://docs.replit.com/learn/projects-and-artifacts/replit-deployments)
offers autoscaling, static, reserved-VM and scheduled deployment, and warns
against relying on the published app's filesystem for durable data. These
are useful capabilities, but they do not demonstrate a benefit over our
existing Cloudflare/Fly split. Require a reproducible export, known cost,
successful rebuild and credential isolation before choosing it. No Replit
subscription or application was created in this work.

## Founder and engineering work sequence

This is a dependency estimate, not a completion claim or a replacement for
the active plan. Days begin when the visible two-offering release is verified.

| Work | Target window | Owner | Acceptance and dependency |
| --- | --- | --- | --- |
| Confirm live offer, sign-up, payment and first useful download | Days 0-2 | Engineering | A fresh non-admin customer completes the real path; exact failures recorded. |
| Interview five prospective users across the two strategic decision jobs | Days 1-7 | Founder, with prepared scripts | Save task, current workaround, urgency and explicit permission to follow up. Five is a test target, not completed recruitment. |
| Deliver two strategic briefs and their smallest useful execution packages | Days 2-7 | Engineering | Sources current; claims separated; same-task baseline; working outputs; meaningful revision. Depends on a concrete interview task. |
| Prepare the funding evidence pack | Days 1-5 | Engineering and founder | Product video, exact live state, company facts, cohort results, costs/runway and unresolved risks. Urgent eligibility review for October 16. |
| Run a small onboarding cohort | Days 7-14 | Founder and engineering | Track starts, connection failures, first accepted task, seven-day return and support time. Do not count free accounts as revenue. |
| Publish one case study and make one relevant editorial pitch | Days 10-21 | Engineering prepares; founder owns personal posting | Reproducible evidence and a visible customer path, not catalogue-count advertising. No message sent by this research run. |
| Test one distribution channel | Days 14-28 | Founder | First establish attributable activation and repeat use. Advertising spend remains owner-managed. |
| Expand engines and collection coverage from observed demand | After the first cohort | Engineering | Measured source coverage, cost and evidence quality; no duplicate file inflation or unbounded generator expansion. |

The investor pack should explain the difference between source leads,
candidate files, distinct served files, customer use and recurring revenue.
The next product proof is a useful decision and a completed task, not a larger
counter on its own.
