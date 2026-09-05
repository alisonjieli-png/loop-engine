# Scoped record operations over existing stores

Date: 2026-09-04. Status: accepted for the bounded local implementation.

## Decision

Extend `CatalogStore`, `IntelligenceQuery`, and the existing artifact store.
Do not create a second Record Fabric runtime, registry authority, or storage
engine. `RecordOperationService` is an internal mechanic whose operations run
through canonical Loops. A host policy binds schema, namespace, classification,
limits, and physical storage; model input supplies document values and typed
operations only.

```text
Canonical Loop operation
├── Host scope and schema
├── Typed read or mutation
├── Exact effect approval for writes
├── Immutable document revision
└── Atomic SQLite current-reference precondition
```

Current managed operations are create, get, query, update, and retire.
Retirement preserves history. No raw SQL, hard delete, source-file mutation,
Run History rewrite, or intelligence promotion is exposed.

## Alternatives considered

Rewriting JSON through a convenience database package would retain unsafe
read/modify/write semantics unless transactions and revisions were added.
Using DuckDB as a universal writer would ignore its different concurrency
model. Adding SQLAlchemy or a new ORM now would duplicate existing contracts
without proving the missing semantics. Keeping all operational notes as manual
Markdown would retain conflicting writers and ambiguous current state.

SQLite supplies the first local transactional authority. DuckDB remains an
optional query implementation. A future PostgreSQL adapter must satisfy the
same applicable contracts and its own concurrency/security qualification.

## Consequences and limits

Queries must match across supported adapters, and residual filters run before
pagination. Capabilities describe implemented behavior, not everything the
underlying engine could support. Typed precondition failure differs from
storage uncertainty. A successful write confirmation needs exact readback,
or a valid later revision chain containing the committed revision.

Artifact publication precedes database compare-and-swap. A failed or uncertain
head update may leave an unreferenced artifact. This is not a distributed
transaction; no automatic cleanup or false success is allowed.

Host backend bindings remain trusted configuration. Low-level store methods
are not authorization APIs. The first CLI does not persist its operational
Run History to a third target. Generated session Markdown, legacy writer
migration, transaction-wide outbox, server substitution, and retention remain
separate work. This decision changes no existing Run History authority.

See [queryable records and storage](../guides/queryable-records-and-storage.md)
and the [managed-record example](../../examples/24_managed_records/).
