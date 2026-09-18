# Competitive landscape and monetization: memory, learning, and optimization layers for agents

Date: 2026-09-18. Requested by the owner after the SenseLab reading: compare
the companies and projects adjacent to Loop Engine, contrast them with Loop
Engine's boundaries, and learn from how they charge. Every price, quota, and
claim below was read from the vendor's own public page or its public
repository on this date and is quoted as the vendor states it. Nothing was
purchased or benchmarked. Two companies from the owner's notes, Overmind and
Lemma, could not be reached at any resolvable domain today and are listed
as unverified.

## The landscape in one tree

```text
Layers adjacent to Loop Engine
├── Memory and context for agents
│   ├── Mem0, Zep and Graphiti, Supermemory, Cognee, Honcho, MemOS, Hindsight
│   └── SenseLab (memory plus outcome-linked confidence and training export)
├── Harness and prompt optimization, research workbenches
│   ├── Synth (local workshop plus managed research)
│   ├── Tellurio and Afnio (auto-tuned harnesses, hosted experiment tracking)
│   └── Overmind and Lemma (described in the owner's notes; unverified today)
├── Evaluation, simulation, and tracing
│   └── LangWatch
├── Right-sized computation
│   ├── Not Diamond (model routing)
│   ├── TypeSafe Jev (typed decisions, text only)
│   ├── PrismML Bonsai (compressed open-weight models)
│   └── Osmosis and Adaptive ML (post-training of specialized models)
├── Services-led enterprise deployment
│   └── Distyl
└── Precedents
    ├── Adaptive ML acquired by Datadog (announced June 2026)
    └── TensorZero archived on GitHub (2026-06-11)
```

Loop Engine sits across these layers rather than inside one: it owns the
run, the four intelligence layers, code and tool reuse as qualified
executable capability, independent verification, the model ontology, and
the records that say which implementation of an operation was cheapest.
None of the companies below owns all of that; several own one layer far more
deeply than Loop Engine does today.

## Comparison chart

Stars and licenses are from the GitHub programming interface on 2026-09-18.
"Open core" means an open source engine with paid hosted or governance
features.

