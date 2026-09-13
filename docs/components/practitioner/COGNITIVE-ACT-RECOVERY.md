# Cognitive-act recovery and candidate learning

Loop Engine can check a model response before handing it to another step,
diagnose repeated work, and capture a conditional recovery lesson for review.
These operations use the existing Loop runtime and model authority. They do
not establish general intelligence or autonomous improvement across tasks.

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

A custom cognitive body is a Loop configuration or adapter. It is not a new
Node class. Native gateway execution, a registered custom harness, a single
external harness, and a configured multi-harness recovery order remain
available. Within this workflow, model-using assignments share one `ModelExecutionSession`.
An external harness gets its own confined process workspace per attempt.

The relevant profiles remain branches of the existing roles:

```text
Loop role profiles used by this workflow
├── Practitioner
│   ├── practitioner.reference_nine_step@1.0.0
│   ├── practitioner.solver@1.0.0
│   └── practitioner.self_improvement@1.0.0
├── Intelligence
│   └── intelligence.context.serve@1.0.0
└── Solution
    └── solution.validator@1.0.0
```

## Check before handing off

`ModelResponseContract` is a passive, versioned schema and normalization
policy. It is separate from the example text that helps a model understand
the desired output. Example prose never becomes executable authority.

`ModelStepRequest.admission_contract` binds that contract to the final prompt
and semantic-call identity. The existing deterministic Solution validator
checks the response before the model session returns it to a consumer.

The action decision, execution method, and recovery-panel responses have
explicit contracts. A method must address the selected action and cannot
select a capability outside that action. Permissions, dependency bindings,
effect approval, and independent task verification still have their own
checks. Passing the response schema does not pass those later checks.

The current adaptive planner needs an execution capability for non-control
actions. Its action contract checks that prerequisite before asking a model
to produce a method. An empty capability list for composition cannot enter an
impossible method-repair cycle. This is an implementation constraint of this
planner, not a rule forbidding other custom Loop bodies from composing graphs.

Meaning-preserving normalization is explicit. The existing admission policy
can remove an exact JSON fence, an approved presentation preamble, or one
JSON-string encoding layer. It cannot invent a missing field, change a value,
accept duplicate keys, or execute model text.

A rejected response is not a failed network connection. Its exact digest and
safe schema diagnostics enter the next repair packet. Required field names
are disclosed only when the contract's policy enables that feedback. Candidate
values and unexpected property names are not copied into these diagnostics.

## Orient from observable progress

The progress projection ignores changing pass IDs, stage IDs, confidence,
estimated utility, and rewritten explanations. It compares source and web
evidence, project identities, artifact values, issued host observations, and
executable action inputs. It is not an acceptance check or a result-cache key.

An exact repeat, including a non-adjacent action cycle, requests diagnosis.
The optional `diagnose_unchanged_evidence` setting also requests diagnosis
when a different action produces no new material evidence. It reports that
the action changed, so the model can distinguish exploration from repetition.
It does not impose a task-call ceiling or choose a terminal route.

When that option is enabled, an exhausted action or method response-repair
cycle can also enter the recovery panel before execution. The signal records
that the action did not run. Failure of the panel is recorded once, without
recursively asking it to recover itself.

The existing recovery panel performs three model-using assignments:

```text
Recovery assignments within the Practitioner workflow
├── Diagnose the observed stall
├── Propose distinct changed strategies
└── Adjudicate one offered strategy
```

The selected directive returns to the normal action, permission, and execution
checks. A changed plan is not evidence that the recovery worked. Task outcomes
and independent verification remain separate.

## Capture without self-promotion

`capture_recovery_learning` enables an additional small assignment owned by
`practitioner.self_improvement@1.0.0`. It receives the observed stall and the
selected recovery directive, rather than the entire run transcript. It uses
the existing model session and its selected harness configuration.

The assignment chooses an explicit disposition:

```text
Recovery learning disposition
├── ephemeral_task_only
│   └── Record why no reusable candidate is justified
└── requires_validation
    └── Retain a candidate with applicability and contraindications
```

The result uses the existing `LearningCandidate` and `LearningBundle` records.
The canonical artifact store retains the bundle, and Run History records
body-free source and result references. The bundle remains run-local staging.
It is not added to selected intelligence and cannot approve or promote itself.

Even a well-formed candidate can be wrong. The source recovery is still a
proposal when this capture runs. Independent review, fresh-task benefit, and
negative-transfer checks are required before claiming useful learning.

## Enable the optional behavior

The public Python request keeps diagnosis and learning capture separate:

```python
request = SolveRequest(
    intake,
    model_execution=authorized_model_execution,
    host_runtime=approved_host,
    diagnose_unchanged_evidence=True,
    capture_recovery_learning=True,
)
outcome = solve_task(request)
```

Both settings default to false. Neither grants a provider route, spending,
tools, filesystem access, or intelligence promotion. The configured model
authority still applies to every recovery and capture call. The current
learning-capture implementation requires a model-using mode.

The [harness recovery policy](../core-architecture/HARNESS-FALLBACK.md) controls
whether another registered harness may try the same cognitive assignment.
It preserves budgets and stops for unresolved accounting or effects. Collecting
multiple successful candidates remains a separate portfolio policy.

## Verification scope

Offline checks cover response repair through the actual Practitioner path,
method-to-action binding, metadata-insensitive progress signals, candidate
capture, persistence, and non-promotion. Live task results are reported
separately. A fresh query set on a previously attempted task is not a new
unseen task, and an accepted learning bundle is not evidence of AGI.
