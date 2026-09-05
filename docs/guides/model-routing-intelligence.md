# Model-routing intelligence

Model-routing intelligence helps a Loop decide whether it needs a model and,
when it does, which configured route satisfies the task contract. The decision
is deterministic. `ModelGateway` still owns every provider call.

The implementation is in
`loop_engine.core.model_routing_intelligence`. It adds passive records and a
bootstrap selector. It does not add a runtime, graph authority, provider plane,
or persistent intelligence layer.

## Architecture position

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Model routing sits inside the model settings branch. It does not change the
Loop role or run mode.

```text
Current Loop reaches a semantic operation
├── deterministic evidence satisfies the contract
│   └── ModelSelectionDecision: no_model_required
└── model work may be needed
    ├── ModelSelectionRequest
    ├── Model-Routing Intelligence portfolio
    ├── deterministic hard filters
    ├── evidence-aware ranking of eligible routes
    ├── ModelSelectionDecision
    └── ModelGatewayConfig
        └── ModelGateway
            └── one Loop identity for each physical provider attempt
```

The portfolio identity is
`core.intelligence_portfolio.model_routing@1`. Its search scope is the existing
four-layer catalog:

```text
Model-Routing Intelligence portfolio
├── Context Intelligence
│   └── provider documentation, model cards, licenses, and declared limits
├── Code Intelligence
│   └── adapters, endpoint handshakes, parsers, and repair procedures
├── Runtime History and Solution Intelligence
│   └── exact attempts, bounded benchmarks, failures, latency, and cost
└── User Feedback Intelligence
    └── scoped preferences and organization guidance
```

Current availability is supplied as a runtime snapshot. It is not written to a
fifth layer.

## Records have different jobs

| Record | Question it answers | Persistence boundary |
|---|---|---|
| `ModelCapabilityRecord` | What does this exact deployment technically support? | Reviewed record in an existing intelligence layer |
| `ModelSuitabilityRecord` | How did this route perform for this bounded task population? | Reviewed Runtime History and Solution Intelligence generalization |
| `ModelRouteAvailabilitySnapshot` | Is the exact route usable now? | Runtime Memory or another current runtime snapshot |
| `ModelSelectionRequest` | What does this Loop need, and what does policy permit? | One run |
| `ModelSelectionDecision` | Which hard constraints passed, which routes were rejected, and which route was selected? | Run History candidate payload |
| `ModelOutcomeEvidence` | What happened during the later gateway attempt? | Run History, with raw prompts and reasoning absent |
| `ModelRoutingLearningCandidate` | What scoped routing rule should an independent reviewer consider? | Candidate storage until review |

A provider claim can populate a source-backed capability record. It does not
prove task suitability. A successful health probe proves current availability,
not quality. One successful run is Run History evidence, not a reusable routing
rule.

## Selection order

`ModelRouteBootstrapSelector` applies hard constraints to every route before it
calculates a rank. A failed route is kept in `rejected_routes` with named
reasons.

Hard checks cover:

- run mode and route purpose;
- route and provider allowlists and denylists;
- the authority intersection between `ModelSelectionRequest` and
  `RuntimeSettings`;
- route, provider, model, locality, revision, and deployment identity;
- reviewed capability status and validity dates;
- operator, response topology, modality, tools, structured output, context,
  and output limits;
- fresh availability, endpoint health, model state, and credential state;
- cost ceilings and measured reliability targets;
- task-scoped, current suitability evidence.

Only eligible routes receive a score. The decision retains each contribution:
measured success, schema validity, verification pass rate, stability, evidence
confidence, latency fit, cost fit, locality preference, provider preference,
thinking-power fit, and counterevidence. These values break ties among valid
routes. They do not grant permission.

## Deterministic work comes first

Set `deterministic_sufficient=True` only when the request includes a typed
deterministic procedure or another evidence reference. The selector then
returns `no_model_required` without inspecting or calling a provider.

```python
from loop_engine.core.model_routing_intelligence import ModelSelectionRequest

request = ModelSelectionRequest(
    request_id="selection.validate-customer-import",
    run_id="run.customer-import",
    loop_id="loop.validate",
    role="solution",
    profile="solution.validator",
    run_mode="deterministic",
    compiled_task_ref="task:customer-import/v1",
    task_fingerprint="known-schema-validation/v1",
    operator="validate",
    response_topology="report",
    output_contract="schema:validation-report/v1",
    model_purpose="decide_label",
    deterministic_sufficient=True,
    deterministic_evidence_refs=("procedure:json-schema-validator/v1",),
)
```

