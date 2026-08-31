# Transactional semantic runtime evaluation

Date: 2026-08-31

## Result

The offline semantic routing slice passed 16 of 16 checks. The final source
checkout full suite passed 1,617 of 1,617 checks. The corrected Python 3.10
wheel passed 1,588 of 1,588 installed checks. Both full runs made zero provider
calls. All zero-tolerance conformance gates passed.

This is local contract and runtime evidence. The interpreter transports are
injected fixtures. It is not a live-provider quality or production reliability
result.

## Commands

```bash
PYTHONPATH=src .venv/bin/python -c '
from loop_engine.core.semantic_runtime_checks import self_test
r = self_test()
print(r["passed"], r["total"], r["all_passed"])
'

PYTHONPATH=src .venv/bin/python -m loop_engine --self-test
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src .venv/bin/python -m loop_engine --repo-conformance --format json
git diff --check
```

Focused result: `16 16 True`.

## Canonical semantic identity

| Field | Exact value |
|---|---|
| Contract | `semantic.route_claim` |
| Version | `1.0.0` |
| Semantic contract digest | `24d4578dfc61fb2535bb0bbe1258c8b7d215c340118fe085f4c9ba79c5a5de50` |
| LoopDefinition digest | `05abc160ab7133576eda84cae26957dfc813c334169011d54119d3cc302c4184` |
| Example ProgramID | `a8cedba6b9a7c39771009db773bc0f9cad1200ef69d6550933ced1bf1ed716be` |

The ProgramID includes exact contract, definition, realization, interpreter,
context, tool catalog, verification policy, and effect policy digests.

## Trust transition proof

The accepted routing case recorded:

```text
candidate
  -> structurally_valid
  -> contract_valid
  -> verified
  -> effect_authorized
  -> committed
```

The verifier and effect controller issue records that model output cannot
construct through the interpreter response. The trusted state store checks both
issuance identities, candidate and delta digests, base state version, and
idempotency key before compare-and-swap commit.

The focused tests also prove:

- an identical commit replay does not advance state;
- a stale base version is refused;
- missing facts return a verified `NEEDS_REVIEW` abstention with no commit;
- prompt-injection text inside evidence does not change the route;
- an undeclared state effect is rejected; and
- the semantic contract and execution record round-trip without identity drift.

## Interpreter requalification

The exact four-item fixture population contains two ordinary routes, one
missing-facts case, and one prompt-injection case.

| Profile | Accepted | Abstained | Rejected | False accepts | Unsafe commits | Fixture qualification |
|---|---:|---:|---:|---:|---:|---|
| `semantic.routing.fixture_a@1.0.0` | 3 | 1 | 0 | 0 | 0 | passed for this exact fixture population |
| `semantic.routing.fixture_b@2.0.0` | 2 | 1 | 1 | 0 | 0 | failed; prior profile retained |

The changed interpreter profile produces a different ProgramID. The failed
profile cannot replace the prior qualified profile. Its rollback target is
profile A digest
`850744d3fb4851f263a34b60b7070cfd85abc231686f1b30107b514e5403970b`.

Zero unsafe commits in four fixtures is an observed rate only. It is not a
statistical upper bound and does not prove the production risk budget.

## Semantic materialization

The accepted semantic procedure enters the existing Reusable Capability
Flywheel. It creates, qualifies, and promotes one deterministic Code
Intelligence realization under the unchanged semantic contract.

| Field | Exact value |
|---|---|
| Asset | `code.semantic.route_claim` |
| Version | `1.0.0` |
| Artifact digest | `a77d01be2c3af3d6d500e1232eefbf6bd0351ce0d32ac349ca938ff3ce51583e` |
| Qualification digest | `8ec1b14633cd675763282743715a576b8edc21a9694fcc14f1cf3f05fc447e23` |
| Promotion transition | `capability_transition.42fbe9fce094176f500d027a` |
| Covered region | `jurisdiction:CA` |
| Warm model calls | `0` |
| Unsupported-region fallback calls | `1` |

The candidate is not selectable before qualification and promotion. The
resolver chooses the promoted deterministic realization for California. It
returns to the qualified semantic realization for an unsupported New York
input and safely returns `NEEDS_REVIEW`.

## Strategy benchmark

The strategy record uses one routing input and injected transports.

| Strategy | Success | Model calls | False accepts | Unsafe commits | Token state | Cost state |
|---|---|---:|---:|---:|---|---|
| Direct coherent interpretation | yes | 1 | 0 | 0 | fixture values present | unknown |
| Step-by-step interpretation | yes | 3 | 0 | 0 | unknown | unknown |
| Specification to plan | yes | 1 | 0 | 0 | unknown | unknown |
| Hybrid deterministic shell | yes | 1 | 0 | 0 | fixture values present | unknown |
| Promoted deterministic reuse | yes | 0 | 0 | 0 | zero | zero in fixture |

Local millisecond values are stored in
`artifacts/verification/semantic_runtime_results.json`. They measure Python
fixture overhead and must not be used as provider latency evidence.

## Clean wheel verification

The final wheel was built in an isolated build environment and installed in a
new Python 3.10 virtual environment outside the repository. The first clean
install run exposed that Python 3.10 needed `tomli` in base dependencies. The
marker was moved into the base dependency set, the wheel was rebuilt, and the
entire installed suite was rerun.

| Check | Result |
|---|---|
| Installed import | resolved from temporary `site-packages` |
| Required packaged resources | 4 of 4 present |
| Installed flywheel checks | 33 of 33 passed |
| Installed semantic checks | 16 of 16 passed |
| Installed full offline suite | 1,588 of 1,588 passed |
| Installed provider calls | 0 |
| Installed conformance | all gates passed |
| Wheel SHA-256 | `958af7ede3c4e76700f640ddd9de9435a4f75bf5cab757c0480cfc188bd96c31` |
| Source archive SHA-256 | `c49049b4cdd3cd8b210cb8a926b07e4da54ff622fac22b3c60bd6cffbd781abb` |

Optional data and integration adapters were not installed in the clean Python
3.10 environment. The source checkout suite exercised the available full
development environment and repository-only checks.

## Remaining limits

- No live provider was called.
- The four routing cases do not establish a production reliability envelope.
- The deterministic realization is an exact local fixture, not untrusted code
  executed in the production sandbox.
- External effect approval is fail-closed but not exercised by the pure routing
  fixture.
- Model diversity, distributed state commits, tenant isolation, embedding
  retrieval, cross-session consolidation, and live economic savings remain
  unproven.

The highest-value next increment is a frozen, privacy-safe routing population
run through two real configured interpreter profiles and an independent
verifier, with enough cases to estimate false-accept, abstention, latency, and
cost bounds before enabling any production semantic profile.
