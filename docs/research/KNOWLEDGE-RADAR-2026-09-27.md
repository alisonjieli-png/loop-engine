# Knowledge radar: research record (September 27, 2026)

Kind: research record and design. Roadmap step S-6.214 (daily distillations).
Prior art was checked on September 27, 2026; every address below loaded that
day unless it is marked otherwise. This record reports what was read and the
design it leads to. What the first version implements, point by point, and
the evidence of its first run are in the component guide,
[`tools/knowledge_radar/README.md`](../../tools/knowledge_radar/README.md).

## What the owner asked for

On September 27, 2026 the owner described a knowledge feed for coding
harnesses. Developers spend a lot of time keeping up with papers, benchmarks,
models, pipelines, tools and services, usually through newsletters and
digests that they paste into a harness as context. The owner asked for agents
that watch these sources continuously and serve the results to harnesses
through Baltor, and that ask again as the answers age: "Is this the most
efficient way of doing things, or what is best, or what's the best context,
or what's the best SaaS or services that we could use?" Papers are not
limited to AI and machine learning; any scientific field can be seed
intelligence.

Three later additions the same day shaped the design:

1. The rule for what to hold: "if the research time takes an engineer more
   than five minutes, multiple websites to go to ... We should just do that
   once and then put it into our context layer", while "rather than holding
   stock price, we can hold tools that can call stock prices". Served files
   include executable code, not only instruction files.
2. A pipeline design: a question registry rather than a topic list, distinct
   check outcomes, time fields on every claim, separate vetting dimensions,
   common origin, an ingestion contract per source, negative knowledge, cost
   per accepted task as an evaluation product, durable stages, and proof
   before scale.
3. A principle: "Research once, validate for defined conditions, distribute
   many times, and repeat only the work invalidated by a meaningful change",
   with honest answer states, four freshness times per source, invalidation
   relationships, request coalescing and three data layers. A separate
   researcher is checking the competitor claims of that analysis in
   `docs/research/SHARED-RESEARCH-SERVICE-LANDSCAPE-2026-09-27.md`; this
   record does not repeat that work.

## What exists and how the design reuses it

| Existing piece | How the design uses it |
|---|---|
| Codex's source discovery collector (private state, eight source families, four runs a day, twenty requests a run, no model calls) | Read only, through the `collector_state` engine: Hugging Face daily papers and blog, the official Model Context Protocol registry, skills and plugins. The radar never writes to it. |
| The model directory (2,145 models and 190 endpoints, rebuilt daily by `model-directory.yml`) | The `model_directory` and `endpoint_directory` engines read the packaged data: prices with dates, published index values, licences, sizes, quantizations. |
| The directory of protocol servers and agent interfaces (36,231 rows, rebuilt daily by `mcp-directory.yml`) | The `mcp_directory` engine reads names, categories, licences and update days. Descriptions are read only to prove a brief does not repeat them. |
| The library ingestion component (bounded HTTPS transport, request budget, request log, gh reader, sandbox commands) | Every network engine uses its transport, budget and log. The radar keeps its own read-only gh allow list, because the ingestion reader does not allow search, advisories or releases. Package tests run through its bubblewrap command with no network. |
| The native candidate format and its preparation factory | Every deliverable is a `harness_candidate_batch_proposals/v2` proposal; the factory writes the candidate catalogue and pins cited repository files to the committed revision. |
| The review panel's native precheck engines | Run unchanged over the radar's catalogue: licence, format, safety, effects, secrets and duplicates. |
| The owner's public directory repositories | Read at an exact commit and parsed as syntax trees, never run: agent tools, model endpoints and image generation interfaces (MIT). `aidonerightcorp/project-radar-repo` and `aidonerightcorp/capability-intelligence-atlas` were empty on September 27, 2026. |
| The benchmark-radar research of September 26, 2026 | Its lessons are applied: separate observations from catalogue identities, one query contract behind several interfaces, a clear rights boundary, repeated generic text as a warning sign. |

