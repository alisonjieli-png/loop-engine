# Shared research service landscape: prior art, verified claims and the first demonstration

Kind: dated research record, September 27, 2026, United States Eastern time.
The [roadmap](../roadmap/roadmap.yaml) remains the only task authority.
Nothing in this record approves library material, adopts an engine, installs
a dependency, calls a model, buys a service or makes a claim about customer
benefit. It reports what was read, what was observed in live public
interfaces and what engineering recommends.

The owner, September 27, 2026: engineers should never need to read
newsletters, blogs, directories or lists to keep up. Baltor researches once,
daily, and serves the result to thousands of harnesses. Research that takes an
engineer more than about five minutes across several sources is done once and
served as files (briefs, data files, tested Python or TypeScript). Volatile
facts, such as a stock price, are served as tools.

An outside analysis the owner shared states the rule as "Research once,
validate for defined conditions, distribute many times, and repeat only the
work invalidated by a meaningful change", and the product answer as "Here is
the currently qualified way to accomplish this task under your constraints,
with the implementation, evidence, limitations, and update history already
prepared."

This record does five things:

1. checks fourteen factual claims from that analysis against primary sources;
2. maps other products and open-source projects that already do parts of the
   idea;
3. recommends, for each stage of the pipeline, which systems to adopt as
   engines, which to keep as Baltor-native engines and which to watch as
   competitors, under the rule that every functional component sits behind a
   fixed, typed, versioned edge with swappable engines;
4. chooses the first capability family for an end-to-end demonstration;
5. states plainly where Baltor is differentiated and where it is not.

## Summary

- The analysis is accurate in substance. All fourteen claims hold at least
  in part; one of them, Exa's refresh behaviour, holds only in part. The
  corrections that matter for Baltor: Context7 answers a task question in
  one call only since September 22, 2026, and only through its web interface
  and software kit; Parallel schedules by frequency, not cron; the official
  MCP Registry is still a preview with no uptime or durability promise;
  Anthropic's tool search has needed no beta header since February 17, 2026;
  a GitHub `304` response is free only on an authorized request; and neither
  Sigstore nor The Update Framework says whether content is good.
- Every stage of the pipeline already has working products or open-source
  engines, and the market is consolidating: Snyk, Palo Alto Networks,
  Arcade.dev, OpenAI, Nebius and Elastic bought scanners, registries and
  search services in the last fifteen months, and one documentation service
  (Docfork) shut down. None of the products checked combines research done
  once across many sources, qualification published for declared conditions
  (harness, model class, route, hardware), immutable releases with durable
  withdrawal, and placement into many harnesses. Tessl comes closest; Claude
  Code now ships its own with-and-without plugin evaluator.
- The research literature supports conditional claims only. Curated, focused
  skills raised pass rates by 16.6 points on average in SkillsBench, and
  current documentation for changed interfaces raised accuracy by 10 to 20
  points. Generated context files, repository overviews and skills an agent
  writes for itself did not help and cost more.
- Baltor already runs the skeleton on main: a daily research watch, a daily
  protocol server directory that reads the registry incrementally, a daily
  model directory, content-addressed releases, durable withdrawals and an
  unattended daily release with rollback. The gaps: validators are recorded
  but not sent, pages are fingerprinted by their whole body, there is no
  edge for change detection or claim extraction, nothing is signed, and an
  installed copy is not checked again after a withdrawal.
- Two findings about Baltor's own data. The model directory records
  structured output as supported on Ollama Cloud, but Ollama's documentation
  has said "Ollama's Cloud currently does not support structured outputs"
  since April 22, 2026. And the terms of OpenRouter and Artificial Analysis
  sit uneasily with republishing their values daily; that use is recorded
  here as disputed.
- The first demonstration should use small-model selection for structured
  extraction, with retrieval and reranking second and document extraction
  third. Its trigger already fires daily, its local check is exact and needs
  no graphics processor, it runs within the owner's model authority, and it
  proves the north star directly: small models doing more.

## How this was checked, and its limits

- Every fact comes from a primary source: vendor documentation, pricing
  pages, official announcements and changelogs, official repositories,
  specifications and the papers themselves. Each carries its link and the
  source's own date. "Undated, read September 27" means the page shows no
  date.
- Public interfaces were read live on September 27: the OpenRouter Models
  API and its per-model endpoint listing, the official MCP Registry and the
  Hugging Face Hub API without a credential, and GitHub repository metadata
  (stars, licences, release dates) through the authenticated GitHub command
  line, read only.
- The web reading ran as seven parallel research passes. The author of this
  record repeated the reads that carry the most weight (named in each
  section) against the same primary pages.
- Nothing was purchased, installed or signed up for, and no model was called.
- Prices change often. Every price is a statement of the page on the day it
  was read, not a quotation Baltor can rely on later. All prices are in
  United States dollars.
- A vendor's statement about its own quality or results is reported as the
  vendor's statement. It is not independent evidence.
- Pages that required a sign-in, or refused automated reading, are marked.

## The fourteen claims, verified

| Number | Claim in the analysis | Verdict | What changes the claim |
|---|---|---|---|
| 1 | Context7: task search, versions, refresh, caching, search without resolving, price | Verified with corrections | Versions are exact tags; one-call search exists in the web interface and software kit since September 22, 2026, not in the protocol server tools; Pro now includes 2,000 calls per seat |
| 2 | Tessl: packages, governance, evaluations with and without context, observability, repository findings, setup agent, price | Mostly verified | "Tiles" became "plugins"; most governance is on the Enterprise plan; findings read skill files and manifests, not AGENTS.md quality |
| 3 | Microsoft Agent Package Manager: resolution, pinned commits and hashes, lockfiles, placement into harness folders | Verified | A project in Microsoft's GitHub organisation at version 0.32.0, not an announced product; `compile` handles instructions only |
| 4 | Official MCP Registry: aggregators and subregistries, `updated_since`, status changes, preview, no durability promise | Verified | Still a preview on September 27, 2026; its documents disagree on whether metadata can be erased |
| 5 | Parallel: scheduled monitoring of research results with structured output and webhooks | Verified with a correction | Frequency from one hour to 30 days, not cron |
| 6 | Exa Websets: scheduled discovery and refresh with cron and timezone | Partly verified | Refresh is not accepted by the request schema; Websets plan prices could not be read |
| 7 | Firecrawl: change tracking with snapshots and line or field diffs, scheduled monitoring | Verified | Native scheduled monitors exist since May 26, 2026 |
| 8 | Augment Context Engine over MCP, local and remote | Verified | Its improvement numbers are Augment's own and disagree between its pages |
| 9 | Hugging Face Hub and OpenRouter metadata | Verified, with a split | Hugging Face serving price and context length come from its router, not the model card; OpenRouter latency and throughput need a key |
| 10 | OpenAI and Anthropic tool search and deferred loading | Verified with corrections | Anthropic's needs no beta header since February 17, 2026; Claude Code defers all protocol server tools by default; GPT-5.4 nano lacks it |
| 11 | "Evaluating AGENTS.md", revised June 23, 2026 | Verified | Version 2 softened version 1's conclusion |
| 12 | Agentic Context Engineering | Verified | The headline gains are margins over other adaptation methods, not over the unadapted agent |
| 13 | GitHub: webhooks over polling, free `304` responses, public is not open source | Verified | A `304` is free only on an authorized request |
| 14 | Sigstore and The Update Framework | Verified | Neither says whether content is safe or good |

### 1. Context7

Verdict: verified, with two corrections. Versions are exact tags, and only
the web interface and software kit (since September 22, 2026) skip the
library-resolution step; the protocol server tools still resolve first.

Observed:

