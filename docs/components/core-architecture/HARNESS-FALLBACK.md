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

## Declare wrapper layers and native control ownership

The [layered harness proposal](../../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
asks for two more configuration dimensions: which wrappers compose one
harness implementation, and who owns each native control of the harness.
`core.harness_layering` records both as passive, digested declarations that
are bound to one assignment before execution. Nothing in the module launches
a process, enables a native goal, or grants tool, effect, or spending
authority. A binding without a layering record means the direct adapter,
which is what every current recipe runs.

```python
from loop_engine.core.harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
from loop_engine.core.harness_layering import (
    CompositionFallback, ControlOwnership, LayeredHarnessBinding,
    NativeControl, NativeControlPolicy, WrapperComposition, WrapperLayer,
)

outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
preparation = WrapperLayer("instruction-prep", "1.2.0", ("instruction_preparation",),
                           inspects=("instructions",), transforms=("instructions",))
bridge = WrapperLayer("session-bridge", "0.4", ("native_session_bridge", "accounting"),
                      depends_on=("instruction-prep",))
composition = WrapperComposition("prepared-bridge", "codex", (preparation, bridge))
controls = NativeControlPolicy.owning_loop_for_everything()
binding = LayeredHarnessBinding(
    "assignment:orient-42", composition, controls,
    (CompositionFallback((HarnessFailureKind.UNAVAILABLE,), "different_harness",
                         "opencode is the registered alternative", harness_id="opencode"),),
    outer)
print(binding.content_digest)
```

A `WrapperLayer` names its identity, version, responsibilities from a closed
vocabulary, what it may inspect or transform, its settings as plain finite
JSON data (held read-only after validation, so a digest cannot be changed
underneath), and the wrappers it depends on. A `WrapperComposition` orders the layers around
one registered harness; order is part of the digest, a dependency must sit
earlier, and transport and accounting each have at most one owner because
physical calls and effects are counted once. An empty composition is the
direct adapter and the comparison baseline.

A `NativeControlPolicy` resolves every native control (goal management,
planning and continuation, tool and resource use, retry and fallback,
context and session state, steering and queued work, pause and cancellation,
completion and output publication) to `owning_loop`,
`delegated_within_authority`, `supervised_native`, `disabled`,
`unsupported`, or `unknown`. The matrix must be complete, `unsupported` and
`unknown` need a written reason, and completion can never be delegated: a
native completion claim is a candidate the owning Loop checks, never its
result.

A `LayeredHarnessBinding` checks the coordination rules against the outer
`HarnessFallbackPolicy`: several fallbacks may name one failure kind and are
its ordered alternatives, tried in the declared order by the binding as the
single decider (the same alternative at two ranks is refused); a fallback to
another harness must name an alternative the outer policy lists, for a
failure the outer policy permits; a wrapper or order fallback must differ
from the initial composition; and a native retry owner needs the outer
policy's new `allow_native_retry` permission, which is off by default
and enters the policy record only when set (`harness_fallback_policy/v3`),
so every existing policy digest is unchanged. That rule is the proposal's
requirement that a native transport retry cannot bypass an outer
semantic-recovery restriction.

A `HarnessSemanticBinding` accepts the binding as its `layering` argument.
At construction it checks that the declaration wraps the selected harness,
was checked against this binding's own fallback policy, and names only
registered alternatives, and it refuses, with the exact reason, anything no
registered executor implements: a composition with wrapper layers, a
natively owned control the adapter does not declare in its
`HarnessExecutionCapabilities.native_controls` (the message names the
unsupported controls and the adapter's declared ones), or a declared
control that no executor hands to the harness yet. The three reasons stay
distinct, so "unsupported by this adapter" is never confused with "not
implemented yet", and a declaration is never run as something else. An
adapter's declared native controls are version-bound facts, not
permissions; the tuple enters the capabilities record only when nonempty
(`harness_execution_capabilities/v2`), so existing records and digests are
unchanged, and every current recipe declares none.

At invocation the binding writes one `harness_layering_bound/v1` record with
the assignment reference, the binding digest, the composition identity, the
control policy digest, the natively owned controls, the adapter's declared
native controls, and the executor that will run, and every
`harness_attempt_assessment/v1` record carries the same digests. The
executor is always `direct_adapter` today. A binding without a layering
record reports an empty digest and the same executor, so an undeclared
attempt is distinguishable from a declared direct one.

A host can also declare the binding in a file and load it with
`load_layered_binding(path, assignment_ref=..., fallback_policy=...)` from
`core.harness_configuration`. The file holds `schema_version` 1, the
`initial` composition record, the `fallbacks` list, and the `control_policy`
record; the outer fallback policy and the assignment reference come from the
run, so a file cannot smuggle a different policy, and the same strict reading
rules as harness manifests apply (one bounded absolute regular file, no
duplicate keys, no unknown fields). The loaded binding is the validated
record itself and runs, records, and refuses exactly as a typed one.

Both dimensions are enumerable and indexable for a configuration search
through `core.harness_layering_space`. A `ControlPolicySpace` for one
adapter holds every complete control policy the adapter can honor (a
declared control may be owned by the Loop, delegated, supervised, or
disabled; an undeclared one only owned by the Loop or disabled; completion
never delegated), decodes any policy from an integer index with mixed
radix, and returns a policy's index or refuses one outside the space. A
`CompositionSpace` holds every valid ordered selection of catalogue layers
around one harness up to the depth the caller states (dependencies
earlier, single owners for transport and accounting), with the direct
adapter at index 0 and the sequences produced one at a time, so no size
ceiling is invented and a large catalogue costs time per lookup rather than
memory. A
`LayeringSpace` is their product for one assignment and yields validated
bindings by index, reporting an index inadmissible when the outer policy
would refuse it (a natively owned retry without `allow_native_retry`).
Sizes are exact: an adapter declaring nothing has 256 control policies,
one declaring every control 49,152, and a four-layer catalogue to depth
three has 20 compositions. Nothing is materialized beyond the candidate
asked for.

The records are declarations. The proposal's comparison controls
(continuation owner, retained versus fresh session, wrapper order,
concurrent native and outer retry, cancellation in flight, native counter
resets, rejected native completion, unavailable native features, and
fallback to Loop Engine control) remain the qualification work before any
executor for a layered profile is registered.

A configuration search addresses both dimensions through
`generation.layering_axes`. The control policy space and the composition
space become two `integer_range` axes of a `ConfigurationSpace`, policy
first and composition last, so a space holding only those axes assigns
every address the integer the layering space assigns it. A fixed context
field carries the layering space's digest, and a configuration addressed
in a different layering space is refused on decode rather than read
against the wrong table. Every proposal adapter (exact enumeration, seeded
exploration, warm start, and the optional Bayesian, genetic, and
covariance adapters) then proposes layering addresses alongside the other
dimensions of the search. Admissibility under the outer policy is not a
value-equality rule, so it is reported per address by
`layering_exclusions` in the same form as the space's conditional
exclusions, a lazy walk skips refused addresses while keeping their
identity, and `refuse_inadmissible_proposals` splits a proposal batch into
a separate record without altering the record the search wrote.

An enumerable address is not an executable one, and a search should know
the difference before it proposes. `core.harness_layering_availability`
projects every address of a layering space onto exactly one of five states
for one adapter, by the same rule `HarnessSemanticBinding` applies at
construction (the binding now calls it): the outer policy refuses the
address, no executor runs a layered composition, the adapter does not
declare a natively owned control, the adapter declares it but no executor
hands it over yet, or it executes now (the direct adapter under a policy
that owns or disables every control). `classify_address` returns the state
and the exact reason for one address, `availability_summary` counts the
whole space from its policies and its composition count without walking
the compositions and lists the executable addresses exactly, and
`generation.layering_axes.address_availability` answers for one
configuration. Today every executable address is the direct adapter; the
projection makes that visible instead of proposing declarations as if
they could run.

The same projection feeds the configuration setters.
`core.harness_layering_configuration` describes one assignment's layering
space as a `ConfigurationTargetSpec` with two integer settings, the
control policy index and the composition index, on a plain
`LayeringConfiguration`. Support is declared by the space, availability is
"available" when at least one address executes today and "unavailable"
otherwise, both facts cite the availability summary by its digest, and
qualification stays unknown unless the caller supplies a fact from
independent evidence. The allowed values are exactly the policies whose
direct-adapter address executes now and, for the composition, the direct
adapter alone until a wrapper executor is registered; the joined record
keeps the declared remainder visible beside the target. A setter or a
meta-selector therefore refuses the same addresses invocation would
refuse, before proposing them.

## Verification

`core.harness_layering.self_test()` proves the declarations, the order
sensitivity of the composition digest, the complete control matrix, and
each coordination rule with a fixture outer policy.
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