## Prior art and analogues

### Newsletters and digests

TLDR AI (<https://tldr.tech/ai>, every weekday, advertising), The Batch
(<https://www.deeplearning.ai/the-batch/>, weekly), Import AI
(<https://importai.substack.com/>), Latent Space (<https://www.latent.space/>)
and its automated AINews digest (<https://news.smol.ai/>, with RSS), Ben's
Bites (<https://www.bensbites.com/>), Last Week in AI
(<https://lastweekin.ai/>), Interconnects (<https://www.interconnects.ai/>),
The Rundown AI (<https://www.therundown.ai/>), Console
(<https://console.dev/>, weekly developer tool reviews) and Changelog News
(<https://changelog.com/news>, newest feed item April 29, 2026) all send dated
issues as email and web prose. None is machine-readable per topic, none has a
validity window, and none re-checks an old claim: a fact is only as fresh as
the issue that carried it.

### Paper discovery

| Service | Address | What it gives | Gap for a harness |
|---|---|---|---|
| Hugging Face Daily Papers and Trending Papers | <https://huggingface.co/papers>, <https://huggingface.co/api/daily_papers> | A daily list ranked by upvotes, as JSON | AI only, ranked by attention, no verdict or expiry |
| Papers with Code | <https://paperswithcode.com/> | Redirects to Hugging Face Trending Papers | No longer a separate service |
| arXiv | <https://info.arxiv.org/help/api/index.html> | Query interface and RSS; metadata CC0; one request every three seconds | Raw listings |
| OpenAlex | <https://help.openalex.org/access/pricing/> | 327 million works across all sciences, CC0; one dollar a day free, then prepaid credits | Metadata only |
| Semantic Scholar | <https://www.semanticscholar.org/product/api> | Paper graph and recommendations | No synthesis |
| alphaXiv | <https://www.alphaxiv.org/docs/mcp> | A protocol server with 19 tools over papers | Papers, not dated choices |
| Elicit, Consensus | <https://elicit.com/pricing>, <https://consensus.app/pricing/> | One research question answered per run (Elicit Pro 49 US dollars per seat per month) | Nothing is maintained after the run |

### Leaderboards and model comparison

| Service | Address | What it gives | Gap for a harness |
|---|---|---|---|
| Arena (formerly LMArena, renamed January 28, 2026) | <https://arena.ai/leaderboard> | Twelve preference leaderboards | No date on the page, no interface |
| Artificial Analysis | <https://artificialanalysis.ai/documentation> | Intelligence, coding and agentic indices, speed and price; free interface of 1,000 requests a day with attribution | No validity date per fact, no brief per task |
| OpenRouter rankings | <https://openrouter.ai/rankings> | Weekly token share by model; usage data through September 26, 2026 | Popularity, not quality |
| SWE-bench | <https://www.swebench.com/> | Dated result folders, verified by re-running | Coding tasks only |
| Open LLM Leaderboard | <https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/1135> | Retired March 13, 2025 | Shows that sources retire, so a radar needs source health checks |
| Benchmark Radar | <https://benchmark-radar.org/> | 17,170 benchmark records, a daily briefing, JSON and RSS; editorial content CC BY-NC-SA 4.0 | Benchmarks only; commercial reuse needs written permission, so Baltor copies none of it |
| Epoch AI Benchmarking Hub | <https://epoch.ai/benchmarks> | 401 models by 86 benchmarks, CSV, updated September 27, 2026 | Results, no advice |
| models.dev | <https://models.dev/api.json> | An open model catalogue with release and update dates (MIT) | Prices are as fresh as the last contribution |

### Documentation and search for harnesses

| Service | Address | Price (page read) | Gap for a harness |
|---|---|---|---|
| Context7 | <https://context7.com/plans> | Free 1,000 calls a month; Pro 10 US dollars per seat per month with 2,000 calls; 5 dollars per 1,000 extra calls | Documentation for a library already chosen; no dates on answers |
| Exa | <https://exa.ai/pricing> | Search 7 dollars per 1,000 requests; monitors 15 dollars per 1,000 | Live search: a tool for asking again, not a store |
| Perplexity | <https://docs.perplexity.ai/getting-started/pricing> | Search 5 dollars per 1,000 requests; Sonar per token plus per request | Same |
| Tavily (acquisition by Nebius announced February 10, 2026) | <https://www.tavily.com/pricing> | 1,000 free credits a month, then 0.008 dollars a credit | Same |
| Brave Search | <https://brave.com/search/api/> | 5 dollars per 1,000 searches with 5 dollars of free credit a month | Same |
| Ref | <https://docs.ref.tools/usage/pricing> | Pro 50 dollars for 6,000 credits | Documentation search |
| DeepWiki | <https://docs.devin.ai/work-with-devin/deepwiki-mcp> | Free for public repositories | One repository at a time, no regeneration date |
| llms.txt | <https://llmstxt.org/> | A convention for a site index | No date, version or expiry fields |
| Tessl Registry | <https://tessl.io/registry> | Versioned skills with quality, uplift and security scores and review dates, over a protocol server | How to use a library, not which to choose; no expiry |
| Stack Overflow for Agents | <https://stackoverflow.blog/2026/06/10/announcing-stack-overflow-for-agents/> | Validated questions and blueprints for agents, launched June 10, 2026 | Fixes, not dated choices |
| Releasebot | <https://releasebot.io/pricing> | 61,373 release entries from 770 vendors over RSS, email and a protocol server; 5 or 30 dollars a month | Raw changes, no verdicts |

### Technology choice and alternatives

The Thoughtworks Technology Radar (<https://www.thoughtworks.com/radar>, FAQ
<https://www.thoughtworks.com/radar/faq>) is the closest analogue for the
word: twice a year, about twenty senior technologists place "blips" in four
quadrants and four rings (Adopt, Trial, Assess and a fourth ring the site now
calls Caution). A blip appears for one edition unless it moves rings, so each
verdict expires by default. It has no interface, no valid-until date per
blip and no evidence links. InfoQ trends reports
(<https://www.infoq.com/infoq-trends-report-2026/>) are yearly prose.
StackShare was bought by FOSSA on August 1, 2024
(<https://fossa.com/blog/fossa-acquires-stackshare-enhance-developer-tools-management-security/>)
and its site refused automated reading on September 27, 2026. AlternativeTo
(<https://alternativeto.net/>) holds 154,759 apps and two million opinions
with no interface. Stripe Projects (<https://projects.dev/>) sets up 66
providers from a command line and says it does not rank or recommend them.

### Freshness and lifecycle data

endoflife.date (<https://endoflife.date/>, 478 products, MIT, automated
release checks for most products), deps.dev (<https://docs.deps.dev/>,
CC-BY 4.0, fresh within about an hour), OSV (<https://osv.dev/>, no sign-in,
the later modification time is authoritative), the GitHub Advisory Database
(<https://github.com/github/advisory-database>, CC-BY 4.0, 123,823 malware
advisories), OpenSSF Scorecard (<https://scorecard.dev/>, weekly), the CISA
catalogue of exploited vulnerabilities
(<https://www.cisa.gov/known-exploited-vulnerabilities-catalog>) and IsDown
(<https://isdown.app/pricing>, status as a paid tool) all publish dated,
machine-readable facts. None recommends. Guru
(<https://help.getguru.com/docs/verifying-and-unverifying-cards>) gives each
card a verifier and an interval after which it becomes unverified: the
clearest model of expiry, for private knowledge.

### Nothing does all of it

No product found on September 27, 2026 serves per-question briefs about
technology choices with both an as-of and a valid-until date, asks them again
when they expire, and delivers them over a harness protocol. The closest are
the Thoughtworks Radar (expiring verdicts, no interface), Tessl (harness
native, no expiry, how-to rather than which), Guru (expiry model, private),
the lifecycle data sets (dated facts, no advice), the model comparison data
(no validity date) and the change trackers (one kind of fact each).

## What is different about the radar

The design differs from these analogues in six ways.

- **Dated and expiring.** Every brief carries its as-of day and a
  valid-until day computed from its own claims. A claim whose review day has
  passed is listed as not established, never as current. Reading an old,
  dated claim again does not renew it.
- **Asked again as it ages.** The planner re-selects a question when its
  cadence passes or a source it reads changes, and each brief lists the
  questions a harness should ask before choosing.
- **Loadable as it is.** Each answer is a native harness package (a skill
  with a decision card, a typed table and schemas) that passes the same
  prechecks and review as the rest of the library.
- **Tied to runnable components.** Where a choice depends on the caller's
  constraints, the radar ships a decision helper over its own dated table;
  where a fact is volatile, it ships a tool with typed contracts and a
  known-wrong test instead of a stored number.
- **Honest.** Every question has an answer state. A gap is named as a gap,
  a source that could not be read is named as such, and nothing popular is
  offered to hide a missing answer.
- **Evidence-bound.** Every claim names its source, its engine and its
  dates; several listings of one origin count once; no source prose is
  repeated.

## The metered unit

The analogues charge per request or credit (Exa, Perplexity, Brave, Tavily,
Ref), per seat (Context7, Elicit, Socket), per monitored item (IsDown), or
not at all (the public data sets). None charges per brief or per topic.

Recommendation: count a radar package as one library item, so its download
is the existing measured unit, "one downloaded item", under the existing
Baltor Pro plan. Search and a public teaser stay free. A tool's calls run in
the customer's harness with the customer's own network access, so the
download is metered, not the calls. The price decision in `AGENTS.md` already
makes one downloaded item the measured unit, and a separate radar price would
split one library into two products. A private question (an organization
asking for its own research job) would be a different unit, a budgeted
research job, and needs its own price decision when it exists.

## Does a brief improve a harness's choice?

Published results argue for measuring rather than assuming. Context files
did not generally improve task success and raised cost by over 20 percent in
arXiv 2602.11988; AGENTS.md files cut runtime and output tokens in arXiv
2601.20404; curated skills raised pass rates while self-written skills did
not help on average in SkillsBench (arXiv 2602.12670); models accepted wrong
retrieved content over 60 percent of the time when their own prior was right
in ClashEval (arXiv 2404.10198); and inserting deprecation notes reduced the
use of deprecated interfaces in arXiv 2406.09834.

The evaluation design, for a frozen set of choice tasks (for example choose a
model for a step under a budget, choose a document extraction pipeline for a
set of scanned files, choose a supported runtime version for a release):

```text
conditions (same tasks, same model, same harness version)
├── A. the harness's ordinary workflow, with its own browsing
├── B. a daily digest pasted as context
├── C. the radar task packet (the brief for the question)
├── D. the task packet plus its tested implementation (helper or tool)
└── E. a deliberately stale packet, to measure how much harm an old answer does
measures
├── choice accepted by the task's own acceptance check, scored against facts a tool fetched that day
├── tokens, model calls, web requests, wall time and cost
└── an equivalence bound, so "no difference" is a measured result and not an absence of evidence
```

The runs need explicit model authority, a frozen task population and an
independent evaluator; none ran in this pass. The smallest packet that shows
a benefit is the one to serve: if condition C does not beat A on accepted
choices or cost, the radar must shrink or change the packet rather than add
more context.

### The cheapest model per unit of thinking, as an evaluation product

The owner asked for "the cheapest model per unit of thinking per task". The
first version ships an honest proxy: the listed output price divided by the
published intelligence index, with a helper that applies the caller's
constraints, and it says it is a proxy. The product is a measured frontier:

```text
configuration record: model, provider, version, reasoning setting, context strategy, tools, validators,
                      retry policy
frozen evaluation set per task family, with an independent acceptance check
measure: cost per accepted task, quality and latency, including options with no model at all
         (a parser, a SQL query, a classical model)
publish: the cost, quality and latency frontier per task family, dated, with its configuration records
```

It needs model authority and an evaluation budget before any run.

## Where each part sits

| Part | Zone |
|---|---|
| Question registry, source contracts, engines, planner, brief generator, packaging, vetting and the daily run with its state | Internal local |
| Codex's source discovery collector | Internal local |
| Model and protocol server directory refresh | Internal server-side (scheduled workflows) |
| Independent review of the day's candidates | Internal local |
| The daily catalogue release, without a redeploy | Internal server-side |
| Search with freshness, withdrawal of superseded briefs, the teaser page and the feeds | Public service |
| Loading a brief, running a helper or a tool | Customer client and harness |

## The daily pipeline, stage by stage

| Stage | What happens | Zone |
|---|---|---|
| Discover | The collector and the directory refreshes read public sources on their own schedules | Internal local and server-side |
| Plan | Select overdue, changed, demanded and a small exploration share of questions within a budget, with one stable work identity per question | Internal local |
| Collect | Each binding's engine reads its source under its ingestion contract; each answer is written once | Internal local |
| Extract and diff | Compare each binding with its last successful check and name one of five check outcomes | Internal local |
| Analyse with cheap models first | A small model reads sources and writes original summaries and flags; a larger model sees only the few that need it | Internal local, under model authority |
| Vet | Six separate dimensions: source identity, cited evidence, inspection, sandbox tests with known-wrong cases, compatibility, approval for a scope | Internal local |
| Package | The existing native candidate format through the existing preparation factory | Internal local |
| Release | The existing daily catalogue release publishes reviewed items without a redeploy | Internal server-side |
| Serve with freshness | Search prefers the newest brief of a question and marks or hides expired ones | Public service |
| Monitor and withdraw | A newer brief supersedes an older one; a failed check or a changed source withdraws what it invalidates, following recorded invalidation edges | Internal server-side |

## Questions declared on September 27, 2026

The registry, [`questions-v1.json`](../../tools/knowledge_radar/questions-v1.json),
declares 61 questions: 52 with a source today and 9 declared gaps, each with
its reason.

| Question | Area | Minutes, sources | Volatility, refresh | Delivery | Sensitivity | Status |
|---|---|---|---|---|---|---|
| New AI and machine learning papers (`papers_ai_ml_daily`) | papers | 20, 3 | days, daily | brief | general | active |
| New and most cited papers across the sciences (`papers_across_sciences`) | papers | 45, 9 | weeks, weekly | brief | general | active |
| Model leaders on published indices (`benchmarks_model_indices`) | benchmarks | 20, 4 | days, daily | brief, data file | general | active |
| New benchmarks and evaluation suites (`benchmarks_new_evaluation_suites`) | benchmarks | 30, 3 | weeks, weekly | brief | general | active |
| Reasoning and decision models (`models_reasoning_decision`) | models | 30, 4 | days, daily | brief, data file | general | active |
| Cheapest model per unit of published thinking (`models_cheapest_thinking`) | models | 40, 5 | days, daily | brief, data file, decision helper | general | active |
| Coding models (`models_coding`) | models | 25, 4 | days, daily | brief, data file | general | active |
| Small open-weight models (`models_small_open`) | models | 25, 3 | weeks, weekly | brief, data file | general | active |
| Models for laptops and CPU-only machines (`models_cpu_laptop`) | models | 30, 3 | weeks, weekly | brief, data file | general | active |
| Embedding models (`models_embeddings`) | models | 25, 3 | weeks, weekly | brief, data file | general | active |
| Rerankers (`models_rerankers`) | models | 20, 3 | weeks, weekly | brief, data file | general | active |
| Document reading and text recognition models (`models_document_reading`) | models | 30, 4 | weeks, weekly | brief | general | active |
| Typed decision and structured output models (`models_typed_decision`) | models | 25, 4 | days, daily | brief, data file | general | active |
| Text classification models (`models_text_classification`) | models | 20, 2 | weeks, weekly | brief | general | active |
| Entity extraction, linking and resolution (`models_entity_extraction_linking`) | models | 35, 3 | weeks, weekly | brief | general | active |
| Time series forecasting (`models_time_series_forecasting`) | models | 30, 3 | weeks, weekly | brief | general | active |
| Document extraction pipelines (`pipelines_document_extraction`) | pipelines | 40, 4 | weeks, weekly | brief | general | active |
| Web scraping and crawling (`pipelines_web_scraping`) | pipelines | 40, 4 | weeks, weekly | brief | general | active |
| Browser automation for agents (`pipelines_browser_automation`) | pipelines | 30, 3 | weeks, weekly | brief | general | active |
| Image collection and dataset building (`pipelines_image_collection`) | pipelines | 30, 2 | weeks, weekly | brief | general | active |
| Risk evaluation pipelines (`pipelines_risk_evaluation`) | pipelines | 40, 3 | weeks, weekly | brief | general | active |
| Geospatial pipelines (`pipelines_geospatial`) | pipelines | 40, 3 | weeks, weekly | brief | general | active |
| 3D reconstruction and generation (`pipelines_three_dimensional`) | pipelines | 40, 4 | weeks, weekly | brief | general | active |
| Computer-aided design tools (`pipelines_cad`) | pipelines | 40, 3 | weeks, weekly | brief | general | active |
| 2D graphics and design tools (`pipelines_two_dimensional_design`) | pipelines | 30, 3 | weeks, weekly | brief | general | active |
| Prediction systems (`pipelines_prediction_systems`) | pipelines | 35, 3 | weeks, weekly | brief | general | active |
| Fast tools written in Rust (`tools_rust_rewrites`) | tools | 30, 2 | weeks, weekly | brief | general | active |
| Agent frameworks (`tools_agent_frameworks`) | tools | 40, 3 | weeks, weekly | brief | general | active |
| Model Context Protocol servers by category (`tools_protocol_servers_by_category`) | tools | 20, 3 | weeks, weekly | brief | general | active |
| Agent skills and harness plugins (`tools_agent_skills_and_plugins`) | tools | 20, 2 | days, daily | brief | general | active |
| Application hosting (`infra_app_hosting`) | infrastructure | 60, 10 | weeks, weekly | brief | general | active |
| Vector and semantic search (`infra_vector_search`) | infrastructure | 60, 8 | weeks, weekly | brief | general | active |
| Model endpoints and local runtimes (`infra_model_endpoints`) | infrastructure | 60, 6 | weeks, weekly | brief, data file | general | active |
| Email sending (`infra_email_sending`) | infrastructure | 45, 6 | weeks, weekly | brief | general | active |
| Logging and observability (`infra_logging_observability`) | infrastructure | 60, 8 | weeks, weekly | brief | general | active |
| Uptime monitoring (`infra_uptime_monitoring`) | infrastructure | 45, 6 | weeks, weekly | brief | general | active |
| Authentication (`infra_authentication`) | infrastructure | 60, 8 | weeks, weekly | brief | security | active |
| Payments and subscriptions (`infra_payments`) | infrastructure | 60, 6 | weeks, weekly | brief | financial | active |
| Product analytics (`infra_product_analytics`) | infrastructure | 45, 6 | weeks, weekly | brief | general | active |
| Image generation interfaces (`infra_image_generation_apis`) | infrastructure | 40, 5 | weeks, weekly | brief | general | active |
| Developer service status (`infra_service_status`) | infrastructure | 2, 1 | hours, daily | tool | general | active |
| Runtime, framework and database support calendar (`calendar_runtime_support`) | calendars | 20, 6 | weeks, weekly | brief, data file, decision helper | general | active |
| Model and interface deprecation dates (`calendar_model_deprecations`) | calendars | 30, 8 | weeks, weekly | brief, data file | general | declared gap |
| Conference and competition deadlines (`calendar_conference_deadlines`) | calendars | 20, 6 | weeks, weekly | brief, data file | general | declared gap |
| Recent critical and high security advisories (`security_recent_advisories`) | security | 30, 3 | days, daily | brief, tool | security | active |
| Malicious package reports (`security_malicious_packages`) | security | 20, 2 | days, daily | brief | security | active |
| Licences of popular projects (`licences_popular_projects`) | licences and pricing | 40, 30 | weeks, weekly | brief | legal | active |
| Developer service pricing changes (`pricing_developer_services`) | licences and pricing | 3, 1 | hours, daily | tool | financial | declared gap |
| United States federal rules on artificial intelligence (`regulation_us_federal_ai`) | regulation | 30, 2 | weeks, weekly | brief | legal | active |
| United States federal rules on privacy (`regulation_us_federal_privacy`) | regulation | 30, 2 | weeks, weekly | brief | legal | active |
| AI and privacy law timelines by jurisdiction (`regulation_ai_privacy_by_jurisdiction`) | regulation | 90, 12 | weeks, weekly | brief, data file | legal | declared gap |
| Geopolitical developments affecting technology (`events_geopolitical`) | events | 60, 10 | days, daily | brief | legal | declared gap |
| Reference exchange rates (`markets_exchange_rates`) | markets | 2, 1 | days, daily | tool | financial | active |
| Stock quotes (`markets_stock_quotes`) | markets | 2, 1 | hours, daily | tool | financial | declared gap |
| Sanctions and export control screening (`markets_sanctions_screening`) | markets | 4, 1 | hours, daily | tool | legal | declared gap |
| Legal entity lookup (`markets_legal_entity_lookup`) | markets | 4, 1 | days, daily | tool | financial | active |
| Agent protocol and specification releases (`standards_protocol_releases`) | standards | 20, 5 | weeks, weekly | brief | general | active |
| Major version changes in widely used software kits (`sdk_major_version_changes`) | standards | 30, 14 | days, daily | brief | general | active |
| Coding harness releases (`harness_releases`) | tools | 25, 8 | days, daily | brief | general | active |
| Local inference hardware fit (`hardware_local_inference_fit`) | models | 30, 4 | weeks, weekly | brief, data file | general | declared gap |
| Public data source availability (`data_public_sources`) | pipelines | 45, 6 | weeks, weekly | brief | general | declared gap |

## How the owner's additions map onto the design

| Point | Design |
|---|---|
| Research cost, volatility, delivery and refresh per question | Typed fields on each question, and a reader that refuses a delivery that breaks the rule |
| Deliverable kinds | A skill package with the brief and its metadata (as of, valid until, last verified, confidence, sources, questions to ask again); a typed table with its schema; a decision helper over that table; a tool with typed contracts and a known-wrong test |
| Vetting before the context layer | Deterministic prechecks, link checks, schema validation, a refusal of copied source prose, sandbox tests, and independent review by another model family; two families and a source on every claim for legal, security and financial questions |
| Question registry and a daily planner | Audience, constraints, baseline, acceptable evidence and intended output per question; overdue, changed, demanded and explored questions within a budget |
| Check outcomes and time fields | Five outcomes, of which a failed read is never "no change"; seven time fields per claim; "no currently validated recommendation" when freshness cannot be established |
| Common origin and ingestion contracts | An origin key per claim, so several listings of one origin count once; one contract per source engine with its access method, permitted uses, attribution, pacing and failure policy |
| Negative knowledge | What is not established, expired claims and what would change the conclusion, in every brief |
| Reuse at five levels | Source answers, claims, comparisons under an evaluation contract, implementations and scoped, expiring failure records |
| Invalidation and freshness | Edges from each source, table and asset to what depends on it; four freshness times per source; conditional requests where a source supports them |
| Honest answer states | Approved result, candidate, needs research, needs local evaluation, blocked by policy, no eligible option established |
| Three data layers and coalescing | Public shared, organization-private and case-private layers, with only the public layer pooled; one research job per question, constraints and evidence version |
| Suggested sources | arXiv, OpenAlex, Hugging Face Hub, models.dev, GitHub releases, the official protocol server registry, OSV, FederalRegister.gov and eCFR (whose web rendition is not the official legal edition), SEC EDGAR, SAM.gov and USAspending, and GLEIF |
| Durable scheduling | A timer starts work; stages with done markers, a journal and stable work identities give durability; DBOS (named in roadmap step S-6.75) and Temporal are candidate engines for a later durable scheduler behind a typed edge |
| Proof before scale | One complete loop on a few recurring questions compared with a harness doing its own research, and five readiness demonstrations: a resumed campaign, a duplicate trigger, a steering source, an expired claim and a revoked release |

## Serving design

### Finding briefs through search

A radar brief is an ordinary library item, so the existing search finds it.
Its purpose should start with "Dated brief, as of" and name its valid-until
day, and its search tags should include `radar <question id>`, the as-of day
and the valid-until day, so a harness sees the dates in the first answer.
The changes that follow belong to the catalogue search component:

1. Serve two attributes on every radar item: `radar_question` and
   `valid_until`.
2. Among items of one `radar_question`, rank the newest as-of first and leave
   out items past their valid-until day unless the request asks for expired
   items; an answer that includes one marks it stale and carries the hint to
   search again.
3. Withdraw a superseded brief in the daily release through the existing
   withdrawal path, keeping its record.

### The public teaser and the feeds

A daily run can write a teaser page of question titles, areas, answer states
and dates with no brief body, a JSON Feed 1.1 file and an RSS 2.0 file.
Serving them needs four small changes in files that parallel builders own in
this consolidation, so they are listed for the release integrator: a builder step that copies
the day's feed files into the service's packaged assets; a renderer module
in the shape of `status_pages.py` that answers `/radar`, `/radar.json` and
`/radar.xml` from that packaged record; one call in the web route; and three
site map rows with their checks. The teaser should link to sign-up, and the
feeds should carry only what the teaser shows.

## Proposed schedule (not installed)

- A user timer at 08:30 UTC every day, after the collector's early run and
  before the 10:00 UTC library slot, running the command with network reads
  and local writes. The planner then answers only the questions that are due
  or whose sources changed.
- The independent review of the day's radar catalogue after the run, by a
  model family other than the producer's (anthropic), with the stricter rule
  for sensitive questions, then the daily release as usual.
- A weekly report of answer states and freshness times, read in the session
  handoff.

## The first end-to-end demonstration

The analysis proposes document extraction as the first capability family; the
separate researcher will confirm or replace that choice. The demonstration to
design toward: an upstream document parsing project publishes a release; one
shared job investigates it; a candidate helper is tested on a frozen set of
documents with known-wrong cases; one immutable release is published; two
different harnesses retrieve it without repeating the browsing and both pass
local acceptance; a later bad release is revoked through the withdrawal path,
and both harnesses see the revocation.

## Open design work

- Independent review of the day's catalogue and its inclusion in a daily
  release.
- Native loading of the packages in Claude Code, Codex, OpenCode and Pi.
- The search attributes, ranking and withdrawal described above.
- The routes for the teaser and feeds.
- Model-read summaries with a named writer (S-6.214 asks for them), under
  model authority, cheap models first.
- Engines for the declared gaps: deprecation pages, deadlines, regulation
  outside the United States federal register, events, pricing pages, stock
  quotes, sanctions lists, hardware fit and public data catalogues.
- An engine slot record for the source edge in `engine_slots.yaml`.
- The evaluation of section "Does a brief improve a harness's choice?".
