# ADR: Transactional semantic runtime

Status: accepted for the current offline routing vertical slice.

## Context

A Loop may need semantic judgment even when no dedicated Python implementation
exists. Treating an empty function or docstring as a hidden model runtime would
create a second execution path with weak identity, effects, and verification.

Loop Engine already has one sealed `Loop` runtime, exact `LoopDefinition`
identity, three modes, typed contracts, model boundaries, effect approval,
catalog stores, and Run History. The missing decision was how an
implementationless specification uses those authorities.

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
    ├── Exact LoopDefinition
    ├── SemanticLoopContract when semantic behavior is declared
    ├── Selected realization
    ├── Typed input and output
    ├── Conditions, permissions, effects, and budgets
    └── Run History
```

Semantic contracts, interpreter profiles, realization bindings, candidates,
state deltas, verification records, effect decisions, execution records, and
reliability reports are passive objects. They are not graph vertices.

## Decision

The semantic specification is bound into the existing `LoopDefinition`.
`bind_semantic_loop_contract()` adds its digest to canonical configuration
facts. This changes the exact `LoopDefinition` digest. The final
`SemanticLoopContract` points back to that exact definition.

```text
SemanticLoopContractDraft
  -> specification digest
  -> exact LoopDefinition configuration fact
  -> new LoopDefinition content digest
  -> bound SemanticLoopContract
```

No decorator runtime is added. A future decorator may only create these passive
records and start the existing `Loop`.

## Semantic transaction

`execute_semantic_loop()` starts the bound Solution Loop and performs one
coherent semantic operation.

```text
typed input and provenance-aware context
  -> deterministic input and precondition checks
  -> one selected realization
  -> SemanticCandidateOutput and ProposedStateDelta
  -> Spawned Practitioner verifier Loop
  -> Spawned effect authorization Loop
  -> Spawned compare-and-swap commit Loop
  -> SemanticExecutionRecord and Run History
```

The default direct semantic realization makes one model call for the coherent
component. The fine-grained, multi-call alternative exists only as a benchmark
strategy in the current slice.

## Trust states

```text
candidate
  -> structurally_valid
  -> contract_valid
  -> verified
  -> effect_authorized
  -> committed
```

The model returns strict data. It cannot construct an issued verification or
effect authorization. `SemanticVerifier` and `SemanticEffectController` attach
private issuance identity. `CatalogTrustedSemanticState` checks those identities,
the candidate digest, the base state version, and the idempotency key before it
uses the existing `CatalogStore.put(..., precondition=...)` boundary.

A rejected or abstained result is not committed. A stale delta is refused. An
identical replay returns the existing commit without advancing state.

## Effective program identity

The effective semantic program is not the specification text alone.

```text
SemanticProgramIdentity
├── semantic contract digest
├── LoopDefinition digest
├── realization binding digest
├── interpreter profile or deterministic artifact digest
├── context-pack digest
├── tool-catalog digest
├── verification-policy digest
└── effect-policy digest
```

Changing any component changes `ProgramID`. An interpreter profile change must
run independent regression qualification. A failed qualification leaves the
prior qualified profile selectable.

## Realizations and modes

The modes remain deterministic, hybrid, and non-deterministic. A realization
does not add another mode.

```text
One SemanticLoopContract
├── deterministic code realization
├── cached procedure realization
├── promoted composite realization
├── hybrid semantic realization
├── direct semantic realization
├── novel generation realization
└── human authority or abstention
```

`select_semantic_realization()` applies lifecycle, exact contract, coverage,
unsupported-region, qualification, interpreter, and Code Intelligence checks.
It prefers an eligible promoted deterministic realization. An unsupported
region can fall back to a qualified semantic realization under the same
contract.

## Materialization

Semantic materialization reuses the Reusable Capability Flywheel. The routing
fixture emits a semantic procedure opportunity, creates a deterministic code
candidate with source-to-candidate lineage, and uses existing Code Intelligence
qualification and promotion. The semantic contract identity does not change.

## Implementationless routing fixture

The fixture routes a typed claim to `AUTO`, `PROPERTY`, or `NEEDS_REVIEW`.
The semantic contract has no dedicated implementation body. It requires a
declared queue, one applicable rule reference, no invented facts, and no
effects.

The offline proof covers:

- accepted direct semantic routing;
- safe `NEEDS_REVIEW` for missing facts;
- prompt-injection text treated as untrusted evidence;
- malformed policy output rejected before commit;
- undeclared state effects rejected;
- stale-state and idempotent-replay behavior;
- interpreter profile change, regression failure, and rollback;
- materialized deterministic routing with zero model calls;
- semantic fallback outside the deterministic coverage region; and
- five strategy records for direct, stepwise, plan generation, hybrid, and
  promoted deterministic execution.

## Evidence boundary

The interpreter transports are injected offline fixtures. The four-item
reliability population has zero observed false accepts and unsafe commits, but
this is not a statistical upper bound and does not prove the production risk
budget. Local timing does not predict provider latency.

The current slice does not prove live model quality, model diversity,
distributed state commits, external effect execution, container isolation,
cross-tenant privacy, or production-scale reliability.
