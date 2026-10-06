# Catalogue at scale: segmented releases and disk-backed search

Kind: dated architecture record. October 5, 2026. This integrates the saved
catalogue work into the current source. The [roadmap](../roadmap/roadmap.yaml)
owns delivery and [AGENTS.md](../../AGENTS.md#commit-push-and-release-authority)
owns deployment and spending authority. The earlier unfinished design and
measurement files remain preserved in their original worktree and the private
integration archive.

## Scope and classification

The existing service catalogue owns identity, versions, approval, access,
withdrawal and bodies. A search index is a rebuildable projection of that
catalogue. The change adds a selectable index implementation and a segmented
release format through those existing owners.

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

The index engines and operator commands remain internal adapters. They add no
runtime, account authority, intelligence layer or approval path.

## Release and serving changes

| Boundary | Change | Preserved contract |
|---|---|---|
| Catalogue publication | `catalogue_release/v2` names content-addressed segments of sorted identity/version pairs. | Exact item versions, content digests, durable withdrawals and atomic pointer changes. |
| Transfer | `catalogue_release_bundle/v2` carries segments, item records and missing bodies. | Publisher/service format negotiation occurs before upload. |
| Search | `catalogue_search_index/v1` selects an in-memory or SQLite disk index. | The existing retrieval request, authorization, ranking and response. |
| Host configuration | `service_catalogue_source/v2` names `search_engine` and `index_root`. | Version 1 keeps its existing in-memory behavior. Unsupported engines refuse startup. |
| Index preparation | `index-catalogue` prepares an index before a service restart. | The old view serves while a later index is built and checked. |

The `sqlite_disk_index` engine stores descriptors and full-text data in SQLite,
vectors in memory-mapped files, and filter postings beside them. It reads item
records on demand through a bounded cache. The `in_memory_view_index` engine
remains available. `lance_object_store_index` remains a planned prototype and
cannot be selected by a host.

A fresh disk index preserves the in-memory engine's candidate pools. Both now
use `CATALOGUE_RANKING_POLICY`. Integration found that the saved disk code used
the generic two-times candidate pool while current catalogue search used ten
times. The comparison failed on 337 judged hybrid queries despite identical
pools when passed the same explicit size. The shared default repairs that
disagreement; an explicit caller policy remains supported.

A small subsequent release can use an overlay. Its vector scoring is exact;
its lexical scores use the base corpus statistics. Larger deltas trigger a
full rebuild. The test suite retains separate exactness checks for fresh
indexes and a declared relevance tolerance for overlays.

## Bounds and publication checks

Segments have canonical boundaries and immutable digests. Reordering segments,
altering a stored segment, restoring a withdrawn version, changing a proof or
using an unsupported release format is refused by the owning checks.

The operator verifies uploaded bodies, segments and item records by separate
object kind. Readback uses counts and sorted-name digests per hash prefix,
then lists only a prefix that differs. This preserves the bounded readback
repair already on main and extends it to segmented releases. A file under
`segments` cannot satisfy a missing file under `items`, even with the same
digest. The original combined listing failed that regression case.

Index builds share one lock. A refresher keeps serving its current view while
another process owns the build. Partial indexes are not installed. Old index
files are rebuildable caches; the retention code keeps active and recent
releases, including the previous view during the swap window. Catalogue item
records and body-store contents have their own retention rules.

## Evidence and limits

The saved measurements cover synthetic collections from 100,000 to ten million
items on a shared workstation. They establish bounded index-memory behavior
for the tested configurations. They do not establish equivalent Fly latency
or a corresponding population of usable library files.

One saved full-path run at 100,000 items measured an initial disk-index build
of 232.95 seconds, a prepared-view open of 0.31 seconds, hybrid search at
216.3 milliseconds p95 over 40 requests, and a 110-item update publication of
31.02 seconds followed by a 2.6-second view change. Its discover and full-list
operations each took about a minute. These results predate the integration
repair to the shared ranking default and require fresh measurement on the
actual deployed catalogue.

The integrated owning tests exercise the judged query set, exact payload
delivery, Public Good projection, one-item grant lookup, withdrawal, concurrent
builds and both publisher/service version pairings. Whole-library listing and
discovery still perform work proportional to catalogue size. Faster aggregate
counts and paged discovery remain follow-up work.

## Deployment sequence and recovery

1. Deploy the tested image while keeping the current catalogue configuration.
   The image includes the `catalogue-index` dependency extra.
2. Verify live free space and preserve the host configuration with its owner
   and permissions. Prepare a separate configuration naming
   `service_catalogue_source/v2`, `sqlite_disk_index`, and a service-owned index
   directory. Retain every existing access, body-store and refresh setting.
3. Run `loop-engine service index-catalogue --config CONFIG` as the service
   user against that separate configuration. Retain its result and exact
   release identity. The current service continues serving.
4. Validate the prepared configuration as the service user, install it through
   the existing configuration procedure, restart, and check search, delivery,
   Public Good access, readiness and every supported hostname.
5. Publish a segmented release only after format negotiation and a successful
   preservation/reconciliation check. Retain the previous release and a
   compatible rollback image.

The first version 2 release raises the catalogue state to version 3. An older
image that cannot read that state refuses startup. Image rollback therefore
requires an image supporting state version 3. Before that migration, the
previous image remains eligible. The in-memory engine can still read supported
releases, subject to its measured memory requirement.

The running Fly Machine has two shared CPUs and 4096 MiB. Deployment
`37393965173` refused an 8192 MiB request. The source configuration restores
4096 MiB so deployment matches the observed supported allocation. Larger
capacity and spending beyond the standing allowance require their own evidence
and authority.
