# Reusable Capability Flywheel evaluation

Date: 2026-08-31

## Result

The offline flywheel vertical slice passed 33 of 33 checks. The final source
checkout full suite passed 1,617 of 1,617 checks with zero provider calls. The
corrected Python 3.10 wheel passed 1,588 of 1,588 installed checks with zero
provider calls. All zero-tolerance conformance gates passed, and repository
conformance indexed 321 files with no problems.

This is local contract and runtime evidence. It does not prove live provider,
remote worker, production sandbox, retrieval-quality, or economic performance.

## Commands

```bash
PYTHONPATH=src .venv/bin/python -c '
from loop_engine.core.reusable_capability_checks import self_test
r = self_test()
print(r["passed"], r["total"], r["all_passed"])
'

PYTHONPATH=src .venv/bin/python -m loop_engine --self-test
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src .venv/bin/python -m loop_engine --repo-conformance --format json
git diff --check
```

Focused result: `33 33 True`.

## Cold-to-warm proof

```text
cold CapabilityNeed
  -> no active realization
  -> one injected non-deterministic discovery call
  -> accepted narrow email implementation
  -> async ReuseOpportunityObserved
  -> reactive worker assessment Loop
  -> reactive worker generalization Loop
  -> configurable key_fields and keep policy
  -> content-addressed CodeAssetSpec candidate
  -> candidate absent from active projection
  -> independent qualification
  -> explicit promotion
  -> versioned projection manifest
  -> paraphrased warm CapabilityNeed
  -> deterministic invocation
  -> independent result verification
  -> accepted result with zero model calls
```

Promoted exact identity:

| Field | Value |
|---|---|
| Asset | `code.data.record_deduplication` |
| Version | `1.0.0` |
| Artifact digest | `6cfbda776790640fd99ddc3fa74950e1cd43061bff3ca38eed54efed554d6cbd` |
| Qualification digest | `290f04311909d4b0c4b6ed77bfbfc2fceb740adea639c3049320e8bda561a6ac` |
| Admission | `admission-dedup-v1` |
| Projection digest | `fc6ddc2b1a4483363c7141805fec46300d21d0d9d50cd4a45e005fb4329af671` |
| Projection manifest | `capability_projection_manifest.39fe4a40977d0585fd570435` |

The focused proof uses two different source digests. The cold implementation is
narrow. The candidate code is parameterized. A
`CapabilityGeneralizationRecord` binds both artifacts and names the new
parameters, preserved invariants, removed assumptions, producer Loop, and
evidence.

## Functional checks

The 33 checks prove:

- seven hybrid configurations remain passive profiles under one hybrid mode;
- a cold need escalates without a false match;
- retry provenance does not change normalized need identity;
- accepted work emits a typed reference-only opportunity;
- duplicate async delivery creates one activation;
- assessment and generalization execute inside the reactive worker;
- inline and asynchronous paths call the same harvest implementation;
- low-value work stays evidence-only;
- non-code observations do not become code candidates;
- a candidate cannot enter the active projection;
- producer self-qualification and self-promotion are refused;
- qualification and promotion bind the exact artifact and contracts;
- forged projection metadata cannot hide authoritative effects;
- warm deterministic execution uses zero model calls;
- the result verifier is independent from the capability producer;
- catalog authority, projection, and artifact survive close and reopen;
- the adaptive Practitioner protocol invokes the promoted capability with zero
  model calls;
- hybrid normalization, adaptation, diagnosis, repair, and reranking stay
  bounded;
- an over-budget repair and oversized rerank are refused before a model call;
- repair creates a new candidate version;
- review can reject that candidate;
- exact duplicates consolidate;
- rollback restores only the same exact qualified version;
- deterministic projection rebuild is stable; and
- quarantine removes the version even when old projection records remain.

## Observed metrics

| Metric | Observed value |
|---|---:|
| Cold discovery model calls | 1 |
| Harvest model calls | 0 |
| Warm deterministic model calls | 0 |
| Adaptive Practitioner warm model calls | 0 |
| Hybrid normalization model calls | 1 |
| Hybrid adapter model calls | 1 |
| Hybrid diagnosis and repair model calls | 1 |
| Candidate versions created | 2 |
| Qualifications | 1 |
| Promotions | 1 |
| Duplicate consolidations | 2 |
| Evidence-only outcomes | 1 |
| Rejections | 1 |
| Rollbacks | 1 |
| Quarantines | 1 |
| State-corruption incidents | 0 |
| Producer/verifier separation violations | 0 |

Input tokens avoided, output tokens avoided, live model cost avoided, and live
latency avoided remain unknown. The injected transport does not report
provider-comparable usage or price.

## Clean wheel verification

The final wheel was built in an isolated build environment and installed in a
new Python 3.10 virtual environment outside the repository. The first clean
install exposed that Python 3.10 needed `tomli` in base dependencies. The
dependency marker was corrected, and a new wheel was built and fully retested.

| Check | Result |
|---|---|
| Import source | temporary `site-packages` |
| Required packaged resources | 4 of 4 present |
| Installed flywheel checks | 33 of 33 passed |
| Installed semantic checks | 16 of 16 passed |
| Installed full offline suite | 1,588 of 1,588 passed |
| Installed provider calls | 0 |
| Installed conformance | all gates passed |
| Wheel SHA-256 | `958af7ede3c4e76700f640ddd9de9435a4f75bf5cab757c0480cfc188bd96c31` |
| Source archive SHA-256 | `c49049b4cdd3cd8b210cb8a926b07e4da54ff622fac22b3c60bd6cffbd781abb` |

Optional data and integration adapters were not installed in the clean Python
3.10 environment. The source checkout exercised the available development
environment and repository-only checks.

## Real provider and persistent local proof, 2026-08-31

A self-contained interval-normalization task completed through the canonical
solve service with Ollama Cloud. The cold run used 10 physical model calls,
created 121 Loops, executed seven governed tool actions, passed 14 generated
tests, and returned an exact Python artifact. The accepted artifact then
entered the canonical reuse lifecycle using the explicit inline override
because the same proof immediately required the new capability.

Independent qualification ran four fixed cases, 200 generated cases, and four
invalid-input cases against the exact artifact digest. A different authority
promoted that digest. The authority catalog and search projection were stored
in SQLite, closed, reopened, and used by a later canonical solve. The warm run
completed with zero model calls and an intact 40-event Run History.

Machine-readable evidence is stored in
`artifacts/verification/real_reusable_capability_proof.json`.

This proof does not claim that public `loop-engine solve` automatically
dispatches asynchronous harvesting or discovers the persistent resolver from
settings. Those two production wiring steps remain open.

## Limitations

### Implemented but not production-proven

- Catalog restart uses local SQLite.
- Reactive scheduling uses a local SQLite scheduler and process worker.
- Code source uses the local content-addressed artifact store.
- The controlled regression fixture still uses injected transports. The new
  interval proof separately uses the production generated-project sandbox and
  real Ollama Cloud calls.

### Deferred scale and external proof

- Live provider quality and usage.
- Remote workers and remote artifact stores.
- Embedding and graph projections.
- Structural and behavioral duplicate clustering beyond the exact proof.
- Cross-session consolidation.
- Frozen-population retrieval calibration.
- Dependency vulnerability, copied-code, license, and tenant-leakage review for
  effectful generated code.
- Measured break-even count and realized savings.

The highest-value next increment is a frozen multi-task run using a real
configured provider and the approved sandbox, with persistent deployment-bound
catalog and worker configuration.
