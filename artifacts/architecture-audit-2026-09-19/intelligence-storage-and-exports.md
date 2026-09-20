# Intelligence storage, retrieval, and solution exports

Date: September 19, 2026. Kind: focused architecture audit before repairs.
Checkout: `main` at `48cc954322691e492aad69a465ba470a112730e7`, with existing
uncommitted work preserved. Findings describe the source hashes retained in
[the probe results](intelligence-storage-probe-results.json). Later repairs
must be assessed separately against those hashes.

The repository contains useful contracts for exact Code Intelligence
admission, managed records, and independent verification. They do not yet
govern every route that serves or executes intelligence. The most consequential
gaps are direct candidate execution, export verification that continues after
integrity failure, unbound inline content, and inconsistent write concurrency.
The current default query also composes several older stores instead of using
one configured catalog adapter throughout.

This audit semantically inspected 53 source files at the paths or symbols
listed below. It is not a claim that every line, runtime branch, backend,
customer deployment, or architecture component has been verified. No live
model, cloud operation, untrusted export, or real customer record was used.

## Classification and scope

The governing runtime classification is unchanged:

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

The following diagrams describe data and service dependencies. Their boxes
are modules, passive records, and stores, not additional executable runtime
vertices.

```text
Current public intelligence path
├── Context registries and packaged resources
│   └── context_catalog.build_context_records -> list[StoreRecord]
├── architecture_map.MODULE_MAP and Code template records
│   └── intelligence_layers.build_intelligence_catalog -> module/template cards
├── saved Run History manifests and complete event logs
│   └── RunHistory.load -> small previous-run cards
└── AdviceStore JSONL file
    └── advice_records_for_search -> all nonretired advice cards
        ↓
dict[layer name, list[StoreRecord]]
    -> IntelligenceSearchRequest
    -> query_intelligence
    -> new Retriever with SQLite full-text and hash-vector indexes
    -> hits plus IntelligenceItemRef
    -> load_intelligence_item / load_intelligence_ref
    -> supplied resolver
    -> selected value
```

