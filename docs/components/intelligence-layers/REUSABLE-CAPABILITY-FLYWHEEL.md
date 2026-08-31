# Reusable Capability Flywheel

The Reusable Capability Flywheel turns an accepted generated implementation
into a governed Code Intelligence candidate. A later task can run the promoted
artifact without another model call when contracts match exactly.

## Complete flow

```text
New task
  -> no active capability match
  -> non-deterministic discovery
  -> accepted and verified result
  -> reference-only reuse opportunity
  -> asynchronous harvest activation
  -> structured reuse assessment
  -> source-to-candidate generalization record
  -> exact Code asset candidate
  -> independent qualification
  -> explicit promotion
  -> search projection rebuild
  -> future typed need
  -> hard eligibility
  -> deterministic invocation
  -> verified output with zero model calls
```

## Contracts

| Contract | Purpose |
|---|---|
| [`CapabilityNeed`](../../../src/loop_engine/core/reusable_capability_records.py) | Typed subtask goal, contracts, effects, capabilities, environment, privacy, tenant, and search terms. |
| [`ReuseOpportunityObserved`](../../../src/loop_engine/core/reusable_capability_records.py) | Reference-only event created after accepted verified work. |
| [`ReuseAssessment`](../../../src/loop_engine/core/reusable_capability_records.py) | Advisory dimensions, 1 to 10 summary, confidence, recommendation, evidence, and blockers. |
| [`CapabilityGeneralizationRecord`](../../../src/loop_engine/core/reusable_capability_records.py) | Exact source and candidate artifacts, parameters, preserved invariants, removed assumptions, producer Loop, and evidence. |
| [`CodeAssetSpec`](../../../src/loop_engine/core/code_intelligence_assets.py) | Searchable Code Intelligence card plus immutable external body reference. |
| [`CodeAssetAdmissionRecord`](../../../src/loop_engine/core/code_intelligence_assets.py) | Independent proof bound to exact artifact, dependency, contract, and effect digests. |
| [`CapabilityResolutionPlan`](../../../src/loop_engine/core/reusable_capability_records.py) | Exact execution, required selection, bounded assistance, novel build, or abstention. |
| [`CapabilityInvocationRecord`](../../../src/loop_engine/core/reusable_capability_records.py) | Exact code identity, input and output digests, mode, model-call count, verification, and acceptance. |

The 1 to 10 score is descriptive. It cannot promote a capability. A creation
recommendation must still preserve the accepted source artifact, and every
active artifact must pass independent qualification and promotion.

## Authoritative records and projections

`CapabilityAuthority` writes to a supplied `CatalogStore`. It does not own a
second in-memory registry.

```text
Catalog authority
├── code_asset
│   └── immutable CodeAssetSpec for one lifecycle state
├── code_asset_admission
│   └── exact independent qualification record
├── code_asset_state
│   └── current lifecycle pointer to an immutable exact record
├── capability_transition
│   └── actor, evidence, before state, after state, and digest
├── capability_alias
│   └── duplicate opportunity linked to existing exact content
├── reuse_assessment
│   └── complete advisory dimension set and source evidence
└── capability_generalization
    └── immutable source-to-candidate lineage

Rebuildable view
├── immutable capability_search_projection records
├── versioned manifest
└── active manifest pointer
```

The projection stores no executable body. It contains the authority reference,
contract digests, effects, dependencies, environment, license, search terms,
artifact digest, qualification digest, and admission reference.

## Search and eligibility

The current resolver reads only records named by the active projection
manifest. It performs structured comparison and lexical overlap. It computes
hard eligibility from current authoritative `CodeAssetSpec` data, not from
projection claims, before returning an executable plan.

Hard checks include:

- current lifecycle is `registered`;
- the current state points to an exact registered `CodeAssetSpec`;
- exact admission still matches the artifact and contract set;
- input and output contracts match, or an enabled adapter stage is present;
- effects are within current authority;
- required capabilities exist and prohibited capabilities do not;
- environment and dependency constraints match;
- tenant scope matches;
- license state is known.

Lexical overlap helps order records. It cannot override any hard failure.
When one capability has an exact operation family and contract match, the plan
can execute deterministically. Several eligible matches require an explicit
selection or bounded reranking.

