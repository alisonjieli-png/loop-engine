# Knowledge radar

Kind: tool component and architecture contract, internal local zone. Roadmap
step S-6.214 (daily distillations) and the owner's knowledge radar direction
of September 27, 2026. The command is
[`tools/build_knowledge_radar.py`](../build_knowledge_radar.py). The research
record is
[`docs/research/KNOWLEDGE-RADAR-2026-09-27.md`](../../docs/research/KNOWLEDGE-RADAR-2026-09-27.md).

The radar answers recurring engineering questions once, for everyone, and
serves each answer as dated files a coding harness can load: a decision card
with ranked, source-linked evidence, a data file with its schema, a small
decision helper over that data, or a tool that fetches a fact too volatile
to store. Every answer names the day it was checked and the day it stops
being current. The radar approves nothing, serves nothing and publishes
nothing: its packages are candidates for the existing independent review and
catalogue release path.

`community.py` prepares disclosed questions for selected practitioner
communities and converts research notes into unreviewed leads. Its posting
request uses the existing `EXTERNAL_MESSAGE` effect and binds the exact
account, destination, content and rules evidence. It sends nothing. Platform
connection, approved dispatch, uncertain-outcome reconciliation and reply
collection remain integration work. Store those records through
`RecordOperationService`; do not add a second queue or approval system.
Automated commercial Reddit access requires a platform-access review before
activation. A public reply does not grant permission to redistribute its
code, assets or prose. See [the source and engine record](../../docs/research/CREATIVE-COMPONENTS-AND-ENGINE-CONTROL-2026-09-29.md).

## Multidimensional query pages

`tools/plan_knowledge_queries.py` extends this radar's discovery planning. It
reuses the idea matrix's method vocabulary, the expansion policy's contexts,
the existing source contracts and `CommunityStore`/`RecordOperationService`.
It adds no scheduler, database implementation or source engine, calls no model
and cannot approve or publish material. The original query compiler and its
tests were produced by OpenAI; they do not change the Anthropic provenance of
the older radar generator or assets.

The typed edges are `knowledge_radar_query_matrix/v1`,
`knowledge_radar_query_cursor/v1`, `knowledge_radar_query/v1`,
`knowledge_radar_query_page/v1` and `knowledge_radar_query_tick/v1`.
Readers reject unknown versions, extra fields, invalid bounds and changed
cursor bindings. The validated matrix is an immutable snapshot. A cursor
binds the vocabulary, routes, source contracts and implementation files.
Query identity binds normalized source/query text; work identity also binds
the source contract, explicit dispatch parameters and implementation. Neither is a component
method identity. Reuse unchanged implementations across applicability facets.

```text
Existing Practitioner/code-execution Loop and managed records
├── Lazy query pages: country/area, SDG target, industry, task, audience,
│   occupation, language, artifact form, harness, source kind, failure mode
├── Existing radar source edge: public repository metadata, bounded reads
└── Observed origins awaiting source, rights, relevance and qualification checks
    └── Existing component preparation/admission/publication path; no automatic grant
```

The deterministic coprime traversal spreads successive queries over all
dimensions and rotates routes. It does not allocate the whole Cartesian
product. The upper-bound combination count includes hypotheses that may be
duplicates, incompatible or useless. Pages report examined combinations,
deduplicated planned queries, exclusions and emitted-value coverage. Executed
queries, physical request reservations/logs, empty reads, partial responses,
failures and distinct observed origins are separate counters. None measures
useful files, complete world/source coverage or accepted customer outcomes.

The language facet contains English language names; it does not translate
queries. The live pilot used three simple phrases, each read twice during
development. Discovery yield for the default conjunctive country/method
matrix remains unmeasured. Requiring country or industry words can miss
globally reusable code whose documentation does not mention those facets.

The default country vocabulary is an explicit 16-name pilot. For a full
source-bound inventory, pass `--country-inventory` with
`knowledge_radar_country_inventory/v1`: `source_url`, `source_sha256`,
`observed_on`, `rights_basis`, `coverage` (`declared_m49_snapshot` or
`pilot_subset`), and `entries` of distinct three-digit `m49`/`name` pairs.
`source_sha256` may bind an exact source manifest for multiple files. Preserve
that manifest, upstream notices and code/name mappings beside the input.
Inventory completeness must be compared with a dated primary snapshot;
structural validation alone does not certify it. Country/area names are not
legal jurisdictions or sovereignty claims. Aggregate regions are separate.
The command never fetches or redistributes a country taxonomy on its own.

