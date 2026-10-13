# Agent Feeds: evidence, delivery and task queues

Kind: dated research and source-inspection record, October 13, 2026.
This review recommends the next useful Feeds increments and records the
implementation boundaries inspected during the AgentFeeds launch preparation.
The [roadmap](../roadmap/roadmap.yaml) owns work status. The
[deployment record](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
owns what is live; this document does not establish a new deployment.

Agent Feeds should help an agent decide whether a change matters to its task,
what alternatives fit, and which bounded test would settle the choice.
The first customer can start with public information and a short project brief.
Private repository access is optional. Useful silence, keeping the existing
tool and reporting missing evidence are valid outcomes.

## Evidence and coverage

The source inspection began at `d8eba9df`; launch integration was inspected
through `b141f077`. Concurrent presentation changes were still under review.
The supplied October 13 history audit informed the questions below. Its
private archive and original historical run packs were not independently
reopened for this record. No account-wide coverage claim follows from it.

| Evidence class | Material inspected | What it establishes |
|---|---|---|
| Source inspection | Packaged source directory, renderers, profile compiler, knowledge radar, managed records and queue code | The behavior represented by those exact files |
| Offline execution | Dismissed-lead reproduction and repaired queue checks | The tested store/scheduler behavior, without provider or model calls |
| Current documentation | GitHub, MCP Registry, PyPI, OSV, Airflow, Celery and BEIR primary pages linked below | Documented interfaces and approaches, without executing those services |
| Supplied historical report | October 13 feeds/history audit and its earlier research references | Leads for reconciliation, not independently repeated measurements |
| Proposed acceptance | Decision-feed and queue cases below | Work to qualify, with no claimed result |

The packaged directory was recounted: 60 distinct source IDs in 19 collections,
with `source_docs_checked_on` set to October 9. Its declared scope is
`source_descriptions_only`, refreshed with a website release. Those are source
references and documentation dates, not 60 running collectors or 19 maintained
event streams. The complete membership is in the
[single directory](../../src/loop_engine/core/service_runtime/feed_source_collections.json).

The supplied audit's 184 research sources and 220,000 candidate definitions
belong to different inventories. They are not added to the directory count.
Source IDs, URLs, collectors, observations, decision briefs, parameterized
views, component files, runs and accepted outcomes each need their own count.
Historical retrieval, token-saving and competition figures are not rerun here
and do not establish general customer savings or current benchmark leadership.

## One service, separate customer experiences

The [owner's brand decision](../architecture/OWNER-DECISIONS.md#separate-product-brands-october-13-2026)
keeps Baltor's combined product site and gives AgentFeeds its own site at
`agentfeeds.si`. AgentFeeds needs its own navigation, visual design, onboarding,
canonical links, errors and setup material. A redirect or a Baltor navigation
shell does not satisfy that direction.

Reuse the same feed contracts, backend, account identity, entitlement policy
and operator. Select presentation from exact trusted hosts. A host or brand
header must not grant tenant access, model access or a new billing allowance.
Keep browser assets and requests on the intended origin; validate email,
confirmation, recovery, consent and checkout return destinations. Shared
accounts require explicit session behavior on each domain, not copied tokens.

The current price decision is Basic at $9 per month, with Feeds free through
December 31, 2026 Eastern and explicit paid opt-in. A price is not evidence
that saved feeds, hosted schedules or personalized push delivery work.
Existing grants and subscriptions remain governed by the
[current pricing decision](../architecture/OWNER-DECISIONS.md#current-prices-october-11-2026).

Onboarding should let someone inspect a useful collection, select sources,
download an agent reading profile and verify one read in their chosen harness.
Show the source-documentation date and the actual schedule owner. A successful
download must not be described as native loading, execution or an accepted
decision. Profile edits should invalidate old download results immediately.

## Existing implementation and the remaining connection

| Concern | Existing owner | Finding and next acceptance |
|---|---|---|
| Public collections | [Source renderer](../../src/loop_engine/core/service_runtime/feed_source_collections.py) | Bounded directory projection; release candidate has stable item IDs and RSS alongside JSON and Markdown |
| Per-agent selection | [Profile compiler](../../src/loop_engine/core/service_runtime/feed_profiles.py), [web export](../../src/loop_engine/core/service_runtime/feed_profile_web.py) | Shared compiler produces passive files; saved hosted settings and an activated schedule remain absent |
| Catalogue notice | [Catalogue feed](../../src/loop_engine/core/service_runtime/catalogue_feed.py) | Current served-state notice; no complete event history |
| Source collection | [Knowledge radar](../../tools/knowledge_radar/README.md) | Typed adapters, source contracts, budgets and private observations exist; qualify each source's actual contribution to public feeds |
| Decisions | [Question planner](../../tools/knowledge_radar/planner.py), [brief compiler](../../tools/knowledge_radar/brief.py) | Dated candidate answers and missing-evidence states exist; customer delivery and comparative benefit need qualification |
| Durable source work | [Managed adapter](../../tools/knowledge_radar/community_store.py), [work compiler](../../tools/knowledge_radar/community_work.py) | Reuse managed revisions and the reactive scheduler; no second research store or queue |
| Bounded execution | [Overnight queue](../../tools/overnight_queue.py) | Executes an ordered manifest of task files with reserved limits and unknown-outcome holds; raw-data task extraction is separate |
| Brand delivery | [Presentation profiles](../../src/loop_engine/core/service_runtime/brand_profiles.py), [HTTP boundary](../../src/loop_engine/core/service_runtime/http.py) | Exact host/origin behavior and independent UI require integrated browser and live checks |

The gap is the qualified connection between existing source observations,
task-specific decisions and customer delivery. Rebuilding each part would
duplicate working ownership. Installing a source adapter alone does not close
that gap. The earlier [source-selection record](AGENT-FEED-SOURCE-COLLECTIONS-2026-10-08.md)
is a dated, smaller directory snapshot and should retain its original counts.

## Collection mechanisms worth using

GitHub recommends webhooks where available, conditional authenticated polling
when polling is necessary, serial requests and explicit rate-limit handling.
Use these mechanisms for a declared repository watchlist and preserve actual
request outcomes. This is documentation review, not a throughput measurement. [GitHub REST practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

The MCP Registry documents cursor pagination, `updated_since` and deleted
records in incremental synchronization. Keep native server/version identities
and status changes; a deleted listing must not survive as a current option.
Registry admission does not establish that a server works for the task. [Official registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)

PyPI recommends the JSON Index API for new integrations and exposes serial
markers and project distribution records. Preserve package, release and file
identity separately. A wheel for another platform is not a new capability. [PyPI Index API](https://docs.pypi.org/api/index-api/)

OSV batch queries match package/version or commit inputs and return advisory
identities with modification dates. Pagination can apply separately to each
query. Resolve relevant records and match the actual pinned environment before
proposing an update. An empty page is not a blanket security certificate. [OSV batch queries](https://google.github.io/osv.dev/post-v1-querybatch/)

For every activated source, retain its access mechanism, credential reference,
rights, parser version, cursor, last attempt, last success and coverage limits.
Keep publication, effective, observation and verification times separate.
An interrupted request has an unknown outcome until reconciled. Retrying
must respect the existing shared quota and effect owners.

## The first four decision families

Use a pinned development set first, then separately authored acceptance cases.
The order below is a proposed delivery sequence, not four completed services.

| Order and family | First useful output | Acceptance before expansion |
|---|---|---|
| 1. Model lifecycle and cost | A pinned workload's affected model/version, effective date, incumbent and alternatives, with a bounded parity test | Catch applicable retirements and price-unit changes; withhold wrong-platform notices; separate listed-price estimates from measured usage; keeping the incumbent can pass |
| 2. MCP and harness compatibility | An exact client/server/SDK change and the integration test it requires | Preserve deleted/deprecated status, authentication and scope changes; exercise the supported host; a registry listing or installed file alone cannot pass |
| 3. Dependency applicability | A package/version advisory match, fixed-version candidate and rollback check | Test aliases, affected ranges, withdrawn records, absent dependencies, partial responses and unknown versions; avoid unrelated update tasks |
| 4. Creative production | A coherent image, motion, scene or audio recipe with usable source and a revision plan | Render the requested result, inspect visual/audio quality, make a meaningful revision and reopen in a clean supported environment; preserve asset rights and exact dependencies |

Each family starts with a small explicit source set and one real customer job.
First demonstrate collection, then correct applicability, then a supported
agent's decision, and finally an independently checked outcome. Expand when
new sources cover missed jobs or reduce decision error at an acceptable cost.

Creative coverage must extend beyond engine links. Background generation,
segmentation, motion, typography, composition, narration, audio mixing and
export each can change the result. The acceptance target is the finished work
and its editability. Layer counts, frame counts and successful encoding do not
replace inspection against the chosen production format.

## Queue belongs in AgentAFK

The [AgentAFK queue direction](../architecture/OWNER-DECISIONS.md#task-intake-and-prioritization-within-agentafk-october-13-2026)
places extraction and prioritization of authorized raw inputs there, including
feed evidence. A queue candidate needs the source observation,
task, expected output, next check, dependencies, missing information, estimated
effort, deadline, budget fit and reason for its position. Raw source instructions
remain data. A recommendation does not authorize installation or execution.

The current community intake ranks keyword hints: tool mentions, workflow or
failure signals, and a linked GitHub source. The scheduler adds priority aging.
That is an inspectable baseline, not a measurement of task value. Compare a
future task ranker against it and first-in-first-out ordering on independent
labels. Include duplicate, irrelevant, superseded, dismissed and keep-current
cases; preserve source-to-task references when multiple observations support one task.

Existing projects separate scheduling mechanics from useful task selection.
Airflow documents absolute and dependency-derived priority weights plus custom
strategies. Celery documents broker-dependent priority behavior and explains
why late acknowledgments require idempotent work. These are relevant designs;
this review did not run either as a replacement engine or establish superiority
over the existing scheduler. Reuse the current scheduler now; qualify any
replacement behind its existing contract. [Airflow weights](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/priority-weight.html), [Celery routing](https://docs.celeryq.dev/en/stable/userguide/routing.html), [Celery task acknowledgments](https://docs.celeryq.dev/en/stable/userguide/tasks.html)

The queue review reproduced a concrete failure: a dismissed lead returned to
work after a compiler revision. The prepared repair preserves dismissal during
source refresh, refuses new admission and checks current managed state before
compilation. A pending dismissed activation becomes canceled with
`LEAD_DISMISSED`, retaining its history. The repair passed 140 related tests
and three removed-guard controls. This is component evidence, not a hosted
customer Queue launch or a retroactive withdrawal of earlier briefs.

## Matching, rights and correction behavior

Apply eligibility before ranking: task, platform, exact version, required
inputs, available access, rights, declared effects and budget. Missing critical
facts should yield a bounded research task or abstention. Preserve rejected
alternatives and the conditions that would justify reconsidering them.

Retain canonical public evidence once and derive customer views as needed.
Keep private project constraints, credentials, costs and feedback within their
authorized account scope. Assign retention separately to source metadata,
permitted excerpts, private uploads, decision records and execution records.
Collection access does not grant redistribution rights; record attribution and
reuse conditions per source and asset, with a usable withdrawal path.

Corrections need stable identities, immutable revisions and explicit
supersession. Notify affected decisions, invalidate cached views and preserve
why a recommendation changed. An outage must appear as missing coverage.
No-change, partial success, withdrawn content and unknown request outcome are
different states. A changed directory must not silently expand a saved selection.

## Retrieval and economics

Compare lexical retrieval, the deployed representation and any challenger on
the same frozen corpus, filters and independently judged queries. Include
incomplete metadata and negatives. BEIR supplies established retrieval
evaluation patterns and metrics; it does not measure Baltor's changing-source
coverage or decision usefulness. Report those separately. [BEIR evaluation framework](https://github.com/beir-cellar/beir)

The product comparison should hold the agent, model, task and budget constant:
ordinary browsing versus Baltor evidence with permitted browsing, plus a raw
source digest control where practical. Measure accepted decisions, supported
claims, useful-alert precision, appropriate silence, missed changes, latency
and human review time. Preserve failed attempts and judge disagreement.

Cost per accepted outcome includes acquisition, refresh, search, verification,
model usage, retries, storage and allocated operating cost. It is undefined
when no outcome is accepted. Separate cold, cached and refresh runs, and keep
estimated time value apart from realized cash savings. Use repeat customer
utility and servicing cost to test the Basic offer; source counts do not
establish demand or retention.

## Release acceptance and unfinished work

The prepared source changes include stable collection item IDs, curated RSS,
trusted-origin reading guides and the dismissal repair. Brand presentation
and shared-account integration remain subject to the release's exact checks.
Run the existing source/profile checks, `test_brand_presentations`, the
AgentFeeds browser checks, and negative origin/cross-tenant/cache controls on
the integrated tree. Preserve failed attempts alongside passing continuations.

Live acceptance requires the real domain and TLS, all brand pages and links,
anonymous and conditional downloads, profile export and a fresh harness read.
Exercise supported sign-up, recovery, consent and billing-return routes while
checking Baltor for regressions. Record the committed revision and rollback
identity through the existing guarded release procedure.

Saved account feeds, maintained decision streams, prospective coverage,
customer task-priority benefit and creative portability remain separate
acceptance work. This record adds no blanket claim about frontier agents and
does not convert the supplied history audit into complete account evidence.

## Owner clarification after launch preparation

Later on October 13 the owner prioritized keeping agents current directly,
providing ready-to-use agent files and tools, and inexpensive long-horizon
overnight work. Token savings are a longer-term measurement concern, not a
launch gate. The comparison methods above remain useful for later claims;
they must not delay publishing a useful source directory or working profile.

The owner also requested customized self-learning AgentAFK queues, with
graph-based dependencies and priorities, comparable to Airflow for agents.
Airflow's documented dependency graphs, priority strategies and resource pools
are useful scheduling references. They do not themselves establish learned
task value or acceptance of an agent result. Reuse the current task store and
scheduler first, and qualify a replacement behind the existing typed edge.
[Airflow task dependencies](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html),
[priority strategies](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/priority-weight.html),
[resource pools](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html).

Separate the prerequisite graph from the execution graph. Readiness enforces
dependencies and declared effects before a ranking engine orders eligible
tasks. Bounded research and revision stay within the existing Loop behavior;
new task discoveries create reviewable graph revisions. Learn from independently
checked outcomes, cost, elapsed time and intervention rather than rewarding
raw activity or the agent's own completion claim. Version the policy, retain
customer preferences and dismissal, evaluate held-out cases, run challengers
in shadow and preserve a deterministic fallback. S-6.24.03 owns this work;
an adaptive customer queue is not part of the AgentFeeds launch claim.
