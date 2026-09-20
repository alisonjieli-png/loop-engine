# Catalog and shared-memory write repairs

Date: September 19, 2026. Kind: implemented repair and scoped verification.
This record follows the pre-repair intelligence audit. It does not rewrite
that audit's source hashes or historical diagnostic results.
The owner's later direction requires current active contracts only. The
temporary legacy revision reader added earlier in this batch was removed.

Six existing modules changed: `catalog/capabilities.py`,
`catalog/stores/in_memory.py`, `catalog/stores/sqlite_store.py`,
`catalog/stores/duckdb_store.py`, `catalog/versioning.py`, and
`core/shared_memory_scopes.py`, all under `src/loop_engine`.

The in-memory and DuckDB adapters now understand the same exact absence and
version guards as SQLite. In-memory checks and writes are protected by a
reentrant lock. DuckDB checks and writes share a transaction. Bundle imports
are atomic within the supported store boundary. Guarded writes across all
three adapters reject an unchanged record version. Operation capabilities
require the Boolean value `True`; a truthy string or number grants nothing.

Catalog versioning uses the store's atomic absence guard for initial creation.
Historical copies use create-if-absent semantics and preserve the complete
original record in `catalog_record_revision/v2`. Historical reads verify both
identity and content digest. Older inline revision formats receive an
unsupported-version diagnostic. Their stored bytes remain intact; no runtime
fallback tries to reconstruct or reinterpret them. Ordinary caller attributes
beginning `revision_` survive in the current complete snapshot format.

The immutable predecessor is written before the guarded current record. These
two writes are deliberately not described as one transaction. If the current
update fails, an identical copy of the still-current version may remain; the
history view does not report it as a second version. Unknown acknowledgments
and failed readback do not return a successful revision. A valid subsequent
revision can confirm an already-superseded committed version through its exact
preserved predecessor.

Shared-memory creation uses an atomic absence guard. Updates require a new
version, and numeric or dotted-numeric versions must advance. Scope identity
and namespace must both match before updating an existing record. A successful
write now requires a valid acknowledgment and matching readback. A backend
failure or intervening change that prevents confirmation is reported as an
unknown outcome, not a successful write or an invented stale-version result.

The supported storage interfaces and the existing managed-record service stay
in place. No parallel database, event log, runtime type, or new top-level
repository folder was added.

## Verification

[Current results](storage-current-contract-verification-results.json) bind the checks to the
exact six source hashes. The [verification runner](storage-write-verification.py)
executes the owning checks and mutates callables only in memory.

- 69 owning checks passed, including concurrent absence/version contention,
  stale versions, import rollback, unknown acknowledgments, false write
  confirmations, historical tampering, refusal of unsupported revision shapes, and SQLite/DuckDB
  restart and rollback.
- 142 dependent checks passed across catalog conformance, negotiation,
  registry, composite reads, managed records, reusable capabilities, temporal
  facts, and hosted service handlers.
- All 14 injected mutants were detected. They remove synchronization, absence
  guards, revision advancement, rollback, digest checks, acknowledgments,
  readback, or exact-Boolean capability enforcement.
- The scoped source diff has no whitespace errors.

No live provider or cloud call ran. No commit was made. Full repository
self-test, generated-map refresh, exported-tree installation, and release
verification remain the coordinating agent's integration work.

## Limits retained explicitly

SQLite retains its existing connection thread affinity. Its concurrent-writer
checks use separate connections. DuckDB qualification here concerns concurrent
connections within one process, not a shared file written by multiple hosts.
An in-memory acknowledgment remains non-durable despite its atomic write guard.

Generic version tokens remain caller-owned. Guarded writes reject immediate
reuse of the expected token; callers using opaque tokens must keep them fresh.
Shared Memory additionally enforces ordering for numeric versions. These
changes do not make every arbitrary multi-record lifecycle operation atomic.

The repair addresses the storage parts of INT-04 and INT-05 and questions
INT-Q004, INT-Q005, INT-Q006, INT-Q008, INT-Q014, INT-Q016, INT-Q017, and
INT-Q072. The multi-record transaction question INT-Q015 remains a documented
boundary rather than a claim of atomicity. Other intelligence, admission,
retrieval, and export findings remain separate work.