Preview (no files or requests):

```sh
PYTHONPATH=src:tools python tools/plan_knowledge_queries.py \
  --state /path/to/private/community-state --page-size 10
```

Add `--authorize-local-writes` to save one page in that same managed store.
Existing `source` and `run` records own the cursor, page journal, planned
queries, attempts and observed origins; planned queries never masquerade as
observed community leads. The existing `scan.lock` serializes operators.
Page journals recover a partial enqueue without losing or doubling work.
Recovery replays the bounded page and checks its queries, route, facets,
purpose, counters and next cursor. A query's managed record identity must
match its exact work identity before dispatch.
Execution selects only this exact plan's queued work; another plan in the
same store is not drained. A duplicate already pending under an earlier plan
stays owned by that earlier plan. It is not re-enqueued as a new capability.

Only `github_search` currently has a compatible keyword-query binding.
`--execute-queued --authorize-network-reads --authorize-local-writes` enables
it, through the existing canonical Loop, `RadarNetwork` and `RequestBudget`.
Defaults are five operations, five physical requests and five per source;
each is separately bounded by flags and the existing source contract. Public
repository search is forced. Quoted terms cannot introduce search operators.
The GitHub adapter also requires an explicit `private: false` response field,
no contradictory visibility, and a canonical GitHub URL matching `full_name`.
Rejected rows leave no repository name, URL or description in saved results.
The selected engine identity/version must match the source contract.
Official-web and other incompatible source routes remain `deferred_adapter`.
No scraping fallback, broad credential access or private-source dork is added.

Use only public, non-confidential vocabulary. Repository secret patterns and
query-specific email, private-path and confidentiality markers reject obvious
cases before storage. These are heuristic checks. They cannot infer whether
an arbitrary phrase is confidential; the operator remains responsible for
the terms authorized for external search.

An attempt intent is recorded before the dispatch hold. An orphaned intent
alone means no request was dispatched. Once the hold is reserved, interruption
leaves `reserved_unknown_outcome` until an operator reconciles the request
log. Query holds use query identity, and source access/rate holds use source
identity; changing a parser or implementation version cannot clear them.
Earlier unresolved records keep their holds. Reconciliation reads at most
1,000 records in each of four state/kind windows and stops dispatch if a
window might be incomplete. The queued lookup has its own 1,000-record cap.
The planner does not claim an exhaustive census from a capped window.

A saved attempt result can survive an interrupted origin fold. The read is
not repeated; an operator must reconcile the missing fold and hold. This
command does not perform that reconciliation automatically. Saved failed
attempts with access/rate refusals also hold the source, even if the process
stopped before writing its source-hold record. Reconciliation must preserve
the failed response and rationale in a new managed revision, mark the
reconciled attempt complete, and resolve its work/dispatch/source holds.
Changing only a hold flag does not clear the unresolved attempt evidence.
The inner failed outcome remains failed; completion records reconciliation,
not a successful source read. Store checks
detect corrupt or mismatched records, not a malicious writer who can replace
the entire trusted operator store and its inputs.

Source observations keep licence *declarations*, not redistribution grants.
Exact versions, payload/media/model/data rights, direct relevance, privacy,
compatibility, meaningful positive/negative checks and independent admission
remain gates. Services/MCP/SaaS require their actual operations,
authentication, costs, limits, effects and evidence date before a useful
reference or connection recipe is proposed. Query output alone cannot do so.

Offline checks: `PYTHONPATH=src:tools python -m unittest
tools.test_knowledge_query_matrix tools.test_harness_idea_matrix
tools.test_knowledge_radar tools.test_community_watch`.

## Bounded community watch

`tools/watch_community_workflows.py` adds a separate acquisition path to this
component. Its `community-watch-v1.json` declares six public forum feeds and
bounded research topics. Direct Reddit feeds and APIs are not enabled. An
optional native Codex invocation uses the existing ChatGPT login and native
web search to research one topic; it is not a substitute Reddit API or an
access-control bypass.

The operator must authorize network reads and private local writes. Native
research needs its own grant. A tick reads at most twelve responses, considers
at most forty entries per source, compiles twenty work orders and reserves at
most one native invocation. The durable daily ceiling is four invocations.
One invocation can contain several model turns; physical model calls are
unknown when the harness does not report them. Token usage is preserved when
reported. The search/page limits in its prompt are guidance, not a verified
native enforcement counter. Process duration is bounded separately.

