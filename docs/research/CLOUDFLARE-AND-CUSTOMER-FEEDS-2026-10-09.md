# Cloudflare placement and customer feed customization

Kind: engineering decision and next-build record, October 9, 2026. Primary
provider documentation was checked for this review. Recommendations below are
engineering judgments; a provider feature is not a qualified Baltor engine.
The [roadmap](../roadmap/roadmap.yaml) remains the task queue and
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) owns authority.

## Decisions for this release

Ship the redesigned website and the customer reading-profile editor through
the existing Cloudflare export. Keep customer sign-in, billing and custom
search on their current qualified backends. Complete R2 delivery qualification
next. Develop shared source collection and event delivery on Cloudflare in
small, measurable steps.

The [current deployment record](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
already records nine product hostnames behind Cloudflare, a segmented catalogue,
1,560,856 distinct served files, custom SQLite search and Supabase identity.
The current bodies are mirrored across five R2 scopes; volume delivery is still
selected. These are recorded observations, not new live probes in this review.
The [October 5 design](../architecture/CLOUDFLARE-HOSTING-2026-10-05.md) remains
useful prior work, but its earlier resource sizes and credential blockers are
historical.

## Placement by responsibility

| Responsibility | Decision | Benefit and qualification boundary |
|---|---|---|
| Public website, documentation and curated feeds | Continue Workers Static Assets and the existing `web_page_delivery` engine | Public pages can stay available while the Python origin releases. Export and compare exact bytes, headers, canonical URLs and all hostnames. Static Assets is for the website: its paid limit is 100,000 files per Worker version, not ten million library files. [Limits](https://developers.cloudflare.com/workers/platform/limits/) |
| Library bodies, previews and large media | R2 through the existing `catalogue_body_store` engine | Storage separates from origin capacity; R2 has no egress charge. Access decisions, revocations, digest checks and usage completion remain with the service. Use immutable digests, private object access and an exact mirror/rollback record. [R2](https://developers.cloudflare.com/r2/how-r2-works/) |
| Public release/source metadata | D1 as a rebuildable projection when a measured read needs it | Indexed SQL supports bounded filters. A paid database is limited to 10 GB and serializes its queries, so a giant unsharded full-scan catalogue is unsuitable. Identity and billing authority do not move as a side effect. [D1 limits](https://developers.cloudflare.com/d1/platform/limits/) |
| Collectors and lightweight parsers | Bounded Workers adapters behind existing research source contracts | Shared collection can serve many interested customers. Streaming parsing must fit 128 MB and explicit CPU/request bounds; browser automation, native binaries and large transforms need a suitable worker environment. [Workers limits](https://developers.cloudflare.com/workers/platform/limits/) |
| Collection dispatch | Queues, with existing job identities and idempotent consumers | Separate bursts of source discovery from processing. Delivery is at least once; an acknowledgment is not evidence of exactly one provider effect. Reconcile unknown outcomes and use bounded batches. [Delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/) |
| Long research/release sequences | Workflows as a hosting engine for the existing workflow | Persist orchestration across waits and retries; record exact source/job identities. A Workflow step is infrastructure around governed work, not a new Loop runtime or a step for every file. Waiting does not consume CPU time, but steps and retained state are billed. [Workflows pricing](https://developers.cloudflare.com/workflows/reference/pricing/) |
| Shared source cursors, leases and rate budgets | Evaluate Durable Objects for scoped coordination | Use one explicit owner per source/account shard. Qualify fencing, idempotency and recovery before replacing current state. Request, duration and SQLite usage are separate cost dimensions. [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/) |
| Public cache | KV for immutable projections only | Eventual consistency can delay visible changes by 60 seconds or more. Revocation, token validity, quota reservation and current account authority need a stronger owner. [KV consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/) |
| Native search, indexing, media and evaluation tools | Retain Fly/container engines while comparing alternatives | The existing process has custom ranking and persistent files. Cloudflare Containers can run native code, but its local disk is ephemeral by default; moving the authoritative SQLite file there would change durability. [Container lifecycle](https://developers.cloudflare.com/containers/api/container-class/) |

Existing search experiments are a reason to compare carefully. On 30,757
entries and 118 queries per mode, D1 returned the same answers as the local
engine. Measured edge round-trip p95 was 261 ms lexical and 549.8 ms hybrid;
local computation p95 was 62.4 ms and 218.3 ms respectively. These compare
remote round trips with local computation, not two equal deployments.
The [lexical](../../artifacts/cloudflare-2026-10-05/d1-lexical.json) and
[hybrid](../../artifacts/cloudflare-2026-10-05/d1-hybrid.json) populations are
small and historical. Only 37 of the sampled queries had a relevant catalogue
item; the [in-corpus correction](../../artifacts/cloudflare-2026-10-05/judged-in-corpus.json)
reports hit-at-10 of 0.7027 and 0.7297. Exact parity does not establish adequate
retrieval quality or ten-million-file performance. Reuse this adapter and
measurement tool before introducing another search service.

## Customer sign-in and Cloudflare Access

Baltor currently uses Supabase for customer identity. Keep the tested
email-first sign-up, account mapping and session revocation for this release.
Cloudflare Access is useful immediately for staff tools and internal consoles.
Its Cloudflare identity provider authenticates Cloudflare accounts, and its
email PIN option admits users under Access policies. Those facilities do not
automatically provide Baltor's subscription mapping, account lifecycle or
per-agent permissions. [Cloudflare identity](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/cloudflare/),
[email PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/).

Access also offers Managed OAuth for CLIs and MCP. The provider explicitly
warns that enabling it changes `401` handling and should not wrap an application
already relying on its own OAuth challenge. Baltor has that existing server.
Evaluate a separate adapter against the same PKCE, resource, consent, grant,
refresh and revocation tests before replacing it. [Managed OAuth](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/).

If customer identity on Workers becomes worthwhile, evaluate the existing
open-source Better Auth project, whose database documentation lists a
community Cloudflare D1 dialect, before writing an identity system. Pin the
source and licence, preserve exact subject mappings, prove email ownership,
recovery, session revocation and rollback, and compare operating cost. This is
an evaluation candidate, not an installed or approved migration.
[Better Auth database adapters](https://better-auth.com/docs/adapters/other-relational-databases).

Turnstile is a possible abuse-control supplement, not an identity provider.
Its free plan includes unlimited challenges and up to 20 widgets. The current
privacy notice says every page script is first-party; adopting a browser
widget requires a concrete reviewed disclosure/CSP change. The present
failed-attempt limiter continues to work without that change.
[Turnstile plans](https://developers.cloudflare.com/turnstile/plans/).

## Cost gates for growth

Use measured GB, operations, CPU and source calls, not the count of files as a
cost forecast. Workers Paid starts at $5/month with 10 million requests and
30 million CPU milliseconds included. Direct static-asset requests are free;
a request invoking the Worker follows Worker pricing. R2 Standard lists
$0.015/GB-month, $4.50/million Class A operations and $0.36/million Class B
operations, with 10 GB-month, one million Class A and ten million Class B
included monthly. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[R2 pricing](https://developers.cloudflare.com/r2/pricing/).

An illustrative cold upload of ten million separate small objects costs
about $40.50 in Class A operations alone after a fully unused one-million
allowance. Ten million queue messages normally imply thirty million queue
operations, about $11.60 after the paid inclusion. Ten million Workflow steps
would be about $76 beyond the included 500,000, before compute and storage.
These are arithmetic scenarios, not the current bill. Retries, multipart
operations, other usage and billing rounding can increase them.
[Queue pricing](https://developers.cloudflare.com/queues/platform/pricing/),
[Workflow pricing](https://developers.cloudflare.com/workflows/reference/pricing/).

Batch queue and workflow work around bounded source jobs and release segments.
Investigate indexed immutable body packs only behind the existing body-store
edge, retaining each exact file digest and proving range retrieval, partial
failure and rollback. Do not change current object layout during the design
release. The canonical authority currently records $50/month infrastructure
and $10 setup; the older design quotes a different historical ceiling. Reconcile
the live bill and authority before an operation that would exceed the canonical
allowance. No spend or infrastructure mutation occurred in this review.

Cloudflare Workers Logs are enabled by default for newly created Workers and
can include request metadata. Configure logging deliberately; disable general
invocation logs for customer routes and retain only permitted operational
fields. A successful private profile export must not create a new activity log
by accident. [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/).

## Feed customization delivered and what follows

The current increment adds the `/feeds` browser editor, source inclusion and
exclusion, a requested client reading interval, exact downloads, and one shared
installed compiler for web and CLI. The directory is pinned before export;
selection changes invalidate old downloads. The source checks' age is shown
separately from unknown upstream article freshness. A saved file is not a
hosted subscription, an authenticated agent assignment or a running timer.

The first release needs no new credential. Two independent local agents can
receive different `profile.json` and `READING.md` files from the same public
directory. An agent label describes the intended reader; the customer's
harness enforces placement and access.

Next, build private saved profiles in the existing `RecordOperationService`
and Fly service store: owner-bound agents, opt-in read/write scopes, immutable
revisions, expected-version updates, revocation and bounded counts. Existing
OAuth metadata grants must not gain write permission. The approved October 1
privacy notice covers explicitly submitted content and revisions on Fly; the
specific uncovered change would be storing it at a new provider/location or
adding a broader successful-request log. Keep that distinction explicit.

Then maintain admitted shared events and let each profile select those events.
Every event needs source identity, observation/publication times, rights,
corrections/withdrawals, compatibility and partial-coverage status. Shared
collection avoids repeating one paid source request for every customer.
Per-profile cursors, deliveries, email opt-in and external destinations are
separate typed records. Internal research credentials and customer cloud-tool
credentials stay separate in the existing provider/credential registry.

## Ordered next changes

| Order | Work | Finish condition |
|---|---|---|
| 1 | Design/profile release | Exact main CI; guarded origin release; static export; all-host route checks; actual browser profile downloads match server hashes |
| 2 | R2 delivery canary | Ordinary customer exact bytes, wrong digest, revocation, refused-read usage, interrupted transfer and volume rollback all pass |
| 3 | Shared source collector canary | One permitted source job on Workers/Queues; recorded request budget, retry recovery, freshness and withheld private candidates |
| 4 | Authenticated saved profiles | Two accounts and two agents per account; isolated assignment reads/writes, stale revision refusal and immediate revocation |
| 5 | Personalized admitted events | One dated new event reaches exactly the selected agent; replay creates no second logical delivery; withdrawal is visible |
| 6 | Search placement comparison | Same current corpus, judged queries, authority filters, p50/p95, cost, restart and restore on both engines; adopt only a demonstrated benefit |
| 7 | Broader origin replacement | Existing state and identity conformance pass on the candidate; documented restore and rollback; provider disclosures reconciled |

Steps 2 through 7 are queued engineering work, not completed by the profile
editor or by this research. Root integration owns their roadmap scheduling.
