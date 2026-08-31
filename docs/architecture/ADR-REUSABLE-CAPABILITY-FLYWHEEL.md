# ADR: Reusable Capability Flywheel

Status: accepted for the current offline contract vertical slice.

## Context

Loop Engine can solve new work with a model, but a successful generated
implementation did not previously have one governed path into reusable Code
Intelligence. The existing parts were separate. Code cards described immutable
software. The Solution Library found related prior work. The reactive worker
scheduled asynchronous Loops. Run History stored digest-chained events.

The missing decision was how these parts become one closed reuse circuit.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non_deterministic
    └── Typed contract, conditions, permissions, and Run History
```

Capability needs, opportunities, assessments, admission records, lifecycle
records, and search projections are passive data. They are not graph vertices.
The work that creates or uses them runs through a classified Loop.

## Decision

Loop Engine uses a Reusable Capability Flywheel with three connected planes.

```text
Online resolution
  typed CapabilityNeed
  -> active search projection
  -> hard eligibility
  -> exact selection or bounded assistance
  -> exact Code Intelligence invocation
  -> independent output check

Asynchronous harvesting
  accepted verified result
  -> ReuseOpportunityObserved
  -> reactive trigger and leased activation
  -> structured ReuseAssessment
  -> CapabilityGeneralizationRecord
  -> candidate CodeAssetSpec
  -> independent qualification
  -> explicit promotion
  -> projection rebuild

Offline consolidation
  capability and failure history
  -> bounded duplicate or overlap region
  -> proposed merge, split, adapter, or replacement
  -> independent qualification before any lifecycle change
```

The current implementation completes the online plane and a working
asynchronous harvesting slice. Offline consolidation currently handles exact
artifact duplication. Structural clustering and behavior-based merging remain
future work.

## Authority and storage

```text
Authoritative catalog records
├── immutable CodeAssetSpec record
├── CodeAssetAdmissionRecord bound to exact digests
├── current lifecycle record
├── immutable lifecycle transition records
├── ReuseAssessment evidence record
└── CapabilityGeneralizationRecord from source to candidate

External artifact storage
└── immutable ExternalPayloadRef with SHA-256 digest

Rebuildable catalog records
├── immutable versioned capability search records
├── versioned projection manifest
└── active projection pointer

Operational evidence
└── Run History event chain
```

The catalog store is the source of truth. The projection can be deleted and
rebuilt. A projection match never grants lifecycle, effect, tenant, contract,
or dependency authority.

## Lifecycle

```text
candidate
  -> validated
  -> registered
  -> deprecated, quarantined, rejected, superseded, or retired
```

The producer cannot be the sole verifier or promoter. Qualification binds the
artifact, dependency, contract, and effect digests. Promotion creates a new
registered exact record. It does not rewrite the generated artifact.

## Three modes only

The flywheel does not add run modes. The modes remain deterministic, hybrid,
and non-deterministic.

Hybrid variations are passive assistance profiles. The installed profiles
cover normalization, reranking, adaptation, diagnosis, repair, composition,
and a combined profile. One profile may enable several stages without creating
a new Loop class or mode.

## Context Intelligence outage policy

The main Practitioner portfolio now lives under Context Intelligence at
`src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`.
A small minimum portfolio lives at
`src/loop_engine/data/practitioner_context_fallback.yaml`.

The minimum portfolio is used only when the caller declares Context
Intelligence unavailable and permits the fallback. The load record names the
source, digest, and degradation reason. A malformed primary portfolio fails
closed because corruption is not an ordinary outage.

## Consequences

- A cold model-built solution can become a candidate without blocking the
  source result.
- A candidate cannot enter active deterministic search.
- A warm exact task can execute with zero model calls.
- A free-form task can spend one bounded model call on normalization.
- A contract mismatch can use an ephemeral verified adapter.
- A failed output cannot change trusted state.
- A repair becomes a new candidate version.
- A rejected candidate never enters active resolution.
- A superseded exact qualified version may be restored by an explicit rollback
  transition.
- Exact duplicate harvesting adds an alias evidence record instead of another
  active capability.
- A narrow semantic procedure can use the same harvest and admission path to
  create a deterministic realization candidate.

## Rejected alternatives

Separate hybrid modes were rejected because they duplicate one semantic axis.
A second capability registry was rejected because the unified catalog already
owns authoritative records. Model-only promotion was rejected because a reuse
score is advice, not proof. Loading all code into a model context was rejected
because search cards and exact references already support progressive loading.

## Current evidence boundary

The vertical slice is an offline contract test with an injected model
transport. Python source uses the existing content-addressed artifact store.
Catalog authority and search projections survive a SQLite close and reopen in
the focused fixture. It proves architecture, lifecycle, call accounting,
restart persistence, and deterministic behavior. It does not prove live
provider quality, production sandbox isolation, remote artifact storage,
semantic search recall, or economic savings.