Source state, leads, original summaries and work orders use the existing
`RecordOperationService`. Queue admission and fenced worker completion use
`SQLiteReactiveScheduler`. Feed reads and compilation run inside canonical
Loops; the optional delegate is one bounded model-led Loop. There is no new
runtime or approval path. State remains outside the repository. Thread bodies,
author profiles, copied code and downloaded media are not retained. A source
link or keyword classification establishes neither rights nor correctness.

Failed reads preserve the last successful state and back off. Validators bind
to the exact source URL. Repeated inputs do not create repeated work. A changed
compiler has a new source digest, requeues saved leads and defers old briefs;
bounded reconciliation reports incomplete coverage instead of claiming a full
backfill. Per-run identifiers remain unique even within the same second.
The persisted scheduler journal is not a complete native model transcript.

Example, with a private directory chosen by the operator:

```bash
PYTHONPATH=src:tools .venv/bin/python tools/watch_community_workflows.py \
  --library /absolute/private/community-state \
  --authorize-network-reads --authorize-local-writes
```

Add `--authorize-native-research` only for the existing subscription route.
Without both read and write grants the command returns a plan with no effects.
Scheduling must use a pinned reviewed checkout, not mutable source. This path
does not post, install a discovered tool, approve a component or publish files.
Its positive and refusal checks are `tools/test_community_watch.py`.

## Authenticated community API intake

`tools/read_reddit_research.py` reads the owner's selected Reddit34 endpoint
through RapidAPI. The credential is resolved from the system keyring and sent
only to the fixed provider host. The reader follows no redirect, performs no
automatic retry and retains no thread body, author profile or media. It
normalizes the observed response into the same `community_workflow_lead/v1`
records that feed the existing managed store and reactive scheduler.

The [community registry](community-sources-v1.json) holds the requested design,
game, modeling, graphics and video sources. An explicit read can select one
community; recurring runs rotate that registry. A private source record reserves
each request before dispatch and carries the provider's remaining allowance.
The next read waits at least a day and longer when needed to spread the
remaining allowance over the provider's reset window. An uncertain request
requires reconciliation before another call. This command alone installs no
timer, invokes no model, approves no candidate and publishes nothing.

```bash
PYTHONPATH=src:tools .venv/bin/python tools/read_reddit_research.py \
  --library /absolute/private/community-state --subreddit aigamedev \
  --authorize-network-reads --authorize-local-writes --authorize-keyring-read
```

The existing credential reference is service `reddit34.p.rapidapi.com`, account
`owner`, purpose `research-api`, application `loop-engine`. No key belongs in a
command, registry, generated component or report. Other API providers need
their own observed request contracts and account allowance before activation.

Checks: `tools/test_rapidapi_reddit.py` and `tools/test_reddit_research.py` cover
source binding, response failures, complete-window accounting, duplicate and
removed posts, credential destination, quota pacing, queueing and uncertain
outcomes. Forum claims remain unverified leads with no established reuse rights.

## Daily source-led expansion

`tools/expand_community_capabilities.py` consumes the watcher's research work
orders and prepares complete native candidates. It uses the existing managed
record store, model gateway and native preparation factory. Each work order
has three bounded model turns: identify a useful opportunity, interrogate and
revise it, then produce files. The second turn can choose reuse or defer;
neither produces another package. This production critique is not independent
review.

The policy in `expansion-dimensions-v1.json` covers industry, use case, data
type, role and job description, stage, failure, contracts, tools, constraints
and delivery format. These are applicability dimensions. Package identity
excludes title, industry and output format and instead binds the method,
input/output contracts and discriminating checks. Exact method matches are
reused. The existing candidate store is also searched read-only before the
critique; that metadata search is bounded and reports incomplete coverage.
It does not prove semantic uniqueness or approve an existing candidate.

The default policy allows at most 32 work orders and 96 model dispatches per
UTC day, with an 8,192-token output allocation and 180-second timeout per
turn. Reported usage reaching two million tokens stops further dispatches;
this is a post-call stop, not an exact preflight total-token bound. Unknown
usage, an interrupted reservation or an unknown provider outcome blocks more
calls that day. There is no failover, automatic retry or provider purchase.
The scheduler must share one private state directory so repeated invocations
share these limits.

