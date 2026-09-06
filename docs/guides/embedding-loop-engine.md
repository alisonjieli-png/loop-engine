# Use Loop Engine inside another project

An application can use Loop Engine to reason over its own operations and
verification rules. Pass a `HostRuntimeBinding` to `SolveRequest`. The Loop
selects registered capabilities, consumes their observations, and continues
until the host confirms task completion or the run returns an honest blocker.

This is a Python embedding API with synchronous callbacks. It does not require
an empty host workspace or a generated Python project. It does not install a
remote host, create a TypeScript SDK, or supply Git and deployment policies
automatically.

## One runtime, different execution environments

```text
Operational runtime type
└── Loop
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
    ├── Role: Practitioner, Intelligence, Solution
    ├── Versioned role profile
    ├── Mode: deterministic, hybrid, non-deterministic
    ├── Step profile and typed input/output contract
    ├── Loop condition and exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when authorized
    └── Run History

Starting Practitioner
├── reasons over the task and registered capability contracts
├── invokes selected host capabilities through Code Intelligence Loops
├── receives observations and failures
├── uses a separate Practitioner verifier with host-owned gates
└── returns the verified host result or continues the same task
```

The built-in generated-project capability remains a Python execution profile.
A host capability does not pass through `GeneratedProjectCommand`, so its
operations can use another language, a database, an existing service, or a
different execution environment. The host must implement and authorize those
operations. No domain label selects a special Loop runtime.

## Call the public API

```python
from loop_engine import HostRuntimeBinding, SolveRequest, solve_task
from loop_engine.code_nodes.solution_model_port import ModelExecution
from loop_engine.templates.intake import TaskIntakeRequest, intake_task


def solve_for_host(
    task: str,
    host: HostRuntimeBinding,
    model: ModelExecution,
    runs_dir: str,
):
    return solve_task(SolveRequest(
        intake=intake_task(TaskIntakeRequest(text=task)),
        host_runtime=host,
        model_execution=model,
        runs_dir=runs_dir,
        interaction_mode="autonomous",
    ))
```

The [complete JavaScript example](../../examples/25_host_runtime/README.md)
constructs a host binding, exposes an existing source file, applies a
digest-checked replacement, and runs fixed `npm test` gates in Docker. It does
not give the model permission to change the test files.

`autonomous` controls clarification behavior. It is not a grant of file,
network, model, spending, or deployment authority. The example explicitly
authorizes model calls and sharing its fixture source with the model.

## What the host supplies

Use the existing `CapabilityDirectory` and `CapabilityHandshake` to register
endpoints. A `HostOperationBinding` selects one registered endpoint and adds
the actual JSON input/output schemas, exact-effect builder, implementation
reference, and scoped permission names.

| Binding field | Responsibility |
|---|---|
| `directory` | Existing registry of explicitly installed endpoints. Discovery does not invoke them. |
| `operations` | Operations available for model selection. Each has an exact schema and registration identity. |
| `verifier` | Separate, pre-registered host verification endpoint. It is not offered as a model-selectable tool. |
| `authorize` | Trusted callback receiving an exact `ApprovalRequest` and returning an `ApprovalDecision`. |
| `snapshot` | Trusted host read returning the SHA-256 identity of the current subject, including relevant gate and dependency state. |
| `scope_ref` | Stable identity of the host-controlled resource scope. |
| `share_outputs_with_model` | Explicit disclosure grant. This model-visible adapter requires literal `True`; omission refuses construction. |

Handshake schema names describe ports; they are not validators. The host
binding's JSON Schemas validate actual values. Schemas must be self-contained.
The handshake must declare a positive response-byte allowance. For larger
results, return bounded metadata and references through the host's data tools.

Callbacks receive a `HostInvocation` containing arguments, scope, current
state reference, and a unique physical invocation ID. They do not receive a
writable reference to the original task or an approval decision from the model.
The host must check state preconditions atomically when it performs an effect.

## Permissions remain scoped

A host operation may declare `permission_names=("source_read",)` or another
application vocabulary. That declaration permits the corresponding request
to reach the host authorizer. It does not approve the effect or enable the
engine's core source reader.

Core, mixed, and capability-free requests keep their normal core permission
checks. A host-only request is checked against the selected host operations.
Exact invocation, arguments, scope, state, and registration digests are bound
into the approval. Changed arguments or state require another decision.

Host callbacks are trusted application code. The embedding API does not
sandbox arbitrary Python callbacks, authenticate an application merely from
an actor-name string, or remove secrets from arbitrary host output. Keep
credentials out of responses. Use the host's existing confinement, authorization,
privacy, and audit mechanisms inside its adapters.

## Verification and results

The host verifier receives the original task, exact host result, and current
state reference. It returns explicit fields:

```json
{
  "passed": true,
  "task_complete": false,
  "observations": {"checked": "one valid intermediate observation"},
  "notes": "The observation is valid; further work is required."
}
```

`passed` and `task_complete` are different. Valid intermediate observations
may support another pass. Final success requires an issued, matching report
that confirms completion against the current host state. The model cannot
replace that report by declaring success.

Inspect `SolveOutcome.terminal_code`, `solved`, `result`, and `verification`.
A host result uses `host_operation_result/v1`, not a fabricated project
manifest. Its `value` follows the host's schema and need not be a file. Do not
assume that `workspace` or the built-in generated-artifact list represents
the host's repository, database, or deployment.

Snapshots are host attestations. The engine checks their identities and
freshness; the host is responsible for what the snapshot covers and whether
its verifier genuinely checks the contract. A passing repository suite is
useful evidence, not proof that all possible inputs are correct.

## Failures and retries

Host invocation pins the selected handshake and callable. It disables implicit
directory fallback, including fallback installed while an endpoint is running.
The existing action fence uses arguments, binding identity, and the last
observed host state; a changed observation is distinct from an identical retry.

An unknown effect outcome is not a failure that may be replayed freely. The
engine records it and refuses further mutation in that scope until it can be
reconciled. Version 1 does not provide automatic reconciliation or cross-process
exactly-once execution. Host transport adapters must preserve invocation IDs
and their own durable idempotency and recovery rules.

## Generalization and adoption checks

The same interface can describe these host responsibilities. Only the linked
repository example is demonstrated by this change; the other rows are possible
bindings, not completed integrations.

| Environment | Possible host operations | Host-owned acceptance |
|---|---|---|
| Existing repository | Inspect, patch, execute, produce diff or branch metadata | Fixed repository tests and policy checks |
| Data system | Query records, transform data, materialize snapshots | Schema, integrity, and held-out metric checks |
| Research environment | Retrieve sources, extract claims, assemble an answer | Source support and claim verification |
| Simulation | Observe state, propose actions, run experiments | Invariants and measured outcomes |

Before adopting a host adapter, prove denied authority, stale snapshots, failed
gates, changed registrations, malformed outputs, and interrupted effects as
well as success. A task added after interface development should need only
task information, host capabilities, and verification configuration, not a
domain branch in the core.

Do not count fixture responses, renamed examples, metadata downloads, or local
cross-validation as unseen-task or external-grading evidence. Freeze a mixed
task population and its evaluators, run the public path, and preserve failures
and exclusions. This API removes one architectural constraint; it does not
establish general AGI or broad unseen-task performance.
