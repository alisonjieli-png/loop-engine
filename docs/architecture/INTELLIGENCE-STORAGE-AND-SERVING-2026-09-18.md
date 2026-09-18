# Intelligence storage and serving: variations, measurements, and the decision

Date: 2026-09-18. Owner direction the same day: intelligence is stored and
served through one store contract, never by editing text files; packaged
JSONL and YAML ship as the default and are read and written through DuckDB
or an equivalent with full create, read, update, and delete by tool or
Python call; a server database serves wide rollouts; search characteristics
live in the database with a key that points at a file, an object store, or
an installed package; and every variation is analyzed and measured before
one is chosen. This record is roadmap step S-2.9.

## What exists today

```text
Intelligence access today
├── catalog/: one CatalogStore contract (get, query, stream, put with precondition,
│   export, import_bundle, health) with a capability handshake per adapter
│   ├── stores/in_memory: reference adapter, one process lifetime
│   ├── stores/package_jsonl: read-only shards shipped inside the package
│   ├── stores/sqlite_store: writable local file, precondition writes
│   ├── stores/duckdb_store and duckdb_files: writable local file, files as tables
│   └── composite: one logical view over several stores, refuses identity conflicts
├── core/record_operations: managed notes through an exact effect plan and approval
├── core/store_serve.SolverStore: the string bank, read from JSONL, appended to an
│   organization overlay file directly
├── strings/*.py: question forms, personas, fragments, and templates authored in code
├── data/*.yaml: architecture, terminology, catalogs, and profiles as packaged files
└── memory/storage: the four-memory reference store with versions per record
```

The contract the owner asked for already exists for catalog records. Three
things do not: the string bank and the code-authored forms are outside it;
nothing refuses a runtime write to an intelligence file; and no adapter
carries search characteristics separately from bodies.

## Variations

| Variation | Where bodies live | Where search characteristics live | Offline demo | Wide rollout | Write path |
|---|---|---|---|---|---|
| V1 files only | JSONL and YAML in the package | none; full scans | yes | no | text edits (the state to leave) |
| V2 DuckDB over packaged files | JSONL in the package, read as tables | DuckDB tables and indexes built at install or first use | yes | small teams | store call; the file is never edited by a run |
| V3 SQLite local file | rows in one file | same file, indexed columns | yes | single host | store call with a precondition |
| V4 server database with vectors | rows, or references to files | indexed columns and vector columns | no | yes | store call over a connection |
| V5 analytics warehouse | references and large tables | columnar tables | no | yes, batch analysis | bulk load |
| V6 package references | Python package resources | any of V2 to V4 | yes | yes | the package is versioned; the database holds the reference |
| V7 sidecar of characteristics | files, object store, or package | V2 to V4 | yes | yes | the body is immutable; the sidecar is the write path |

V6 and V7 are not alternatives to V2 to V4; they say what the database
holds. The decision below combines them.

## Complexity and flexibility

| Property | V1 | V2 | V3 | V4 | V6 plus V7 |
|---|---|---|---|---|---|
| Get by identity | linear scan | index | index | index | index on the reference |
| Attribute query | linear scan | pushdown when typed, else scan | pushdown on scalar columns only | pushdown, JSON operators | pushdown on the sidecar |
| Write cost | rewrite a file | row insert | row insert | row insert | insert a small row |
| Concurrency | none | one writer per file | one writer per file | many | many on the sidecar; bodies immutable |
| Size on disk | the text | text plus tables | rows | rows | small rows plus the packaged bodies |
| Offline install | yes | yes | yes | no | yes for packaged bodies |
| Maintenance | edits drift | schema and regeneration | schema | schema and operations | reference format and package versions |

## Measurement

The script `storage_bench.py` (kept with the session evidence) builds a
seeded population of 20,000 records with four layers, five artifact kinds,
eight namespaces, a `topic` attribute drawn from fifty values, tags, and a
forty-word payload, then measures each adapter as it exists today on one
host. Every number is a single run; the direction, not the digit, is the
finding.

| Adapter | Put 20,000 | Get 1,000 by identity | 20 attribute queries (about 401 hits each) | 20 namespace queries, limit 100 | Export | Bytes on disk |
|---|---|---|---|---|---|---|
| in-memory | 0.29 s | 0.015 s | 0.81 s | 0.043 s | 0.33 s | 0 |
| package JSONL (read-only) | 0.16 s to write the shard | 42.8 s | 2.48 s | 0.11 s | 0.14 s | 11.98 MB |
| SQLite | 1.35 s | 0.017 s | 3.61 s | 0.052 s | 0.49 s | 11.47 MB |
| DuckDB | 80.6 s | 0.46 s | 4.25 s | 0.15 s | 0.53 s | 13.97 MB |

Findings:

- The packaged JSONL adapter scans the shard for every get: 1,000 gets took
  42.8 seconds. It is fine for a demo of a few hundred records and wrong as
  a serving path. This is the cost of V1 in numbers.
- SQLite gets by identity in 17 microseconds each but answers attribute
  queries by filtering JSON in Python after a scalar predicate: 3.6 seconds
  for twenty queries. The attributes need indexed columns or a sidecar.
- The DuckDB adapter inserts one row per statement: 80.6 seconds for 20,000
  rows. Batched inserts or an appender are required before it is the default
  writer; its reads are adequate and its files-as-tables path is the natural
  V2.
- No adapter carries embeddings or a separate characteristics table today, so
  hybrid retrieval cannot be measured yet.

## Decision

Adopt V2 as the default with V6 and V7 as the record shape, and V4 as the
rollout target behind the same contract:

1. Packaged intelligence ships as JSONL and YAML inside the package and is
   addressed by a package reference of the form
   `loop_engine.data.<collection>#<record_id>`. A run never edits those files.
2. A DuckDB catalog built from the packaged files at install or first use is
   the default read and write path for a demo and a self-hosted install.
   Writes go to an organization overlay through the store contract with a
   precondition, exactly as `SQLiteRecordStore.put` does now. The DuckDB
   adapter gains batched writes before it becomes that default.
3. Every record carries its search characteristics (facets, digests,
   optional embeddings) in indexed columns beside a body reference. A body
   larger than a declared limit stays in a file, an object store, or a
   package, and only its reference and digest enter the database.
4. A server database with vector columns serves a hosted rollout through
   the same `CatalogStore` contract; the composite catalog already refuses
   identity conflicts across stores, which is what a migration needs.
5. The string bank and the question forms load through a store adapter, so
   they become records with identities, versions, and namespaces instead of
   code and appended lines.
6. A conformance scan refuses runtime code that opens an intelligence file
   for writing outside the declared adapters, and a settings record names
   the default store per deployment profile (demo, self-hosted, hosted).
7. Every write is a typed operation (create, read, update, delete, revise,
   rollback) that a harness performs through a tool call or a Python call;
   the managed record service's exact effect plan and approval remain the
   authority for host-configured collections.

Steps S-2.10 and S-2.11 in the roadmap implement points 2 to 7. The
versioning module added on 2026-09-18 already keeps every previous version
inside the same store, so rollback needs no second system.

## What this decision does not claim

It does not claim that DuckDB is the only local engine, that any server
database has been measured, or that hybrid retrieval works today. The
measured table covers four adapters on one host with one population; a
rollout decision needs the same table on the target database with the real
population.