```bash
PYTHONPATH=src:tools .venv/bin/python tools/expand_community_capabilities.py \
  --library /absolute/private/community-state \
  --candidate-store /absolute/private/import-store \
  --maximum-work 32 --authorize-local-writes --authorize-model-calls
```

Without both grants the command returns a plan and writes nothing. Production
requires the generator and policy to match the current committed revision.
Use an immutable reviewed checkout for scheduling. Outputs include native
payloads, the model's declared dependencies and effects, source references,
contracts and test fixtures. They remain outside Git and are not executed by
this command. A prepared catalogue is directly readable by
`tools/review_catalogue_candidates.py --content-profile native-original`.
Independent review, sandbox qualification and catalogue publication remain
separate stages; a daily candidate count is never the live library count.

The watcher includes forum, news and RSS metadata. Social-media and vendor
research uses the separately authorized native web-research route. It does
not scrape private communities, retain author profiles, post messages or
republish discovered content. The source registry includes 3D generation,
procedural systems, workflow automation and geospatial research topics.

Checks: `tools/test_community_expansion.py` and `tools/test_community_watch.py`.

## Runtime classification

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

A daily-brief radar run is a Starting Practitioner task of the code execution profile
that an operator or a timer starts with the command above. It runs
deterministically and makes no model call. Its source engines, the brief
generator, the planner and the vetting checks are adapters and records the
run uses: none is a graph vertex, a role, a mode or a runtime type. Reads of
the network need the run's explicit grant and each engine's source contract.

## The owner's delivery rule, as typed fields

Each question in [`questions-v1.json`](questions-v1.json) declares its
research cost (engineer minutes and distinct sources), the volatility of its
facts, its delivery kinds and its refresh cadence. The reader refuses a
question whose delivery breaks the rule:

```text
delivery rule (records.rule_findings)
├── facts change faster than the refresh  -> a tool that fetches them; nothing stored may carry them
├── research above the threshold          -> a brief or a data file, done once for everyone
├── research at or below the threshold    -> no stored file; at most a tool
└── a helper or a tool                    -> names its asset; a helper reads a data file
```

The threshold is the owner's: more than five engineer minutes or more than
one website. A sensitive question (legal, security or financial) carries the
review requirement of two independent model families with a source on every
claim.

## Records

```text
knowledge_radar_question_registry/v1   the declared questions, the rule and the planner policy
knowledge_radar_question/v1            audience, constraints, baseline, acceptable evidence,
                                       intended output, research cost, volatility, delivery,
                                       refresh, sensitivity, questions to ask again, negative knowledge
knowledge_radar_source_contracts/v1    one ingestion contract per engine: access method, hosts,
                                       permitted uses, what is never used, attribution, terms,
                                       pacing, request ceiling, failure policy
knowledge_radar_observation/v1         one claim: key, common origin, title, link, facts, licence,
                                       event_at, source_published_at, observed_at, effective_from,
                                       effective_until, last_verified_at, review_after
knowledge_radar_source_check/v1        one binding's check outcome: checked with no relevant change,
                                       checked with a material change, partially checked, could not
                                       check, source disappeared or access changed
knowledge_radar_plan/v1                the questions a run selected (first run, overdue, changed
                                       source, demand, exploration) and a stable work identity each
knowledge_radar_brief/v1               the decision card and its evidence, or a notice that no
                                       currently validated recommendation exists
knowledge_radar_table/v1               a question's current claims as one typed table, with a schema
knowledge_radar_vetting/v1             six separate vetting dimensions per package
knowledge_radar_index/v1               every declared question with its honest answer state
```

A failed read is never recorded as "no change": the previous successful
check stays the baseline, its claims keep their old dates, and the brief
lists the failure under what is not established. Reading an old dated claim
again never renews it: its review date counts from the claim's own date.

## Engines behind one source edge

`knowledge_radar_source/v1` has seventeen Baltor-native engines. Local
engines read files: `collector_state` (the source discovery collector's
latest private exports, read only), `model_directory`,
`endpoint_directory`, `mcp_directory` (the directory data this repository
packages for its public pages) and `curated_seed` (official links a person
declared, unverified until a link check resolves them). Network engines
make bounded read-only requests through the library ingestion transport,
budget and request log: `github_search`, `github_advisories`,
`github_releases` and `owner_directory` through the gh login with the
radar's own read-only allow list, and `huggingface_models`,
`huggingface_new_models`, `arxiv_listing`, `openalex_works`,
`endoflife_calendar`, `federal_register`, `models_dev_catalogue` (models.dev,
MIT) and `litellm_prices` (the LiteLLM price map, MIT) over HTTPS GET. No
engine reads OpenRouter or Artificial Analysis by script: the contracts file
names both as hosts that are never read, a contract that names one is
refused, and both appear in briefs only as attributed links a customer
opens. The model directory's LMArena text scores (CC BY 4.0) are shown with
their credit, which every brief carries for each source that gave it claims.

