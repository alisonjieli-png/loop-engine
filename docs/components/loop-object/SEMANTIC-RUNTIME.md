# Transactional semantic runtime

The semantic runtime lets one exact Loop contract execute without a dedicated
conventional implementation body. The contract remains canonical. Direct model
interpretation, hybrid interpretation, and deterministic code are replaceable
realizations under the three existing modes.

## Complete classification

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
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non_deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop and exit conditions
    ├── Budget, permissions, and effects
    ├── Optional SemanticLoopContract
    ├── Selected qualified realization
    └── Run History
```

Passive semantic records do not become graph vertices.

## Canonical identity

`SemanticLoopContractDraft` contains the complete implementation-independent
behavior:

- intent and specification;
- typed input and output schema references;
- preconditions and postconditions;
- permitted and prohibited effects;
- required context and evidence;
- resolution and interpreter policies;
- verification, completion, failure, and abstention policies;
- reliability budget and risk class; and
- execution-record policy.

`bind_semantic_loop_contract()` hashes the draft and adds the digest to exact
`LoopDefinition.configuration_facts`. The resulting `LoopDefinition` has a new
content digest. The bound `SemanticLoopContract` points to that exact
definition.

The effective program identity includes:

```text
SemanticProgramIdentity
├── SemanticLoopContract digest
├── LoopDefinition digest
├── realization binding digest
├── interpreter profile or deterministic artifact digest
├── context-pack digest
├── tool-catalog digest
├── verification-policy digest
└── effect-policy digest
```

An interpreter, context, tool, verifier, or effect-policy change produces a
different `ProgramID` even when the visible specification text is unchanged.

## Realization selection

```text
One canonical semantic contract
├── promoted deterministic code
├── cached verified procedure
├── promoted composition
├── bounded hybrid semantic body
├── direct non-deterministic interpretation
├── novel implementation generation
└── human authority or abstention
```

`select_semantic_realization()` checks exact contract identity, lifecycle,
qualification, mode, covered input region, unsupported regions, interpreter
profile, and Code Intelligence authority. It prefers a qualified deterministic
realization when it covers the current region. It may return a qualified
semantic realization for another region.

This ordering is a local resolver policy. It does not turn deterministic-first
into a universal product rule.

## One coherent transaction

`execute_semantic_loop()` starts the exact bound Solution Loop.

```text
input validation
  -> precondition check
  -> selected realization
  -> SemanticCandidateOutput
  -> ProposedStateDelta
  -> Spawned Practitioner verifier Loop
  -> Spawned effect authorization Loop
  -> Spawned trusted commit Loop
  -> SemanticExecutionRecord
```

The direct and hybrid semantic realizations make one model call for the
coherent operation. The current benchmark also runs a three-call stepwise
alternative, but that is not the default runtime.

## Candidate, verified, and committed

```text
candidate
  -> structurally_valid
  -> contract_valid
  -> verified
  -> effect_authorized
  -> committed
```

Model output is strict untrusted data. The model cannot issue
`SemanticVerificationRecord` or `SemanticEffectAuthorization`. The approved
verifier and effect controller attach private issuance identity. The trusted
state store validates those identities and all matching digests.

`CatalogTrustedSemanticState` uses the existing `CatalogStore` write contract.
It requires the exact base version and performs compare-and-swap. A stale delta
fails. Repeating the same candidate and idempotency key returns the existing
commit without advancing state.

An abstained or rejected candidate is not committed. For external effects,
`SemanticEffectController` requires records from a configured external-effect
consumer. A missing effect-approval path fails closed.

## Context safety

Each `SemanticContextItem` carries a provenance reference and one trust label:

- `verified_fact`;
- `trusted_policy`;
- `untrusted_input`;
- `untrusted_retrieval`; or
- `untrusted_tool_output`.

`SemanticContextPack` has an assembler identity, policy digest, byte ceiling,
token estimate, and content digest. Retrieved text, comments, evidence, and
tool output remain data. They cannot change system authority.

## Routing fixture

The current implementationless fixture is `semantic.route_claim@1.0.0`.
It routes one typed claim to `AUTO`, `PROPERTY`, or `NEEDS_REVIEW`.

The contract requires:

- one declared queue;
- one applicable reviewed rule reference;
- no invented claim type or jurisdiction;
- exact missing fields for `NEEDS_REVIEW`; and
- no state or external effect.

The fixture verifies:

- direct one-call semantic execution;
- safe abstention when facts are missing;
- prompt-injection text treated as untrusted evidence;
- rejected unsupported queues and undeclared effects;
- state unchanged after rejection or abstention;
- idempotent commit and stale-version refusal;
- different ProgramID after an interpreter profile change;
- independent regression failure and rollback;
- fixture-scoped reliability counts;
- deterministic materialization through the Reusable Capability Flywheel;
- zero-model deterministic reuse for the covered California region; and
- semantic fallback outside that deterministic region.

## Materialization

The routing proof observes an accepted semantic procedure and sends it through
the same harvest function used by the code flywheel.

```text
semantic execution record
  -> ReuseOpportunityObserved
  -> ReuseAssessment
  -> CapabilityGeneralizationRecord
  -> CodeAssetSpec candidate
  -> independent CodeAssetAdmissionRecord
  -> explicit promotion
  -> deterministic SemanticRealizationBinding
```

The semantic contract digest remains unchanged. The deterministic binding is
eligible only while the exact Code Intelligence artifact remains registered.

## Evidence limits

The interpreter ports in the current fixture are injected offline transports.
The four routing fixtures have zero observed false accepts and unsafe commits.
Four cases are not enough to establish a production reliability bound.

The local strategy timings measure Python fixture overhead. They do not predict
live provider latency or cost. Live model quality, model diversity, external
effects, distributed compare-and-swap, and production-scale input regions
remain unproven.

See the [exact local evaluation](../../verification/SEMANTIC-RUNTIME-EVALUATION.md)
for contract digests, ProgramID, strategy results, clean-wheel checks, and
limitations.
