# Per-step harness recovery

A model-using Loop can try an ordered set of registered harnesses for one
semantic step. For example, OpenCode can be the first choice, with Pi and
Codex as alternatives. The default remains one harness.

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

Harnesses remain adapters. They are not another operational runtime. Each
physical adapter attempt runs in its own canonical Spawned Practitioner Loop
with an exact registered profile. The original semantic step owns the shared
model-call authority and deadline.

## Configure an order

Use `HarnessFallbackPolicy` with `HarnessSemanticBinding`, or load exact
installed process configurations with `load_harness_fallback_binding`:

```python
from loop_engine.core.harness_fallback import HarnessFallbackPolicy, HarnessFailureKind
from loop_engine.core.harness_configuration import load_harness_fallback_binding

policy = HarnessFallbackPolicy(
    harness_ids=("opencode", "pi", "codex"),
    switch_on=(
        HarnessFailureKind.UNAVAILABLE,
        HarnessFailureKind.INCOMPATIBLE,
        HarnessFailureKind.EXECUTION_FAILED,
        HarnessFailureKind.RESPONSE_REJECTED,
    ),
)
binding = load_harness_fallback_binding(
    approved_config_paths,  # One exact absolute config path per adapter, in order.
    policy=policy,
    work_root=approved_run_directory,
    socket_directory=approved_socket_directory,
    artifact_store=run_artifact_manager,
)
# Supply binding as ModelExecution.harness under the existing model authority.
```

Every alternative must already be explicitly registered or configured. A name
does not cause installation, import, or permission discovery. Forks need their
own identity and pinned configuration. Changing a registered adapter requires
a new binding.

## What changes between attempts

Each attempt gets a fresh request identity and private workspace. The original
prompt, system context, semantic-call identity, model routes, output allowance,
and tool restrictions stay bound. The next attempt receives a small typed
failure observation and a reference to the prior attempt. It does not inherit
the previous harness's working directory or entire transcript.

Calls and tokens already used remain charged. Later attempts receive the
remaining deadline and authority, not a reset budget. Failed physical calls
remain in canonical Run History and are not counted twice through the adapter.

```text
Attempt observation
├── Admitted response
│   └── Return the proposal and stop recovery
├── Explicitly permitted harness failure
│   └── Try the next registered adapter with remaining authority
└── Shared or unresolved failure
    └── Stop for diagnosis, backoff, or reconciliation
```

Uncertain accounting, possible external effects, shared provider failures,
missing output-capacity authority, and exhausted budgets do not authorize
another harness. Generic adapter exceptions are not assumed safe to retry.
Provider failover is a separate policy. Changing a harness never silently
changes the model or provider.

An unexpected effect also blocks later invocations in the same model session.
Its reconciliation state is separate from uncertain token accounting. This
binding does not expose a reset that silently permits replay.

The current process realization is a brokered text proposal. Native harness
tools are disabled. This recovery path does not repeat file writes, API
mutations, or other host operations. Those need their own effect-specific
reconciliation and authorization.

## Check the response before handing it off

`ModelInvocationRequest.response_expectation` accepts an
`ObservationExpectation` bound to the exact invocation's
`semantic_call_id` and `exact_input_digest`. That digest covers both prompt
and system text. Bind the expectation before calling the model.

The gateway checks each response against its explicit JSON Schema. Invalid
JSON or a schema mismatch can trigger `RESPONSE_REJECTED` recovery when the
policy permits it. A schema match only admits a response. It does not establish
task correctness, authorize an effect, or promote intelligence.

An explicitly registered `HarnessResponseEvaluator` can check an admitted
response in a separate canonical Practitioner verifier Loop. The trusted host
supplies the deterministic callback, exact implementation digest,
qualification reference and digest, and evaluated response-contract identity.
Register these bindings in `ModelExecution.response_evaluators`. A request
can select an exact `response_evaluation_ref`; otherwise an unambiguous match
to the bound response contract is used. Missing, ambiguous, or incompatible
explicit bindings refuse before a model call.

The callback returns `ResponseEvaluationVerdict` with `passed`, `rejected`,
or `inconclusive` and bounded finding codes. Exceptions and malformed callback
results become inconclusive, not passing results. Every evaluation binds the
semantic-call identity, exact input digest, admitted response digest, and
verifier Loop identity in Run History. It does not accept the whole task.

To permit recovery after a semantic rejection, explicitly include
`HarnessFailureKind.SEMANTIC_REJECTED` in `HarnessFallbackPolicy.switch_on`.
The next harness receives the bounded finding codes. Inconclusive evaluation,
uncertain effects, shared provider failure, and accounting uncertainty stop
recovery. Semantic rejection is distinct from structural response rejection.

Inside one attempt, the gateway records an evaluator's verdict on the
physical attempt as `semantic_response_rejected` or
`response_evaluation_inconclusive` and stops the invocation on the route that
produced the answer. It never tries another route or provider because of a
verdict unless `ModelGatewayConfig.allow_evaluator_route_failover` is set.
That permission is separate from `allow_failover`, which governs provider
and transport failures only. Power escalation policies see the verdict codes
as distinct from `output_validation_failed`, so an escalation must name them
explicitly to react to them.

