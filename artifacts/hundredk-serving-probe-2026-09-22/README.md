# Offline 100,000-row serving probe, September 22, 2026

This is a **synthetic metadata probe**, not a 100,000-package library, an approval
campaign, or a qualified SaaS run. It writes no candidate or body into the
active catalogue, contacts no service or model, and reads no customer body.
The source boundary was inspected at `a51ac96378ce63cd4504499ea865a22e78168fec`;
the relevant serving, retrieval, builder, Docker and workflow files were
unchanged when `main` advanced to `4795276e6edfda14db5ef3be0980f554405fc8bf`.

## Fixture and method

`probe.py` deterministically emits one manifest row for each numbered logical
item. Each row stands for **one distinct primary physical file**. Seven paths
rotate through `SKILL.md`, Python tool, `AGENTS.md`, `CODEX.md`, YAML agent,
JSON plugin and JSON protocol configuration. Each item has a 21-character
identity, a short purpose with one unique token, a synthetic 64-character
digest placeholder, `harness_local` family, 2,048 declared bytes, one
synthetic tenant grant, and an expressly synthetic approval reference. No
file at the body path exists, and the placeholder digest does not attest a
body. The fixture therefore does **not** cover a skill with scripts, assets
and references as one multi-file package.
The repository's recorded target is 100,000 distinct approved logical
packages, with unique eligible payload files counted separately. This fixture
happens to have one synthetic file row per synthetic package; it proves
neither count for an active release.

The manifest size uses the builder's indented JSON shape. The listing size
uses the unwrapped `provisioning_list/v2` result; the actual HTTP and protocol
wrappers add bytes. The grant size is one tenant's compact
`service_grants/v1` payload. These sizes are exact for this fixture; they are
not size estimates for real items. The streaming manifest calculation matched
normal `json.dumps` for a 10-row control. Search records reproduce the hosted
route's `StoreRecord` fields: identity, purpose, kind and source layer. Each
index run used a fresh Python process and one unique-token lexical query.
`fts5_only` is the existing SQLite FTS5 backend alone; `retriever` is the
current hosted `Retriever` constructor, which builds FTS5 **and** 512-element
Python hash vectors even for a lexical query. The 100,000-row `retriever` run
completed under a 3,072 MiB process address-space limit. RSS comes from Linux
`/proc/self/status`. The environment was x86_64, Python 3.10.20. Timings are
one local run each, with no concurrency, disk persistence, real grants, file
hashing, or relevance challenge set. They are diagnostic measurements, not
latency targets.

| Rows / primary files | Manifest bytes | Bare list bytes | One-tenant grant bytes | FTS5 build / query, seconds | FTS5 peak RSS | Current Retriever build / query, seconds | Retriever peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 1,220,844 | 733,280 | 472,650 | 0.0155 / 0.0003 | 22.4 MiB | 0.3522 / 0.0040 | 42.4 MiB |
| 10,000 | 12,207,292 | 7,331,579 | 4,725,799 | 0.1931 / 0.0005 | 37.7 MiB | 4.2161 / 0.1349 | 233.7 MiB |
| 100,000 | 122,071,567 | 73,314,429 | 47,257,224 | 1.8018 / 0.0007 | 180.3 MiB | 48.5747 / 0.7918 | 2,148.2 MiB |

Full machine-readable results are in `manifest-sizes.json`,
`payload-sizes.json`, and `fts5-{count}.json` / `retriever-{count}.json`.
The unique-token query placed its intended item first at every tier; this
establishes only fixture plumbing, not useful search relevance.

## Current serving path and hard limits

```text
Reviewed release in the image
├── One indented JSON manifest, maximum 2,000,000 bytes at host load
├── One approved row and body path per item; builder accepts .md source bodies
├── Full file stat and SHA-256 at host load; body later read as UTF-8 text
├── One stored grant-array record per tenant, replaced as a whole
└── Per request
    ├── list/discover scan every registered item without pagination
    ├── search calls full list and reconstructs a fresh Retriever
    ├── Retriever builds FTS5 and hash vectors before lexical search
    └── read rechecks exact grants and digest, then meters and returns one string
```

The checked-in release manifest holds 43 `skill` items in 63,671 bytes. The
synthetic manifest first crosses the loader's 2,000,000-byte limit at **1,639
rows** (2,000,872 bytes); 1,638 rows use 1,999,653 bytes. The limit is in
`service_runtime/http_entrypoint.py:_host_json` and is applied to both the
host file and manifest. The checked-in builder's `.md` gate and flattened
`bodies/<basename>` output are in `tools/build_host_catalogue_manifest.py`.
Its `build()` creates one `body_path` and one body per item. The host loader
hashes each file at startup and its reader calls `read_text(encoding="utf-8")`.
`ProvisioningServer._read` accepts only a string and returns it in one body
record. The HTTP download calls it in full and sends it as
`application/octet-stream` named `intelligence.txt`. These contracts cannot
faithfully package a native skill directory with scripts and assets or
deliver arbitrary binary harness files.

