# Model-routing verification report

Date: 2026-08-27

Starting main revision: `6a26978c5e6cd2e3852818c4bb4b2dac23b0da76`

## Verdict

The bounded Model-Routing Intelligence bootstrap selector is verified offline.
Live provider routing and model-quality claims remain unproven.

No core architecture change was required. The slice uses the existing `Loop`,
`ModelGateway`, `ProviderSpec`, `ModelRoute`, `ModelGatewayConfig`, and
`RuntimeSettings` contracts.

## Implemented scope

```text
Model-routing vertical slice
├── passive records
│   ├── ModelCapabilityRecord
│   ├── ModelSuitabilityRecord
│   ├── ModelRouteAvailabilitySnapshot
│   ├── ModelSelectionRequest
│   ├── ModelSelectionDecision
│   ├── ModelOutcomeEvidence
│   └── ModelRoutingLearningCandidate
├── portfolio definition
│   └── core.intelligence_portfolio.model_routing@1
├── deterministic bootstrap selector
│   ├── no-model decision
│   ├── hard filtering before ranking
│   ├── explainable score contributions
│   ├── same-tier failover plan
│   ├── separate escalation plan
│   └── explicit abstention
└── safeguards
    ├── local-only locality enforcement
    ├── role-independent route eligibility
    ├── exact model and deployment identity
    ├── stale evidence rejection
    ├── negative-transfer rejection
    ├── unknown usage preservation
    └── independent candidate review
```

Capability, suitability, and availability remain separate. The portfolio uses
the four existing intelligence layers. Availability remains a current runtime
snapshot, not persistent intelligence.

## Verification commands

```bash
python3 -m py_compile \
  src/loop_engine/core/model_routing_intelligence.py \
  src/loop_engine/core/model_routing_intelligence_checks.py
```

Result: passed.

```bash
PYTHONPATH=src python3 -c \
  'import json; from loop_engine.core.model_routing_intelligence import self_test; print(json.dumps(self_test(), indent=2))'
```

Result: 14 of 14 checks passed. Provider calls: 0.

```bash
PYTHONPATH=src python3 -m \
  loop_engine.core.model_routing_intelligence_checks \
  benchmarks/model-routing/frozen-bootstrap-cases-v1.json
```

Result: 14 of 14 frozen cases passed. Provider calls: 0.

Frozen fixture SHA-256:
`11d77de37bc75e113583fde4cbd14035f6237fbceeb84ce761f7963dcb712ef6`.

## What the evidence proves

- A source-backed deterministic procedure can produce
  `no_model_required`.
- Hard policy and capability checks run before ranking.
- A local-only request excludes every cloud route even when a cloud provider
  is preferred.
- Equivalent bounded requests from Practitioner, Intelligence, and Solution
  roles receive the same route decision.
- A short-classification suitability record does not transfer to a repository
  architecture task.
- A changed deployment digest invalidates the old suitability record.
- A stale runtime availability snapshot makes its route ineligible.
- A selected decision maps into the current `ModelGatewayConfig` contract.
- Model selection has its own governed Loop identity and canonical events.
- Bootstrap selection calls no provider adapter.
- Missing usage remains unknown.
- A producer Loop cannot approve its own routing candidate.

## What remains unproven

- No live local, organization, subscription, or cloud provider was called.
- No Qwen deployment was installed or measured.
- The synthetic suitability values do not measure model quality.
- The portfolio definition is not yet wired to automatic four-layer retrieval.
- Model selection and outcome records are not yet emitted into Run History.
- Studio does not yet display these records.
- The public CLI does not yet expose model inventory, explain, or benchmark
  commands.
- No held-out routing-regret campaign has run.

Those items need shared-file integration or authorized external providers. The
offline result must not be promoted into a live-integration claim.

## Shared integration hooks

The focused module is importable through its full path. The following shared
surfaces still need an owning change:

1. Export reviewed public symbols through `loop_engine.core` and the top-level
   package.
2. Add `self_test()` to the canonical package self-test registry.
3. Query the portfolio through the existing Intelligence Search and Retrieval
   path and save an exact portfolio snapshot reference.
4. Emit selection, rejection, failover, escalation, outcome, and learning
   events through the existing Run History vocabulary.
5. Add Studio projections for model selection and model attempts.
6. Add CLI explain and benchmark commands that remain non-executing unless the
   user gives separate provider-call authority.

None of those hooks requires another runtime or model gateway.
