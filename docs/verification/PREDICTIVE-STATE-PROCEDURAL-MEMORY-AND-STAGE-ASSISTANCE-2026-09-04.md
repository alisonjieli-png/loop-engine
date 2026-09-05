# Predictive state, procedural memory, and stage assistance verification

Verification date: 2026-09-04

Repository revision: `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`

Branch: `main`

Later audit qualification: the
[architecture mesh and corpus audit](ARCHITECTURE-MESH-CORPUS-AUDIT-2026-09-04.md)
reproduces a genuine verifier record for result B being attached to result A.
The exact-lineage tests below did not cover that evaluated-subject mismatch.
It also identifies incomplete accepted/speculative artifact separation in the
adaptive integrator. Preserve the test results as scoped offline evidence;
they do not establish those missing invariants. No runtime correction was
made by the later audit.

This report covers the current dirty checkout. Existing edits and untracked
files were preserved. No commit, push, release, Kaggle submission, or live
model call was made for this work.

## Architecture boundary

The implementation keeps one executable runtime.

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

Information measurements, procedural assessments, hydrated prior material,
fingerprints, outcome records, and SQLite indexes remain passive. Classified
Loops own any work that creates, retrieves, executes, verifies, or acts on
them.

## What was implemented

### Information diagnostics

The offline candidate layer now includes:

- finite categorical entropy and Shannon-surprisal calculations;
- Bayesian-surprise calculations kept distinct from Shannon surprisal;
- discrete empirical predictive-information diagnostics;
- deterministic in-sample data-processing checks;
- stochastic projections with no unsupported deterministic residual claim;
- paired context-compression and declared-loss operating points;
- separate estimator contracts and units for bits versus bytes and task loss;
- typed infrastructure-validity records;
- minimum valid-population coverage;
- exact physical-sample deduplication;
- absolute treatment-loss and false-acceptance ceilings;
- explicit unknown cost and latency handling.

The aggregate result types use recomputation functions. Their source
references and validity records are still unissued candidates until a
canonical Run History resolver exists.

### Procedural-memory control candidates

"AI muscle memory" is used only as an engineering metaphor for evidence-gated
procedural automaticity. The offline assessment records seven control probes:

```text
Procedural control candidate
├── initiation
├── termination
├── interruption
├── outcome devaluation
├── negative transfer
├── fresh control
└── deliberative fallback
```

The strongest possible status is
`candidate_support_pending_resolution`. The record cannot report resolved
support, execute or retrieve a procedure, mutate state, grant authority, or
promote itself. Exact procedure-to-probe binding, assessor identity, packet
freshness, validity issuance, and fallback availability remain unresolved.

### Public-solve control inventory

Every active advisory or fresh binding carries a
`PublicSolveControlManifest`. It contains ten components: task and source,
solver policy, runtime definition, context and interface, model execution,
capability surface, execution environment, evaluation, workspace isolation,
and observer sinks. Unknown values must be named. The current contract admits
only `mechanism_only`; it cannot report `paired_candidate`.

The complete manifest is written to Run History before the first model
attempt. A passive `StageControlApplicationCandidate` contract also exists for
a later stage-local base-state, base-packet, treatment-delta,
realized-execution, evaluator, and workspace-seed proposal. It is unverified,
is not populated by the product path, and is not experimental evidence.

Control and experiment event bodies are excluded from model-visible history.
The packet receives digests of the experiment and trial references, not their
raw labels. The fixture places one forbidden sentinel in both channels and
proves that neither arm sends it to the provider adapter.

### Public offline stage assistance

The programmatic public solve path now supports this offline flow:

```text
SolveRequest
  -> treatment-neutral task/source digest
  -> pre-run control manifest
  -> advisory or fresh experiment binding
  -> Starting Practitioner Loop
  -> exact semantic-stage occurrence
  -> rendered model work packet
  -> prompt-sensitive provider adapter
  -> admitted assistance disposition
  -> selected action
  -> capability execution
  -> downstream verification
  -> exact action selection, execution, and verification occurrences
  -> action-producing stage outcome update
  -> Run History and public SolveOutcome
```

