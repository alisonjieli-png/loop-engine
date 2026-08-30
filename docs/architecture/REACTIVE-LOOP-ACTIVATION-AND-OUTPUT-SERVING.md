# Reactive Loop activation and output serving

## Status

Loop Engine now has a local reactive execution foundation. It supports typed
reactive profiles, storage-neutral value references, durable trigger
admission, fenced work leases, asynchronous execution through exact Loop
definitions, immutable candidate and evaluation records, and append-only
portfolio serving.

This checkpoint does not claim distributed execution, external push
endpoints, production polling, process-based CPU parallelism, or automatic
attachment of a reactive profile to every existing `LoopDefinition`.

## Architecture decision

There is still one operational runtime type.

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Mode: deterministic, hybrid, or non-deterministic
    ├── Exact LoopDefinitionRef
    ├── Finite activation
    ├── Typed inputs and outputs
    ├── Budget, permissions, and effects
    └── Run History

Passive reactive records
├── ReactiveLoopProfile
├── ReactiveSeriesDefinition
├── TriggerEnvelope
├── ActivationRecord
├── WorkLease
├── CandidateOutput
├── CandidateEvaluation
└── OutputPortfolioSnapshot

Internal runtime mechanics
├── InformationResolver
├── SQLiteReactiveScheduler
├── CanonicalReactiveExecutor
├── AsyncReactiveWorker
└── SQLiteReactiveOutputStore
```

A series is not an executable graph vertex. It groups a durable ongoing
responsibility. Each admitted trigger creates one finite activation. A claimed
activation starts the exact canonical `Loop` named by its
`LoopDefinitionRef`.

## Information identity and storage

`LoopValueRef` is the exact logical identity for a value produced by a Loop.
Physical storage is represented separately by `InformationStorageBinding`.

```text
LoopValueRef
├── content digest
├── value contract
├── semantic role
├── producer Loop
└── producer definition

InformationStorageBinding
├── adapter identity
├── opaque locator token
├── durability
├── sharing scope
├── permissions
├── media type
└── size
```

Consumers never receive the locator token from the public descriptor. They
submit an `InformationAccessRequest`. The resolver checks scope, permission,
size, exact reference identity, and content digest before returning a value.

The current local adapters cover process-local inline values,
content-addressed files through `ContextArtifactStore`, and durable JSON
values in SQLite.

One exact reference can have several materializations. A process-local binding
does not claim restart durability. Possessing a reference does not grant read
authority.

## Reactive profile

`ReactiveLoopProfile` keeps independent policy dimensions separate.

```text
ReactiveLoopProfile
├── ActivationPolicy
├── AdmissionPolicy
├── InputSchedulingPolicy
├── PersistenceMode
├── ExplorationPolicy
├── OutputPortDefinition records
├── PortfolioPolicy
├── EmissionPolicy
├── ServingPolicy
├── RetentionPolicy
└── ReactiveLivenessPolicy
```

The safe one-shot profile accepts explicit requests, keeps ephemeral state,
uses one candidate route, and does not reactivate on reads. A durable series
must explicitly enable reactivation and provide its own activation limit.
Loop Engine does not invent one universal wall-time value.

## Trigger and activation lifecycle

```text
TriggerEnvelope
→ schema and exact-profile validation
→ unchanged-input and deduplication checks
→ admitted ActivationRecord
→ worker claim
→ expiring WorkLease with fencing token
→ activation starts exact LoopDefinitionRef
→ canonical Loop reaches one terminal event
→ fenced terminal update
→ result remains queryable
```

An expired lease returns work to admission while attempts remain. The next
claim gets a higher fencing token. The old worker cannot commit. Exhausted work
enters `DEAD_LETTER` with an explicit failure code.

Scheduler state uses SQLite WAL and append-only activation revisions. Live
Python coroutines are never serialized.

## Candidate outputs and portfolios

Candidate output, evaluation, rank, and delivery are separate facts.

```text
CandidateOutput
└── immutable production metadata plus LoopValueRef payload

CandidateEvaluation
└── independent verdict, confidence vector, risk, cost, latency, and novelty

OutputPortfolioSnapshot
└── ranks under one exact policy version and input watermark
```

Rank is not stored on `CandidateOutput`. The same candidates may have different
ranks under different policies. A candidate producer cannot be its sole
verifier for a verified result.

The SQLite output store is append-only. It supports current and as-of portfolio
queries without waking the producer. Changed candidate identities, rewritten
portfolio versions, missing references, and changed record bodies fail closed.

## Asynchronous execution proof

The local proof starts three independent durable activations. Each activation
creates a separate canonical Loop with an activation-namespaced Loop ID. The
blocking handlers execute through thread placement and overlap in wall-clock
time.

```text
Reactive series
├── activation A → activation.A.loop1
├── activation B → activation.B.loop1
└── activation C → activation.C.loop1
```

The proof checks three distinct Loop IDs, exact definition references, real
overlap before any handler finishes, one terminal history per Loop, and one
durable terminal activation record per Loop.

This proves local thread placement for blocking test work. It does not prove
process-level CPU parallelism.

## Run History

Reactive events use the existing event vocabulary and observer boundary.

```text
loop.activation.admitted
loop.activation.leased
loop.activation.started
loop.activation.heartbeat
loop.activation.recovered
loop.activation.completed
loop.activation.failed
information.binding.published
information.materialized
output.candidate.stored
output.evaluation.stored
output.portfolio.stored
```

SQLite state supports restart and efficient lookup. It does not replace Run
History as the canonical runtime event evidence.

## Exact remaining work

- Attach an exact reactive profile reference to every new `LoopDefinition`.
- Add durable binding discovery after process restart.
- Add subscription, acknowledgment, outbox, and retraction delivery.
- Add approved push and polling adapters.
- Add cancellation propagation through reactive workers.
- Add process placement for CPU-heavy independent Loops.
- Add remote-worker and partition testing.
- Connect candidate creation and portfolio publication to the adaptive
  Practitioner.
- Prove task-conditioned topology elasticity across unrelated task families.
- Add Studio views for active series, leases, candidate history, and portfolio
  evolution.