| Company | What it sells | Open source | Pricing and packaging (vendor's numbers) | Metering unit | Buyer | Overlap with a Loop Engine boundary | What Loop Engine has that it lacks | What it has that Loop Engine lacks |
|---|---|---|---|---|---|---|---|---|
| Mem0 | Persistent memory for agents; graph memory; memory consolidation | Apache 2.0, 65,589 stars | Hobby free (10,000 adds and 1,000 retrievals per month); Starter $19 per month (50,000 adds, 5,000 retrievals); Pro $249 per month (500,000 adds, 50,000 retrievals, graph memory, consolidation); Enterprise custom with on-premises, audit logs, single sign-on | Add and retrieval requests per month | Solo builders to production teams | Context Intelligence retrieval; procedural memory in its Python package | Execution, verification, code reuse, typed contracts, cost records | Scale, integrations, a consolidation process, and a large community |
| Zep and Graphiti | Temporal knowledge graph memory with provenance and evolving facts | Graphiti Apache 2.0, 30,986 stars | Free 10,000 credits per month; Flex $125 per month (50,000 credits, then $25 per 10,000); Flex Plus $375 per month (200,000 credits, then $75 per 40,000); Enterprise custom with bring your own key and bring your own cloud | Credits | Startups to large enterprises | Context Intelligence with time validity; the freshness rule Loop Engine records on facts | Execution, verification, the solutions space | Edge invalidation at write time, a mature graph store, rate-limited tiers |
| Supermemory | Model-independent memory and context engine, connectors, self-hosting | MIT, 30,159 stars | Free ($5 credits per month); Pro $19 per month ($20 credits); Max $100 per month ($130 credits); Scale $399 per month ($600 credits, self-hosted option, compliance reports); Enterprise custom; its own token unit at $5 to $10 per million for memory and $1 to $2 per million for retrieval, plus $5 per million search queries and $100 per million operations at Scale | Ingested tokens, queries, operations | Individual developers to enterprises | Context Intelligence; the "retain a reference, load on demand" rule | Verification, code reuse, model ontology | Connectors, a startup program, compliance packaging, a forward-deployed engineer at the top tier |
| Cognee | Memory platform with graph relationships, ontologies, citations | Apache 2.0, 30,809 stars | Free (1 million tokens); Standard $1.00 per million tokens processed plus $5 per additional workspace; Enterprise bring your own cloud, custom; open source self-hosted free | Tokens processed, workspaces | Individuals to large organizations | Ontology and evidence graph; citations resemble Loop Engine's evidence references | Execution, verification, cost-based implementation choice | Source connectors, code indexing, bi-temporal conflict resolution in the paid tier |
| Honcho (Plastic Labs) | Reasoning-based memory of people, agents, and projects; "continual learning for stateful agents" | AGPL-3.0, 7,244 stars | Ingestion $2.00 per million tokens; unlimited context calls; reasoning tiers from $0.001 to $0.50 per query; startups get $1,000 in credits and twelve months of subsidized pricing | Ingested tokens and priced reasoning queries | Companion, tutor, support, and coding agent builders | User Feedback Intelligence and per-user representations | Independent verification, executable capability | A per-query reasoning ladder that prices depth of thought explicitly |
| MemOS (MemTensor) | Memory operating system with a local edition and a cloud | Apache 2.0, 11,455 stars | Cloud Free (50,000 adds, 20,000 searches, 3 million input and 1 million output tokens); Starter $19 per month (600,000 adds, 200,000 searches), shown as currently free; Pro $286 per month (80 million adds, 30 million searches), shown as currently free; Enterprise custom; MemOS Lite runs fully local | Adds, searches, tokens, storage | Students and proofs of concept to scaling teams | Skills as prompt guides overlap with Code Intelligence, but they are instructions, not executables | Qualified executable tools, verification | A behavior-scoring plugin and a large user base in its ecosystem |
| Hindsight (Vectorize) | Agent memory with retain, recall, and reflect operations | MIT, 23,894 stars, created 2025-10-30 | Self-hosted free; cloud pay as you go: retain $10.00 per million tokens, recall $0.75 per million, reflect $0.05 per call, storage $0.25 per million tokens per month after 30 days; Enterprise custom with bring your own cloud and uptime commitments | Tokens per operation kind, calls | Developers of agents and coding assistants | Context Intelligence; the reflect step resembles Loop Engine's derived records | Verification, code reuse, cost records | Per-operation pricing that separates storing, retrieving, and synthesizing |
| SenseLab (AMFS) | Outcome-linked memory, decision traces, confidence, training export, managed tool-call models | Apache 2.0 core, 76 stars | Free $0 (1,000 operations); Starter $29 per month (25,000); Pro $149 per month (50,000); Teams $449 per month (300,000); overage packs of 10,000 operations at $25, $20, or $15 by plan; reads cost 1 operation, writes 2, outcome commits 0; Managed Models $199 per month per account, serving at $1.00 input and $5.00 output per million tokens (a pro variant at $1.25 and $8.00), 10 million training tokens per month included then $10 per million; the pricing page shows 1 seat on Free while the billing document shows 2 | Operations, seats, keys, training and serving tokens | Individuals, small teams, businesses | The reuse evidence rule Loop Engine adopted on 2026-09-18; training export; briefings | Execution, verification, code and tool reuse, typed contracts, implementation choice | Branching, merge, pull requests, access control, signed traces, a dashboard, and hosted fine-tuning, all paid-only |
| Synth | Local research workbench (macOS) and managed research in the cloud; optimizers and containers as open source | Software development kit MIT, 82 stars | Workshop free with a permanent $10 allowance for account-backed work; local models, data, and execution need no account; cloud research billed separately; no public price list | Account-backed usage, provider costs pass through | Researchers and research engineers | The solutioning space: experiments, traces, candidates, comparison | Independent verification as a gate, the solutions space, code reuse across tasks | A polished local workbench and "experiments per minute" as the product promise |
| Tellurio and Afnio | Open source workflow optimization and a hosted experiment tracker | Site names github.com/Tellurio-AI/afnio; not found through the GitHub programming interface today (a tutorials repository exists) | Studio Free $0 per user (1 seat, 20 private runs and 3 private optimize hours per month); Pro $50 per user per month (5 seats, 80 private runs, 20 optimize hours, $1 per additional hour); Enterprise custom | Seats, runs, optimize hours | Individuals to enterprise agent teams | Harness and prompt optimization; explicit operation inputs and outputs resemble Loop Engine's typed ports | Verification, model ontology, reuse of executables | Optimize time as a metered unit |
| LangWatch | Evaluations, simulations, scenarios, tracing for agents | Apache 2.0, 4,814 stars | Developer free (50,000 events per month, 14 days of data, 2 users); Growth €29 per core seat per month with 200,000 events included then €5 per 100,000 and €3 per gigabyte beyond 30 days; Enterprise custom, self-hosted or on premises | Events, seats, storage | Individual developers to regulated teams | Independent evaluation and campaign reporting | Execution ownership, reuse, model ontology | Simulation-based testing and marketplace billing |
| Not Diamond | Predicts which model to use per prompt | Python software development kit archived 2025-12-11, 91 stars | Pay as you go at $0.05 per million tokens routed, positioned as cheaper than the cheapest model; Enterprise custom with organization analytics and single sign-on | Tokens routed | Developers and enterprise teams | Model routing inside the model ontology | Routing to no model call at all, verification, reuse | A fee anchored below the savings it claims (20 to 40 percent) |
| TypeSafe (Jev) | Typed decisions with probabilities instead of text; text only | No open weights (none on the model hub) | $42 per billion input tokens ($0.042 per million), output free; version jev-1.13.0 behind aliases jev-latest and jev-preview; 64,000 token context; rate limits adjust dynamically | Input tokens | Enterprises automating decisions | The judgment model kind in the model ontology; a candidate hybrid contract sensor | The ability to decide a model is unnecessary; verification | A calibrated-probability product and 12.2 times cheaper batching of many questions in one call |
| PrismML (Bonsai) | Ternary and 1-bit compressed open-weight models and a runtime | Apache 2.0 weights on the model hub (Ternary-Bonsai-27B: 650,692 downloads; Bonsai 2 27B: 405,609) | No public pricing; models free to download; a consumer application | None published | Device and laptop deployments | Local generative routes under the model ontology | Everything above the model | The models themselves and a runtime that makes them run |
| Osmosis (Gulp AI) | Forward-deployed reinforcement learning post-training for task-specific models | No public repository found | No public pricing; hands-on deployments; retraining "as little as every hour" | Not published | Enterprises needing extraction, tool-use, and code models | The "train our own model" branch of the engineering-lab questions | Deciding whether to train at all from cost records | Training infrastructure and reward engineering as a service |
| Adaptive ML | Post-training, evaluation, and serving of specialized models | Not applicable | Acquired by Datadog; the vendor site links a June 2026 announcement; named enterprise customers | Not published | Enterprises | Same branch as Osmosis | Same as Osmosis | An exit to an observability vendor |
| Distyl | Services-led deployment of agentic systems with a platform of composable routines and auditability | Not applicable | No public pricing; investors named on the site; "1B+ decisions processed annually"; "50+ enterprise deployments" | Engagements, decisions processed | Fortune 500 and institutions | The lab-of-engineers operating model | A product | Revenue from deployment work rather than software |
| TensorZero | Was a gateway, observability, evaluation, and optimization platform | Apache 2.0, 11,720 stars, archived 2026-06-11 | "No longer maintained" per its site | None | None now | Gateway and evaluation | Nothing to add | A warning: an open gateway without a moat did not survive |
| Overmind, Lemma | Described in the owner's notes as trace-driven optimization with specialist training, and trace auditing with failure grouping | Unverified | Unverified; the .ai domains reached today belong to other companies or are parked | Unverified | Unverified | Would overlap the failed-check review and the engineering loop | Unverified | Unverified |

## What the chart says about Loop Engine's position

Every memory vendor sells retrieval, provenance, and confidence over prose
entries. None executes code, verifies a deliverable, or keeps a tool as a
qualified executable capability, and none records which implementation of
an operation was cheapest. That is the gap the owner named on September 18,
and it is now a typed boundary in Loop Engine (the model ontology, the
operation cost records, the solutions space). The optimization vendors
(Synth, Tellurio, and the unverified pair) sell the solutioning space
without the solutions space: experiments and tuned harnesses, but no plural,
verified, reusable solutions per task.

The strongest evidence for the position is a competitor's own record. The
AMFS repository's preregistered benchmark found every memory arm worse than
no memory on first-attempt success at five to seven times the tokens until
outcomes reconciled the exact read set (see the
[SenseLab record](EXTERNAL-SENSELAB-2026-09-18.md)). Loop Engine's thesis is
that reuse must be selected by verified outcomes and cost, not by
similarity, and that the cheapest adequate implementation is often not a
model call. No vendor above sells that decision.

## How they charge, and what each unit rewards

| Pattern | Who uses it | What the unit rewards | Fit with Loop Engine's thesis |
|---|---|---|---|
| Operations per month with paid overage packs | SenseLab (reads 1, writes 2, outcomes free) | More reads and writes; outcomes deliberately free so learning signal keeps flowing | Poor as a primary unit: Loop Engine exists to make fewer calls. The free outcome commit is worth copying for verification records. |
| Tokens ingested or processed | Supermemory, Cognee, Hindsight, Honcho ingestion | Heavier ingestion | Poor: it rewards loading more context, the opposite of the minimal-sufficient-context rule. |
| Per operation kind at different rates | Hindsight (retain $10, recall $0.75, reflect $0.05) | Separates storing, retrieving, and synthesizing | Good model for Loop Engine's operation cost records: price what costs, not what is convenient to count. |
| Per query by depth of reasoning | Honcho ($0.001 to $0.50 per query) | Paying more for more deliberation | Directly matches the engineering-lab question "how much reasoning does this step need"; a natural unit for the judgment and verification services. |
| Credits with rollover and rate limits | Zep | Predictable spend, rate-limited tiers | Neutral; useful for a hosted judgment service. |
| Per seat plus usage | LangWatch (€29 per core seat), Tellurio ($50 per user), Letta Teams ($20 per seat) | Team adoption, collaboration | Good for the Studio and campaign dashboards; seats do not distort engine behavior. |
| Per agent per month plus tool execution time | Letta ($0.10 per active agent, $0.00015 per second of tool execution) | Long-lived agents and compute time | Interesting for Spawned Loops and sandbox execution: charge the compute a run actually used. |
| Optimize hours | Tellurio ($1 per additional hour) | Time spent searching configurations | Matches campaign runs; the honest unit for the engineering loop. |
| Routing fee below the savings | Not Diamond ($0.05 per million tokens routed, claimed 20 to 40 percent savings) | Fee anchored to avoided cost | The best analog for the implementation selector: charge a fraction of the model calls the reuse and cost records avoided, which is measurable from the records. |
| Managed specialist models as subscription plus serving | SenseLab ($199 per month, $1 and $5 per million tokens, eligibility thresholds) | Training only when data suffices; recurring serving | Direct precedent for the "train our own model" branch; the eligibility thresholds (100 to 200 decisions, at least 3 tools, at least 60 percent success) are a product mechanism, not only a guide. |
| Open core with governance in the paid tier | SenseLab (branches, access control, signed traces, dashboard), Supermemory (compliance at Scale), Mem0 (on premises, audit logs) | Free engine, paid collaboration and control | The natural split for Loop Engine: runtime, contracts, and records open; hosted verification, shared solutions spaces across teams, managed specialists, and dashboards paid. |
| Free local, paid cloud compute | Synth ($10 allowance), MemOS Lite, Hindsight self-hosted | Adoption on the developer's machine | Loop Engine already runs locally; the paid path is the shared and hosted layers. |
| Services-led deployment | Distyl, Osmosis, Supermemory's forward-deployed engineer | Revenue from engagements | The lab-of-engineers model can be sold as forward-deployed research on a customer's task families, with the records as the deliverable. |
| Exit | Adaptive ML to Datadog (June 2026) | Observability vendors buying the learning layer | The acquisition case the owner raised is real; the buyer wanted production signals feeding specialized models, which Loop Engine's records are designed to produce. |
| Abandonment | TensorZero (archived) | None | An open gateway without a differentiated moat did not survive; the moat must be the verified records and the reuse they enable. |

Price anchors from the market on this date: entry tiers at $19 to $29 per
month, team tiers at $125 to $449 per month, seats at $20 to $50 per user
per month, and usage from $0.042 per million tokens (a typed decision) to
$10 per million tokens (storing memory).

## Lessons Loop Engine should take

1. Meter what the thesis improves. A unit that grows when the engine works
   well is verified completions per task family, or model calls avoided by
   qualified reuse; both are already computable from the operation cost
   records and the learning records. A unit that grows when the engine
   works badly (reads, tokens ingested, calls) contradicts the product.
2. Keep outcomes free. SenseLab makes outcome commits cost nothing because
   the learning loop starves without them. Loop Engine's independent
   verification records should never be metered.
3. Price deliberation depth, not volume, for hosted judgment. Honcho's
   per-query ladder and TypeSafe's flat input rate show buyers accept a
   price for a bounded judgment; the engineering-lab question "is a model
   necessary here" is the product, and the answer "no" should be cheapest.
4. Put governance, not the engine, behind the paywall. Every open-core
   vendor draws the line at branching, access control, signing, dashboards,
   and hosting. For Loop Engine the equivalents are shared solutions spaces
   across teams, hosted verification, managed specialists, and the Studio.
5. Gate training on evidence thresholds and sell it as a subscription plus
   serving. SenseLab's numbers are a usable starting shape; Loop Engine's
   `TrainingExportPolicy` already excludes unverified and synthetic rows,
   which is the stricter version of the same rule.
6. Charge the engineering loop by the hour and the selector by avoided
   cost. Tellurio's optimize hours and Not Diamond's routing fee are the two
   units that match what Loop Engine actually does.
7. Do not compete on memory. The memory market is crowded, priced to the
   floor, and its own benchmark shows memory without outcome-grounded
   selection can hurt. Compete on the decision of which machinery performs
   each operation, and on the verified records that make that decision
   defensible.

## Caveats

- Vendor pages change; every number carries the date at the top.
- Star counts measure attention, not revenue or quality.
- SenseLab's pricing page and billing document disagree on Free seats (1
  versus 2); the discrepancy is recorded, not resolved.
- Not Diamond's Python software development kit is archived while its
  product page remains live; the product's status was not verified beyond
  the page.
- Overmind and Lemma are recorded from the owner's notes only.
- No claim here about a company's revenue, customers, or roadmap goes
  beyond what its public page states.