Advisory candidates require a matching `StageAssistanceMaterial`. That record
binds the candidate, source occurrence, semantic signature, hydration level,
content digest, and source evidence. The material is labeled as untrusted
evidence and not an instruction. Its body enters the rendered selected-
intelligence section.

The fresh arm rejects candidates and hydrated material. Both active arms skip
unrelated prior-region tuning. The fixture provider checks required and
forbidden prompt fragments at its physical adapter boundary.

The exposure, decision, and action records now join:

- packet and rendered prompt digests;
- logical gateway request digest;
- physical provider request digest;
- physical model-attempt Loop identity;
- admitted response digest;
- semantic payload digest;
- selected-action occurrence reference;
- admitted plan digest and execution occurrence reference;
- complete result-packet digest;
- verifier-stage occurrence and semantic-call identity;
- exact evaluation-record digest;
- downstream use and direct local verification as separate methods.

The exact `decide_next` stage records downstream consumption and a separate
local action-result verification signal. The other six semantic stages remain
unknown. This does not assign treatment credit or causal benefit. The verifier
uses the same Practitioner model path, so evaluator independence and
attribution confidence remain unknown.

## Offline advisory/fresh mechanism evidence

The current durable evidence root is
[`stage-assistance-public-offline-exact-lineage-20260904`](../evidence/runs/stage-assistance-public-offline-exact-lineage-20260904/).

The report is
[`report.json`](../evidence/runs/stage-assistance-public-offline-exact-lineage-20260904/report.json),
SHA-256
`ed1c9a57ba926518739d582937e706e03e491b45a0e2490094fc2a1d3b527607`.

| Evidence | Result |
|---|---:|
| Calibration runs | 1 |
| Separately executed arm runs | 2 |
| Logical calls across both arm runs | 14 |
| Physical adapter calls across both arm runs | 14 |
| Total fixture calls including calibration | 21 |
| Live provider calls | 0 |
| Advisory hydrated bodies in prompt | 7 |
| Fresh hydrated bodies in prompt | 0 |
| Assistance decisions per arm | 7 |
| Directly linked action stages per arm | 1 |
| Other locally uncredited stages per arm | 6 |
| Pre-run control manifests per run | 1 |
| Control evidence class | mechanism-only |
| Named blocking control unknowns | 6 |
| Solved arms | 2 of 2 |
| Intact saved Run Histories | 3 of 3 |
| Events per saved Run History | 551 |

Saved run IDs:

- calibration: `adaptive-64dc506ed803819e6a38f992`;
- advisory: `adaptive-cc136d15c8504634261d69dd`;
- fresh: `adaptive-2bf3040550fccf6f6af12fb0`.

The mechanism fixture passes 23 of 23 checks. Equal outcomes are expected
because the injected responses and project executor are controlled fixtures.
They do not show that assistance improves quality, cost, or latency.

The report contains its source revision and generation time, but its source
snapshot status is `dirty_checkout_not_content_bound`; it has no complete
dirty-worktree digest. It is mechanism evidence, not a reproducible source
snapshot or valid paired comparison.

## Verification results

| Check | Result |
|---|---:|
| Information evidence | 29 / 29 |
| Information adversarial checks | 24 / 24 |
| Procedural control checks | 57 / 57 |
| Hydrated material checks | 7 / 7 |
| Stage action lineage checks | 17 / 17 |
| Stage action lineage adversarial checks | 12 / 12 |
| Public-solve control manifest checks | 10 / 10 |
| Model-visible semantic event history checks | 3 / 3 |
| Public solve adaptation checks | 5 / 5 |
| Stage assistance contracts | 37 / 37 |
| Model gateway | 18 / 18 |
| Solution model port | 9 / 9 |
| Public offline pair | 23 / 23 |
| Source full self-test | 2,430 / 2,430 |
| Source conformance | 27 / 27 gates |
| Clean-wheel applicable self-test | 2,392 / 2,392 |
| Clean-wheel conformance | 27 / 27 gates |

The clean-wheel run did not install optional `duckdb`, MCP, model2vec, NumPy,
OpenTelemetry, pandas, or scikit-learn adapters, so those suites were reported
as not applicable rather than passed.