- The [API guide](https://context7.com/docs/api-guide) (source changed
  September 22, 2026) lists `GET /api/v3/search` ("Find relevant
  documentation without resolving a library first"), the older library
  search and context endpoints, and `POST /api/v1/refresh`. In the context
  endpoint, `query` is the "User's original question or task - used for
  intelligent relevance ranking". The earlier `topic` parameter was removed
  in the protocol server's version 2.0.0 (December 29, 2025).
- Versions: "You can pin a specific version with either
  `/owner/repo/<version>` or `/owner/repo@<version>`", for example
  `/vercel/next.js/v15.1.8`. No range form such as `v15.x` is documented.
- Refresh: `POST /v1/refresh` will "Trigger a refresh of an existing library
  to fetch the latest documentation"; the
  [library updates page](https://context7.com/docs/library-updates) (changed
  May 5, 2026) says logged-in users can refresh any library from its page,
  that the top 100 libraries refresh daily and the rest every 45 days, and
  that private libraries are not refreshed automatically.
- Caching: "Documentation updates are relatively infrequent, so caching
  responses for several hours or days reduces API calls and improves
  performance." A live response carried
  `cache-control: public, max-age=0, must-revalidate`, so caching is left to
  the client.
- Search without resolving: the [Search API page](https://context7.com/docs/search-api)
  (re-read by the author of this record) says "You send a question, and
  Context7 picks the relevant libraries, searches them, and returns the best
  snippets in one request. No library ID is needed." A version is "Strict
  with one library, a preference with several." Upstash announced it on
  [September 22, 2026](https://upstash.com/blog/context7-search): "Until
  today, the only way to use it was a two-step API built for looking up one
  library at a time." The protocol server package 4.1.1 (September 14, 2026)
  still exposes only `resolve-library-id` and `query-docs`.
- Pricing ([plans](https://context7.com/plans), undated, read September 27 by
  two separate reads): Free, 1,000 calls a month, then 20 bonus calls a day;
  Pro, 10 dollars per seat a month with 2,000 calls per seat, then 5
  dollars per 1,000 calls, and private repositories at 5 dollars per million
  tokens parsed; Enterprise from 30 dollars per user a month for small
  teams. Search calls cost the same as other calls. The
  [September 22 market review](ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md)
  recorded 5,000 calls per seat for Pro; the page now says 2,000.
- Traction: `upstash/context7` had 62,469 stars on September 27 (GitHub
  interface). The npm package `@upstash/context7-mcp` had 3,278,546
  downloads between August 28 and September 26, 2026. Upstash publishes no
  library count beyond "thousands"; the public sitemaps list 106,568 library
  pages (a count made for this record, not a vendor figure). The repository
  README says the backend, parsing and crawling engines "are private".

Inference: Context7 is solved, cheap, and moving toward one-call answers to a
task question. Its per-call price above the allowance (5 dollars per 1,000)
is a useful reference for Baltor's per-item unit.

### 2. Tessl

Verdict: mostly verified. Packages are now called plugins ("tiles" is the
legacy format), governance controls are mainly on the Enterprise plan, and
there is no dedicated quality score for AGENTS.md files.

Observed (documentation pages undated, site updated September 25, 2026):

- The [overview](https://docs.tessl.io/overview/readme) lists a registry and
  package manager ("Discover, install, version, and roll back skills and
  plugins like any other dependency"), governance ("RBAC controls who can
  create, publish, and view skills, while install and publish policies and
  required skills enforce your standards across every workspace"),
  evaluations, observability ("See where skills actually activate across
  agent sessions, not just where they're installed"), context and findings
  across repositories, and the Tessl Agent, which "autonomously monitors and
  improves your agentic setup" (open beta).
- The [migration page](https://docs.tessl.io/use/tile-to-plugin-migration):
  "Tessl is transitioning from **tiles** to **plugins**". Plugins bundle
  skills, rules, commands, protocol servers and hooks; `tessl.json` records
  installed dependencies.
- Evaluations: "An evaluation runs an agent on real tasks twice, once
  without the skill and once with it, then scores the difference." Tasks can
  be rebuilt from a customer's own commits. Registry pages show a lift figure
  for each skill, such as "1.14 x Agent success vs baseline".
- Governance: install policies at three levels where "the tightest one wins";
  "A source that hits the block threshold cannot be installed. There is no
  override." Security scores come from Snyk.
- Repository findings read only `skill.md` files and manifests; evaluations
  can measure "context files against real tasks taken from your codebase's
  commit history". No AGENTS.md quality score was found.
- Setup: `tessl init` will "Set up your repository and configure your coding
  agent" for Claude Code, Cursor, Codex, Gemini CLI, Antigravity and GitHub
  Copilot, among others.
- Pricing ([pricing page](https://tessl.io/pricing), undated, read September
  27 by two separate reads): Free, 1,000 credits a month; Team, 100
  dollars a month with five times the credits; Enterprise, a platform fee
  plus credits. No seat charge. Publishing and installing cost nothing;
  reviews, evaluations and agent runs use credits. Install and publish
  policies, audit logs and single sign-on are Enterprise features.
- Traction: a 100 million dollar Series A led by Index Ventures and a 25
  million dollar seed round (press release, November 14, 2024). The public
  search interface returned 49,159 entries on September 27 (47,472 skills
  and 1,687 tiles), many of them indexed automatically from GitHub. No user
  numbers are published.

Inference: Tessl is the closest analogue to Baltor: a registry, measured
lift with and without a skill, install policies and activation telemetry.
Its evaluations are per skill and per customer task; no public, dated
qualification across harness, model class and hardware was found.

### 3. Microsoft Agent Package Manager

Verdict: verified that it exists and does what the analysis says, with two
nuances. `apm compile` handles only instructions (installation places the
other primitives), and it is a project in Microsoft's GitHub organisation,
not an announced Microsoft product.

Observed:

- [microsoft/apm](https://github.com/microsoft/apm): "An open-source,
  community-driven dependency manager for AI agents." MIT licence,
  "Copyright (c) Microsoft Corporation". Latest release 0.32.0 on September
  25, 2026; first release August 27, 2025. 3,910 stars and 101 contributors
  on September 27. Support "is limited to" GitHub issues and discussions.
- [Documentation](https://microsoft.github.io/apm/llms-full.txt): "APM
  resolves the full transitive closure (packages and MCP servers), applies
  the policy gate to every node, and records each one in the lockfile." The
  lockfile `apm.lock.yaml` "Pins exact commit SHAs and per-file content
  hashes so every `apm install` from the same lockfile produces
  byte-identical output", with fields such as `resolved_commit`,
  `content_hash`, `deployed_files` and `deployed_file_hashes`.
- Placement: `apm install` "compiles primitives into each declared harness
  directory"; "Compile only handles **instructions**". Targets named: Copilot,
  Claude, Grok Build, Cursor, Codex, Gemini, OpenCode, Windsurf and Kiro, with
  Antigravity and Hermes on request. Primitives include instructions,
  prompts, agents, skills, hooks, commands, plugins and protocol servers.
- Maturity: the lockfile governance is described as "stable and
  production-ready"; the policy engine is "in **early preview**"; registries
  sit behind experimental flags.

Inference: this matches the [September 24 survey](REGISTRY-AND-PACKAGE-INFRASTRUCTURE-SURVEY-2026-09-24.md),
which decided to trial it behind the `material_install_layout` edge. The
decision stands.

### 4. The official MCP Registry

Verdict: verified on every part. The registry is still a preview.

Observed:

- The [aggregators guide](https://modelcontextprotocol.io/registry/registry-aggregators)
  (source last changed March 12, 2026; re-read by the author of this record
  on September 27) says aggregators "are expected to scrape data on a regular
  but infrequent basis (e.g., once per hour), and persist the data in their
  own data store", and that "A subregistry is an aggregator that also
  implements the OpenAPI spec defined by the MCP Registry." A subregistry may
  add its own metadata under `_meta`, such as ratings or security scan
  results.
- `updated_since` is documented on `GET /v0.1/servers` in RFC 3339 format.
  The [official API document](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)
  (last changed August 10, 2026) adds that `include_deleted` becomes true
  automatically when `updated_since` is given. A live read on September 27
  returned records updated on September 26. Paging 4,000 records updated
  since September 15 returned 3,819 active, 100 deprecated and 81 deleted, so
  deletions do arrive through incremental reads.
- `status` takes the values `active`, `deprecated` and `deleted`. The guide:
  "Server metadata is generally immutable, except for the `status` field",
  "We recommend that aggregators keep their copy of each server's `status`
  up to date", and a deleted server "might be spam, malware, or illegal".
  Publishers can mark their own entries deleted (changelog, February 27,
  2026).
- Preview: the registry launched "in preview" on
  [September 8, 2025](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/).
  The interface has been frozen at version 0.1 since October 24, 2025. Every
  registry page read on September 27 carries: "The MCP Registry is currently
  in preview. Breaking changes or data resets may occur before general
  availability." A March 16, 2026 proposal to drop the preview wording was
  closed; the maintainer wrote that the registry "is actually still in
  preview and hasn't reached general availability yet"
  ([pull request 1058](https://github.com/modelcontextprotocol/registry/pull/1058)).
- Durability: "The MCP Registry **does not provide uptime or data durability
  guarantees**" (aggregators guide). The terms say "we don't guarantee the
  accuracy, completeness, safety, durability, or availability of the
  Registry". The moderation policy says "consumers should assume
  minimal-to-no moderation".
- Two registry documents disagree: the frequently asked questions (September
  5, 2026) say metadata "is never permanently removed", while the moderation
  policy (January 22, 2026) says "In extreme cases, we may overwrite or
  erase the server's metadata."

Inference: Baltor's directory already follows the guide: incremental reads
with an overlap, and deprecated and deleted servers left out. It should keep
its own copy of every record it serves, plan for a full re-read after a data
reset, and treat the registry's data as publisher declarations, not reviewed
facts. Baltor could become a subregistry that adds its own reviewed
metadata under its own `_meta` key.

### 5. Parallel: scheduled monitoring of research results

Verdict: verified, with one correction. Schedules are a fixed frequency from
one hour to 30 days, not a cron expression.

Observed:

- The [snapshot monitor quickstart](https://docs.parallel.ai/monitor-api/quickstart-snapshot)
  (undated; re-read by the author of this record): a snapshot monitor
  "watches the output of a Task Run on a schedule. Each execution re-runs
  the same task and compares the result against the previous snapshot."
  With a JSON schema, "the JSON schema acts as a stable template the monitor
  can diff field-by-field across runs". A material change is described by
  example: "new data, a removed field, a significant value shift". The
  webhook carries `changed_output` (only the changed fields, each with its
  citations and reasoning) and `previous_output`.
- The [create-monitor reference](https://docs.parallel.ai/api-reference/monitor/create-monitor)
  (undated): frequency "Must be between 1h and 30d (inclusive)", in hours,
  days or weeks. Webhooks are signed and include `monitor.event.detected`,
  `monitor.execution.completed` and `monitor.execution.failed`.
- The [changelog](https://docs.parallel.ai/resources/changelog): public alpha
  on November 13, 2025; structured outputs for monitors on January 21, 2026;
  "generally available" on May 6, 2026. A monitor "tracks new updates from
  the time of creation", with no history.
- Pricing ([pricing page](https://docs.parallel.ai/getting-started/pricing),
  undated, read September 27): monitors cost 3 dollars (lite) or 10 dollars
  (base) per 1,000 executions. Task runs cost 5 dollars (lite) to 2,400
  dollars (ultra8x) per 1,000 successful runs. Search costs 1 or 5 dollars per
  1,000 requests. Eligible organisations with a card get 5 dollars of free
  credit a month (July 15, 2026). How a snapshot re-run is billed when the
  original task used a larger processor is not stated.
- Traction: a 100 million dollar Series A at a 740 million dollar valuation
  (November 12, 2025) and a 100 million dollar Series B at a 2 billion dollar
  valuation (April 29, 2026), which states "More than 100,000 developers are
  building on Parallel today."

Inference: this is the closest managed match to "repeat only the work
invalidated by a meaningful change" for questions without a single source
page. It detects change by redoing the research, so every check costs an
execution even when nothing changed.

### 6. Exa Websets: scheduled discovery and refresh

Verdict: partly verified. Cron and timezone scheduling and the search
behaviour are real; refresh is described but not accepted by the request
schema; Websets plan prices could not be read.

Observed:

- The [Websets monitor page](https://exa.ai/docs/websets/api/monitors/create-a-monitor)
  (undated) says "Configure `cron` expressions and `timezone` for precise
  scheduling control" and "Run `refresh` operations to update items contents
  and enrichments". The cadence must be "a valid Unix cron with 5 fields"
  and "must trigger at most once per day"; the timezone defaults to
  `Etc/UTC`.
- The request schema in [Exa's specification](https://exa.ai/docs/exa-spec.yaml)
  (version 2.0.0), which Exa calls the source of truth, accepts only the
  `search` behaviour. "Refresh" appears only in prose and as a run type.
- A separate Monitors interface ([changelog](https://exa.ai/docs/changelog),
  March 30, 2026) runs searches on an interval of at least one hour and
  delivers results "deduplicated against previous runs so you only get new
  content", with structured output and citations.
- Pricing ([API pricing](https://exa.ai/docs/admin/pricing), undated, read
  September 27): search 7 dollars per 1,000 requests; contents 1 dollar per
  1,000 pages per content type; answer 5 dollars; monitors 15 dollars per
  1,000 requests. The Websets billing pages returned HTTP 429 to automated
  reads, so Websets plan prices are unverified here.
- Traction: an 85 million dollar Series B (September 3, 2025) and a 250
  million dollar round at a 2.2 billion dollar valuation (May 20, 2026), citing
  "over 400,000 developers".

Inference: Exa discovers new items; it does not compare versions of a page
Baltor already knows. It fits the discover stage, not the change-detect
stage.

### 7. Firecrawl: change tracking and scheduled monitoring

Verdict: verified. Firecrawl also has native scheduled monitoring since May
26, 2026.

Observed:

- The [change tracking page](https://docs.firecrawl.dev/features/change-tracking)
  (undated; re-read by the author of this record): include `markdown` and
  `changeTracking` in `formats`. Git-diff mode "Returns line-by-line changes
  in a format similar to `git diff`"; JSON mode "Extracts specific fields from
  both the current and previous version of the page using a schema you
  define". `changeStatus` is `new`, `same`, `changed` or `removed`.
  "Previous scrapes are matched on exact source URL, team ID, `markdown`
  format, and `tag`", and "Snapshots are stored persistently and do not
  expire." Tags keep "separate tracking histories" for one address.
- Cost: "JSON mode uses LLM extraction and costs **5 credits per page**";
  basic and git-diff tracking cost nothing extra.
- The [monitoring page](https://docs.firecrawl.dev/features/monitoring):
  "Schedules can be provided as cron or as simple natural language text",
  with a timezone and a five-minute minimum. A monitor holds 1 to 50 targets;
  an optional plain-language goal lets a model judge whether a change
  matters. Announced as "/monitor" on May 26, 2026 in the
  [changelog](https://www.firecrawl.dev/changelog).
- Plans ([pricing](https://www.firecrawl.dev/pricing), "Effective September 4,
  2026"): Free, 1,000 credits a month; Hobby, 19 dollars a month for 5,000;
  Standard, 83 dollars a month billed yearly for 100,000; larger plans above.
  The pricing page says the monitor's extraction engine bills 7 credits per
  page while the monitoring documentation implies 5; which applies was not
  resolved.
- Licence and traction: AGPL-3.0 for the server, MIT for the software kits;
  185,393 stars on September 27; a 75 million dollar Series B announced on
  September 22, 2026, stating "Over 1.5 million users".

Inference: Firecrawl is the only service checked that compares versions of a
known page without a model call (line diffs), and with a schema when a model
call is acceptable. The AGPL licence matters only if Baltor runs a modified
copy as a network service; calling the hosted interface does not trigger it.

### 8. Augment Context Engine over MCP

Verdict: verified for the product, both modes, harnesses and price. The
evaluation numbers are Augment's own and disagree between its pages.

Observed:

- Announced on [February 6, 2026](https://www.augmentcode.com/blog/context-engine-mcp-now-live)
  (updated June 18, 2026): "Today we're launching Context Engine MCP to bring
  Augment's industry-leading semantic search to every MCP-compatible agent."
- The [documentation](https://docs.augmentcode.com/context-services/mcp/overview)
  (undated) offers a local mode, "Run the Auggie CLI locally as an MCP server
  (stdio)", which indexes the working directory, and a remote mode, "Connect
  to Augment-hosted Context Engine over HTTP", which indexes repositories
  chosen through Augment's GitHub application. Quickstarts cover Claude Code,
  Codex, Cursor, Zed, GitHub Copilot, OpenCode, Kiro, Gemini CLI and others.
- Price: queries are billed as "LLM tokens at the provider's public API list
  price plus the 40% service fee", about 3 to 6 cents a query; plans start
  at 20 dollars a month ([pricing](https://www.augmentcode.com/pricing),
  undated, read September 27).
- Augment reports "300 Elasticsearch PRs, each with 3 different prompts" and
  "Claude Code + Opus 4.5: 80% improvement". Its summary says "70%+ across
  Claude Code, Cursor, and Codex" but gives no Codex number, and its product
  page credits the same figures to Opus 4.6. No independent evaluation was
  found.

Inference: Augment retrieves the customer's own code. It is a possible engine
behind Baltor's retrieval edges for a customer's repository, not a competing
library of harness files.

### 9. Hugging Face Hub API and OpenRouter models API

Verdict: verified for OpenRouter. For Hugging Face, model metadata is
verified; serving price and context length come from a separate router, not
from the model card.

Observed, Hugging Face:

- Model information, documented in the
  [huggingface_hub 2.0.0 reference](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api)
  (package released September 24, 2026), includes `id`, `author`,
  `downloads` (last 30 days), `likes`, `tags`, `pipeline_tag`,
  `library_name`, `card_data` ("Model Card Metadata"), `siblings`,
  `safetensors` parameter counts, `gated`, `last_modified`, `inference`
  ("Warm if the model is served by at least one provider") and
  `inference_provider_mapping`.
- The licence is declared in the model card metadata and repeated as a
  `license:` tag. A live read of `Qwen/Qwen3-8B` on September 27 showed both.
  Context length is not a Hub field; it sits in the repository's
  `config.json` (`max_position_embeddings`).
- Serving facts come from the Inference Providers router
  ([documentation](https://huggingface.co/docs/inference-providers/hub-api),
  last changed July 9, 2026): per provider, `status`, `context_length`,
  `pricing` in dollars per million tokens, `supports_tools`,
  `supports_structured_output`, `first_token_latency_ms` and `throughput`,
  "when available". A live read of `router.huggingface.co/v1/models` on
  September 27 returned 138 models and 332 provider entries; 218 entries
  carried a price and 211 a context length.

Observed, OpenRouter (live reads on September 27 by the author of this
record, confirmed against the
[models guide](https://openrouter.ai/docs/guides/overview/models) and the
[API reference](https://openrouter.ai/docs/api/api-reference/endpoints/list-all-endpoints-for-a-model),
both undated):

- `GET /api/v1/models` returned 458 models. Each model carries `id`,
  `canonical_slug`, `name`, `created`, `description`, `context_length`,
  `architecture`, `pricing`, `top_provider`, `per_request_limits`,
  `supported_parameters`, `default_parameters`, `knowledge_cutoff`,
  `expiration_date`, `hugging_face_id` and a link to its endpoint listing.
  251 models carried a `benchmarks` object with Artificial Analysis
  intelligence, coding and agentic indexes, and 326 a `reasoning` object.
  Price fields include prompt, completion, cache reads and writes, internal
  reasoning and web search, "in USD per token/request/unit".
- The per-model endpoint listing gives each provider's name, quantization,
  context length, maximum prompt and completion tokens, price, status and
  uptime over the last 5 minutes, 30 minutes and day. Latency and
  throughput exist but are "Only visible when authenticated with an API key
  or cookie"; they were null in the anonymous reads.

Inference: model-card facts (licence, parameters, task) belong to the model;
serving facts (price, context length, uptime) belong to a model and provider
pair and change daily. The same model showed a context length of 40,960
through one Hugging Face provider and 131,072 through OpenRouter. Baltor's
model directory reads the Hub interface and OpenRouter's interfaces and dates
each fact; the Hugging Face router is a further source of serving facts per
provider that it does not read yet.

### 10. Tool search and deferred tool loading

Verdict: verified. Two details have changed: Anthropic's tool search no
longer needs a beta header, and Claude Code now defers every protocol server
tool by default.

Observed:

- OpenAI's [tool search guide](https://developers.openai.com/api/docs/guides/tools-tool-search)
  (undated, read September 27): "In the Responses API, only `gpt-5.4` and
  later models support `tool_search`." Functions are marked
  `defer_loading: true`; namespaces group them, with advice to keep each
  under 10 functions. Search runs hosted or in the client. The
  [changelog](https://developers.openai.com/api/docs/changelog) adds tool
  search on March 5, 2026 and notes on March 17, 2026 that GPT-5.4 nano
  "does not support tool search". No limit on the number of tools is stated.
- Anthropic's [tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
  (undated, read September 27) has two versions,
  `tool_search_tool_regex_20251119` and `tool_search_tool_bm25_20251119`.
  Tools are marked `defer_loading: true`, and at least one tool must stay
  loaded. Limits: up to 10,000 deferred tools per request; five results by
  default. It launched as a public beta on November 24, 2025, and the
  [release notes](https://platform.claude.com/docs/en/release-notes/overview)
  of February 17, 2026 say it "no longer require[s] a beta header". The
  Claude API reference bundled with Claude Code agrees: no beta
  header, and available on the Claude API, Amazon Bedrock (through
  InvokeModel only), Google Vertex AI and Microsoft Foundry.
- Claude Code's [protocol server page](https://code.claude.com/docs/en/mcp)
  (undated, read September 27): "Tool search is enabled by default: MCP tools
  are deferred and discovered on demand." The `ENABLE_TOOL_SEARCH` setting
  keeps an `auto` mode that loads tools up front while their definitions
  total less than 10 percent of the context window. The change that made
  deferral the default is not in the changelog found.

Inference: both major providers now let a harness hold thousands of tools
and load a few on demand. For Baltor this lowers the cost of offering many
small tools, but it moves the problem to retrieval: a tool that is never
found is never used. Tool names and descriptions become search surfaces
that Baltor must write and test, and LiveMCPBench found retrieval errors
behind nearly half of the failures.

### 11. The paper "Evaluating AGENTS.md"

Verdict: verified. The revision date in the analysis is correct.

Observed:

- The paper is "Evaluating AGENTS.md: Are Repository-Level Context Files
  Helpful for Coding Agents?" by Thibaud Gloaguen, Niels Mündler and Martin
  Vechev (ETH Zurich) with Mark Müller and Veselin Raychev (LogicStar.ai),
  [arXiv 2602.11988](https://arxiv.org/abs/2602.11988). Version 1 is dated
  February 12, 2026 and version 2 June 23, 2026. There is no third version
  and no venue is stated. Read on arXiv by the author of this record.
- Abstract of version 2: "providing context files does not generally improve
  task success rates, while increasing inference cost by over 20% on
  average". It adds that "while instructions in the context files are well
  followed by coding agents, repository overviews, although popular and
  recommended by model providers, are not helpful."
- Settings: SWE-bench Lite (300 tasks, 11 Python repositories, context files
  generated by a language model only) and a new benchmark of 138 tasks from
  12 Python repositories that each carry a developer-written context file
  (named AGENTbench in version 1 and CTXbench in version 2). Agents and
  models: Claude Code with Sonnet 4.5, Codex with GPT-5.2 and GPT-5.1 mini,
  and Qwen Code with Qwen3-30B-Coder. One sample per configuration.
- Generated context files changed the resolution rate by an average of minus
  0.5 points on SWE-bench Lite and minus 2 points on the new benchmark, with
  p values of 0.87 and 0.37, and raised cost by 20 and 23 percent. Developer
  files changed it by an average of plus 2.4 points (p of 21 percent) and
  raised steps by 3.34 on average and cost by at most 19 percent.
- Version 1 said that context files "tend to reduce task success rates";
  version 2 softened this to "does not generally improve". Version 1's
  introduction gave plus 4 percent for developer files and minus 3 percent
  for generated files; version 2 replaced those with significance tests and
  added ablations. Removing all other documentation from the repository made
  generated files help by 2.7 percent on average, which the authors read as
  context files largely repeating existing documentation.
- Recommendation: omit generated context files for now; keep human-written
  files to instructions that the README does not already give, and evaluate
  them before adoption. Stated limitation: Python only, and only task
  resolution was measured.

Inference: with 138 tasks and one sample per cell, a single cell's standard
error on the new benchmark is about 4 points, so none of the per-agent
differences is strong evidence on its own. The paper supports a narrow rule:
a served instruction file must carry information the repository does not
already hold, and its benefit must be measured, not assumed.

### 12. Agentic Context Engineering

Verdict: verified, with one wording caution about the headline numbers.

Observed:

- "Agentic Context Engineering: Evolving Contexts for Self-Improving Language
  Models", [arXiv 2510.04618](https://arxiv.org/abs/2510.04618), Stanford
  University, SambaNova Systems and the University of California, Berkeley.
  Version 1 is dated October 6, 2025, version 3 March 29, 2026. It was
  published at the International Conference on Learning Representations 2026
  ([proceedings page](https://proceedings.iclr.cc/paper_files/paper/2026/hash/8a94ff6f922d995d7d3f4ebf4143e442-Abstract-Conference.html)).
  Code: [ace-agent/ace](https://github.com/ace-agent/ace), Apache-2.0,
  created November 16, 2025.
- It proposes treating a context as a playbook of itemised entries that
  three roles maintain: a generator that produces reasoning traces, a
  reflector that draws lessons from successes and errors, and a curator that
  merges those lessons as small delta updates. New entries are merged "by
  lightweight, non-LLM logic", and a grow-and-refine step removes duplicates
  by embedding similarity. It names two failure modes of earlier methods:
  "brevity bias" and "context collapse" (in one run a context of 18,282
  tokens collapsed to 122 tokens in one rewrite and accuracy fell below the
  baseline).
- Measured on AppWorld (agents) and on FiNER and Formula (finance) with
  DeepSeek-V3.1 in all three roles. The headline "+10.6% on agents and +8.6%
  on finance" is a margin over the strongest adaptation baselines; the gain
  over the unadapted agent on AppWorld is about 17 points (42.4 to 59.4).
  Adaptation latency fell 82.3 percent against GEPA offline and 91.5 percent
  against Dynamic Cheatsheet online. The paper says its agent "matches the
  top-1-ranked IBM CUGA (60.3%)" on the AppWorld leaderboard of September 20,
  2025 while using a smaller open model.
- It can adapt from execution feedback without labels on AppWorld. In
  finance, without labels or reliable execution signals, performance can
  fall below the base (online, unlabelled FiNER was 3.4 points below).
  Stated limitation: it relies on "a reasonably strong Reflector".

Inference: Agentic Context Engineering is a method for improving one
deployment's context from its own feedback. Baltor's service is the shared
counterpart: the curated playbook is researched once and served to many
deployments. The two combine. A served package can be the starting playbook,
and a customer's local reflection can improve it without Baltor seeing the
customer's data. The finance result is the warning: without a reliable
signal, self-updating context can make results worse, which is why Baltor
keeps independent acceptance separate from generation.

### 13. GitHub guidance on webhooks, conditional requests and licences

Verdict: verified, with one condition that matters: a `304` is free only on
an authorized request.

Observed (both pages re-read by the author of this record on September 27):

- [Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)
  (source last changed July 27, 2026): "You should subscribe to webhook
  events instead of polling the API for data." And: "Making a conditional
  request does not count against your primary rate limit if a `304`
  response is returned and the request was made while correctly authorized
  with an `Authorization` header."
- [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
  (source last changed March 12, 2026): "Public repositories on GitHub are
  often used to share open source software. For your repository to truly be
  open source, you'll need to license it". Without a licence "the default
  copyright laws apply", and "no one may reproduce, distribute, or create
  derivative works from your work." GitHub's terms let other users view and
  fork a public repository.

Inference: the saving from conditional requests applies only to
authenticated requests. Baltor's research watch reads without a credential
and sends no validators today, so it gains nothing from `ETag` yet. The
licence statement confirms the owner's existing rule: material without a
licence that allows copying is used only as inspiration for an original
rewrite.

### 14. Sigstore and The Update Framework

Verdict: verified. Both establish who signed and whether the client's view
is current; neither establishes that the content is safe or good.

Observed:

- Sigstore's [security model](https://docs.sigstore.dev/about/security/) and
  [threat model](https://docs.sigstore.dev/about/threat-model/) (sources last
  changed September 30, 2025): identity comes from OpenID Connect, and "The
  identity and issuer associated with the OIDC token is embedded in the
  short-lived certificate issued by Sigstore's Certificate Authority,
  Fulcio." The Rekor log "is append-only". A signature "guarantees that the
  signature was created by a signer who successfully authenticated to
  Sigstore using that identity at that time." It "does not guarantee ...
  that the signer should have signed the given message, or that the
  software artifact in question is 'good'". "OIDC account compromise is not
  handled by Sigstore", and without third parties monitoring the logs,
  misbehaviour "might go undetected". Verification must pin the expected
  identity and issuer.
- The Update Framework's [security page](https://theupdateframework.io/docs/security/)
  (last modified October 12, 2024) and
  [specification 1.0.36](https://theupdateframework.github.io/specification/latest/)
  (August 5, 2026) protect against arbitrary installation, rollback,
  fast-forward, indefinite freeze, endless data, mix-and-match and related
  attacks, through separate root, targets, snapshot and timestamp roles,
  signature thresholds and expiry ("Clients MUST NOT trust an expired
  file."). Limits: "Target files are opaque to the framework"; if enough keys
  are compromised, "the best that can be done is to limit the number of
  users who are affected"; recovering from a root compromise "is nearly
  impossible".

Inference: signing tells a harness that a release came from Baltor's
release identity; freshness metadata tells it that no one is replaying an old
release or hiding a withdrawal. Whether the material is good still rests on
Baltor's independent review and the local acceptance check.

## What other primary research adds

These were read on arXiv or the publisher's page. The author of this record
re-read the SkillsBench abstract and history.

| Study | Date | Main finding | Limitation |
|---|---|---|---|
| [SkillsBench](https://arxiv.org/abs/2602.12670) | version 4, June 14, 2026 | Curated skills raise the average pass rate "from 33.9% to 50.5%" across 18 model and harness configurations; focused skills with at most three modules beat larger bundles; smaller models with skills can match larger models without them. In the full text, skills the agent wrote for itself scored 8.1 to 11.5 points below no skills. | Terminal tasks only; added context length may explain part of the gain |
| [Agent Skills in the Wild](https://arxiv.org/abs/2601.10338) | January 15, 2026 | Of 31,132 public skills, "26.1% of skills contain at least one vulnerability", and 5.2 percent show high-severity patterns suggesting malicious intent. Skills that bundle scripts were 2.12 times as likely to be vulnerable. | Pattern detector with 86.7 percent precision; intent inferred, not confirmed |
| [Under the Hood of SKILL.md](https://arxiv.org/abs/2605.11418) | May 12, 2026 | Short text triggers in real ClawHub skills manipulated embedding-based discovery (up to 80 percent top-ten placement) and model selection (77.6 percent of paired trials). | Attack study, not a prevalence measure |
| [SkillRet](https://arxiv.org/abs/2605.05726) | version 3, September 1, 2026 | Over 16,129 public skills, "skill retrieval remains far from solved"; a tuned retriever gained 12.9 points of nDCG at 10 over the best prior one. | Retrieval only, not task success |
| [Chroma, Context Rot](https://www.trychroma.com/research/context-rot) | July 14, 2025 | Across 18 models, performance "grows increasingly unreliable as input length grows"; focused prompts of about 300 tokens beat full prompts of about 113,000 tokens. | Technical report, simple tasks |
| [RAG-MCP](https://arxiv.org/abs/2505.03275) | May 6, 2025 | Retrieving tool descriptions first "more than triples tool selection accuracy (43.13% vs 13.62% baseline)" and halves prompt tokens. | One model, one subset, not peer reviewed |
| [LiveMCPBench](https://arxiv.org/abs/2508.01780) | version 2, February 26, 2026 | Over 527 tools, "Retrieval errors account for nearly half of all failures". | 95 tasks |
| [GitChameleon 2.0](https://arxiv.org/abs/2507.12367) | July 2025; Association for Computational Linguistics 2026 | Version-specific problems: documentation retrieval raised the best model from 48.5 to 58.5 percent. | Python libraries only |
| [LibEvoBench](https://arxiv.org/abs/2606.25402) | June 24, 2026 | Putting the correct interface documentation in the prompt gave a consistent gain of 10 to 20 points in calling accuracy; stating the version alone gave no gain. | Workshop paper |
| [CodeUpdateArena](https://arxiv.org/abs/2407.06249) | version 3, April 3, 2025 | Prepending update documentation did not let older open code models use the change. | Older models, synthetic updates |

Inference: the evidence supports conditional claims only. Focused, curated,
current material helps; generated overviews, self-written skills and
material that repeats the repository cost more and do not help. Retrieval is
its own failure point, and public skill registries carry measured risk. A
general claim that served context raises success is not supported, so every
Baltor benefit claim needs its own matched evaluation.

## Who already does parts of this

Observed on September 27 unless another date is given. Prices come from each
vendor's own page (most are undated). Traction figures are the vendor's
claims where marked "(claim)", GitHub stars on September 27, or counts made
for this record from public interfaces ("counted"). A research pass made most
of these reads; the author of this record re-read the entries marked
"(re-read)".

### Documentation served to agents

| Name | What it does | Price | Traction | Source |
|---|---|---|---|---|
| Context7 | See claim 1 | Free to 10 dollars a seat | 62,469 stars | [context7.com/plans](https://context7.com/plans) (re-read) |
| Context Hub (Andrew Ng) | Command line `chub` serving curated, versioned API documentation; agents can annotate locally and send feedback votes; new documents arrive as pull requests | Free, MIT | 13,982 stars | [andrewyng/context-hub](https://github.com/andrewyng/context-hub) |
| DeepWiki (Cognition) | Remote protocol server over generated wikis of public GitHub repositories | Free, "no-authentication-required" | None published | [DeepWiki MCP](https://docs.devin.ai/work-with-devin/deepwiki-mcp) |
| GitMCP | Remote protocol server for any GitHub repository; reads `llms.txt` and the README | Free, Apache-2.0 | 8,433 stars | [idosal/git-mcp](https://github.com/idosal/git-mcp) |
| Ref | Documentation search and page reading for public and private sources | Free 200 credits once; 50 dollars a month for 6,000 | 1,176 stars | [Ref pricing](https://docs.ref.tools/usage/pricing) |
| Nia | Indexes repositories, documentation and PDFs for agents | Free tier of 50 queries a month; from 15 dollars a month | Funding page refused automated reads (unverified) | [Nia pricing](https://docs.trynia.ai/pricing) |
| Docfork | Was a protocol server for library documentation | "Docfork has shut down as of June 14, 2026" | Archived June 13, 2026 | [docfork/docfork](https://github.com/docfork/docfork) (re-read) |
| Mintlify | A search protocol server at `/mcp` for every hosted documentation site, with a tool that reports a wrong or outdated page back to its owners | Included from the free plan | "20,000+" companies (claim) | [Mintlify MCP](https://mintlify.com/docs/ai/model-context-protocol) |
| GitBook | Read-only protocol server per published site | Free; paid plans per site | Not published | [GitBook MCP](https://gitbook.com/docs/ai-for-your-readers/mcp-servers-for-published-docs) |
| kapa.ai, Inkeep | Search over a company's own documentation, served over protocol servers | Paid, by contact | "200+ companies" (kapa.ai, claim); 13 million dollar seed (Inkeep, September 5, 2025) | [kapa.ai](https://kapa.ai/pricing), [Inkeep](https://inkeep.com/blog/inkeep-funding-announcement) |
| `llms.txt` and its directories | A standard index file for language models; directories list sites that publish one | Free | 3,817 sites in one directory | [llmstxt.org](https://llmstxt.org) |

### Registries and directories of skills, plugins and protocol servers

| Name | What it does | Price | Traction | Source |
|---|---|---|---|---|
| Anthropic's official plugin directory | Anthropic's and partners' plugins; partners "must meet quality and security standards", but Anthropic "cannot verify that they will work as intended or that they won't change" | Free | 314 plugins (counted) | [claude-plugins-official](https://github.com/anthropics/claude-plugins-official) |
| OpenAI's plugin directory | One catalogue for ChatGPT and Codex; submissions are reviewed, and uploaded skills are scanned "for policy compliance and security risks" | No fee stated | 65 curated plugins in `openai/plugins` (counted) | [OpenAI submission](https://developers.openai.com/plugins/deploy/submission) |
| Cursor Marketplace | Plugins that bundle rules, skills, agents, commands, protocol servers and hooks; "we review each update before publishing" | Free | Not published | [Cursor plugins](https://cursor.com/docs/plugins) |
| skills.sh and `npx skills` (Vercel) | Installer and leaderboard for skills from any GitHub repository, with audits from Gen, Socket and Snyk | Free | 29,249,583 npm downloads in 30 days (counted) | [skills.sh](https://skills.sh) |
| SkillsMP | Collects skills from public GitHub repositories; interface and protocol server | Free | "3,000,000+" skills (claim); no quality filter documented | [skillsmp.com](https://skillsmp.com) |
| ClawHub (OpenClaw) | Skill and plugin registry; every bundle's hash is checked with VirusTotal and active skills are re-scanned daily (since February 7, 2026) | Free | 9,459 stars | [OpenClaw and VirusTotal](https://openclaw.ai/blog/virustotal-partnership) |
| Tessl | See claim 2 | Free to 100 dollars a month | 49,159 public entries (counted) | [tessl.io/pricing](https://tessl.io/pricing) (re-read) |
| Smithery | Protocol server registry and hosting | No plans shown | Acquired by Arcade.dev on August 5, 2026 | [Arcade.dev](https://arcade.dev/blog/smithery-joins-arcade) (re-read) |
| Glama | Protocol server directory with letter grades for licence, quality and maintenance | Behind sign-up | 92,771 servers listed | [glama.ai](https://glama.ai/mcp/servers) |
| PulseMCP, mcp.so, MCP Market | Protocol server directories; PulseMCP sells an interface with popularity and security analyses | Free to browse | 21,811, about 19,400 and 50,866 servers | [PulseMCP](https://pulsemcp.com/api), [mcp.so](https://mcp.so/servers), [MCP Market](https://mcpmarket.com) |
| Docker MCP Catalog | Container images; "Docker builds and signs all local servers in the catalog" with provenance and software bills of materials | Free | 245 repositories (counted) | [Docker catalog](https://docs.docker.com/ai/mcp-catalog-and-toolkit/catalog) |
| GitHub MCP Registry | Curated list with one-click install into VS Code | Free | 288 servers | [github.com/mcp](https://github.com/mcp) |
| Official MCP Registry | See claim 4 | Free | 36,654 servers at their latest version (counted) | [registry](https://registry.modelcontextprotocol.io) |
| Agent Skills specification | The `SKILL.md` folder format | Free, Apache-2.0 | 46 client products listed (counted) | [agentskills.io](https://agentskills.io) |
| AGENTS.md and the Agentic AI Foundation | The instruction file format, stewarded by the Linux Foundation's Agentic AI Foundation, formed December 9, 2025 with MCP, goose and AGENTS.md as founding projects | Free | "used by over 60k open-source projects" (claim) | [agents.md](https://agents.md) |

Security record: Palo Alto Networks' Unit 42 report of June 23, 2026 cites
Koi's disclosure of 341 malicious skills on ClawHub ("ClawHavoc") and found
five more that stayed unblocked from February to May 2026. OpenClaw's own
note says "A clean scan doesn't mean a skill is safe".

### Package and configuration managers

| Name | What it does | Licence | Traction | Source |
|---|---|---|---|---|
| Microsoft Agent Package Manager | See claim 3 | MIT | 3,910 stars | [microsoft/apm](https://github.com/microsoft/apm) |
| rulesync | Rules, ignore files, protocol server settings, commands, subagents, skills, hooks and permissions for about 50 tools | MIT | 886,410 npm downloads in 30 days (counted) | [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) |
| ruler | One `.ruler/` folder written into about 30 agents | MIT | 246,239 npm downloads in 30 days (counted) | [intellectronica/ruler](https://github.com/intellectronica/ruler) |
| OpenSkills | Installs skills and lists them in AGENTS.md; no release since January 2026 | Apache-2.0 file | 10,767 stars | [numman-ali/openskills](https://github.com/numman-ali/openskills) |
| SkillPort | Checks skills against the specification and serves them with a search tool | MIT | 414 stars | [gotalab/skillport](https://github.com/gotalab/skillport) |
| claude-code-templates | Catalogue of agents, commands, settings, hooks and skills for Claude Code | MIT | 31,969 stars | [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) |

### Model data with price and quality

| Name | What it offers | Terms that matter | Source |
|---|---|---|---|
| OpenRouter | Models, prices, context lengths, per-provider uptime (see claim 9); rankings of usage | Terms of August 31, 2026, section 7, forbid software that will "scrape or copy any information on the Site or the Services" and access "for purposes of reselling API access to Models or otherwise developing a competing service" (re-read) | [openrouter.ai/terms](https://openrouter.ai/terms) |
| Artificial Analysis | Intelligence index, prices, speed and latency; free interface of 1,000 requests a day | "Attribution is required for all use of our free API" (re-read); the website terms (April 28, 2024) grant only "personal, noncommercial use" and forbid building "a similar or competitive website, product, or service" (re-read) | [documentation](https://artificialanalysis.ai/documentation) |
| models.dev | One JSON file of costs, limits and capabilities; 223 providers and 8,170 provider-model entries (counted) | MIT | [models.dev](https://models.dev) |
| LiteLLM price map | Prices, limits and retirement dates; 4,392 entries (counted) | MIT outside `enterprise/` | [BerriAI/litellm](https://github.com/BerriAI/litellm) |
| Portkey models | Pricing database with a keyless endpoint per provider | MIT | [Portkey-AI/models](https://github.com/Portkey-AI/models) |
| Arena leaderboard | Latest ranking and full history, updated September 26, 2026 | CC BY 4.0 | [lmarena-ai/leaderboard-dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset) |
| Epoch AI Benchmarking Hub | 401 models and 86 benchmarks, downloadable | CC BY 4.0 | [epoch.ai](https://epoch.ai/data/ai-benchmarking-dashboard) |
| Routers: Not Diamond, Requesty, Martian | Route requests across models | Not Diamond 0.05 dollars per million tokens; Requesty 5 percent markup; Martian's router status unverified | [Not Diamond](https://notdiamond.ai/pricing), [Requesty](https://requesty.ai/pricing) |

Inference: the OpenRouter clause and the Artificial Analysis website terms
sit uneasily with a public directory that republishes their values daily.
Baltor's [source record](../../tools/model_directory/SOURCES.md) reads only
the documented Models API, relying on the guide's statement that it "makes
the most important information about all LLMs freely available", and shows
Artificial Analysis values with their publisher. That reading is recorded
here as disputed, not settled. The safer design republishes facts from the
openly licensed sources (models.dev, LiteLLM, Portkey, Arena, Epoch AI) and
serves the others as live, attributed lookups until written permission
exists.

### Papers, news and release feeds

| Name | What it offers | Terms | Source |
|---|---|---|---|
| Hugging Face Daily Papers | `/api/daily_papers` as JSON without a key; Papers with Code now redirects to Hugging Face's trending papers | Free | [Hugging Face MCP server](https://huggingface.co/docs/hub/hf-mcp-server) |
| arXiv interface | Paper metadata | Metadata is public domain; one request every three seconds | [arXiv terms](https://info.arxiv.org/help/api/tou.html) |
| Semantic Scholar | Paper and citation graph | Its licence forbids repackaging or redistributing the interface | [Semantic Scholar API](https://www.semanticscholar.org/product/api) |
| alphaXiv | Protocol server with research tools | Sign-in required | [alphaXiv MCP](https://alphaxiv.org/docs/mcp) |
| NewReleases | Watches releases on GitHub, PyPI, npm, Docker Hub and others, with an interface and webhooks | Free | [newreleases.io](https://newreleases.io) |
| Hacker News, NewsAPI.ai, smol.ai AINews | Public news feeds; AINews's newest item was September 10, 2026 | Free or free tier | [HN API](https://github.com/HackerNews/API) |

No product was found that watches tool releases, checks them and serves the
checked summary to agents. The search ran out of budget before it was
exhaustive, so this absence is unverified.

### Qualification and security scanning

| Name | What it checks | Price | Source |
|---|---|---|---|
| Tessl evaluations | Lift of a skill over a baseline on real tasks | Credits | See claim 2 |
| `claude plugin eval` | Each case three times with and three times without a plugin; reports the difference; "There are no custom-code graders" | Model calls on the user's account | [plugin evals](https://code.claude.com/docs/en/plugin-evals.md) (re-read) |
| Anthropic skill-creator | Two subagents, with and without a skill; pass rate, time and tokens with the difference | Free, Apache-2.0 | [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) |
| skill-eval-harness | Same case, model and repetition with and without a skill, for several harnesses | MIT, 76 stars | [adewale/skill-eval-harness](https://github.com/adewale/skill-eval-harness) |
| Snyk Agent Scan (formerly mcp-scan) | Agents, protocol servers and skills on a machine, for injected instructions and poisoned tools; sends component data to Snyk | Free, Apache-2.0 | [snyk/agent-scan](https://github.com/snyk/agent-scan) |
| Socket and Snyk on skills.sh | Scans of every file a skill references; install blocked for malicious skills | Free for skills.sh users | [Socket](https://socket.dev/blog/socket-brings-supply-chain-security-to-skills) |
| Gen Agent Trust Hub | Free skill scanner with a public lookup and a list of skills it verified | Free | [Gen](https://ai.gendigital.com/skill-scanner) |
| Cisco skill-scanner | Local scanner with eight analysers, including rules, code flow, a model check and VirusTotal | README says Apache 2.0 | [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) |
| VirusTotal public interface | File reputation, used by ClawHub | 500 requests a day; "must not be used in commercial products or services" | [VirusTotal](https://docs.virustotal.com/reference/public-vs-premium-api) |
| SkillRank | A score that "blends community stars, real usage, and our eval lift" | Free, MIT; its page showed "0 trials" | [skillrank.dev](https://skillrank.dev) |

### Consolidation in the last fifteen months

Snyk bought Invariant Labs, the maker of mcp-scan (June 24, 2025). Elastic
completed its acquisition of Jina AI (October 9, 2025). Nebius acquired
Tavily for a total consideration of 189.7 million dollars (February 19,
2026, per its filing). OpenAI agreed to acquire
promptfoo (March 9, 2026, re-read). Palo Alto Networks completed its purchase of
Koi, which found ClawHavoc (April 14, 2026). Docfork shut down (June 14,
2026, re-read). Arcade.dev acquired Smithery (August 5, 2026, re-read). Firecrawl raised a
75 million dollar Series B (September 22, 2026).

Inference: security scanning and hosting are being absorbed by large
security and platform companies, and a documentation-only service has
already failed. Distribution inside each harness is moving to the harness
makers' own reviewed directories. What is left open is the layer this
record is about: research done once across many sources, qualified for
declared conditions, and delivered with its history to every kind of
harness.

### Change detection without a paid service

Observed on September 27 by a research pass: GitHub release feeds
(`github.com/OWNER/REPO/releases.atom`) and PyPI release feeds
(`pypi.org/rss/project/NAME/releases.xml`, [documentation](https://docs.pypi.org/api/feeds/))
both return an `ETag` and answer `304 Not Modified` to `If-None-Match`. npm's
change feed still exists but lost live streaming on May 29, 2025; consumers
page through it with `since`
([GitHub community notice](https://github.com/orgs/community/discussions/152515)).
Some documentation sites send a `Last-Modified` equal to the request time and
no `ETag`, so validators do not work there. Many vendors publish Markdown
pages or `llms.txt` files whose normalised text can be hashed instead.

Other monitoring services read the same day, all prices from undated pages:
[changedetection.io](https://changedetection.io/) (Apache-2.0, 34,590 stars,
hosted at 8.99 dollars a month for 5,000 watches, REST interface and
webhooks), [Visualping](https://visualping.io/pricing) (free tier of 150
checks a month, interface on every plan),
[Distill.io](https://distill.io/pricing/) (free tier with six-hour minimum
interval), [Browse AI](https://www.browse.ai/pricing),
[Diffbot](https://www.diffbot.com/pricing/) (recurring crawls) and
[Apify](https://apify.com/pricing) (cron schedules for hosted scrapers).
Search and research interfaces priced per 1,000 requests: Brave 5 dollars,
Perplexity 5 dollars (fast search 1 dollar), You.com 5 dollars, Tavily 8
dollars in pay-as-you-go credits.

Inference: at 1,000 items a day, a paid monitor on every item would exceed
the recorded infrastructure allowance of 50 dollars a month (Parallel base
about 300 dollars, Exa monitors about 450 dollars, Firecrawl Growth 333
dollars). Conditional requests, release feeds, registry cursors and
normalised hashes cover most sources for nothing. Paid engines belong on the
few sources that need rendering or semantic judgement, and a research job
should start only when change detection reports a change.

### Precedents for sharing qualification results across many users

Two dependency-update tools already publish qualification results that one
project computes from many other projects' runs. They are the closest
working precedent for "validate for defined conditions, distribute many
times".

- Renovate's [Merge Confidence](https://docs.renovatebot.com/merge-confidence/)
  (page of Renovate 44.115.12, read September 27): it "finds and flags
  undeclared breaking releases" and "analyzes test and release adoption data
  from the Mend Renovate App users". Four badges: Age, Adoption ("The
  percentage of this package's users (within Renovate) which are using this
  release"), Passing ("The percentage of updates which have passing tests for
  this package") and Confidence. It covers Go, npm, Maven, PyPI, NuGet,
  Packagist and RubyGems. The badges are on by default for Mend Renovate App
  users; the advanced workflows need a paying Mend customer or an open-source
  project.
- GitHub Dependabot's compatibility score
  ([documentation](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/about-dependabot-security-updates),
  undated, read September 27): "the percentage of CI runs that passed when
  updating between specific versions of the dependency", "calculated from CI
  tests in other public repositories where the same security update has been
  generated."

Two open vulnerability sources can feed the monitor and revoke stage:

- The [OSV API](https://google.github.io/osv.dev/api/) (undated, read
  September 27) answers `POST /v1/query`, `POST /v1/querybatch` and
  `GET /v1/vulns/{id}`, and states: "Currently there are no limits on the
  API."
- The [GitHub Advisory Database](https://github.com/github/advisory-database)
  (read September 27) is "licensed under the terms of the CC-BY 4.0 open
  source license", stores advisories in the Open Source Vulnerability format,
  and marks curator review in a `github_reviewed` field.

Inference: Baltor can compute the same kind of pass rate for a served
release under a declared condition (harness, model class, operating system),
from local acceptance checks that customers choose to report. That respects
the telemetry rule in the owner's requirements: metadata only by default,
explicit opt-in for anything more.

## What Baltor already has on main

Observed in the detached worktree at revision `923453a4` (origin/main on
September 27, 2026). These are the pieces a shared research service would
build on. The list states what the files do today, not what is planned.

| Piece | What it does today | Where |
|---|---|---|
| Daily research watch | Reads 17 primary sources once a day at 07:41 UTC with bounded HTTPS reads and no model call. A GitHub repository is fingerprinted by its newest commit, a page by the SHA-256 digest of its bounded body. It records the `ETag` and `Last-Modified` validators but does not send `If-None-Match` or `If-Modified-Since`. It opens or updates one issue when a source changed. | [research-watch.yml](../../.github/workflows/research-watch.yml), [research_source_watch.json](../../tools/research_source_watch.json), [refresh_research_sources.py](../../tools/refresh_research_sources.py) |
| Directory of protocol servers | 36,231 rows generated at 12:27 UTC on September 27. 35,968 rows carry the official MCP Registry as a source; the registry is read once in full and then incrementally with `updated_since` and a one hour overlap. Deprecated and deleted servers are left out. GitHub's directory (288 rows) and the Docker catalogue (311 rows) are read too. Refreshed daily at 06:41 UTC. | [mcp-directory.yml](../../.github/workflows/mcp-directory.yml), [build_mcp_directory.py](../../tools/build_mcp_directory.py) |
| Directory of models | 2,145 models, 184 endpoints, 6 local runtimes and 1,226 hardware fit rows, built at 13:06 UTC on September 27 from the Hugging Face Hub API, models.dev and the OpenRouter Models API. The Ollama library is linked only, because its terms refuse automated access. Refreshed daily at 07:23 UTC. | [model-directory.yml](../../.github/workflows/model-directory.yml), [SOURCES.md](../../tools/model_directory/SOURCES.md) |
| Content-addressed catalogue releases | A release lists each item identity with the digest of its immutable item version. The active release pointer moves only under an expected-version guard. A withdrawal is durable and is honoured by every later release and every rollback. | [catalogue_releases.py](../../src/loop_engine/core/service_runtime/catalogue_releases.py) |
| Feedback and withdrawal | A customer report withdraws a Community item at once and a Verified item on a second account's report or a staff flag. A nightly rescan and a weekly upstream check (missing repository, changed licence, advisory, archived repository) run beside it. | [catalogue-feedback-and-withdrawal.md](../guides/catalogue-feedback-and-withdrawal.md) |
| Unattended daily release | Roadmap step S-6.197, "one unattended daily job from the day's approvals to a checked live catalogue release, with automatic rollback", has the status `live_qualified`. | [roadmap.yaml](../roadmap/roadmap.yaml) |
| Engine slots | 51 `engine_slot/v1` records, each a fixed, typed, versioned edge with swappable engines. | [engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml) |
| Client install records | The Pi extension installs a skill by its published SHA-256 digest and writes a `baltor_pi_install/v1` record. A search of the Pi extension and of the placement tool for Claude Code and Codex for "withdraw" finds nothing, which indicates that an installed copy is not checked again against later withdrawals. | [baltor.ts](../../src/loop_engine/core/service_runtime/web_assets/pi/baltor.ts), [install_selected_material.py](../../tools/install_selected_material.py) |
| Conditional requests on Baltor's own pages | The service answers `If-None-Match` for its web assets with an `ETag`. | [web_pages.py](../../src/loop_engine/core/service_runtime/web_pages.py) |

Roadmap step S-6.214, "Daily distillations: new papers, skills, plugins,
protocol servers, services and repositories", is `building`. Step S-6.101,
the public directory of models, is `offline_verified`. No signing with
Sigstore and no metadata from The Update Framework was found in `src`,
`tools` or `.github`.

### Gaps in the current pieces, and the repair each finding suggests

| Gap observed on main | Finding that bears on it | Suggested repair |
|---|---|---|
| The research watch records `ETag` and `Last-Modified` but sends neither back, and reads GitHub without a credential | GitHub counts a `304` as free only on an authorized request; release feeds and PyPI feeds answer `304` | Send `If-None-Match` and `If-Modified-Since`; read GitHub with the workflow's read-only token; watch release feeds instead of commit heads where a release is what matters |
| Pages are fingerprinted by the digest of the whole body, so a changed timestamp or script looks like a change | Some documentation sites send a `Last-Modified` equal to the request time; many vendors publish Markdown or `llms.txt` forms | Fingerprint normalised text, prefer the Markdown or `llms.txt` form, and record the fingerprint method with each observation |
| No edge for change detection or claim extraction | Firecrawl, changedetection.io, Parallel and Exa each cover part of change detection; claim extraction needs source spans | Add two engine slots, `source_change_detection` and `claim_extraction`, with the plain approach as the first engine of each |
| Releases are content-addressed but not signed, and a client cannot tell a current release list from a replayed old one | Sigstore proves the release identity; The Update Framework's timestamp and snapshot roles defeat freeze and rollback | Sign each release manifest from the release workflow's identity and give the release list a short expiry; verify both in the client |
| An installed copy is not checked again after a withdrawal (no match for "withdraw" in the Pi extension or the placement tool) | Withdrawal is durable on the server; the harness keeps its local copy | Serve a signed withdrawal list, have every client check installed digests against it before use, and record the check |
| The registry copy depends on a preview service without durability promises | "Breaking changes or data resets may occur before general availability" | Keep Baltor's own copy of every served record and plan a full re-read after a reset |

## Engines for each pipeline stage

[Rule 6](../../AGENTS.md#what-engineering-does-without-asking) of the owner's
standing authority: every functional component sits
behind a fixed, typed, versioned edge with one or more swappable engines, and
existing projects are searched before anything is built. The tree shows the
nine stages and the edge each one uses today or needs. Slot names are the
`slot_id` values in [engine_slots.yaml](../../src/loop_engine/data/engine_slots.yaml).

```text
Shared research pipeline
├── Discover            library_ingestion_source, web_research_port
├── Change-detect       no slot yet (proposed: source_change_detection)
├── Capture             web_research_port, catalogue_body_store
├── Extract claims      no slot yet (proposed: claim_extraction)
├── Compare, evaluate   response_evaluator, catalogue_qualification_resolver,
│                       library_safety_scan, library_near_duplicate
├── Package             catalogue releases, catalogue_body_store
├── Materialize         material_install_layout, harness_instruction_files,
│                       customer_client_recipe
├── Serve               protocol_endpoint, intelligence_search_retrieval_port,
│                       catalogue_search_policy, tool_protocol_gateway
└── Monitor and revoke  catalogue withdrawals, nightly rescan, weekly
                        upstream check (proposed: withdrawal_delivery)
```

Versions, licences and dates below were read on September 27, 2026 from each
project's repository, package index entry or documentation. The
recommendations are inferences. Adopting an engine still means a pinned
trial in isolated staging, a check that fails without it, and a recorded
decision.

| Stage | Adopt as engines | Keep as a Baltor-native engine | Watch as competitors | Reason |
|---|---|---|---|---|
| Discover | The official MCP Registry with incremental reads; GitHub, PyPI and npm release and change feeds; [deps.dev](https://docs.deps.dev/api/v3/) (licences, advisories, OpenSSF Scorecard and provenance per version; data under CC-BY 4.0 and "Clients are expressly permitted to cache data"); the Hugging Face and OpenRouter interfaces; the skills.sh interface; Exa search only where no registry exists | The question registry (what to research and why), source contracts, the licence gate and deduplication | Context7's and Tessl's indexes | Structured sources cover most of what Baltor tracks. ecosyste.ms and Libraries.io data is CC BY-SA 4.0, so a derived database would inherit share-alike terms. |
| Change-detect | Firecrawl change tracking (hosted) for rendered pages; changedetection.io (Apache-2.0, self-hosted) as the free alternative; Parallel snapshot monitors for questions without one source page | The plain engine: validators sent back, release and package feeds, registry cursors and normalised text hashes | None; these are suppliers | The plain engine is free and covers most sources. Paid monitors on every item would exceed the 50 dollar allowance. |
| Capture | trafilatura (Apache-2.0 from version 1.8.0; 2.2.0 released July 31, 2026) for main text; Playwright (Apache-2.0) for rendered pages; Browsertrix Crawler (AGPL-3.0 or later, 1.14.3, run unmodified in its own container) producing WACZ 1.1.1 packages with SHA-256 manifests when a replayable capture is needed | The bounded reader with its request log, byte digests and storage | Firecrawl's developer index | Capture is commodity work; the evidence digest is what Baltor must own. The WACZ signing specification is still a draft. |
| Extract claims | Deterministic parsers for structured sources first; [LangExtract](https://github.com/google/langextract) (Apache-2.0, 1.7.0 of September 13, 2026), which "Maps every extraction to its exact location in the source text" and leaves ungrounded extractions without an offset; Anthropic's citations where Claude is permitted | The claim record: claim, source span, observed time, valid-until time, volatility class, and the rule that a claim without a source is not served | None found that serve agents | Source spans make every served fact checkable by the customer's own harness. LangExtract runs on local models through Ollama, which fits customers who bring their own model. |
| Compare and evaluate | [Harbor](https://github.com/harbor-framework/harbor) (Apache-2.0, 0.23.0 of September 12, 2026; "the official harness for Terminal-Bench-2.0"; runs Claude Code, OpenHands and Codex in fresh sandboxes); [Inspect AI](https://inspect.aisi.org.uk/) (MIT; runs "Claude Code, Codex CLI, and Gemini CLI" inside sandboxes); skill scanners (Snyk's agent-scan, Apache-2.0; Cisco's skill-scanner, licence not detected by GitHub) behind `library_safety_scan` | Acceptance criteria per condition, independent review, the condition matrix and evidence records; the with-and-without design copied from `claude plugin eval` and skill-creator (at least three runs per arm, report the difference, exclude graders that can only pass with the material) but independent of any one harness | Tessl's evaluations; Claude Code's `claude plugin eval`; promptfoo, which "has agreed to be acquired by OpenAI" (March 9, 2026) and remains open source | The measurement method is public. A dated matrix across harness, model class and route is not. |
| Package | Sigstore signing through GitHub artifact attestations (free for public repositories; the documentation calls them "*not* a guarantee that an artifact is secure"); python-tuf (Apache-2.0) for expiring release metadata; OCI 1.1 artifacts through [ORAS](https://github.com/oras-project/oras) (Apache-2.0, 1.3.4) as an optional mirror with reviews attached as referrers | The package format, digests, provenance, licence evidence, release and withdrawal records | Tessl plugins; Microsoft Agent Package Manager packages; skills.sh | Signing and freshness are solved standards. Package meaning is Baltor's. |
| Materialize | Microsoft Agent Package Manager (MIT; trial decided September 24); rulesync (MIT, 21.0.0 of September 26, 2026, about 50 tools including protocol servers, hooks and permissions); the skills command line from Vercel (MIT, 1.7.0; "OpenCode, Claude Code, Codex, Cursor, and 75 more"; telemetry on by default, to be turned off); ruler (MIT) | Baltor's placement for Claude Code, Codex and Pi, with digests and install records | `tessl init` | Placement is commoditised. Keep the native path where install records and digests are needed. Codex, OpenCode and Cursor share `.agents/skills/`, so installs can overlap. |
| Serve | A listing in the official MCP Registry; tool names and descriptions written for tool search; live tools that wrap volatile sources with their dates; Context7 or DeepWiki named as documentation engines instead of a rebuilt index | The protocol endpoint, search policy, relevance floor and metering | Context7; Augment Context Engine; DeepWiki; Ref | Serving is where Baltor meets the customer. Library documentation is solved elsewhere. |
| Monitor and revoke | The OSV interface and the GitHub Advisory Database (CC-BY 4.0) for advisories; OpenSSF Scorecard results through deps.dev; Sigstore and The Update Framework for a signed withdrawal list with expiry | The withdrawal policy, the client re-check, and pass rates per condition from opt-in reports, in the manner of Renovate and Dependabot | skills.sh audits; Snyk; Socket | A withdrawal has to reach installed copies. Pass rates per condition are what nobody else publishes for agent material. |

## The first capability family for the end-to-end demonstration

The demonstration the analysis proposes: an upstream change triggers one
shared research job, a candidate is tested, one immutable release is
published, two different harnesses retrieve it without repeating the
browsing, both run local acceptance checks, and a later bad release is
revoked. The question is which capability family shows that sequence
fastest and most convincingly.

### A finding that shapes the choice

Observed on September 27: Baltor's model directory row `ollama-cloud`
(`endpoints.json`) records structured output as supported, citing Ollama's
structured outputs page as read on September 24. The source of that page in
the Ollama repository,
[docs/capabilities/structured-outputs.mdx](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx),
opens with the note "Ollama's Cloud currently does not support structured
outputs." The note was added by the commit of April 22, 2026 titled "docs:
update structured outputs doc for cloud". Ollama issue
[12362](https://github.com/ollama/ollama/issues/12362), "JSON reply schema is
ignored by Cloud model", has been open since September 21, 2025. This record
read the documentation source on GitHub rather than Ollama's own site,
because Ollama's terms refuse automated access to its services.

So the row was misread five months after the caveat appeared, not overtaken
by a recent change. It is exactly the error class a shared research service
exists to catch: volatile, stated in a note and an issue thread rather than
a changelog, and decisive for whether a cheap model can do a structured task
under a given condition. On the route the owner has authorised for model
calls, valid output must be measured, not assumed to be enforced.

### How the five families compare

Facts from a research pass (package indexes, release feeds, the Hugging
Face interface and the named benchmark pages, read September 27) and from
the repository at `923453a4`.

| Question | Structured extraction model selection | Retrieval and reranking | Document extraction | Entity matching | Headless rendering |
|---|---|---|---|---|---|
| Does a trigger already fire daily? | Yes: the model directory difference (395 rows carry a structured output fact; 41 are dated September 2026) | Partly: the directory's text-ranking rows | No: none of the 17 watched sources is a document engine | No | No |
| Can the local check run without a graphics processor? | Yes: schema validation and field scores in plain Python; the model call goes to the customer's own route | Yes, for rerankers of about 0.6 billion parameters on small collections | Hard: the strongest engines run vision models; olmOCR needs "at least 12 GB of GPU RAM" | Yes | Yes |
| Is the metric deterministic? | The scorer is exact; model outputs vary, so repetitions and margins are needed | High once weights are pinned | Metrics are exact but model outputs vary | Highest: pair F1 on fixed labels | Low on live pages |
| Ground truth that can ship in a package | Baltor's own generated records; CORD v2 (CC-BY-4.0); ExtractBench (MIT) | Baltor's 354 relevance judgements | olmOCR-Bench (ODC-BY-1.0); OmniDocBench is "for research purposes only and not for commercial use" | The DeepMatcher sets state no licence | web-platform-tests (BSD-3-Clause) |
| Baltor assets on main | Model directory prices and flags; data cleanup and overnight case studies with generated contact data; native placement for Claude Code and Codex | `core/retrieval.py` with BM25, LanceDB and model2vec; `examples/30_search_quality` (recall at 3 of 0.837 held back) | None beyond directory rows | `code_nodes/duplicate_detection.py`; the duplicates population with its scorer | Playwright for Baltor's own site checks |
| How often the best choice changes | Monthly or faster | About quarterly (22 rerankers in 12 months) | Several times a year, about two new models a month | Rarely: dedupe, recordlinkage and py_entitymatching have not released in over two years | Rarely |
| Licence traps | Few for the method; model terms vary | CC-BY-NC rerankers | MinerU's own licence; Marker's model weights free only for research, personal use and companies under 5 million dollars of funding or revenue; AGPL engines; non-commercial benchmark data | Zingg is AGPL-3.0 | AGPL-3.0 and SSPL-1.0 engines |

### Recommendation

Inference, and engineering's decision for the demonstration order:

1. Structured extraction model selection first. The trigger already fires,
   the tests run inside present model authority on Ollama Cloud, the scorer
   is exact, most parts exist, the bad-release case is real, and it proves
   the north star directly: small models doing more.
2. Retrieval and reranking second. Baltor already has the judgements, the
   backends and a saved baseline, and the planned `retrieval_rerank_stage`
   slot needs an engine anyway.
3. Document extraction third. It has the best research-once economics, the
   most fragmented choice and the most licence traps, but Baltor has no
   extraction assets, the best engines need a graphics processor, customers'
   local checks would need heavy installs, and hosted engines would need new
   spending. It needs a plan for graphics processors or hosted spending, the
   olmOCR-Bench fixtures rather than OmniDocBench, and licence gates before
   it goes.

Entity matching has the best assets and the most exact check but a weak
trigger, and its choice is not fragmented, so shared research shows little.
Headless rendering has a stable default and non-deterministic checks.

### Demonstration steps

0. Freeze the design before any model call. The schema class is a contact
   record from free text (name, organisation, email, telephone number,
   address parts, website), generated by the overnight case study's
   population generators, so the data is first-party. Sets: 40 development
   records, 20 held-out records and 12 separate acceptance fixtures. Write the
   known-wrong outputs first (a missing required field, a malformed
   telephone number, an invented postal code, text that is not JSON) and show
   that the scorer rejects each one.
1. Trigger. The daily model directory difference adds a model to the Ollama
   Cloud list or changes a structured output fact. The research watch also
   follows `docs/capabilities/structured-outputs.mdx` in the Ollama
   repository and issue 12362, so a change there invalidates only the Ollama
   Cloud rows.
2. One shared research job, for the changed rows only. Earlier results stay
   valid until their valid-until day. Three repetitions of 60 records with at
   most one repair each is at most 360 requests, under a declared ceiling of
   400, and every call is recorded with its model, usage and outcome. The job
   also tests whether a schema sent on the route is honoured.
3. Candidate test. Field accuracy after normalisation on the held-out
   records must reach at least 0.95 in every repetition, with no invented
   values and fully valid JSON after at most one repair. Among the models that
   pass, the one with the lowest cost per accepted record is chosen: listed
   price where the route has one, tokens on a subscription route. An
   independent reviewer approves the release; the producer never approves its
   own work.
4. One immutable release, with a manifest of SHA-256 digests: `SKILL.md`
   (route, model, as-of and valid-until days, threshold and scores), the JSON
   Schema, `scripts/extract.py` (calls the customer's own compatible
   endpoint, validates and repairs once), `scripts/accept.py` with the 12
   acceptance fixtures and the known-wrong fixtures, and
   `evidence/results.json` listing every model tried, failures included.
5. Two harnesses retrieve it. Claude Code and Codex, each in a fresh folder,
   search and download through Baltor's protocol endpoint and place the
   skill natively. The request log should show no fetch of model cards,
   documentation or leaderboards. Listed, loaded, used and verified are
   recorded as separate facts, and the same task is run once without Baltor
   as the baseline.
6. A local acceptance check in each harness. `accept.py` first runs the
   known-wrong self-test with no model call, then sends the 12 fixtures
   through the customer's own route (12 to 24 requests) and applies the frozen
   threshold. A result is reported to Baltor only if the customer opts in.
7. A bad release and its revocation. Release N+1 relies on a directory fact
   instead of a measurement, for example sending a schema to Ollama Cloud
   because the directory says the route enforces it, or picking a cheaper
   model that fails the held-out set. Both local checks fail. The reports
   write the `catalogue_withdrawal/v1` record for that identity and body
   digest, and the active pointer returns to release N. Both harnesses then
   receive release N again, and the withdrawn digest is refused. Only the rows
   the change invalidated are researched again. The refusal of an already
   installed copy needs the client re-check that does not exist yet.

## Where Baltor is differentiated, and where it is not

### Not differentiated

- Library documentation for agents. Context7 has a free plan, one-call
  search since September 22, 2026, 62,469 stars and 3.3 million downloads of
  its protocol server package in 30 days. DeepWiki's server is free, and
  Andrew Ng's Context Hub is free under MIT. A Baltor documentation index
  would repeat solved work.
- Directories and registries. The official MCP Registry, GitHub's
  directory, the Docker catalogue, skills.sh, Tessl (49,159 public entries)
  and several others list the same material. Baltor's directory of 36,231
  rows is expected, not distinctive.
- Placement into harness folders. Microsoft Agent Package Manager, rulesync,
  ruler and the skills command line from Vercel (29,249,583 npm downloads in
  30 days) all write one source into many harnesses, under MIT.
- Evaluation with and without the material. Tessl sells it per skill. Claude
  Code now ships `claude plugin eval`, which runs every case three times with
  the plugin and three times without and reports the difference (it needs
  version 2.1.269 or later). Anthropic's skill-creator does the same inside a
  session, and SkillsBench and Harbor publish the method.
- Change detection and research jobs. Parallel, Exa and Firecrawl are well
  funded and priced per request, and changedetection.io is free to run.
- Model prices and capabilities. OpenRouter, models.dev and the Hugging Face
  router publish them; Baltor's model directory reads several of them.
- Signing and provenance. Sigstore, GitHub artifact attestations and PyPI and
  npm provenance are standards to adopt, not features to invent.

### Differentiated, if the demonstration proves it

- Qualification per declared condition, published as dated data. For
  example: "this extraction helper, with model X on route Y, reached 0.96
  field accuracy on the held-out set on this day, valid until that day".
  None of the products checked publishes such a matrix across harness,
  model class, route and hardware for agent material. Tessl measures lift
  per skill on a customer's tasks; Claude Code's evaluator measures one
  plugin inside Claude Code; Renovate and Dependabot publish pass rates, but
  for dependency updates.
- One release for many harnesses, with its life cycle. The same content
  addressed release is placed natively into Claude Code, Codex, Pi and
  others, with an install record by digest, and a withdrawal that reaches
  installed copies once the client re-check exists. Most alternatives are
  tied to one harness, one ecosystem or one customer's workspace.
- Small models on the customer's own route. Baltor qualifies cheap and local
  models on the route the customer brings. Context7, Augment and Tessl assume
  the customer's harness model does the work. The Ollama Cloud finding in
  this record shows why the route matters: the same model can or cannot
  return schema-valid output depending on where it runs.
- Honest records as a product rule. Every fact is dated and sourced, an
  unknown stays unknown, commercial relationships never affect ranking, and a
  withdrawal survives rollbacks. This earns trust, but another company can
  copy it.

Inference: the lasting advantage would be accumulated qualification data,
including opt-in outcome reports from many customers' local checks, in the
manner of Renovate's Merge Confidence. A competitor cannot copy that without
the same population. Until that data exists, Baltor is an assembly of parts
that each exist elsewhere, and its claims must stay at what has been
measured.

## Decisions this record makes, and the reasons

These are engineering judgements under the owner's direction to decide
instead of asking. None of them is implemented by this record, and the
roadmap is unchanged; the proposed roadmap entries follow the decisions.

1. The first demonstration uses small-model selection for structured
   extraction; retrieval and reranking is second and document extraction
   third. Reason: the trigger already fires daily, the acceptance check is
   exact and needs no graphics processor, the model access is already
   authorised, and the family proves the north star directly.
2. Change detection starts with the plain engine: validators sent back,
   release and package feeds, registry cursors and normalised text hashes.
   Paid monitors are added only for sources that need rendering or semantic
   judgement. Reason: the free methods cover most sources, and paid monitors
   on every item would exceed the recorded allowance.
3. Baltor does not build its own library documentation index. It names
   Context7 or DeepWiki as documentation engines. Reason: the problem is
   solved, cheap or free, and a documentation-only service (Docfork) has
   already closed.
4. The September 24 decision to trial Microsoft Agent Package Manager behind
   `material_install_layout` stands. Reason: its lockfile, content hashes,
   transitive resolution and placement were verified again, under MIT.
5. No record may claim that revocation reaches a harness until release
   manifests are signed, the release list carries an expiry, and clients
   check installed digests against a signed withdrawal list. Reason: Sigstore
   and The Update Framework establish identity and freshness, and nothing on
   main re-checks an installed copy today.
6. The model directory's Ollama Cloud structured output fact is to be
   corrected, and the research watch is to follow the Ollama documentation
   source and issue 12362 through GitHub. Reason: the documentation has
   carried the "does not support structured outputs" note since April 22,
   2026.
7. Republished model facts should come from openly licensed sources
   (models.dev, LiteLLM, Portkey, Arena, Epoch AI); OpenRouter and Artificial
   Analysis values should be live, attributed lookups until either gives
   written permission. Reason: their terms forbid copying by script and
   competing uses, and the current reading of the OpenRouter guide is
   disputed. Asking those companies for permission is an outside
   communication that this record does not make.
8. Baltor publishes benefit claims per condition only. Reason: the research
   supports curated, focused, current material under measured conditions, and
   shows generated overviews and self-written skills failing to help.
9. Becoming a subregistry of the official MCP Registry, with Baltor's review
   results under its own `_meta` key, is to be evaluated, not adopted yet.
   Reason: the registry invites it, but it is still a preview with no
   durability promise.

## Proposed roadmap entries

These are proposals for the task authority, not changes to it.

1. Under D-19, a `source_change_detection` slot. First engine: the plain
   method above. Optional engines: Firecrawl change tracking,
   changedetection.io and Parallel snapshot monitors. A timestamp-only change
   must not count as a change, and a new release in a feed must.
2. Under D-19, a `claim_extraction` slot. First engine: deterministic parsers
   for structured sources; model-led engine: LangExtract. A claim without a
   source span is refused by a named check.
3. A step "revocation reaches installed copies": signed release manifests,
   an expiring release list, a signed withdrawal list, and a re-check of
   installed digests in the Pi extension and the Claude Code and Codex
   placements. A replayed old release list and a withdrawn digest must each
   be refused.
4. A step for the first shared research demonstration (structured
   extraction model selection), with steps 0 to 7 above as its checks and the
   bad release as its adversarial case. It depends on S-6.101, S-6.62,
   S-6.199 and entry 3.
5. Under S-6.101, the Ollama Cloud correction and the move of republished
   facts to openly licensed sources.
6. Under S-6.214, the research watch repairs: validators sent back,
   authenticated GitHub reads with the workflow's read-only token, and
   normalised fingerprints.

## Evidence states

- Observed on September 27 by the author of this record: live reads of the
  OpenRouter Models API and one endpoint listing; npm download counts; the
  repository files named here at revision `923453a4`; GitHub repository
  metadata (stars, licences, push dates); Ollama issues 12362 and 13206 and
  the Ollama documentation source with its April 22, 2026 commit; and
  re-reads of the Context7 plans, Search API and announcement pages, the
  Tessl pricing page, the MCP Registry aggregators guide, GitHub's REST API
  best practices, the Parallel snapshot quickstart, the Firecrawl change
  tracking page, the Claude Code plugin evaluation page, promptfoo's
  announcement, the deps.dev documentation, the Arcade.dev announcement, the
  Docfork repository, the OpenRouter terms and models guide, the Artificial
  Analysis documentation and website terms, Renovate's Merge Confidence
  page, Dependabot's compatibility score section, the OSV interface page, the
  GitHub Advisory Database repository, and the arXiv pages of the AGENTS.md
  paper and SkillsBench.
- Observed on September 27 by the seven research passes and not re-read by
  the author: the remaining vendor pages, papers and live reads cited here,
  each with its link.
- Unverified: Exa Websets plan prices and Nia's funding (automated reads
  refused); how Parallel bills a snapshot re-run of a large processor; the
  meaning of OpenRouter's negative status codes; the date Claude Code began
  deferring every protocol server tool; Martian's router status; the
  absence of any product that watches tool releases and serves checked
  summaries to agents (the search budget ran out).
- Disputed: whether MCP Registry metadata can ever be erased (its frequently
  asked questions against its moderation policy); Augment's improvement
  numbers (its blog against its product page); Firecrawl's credit cost for
  schema extraction inside a monitor (5 against 7 credits); and whether
  Baltor's daily republication of OpenRouter and Artificial Analysis values
  is permitted.
- Inferred: every recommendation, the demonstration order and the
  differentiation statements.
