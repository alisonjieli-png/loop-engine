# Baltor server research artifact

Kind: component-specific research companion for Claude Code, September 23,
2026. This describes the hosted service boundary and the evidence needed
to scale it. It is not a replacement for the [roadmap](../roadmap/roadmap.yaml),
the [current deployment record](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
or the service contracts. Read the [100,000-package synthesis](SAAS-AND-HUNDRED-THOUSAND-EXECUTION-GATES-2026-09-22.md)
for the full launch sequence.

## Runtime relationship

    Operational runtime type
    └── Loop
        ├── Operational relationship
        │   ├── Starting
        │   ├── Spawned by
        │   ├── Queried by
        │   ├── Retrieved by
        │   └── Connected from
        ├── Role: Practitioner, Intelligence, or Solution
        ├── Versioned role profile and purpose categories
        ├── Run mode: deterministic, hybrid, or non-deterministic
        ├── Step profile; typed input and output; loop and exit conditions
        ├── Graph relationships; budget, permissions, and effect policy
        ├── Model settings when the mode permits a model
        └── Run History records

The hosted service is a set of records, adapters and edges used by classified
Loops, not another executable graph vertex. The
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
governs how a discrete cognitive or act step Loop node uses this service.
The customer's harness and model run under the customer's control.

## Current evidence

The [live read-only audit](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
and [release 15 record](../../artifacts/architecture-audit-2026-09-19/pilot-release-13.json)
show one Fly Machine, two gigabytes of memory, a one-gigabyte volume, SQLite
durable records, eight healthy public hostnames, personal-key and protocol
paths for operator-provisioned accounts, a working invitation list, and 43
packaged Markdown guidance bodies. The release's catalogue check reported
34 offered and nine withheld for the pilot owner. The public capabilities
record still reports registration and email sign-up closed, checkout and
portal off. Health and protocol checks do not prove a customer finished a
step. All 43 packaged bodies have ordinary Markdown filenames and no Agent
Skills frontmatter; native skill pickup is unproved.

The service already negotiates the supported protocol revisions
2025-11-25 and 2026-07-28 at the relevant runtime boundary. New components
must retain explicit version, capability, schema and qualified-adapter
handshakes. A failing handshake cannot silently downgrade authority or
reinterpret a record. The [pre-launch version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
permits removal of old unpublished shapes while preserving old evidence
bytes.

## Server responsibilities

    Hosted service
    ├── Account and entitlement
    │   └── Sign-in binding, key scope, expiry, revocation and usage
    ├── Catalogue authority
    │   └── Approved exact package versions, rights and withdrawal
    ├── Search projection
    │   └── Small eligible references, relevance floor and bounded pages
    ├── Delivery
    │   └── Reauthorize, verify digest and supply a complete native package
    └── Operations
        └── Health, release record, per-host checks and rollback

The server must never infer file, network, secret, model or spending
permission from a filename, prose, review score or search hit. Search,
selection, materialization, execution and acceptance are distinct stages.
A small reference is safe to offer only after eligibility and tenant
filters. An exact body is read after another current grant, rights,
withdrawal and digest check. Credentials for the customer's model and
local protocol servers stay in the [client-side scoped broker design](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md),
not in the hosted intelligence body.

## The measured scale failure and proposed repair

The [offline synthetic probe](../../artifacts/hundredk-serving-probe-2026-09-22/README.md)
used one fake primary file per row. At 100,000 rows its manifest was
122,071,567 bytes against a 2,000,000-byte host-loader limit; an unpaged
bare list was 73,314,429 bytes against a 262,144-byte response ceiling; and
one tenant's grant array was 47,257,224 bytes. The current Retriever built
a fresh full-text and 512-element hash-vector index for a lexical request
in 48.57 seconds, peaking at 2.10 gibibytes. That exceeds the documented
30-second request deadline and two-gigabyte Machine memory before other
service work. A full-text-only component built in 1.80 seconds in this
fixture, but one exact-token query is not a relevance or concurrency test.

S-6.62 already owns a content-addressed body store, versioned release
record, guarded active pointer, hot-swapped index and grants that follow the
release with sparse explicit denials. S-6.32 owns search behind a fixed
engine edge and a measured relevance floor. D-05 owns durable records,
private exact-byte files and rebuildable projections. These are proposed
repairs, not deployed behavior. A new release should stage complete trees,
verify every file digest, build a projection beside the active one, then
advance the guarded pointer. A direct read must refuse a withdrawn or
replaced file even when a stale search card or older image names it.
Metadata enumeration needs bounded pages and stable cursors. Complete
multi-file delivery must preserve relative paths and prevent partial
activation; non-text files cannot be forced through one UTF-8 string body.

## Server acceptance gates

| Gate | Discriminating evidence |
|---|---|
| Invited customer path | An invited person signs in, issues a personal key, searches, retrieves exact approved bytes, sees usage, loads selected material in a supported native client and produces an independently accepted step. Offered, fetched, loaded, used and verified are separate records. |
| Release and rollback | A committed revision passes continuous integration, deploys by image digest, applies grants, records both active and rollback images, and runs website, catalogue, service and protocol checks on every hostname. Removing the grant step fails the catalogue check. |
| 100,000-package staging | Two tenants with different grants; 100,000 active approved package records; bounded enumeration; held-out relevant and no-answer queries; complete package delivery; revoke during search and download; withdrawal that survives image and pointer rollback; cold, reused and concurrent memory and latency measurements. Synthetic rows are only a failing baseline. |
| Paid service | Registration, recovery, checkout, signed event to entitlement, portal, cancellation, data export/deletion and support form one checked journey. Session creation alone is insufficient. Owner-approved terms precede paid access. |

The [roadmap](../roadmap/roadmap.yaml) owns these gates through D-17, D-18,
D-05, S-6.32, S-6.35, S-6.38, S-6.40 and S-6.62. The [records index](../RECORDS-INDEX.md)
lists the dated verification reports. No 100,000-package active release or
fully functioning paid customer journey has been observed.
