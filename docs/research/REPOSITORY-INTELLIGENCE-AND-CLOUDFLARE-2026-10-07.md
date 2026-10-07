# Repository intelligence and Cloudflare research

Research date: October 7, 2026. Baltor should acquire source observations once,
then reuse them for rankings, customer feeds, context files, evaluated
components and demonstration drafts. Separate collectors for every ranking
website would duplicate identities, overstate corroboration and complicate
rights management. Implementation work belongs to S-6.214, S-6.215 and
S-6.217 in the [roadmap](../roadmap/roadmap.yaml); the
[delivery plan](../roadmap/DELIVERY-SEQUENCE.md) owns sequencing.

The observations below come from public documentation, small pinned source
snapshots and bounded public API reads. A repository manifest describes that
source revision, not a verified private production deployment. The private
audit named by the workstation's START-HERE-BALTOR pointer retains exact
source revisions, raw probe responses and failed attempts. No upstream code
was executed merely because it appeared in these lists.

## Corrections that affect the design

GitHub introduced a privacy-safe star-history endpoint on September 4, 2026.
`GET /repos/{owner}/{repo}/stargazers/history` provides counts of stars created
in weekly records with daily counts. A public read succeeded during this
research. Those counts are not net star growth: removals and count corrections
can make a change in the current total differ. Keep owned count snapshots
and the provider's creation history as separate measurements. The API's
day/week boundaries are not guaranteed to be UTC.
[Announcement](https://github.blog/changelog/2026-09-04-new-api-endpoint-provides-privacy-safe-star-history-data/),
[endpoint contract](https://docs.github.com/en/rest/activity/starring?apiVersion=2026-03-10#get-repository-star-history)

OSSInsight currently warns that a pagination change caused missing star,
pull-request and issue events in its ingestion since mid-2025. Its paused
star rankings are not a healthy current source. Preserve the operator's
coverage notice with any imported observation.
[Current service notice](https://ossinsight.io/)

OpenAlex's current authentication documentation permits small keyless use,
contrary to earlier key-required announcements. A bounded keyless query
returned 200 and reported a $0.10 daily allowance and $0.001 query usage.
This is API budget accounting, not a cash charge we made. Production access
should use a named credential and quota rather than depend on incidental
anonymous access. [Authentication](https://help.openalex.org/api/authentication/)

Ten bounded source probes produced nine successful reads: GitHub search and
star history, Hugging Face models/datasets/Spaces/papers, OpenAlex, arXiv and
Crossref. Semantic Scholar returned 429 and was not retried. These probes
establish those responses, not complete collection coverage or sustained
allowances. No paid Trendshift subscription was opened.

## Source and architecture registry

### Discovery products

| Source | Architecture or setup observed | Useful features to adapt | Acquisition and limit |
| --- | --- | --- | --- |
| [Trendshift](https://trendshift.io/) | Public product and documented Signal API; private stack and ranking formula unknown | Time windows, topics, comparisons, saved research, source explanations and social attention | Optional paid adapter. Its own rankings and captured GitHub Trending order are separate sources. Do not infer quality from either. |
| [GitHub Trending](https://github.com/trending) | Server-rendered discovery surface with language and period controls | Preserve original rank, cohort and observation time | Prefer an allowed feed/archive for discovery; HTML layout changes must fail visibly. Stars-sorted search is not Trending. |
| [EvanLi Github-Ranking](https://github.com/EvanLi/Github-Ranking) | Python, GitHub GraphQL, pandas, dated CSV/Markdown output and a machine-specific shell/cron example; MIT | Simple bounded daily batch and historical cohort membership | Modernize the processor before using it. Preserve stable IDs and validate GraphQL errors. Do not execute its publication shell unchanged. |
| [Best of JS](https://github.com/bestofjs/bestofjs) | TypeScript monorepo, Octokit jobs, daily observations and generated static data; Next/React frontend; PostgreSQL/Neon local setup; MIT | Curated universe, tags, daily growth, cheap serving | Best initial snapshot pattern. Pin runtime and dependency versions; adapt jobs rather than adopt the entire application. |
| [Gitstar Ranking](https://github.com/k0kubun/gitstar-ranking) | Rails source; inspected Gemfile pins 6.1.3.1 and development Compose uses PostgreSQL 12/trust; MIT | Repository, organization and user aggregation | Borrow the model, not the old development security settings. No production-stack claim. |
| [Star History](https://github.com/star-history/star-history) | TypeScript/Hono backend with D3 and LRU cache; Next frontend; MIT | Repository comparison, aligned-age timelines, exports and embeds | Use owned observations and current privacy-safe history. Mark gaps instead of inventing continuous history. |
| [OSS Gallery](https://github.com/dubinc/oss-gallery) | Next server/form actions, Dub analytics, Tremor charts and Vercel Postgres; MIT | Cards, submissions, collections and audience feedback | A card click is not a successful installation or useful task result. Record those outcomes separately. |
| [GitHubTrendingRSS](https://github.com/mshibanami/GitHubTrendingRSS) | Swift/SwiftSoup/Stencil batch generation with Actions and Pages; MIT | Daily feeds without another browser scraper | Treat it as a derivative GitHub Trending observation, not an independent endorsement. |
| [GitHub Trending Archive](https://github.com/antonkomarev/github-trending-archive) | Dated compact ranking archive | Historical occurrences and first-seen analysis | Its recursive tree exceeded this audit's 12 MB read cap. Use bounded directory pagination; archive coverage remains explicit. |
| [Track Awesome List](https://github.com/trackawesomelist/trackawesomelist-source) | Deno processing and JSON records; AGPL-3.0 source | Changes in curated specialist lists | Distinguish implementation licence from licences of linked repositories and editorial content. |

Trendshift advertises a $9/month Signal product with routes for its own
daily/weekly/monthly/yearly rankings, engagement spikes and GitHub Trending
captures. The authenticated schema, allowance and retention were not tested.
Its terms restrict raw API redistribution and substantial reproduction.
Use permitted derived analysis or obtain permission; do not build a public
mirror by assuming a paid API grants unlimited resale.
[Signal](https://trendshift.io/signal), [terms](https://trendshift.io/tos)

EvanLi's pinned processor queries 34 language cohorts and the global stars and
forks cohorts, with two pages of 50 each. That is at most 72 searches and
3,600 list memberships per run, not 3,600 unique repositories. It fetches a
repository ID but omits it from the output, and labels `pushedAt` as
`last_commit`. The helper already has a timeout and retries; the repair is
rate-aware and payload-aware handling, not adding supposedly absent retries.
Its old dependency pins and publication shell need replacement. Stage and
validate a complete run before publishing any daily view.
[Pinned processor](https://github.com/EvanLi/Github-Ranking/blob/1106940defc0c7f00e0dd786b947ef2e8f6e1f69/source/process.py)

### Underlying metadata and qualification

| Source | Setup and evidence | Baltor use and admission boundary |
| --- | --- | --- |
| [GitHub REST and GraphQL](https://docs.github.com/en/rest) | Canonical provider IDs, metadata, search and aggregate history | Primary identity and owned measurements. Respect separate endpoint budgets, capped search results, incomplete flags and conditional requests. |
| [GH Archive](https://www.gharchive.org/) | Public event archives and BigQuery access | Targeted historical analysis. Missing events or timeline limits are not zero activity. Keep dataset and ingestion coverage. |
| [OSSInsight](https://github.com/pingcap/ossinsight) | Open-source ETL, Next/React, ECharts, TiDB and rate-limiting/cache components; Apache-2.0 | Study SQL and comparisons. Do not ingest its currently affected rankings as complete observations. |
| [OpenDigger](https://github.com/X-lab2017/open-digger) | Open-source metrics and OpenRank; Apache-2.0 | Maintenance/community evidence beyond stars. Keep formula version and measurement population. |
| [ecosyste.ms repositories](https://github.com/ecosyste-ms/repos) | Rails aggregation; AGPL-3.0 software, separate data terms | Cross-forge identity, package and dependency relationships. Resolve commercial API/export terms before bulk integration. |
| [Libraries.io](https://github.com/librariesio/libraries.io) | Package and repository discovery; AGPL-3.0 implementation | Package-to-repository enrichment and ecosystem coverage. Code and hosted-data rights are separate. |
| [LibHunt](https://www.libhunt.com/) | Public alternatives/discussion product; private stack not verified | Adjacent-project discovery. Bulk collection rights and endpoint contract remain unverified. |
| [GrimoireLab](https://github.com/chaoss/grimoirelab) | Multi-collector community analytics and identity management; GPL-3.0 | Deeper health investigations for selected candidates, not a required service for every repository. |
| [CNCF DevStats](https://github.com/cncf/devstats) | GitHub data, PostgreSQL, Go tools and Grafana; Apache-2.0 | Contribution metrics and dashboard patterns. Preserve project-cohort definitions. |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | Automated repository-practice checks; Apache-2.0 | Qualification evidence. A score is not a safety guarantee, a licence, or a passed Baltor task. |

The best first collector set is GitHub metadata/search/history, EvanLi
historical cohorts, one Trending feed, curated-list changes and owned daily
snapshots. Add complex event warehouses when a measured question needs them.
Five thousand repositories observed daily produce 1,825,000 snapshot rows per
365-day year. That is a planning count, not a deployment benchmark.

### Hugging Face and papers

Hugging Face provides machine-readable discovery for models, datasets and
Spaces, plus daily-paper discovery. The public probes returned bounded
trending selections from each. Retain the provider type, repository ID,
revision, model card or dataset card link, licence declaration and observation
time. Download counts are provider-defined events, not comparable to GitHub
stars or customer adoption. Model-card evaluation claims remain external
claims until their setup and evidence are checked.
[Hub API](https://huggingface.co/docs/hub/api),
[client and paper commands](https://huggingface.co/docs/huggingface_hub/main/guides/cli),
[dataset download counting](https://huggingface.co/docs/hub/main/datasets-download-stats)

Use arXiv identifiers and versions, DOI/Crossref metadata, OpenAlex entities,
Semantic Scholar's documented APIs and public OpenReview records as
complementary sources. A preprint, accepted paper, revision, withdrawal,
citation count and reproduced result must have different fields. Resolve
source licences before storing full text; an accessible abstract does not
authorize republishing the paper. The arxiv-sanity-lite source is a useful
small recommendation-system reference, but the inspected revision's latest
commit was in 2022, not evidence of a current maintained service.
[arXiv API](https://info.arxiv.org/help/api/),
[Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/),
[OpenAlex](https://help.openalex.org/api/),
[Semantic Scholar](https://www.semanticscholar.org/product/api),
[OpenReview](https://docs.openreview.net/),
[arxiv-sanity-lite](https://github.com/karpathy/arxiv-sanity-lite)

## Proposed internal and customer boundaries

```text
Existing Loop orchestration and typed engine contracts
├── Internal acquisition
│   ├── Source registry: API/feed/parser, limits, credential reference and rights
│   ├── Bounded query: intent, budget, source request and explicit partial/failure state
│   └── Private raw snapshot: allowed bytes, hash, timestamps and retention
├── Internal production
│   ├── Canonical entities and source observations
│   ├── Coverage checks, ranking dimensions and explanations
│   ├── Original descriptions, context, candidate files and media drafts
│   └── Independent admission and exact-version publication
└── Customer delivery
    ├── Authorized search and exact component downloads
    ├── Saved feeds, per-agent assignments and dated snapshots
    └── Demonstrations and comparisons whose claims cite recorded evidence
```

Workers, Queues and Workflows are hosting and transport choices. They do not
introduce a second Loop runtime, grant effect authority or approve generated
work. Reuse the existing research query, knowledge radar, decision, model,
record and serving contracts. Native rendering and large index construction
need an execution profile with the required processes, memory and hardware.

Store entities separately from observations. An entity has a stable provider
identity and aliases. An observation has source identity, retrieval and
source-reported times, original rank, period, cohort, parser version, rights,
coverage and failure state. Four websites repeating the same Trending list
are one underlying signal with four occurrences.

Keep popularity, momentum, discussion attention, maintenance evidence,
capability fit and demonstrated reuse separate. Explain why an item surfaced.
Net star change is `end_count - start_count`; divide by actual elapsed days
for a rate. Keep negative changes. A missing baseline produces missing
growth, not zero. A candidate leaving a top-100 cohort has not become
inactive. Repository text is untrusted input, never a command to execute.

For queued work, use deterministic job identity, immutable input hashes,
recorded producer/parser versions, bounded attempts and idempotent effects.
Cloudflare Queues offers at-least-once delivery, not exactly once or ordering.
Carry small job references rather than media or large documents. A receiver
must reconcile a possibly completed external write before retrying it.
[Delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/),
[limits](https://developers.cloudflare.com/queues/platform/limits/)

## Customer feed customization

A saved feed definition should contain source families, topics or tasks,
include/exclude rules, languages, freshness window, evidence threshold,
ranking weights, maximum entries, output format and delivery schedule. Give
customers a preview and a reason for each included item. Keep feed versions
and snapshot IDs stable so an agent can ask only for changes.

Assign feeds to agents through a separate binding: agent identity, exact feed
version, permitted projection, cursor and revocable credential. The agent
does not inherit all of the customer's access. Test two customers and two
agents through creation, editing, stale cursors, revocation and failure.
Filters may narrow access; they never grant new access.

The cheaper Feeds offering serves maintained information and permitted
context exports. Components adds reusable tools, code, assets, environments
and full packages. Both use one account and explicit entitlements. Shared
source research can serve many selections; avoid a model call per customer
per item when a permitted shared summary is sufficient. Opt-in email or
webhooks need subscription, unsubscribe, signing, duplicate and delivery
records. A feed preview is not evidence that those features are live.

## Cloudflare capabilities and free allowances

The advantages are independent object storage, global public delivery,
small event-driven services and less machine maintenance. The main tradeoffs
are runtime limits, operation-based costs, consistency choices and another
provider boundary. Custom code can run on Cloudflare; migration does not
require using a hosted search ranking product.

| Service | Useful role | Limit or cost to preserve in planning |
| --- | --- | --- |
| [Workers](https://developers.cloudflare.com/workers/platform/pricing/) | Public routing, lightweight APIs, acquisition adapters | Free requests have CPU constraints; the paid platform starts at $5/month. Bound CPU and request populations, not only monthly traffic. |
| [Static Assets](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) | Public website and immutable frontend files | Static-asset requests are distinct from billable Worker invocations. Keep deployment assets synchronized with the origin revision. |
| [R2](https://developers.cloudflare.com/r2/pricing/) | Private source objects, component bodies and media | Standard storage includes 10 GB-month, one million Class A and ten million Class B operations free; usage beyond that is billed. Egress is free, storage and operations are not. |
| [D1](https://developers.cloudflare.com/d1/platform/limits/) | Feed definitions or qualified projections | Free databases are limited to 500 MB each; paid databases to 10 GB each. Avoid assuming one database holds every observation and full-text index forever. |
| [KV](https://developers.cloudflare.com/kv/concepts/how-kv-works/) | Replaceable public caches | Eventual consistency is unsuitable as the sole authority for immediate revocation, payment or exact quotas. |
| [Queues](https://developers.cloudflare.com/queues/platform/pricing/) | Bounded acquisition and processing jobs | Free includes 10,000 operations/day. A small message normally consumes multiple operations; retries add more. |
| [Workflows](https://developers.cloudflare.com/workflows/reference/pricing/) | Durable multi-stage coordination | The documented free allowance is 3,000 steps/day; Worker CPU and request billing remain relevant. |
| [Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/) | Optional summarization, classification and embeddings | 10,000 free neurons/day, not 10,000 tokens or unlimited calls. Some models need billing enabled; enforce run ceilings. |
| [AI Gateway](https://developers.cloudflare.com/ai-gateway/reference/pricing/) | Provider analytics, caching and rate limits | Core features are free; new gateways use Workers Logs pricing for logs. Prompts must not enter new logs without a permitted data policy. |
| [Vectorize](https://developers.cloudflare.com/vectorize/platform/pricing/) | Optional retrieval engine comparison | Free quota is five million stored dimensions and thirty million queried dimensions/month, not five million files. |
| [AI Search](https://developers.cloudflare.com/ai-search/platform/limits-pricing/) | A measured managed-search alternative | Free query/file limits are much smaller than the ten-million-file goal. Retain the custom search engine until an alternative wins the relevant tests. |
| [Turnstile](https://developers.cloudflare.com/turnstile/) | Browser abuse protection | It is not login. Keep interactive challenges out of normal authenticated agent/MCP traffic. |
| [Email Service](https://developers.cloudflare.com/email-service/platform/pricing/) | Candidate account mail or opted-in digests | Routing and sending differ. Current transactional sending beta has a paid-plan allowance; free sending is restricted to verified destinations. Qualify deliverability before replacing the existing sender. |

The Clef and Clef-flash Workers AI models expose bounded typed decisions and
probabilities over allowed answers. They are candidates for the existing
decision-engine slot, not an approval authority. The current SystemOneAdapter
expects a different route, so direct compatibility needs an adapter and
conformance evidence. No Clef call was made in this research.
[Clef-flash model contract](https://developers.cloudflare.com/workers-ai/models/clef-flash/)

### Identity

Baltor currently uses Supabase for customer sign-up and its own OAuth/API
permissions and account-origin protections. Cloudflare Access can protect
staff tools using an identity provider or supported one-time-password flow.
It does not supply Baltor's customer database, billing entitlements or scoped
agent access merely by protecting a hostname.
[Access identity integrations](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/)

A Cloudflare-hosted customer identity engine is feasible. Better Auth's
documented D1 support is one candidate to evaluate, including its use of
batch atomicity because D1 lacks interactive transactions. Keep it behind
the existing browser identity boundary. Require email ownership before a
password can bind an address, existing-user mapping, recovery, session
revocation, CSRF protection, key management and rollback before migrating
customers. Moving login should not delay a qualified storage or static-site
migration. [Better Auth D1 support](https://better-auth.com/blog/1-5)

### Cost checkpoints

The live 1,352,837 distinct files contain about 7.94 GB of payload bytes.
Those bytes alone fit inside R2's storage allowance, but retained versions,
metadata, other buckets and operation usage also count. At ten million
objects, initial writes alone can exceed the monthly free operation allowance
even when storage is small. Batching small immutable payloads into verified
packs is worth measuring as another body-store engine; it is not implemented
by the current one-object-per-digest adapter.

Keep Fly for the current custom index and authoritative record store until
measured alternatives preserve isolation, recovery and cost. Cloudflare
logs supplement those application records; they do not replace them.
No new recurring subscription follows from this research table.

## Benchmark intake

Collect benchmark observations, not a single universal model or hardware
ranking. Each result needs the exact model/revision, quantization, precision,
runtime, harness version, dataset version, task, metric direction, hardware,
batch/concurrency, date, source and measurement conditions. Missing fields
stay explicit. Compare like-for-like subsets and label vendor-reported,
third-party measured and Baltor-reproduced results separately.

Start with source-bound records from HELM, lm-evaluation-harness, LiveBench
and MLPerf. MLPerf Inference v6.1 is a current hardware-inference reference;
division and system configuration matter. LiveBench's code licence does not
replace the licences of each included dataset. Maintain coverage lists so
"all models" means tracked coverage and named gaps, not invented scores.
[HELM](https://crfm.stanford.edu/helm/index.html),
[evaluation harness](https://github.com/EleutherAI/lm-evaluation-harness),
[LiveBench datasheet](https://github.com/LiveBench/LiveBench/blob/main/docs/DATASHEET.md),
[MLPerf Inference v6.1](https://mlcommons.org/2026/09/chairs-mlperf-inference-v6-1/)

Search-provider adapters should also be compared rather than conflated:
SearXNG is a metasearch deployment choice, Brave and Ollama search have their
own APIs, RapidAPI is a marketplace of distinct providers, and a Google API
must be chosen by the actual supported product and eligibility. Register each
adapter's source contract, attribution, response bounds, quota, credential
reference and retention rules before enabling dispatch. A failed provider
does not authorize scraping its website or silently switching engines.
