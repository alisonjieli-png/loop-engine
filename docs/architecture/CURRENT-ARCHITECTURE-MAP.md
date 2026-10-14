# Loop Engine current architecture map

Kind: maintained orientation guide. Source checked against release 87,
revision `9d7b7e50`, on October 11, 2026. This page is not a generated file
inventory or a second contract registry. The
[generated source map](../../src/loop_engine/ARCHITECTURE-MAP.md),
[component guides](../components/README.md) and
[contract index](../contracts/README.md) own the implementation detail.
The [current deployment](MVP-CLIENT-SERVER.md#current-deployment) and its
release records establish what is live.

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
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Deployment zones, services, engine slots, files and data stores are not
executable graph vertices. Preserve the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
of a discrete cognitive or act step Loop node.

## 1. Repository layout

```text
loop-engine
├── src/loop_engine: production package and packaged contracts
├── tools: internal acquisition, production, qualification and operators
├── integrations: customer harness integrations
├── devtools: development assurance, with no reverse production dependency
├── docs: current guides, contracts and dated evidence
├── examples and benchmarks: runnable examples and declared test populations
└── artifacts: recorded observations and generated views, not runtime authority
```

The [repository organization guide](../REPOSITORY-ORGANIZATION.md) owns folder
rules. Private source bodies, credentials, unpublished candidates and raw owner
history stay outside the public repository. A current file map comes from
`python -m loop_engine --map`; do not copy it into a second hand-maintained tree.

## 2. Package architecture

The [Core Architecture guide](../components/core-architecture/README.md)
defines three public capability groups: Intelligence Search and Retrieval,
Web Research, and Custom Plugins. Provider routing, permissions, workspaces,
stores, Runtime Memory and reports are internal mechanics.

The four operating zones separate customers from internal production:

```text
Baltor operating zones
├── Public service
│   ├── Website and public feeds
│   └── Authorized accounts, API/MCP, search and exact-file delivery
├── Customer environment
│   ├── Customer's chosen harness and model access
│   └── Selected files, native tools and customer-authorized effects
├── Internal hosted operations
│   ├── CI, guarded releases, health checks and publication operators
│   └── Scoped source collection and production coordination
└── Internal local or on-demand production
    ├── Research, candidate generation and native builds/renders
    └── Qualification, independent review and retained failure evidence
```

The [September 27 four-zone record](FOUR-ZONE-ARCHITECTURE-2026-09-27.md)
preserves the rationale and migration proposals. Its old machine sizes and
deployment paths are historical. A zone names a trust boundary, not necessarily
a machine: an operator running on the workstation still belongs to the
internal hosted-operations boundary when it changes production.

### Hosting and execution pattern

| Responsibility | Current placement | Execution pattern | Remaining qualification |
| --- | --- | --- | --- |
| Public pages and assets | Cloudflare Worker and exact static export | Available continuously, invoked per request | Export identity and dynamic-route exclusions checked per release |
| Accounts, billing, API/MCP and authoritative writes | Fly service with existing managed providers | One always-running Machine; `fly.toml` has autostop off | Any replacement must preserve identity, entitlements, effects and rollback |
| Authorized catalogue search | Custom SQLite-backed index on Fly | Request-driven within the running service | D1 and Lance candidates remain separate measured prototypes |
| Component bodies | Fly volume; current bodies also mirrored to R2 | Authorized reads; bounded publication batches | R2 mirroring is not activation of the authenticated body-store engine |
| CI and releases | GitHub Actions with scoped operators | Event-triggered jobs | Exact revision gates, single dispatch, readback and rollback |
| Source research and component production | Existing internal tools and approved worker environments | Bounded scheduled, triggered or operator-started jobs | Installed schedule, successful run and publication require separate evidence |
| Customer execution | Customer's chosen harness or qualified local worker | Customer-controlled, on demand | Download, native loading, execution and accepted outcome are different facts |

The current Fly configuration declares two shared processors and 4 GB memory,
with `min_machines_running = 1`. Public edge availability does not require
a permanently executing Worker. No new Cloudflare database, queue, model route
or browser worker is activated by this document.

### Cloudflare candidates

Evaluate Cloudflare products behind the existing contracts. Structured facts,
prices and requirements need exact filtering; semantic retrieval can return
related candidates and supporting evidence. It cannot make an unknown hard
requirement pass.

Vectorize currently documents ten metadata indexes per index and 10 KiB of
metadata per vector. D1 documents 100 columns per table and a 10 GB maximum
database on paid plans. These are design constraints, not measured Baltor
capacity. Use sparse typed observations and limited search projections, not
a universal table containing every comparison dimension.
[Vectorize limits](https://developers.cloudflare.com/vectorize/platform/limits/),
[D1 limits](https://developers.cloudflare.com/d1/platform/limits/)

Queues documents at-least-once delivery. A redelivered job must resolve its
existing invocation record before a paid or externally effective retry.
Queue, provider SDK and Loop repair must not independently repeat the same
logical operation. The existing scheduler and effect records own that policy.
[Queues delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/)

### Large local jobs and bounded cloud work

The October 11 catalogue reconciliation completed under a 20 GiB local limit
after an earlier 12 GiB attempt was killed at its ceiling. The completed run
verified 1,560,856 baseline bodies and 341,902 additions in 24m40s, with a
14,535,568 KiB maximum process resident set and no swap. It produced a private
candidate, not a published catalogue. The reconciler releases construction
state before its independent reread and no longer composes the same catalogue
twice before writing. These changes retain the complete byte and proof checks.

Cloudflare Workers documents 128 MB per isolate. Containers documents a
12 GiB maximum among its listed configurations; larger allocations require a
provider request. Neither is a direct destination for this measured local job.
Use Workers for bounded request handling and small jobs. Evaluate Queues and
Workflows for transport and waiting behind the existing scheduler, with R2 for
immutable bodies. Keep large qualification, native rendering and publication
checks on approved machines until a partitioned implementation passes the same
checks. No new cloud resource is activated by this placement decision.
[Workers limits](https://developers.cloudflare.com/workers/platform/limits/),
[Containers limits](https://developers.cloudflare.com/containers/platform/limits/)

Local parallel verification is under qualification. Threads were slower in
the tested samples. The final-code experiment over 46,538 files and
224,074,942 bytes had median wall times of 6.133s in process, 3.863s with
four workers and 3.896s with eight, including startup and shutdown. Aggregate
CPU times were 6.037s, 15.321s and 26.674s respectively. The existing cache and
concurrent host load were uncontrolled; this sample does not establish
full-catalogue speed. The explicit opt-in engine sends
bounded digest/size batches and explicit roots to workers, keeps payload bytes
out of results, preserves deterministic refusal order and retains serial
verification as the default until the complete path is qualified. Only
baseline/update body checks opt into processes. New-payload collection,
writing, final metadata/proof validation and the publisher remain serial.
The final metadata reread is not a second full payload verification pass.
Streaming or disk-backed operator metadata remains a separate scaling task.

### Separate product brands

AgentStudios is the owner's selected creative-focused offering on the
account-verified `agentstudios.si` domain. S-6.35.08 owns its independent
presentation and exact hostname qualification over these same backend
boundaries. Its setup is in progress, not part of the release 91 live-host
inventory below. The [owner decision](OWNER-DECISIONS.md#independent-offerings-and-agentstudios)
records the scope and replaces the earlier AgentMedia placeholder.

The owner's standing October 13 direction keeps `baltor.ai` as the combined
site for all three offerings, with separate branded domains as additional
customer acquisition channels. AgentFeeds covers maintained information and
decision guidance, AgentFoundry covers component building and reusable working
material, and AgentAFK covers local and cloud AFK execution. AgentAFK includes the proposed hosted
computer; AgentComputer is not a separate brand. The
[owner decisions](OWNER-DECISIONS.md#separate-product-brands-october-13-2026)
record the separate acquisition channels and existing prices, grants and
preview terms.

S-6.35.06 in the [roadmap](../roadmap/roadmap.yaml) owns implementation and
qualification. The owner confirms purchasing `agentfeeds.si` and `agentafk.si`
through Namecheap and selects `getagentfoundry.si` for AgentFoundry, replacing
the working name AgentKits. Engineering verified all three domains in the
registrar account. AgentFeeds launched in release 90. Release 91 serves
AgentFoundry on `getagentfoundry.si`, AgentAFK on `agentafk.si` and the
Don't be a meat proxy campaign on `dontbeameatproxy.si`, each with its `www`
hostname. All are live for public review. The new-site run passed every
functional assertion but retained four secondary browser-body accounting
errors; the release record preserves that instrumentation limit rather than
calling the strict aggregate successful.
Each presentation uses the shared backend without joining another brand's
navigation. Cloudflare owns DNS; these eight hosts serve directly from Fly
rather than the Baltor static Worker. A Baltor subdomain does not satisfy
the owner's direction.

AgentFoundry has component previews, public collection search, existing
account access and MCP setup. Its checkout return path remains unqualified.
AgentAFK exposes a browser-local Preview; hosted execution and learned queue
ranking remain unfinished. AgentAFK and the campaign refuse account and
provider-effect routes. The campaign leads to AgentFeeds, not another product
or backend. Baltor retains the combined offerings.
The [current deployment](MVP-CLIENT-SERVER.md#current-deployment) binds the
eighteen-host release checks and configuration-aware rollback.

### Proposed AgentBriefs decision-support composition

AgentBriefs is a selected name, not a registered service brand or a live
hostname. Its [owner decision](OWNER-DECISIONS.md#agentbriefs-executive-intelligence-proposal)
and S-6.35.09 in the [roadmap](../roadmap/roadmap.yaml) describe the proposed
executive presentation. The following map assigns future work to existing
owners; it does not claim that the complete customer workflow is implemented.

| Proposed stage | Existing owner to extend | Required output and boundary |
| --- | --- | --- |
| Company context | Managed records and tenant access | Versioned private goals, stack, projects and constraints; source access and synchronization permission remain explicit. |
| Source intake and research | AgentFeeds source contracts and managed research | Dated, attributable observations; quarantined newsletter content is not trusted instructions or public library material. |
| Opportunity assessment | Typed decision engines and evaluation rubrics | A versioned relevance assessment with uncertainty and source support, separate from experiment permission. |
| Proof experiment | Canonical Loop execution, task queue, model gateway and sandbox profiles | Approved task and baseline, scoped data and credentials, bounded resources and recorded attempts; no production effects inferred. |
| Evidence brief | Existing artifact, evaluation and acceptance boundaries | Source-backed strategic analysis or reproducible experimental results, with the evidence category visible. |
| Notification | Existing account access and permitted delivery boundaries | A deduplicated, threshold-qualified alert; relevance never grants consent to contact someone. |
| Decision Memory | Managed records, Run History and feedback | Linked decisions, corrections and later outcomes without overwriting original evidence or adding an intelligence layer. |

Each new functional edge needs a typed, versioned contract and conforming,
swappable engines through the existing engine-slot standard before execution.
Every executable graph vertex remains a Loop. The proposed executive team is
a composition of bounded steps, not another runtime or an unrestricted
autonomous operator. Read-only research, sandbox experiments, notifications
and production changes have separate authority. Importing a company plan
does not authorize any of them by itself.

The first customer proof should use one authorized company profile, one
decision family and a fixed evaluation population. Test both a useful alert
and a plausible but unsupported candidate that must be withheld. Preserve
all failures, and distinguish measured experiment results from realized
outcomes after a customer independently adopts a recommendation. Provider
plan usage, connector access and application identity remain separate;
the owner decision records the conditional OpenAI path and API-key fallback.

### Brand, product and access identities

Keep these identities separate:

| Identity | Owns | Does not grant |
| --- | --- | --- |
| Brand | Approved hostnames, design, copy, support presentation and public metadata | Product access or execution authority |
| Product | The useful customer outcome and its existing typed service contracts | An invented independent company |
| Plan | Price, included capabilities and stated limits | New provider or model spending authority |
| Tenant/account | Customer identity, private state, credentials and grants | Access to another customer's records |
| Experiment | Assignment, tested difference, observation window and result | Undisclosed tracking or a false claim about demand |

A first implementation should select an approved brand from the request
hostname and serve a brand-specific static export through the existing edge.
Fly retains authoritative identity, entitlements and billing until a separately
qualified migration. Shared product APIs and content identities stay unchanged.
Include the brand in relevant cache keys, export identity, OAuth return paths,
checkout configuration and support context. Refuse unknown hosts and unapproved
redirects. Brand presentation must never stand in for tenant authorization.

Unrelated domains cannot share an ordinary first-party cookie. Keep sessions
origin-bound and make any common sign-in an explicit, tested redirect flow.
Do not silently merge accounts, share private activity, duplicate charges or
change existing grants when a person visits another brand. A shared backend
also shares failure risks; measure and bound each brand's demand.

Cloudflare supports multiple Worker Custom Domains in zones the operator
controls. Billing needs a separate decision: Stripe requires separate accounts
for independently operating projects or businesses and warns that mismatched
public business details can confuse customers. One backend does not imply one
payment account is appropriate for every brand.
[Cloudflare Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/),
[Stripe account guidance](https://docs.stripe.com/get-started/account/multiple-accounts)

Brands can have different names and presentation while accurately identifying
their operator. Do not imply independent ownership, fabricate competitor
endorsements or report the same customer's activity as independent demand.
The FTC's guidance covers both express and implied advertising claims; a
footer cannot cure a misleading main claim. Existing approved privacy and
terms remain unchanged. New public legal commitments still need owner approval.
[FTC advertising guidance](https://www.ftc.gov/business-guidance/resources/advertising-faqs-guide-small-business)

For a presentation test, hold the offer, price, traffic source and eligibility
constant. Different products or audiences test different propositions, not only
branding. Measure a useful first outcome, repeat use, support burden and cost
per retained customer; page views alone do not qualify a brand. Acquisition
spend remains with the owner.

## 3. Database architecture

```text
State ownership
├── Public service records
│   ├── Accounts, grants, billing policy and usage
│   └── Catalogue releases, exact item versions and withdrawals
├── Immutable material
│   ├── Content-addressed component bodies
│   └── Versioned source evidence and candidate artifacts
├── Internal work
│   ├── CommunityStore and RecordOperationService
│   └── Existing reactive scheduler, leases and operation records
└── Customer state
    └── Customer-owned project files, context and model credentials
```

Use managed-record operations for managed collections. Search indexes and
public lists are derived views, not permission stores. Credentials stay in
their owning secret systems. A private observation does not become public
because its summary is indexed.

## 4. Query paths

The [supply and retrieval guide](CAPABILITY-SUPPLY-AND-RETRIEVAL.md) describes
the current `catalogue_search_index/v1` edge. Its selectable baseline and disk
engines use SQLite FTS5 and deterministic hash vectors, not learned semantic
embeddings. Host selection is explicit; an unavailable engine is refused.

```text
Customer question
  → typed request and authentication where required
  → eligible catalogue records and explicit filters
  → selected qualified search engine
  → small references, conditions and evidence
  → separately authorized exact-file materialization
```

Feeds currently include source collections, catalogue updates and downloadable
reading profiles. Maintained comparisons, hosted saved assignments and
personalized event delivery have their own roadmap gates. For decision feeds,
keep option/version, typed observation, workload, evidence, benchmark protocol
and comparison policy separate. There is no universal best rank.

## 5. Access paths

Discovery grants no execution authority. Customer model access stays with the
customer. An internal research subscription is not a customer entitlement or
permission to resell a provider operation.

Engine adapters validate typed inputs, allowed destinations, credential scope,
quotas and result contracts. Source permissions govern collection, retention,
reuse and publication separately. A source's code license does not necessarily
cover its media, trademarks or third-party datasets.

A supported MCP connection proves only its tested transport and contract.
The harness still decides whether to load information or execute an action.
Do not claim every Spawned Loop is an operating-system sandbox; use the exact
isolation guarantees of its qualified executor.

## 6. Runtime paths

A functional component has a fixed typed, versioned edge and one existing
engine slot. It can use a native implementation, a pinned upstream adapter or
another qualified engine without changing its callers. An adapter is not a
new runtime.

The [Practitioner guide](../components/practitioner/README.md) and kernel
handshake define required and optional steps. The name of a reference profile
does not imply a fixed number of steps in every current procedure. Solution
graphs, native frames and scene objects retain their existing owners.

Research follows the same boundaries:

```text
Source observation
  → prioritized research question
  → bounded follow-up investigation
  → existing-capability search
  → candidate method, component or decision record
  → qualification and independent review
  → approved publication
  → observed retrieval, use and outcome
```

Follow-up searches inherit the parent's remaining request, model, time and
byte allowances. A generated idea or trigger cannot widen them. The current
community harness has prompt-level search limits; those alone do not prove a
hard network cap. The existing reactive scheduler refuses unsupported cooldown
settings, and its series-specific priority policy must be selected explicitly.

## 7. Devtools architecture

The development package imports the production package, never the reverse.
Bootstrap checks can inspect structure before importing the runtime.
Repository assurance, contract conformance, native tests and browser checks
cover different failure classes. The
[working cycle](../context/TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle)
owns their release sequence.

## 8. Conformance commands

Run from the reviewed checkout with its supported environment:

```sh
PYTHONPATH=src python -m loop_engine --map
PYTHONPATH=src python -m loop_engine --conformance
PYTHONPATH=src python -m loop_engine --self-test
PYTHONPATH=src:tools python tools/regenerate_all.py --pristine
```

These checks do not establish a live provider call or deployed state.
Use the owning component's smallest checks first and preserve failed attempts.

## 9. Memory types

The current memory vocabulary is `working`, `episodic`, `semantic` and
`procedural`, defined in
[memory_type.py](../../src/loop_engine/memory/model/memory_type.py).
The four persistent intelligence layers remain Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Runtime Memory is temporary. Memory types, intelligence layers
and material families are different axes; User Feedback is not a fifth memory
type, and layers do not have a universal one-to-one memory-type mapping.

## 10. Current invariants

The [Constitution](CONSTITUTION.md), [terminology](../../terminology.yaml),
[machine-readable architecture](../../architecture.yaml) and
[functional component standard](FUNCTIONAL-COMPONENT-STANDARD.md) own the rules.
This map does not repeat their identifiers as another enforceable registry.

Keep implemented behavior, configured deployment and future candidates
distinct. Preserve exact source identity, versions and rights. Unknown evidence
stays unknown. Candidate volume, qualified material, served files and measured
customer benefit remain separate counts.