Each source contract says whether the source's facts may be stored in a
served file (`republication`) and which upstream values its engine drops
(`excluded_upstreams`, `excluded_publishers`). A run refuses to start when a
question that stores an answer binds a live-lookup-only source, and the
directory engines drop every value the packaged directories took from
OpenRouter or that Artificial Analysis published. The reason is decision 7
of `docs/research/SHARED-RESEARCH-SERVICE-LANDSCAPE-2026-09-27.md`. Source prose that an answer carries
(descriptions, abstracts, release notes, advisory summaries) is kept only
as hashed eight-word runs, so the vetting stage can refuse a brief that
repeats it. A title that tries to steer a reader is excluded, never
rewritten.

## Hourly model watch

[`tools/watch_model_releases.py`](../watch_model_releases.py) checks the
bindings of the hourly question `models_new_releases` once: models.dev, the
newest Hugging Face repositories of major labs and the LiteLLM price map. It
sends back the validators of each source's last complete read, so an
unchanged source answers 304, which is the only "no change" that needs no
body. A failed read is "could not check" and changes nothing; a partial read
never counts a removal. On a material change it writes a change record under
`<library>/model-watch/<day>/` and marks every question that reads that
source; the daily planner answers those questions before they are due. It
never reads a model card and makes no model call.

```text
PYTHONPATH=src:tools python tools/watch_model_releases.py \
  --library /home/username/baltor-library/radar --authorize-network-reads --authorize-local-writes
```

## Stages of one day

```text
plan -> collect -> links -> diff -> brief -> package -> vet -> feed -> record
```

Each stage writes its files and a done marker in the day folder. A second
process for the same day answers `already_running`; a finished day answers
`already_complete` and writes nothing; an interrupted day resumes at the
first unfinished stage and never reads a stored source answer again. Only
the last stage writes the shared state under `<library>/state`: the last
successful check of each binding and four freshness times (last attempted
retrieval, last successful retrieval, last material change, last successful
evaluation).

## Deliverables in the existing package format

```text
brief (and data file)   skill package: SKILL.md, references/brief.json, references/provenance.json,
                        contracts/brief.schema.json, optional table and table schema, LICENSE
decision helper         tool package: the asset's files plus the day's table at its data path
tool                    tool package: the asset's files, with typed input and output contracts,
                        a known-wrong test and no stored value
```

Packages pass through the existing preparation factory
(`tools/prepare_harness_candidates.py`), which pins every cited repository
file to the committed revision. The assets live in [`assets/`](assets/).

## Vetting dimensions

`source_identity_checked`, `claim_supported_by_cited_evidence`,
`implementation_inspected` (the existing native prechecks),
`implementation_tested_or_reproduced` (the package's own tests in a
bubblewrap sandbox with no network, including a known-wrong case),
`compatibility_tested` and `publication_approved_for_scope`. The last two
are never done by this component.

## Command

```text
PYTHONPATH=src:tools python tools/build_knowledge_radar.py \
  --library /home/username/baltor-library/radar --as-of 2026-09-27 \
  --collector-state /home/username/baltor-private/source-discovery-2026-09-26/state \
  --authorize-network-reads --authorize-local-writes
```

Without `--authorize-local-writes` it prints the plan that a run would make
now, read from the library's state, with the reason for each selected
question, and writes nothing. `--only` limits a run
to named questions, `--skip-link-checks` and `--skip-sandbox-tests` leave
those dimensions not done, and `--stop-after` stops after a stage.
`--rerun` answers every planned question again, for example after a fix;
give it a new `--output` folder so the earlier attempt stays beside it. The
checks are [`tools/test_knowledge_radar.py`](../test_knowledge_radar.py),
[`tools/test_knowledge_radar_pipeline.py`](../test_knowledge_radar_pipeline.py),
[`tools/test_knowledge_radar_assets.py`](../test_knowledge_radar_assets.py)
and [`tools/test_knowledge_radar_model_watch.py`](../test_knowledge_radar_model_watch.py).

## What the first version implements