Embedding and graph indexes can be added as rebuildable projections. They do
not need to change the authority record or invocation contract.

## Hybrid assistance profiles

The installed policy file is
`src/loop_engine/data/reusable_capability_hybrid_profiles.yaml`.

| Profile | Enabled model work |
|---|---|
| `hybrid.normalize_then_resolve` | Normalize the need and expand search terms. |
| `hybrid.retrieve_then_rerank` | Compare only the supplied eligible candidate references. |
| `hybrid.adapt_then_execute` | Propose narrow input and output adapters. |
| `hybrid.execute_then_diagnose` | Classify a bounded execution failure. |
| `hybrid.execute_then_repair` | Diagnose and propose a new candidate version. |
| `hybrid.compose_promoted_capabilities` | Propose a composition of promoted capabilities. |
| `hybrid.full_assisted_resolution` | Combine the installed stages in one structured semantic operation. |

These are profiles, not modes or subclasses. The model receives a bounded
packet and must return an exact stage-output object. It does not see the whole
repository or catalog. Reranking cannot select outside the eligible set.

An adapter remains ephemeral after one successful run. Repeated evidence may
create a separate adapter opportunity, but it still follows candidate,
qualification, and promotion rules.

## Asynchronous harvesting

`HarvestDispatch.ASYNC` is the default. The source task creates a small event,
publishes its value through `InformationResolver`, and admits a
`TriggerEnvelope` to `SQLiteReactiveScheduler`. The source task does not wait
for candidate construction.

`AsyncReactiveWorker` claims the activation with a fenced lease and starts the
exact `LoopDefinition`. Its assessment and generalization stages run as Loops
inside the worker before candidate registration. Duplicate event delivery
returns the existing activation. Worker failure does not change the already
accepted source result.

Inline harvesting uses the same assessment and candidate admission contracts.
It skips reactive placement only when the caller explicitly selects inline
dispatch.

The public adaptive Practitioner accepts an optional typed
`ReuseObservationPort`. When configured, a verified generated project submits
its exact source Loop, definition, Run History, workspace, and manifest
identity after completion. The port defaults to asynchronous dispatch. A base
installation does not invent a persistent catalog or worker configuration, so
deployments must bind the port to their approved stores and reactive series.

## Trust and failure handling

```text
model or generated implementation
  -> candidate record
  -> independent validation
  -> exact admission record
  -> explicit promotion
  -> active invocation
  -> output postcondition
  -> accepted result
```

Candidate and validated assets are absent from the active projection. The
producer cannot be the sole verifier or promoter. A failed postcondition
creates a rejected invocation record and leaves active state unchanged.

A repair uses a new version and a new artifact digest. It cannot rewrite the
promoted version. Review may mark a candidate `rejected`. A serious defect can
move an active version to `quarantined`, which removes it from the active
projection manifest. An explicit rollback may restore only the same exact
previously qualified version.

The current invocation still uses the existing Code Intelligence materializer
and component Loop. Untrusted code, file writes, commands, network calls,
secrets, and external effects remain subject to existing sandbox, workspace,
and exact approval contracts.

## Context Intelligence fallback

The full Practitioner question, guidance, and persona portfolio is stored at
`src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`.
The minimum outage portfolio is stored separately at
`src/loop_engine/data/practitioner_context_fallback.yaml`.

Use `load_practitioner_context_with_record()` when the caller needs the source
and degradation record. A declared outage can use the minimum file when policy
allows it. A caller may choose a fail-closed policy instead.

## Current verified scope

The offline vertical slice proves a pure Python function, content-addressed
artifact materialization, SQLite catalog restart, SQLite reactive scheduling,
the adaptive Practitioner resolver adapter, and an injected model transport.
It does not prove remote workers, container sandbox quality, embeddings,
structural code clustering, license scanning, dependency vulnerability
scanning, or live provider behavior.

The same flywheel can materialize a stable semantic procedure into a candidate
deterministic realization without changing its canonical semantic contract.
Read [Transactional semantic runtime](../loop-object/SEMANTIC-RUNTIME.md).