The default HTTP response ceiling is **262,144 bytes**. The synthetic bare
list first crosses it at **358 rows** (262,595 bytes); 357 rows use 261,864
bytes, leaving too little for the real response wrapper. The protocol tool
also checks its fully serialized answer against the same ceiling. Search is
limited to **50 returned hits**, but the route first calls an unpaged full
`list`; `ProvisioningServer._offered` scans all registered items. The search
route then constructs `Retriever(records)` anew. It rereads the entire
tenant grant record several times before and after search. These paths are in
`service_runtime/http.py:_search`, `service_runtime/provisioning.py`,
`service_runtime/runtime.py:grant_snapshot`, and
`core/provisioning_server.py:_offered`.

Other default HTTP limits are 65,536 request bytes, 16,384 inline body bytes,
64 MiB download bytes, eight concurrent operations, and a 30-second request
deadline (`service_runtime/http.py:ServiceHttpConfiguration`). The measured
100,000-row current index construction alone took 48.57 seconds and its peak
RSS was 2.10 GiB. The Fly profile declares one shared CPU and `memory =
"2gb"` (`fly.toml`). Thus even after lifting the manifest cap, this fixture's
per-request index would exceed the documented Machine memory and default
deadline before accounting for the web server, grants, SQLite, bodies, or
other tenants. The FTS5-only component measurement shows a plausible reusable
engine to qualify; its in-memory index was still rebuilt for the test and
its one exact-token query says nothing about relevance or concurrent latency.

The current release workflow source **does** contain an apply-packaged-grants
step (`.github/workflows/fly-pilot.yml`, lines 182–212). The older current
deployment page still says this action is manual after Fly release 12. The
source change alone does not establish that a newer release ran the workflow
or that live grants match it. The release image copies the whole catalogue
folder (`Dockerfile.service`), and `apply_host_grants` replaces each tenant's
whole stored grant array. At 100,000 rows this fixture's one-tenant payload is
47.3 million bytes; no SQLite transaction, deployment, cold start or image
build was measured here.

## Existing roadmap gates this evidence informs

| Existing item | Engineering consequence | Proof required before calling 100,000 packages served |
|---|---|---|
| **S-6.40** library growth | Count approved distinct logical packages, their exact physical files, rendered variants, candidates and withdrawn files separately. Extend the typed, versioned item contract to preserve relative path, format, bytes, digest, dependency and effect for every component of a multi-file package. Keep independent exact-byte review and file-level rights evidence. | Reconcile 100,000 **real approved logical packages** and the separate unique payload-file count against active release and retrievable exact revisions; no synthetic row or generated candidate counts. Run native format and digest checks for scripts, assets, configs and instruction files. |
| **S-6.62** catalogue releases and settings | Replace the single giant startup JSON and whole per-tenant grant array with a versioned release manifest or indexed projection, immutable component references, an auditable delta and a policy that grants eligible approved items while retaining exact revocation and old-release refusal. Paginate metadata enumeration and apply account settings as narrowing filters. | Add/withdraw/rollback one batch across two tenants; prove release counts, grants and exact digests reconcile. A withdrawn or changed component must be refused at read even after search or when pinned to an obsolete release. Keep a negative control for a dropped grant or unapproved addition. |
| **S-6.32** hosted search engine slot | Reuse the existing FTS5 backend or another qualified indexed engine behind the fixed typed edge. Build and persist a rebuildable projection once per release rather than reconstructing the full list and vector table on each query. Push authorization filters into candidate generation; apply the measured purpose policy and relevance floor. | Held-out task phrasings and no-answer queries across all supported file kinds, with recall, rank, weak extras, effect eligibility, filtered latency and memory reported. A poor match must say so. Establish a cold/reused/concurrent latency ceiling before launch. |
| **D-05** cloud records, files and retrieval | Keep one authoritative catalogue transaction contract and immutable exact-byte objects, with indexes rebuildable from it. Qualify PostgreSQL and private object storage only with read-set guards, revocation, checksum, cutover and rollback semantics preserved. Stream or chunk large and non-text package components through a typed delivery contract. | D-05-T01 through T05: equivalent atomic transactions, private exact-object fetch, revoke between search and delivery, projection rebuild and migration reconciliation, and permission-scoped retrieval quality. Include slow clients, partial transfer, tampering, cache isolation, startup and multi-tenant load. |

An end-to-end acceptance gate still requires offered, fetched, placed, loaded,
used and independently verified facts for a native harness step (D-06). A
100,000-row metadata or FTS5 test cannot substitute for that customer journey.

## Reproduction

From the repository root, with the existing environment:

```bash
PYTHONPATH=src .venv/bin/python artifacts/hundredk-serving-probe-2026-09-22/probe.py manifest
PYTHONPATH=src .venv/bin/python artifacts/hundredk-serving-probe-2026-09-22/probe.py payloads
PYTHONPATH=src .venv/bin/python artifacts/hundredk-serving-probe-2026-09-22/probe.py search --count 100000 --engine fts5_only
PYTHONPATH=src .venv/bin/python artifacts/hundredk-serving-probe-2026-09-22/probe.py search --count 100000 --engine retriever --address-space-limit-mb 3072
```

Run each search command separately. The last command requires enough memory
for a roughly 2.15 GiB peak RSS; its address-space limit confines the process
but does not make it suitable for the present 2 GB service Machine.
