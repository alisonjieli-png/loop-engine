# Agent Feed source collections

Kind: engineering source-selection record. Source documentation inspected on
October 8, 2026 UTC (October 7 in the owner's timezone). This is website
reference material, not a published intelligence batch or a measurement of
the cited systems.

## Shipped boundary

The Feeds page presents 13 named collections containing 28 source references.
Each collection has a decision question, practical research task, comparison
fields and a trigger for reviewing the decision again. The cards are organized
around choices an agent helps make, including architecture, model selection,
cost, product positioning and improvement opportunities. JSON Feed
and Markdown downloads let a customer give different source selections to
different agents without opening an account. The customer controls the
harness's polling, model access, budget and permission to visit a source.

The output is a release-curated directory. It contains no collected news,
current benchmark rankings or reproduced results. The documentation-check
date is distinct from an upstream publication date. A directory digest binds
the exact packaged bytes; restarting the service does not change it.

The existing catalogue feed, HTTP renderer, ETag handling, shared page frame
and Cloudflare static-site export are reused. `tools/knowledge_radar/feed.py`
was inspected as prior work: its candidate answer states and admitted brief
path remain separate. Turning those candidates into public research would
require the existing qualification and publication process. No parallel
scheduler, entitlement system, store or executable runtime is introduced.

## Sources and intended use

The exact URLs, original descriptions, access notes and reuse cautions live
in the single packaged [source directory](../../src/loop_engine/core/service_runtime/feed_source_collections.json).
The page and downloads all read that directory.

| Collection | Primary sources | Question it helps investigate |
|---|---|---|
| Coding-agent benchmarks | [SWE-bench](https://www.swebench.com/), [HELM](https://github.com/stanford-crfm/helm) | Which evaluated model and harness setting resembles the repository task? |
| RAG and retrieval benchmarks | [MTEB](https://github.com/embeddings-benchmark/mteb), [BEIR](https://github.com/beir-cellar/beir), [Ragas](https://docs.ragas.io/en/stable/) | Is the weakness retrieval, ranking or answer grounding? |
| Model cost and latency | [Artificial Analysis methodology](https://artificialanalysis.ai/methodology), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) | What was measured, and what is only a workload cost estimate? |
| Safety and reliability evaluations | [AILuminate](https://mlcommons.org/ailuminate/), HELM | Which risks and conditions were actually evaluated? |
| Models on your hardware | [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/), [llama-bench](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md), [Ollama](https://ollama.com/library) | Which exact configuration fits and runs on the chosen machine? |
| Model releases and model cards | [Hugging Face Hub API](https://huggingface.co/docs/hub/api), Ollama | What changed, under which licence, at which revision? |
| MCP-compatible tools and services | [Official MCP Registry](https://modelcontextprotocol.io/registry/about), [GitHub Releases API](https://docs.github.com/en/rest/releases/releases) | What can the server do, and which scopes and effects would it receive? |
| Papers worth testing | [arXiv API](https://info.arxiv.org/help/api/index.html), [OpenAlex](https://help.openalex.org/) | What claim is worth reproducing for this problem? |
| Founder stack | [Workers](https://developers.cloudflare.com/workers/), [R2](https://developers.cloudflare.com/r2/), [Fly.io](https://docs.fly.io/), [Resend](https://resend.com/docs/introduction), [Better Auth](https://better-auth.com/docs/introduction) | Who owns compute, storage, email and login, including failure and migration? |
| Developer tools and platform changes | GitHub Releases API, [GitHub Changelog](https://github.blog/changelog/), [Cloudflare Changelog](https://developers.cloudflare.com/changelog/) | Which release or deprecation affects the chosen stack? |
| Product launches and useful tools | [Product Hunt API documentation](https://www.producthunt.com/v2/docs), GitHub Changelog | Which product addresses a specific problem, beyond launch popularity? |
| Hackathons and Kaggle competitions | [Kaggle CLI](https://github.com/Kaggle/kaggle-cli), [Devpost](https://devpost.com/hackathons) | Does this event fit the project and permit the intended public demonstration? |
| Filings and economic context | [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [FRED API](https://fred.stlouisfed.org/docs/api/fred/) | Which dated filing or release may explain the event, and what remains unknown? |

No source is called a universally best option. A model listing is not a licence,
a registry entry is not a safety certificate, and an external benchmark is not
a Baltor result. Reuse notes keep code, dataset, model and article rights
separate. Financial sources provide context, not live options tape, confirmed
trader intent or investment recommendations.

The current Product Hunt API documentation requires permission for commercial
use. Its entry is a reference only; no Product Hunt collector is enabled.
arXiv documents API terms and attribution requirements, while individual
papers retain their own licences. No paper body or upstream article is
republished by this change.

Initial documentation probes for the old Product Hunt docs hostname, the HELM
Safety page and the llama-bench folder URL failed through the browser search
tool. The successfully inspected official Product Hunt API page, HELM
repository and llama-bench README are the retained references. A CISA page
probe also failed; that source is not in this release. Redirects resolved the
Kaggle API repository to the official Kaggle CLI, OpenAlex docs to its help
center and Fly.io docs to docs.fly.io. These outcomes are not availability
guarantees for future collection jobs.

## Checks and continuation

The owning tests cover the complete directory, all 28 representations, exact
collection selection, unknown-version and malformed-record refusals, an
explicit removed-contract-guard control, text escaping, anonymous HTTP,
conditional GET, HEAD, refusal caching and catalogue independence. The edge
conformance suite compares the new exported bytes and headers with the real
loopback service. `tools/check_feed_sources.mjs` checks desktop and mobile
pages, every download, visible scope labels and removed-card/date controls.
It accepts `--local` or a deployed HTTPS origin and a new report path.

Next acceptance work remains explicit:

- Collect permitted upstream observations through the existing research
  query and knowledge radar engines, with source identity, timestamps,
  licences, budgets and failed attempts preserved.
- Produce useful dated digests and benchmark comparison records. Preserve
  model, harness, dataset and evaluator versions; report incompatible
  comparisons instead of inventing a combined leaderboard.
- Add account-owned saved selections, per-agent assignments, revocation and
  delivery history through the current identity and record boundaries.
- Qualify refresh cadence, failed-refresh behavior and opt-in delivery before
  offering a maintained personalized feed or a separate paid plan.

The humanizer pass kept the source names, concrete tasks and availability
limits; it removed vague context-refresh language and avoided benefit claims
that this directory has not measured.