The host must independently qualify the evaluator and bind its expected
behavior to the actual task inputs. A callback declared with one parameter
receives admitted text only and remains input-blind. A callback declared with
two parameters also receives a `ResponseEvaluationContext` carrying the
semantic call identity, the exact input digest, and the evaluated subject
contract reference and digest, so a host oracle can bind its expected answer
to the actual input. A response-contract digest alone cannot prove that a
host callback checks the right input-dependent answer. Neither callback
registration nor a separate verifier Loop proves the independence or
correctness of the supplied oracle. Callbacks run as trusted host code, not
inside an untrusted-code sandbox.

General before-and-after checks for every directory scan, tool action, and
state mutation are not covered by this response evaluator. Existing action
and approval contracts still apply.

## Select the initial harness from reviewed evidence

`HarnessSemanticBinding.selection_policy` accepts an explicit
`HarnessSelectionPolicy`. This is optional. Without it, the configured
fallback order remains the initial order.

The selection operation runs in a canonical Practitioner Loop using the
registered `practitioner.code_execution` profile. Evaluation uses the
registered `practitioner.verifier` profile. These choices belong to the
existing profile hierarchy:

```text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
```

Selection first excludes unavailable adapters and adapters that cannot meet
the typed feature, isolation, or limit requirements. It considers only the
already registered alternatives. It does not install a harness, change the
provider or model, or grant access.

`HarnessSelectionScope` binds the response contract and normalization,
owning definition and role profile, resource profile, execution settings,
evaluation contract, and execution requirements. The model session derives
this scope when a bound response expectation is present, or checks an
explicit scope against the actual invocation. Resource-profile identity is a
host-supplied declaration; this selector does not inspect resource contents.

Each `HarnessTrialEvidence` needs an exact adapter version, provider and
model, matching scope, frozen population identity, evaluator identity,
subject identity, Run History references and digests, and observed counts.
`ReviewedHarnessEvidence` binds an explicit host-issued `HarnessEvidenceReview`
to the exact trial digest. Changed, rejected, or mismatched evidence cannot
determine the ranking. A policy refuses two records that cite the same Run
History reference, because one history is one trial; repeated trials of the
same subject are counted when each has its own history. These records do not
perform the independent review or fetch and authenticate the referenced
histories. The trusted host must do that before constructing the policy. A
different reviewer label alone is not proof of independent review.

The selector compares common population-and-evaluator identities across all
eligible alternatives. If any alternative lacks the policy's minimum matched
record count, selection preserves the eligible configured order. Otherwise
it ranks recorded successful observations before the selected secondary
objective, mean tokens per trial or mean elapsed time. Missing measurements
remain unknown. This is a deterministic ordering of supplied measurements,
not a calibrated quality predictor or a generalization guarantee. The host's
qualification must establish balanced trial coverage and comparable trial
sizes; matching population labels alone cannot establish those facts.

Use `load_harness_selection_policy` to read an explicitly supplied, bounded
policy file, or construct the typed policy in the host. The loader checks the
versioned shape, duplicate fields, and content digest. It does not discover
historical evidence or authorize its own measurements. The current command
line does not automatically create or enable this policy.

The
[complete configuration dimension requirement](../../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
is broader. This implementation ranks harnesses inside one fixed model route
and resource scope. It does not jointly select models, tools, skills,
instruction files, plugins, hooks, supervisors, thinking power, contracts,
or Loop usage.

## Recovery is not a candidate portfolio

Recovery stops at the first admitted response that also passes any registered
response evaluator. With no evaluator, structural admission remains the stop
condition. A portfolio deliberately keeps several candidates, even after a
valid response exists. Continued candidate
production belongs to the existing Canvas and reactive output policies.
This fallback policy does not implement a new portfolio store or select a
winner by model confidence.

Evidence-based initial selection is separate from fallback permission. A useful
comparison must include fixed-harness controls, failure rates, verified task
quality, latency, physical calls, token-accounting completeness, and unknown
costs. A recovery smoke test is not a full-system benchmark.

## Verification

`core.harness_selection.self_test()` and
`core.harness_response_evaluation.self_test()` exercise typed policy parsing,
matched and unmatched evidence, actual model-session dispatch, distinct
semantic verdicts, and permitted recovery through offline fixture adapters.
No fixture result proves a real provider integration, model quality, or an
optimal initial configuration. The earlier 70-call live configuration study
predates these selection and semantic-evaluation changes.

New fallback policies containing semantic rejection use
`harness_fallback_policy/v2`; policies without it retain their existing
encoding. Gateway results with evaluation records use
`model_gateway_result/v2`; results without them retain version 1. Evaluation
records are `harness_response_evaluation/v2`: they carry the evaluated subject
contract reference and digest and whether the callback received the
occurrence context. Records issued without a subject contract keep the
version 1 encoding. Historical results are not rewritten or silently assigned
an evaluation they never received.

`core.harness_fallback.self_test()` exercises the real Loop and gateway
contracts with a clearly labeled offline provider fixture. It covers response
rejection, unavailable and failed adapters, preserved identities, shared
accounting, stale expectations, changed registrations, and effect refusal.
It does not establish which external harness solves tasks best.

The live experiment application is
[`devtools/embodiment_lab/systematic_runtime.py`](../../../devtools/embodiment_lab/systematic_runtime.py).
Its derived reports use DuckDB exports. Canonical Run History and artifact
storage retain their existing writers and authority.

For an already configured local experiment, this command runs one new live
response-admission probe. It calls the configured provider:

```bash
PYTHONPATH=src:devtools .venv/bin/python -m embodiment_lab.systematic_runtime \
  --root /absolute/path/to/configured-study \
  --fallback-order opencode,pi,codex
```