The request stores an evidence reference, not a prose claim that deterministic
work is probably enough.

## Local-only selection

Use `allowed_localities=("local",)` for local-only data. A cloud route fails
the locality hard check even when a preference names that cloud provider.
Preferences cannot broaden policy.

The selector performs no health probe and no model call. Supply a fresh
`ModelRouteAvailabilitySnapshot` from an authorized probe before selection.
If the local endpoint is unavailable, the selector abstains. It does not send
the task to a cloud route.

A local Qwen deployment uses the same path as every other custom endpoint:

```text
CustomEndpoint
├── exact endpoint and model identity
├── ProviderSpec
├── ModelRoute
├── reviewed ModelCapabilityRecord
├── fresh ModelRouteAvailabilitySnapshot
└── ModelRouteBootstrapSelector
    └── ModelSelectionDecision
        └── ModelGateway
```

There is no Qwen-specific selector. Do not copy a context or output limit from
a family name. Record the exact deployment's source-backed capability.

Read [Custom model endpoints](custom-endpoints.md) for endpoint configuration.

## Staleness and negative transfer

A suitability record is eligible only when its selector matches the current
task fingerprint, operator, response topology, domain, profile, consequence,
modality, context range, and output range. The record can also pin the model
revision, deployment digest, and capability-record digest.

A revision or deployment change makes the old suitability record inapplicable.
Evidence for short record classification cannot select that route for a large
repository architecture task. When policy requires suitability and no scoped
record survives, the selector abstains.

## Gateway handoff

Create the selector from the existing gateway so both use the same provider and
route inventory:

```python
from loop_engine.core.model_routing_intelligence import (
    ModelRouteBootstrapSelector,
)

selector = ModelRouteBootstrapSelector.from_gateway(
    gateway,
    capability_records=capability_records,
    suitability_records=suitability_records,
    availability_snapshots=availability_snapshots,
    settings=runtime_settings,
)
decision = selector.select(selection_request)

if decision.status == "selected":
    gateway_config = decision.to_gateway_config()
```

The canonical governed entrypoint wraps that deterministic selector in a Loop
and records the request, rejections, selection, and completed decision:

```python
from loop_engine.core.model_routing_intelligence import (
    ModelSelectionLoopContext,
    select_model_as_loop,
)

selection_run = select_model_as_loop(
    selector,
    selection_request,
    context=ModelSelectionLoopContext(parent=current_loop),
)
decision = selection_run["decision"]
```

This handoff still needs the caller to create a `ModelGatewayRequest`, invoke
`ModelGateway`, validate the result, and record `ModelOutcomeEvidence`. The
bootstrap selector never invokes the gateway itself.

## Learning boundary

`ModelRoutingLearningCandidate` remains candidate-only. An approved candidate
needs a reviewer Loop identity different from the producer Loop identity and a
rollback instruction. Promotion into active Learned intelligence belongs to
the existing candidate-review lifecycle.

Raw prompt text, response text, and private reasoning are absent from
`ModelOutcomeEvidence`. Missing token usage remains `None`, not zero.

## Verification

Run the installed-package contract checks:

```bash
PYTHONPATH=src python3 -c \
  'from loop_engine.core.model_routing_intelligence import self_test; print(self_test())'
```

Run the frozen source-tree benchmark:

```bash
PYTHONPATH=src python3 -m \
  loop_engine.core.model_routing_intelligence_checks \
  benchmarks/model-routing/frozen-bootstrap-cases-v1.json
```

The benchmark uses synthetic routes and adapters that raise if called. It
proves selector contracts only. It does not prove a live provider, the quality
of any model, a local Qwen deployment, automatic portfolio retrieval, Run
History integration, or Studio playback.

The current selector is a deterministic bootstrap for hard eligibility and
evidence-aware ordering. It does not implement model-led stage allocation,
expose retrieved stage candidates to an allocating model, change the adaptive
solve route automatically, or prove that a cheaper route preserves quality.
