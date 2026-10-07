# Cloudflare as Baltor's cloud: target architecture, measurements and migration

October 7 reading note: the byte-preserved [original notes](../../artifacts/cloudflare-2026-10-05/hosting-notes-original.txt)
hold the historical measurements. This rendering only disambiguates two
headings and adds this note. Its payment-method and R2 credential blockers
are resolved; its 25 GB volume and catalogue population are historical.
Use the [current deployment](MVP-CLIENT-SERVER.md#current-deployment) and
[active delivery plan](../roadmap/DELIVERY-SEQUENCE.md) for present state and
acceptance. D1 remains a planned engine, not production search.

Kind: dated design record, October 5 and 6, 2026 (United States Eastern; the
measurements ran from 23:30 to 00:15 UTC, the cost update at 02:30 UTC). It
answers the owner's questions, records what was built and measured on
Cloudflare's free plan, gives the target architecture with Fly.io optional,
the cost against today's Fly bill at 100,000, 1,000,000 and 10,000,000 files
under the owner's $100 a month ceiling, and the order to adopt each part.
The [roadmap](../roadmap/roadmap.yaml) stays the task authority. This record
grants no deployment, spending or publication authority; the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
does.

## The answer in one minute

Baltor still runs on one Fly Machine: shared-cpu-2x with 4 GB and a 25 GB
volume, $29.15 a month by Fly's own price calculator, plus $0.02 for every GB
it sends. Cloudflare does not shrink that bill by itself, because it pays for
one always-on Python process, and that process costs about the same anywhere
($29.24 a month as a Cloudflare Container). What Cloudflare takes away is the
cost that grows with Baltor: the bigger Machine the catalogue would need, the
bandwidth, and the outage on every deploy.

- **First, at no cost:** switch the live service to the disk-backed catalogue
  that is now on `main`. It keeps the Machine at 4 GB to a million files and
  beyond, where the in-memory catalogue needs the 8 GB Machine ($70.27 a month
  in Fly's table) as soon as the next 121,771 packages are published.
- **Then Cloudflare, in this order:** the website (pages stay up through every
  deploy), file downloads from R2 (no bandwidth charge), then search and
  listing at the edge. All three were built tonight; the first and last were
  measured on free prototypes.
- **What it costs:** $34.15 a month at tonight's 370,793 files and still
  $34.15 at 1,000,000 files, against $79.22 for the Fly-only path at
  1,000,000 files (with the traffic assumed in the cost section). Once the
  release train builds indexes off the Machine, the Machine can drop to 2 GB
  and the total to $22.14: a quarter less than tonight's Fly bill at nearly
  three times tonight's size, with no bandwidth charge and no outage for
  readers. At 10,000,000 files the design costs $63.49, inside the owner's
  $100 ceiling.
- **The one owner step:** add a payment method to the Cloudflare account. It
  turns on R2 and Workers Paid ($5 a month); usage inside the included
  amounts costs nothing more.

## The request

The owner, October 5, 2026: "how are we with cloudflare adjustments and
improvements to improve our architecture and using cloudflare for our own
cloud hosting". Later the same evening: "Remember we don't have to still use
fly.io, we can also use cloudflare offerings, lets think about the
architecture improvements, and adjustments, and serverless/scalable front
end, backend, retreival, and other components, we can also increase budgets
as required, but I think cloudflare offerings will allow us to save a
significant amount or at least be more flexible." Later still: "Are we still
only using fly.io, I thought there was significant potential savings with
cloudflare offerings", and at about 22:40 EDT: "we can increase our budget up
to $100 per month, but we should really look at Cloudflare as an option to
reduce costs".

The same evening release 65 kept every hostname down for 85 seconds while the
one Fly Machine built its in-memory catalogue view of 39,710 items before it
listened (22:55:05 to 22:56:30 UTC). That wait grows with the catalogue. The
local measurement of a 92,923-item view is 1.65 GB of extra memory, 1.9 GB
during a hot swap. By the end of the evening the live service served release
`76e970a9…`: 92,923 packages, 370,793 distinct files and 840.5 MB of distinct
file bytes. Release 66 tried to move the Machine to 8 GB and failed, because
shared-cpu-2x cannot exceed 4,096 MiB; nothing changed on the Machine, and
`main` restored the 4 GB allocation. The integrator's commit `3f471466`
brought the disk-backed `catalogue_search_index` slot and segmented releases
to `main`; this record's commits sit on it. The measurements below used the
30,757-item release of that morning, the newest base bundle on the
workstation.

## The answer in one tree

```text
Baltor, target (Fly optional)                               status tonight
├── Front end: the website as static files at the edge      built, measured on workers.dev (phase 1)
│   ├── web_page_delivery slot, engine static_content_network (static_site_export, edge/site_edge_worker.js)
│   ├── every page and asset, byte for byte and header for header the service's own answer
│   └── pages keep serving while the origin restarts; everything else gets the service's unavailable answer
├── Edge proxy: Cloudflare in front of the origin           built: client address mode (off), pass-through
│   └── edge_proxy slot, engine content_network_proxy; failed-attempt limits read CF-Connecting-IP
│       only from Cloudflare's pinned ranges (service_request_limits/v2)
├── Retrieval at the edge                                   built, measured on the 30,757-item release (phase 2)
│   ├── catalogue_search_index slot, engine (d) d1_edge_index: D1 FTS5 + KV hash-vector columns + a Worker
│   ├── same answers as the in-memory engine on every measured request
│   └── D1 bills rows scanned: an OR query scans every match, so cost grows with the library (measured)
├── File bodies in R2                                       built and tested against a real S3 server; needs the owner
│   └── catalogue_body_store slot, engine r2_object_storage; volume stays the default
├── Edge read API for signed-in accounts                    designed (phase 4)
├── Release train on Workflows and Queues                   designed (phase 5)
├── Python origin                                           stays on one small Fly Machine; Containers optional (phase 6)
│   └── accounts, OAuth, the protocol endpoint, metering, billing, publication: the service store's writers
└── Search past a million items                             designed: compute shards or an edge impact index,
                                                            Vectorize for learned embeddings (phase 7)
```

## For the lead, in short

- Two phases are built and measured. The edge website served all 79 exported
  pages exactly, from the edge, while its origin could not be reached; API
  requests got the service's own `service_unavailable` record with
  `Retry-After: 30`. Edge retrieval returned the same answers as the in-memory
  engine on 236 judged requests over the 30,757-item release.
- The series is rebased on `3f471466`. Engine (d), `d1_edge_index`, is
  registered in the integrated `catalogue_search_index` slot as a planned
  engine (kind `edge_database_index`): no host can select it, and the slot's
  kit (53 checks), the D1 kit (23), the site kit (15) and the body store kit
  (36) pass on the rebased tree.
- One owner action: add a payment method to the Cloudflare account. It enables
  R2 (bodies) and the Workers Paid plan ($5 a month), which production needs
  for its CPU and request limits. Nothing else here needs the owner; no DNS
  record or zone setting was changed, and no production DNS or cutover change
  happens until both sessions agree in the coordination file and no deploy or
  publication is running.
- Edge search is free while the library is small or searches are few and costly
  when both grow: D1 bills every row a query scans, and Baltor's OR queries
  scan every matching document (0.9 rows a package a search, measured). At
  1,000,000 files it is free up to about 110,000 searches a month; at
  10,000,000 files lexical search belongs on compute (a second origin with the
  disk index) or an edge impact index, with the edge caching answers.
- Recommended order: the disk-backed catalogue on the live host (no cost), the
  payment method, the website at the edge, bodies in R2, search and listing at
  the edge, then the release train and a 2 GB origin. The cost section gives
  each step's monthly total.

## What each Cloudflare product does for Baltor

Prices and limits were read on October 5, 2026 from the official pages, with
the "last updated" date each page showed.

| Product | What it would do for Baltor | Free plan | Paid price | Limits that matter | Source |
|---|---|---|---|---|---|
| Workers | Edge code: the website router, edge read API, search, signed loads | 100,000 requests a day, 10 ms CPU a request | $5 a month: 10 M requests and 30 M CPU ms included, then $0.30 a million requests and $0.02 a million CPU ms | 128 MB memory, 1 s startup, 50 subrequests (Free) or 10,000 (Paid) | [pricing](https://developers.cloudflare.com/workers/platform/pricing/) (Oct 2), [limits](https://developers.cloudflare.com/workers/platform/limits/) (Sep 5) |
| Workers static assets | The website's pages and files | requests to assets free and unlimited | same | 20,000 files a version (Free), 100,000 (Paid); 25 MiB a file; a `run_worker_first` path is a Worker request | [billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) (Apr 23), [limits](https://developers.cloudflare.com/workers/platform/limits/) |
| D1 | One release's search index, filters and public hit fields; replicated account summaries | 5 M rows read and 100,000 rows written a day, 5 GB | 25 B rows read and 50 M written a month included, then $0.001 a million read, $1.00 a million written; 5 GB, then $0.75 a GB-month | 500 MB (Free) or 10 GB (Paid) a database; 100,000-byte SQL statements; 100 bound parameters; rows read counts every row scanned | [pricing](https://developers.cloudflare.com/d1/platform/pricing/) (Apr 21), [limits](https://developers.cloudflare.com/d1/platform/limits/) (Apr 21) |
| KV | Hash-vector columns, export manifests, cached capability and policy snapshots | 100,000 reads and 1,000 writes a day, 1 GB | 10 M reads, 1 M writes included, then $0.50 and $5.00 a million; 1 GB, then $0.50 a GB-month | 25 MiB a value; eventually consistent (a new value can take up to a minute to reach every location) | [pricing](https://developers.cloudflare.com/workers/platform/pricing/) |
| R2 | File bodies, release segments, index snapshots, large media | needs a payment method on file | $0.015 a GB-month; $4.50 a million writes, $0.36 a million reads; 10 GB-month, 1 M writes, 10 M reads free a month; no egress charge | 1 write a second to one key; presigned links 1 s to 7 days; an API token only after R2 is purchased | [pricing](https://developers.cloudflare.com/r2/pricing/) (Oct 1), [limits](https://developers.cloudflare.com/r2/platform/limits/) (Jun 8), [S3 API](https://developers.cloudflare.com/r2/api/s3/api/) (Jul 31), [presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/) (Aug 22), [tokens](https://developers.cloudflare.com/r2/api/tokens/) (Oct 1) |
| Vectorize | The semantic stage with learned embeddings | 5 M stored, 30 M queried dimensions a month | 10 M stored and 50 M queried dimensions included, then $0.05 a 100 M stored and $0.01 a million queried | 20 M vectors an index, 1,536 dimensions, top 100 without values | [pricing](https://developers.cloudflare.com/vectorize/platform/pricing/) (Apr 21), [limits](https://developers.cloudflare.com/vectorize/platform/limits/) (Aug 5) |
| Durable Objects | Per-shard or per-account state with its own SQLite | SQLite only; 100,000 requests a day | 1 M requests, 400,000 GB-s included; SQLite rows billed as D1; 5 GB, then $0.20 a GB-month | 10 GB an object; 1,000 requests a second an object | [pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/) (Sep 30), [limits](https://developers.cloudflare.com/durable-objects/platform/limits/) (Jun 1) |
| Queues | Fan-out of the release train: body uploads, index builds, cache purges | 10,000 operations a day | 1 M operations a month, then $0.40 a million (about 3 a message) | | [pricing](https://developers.cloudflare.com/queues/platform/pricing/) (Apr 21) |
| Workflows | The daily release train as a durable sequence with retries | 3,000 steps a day | Workers prices plus 500,000 steps a month, then $0.80 a 100,000; 1 GB-month storage, then $0.20 | state kept 30 days (Paid) | [pricing](https://developers.cloudflare.com/workflows/reference/pricing/) (Sep 21) |
| Containers | The Python service without Fly | none | Workers Paid; $0.0000025 a GiB-second memory and $0.00000007 a GB-second disk (provisioned), $0.000020 a vCPU-second (active use only); 25 GiB-hours, 375 vCPU-minutes, 200 GB-hours included; egress $0.025 a GB after 1 TB (North America, Europe) | disks are ephemeral; billing stops when the instance sleeps | [pricing](https://developers.cloudflare.com/containers/pricing/) (Oct 5) |
| CDN proxy and cache | Cloudflare in front of every hostname | 10 cache rules; 2-hour minimum edge TTL; purge by URL, hostname, tag and prefix | | 512 MB a cached file; HTML and JSON are not cached by default; a proxied request that waits more than 125 s for the origin ends in error 524 | [cache rules](https://developers.cloudflare.com/cache/how-to/cache-rules/) (Aug 14), [TTL](https://developers.cloudflare.com/cache/how-to/edge-browser-cache-ttl/) (Aug 14), [purge](https://developers.cloudflare.com/cache/how-to/purge-cache/) (Sep 29), [default behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/) (Sep 14), [error 524](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/) (Jul 23) |

Two terms constrain the design. The
[service-specific terms](https://www.cloudflare.com/service-specific-terms-application-services/)
(updated September 28, 2026) let Cloudflare limit a Free, Pro or Business zone
that serves "video or a disproportionate percentage of pictures, audio files,
or other large files" without its paid services, so large media go through R2
or Stream, never the plain cache. And a Python library's default user agent
meets Cloudflare's browser integrity check (error 1010, observed on
workers.dev tonight), so every Baltor client names itself
(`baltor-edge-client/<version>`).

Fly's prices come from its [pricing page](https://docs.fly.io/about/pricing),
read again at 02:26 UTC on October 6 (22:26 EDT). Its calculator's own
constants for iad, $8.465e-7 a shared vCPU-second and $2.316e-6 a GB-second
beyond the 0.25 GB a shared vCPU includes, give shared-cpu-2x 4 GB $25.40,
shared-cpu-4x 4 GB $26.79 and shared-cpu-4x 8 GB $50.80 for 30 days; a volume
costs $0.15 a GB-month; outbound data costs $0.02 a GB in North America and
Europe. The deploy owner read $70.27 for 8 GB in Fly's table at 22:25 EDT, and
the owner's decision record uses that figure, so the cost tables below use it
for the 8 GB Machine; with the calculator's $50.80 every conclusion stands.
Tonight's bill is $25.40 for the Machine and $3.75 for the 25 GB volume,
$29.15 a month, plus egress.

## Phase 1, built and measured: the website at the edge

### What was built

| Part | File | What it does |
|---|---|---|
| Export | `src/loop_engine/core/service_runtime/static_site_export.py` | Renders every page and asset the service sends an anonymous reader, with the service's own functions (`served_asset`, the model directory, Public Good, Dot, red team and status pages), stores each once by SHA-256, and writes `site_edge_manifest/v1` with the exact header sets the service sends |
| Edge Worker | `src/loop_engine/core/service_runtime/edge/site_edge_worker.js` | Serves the export from Workers static assets, or from KV in a prototype, and passes every other request to the origin; answers the service's own unavailable page or refusal record when the origin cannot answer |
| Kit | `src/loop_engine/core/service_runtime/static_site_checks.py` | 15 checks with the Worker's own source under Node in front of the real service on loopback |
| Operator tool | `tools/cloudflare_site_edge.py` | Export with the live header values and served population, signed load, measurement, outage measurement |

A page differs between Baltor's nine hostnames only by one meta tag that
`web_pages.with_page_head` writes last before `</head>` on a hostname whose
root is not `/`. The export proves this for every page and every hostname root
and stores one copy; the Worker writes the same line in the same place. What
stays at the origin, with the reason: the library page (its bytes depend on
the active catalogue; the release train exports it per release), the OAuth
consent page and sign-in callbacks (they sit beside the routes they call),
every API and the protocol endpoint. The page view counter
(`public_links.viewed`) runs at the origin only, so pages served at the edge
are not counted until the counter moves to an edge-side store; that is a
known gap, not a silent change.

### Measured

The prototype holds the export of this checkout (145 files, 25.96 MB, export
`614cfb51…`) in a KV namespace and passes reads to `baltor-pilot.fly.dev` in
read-only mode. The 2,352 model directory detail pages were left out of the
prototype because a free KV namespace takes 1,000 writes a day; the full
export is 2,498 files, 75.1 MB, rendered in 13 s, and fits static assets.
Latency was measured from one workstation in the eastern United States, on
kept-alive connections, three rounds of every HTML page (`site-edge.json`,
`site-edge-outage.json` in the records folder):

| Measure | Edge (workers.dev) | Fly origin (iad) |
|---|---|---|
| Pages, rounds, statuses | 79, 3, all 200 | 79, 3, all 200 |
| Bodies equal to the export | 237 of 237 | (another release's bytes) |
| Time to first byte, p50 / p95 | 73.6 / 155.4 ms | 63.3 / 138.0 ms |
| Whole page, p50 / p95 | 101.1 / 199.1 ms | 95.2 / 201.1 ms |
| Network round trip to the edge (`/v1/ping`) | 58 to 62 ms p50 | |
| Origin cannot be reached (`*.invalid`) | 79 of 79 pages exact; p50 99 ms | without the edge, every hostname is down |
| `/api/v1/capabilities`, `/api/v1/health` with the origin down | 503 `service_unavailable`, `Retry-After: 30` | connection failure |
| `/library` in a browser with the origin down | 503 with the service's unavailable page | connection failure |

From a workstation near the origin's region the edge and the origin are
equally fast; the gains are availability during releases, no egress charge
for pages (Fly charges $0.02 a GB), and nearer service for readers far from
Virginia, which one workstation cannot measure. The kit proves the exactness
locally: every exported page, asset and hostname root equals the real
service's answer, byte for byte and in every browser-facing header, and
removed-guard controls catch a missing root rule, missing page headers, a
removed read-only guard and a removed unavailable answer.

One platform behavior changed the Worker: Cloudflare does not raise an
exception in a Worker when the origin's name cannot be resolved; `fetch()`
returns Cloudflare's own page with status 530. The Worker now treats 520 to
530, like the origin proxy's 502 to 504, as the origin being unavailable.

## Phase 2, built and measured: retrieval at the edge

### Retrieval implementation

Engine (d) of the scale agent's `catalogue_search_index` slot (edge
`catalogue_search_index/v1`):

| Part | File | What it does |
|---|---|---|
| Export and adapter | `src/loop_engine/core/service_runtime/catalogue_d1_index.py` | Builds one release's D1 index from the same functions the in-memory engine uses (`entry_text`, `search_text`, `_TokenBuckets`); `D1EdgeSearchIndex` speaks the edge (`eligible`, `rank`, `stats`, `policy`, `schema`) and reads `catalogue_search_index_pools/v1` strictly |
| Worker | `src/loop_engine/core/service_runtime/edge/catalogue_search_worker.js` | `POST /v1/rank` (the edge's query and pools contracts), `POST /api/v1/retrieval` (`service_retrieval_request/v2` to `service_retrieval_result/v1` for one enabled account with default library settings), `GET /v1/index`, a signed vector upload |
| Kit | `src/loop_engine/core/service_runtime/catalogue_d1_index_checks.py` | 23 checks with the Worker's own source under Node's SQLite |
| Operator tool | `tools/cloudflare_d1_search.py` | Signing keys, export, vector upload, measurement |

The index lives in a D1 database: a contentless FTS5 table over the service's
own index text (rowid is the position), the public fields of each hit,
bucketed keyword postings and chunked range postings for filters, and the
build record last. The 512 float32 hash-vector columns live in KV, one value a
dimension, because D1 returns a BLOB to a Worker as an array of numbers, which
costs CPU in proportion to its bytes. Requests are signed with Ed25519 keys
whose public halves the Worker holds, so no shared secret is copied into a
host file, a prompt or a transcript. Every vocabulary, limit, label and
refusal sentence the retrieval route uses comes from a profile Python writes
from the service's own constants.

The kit runs the Worker's source under Node's SQLite: pools equal the
in-memory engine's bit for bit on a published store release with filters and
on all 354 judged requests in both modes; the retrieval route answers and
refuses exactly as the service does for one account; removed-guard controls
catch float32 sums, missing lower-casing, round-half-up, a removed signature
check, a missing vector column scored as zero and an unchecked vector upload.

### The live index

| Measure | Value |
|---|---|
| Release | `e817bec2…` (the six Public Good additions of October 5), 30,757 items: 42 verified, 30,715 community |
| Export | 1,001 statements, 87.3 MB of SQL, largest statement 89,999 bytes; 63.0 MB of vectors |
| D1 import | 8.2 s of SQL, 61,630 rows written, 97.9 MB database (3.2 KB an item), primary ENAM (EWR) |
| Vector upload | 512 KV writes |

### Retrieval measurements

Every third judged request of `examples/30_search_quality` (118 requests),
each through the Worker's retrieval route and through `authorized_hits` on the
in-memory engine over the same entries (`d1-lexical.json`, `d1-hybrid.json`):

| Measure | Lexical | Hybrid |
|---|---|---|
| Requests, failures | 118, 0 | 118, 0 |
| Answers differing from the in-memory engine | 0 | 0 |
| Edge round trip, p50 / p95 | 170.0 / 261.0 ms | 408.0 / 549.8 ms |
| Worker time, p50 / p95 | 75 / 95 ms | 233 / 312 ms |
| D1 time, p50 / p95 | 75 / 95 ms | 86 / 117 ms |
| KV time (vector columns), p50 / p95 | none | 152 / 197 ms |
| Rows read a request, p50 / p95 | 28,160 / 40,046 | 28,385 / 40,301 |
| In-memory engine on this workstation, p50 / p95 | 27.1 / 62.4 ms | 140.6 / 218.3 ms |

Judged recall is the in-memory engine's, because the answers are the same.
Only 42 of the 123 judged items are in the live catalogue; over the 107
judged requests whose relevant item is in it, the full judged set gives mean
reciprocal rank 0.6269 and hits within ten 0.6636 lexical, 0.6392 and 0.6916
hybrid (`judged-in-corpus.json`).

Through the Python adapter (`D1EdgeSearchIndex`, 11 requests in each mode and
3 with filters, `d1-rank-pools.json`) every pool had the same identities in
the same order, and filtered pools were identical. Unfiltered lexical scores
were not bit-identical: D1's FTS5 computes some bm25 values one or two units
in the last place away from SQLite 3.50.4 and 3.46.1 (largest relative
difference 4.7e-16; two of five sampled scores differ, while D1's own `printf`
confirms the values it returns are the values it computed). Order is decided
inside SQLite and fusion reads ranks, not scores, so answers are unchanged;
but engine (d) cannot claim the bit-exactness the disk engine claims, and its
registration says so.

### What it costs, and the measured way to cut it

D1 bills the rows a query scans. Baltor's lexical query is an OR of up to
twelve quoted terms ranked by bm25, so it scans every matching document: 0.9
rows a package a search, p50, on the measured release. That is free while the
library is small or searches are few, and dominant when both grow (packages
hold 3.99 files each on the live service):

| Packages (files) | Rows read a search | D1 cost of a million searches a month (beyond the 25 B rows included) |
|---|---|---|
| 100,000 (about 400,000) | 90,000 | $65 |
| 250,600 (1,000,000) | 225,500 | $201 |
| 1,000,000 (about 4,000,000) | 900,000 | $875 |
| 2,506,000 (10,000,000) | 2,255,000 | $2,230 |

Sharding by catalogue segment does not change the total: every shard scans its
own matches. Durable Object SQLite bills rows the same way. A local experiment
on the same release (`prune-experiment.json`) left out each query's terms
that appear in more than a share of the documents:

| Terms kept | Matches scanned a query | Judged requests | Mean reciprocal rank (bm25 order only) | Hits within ten |
|---|---|---|---|---|
| all | 13,154 | 107 | 0.3655 | 0.4766 |
| document frequency at most 20 % | 4,244 | 107 | 0.3682 | 0.4673 |
| at most 10 % | 2,777 | 107 | 0.3689 | 0.4673 |
| at most 5 % | 1,822 | 107 | 0.3689 | 0.4766 |

At 10 % the scan falls by 79 % with no measurable loss on this judged set,
which puts a million searches a month at 100,000 packages inside the included
rows and cuts the cost at 1,000,000 packages to about $165. It is a ranking change, so it is
measured, not adopted: it needs the full judged comparison through the
service's tier order and fusion, and a larger judged set, before any engine
serves it.

## The target architecture

### Front end

The website is static files at the edge (phase 1). In production the export
deploys as Workers static assets from continuous integration with the
release; pages on `baltor.ai` are served as plain assets, which cost nothing
per request, with a generated `_headers` file carrying the service's header
sets (not built: the prototype runs the Worker for every path). The Worker
runs for the hostnames whose root is another page and for the paths that go to
the origin. The library page and the served counts are re-exported by the
release train with each catalogue release.

### Edge proxy and the client address

Cloudflare in front of the origin moves the client address: the origin's
proxy then reports Cloudflare's address in `Fly-Client-IP`, and every visitor
would share one failed-attempt count. `service_request_limits/v2` (proxy
fork, `forwarding_proxy.py`, 73 request-limit checks, 19 of them new) reads
`CF-Connecting-IP` only when the connecting address is inside Cloudflare's
published ranges, pinned with their source digests on October 5 at 22:50 UTC
(set `cloudflare-2026-10-05`), and ignores a forged header from anywhere else.
Version 1 stays the default and behaves as before. Cloudflare's
[HTTP headers page](https://developers.cloudflare.com/fundamentals/reference/http-headers/)
(updated May 5, 2026) says a Worker's request to a non-Cloudflare origin
carries the real client address and only `x-real-ip` can be changed; a range
check still does not prove a request came through Baltor's own zone, which
Authenticated Origin Pulls would, a follow-up.

### Backend: what moves to the edge and what needs Python

| Route | Where | Why |
|---|---|---|
| Pages and assets | edge (phase 1) | static per release |
| `GET /.well-known/oauth-*`, `GET /api/v1/billing/plans` | edge (phase 4) | static per release and policy |
| `GET /api/v1/capabilities`, `GET /api/v1/health` | edge with an origin-written snapshot in KV (phase 4) | per release, plus the origin's own health |
| `GET /api/v1/public-good`, `/api/v1/public-good/files` | edge from the release's D1 index and the policy snapshot (phase 4) | public collection metadata |
| `POST /api/v1/retrieval` for signed-in accounts | edge (phase 4) once an account summary (enabled, entitlement, library setting, denials) is replicated by the origin through Queues and the token is verified at the edge | search is metadata only and not metered; the profile route of phase 2 is the anonymous half |
| `POST /api/v1/provisioning` list and manifest | edge after phase 4, same replicated summary | metadata |
| `POST /api/v1/provisioning` read, `POST /api/v1/download` | Python origin | metered exactly once against the service store; bodies may then go out as short presigned R2 links |
| Account routes (`/api/v1/account/*`), sign-up, recovery | Python origin | Supabase administration, Resend email, the service store, durable request identities |
| `/authorize`, `/token`, `/register`, `/revoke`, consent | Python origin | the OAuth server writes grants and tokens |
| `/mcp` | Python origin | sessions, tool calls that meter, the Python protocol library |
| `POST /api/v1/billing/webhook`, checkout, portal | Python origin | Stripe signatures, idempotent billing records |
| Staff routes, usage, waitlist, feedback | Python origin | service store writers |
| Publication (`publish-catalogue`, `index-catalogue`) | Python, run by the release train | bundle verification, segments, index builds |

### Retrieval

Up to about 300,000 items: lexical at the edge in D1 (one database a release,
3.2 KB an item, inside 10 GB), with the document-frequency cut once it passes
its judged comparison; exact hash vectors from KV only while a query's
columns stay small (about 100,000 items, 14 MB a hybrid query). Past that,
lexical search runs on compute: the scale agent's disk index on the origin
Machine, or on shard Machines or Containers by catalogue segment, with the
edge caching answers by release and normalized request. The semantic stage
moves to Vectorize with learned embeddings (384 dimensions; 20 M vectors an
index), a new ranking that needs the judged comparison and the owner's
authorization for embedding model calls, which tonight's task did not have;
hash vectors are not a fit for an approximate index (the scale agent measured
recall of 0.33 to 0.50 with USearch on them). The Cloudflare-native answer to
row billing is an impact index (engine e): postings ordered by score in R2,
read by a Worker with block-max WAND, which returns the exact bm25 top k while
reading only the postings that can change it, billed in CPU milliseconds
rather than rows. It is designed, not built.

### Storage

R2 holds file bodies (the R2 fork's `r2_object_storage` engine behind
`catalogue_body_store/v1`: 36 kit checks, 6 of 6 against Versity S3 Gateway
v1.8.0, a resumable mirror of 1,200 bodies in 3.7 s with eight workers),
release segments and index snapshots. The volume keeps the service store and
the disk index. Presigned links (1 s to 7 days) deliver large files without
Fly egress; they are bearer links, so a withdrawal waits for expiry unless the
checking proxy serves the file.

### Pipelines

The daily release train becomes a Workflow: collect admitted candidates,
build and verify the bundle (a Python step on the origin or a Container),
upload new bodies to R2 (a Queue fans out, one message a file, about 3
operations each), publish the release, build the D1 index and the vector
columns, export and deploy the website, warm caches, run the live checks. Each
step is retried by the Workflow and keeps its result, so a failure resumes
rather than repeats. At a few thousand new files a day this stays inside the
included steps, operations and R2 writes.

### Identity, billing and email

Supabase stays the identity provider; the edge verifies its JSON Web Tokens
with the published keys for read paths (phase 4). Stripe webhooks stay at the
origin, which keeps the signature check and the idempotent billing records;
Stripe retries for three days, so a release restart loses nothing. Resend
stays the sender for account email. DNS is already on Cloudflare; proxying a
hostname is the switch of phase 1 and the lead's decision.

## Cost against today's Fly bill

The library's shape, measured on the live service tonight (release
`76e970a9…`): 92,923 packages, 370,793 distinct files, 840.5 MB of distinct
file bytes, so 3.99 files a package and 2,267 bytes a file. Assumed traffic a
month, stated so it can be scaled: 1,000,000 page views (159 KB each, the mean
of the exported pages: 160 GB), 100,000 searches and 100 GB of file
downloads. On Fly that traffic costs $5.20 a month in egress; on Cloudflare
$0. All three columns stay under the owner's $100 a month ceiling except where
marked.

| Files (packages) | Today on Fly: shared-cpu-2x 4 GB, 25 GB volume, in-memory catalogue | Fly scaled up as the catalogue grows | Cloudflare target: disk-backed origin and the edge |
|---|---|---|---|
| 100,000 (25,000) | $34.35 | $34.35 (no change needed) | $34.15, then $22.14 |
| 370,793 (92,923, tonight) | $34.35; every deploy is an outage while the view builds | $34.35 now; the next 121,771 packages need the 8 GB Machine: $70.27 + $3.75 + $5.20 = $79.22 | $34.15, then $22.14 |
| 1,000,000 (250,600) | does not fit: the view needs about 6 GB at a hot swap, and shared-cpu-2x stops at 4 GB (release 66) | shared-cpu-4x 8 GB: $79.22 | $34.15, then $22.14 |
| 10,000,000 (2,506,000) | does not fit | does not fit any shared Machine (about 45 GB of view) | $63.49 |

The Cloudflare target, item by item at 1,000,000 files: the Fly origin
(shared-cpu-2x 4 GB, the disk-backed catalogue) $25.40 and its 25 GB volume
$3.75; Workers Paid $5.00, with pages served from static assets for nothing
and search, listing and the router inside the 10 million included requests;
R2 $0, because 2.27 GB of bodies sit inside the free 10 GB; D1 $0, because
100,000 searches at 225,000 rows each read 22.5 of the 25 billion included
rows and the index holds about 0.8 GB; egress $0. Total $34.15. "Then
$22.14": once the release train builds indexes and exports off the Machine,
the origin needs no room for a build and can drop to shared-cpu-2x 2 GB
($13.39); measure its memory with the disk-backed view first. At
10,000,000 files a D1 search would read 2.25 million rows ($200 a month at
100,000 searches), so search moves to compute: a second Fly origin with its
own copy of the disk index, two times $29.15, plus Workers $5 and R2 $0.19
for 22.7 GB of bodies: $63.49.

What moves the numbers: D1 search at 1,000,000 files is free up to about
110,000 searches a month and then costs $2.25 for each further 10,000; with the
document-frequency cut measured above (not adopted) it is free up to about
520,000 and then $0.47 for each 10,000. Fly egress grows by $20.48 a TB of
traffic; Cloudflare's stays $0. A Cloudflare Container in place of the Fly
origin costs about the same (standard-1, half a vCPU and 4 GiB: $29.24 at 10 %
CPU) and about $8 as a basic instance (a quarter vCPU, 1 GiB), which needs the
service store moved off the volume first (phase 6, not built).

### The cheapest arrangement for 1,000,000 files with no deploy outage

The Cloudflare target column: one Fly origin (shared-cpu-2x 4 GB with the
disk-backed catalogue and its 25 GB volume) behind Cloudflare, with the
website from Workers static assets, file bodies in R2, and search and listing
from D1 at the edge. It costs $34.15 a month, and $22.14 once the release
train builds indexes off the Machine. While the origin deploys, the website,
search and listing keep answering from the edge; signed downloads and account
changes wait for the origin's restart, which the disk-backed catalogue
shortens from minutes to seconds (its index opens in 0.16 s, measured
locally). By comparison, the Fly-only path serves 1,000,000 files only on the
8 GB Machine ($79.22) and keeps the outage on every deploy, and Fly with the
disk-backed catalogue alone serves them for $34.35 with a short outage on each
deploy.

### Order of adoption

| Step | What | Who | Monthly total after it (assumed traffic) | Undo |
|---|---|---|---|---|
| 1 | Select the disk-backed catalogue on the live host | deploy owner; no new cost | $34.35, and the 8 GB Machine ($79.22) is never needed | restore the host file |
| 2 | Payment method on the Cloudflare account | owner | unchanged until used | remove it |
| 3 | Client address mode v2 on the host, then the website at the edge, one hostname first (phase 1) | engineering, with both sessions' agreement in the coordination file and no deploy running | $34.15 | unproxy the hostname |
| 4 | Bodies in R2 (phase 3) | engineering | $34.15 | restore the host file; the volume keeps every body |
| 5 | Search and listing at the edge (phases 2 and 4) | engineering, after the document-frequency cut's judged comparison | $34.15 at up to about 110,000 searches a month | route back to the origin |
| 6 | Release train on Workflows and Queues; origin to 2 GB after measuring (phase 5) | engineering | $22.14 | run the current tools; restore the size |
| 7 | Past a few million files: a second origin for search, or engine (e) (phase 7) | engineering | $63.49 at 10,000,000 files | keep one origin |

## Migration

Every phase keeps the existing contracts and engine slots, and each is undone
by the step in its last column.

| Phase | What | Slot and engine | Status | Needs | Undo |
|---|---|---|---|---|---|
| 1 | Website at the edge | `web_page_delivery` / `static_content_network`; `edge_proxy` / `content_network_proxy` | built, measured | client address mode v2 on the host first; Workers Paid for production limits | unproxy the hostnames (DNS only), or unbind the Worker route |
| 2 | Retrieval at the edge for one release | `catalogue_search_index` / `edge_database_index` (planned, registered in the slot) | built, measured | the document-frequency cut judged | no host selects it |
| 3 | Bodies in R2 | `catalogue_body_store` / `private_object_storage` | built, tested | the owner's payment method | restore the host file; the volume still holds every body |
| 4 | Edge read API for signed-in accounts | `catalogue_search_index`, `request_limit_state` (shared store), a replicated account summary through the `record_store` slot | designed | phases 1 to 3 | route back to the origin |
| 5 | Release train on Workflows and Queues | `release_executor` | designed | Workers Paid | run the current tools by hand |
| 6 | Python origin on Containers | `compute_host` / `container_service`; service store on a durable `record_store` engine (D1 or Durable Object SQLite) | designed, optional | a store engine and its conformance kit | keep deploying the Fly image |
| 7 | Search past a few million files | a second origin with the disk index, or engine (e); Vectorize in `retrieval_vector_stage` | designed | owner authorization for embedding calls | host keeps one origin |

## Steps for the lead

1. **Merge.** The series is rebased on `3f471466` and changes no file the
   integration owns beyond additive lines: engine (d) in
   `catalogue_index_engines.ENGINES` (planned), the `edge_database_index` kind
   and two existing checks in the slot record, and the scale kit's
   engine-order check. Regenerate the generated views after any further rebase
   (`tools/regenerate_all.py`); the conformance manifest regenerates unchanged
   and every conformance gate passes.
2. **Step 1 of the order**, by the deploy owner: select the disk-backed
   catalogue on the live host, as `CATALOGUE-AT-SCALE-2026-10-05.md` describes.
   It is the change that keeps the Machine at 4 GB and shortens every deploy.
3. **Client address mode, before any proxying.** Release an image with the
   proxy commits, back up `/data/host.json`, switch `http.request_limits` to
   `service_request_limits/v2` with the `forwarding_proxy` block, restart, run
   the checks the proxy fork listed. It changes nothing until a hostname is
   proxied.
4. **Phase 1.** With Workers Paid on the account and both sessions' agreement
   in the coordination file: deploy `edge/site_edge_worker.js` with the export
   as static assets from CI (a Cloudflare API token with Workers Scripts Edit,
   stored as a repository secret), `ORIGIN` an origin hostname that is not
   proxied, `ORIGIN_MODE` `all`; route `www.baltor.ai` first, proxy it, run
   the live checks on every hostname, then the rest. Undo: DNS only.
5. **Phase 3**, the day R2 exists: the R2 fork's steps (private bucket
   `baltor-catalogue-bodies`, a token scoped to it, Fly secrets, mirror, host
   record, live checks; undo by restoring the host file).
6. **Phase 2 in production** waits for the judged comparison of the
   document-frequency cut through the service's fusion, and for phase 4's
   account summary if signed-in search is to run at the edge.

## Cloudflare resources created tonight (free plan, no charge)

| Resource | Name | Identifier | Holds |
|---|---|---|---|
| workers.dev subdomain | `baltor-ai` | | |
| D1 database | `baltor-catalogue-search` | `b3e9b148-630c-4538-a2f9-26aebb314819` | the 30,757-item index, 97.9 MB, ENAM |
| KV namespace | `baltor-catalogue-search-vectors` | `ca557f80392b466a9db0d39315660381` | 512 vector columns, 63 MB |
| KV namespace | `baltor-web-edge-site` | `a5b3c81bc0b74edaa30ec89cfb2650ce` | the website export without model detail pages, 146 values |
| Worker | `baltor-catalogue-search` | `https://baltor-catalogue-search.baltor-ai.workers.dev` | signed requests only, except `/v1/ping` |
| Worker | `baltor-web-edge` | `https://baltor-web-edge.baltor-ai.workers.dev` | read-only in front of `baltor-pilot.fly.dev`, marked noindex; its load route was switched off after the load |
| Worker | `baltor-web-edge-outage` | `https://baltor-web-edge-outage.baltor-ai.workers.dev` | the same with an origin that cannot be resolved |

The signing keys' private halves stay outside the repository on the
workstation that made them (`search` key `9fed7d5b9cf3be51`, `admin` key
`bc9b96a23619ed4b`). Deleting any of these resources needs the owner's word,
by the standing rule; they cost nothing while they stay.

## Records

`artifacts/cloudflare-2026-10-05/` holds the measurement records named above.

## Limits of this record

- **One workstation.** Latency was measured from one place near the origin's
  region; the edge's advantage for readers elsewhere is not measured.
- **Free plan.** The prototypes ran with Free limits (10 ms CPU a request);
  production numbers on Workers Paid may differ.
- **The judged set is small.** 42 of its 123 items are in the live catalogue,
  and the document-frequency cut was scored on bm25 order alone.
- **Not built:** the `_headers` export, the edge read API, the release train,
  the store engine for Containers, engine (e), the Vectorize stage, page view
  counting at the edge, Authenticated Origin Pulls.
- **Costs are list prices** read on October 5 and 6, 2026, with the traffic
  assumed above; the measured rows-read rate is from one release whose items
  share common words.