`solve_dependencies` installs the bare `build_intelligence_catalog` function.
`_installed_catalog` calls it without the request's run root. `_four_layer_search`
then discards the complete returned reference and keeps a smaller title/identity
projection. It reads version and payload digest from top-level hit fields even
though the typed reference holds those fields. Sources:
[dependency construction](../../src/loop_engine/code_nodes/solve_runtime.py#L530),
[builder invocation and projection](../../src/loop_engine/core/adaptive_practitioner_orientation_capabilities.py#L117),
[catalog construction](../../src/loop_engine/core/intelligence_layers.py#L282).

```text
Governed reusable Code path
accepted source and assessment
    -> CapabilityAuthority.register_candidate_as_loop
    -> candidate exact record and lifecycle pointer
    -> qualify_as_loop with exact CodeAssetAdmissionRecord
    -> validated record
    -> promote_as_loop with a different promoter identity
    -> registered record and lifecycle pointer
    -> rebuild_capability_projection_as_loop
    -> versioned projection manifest and active pointer
    -> CapabilityResolver
    -> current authority and eligibility checked again
    -> invoke_capability_as_loop
    -> execute_code_ref -> supplied materializer and binder
    -> result verifier -> CapabilityInvocationRecord

Separate direct path
caller-supplied IntelligenceItemRef
    -> execute_code_ref
    -> supplied materializer and binder
    -> callable execution, without the admission checks above
```

The governed path's repeated checks are valuable. They make stale projections
insufficient authority to execute. The direct path remains a separate trust
problem; wrapping a callable in a Loop does not establish its qualification.
Sources: [active admission](../../src/loop_engine/core/reusable_capability_flywheel.py#L334),
[authoritative eligibility](../../src/loop_engine/core/reusable_capability_resolution.py#L218),
[invocation](../../src/loop_engine/core/reusable_capability_resolution.py#L532).

## Stores, authorities, and projections

| Boundary | Actual representation and durability | Authority and integration limit |
|---|---|---|
| `CatalogStore` | Generic dictionaries with typed `IntelligenceQuery`; read, put, bundle and health operations. No common delete or transaction context. | Shared adapter contract, not a universal access-control service. Empty query filters do not constrain a tenant or lifecycle. |
| `SQLiteRecordStore` | One current row per identifier, JSON attributes/payload, statement snapshots, serialized writes. | Atomically enforces absence and expected-version writes; supports atomic bundle import. Generic puts can replace rows and do not preserve history by themselves. |
| `DuckDBRecordStore` | Same broad row shape in a local DuckDB database. | Before repair, expected-version check and write are separate; bundle import performs individual puts. It does not declare SQLite's atomic-precondition capability. |
| `EphemeralRecordStore` | Deep-copied dictionaries for one process lifetime. | Useful reference adapter, but its precondition vocabulary differs from SQLite and it supplies no durable state. |
| `PackageJsonlStore` | Read-only line scans of packaged shards. | Files are authoritative. Lookup is a scan; health reports shard count without validating all current content. |
| `DuckDBFileQueryEngine` | SQL reads over exact local JSONL files, retaining complete JSON records. | Read-only file authority; rejects globs and symlinks, binds paths as parameters, and filters residual attributes before pagination. |
| `CompositeCatalog` | Read-only merged view. | A derived projection. It refuses encountered equal-identity conflicts, but bounded reads do not audit unseen rows. Unversioned `get` returns the first store's matching version. |
| `catalog.versioning` | Current record plus synthetic `record_id::version` records in the same store. | Intended revision authority, but initial creation and historical insertion have concurrency and integrity gaps described below. |
| `RecordOperationService` | Scoped catalog head plus immutable content-addressed revision artifacts. | Stronger managed-record boundary: exact effect approval, schema/namespace validation, atomic-store requirement, guarded head update, and explicit unknown-commit/orphan states. This is distinct from generic versioning. |
| `SolverStore` | Mutable `StoreRecord` objects, optional appended organization JSONL. | Older string-bank path. Malformed input rows are skipped, records are returned by reference, and it does not implement `CatalogStore`. |
| `DuckDBCatalogBackend` | Older SQL view over SolverStore-shaped JSONL. | Separate from the two `catalog/stores` DuckDB adapters. It lacks SolverStore's tier gates and interpolates file path/kind into SQL. |
| `AdviceStore` | Append-only guidance JSONL. | Scope and target are stored facts, but ordinary four-layer indexing reads all nonretired rows. No interprocess append/identity lock or truncated-tail recovery was found. |
| `CandidateJournal` | Semantic-learning records and governance entries in `candidates.jsonl`, with flush and file synchronization. | Durable journal with candidate/review/promotion records. Concurrent sequence/tail reservation is not implemented. Direct `query` does not validate the entire chain first. |
| `InMemoryMemoryStore` | Version lists for episodic, semantic, and procedural record types. | Separate query model from `CatalogStore`. Memory types classify records and are not additional intelligence layers. |
| `RunNoteBoard` | Run-scoped in-memory notes, detached on input/output. | Temporary Runtime Memory. Curation emits candidates; it does not activate persistent intelligence. |
| `HarnessIntelligenceCatalogue` | Dictionary of references, digests, metadata, effects, and tags. | A provisioning projection, not a fifth persistent store. No persistence or authoritative source-admission resolution is installed here. |
| `SolutionLibrary` and `SolutionsSpaceRecord` | Prior-solution cards over a supplied older store; separate passive plural solution records. | Neither is automatically populated into the default third-layer catalog or a complete public solve-to-export path. |

The September 18 storage decision proposes a default DuckDB catalog, body
references with indexed search characteristics, and a server database for wide
deployment. The inspected code does not establish that migration. In
particular, a class description that calls DuckDB the default does not install
it in `solve_dependencies` or the hosted handlers.

## Ranked findings

Priority 1 means resolve before exposing the affected route to untrusted
material or concurrent customer traffic. Priority 2 means an important
correctness or integration gap. Source-only concerns are identified separately
from reproduced observations.

### INT-01, priority 1: export integrity checks do not gate execution

`verify_export` trusts the loaded manifest's path keys, package name, isolation
mode, and claimed manifest digest. It records file mismatches and forbidden
content, then still imports the package and may run tests. The package name is
interpolated into Python source. `-I` and `-S` provide Python import isolation;
they do not restrict host filesystem, subprocess, or network access.

The saved probe replaces all export filesystem access and subprocess execution
with in-memory fakes. It observes one runner call after a failed integrity
check, an unvalidated package-name statement in generated code, an unknown
isolation mode passed through, and the unverified digest returned. No untrusted
export was executed. Source: [verify_export](../../src/loop_engine/code_nodes/solution_export.py#L326).
Required check: malformed or changed manifests must refuse before any runner
call, and untrusted execution needs the existing declared sandbox authority.

### INT-02, priority 1: direct Code execution bypasses candidate admission

The probe constructs a `CodeAssetSpec` whose lifecycle is `candidate` and whose
`admission_ref` is empty. `execute_code_ref` materializes and runs a supplied
pure callable, returning `7`. Its request has no authoritative store, exact
admission, lifecycle decision, or effect policy. This does not show a deployed
remote exploit. It shows that the public helper cannot itself uphold the
candidate-only rule. Source:
[execute_code_ref](../../src/loop_engine/core/code_intelligence_assets.py#L581).
Required check: both direct and governed entry points refuse an unadmitted
candidate before resolving an executable body.

### INT-03, priority 1: ordinary inline references do not bind body content

`intelligence_package_from_record` leaves `payload_digest` empty when the
record supplies no digest. The package digest covers identity, locator,
payload digest, and version, not the inline body or full handshake. The probe
selects a record containing `original` and loads `changed` through the same
reference. Source:
[reference projection](../../src/loop_engine/loop/loop_capsule.py#L222).
The external-body path compares an observed digest, but the resolver is
responsible for measuring it. Required checks must cover inline body mutation,
changed effects/contracts, and exact reference versions as separate cases.

### INT-04, priority 1: shared-memory versions do not protect all writes

`SharedMemory.write` accepts a nonempty version without requiring it to change.
Two sequential writers can both use `expected_version="1.0.0"`, write a new
payload still numbered `1.0.0`, and succeed even with SQLite. The second writer
overwrites the first. Initial creation separately reads for absence and then
writes unconditionally. Source:
[SharedMemory.write](../../src/loop_engine/core/shared_memory_scopes.py#L94).
The server correctly binds writer identity to the authenticated tenant; that
does not repair these revision races.

### INT-05, priority 1: adapter guards and historical writes differ

The same `exists:false` creation succeeds on SQLite and fails on the in-memory
adapter. DuckDB performs a read/check/write sequence without a guarded
transaction. `catalog.versioning.revise(None)` does not use SQLite's absence
precondition: two synchronized in-memory callers both successfully create the
same identifier. It also writes the historical row before the current guarded
update, and historical reads remove every user attribute beginning
`revision_`. The probe demonstrates a lost attribute and changed historical
content digest. Sources:
[adapter guards](../../src/loop_engine/catalog/stores/in_memory.py#L56),
[DuckDB write](../../src/loop_engine/catalog/stores/duckdb_store.py#L111),
[revision write/read](../../src/loop_engine/catalog/versioning.py#L100).

`RecordOperationService` already demonstrates stronger behavior: it requires
atomic preconditions, preserves immutable artifact revisions, and returns
`commit_unknown` when acknowledgment or readback cannot confirm the write.
Reuse this boundary's guarantees where applicable rather than inventing a
parallel record store. Source:
[managed mutations](../../src/loop_engine/core/record_operations.py#L333).

### INT-06, priority 1 before shared hosting: source scope is not bound to the solve

The default catalog builder ignores the requested run root when installed as
a bare callable. It reads default saved histories and all nonretired advice
from its selected advice file. Advice scope/target do not become actor-specific
search authorization. This is a source-proven integration gap, not evidence
that a live tenant leaked another tenant's records. A hosted composition needs
an authenticated source binding before any title or body reaches ranking.
Sources: [solve builder](../../src/loop_engine/code_nodes/solve_runtime.py#L549),
[advice search](../../src/loop_engine/core/user_feedback_intelligence.py#L319).

### INT-07, priority 2: qualification does not bind separate data references

Changing `CodeAssetSpec.data_refs` changes the card digest but leaves its
qualification digest unchanged. Admission compares the latter and the code,
dependency, contract, and effect digests. The data references and relevant
environment metadata therefore need an explicit qualification rule. The probe
demonstrates the digest mismatch in coverage, not an execution using changed
data. Source:
[qualification_digest](../../src/loop_engine/core/code_intelligence_assets.py#L261).

### INT-08, priority 2: solution verification labels exceed their bindings

`solutions_space_from_adaptive` marks the selected graph verified when the
input says solved and contains any passed independent report. It does not
match that report to the graph. The probe supplies an unrelated report digest
and receives a verified member. `SolutionsSpaceRecord.from_dict` also ignores
its serialized content digest. These are passive projection defects, not
proof that the underlying independent verifier issued a wrong report.
Source: [solution projection](../../src/loop_engine/code_nodes/solutions_space.py#L162).

### INT-09, priority 2: template identity omits behavioral fields

`TaskTemplate.content_digest` omits input/output contracts and maturity.
Registering the same identifier/version with different contracts and deprecated
maturity is treated as identical, leaving the earlier registered template.
The library also holds only one version per identifier and does not exclude
deprecated templates during search. Task compilation itself correctly keeps
template candidates advisory. Sources:
[template digest](../../src/loop_engine/templates/model.py#L353),
[registration](../../src/loop_engine/templates/library.py#L164).

### INT-10, priority 2: query bounds and facet ranking are inconsistent

`query_intelligence(top_n=1)` returned four results in the four-layer probe.
`Retriever.search` takes a bounded backend pool before applying required
facets, so it can return nothing while an eligible lexical match exists.
Preference bonuses are computed after sorting and do not reorder candidates
before truncation. Index errors are also converted into empty results.
Sources: [unified limit](../../src/loop_engine/core/intelligence_layers.py#L515),
[ranking](../../src/loop_engine/core/retrieval.py#L396).

### INT-11, priority 2: memory contradiction detection is disconnected

The memory store's conflict detector reads `result.record`, but ranking returns
`MemorySearchResult` objects with references and scores only. Two active
semantic claims in one contradiction group were selected with `conflicts=[]`.
`max_candidates` is accepted but not enforced on the inspected query path.
Sources: [conflict detection](../../src/loop_engine/memory/storage/store.py#L67),
[ranked result construction](../../src/loop_engine/memory/query/query.py#L223).

### INT-12, priority 2: persistence and admission are not connected to provisioning

The Harness Intelligence catalog is a dictionary. Its registration rejects
changed body digests but permits metadata replacement for the same digest.
`ProvisioningServer` enforces a generic body entitlement and declared effects,
then validates body bytes. It does not resolve source qualification or an
authenticated per-record disclosure scope. An absent meter still yields
`metered=true`. Its transport is intentionally absent. The separate service
defaults to in-memory shared state and metering. These source observations
agree with the earlier repository review; they were not new live-service tests.
Sources: [registration](../../src/loop_engine/core/harness_intelligence.py#L158),
[serving](../../src/loop_engine/core/provisioning_server.py#L183),
[handler default](../../src/loop_engine/code_nodes/service_endpoints.py#L100).

### INT-13, priority 2: optional retrieval effects and identity need qualification

The model2vec constructor can download a model through `from_pretrained`
without receiving typed network authority. It records a literal
`hf-cache-pin` revision and fixed dimensions rather than the exact observed
model revision. LanceDB creates a temporary index without an inspected cleanup
method. No download or optional backend was executed during this audit.
Source: [optional backends](../../src/loop_engine/core/retrieval.py#L255).

### INT-14, priority 2: older authorities remain separately callable

The older `DuckDBCatalogBackend` interpolates source path and kind into SQL and
does not apply the tier gates of `SolverStore`. `IntelligenceRegistry.promote`
requires only a nonempty evidence sequence, not an independent typed admission.
The inspected call-site search found that registry's construction only in its
self-test, so this is not established as the default product promotion path.
Its public description of durable database truth should not be used as evidence
for the stronger governed Code lifecycle. Sources:
[older DuckDB backend](../../src/loop_engine/core/duckdb_catalog.py#L66),
[older promotion API](../../src/loop_engine/core/intelligence_registry.py#L145).

## Export and recovery limits

The export path is `SolutionExportSpec -> export_solution -> package files and
MANIFEST.json -> verify_export -> host subprocess`. The specification supports
arbitrary supplied files and a concrete text-conformance generator. It is not
a compiler for every arbitrary Solution Canvas.

Its specification digest omits container settings; the safe probe produces
different scheduling definitions with the same specification digest. Verification
does not prove a clean wheel installation, the exact declared dependency set,
container execution, or independent fresh-input acceptance. Tests are optional,
and expected artifacts are checked for existence only. A generated Job still
contains `IMAGE_REFERENCE`, and the default base image is not digest-pinned.
These limits should be reflected in any graph's qualification status.

For storage recovery, SQLite supplies useful single-database guarantees.
Catalog lifecycle changes, version histories, and projection publication span
multiple calls outside a common transaction. CandidateJournal synchronizes each
line to disk, but sequence selection and append are separate. The public
learned-memory projection validates its journal and refuses oversized input;
direct journal queries do not perform that full validation. No multi-host
recovery claim is established by this audit.

## Evidence and exact inspection coverage

[The retained probe](intelligence-storage-probes.py) produced
[16 named observations](intelligence-storage-probe-results.json) with exit code
zero. That means the diagnostic script ran, not that the product passed. It
used in-memory dictionaries, SQLite `:memory:`, controlled thread interleaving,
pure callables, and a mocked export runner. The first command using `python`
failed because that executable is absent; the recorded successful command uses
`python3`. No optional DuckDB race, real untrusted export, deployment, provider,
or full-system benchmark was run.

[The question register](intelligence-questions.json) contains 100 distinct
questions: 48 answered, 14 open, and 38 disputed. A disputed question has a
documented or intended invariant that differs from inspected source or probe
evidence. Each question names its file, owning boundary, evidence, and a
discriminating check where needed.

[The coverage manifest](intelligence-coverage.json) lists every inspected path
for merging into the main architecture graph. The source coverage is exact as
a file list; inspections were focused on the following symbols rather than
an assertion that every line was reviewed:

| Files inspected | Main semantic scope |
|---|---|
| `src/loop_engine/catalog/capabilities.py`, `handshake.py`, `protocol.py`, `query.py`, `registry.py` | Declared capabilities, negotiation, query snapshots, supported operations, adapter selection. |
| `src/loop_engine/catalog/composite.py`, `versioning.py` | Identity conflict handling, pagination, authority, revisions, historical reads, rollback. |
| `src/loop_engine/catalog/stores/in_memory.py`, `sqlite_store.py`, `duckdb_store.py`, `package_jsonl.py`, `duckdb_files.py` | Production constructors, reads, writes, preconditions, imports, exports, health, shutdown; SQLite and DuckDB inspection stopped before most self-test bodies. |
| `src/loop_engine/core/intelligence_layers.py`, `context_catalog.py`, `retrieval.py`, `facets.py` | Layer vocabulary, builders, normal and candidate search, reference loading, backend construction, filters and ranking. |
| `src/loop_engine/loop/loop_capsule.py`, `encapsulate.py` | Passive references, external bodies, lazy loading, digest validation, callable execution wrapper. |
| `src/loop_engine/core/code_intelligence_assets.py`, `reusable_capability_flywheel.py`, `reusable_capability_resolution.py` | Asset/admission identity, template projection, materialization cache, direct execution, active authority, qualification/promotion writes, projection publication and invocation eligibility. |
| `src/loop_engine/core/store_serve.py`, `duckdb_catalog.py`, `intelligence_registry.py`, `solution_library.py` | Older record shapes, overlays, tier gates, SQL view, promotion compatibility, solution candidate assessment. |
| `src/loop_engine/core/harness_intelligence.py`, `harness_intelligence_bridge.py`, `intelligence_tagging.py`, `external_service_intelligence.py` | Provisioning references, metadata identity, candidate imports, tag matching, passive service contracts and credential-reference checks. |
| `src/loop_engine/core/provisioning_server.py`, `service_api.py`, `shared_memory_scopes.py`, `record_operations.py` | Authentication/entitlement path, in-memory metering, member reads/writes, exact managed effects, schema/scope checks, revision commit acknowledgment. |
| `src/loop_engine/code_nodes/service_endpoints.py`, `solve_runtime.py`, `solve_learned_memory.py` | Default storage and catalog bindings, authenticated writer identity, public learned-memory projection and size/chain validation. |
| `src/loop_engine/core/adaptive_practitioner_orientation_capabilities.py`, `practitioner_context.py`, `runtime_memory.py`, `user_feedback_intelligence.py`, `run_history.py` | Installed catalog search, packaged portfolio loading/fallback, run notes, advice persistence/search, saved-history load integrity. |
| `src/loop_engine/memory/storage/store.py`, `repository.py`, `learning_cycle.py`, `src/loop_engine/memory/query/query.py`, `src/loop_engine/memory/semantic/record.py` | Memory references and versions, scoring, contradiction grouping, scope categories, journal append/validation/latest projection and selected lifecycle operations. |
| `src/loop_engine/templates/compiler.py`, `library.py`, `model.py`, `intake.py` | Advisory compilation, template registration/search/version digest, captured instruction provenance. |
| `src/loop_engine/code_nodes/solution_export.py`, `solution_export_checks.py`, `solutions_space.py` | Export validation/rendering/writes/verifier, existing fixture coverage, solution publication/projection/digest reading. |

The manifest also lists 17 governing, component, architecture, and example
documents read for context. The architecture trees and documentation were
treated as statements to check against source, not execution evidence.

## Suggested repair order

First enforce admission and integrity at every callable execution and export
verification entry point. In parallel, repair write preconditions and immutable
history so concurrent callers cannot both succeed with stale state. Bind the
catalog's source scope to the authenticated run before extending hosted access.

Then fix identity completeness, solution verification binding, and retrieval
correctness. Keep managed records, generic catalog revisioning, semantic
learning journals, and rebuildable projections explicitly distinguished while
the approved storage migration is implemented. A single diagram should show
those current boundaries and the missing connections, not collapse them into
one already-completed database service.