The first wheel probe used `--no-deps` and was invalid because `jsonschema` is
a required dependency. Before reaching that point, it exposed an independent
Python 3.14 cold-start issue: two test paths relied on `importlib.util` being
loaded implicitly. The source now imports that submodule explicitly. A fresh
wheel with declared dependencies installed passed.

The source distribution was built from the current checkout. The wheel below
was then rebuilt from a fresh extraction of that source distribution:

| Artifact | SHA-256 |
|---|---|
| `loop_engine-0.1.0.tar.gz` | `699944ceca0a802c1884978992e0cd288503d13c1fbf624c6ef06d1510633986` |
| `loop_engine-0.1.0-py3-none-any.whl` | `03dc0b2075a71d14ebe707cafced830e65ad6cf3d3e10f5dbe50da1c353f5985` |

The generated
[`distribution-verification.json`](../evidence/runs/stage-assistance-public-offline-exact-lineage-20260904/distribution-verification.json)
has SHA-256
`8fc7c4ba8f46d21e2c6c3086f6e30ff516e7156ea2ef00c7a24eec38ffcbd726`.
The binaries remained in a temporary build directory, and the dirty source
checkout still lacks a complete content digest.

## Research interpretation

The associated
[procedural-memory and predictive-state review](../research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md)
uses primary sources to define the safe research direction. The main lessons
implemented here are:

- predictive state should be tested by held-out regret, not declared
  sufficient from a compact representation;
- empirical information estimates need explicit variables, populations,
  estimators, units, exclusions, and bias limits;
- reusable procedures need initiation, termination, interruption,
  devaluation, negative-transfer, fresh-control, and fallback tests;
- fast episodic capture must remain separate from slow, independently reviewed
  consolidation;
- retrieval similarity and repeated success do not grant execution authority.

## Remaining unproven

- A live language model has not used, modified, combined, or rejected the
  hydrated prior material on this product path.
- Candidates are injected by the fixture. A canonical Intelligence Query Loop
  does not yet retrieve and hydrate them from another task's Run History.
- The request-wide trial reference is not a canonical per-stage paired trial.
- Product runtime events are not yet converted into the canonical projection
  record sequence or rebuilt into SQLite from these three histories.
- The task/source digest is intentionally not a full-control digest. The
  pre-run manifest names six blocking unknowns in this fixture: dirty runtime
  build identity, arm-specific injected responses, executor implementation,
  independent evaluator identity, initial workspace content, and callback
  implementation.
- Local source identity still uses path metadata rather than immutable file
  bytes or directory-tree digests. Remote source content and source-to-use
  time-of-check/time-of-use stability are not frozen.
- The stage-local `StageControlApplicationCandidate` is not populated. There
  is no treatment-free base-packet comparison or realized-control drift check.
- The arm still comes from the runtime binding, not a resolved canonical trial
  assignment. No comparator proves that two realized calls differ only by the
  declared treatment.
- Extension snapshots are detached from later caller mutation, but provenance
  and prior-derived contamination checks for extensions, resolvers, templates,
  context resources, workspaces, model sessions, and prompt caches are absent.
- Public control status is bound to the successful in-memory ledger append,
  not yet re-derived from a verified committed Run History scan. Component
  `exact` status also remains caller-declared, so the only admitted manifest
  evidence class is `mechanism_only`.
- One action-stage join does not complete the full stage-outcome vector.
- Treatment contribution and causal assistance benefit remain unknown.
- Information and procedural-control candidates are not persisted or resolved
  through canonical Run History.
- No Kaggle task was executed for this slice. The 100-task campaign remains a
  later gate.
- No small model, router, embedding policy, n-gram policy, or deterministic
  shortcut gained authority.

## Exact next action

Preallocate one canonical `decide_next` stage pair, populate its stage-local
control applications from treatment-free base packets, and bridge its
occurrence, assignment, retrieval, exposure, decision, evaluation, and outcome
records into Run History. Then delete and rebuild the SQLite projection from
those canonical histories. Only after that passes should one bounded live
cross-domain advisory-versus-fresh pair use the same observed provider, model,
settings, tools, evaluator, authority, and source artifacts.

Only after that live pair should the five-task mixed-shape Kaggle gate begin.
