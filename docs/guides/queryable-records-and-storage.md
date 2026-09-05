# Queryable records and storage

Loop Engine already has `CatalogStore` and `IntelligenceQuery` as a typed
file/database boundary. The managed-record tool uses that boundary for
revisioned notes. This is an incremental implementation, not a migration of
every JSON file, Markdown document, log, or database.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by,
    │                 Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role and step profiles
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Typed inputs, outputs, loop condition, and exit condition
    ├── Budget, permissions, and effects
    └── Run History

Internal record mechanics used by Loops
├── Typed queries and host scope
│   ├── Read-only canonical JSONL rows
│   ├── Optional DuckDB JSONL query adapter
│   ├── SQLite records
│   └── Future qualified server adapters
├── Managed mutations
│   ├── Schema and exact effect approval
│   ├── Immutable revision artifact
│   └── Atomic expected-version update of the current reference
└── Distinct authorities
    ├── Git-controlled contracts and documentation
    ├── Canonical Run History and exact artifacts
    └── Rebuildable analytical and search projections
```

## Authority determines the write path

| Information | Authority | Write rule |
|---|---|---|
| Constitution, schemas, reviewed configuration | Git files | Reviewed source change |
| Shipped intelligence | Versioned package sources | Read-only during normal execution |
| Managed notes | Current database reference plus immutable revisions | Typed approved create/update/retire |
| Run History | Existing Run History owner | New events or runs, never note CRUD |
| Exact source, code, datasets and models | Artifact store | Digest-bound artifacts |
| Search and analytical indexes | Declared projection | Rebuild from authority |
| Shared production records | Future qualified server adapter | Explicit transaction and namespace policy |

A large reviewed YAML file can be appropriate. A small file rewritten by
several workers without concurrency checks can be unsafe. SQL access alone
does not establish authority, transactional updates, or safe deletion.

## Current query contract

The SDK accepts `IntelligenceQuery`, not arbitrary SQL. All filters apply
before pagination. Supported filters cover layers, source collections,
artifact kinds, lifecycle, namespaces, and attribute `equals`/`contains`.
Unknown predicate operators fail closed. Stream requests snapshot query fields
at call time, so later caller mutation cannot broaden the query.

Namespace filtering is not authentication. The managed tool enforces host
scope and checks returned records again. Low-level store callers must supply
their own authority boundary.

Adapters do not promise a global sort order. Missing attributes compare as
`None`, and equality retains the existing Python structural semantics.
This is not an arbitrary JSONPath, join, aggregation, or temporal-query API.

| Backend | Implemented surface | Limits |
|---|---|---|
| Package JSONL | Get/query/stream/export | Canonical rows; no mutation or transactional file snapshot |
| DuckDB file adapter | Parameterized local JSONL reads | No raw SQL or advertised Parquet/CSV/Arrow support until implemented in this adapter |
| SQLite | Queries, atomic preconditions and batch import | One database, serialized writers; residual attribute filtering |
| DuckDB record store | Queries and existing native-table writes | Legacy writes are not qualified for managed-record atomic preconditions |
| Composite catalog | Logical read projection | No write dispatch; conflict checks cover encountered records, not unseen rows beyond a bounded query |
| PostgreSQL | Contract/design only | No server integration demonstrated here |

SQL-backed stores push down scalar filters. Attribute matching currently runs
in Python before offset/limit. Bounded Python iteration does not establish a
bound on DuckDB's native memory or total scan cost.

## Managed notes use a tool

Use the [managed-record example](../../examples/24_managed_records/) for a
host policy and commands. `loop-engine records` accepts one bounded JSON
request on stdin. Host configuration selects the storage, schema, namespace,
and limits. Model input cannot set SQL, paths, scope, schema, or authority.

Create/update validate the document, consume approval for the exact effect,
write an immutable revision, and conditionally update the current reference.
Retire adds a tombstone revision. Historical versions remain readable. The
tool has no hard-delete operation or promotion permission.

Only a known precondition failure is a conflict. Storage errors, uncertain
write confirmation, or unverifiable readback produce `commit_unknown`, with
`committed: null`. A blob written before a failed head update may be
unreferenced. It must not be deleted automatically because another writer may
reference the same content. Files and database metadata are not one ACID
transaction.

Results are cards until selected materialization. The CLI reports
`run_history_persisted: false`: operational Loop events are in memory, while
the managed revision chain is durable. Automatic execution-history persistence
to a third target needs separate authority and remains unimplemented.

Use this path for new managed notes when host configuration exists. Do not
directly edit their database or immutable revisions. Source code, schemas,
tests, migration scripts, hand-authored documentation, and exact deliverables
still use their existing writing paths. Existing logs were not silently migrated.

## Package roles and security

DuckDB supports analytical file queries and attached databases, but those
features are not automatically present in every Loop Engine adapter. Its
PostgreSQL extension is a client connection, not a PostgreSQL-wire server.
Native analytical concurrency differs from server OLTP.
[DuckDB JSON](https://duckdb.org/docs/current/data/json/loading_json),
[concurrency](https://duckdb.org/docs/current/connect/concurrency),
[PostgreSQL extension](https://duckdb.org/docs/current/core_extensions/postgres/overview).

Unrestricted SQL can access files, networks, extensions, and secrets. DuckDB
itself treats untrusted SQL as a code-execution risk. Use typed queries on the
trusted connection; put an expert SQL escape hatch inside a separately
authorized sandbox. Parameterized values alone cannot secure arbitrary SQL.
[DuckDB security](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview).

The inspected runtime uses SQLite 3.46.1 and DuckDB 1.5.4. SQLite documents a
WAL corruption race under particular concurrent write/checkpoint conditions,
fixed in 3.51.3 and designated backports. New SQLite record writes retain the
rollback-journal default and reject affected WAL configurations inside every
write transaction, including externally changed journal modes. Other existing
WAL stores still need that qualification. No corruption was observed.
[SQLite WAL](https://www.sqlite.org/wal.html).

SQLite read-only mode refuses record changes and does not create a missing
database. It does not guarantee that all auxiliary bytes remain unchanged:
WAL shared-memory coordination can update `-shm`.
[SQLite URI modes](https://www.sqlite.org/uri.html).

## Views and remaining migration

The [generated architecture views](../ARCHITECTURE-DIAGRAMS.md) show record
access, immutable revisions, current SQLite records, read-only files, and a
target server adapter. C4 output uses C4-PlantUML macros. The former
Structurizr-flavoured text was not valid Structurizr DSL.
[C4 diagrams](https://c4model.com/diagrams),
[C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML).

Generated session Markdown is a next slice. Do not call manually maintained
notes a database projection. Its renderer must bind exact source revisions,
renderer version, output digest, and an approved output target. Keep existing
authority files intact during migration and compare old/new reads before a
writer cutover.

Still open: full managed-writer migration, relational schema mappings for
heterogeneous legacy files, server adapters, snapshot-aware federation,
retention/purge, generated session views, million-record qualification, and
automatic production model-tool discovery. Memory meaning, visibility, grants,
and model hydration remain separate from physical record storage.
