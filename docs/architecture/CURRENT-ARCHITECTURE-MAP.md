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
the tested samples. A clean-spawn process experiment over 46,538 files and
224,074,942 bytes had median wall times of 4.140s with one process, 2.776s with
four and 2.894s with eight, including startup and shutdown. This small sample
does not establish full-catalogue speed. The proposed opt-in engine sends
bounded digest/size batches and explicit roots to workers, keeps payload bytes
out of results, preserves deterministic refusal order and retains serial
verification as the default until the complete path is qualified.

### Separate product brands: proposed, not deployed

The owner's October 11 proposal is to test distinct websites, beginning with
Agent Feeds, over the same services. S-6.35.06 in the
[roadmap](../roadmap/roadmap.yaml) owns this investigation. Domain control has
not been verified. Current hostnames select pages within one Baltor site map
and shared page shell; a display-name substitution is not a separate brand.

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