| Owner direction of September 27, 2026 | First version |
|---|---|
| Research cost, volatility, delivery and refresh per question, with the rule | Implemented: typed fields; the reader refuses a delivery that breaks the rule; known-wrong checks and a removed-guard control |
| Deliverable kinds | Implemented: skill packages with the brief and its metadata, typed tables with schemas, two decision helpers (`choose_model`, `check_support_window`) and four tools (`check_service_status`, `query_package_advisories`, `fetch_reference_rates`, `lookup_legal_entity`) |
| A wider question list | Implemented: 65 questions, 55 with a source and 10 declared gaps with reasons, including retrieval methods with the STAIR paper as a lead |
| Hourly checks for model releases | Implemented: the hourly question, the change-detecting watch with validators sent back over three openly licensed sources, and invalidation of the dependent questions; the schedule is proposed, not installed |
| First demonstration: small models for structured extraction | Implemented: the question `models_structured_extraction` and the `choose_model` helper 2.0.0 over openly licensed data; the measurement and release are the demonstration's own steps |
| Stored facts only from openly licensed sources | Implemented: no engine for OpenRouter or Artificial Analysis, a refused contract for any host that must not be read by script, the republication field and run guard, the directory engines' exclusions, and credits in every brief, each with a known-wrong check |
| Vetting before the context layer | Implemented: native prechecks, seed link checks, schema validation, copied-text refusal, sandbox tests with known-wrong cases, the stricter review requirement on sensitive questions. Independent review stays with the existing panel |
| Question registry and planner | Implemented |
| Check outcomes, time fields, "no currently validated recommendation" | Implemented and tested |
| Separate vetting dimensions | Implemented |
| Common origin and ingestion contracts | Implemented |
| Negative knowledge | Implemented in every brief |
| Cheapest model per thinking per task | The proxy helper is implemented; the measured frontier is design |
| Suggested sources | Wired: arXiv, OpenAlex, Hugging Face Hub, models.dev (through the model directory), GitHub releases, the official protocol server registry (through the collector and the directory), OSV and GLEIF (as tools), FederalRegister.gov. Not wired: eCFR, SEC EDGAR, SAM.gov, USAspending |
| Durable stages, journals, stable work identities, idempotent publication | Implemented; DBOS and Temporal remain candidate engines |
| Readiness demonstrations | Tested: resume, duplicate trigger, steering source, expired claim. Revocation uses the existing catalogue withdrawal path and is not exercised here |
| Repeat only invalidated work | The planner re-runs only overdue or changed questions and the run writes invalidation edges; running only the affected work from the edges is design |
| Reuse at five levels | Source answers, claims, implementations and scoped, expiring failure records are written; comparisons under an evaluation contract are design |
| Four freshness times | Kept per binding in the shared state. The hourly watch sends conditional requests; the daily run still reads each source in full |
| Honest answer states | Implemented in the index and feeds |
| Three data layers and request coalescing | The radar writes the public shared layer only; the work identity is implemented, attaching a second request to a running job is design |

## Design choices and their reasons

- The rule's threshold is five minutes or more than one source, from the owner's words.
- Briefs are skills, so a harness loads one when a step needs it instead of at every start. The skill
  name is stable per question, so a newer brief replaces an older one in a harness folder.
- A brief declares only `reads_fs`. It asks for no network, and it tells the harness to re-check a link
  only under the step's own network authority.
- The producer family is anthropic, because Claude wrote the generator and the assets, so reviewers come
  from another family.
- The hourly watch reads models.dev, Hugging Face and the LiteLLM price map. OpenRouter's terms forbid
  reading it by script, so no engine reads it.
- The cheapest model per unit of thinking stays a declared gap until it is measured: a listed price divided
  by a published index is neither allowed under the terms nor a measurement of thinking on a task.
- High confidence needs two independent source engines; one source gives at most medium.
- Seeds hold names and links only; the reader refuses a seed name that holds a number with a unit.
- Public-service files are not edited by this component; the routes are designed in the research record.

## Limits

- No model reads a source: briefs list, rank and date; they do not summarise.
- Link checks cover seed links; engine links come from each source's own answer.
- The planner reads local change times; network sources are re-read on their cadence.
- arXiv's edge refuses some automated reads with 406 at busy times; the engine waits and tries once more,
  then records "could not check".
- Serving, freshness in search, withdrawal of superseded briefs and a schedule are designed in the research record and not installed here.
