# Spawned Loop delegation

A Spawned task is still a Loop. `SpawnedTaskManager` adds task controls around the
existing Loop runtime. It does not create a second agent or execution engine.

```text
Spawning Loop, with any role
├── Spawned Practitioner
├── Spawned Intelligence
└── Spawned Solution
```

The manager derives a `LoopRoleIdentity` from the selected profile and a
`LoopRelationship.spawned_by(...)` value from the spawning Loop ID. Callers do
not provide a separate role label that could contradict the profile.

Every Spawned Loop starts through `Loop.spawn()`. This keeps the existing rules:

- the spawning Loop must have authority to delegate the requested run mode;
- recursion depth remains bounded;
- the Spawned Loop receives its own Loop profile and contract;
- the Spawned Loop cannot pass on more mode authority than its spawning Loop
  granted;
- the manager records both Loops in the same event history without exposing
  that ledger to the Spawned Loop executor;
- every Spawned Loop must reach a terminal state.

## The delegation object

`DelegationSpec` groups the complete Spawned Loop request in one object. Callers do not
pass a long list of loosely related arguments to `start()`.

| Field | Meaning |
|---|---|
| `goal` | The bounded work assigned to the Spawned Loop. |
| `profile` | An exact, versioned `LoopProfileRef`. |
| `contract` | The existing `LoopContract` with input and output roles. |
| `inputs` | Immutable `LoopPortValue` objects bound to input roles. |
| `mode` | Deterministic, hybrid, or non-deterministic. |
| `budget` | Iteration, model-call, update, output, and optional asynchronous wall-time ceilings. |
| `context` | The context that the Spawned Loop may see and return. |
| `workspace_policy_ref` | An opaque reference to a workspace policy. |
| `return_destination` | Spawning Loop context, shared Runtime Memory, or the caller. |
| `constraints` | Required fields, capabilities, and allowed effects. |
| `delegated_modes` | Modes that this Spawned Loop may pass to Loops it spawns. |
| `llm_thinking_power` | Model tier for hybrid or non-deterministic work. |

The returned `SpawnedTaskSnapshot` exposes the derived identity and
relationship. Profile aliases keep common Spawned Loop requests concise:

- Practitioner: `researcher`, `solver`, `verifier`
- Intelligence: `intelligence.search`, `intelligence.materialize`,
  `intelligence.invoke`, `intelligence.replay`, `intelligence.interpret`
- Solution: `solution.component`, `solution.validator`, `solution.router`,
  `solution.fallback`, `solution.ensemble`

Aliases select profiles only. The same profile can also be used by a Starting,
Queried, Retrieved, or Connected Loop when its contract allows that
relationship.

The workspace field is a reference only. This module does not create a
workspace, run a shell, or interpret workspace permissions.

## Private context by default

The default `ContextVisibilityPolicy` starts the Spawned Loop with a fresh
context. It passes no spawning Loop references and does not share Runtime
Memory. The Spawned Loop returns only its typed output and a short summary.

`SpawnedExecutionRequest` has no public `Loop` field. Its `runtime` field is a
`SpawnedLoopRuntimePort` with this public surface:

```text
SpawnedExecutionRequest
├── task ID, Spawned Loop spec, and task control
├── SpawnedLoopRuntimePort
│   ├── LoopRoleIdentity and LoopRelationship
│   ├── immutable SpawnedLoopRuntimeConfigFacts
│   ├── safe SpawnedLoopRuntimeCounters
│   └── bounded run and cancel operations
└── optional SpawnedLoopRuntimeMemoryPort
```

A custom step handler receives `SpawnedStepRequest`, not the internal Spawned
`Loop`. The public request and runtime port therefore have no route to
the spawning Loop goal, the shared ledger, event history, or the spawning Loop
object. This is a Python public-contract boundary, not a sandbox against
arbitrary reflection.
Run untrusted executor code in an isolated process with filesystem, network,
credential, and resource controls.

The public result has no fields for:

- the Spawned Loop object;
- prompt or message history;
- event history;
- raw tool output;
- filesystem contents.

These details can remain in the executor and Run History for authorized review.
Changing the context policy does not make raw internals part of the public
result.

## Start a deterministic Spawned Loop

```python
from loop_engine.loop.delegation_runtime import (
    SpawnedExecutionRequest,
    SpawnedLoopResult,
    SpawnedStepRequest,
    SpawnedTaskManager,
    SpawnedTaskStatus,
    DelegationConstraints,
    DelegationSpec,
    LoopPortValue,
)
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_profile_catalog import LoopProfileRef
from loop_engine.loop.recursive_loop import Loop, LoopConfig
from loop_engine.loop.recursive_loop import StepOutcome

spawning_loop = Loop(
    "prepare customer data",
    LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
    ),
)

spec = DelegationSpec(
    goal="normalize one customer row",
    profile=LoopProfileRef("solution.atomic_component"),
    contract=LoopContract(
        "normalize-row",
        "code_only",
        input_roles=("raw_row/v1",),
        output_roles=("clean_row/v1",),
    ),
    inputs=(LoopPortValue("raw_row/v1", {"name": " Ada "}),),
    constraints=DelegationConstraints(
        available_fields=("operation_ref",),
        capability_refs=("solution_canvas", "component_execution"),
    ),
)

def normalize(request: SpawnedExecutionRequest) -> SpawnedLoopResult:
    row = request.spec.inputs[0].value
    loop_result = request.runtime.run(
        handler=lambda step: StepOutcome(
            output=f"{step.step}:normalized", mode="deterministic"))
    return SpawnedLoopResult(
        task_id=request.task_id,
        status=SpawnedTaskStatus.SUCCEEDED,
        outputs=(LoopPortValue(
            "clean_row/v1", {"name": row["name"].strip()}),),
        summary="Removed surrounding whitespace from the customer name.",
        terminal_code=loop_result.counters.terminal_code,
        steps_run=loop_result.counters.steps_run,
    )

manager = SpawnedTaskManager(spawning_loop, normalize)
task_id = manager.start(spec)
task = manager.status(task_id)

assert task.result is not None
assert task.result.outputs[0].role == "clean_row/v1"
assert task.result.outputs[0].value == {"name": "Ada"}
```

The example executor performs real bounded work and advances the supplied Spawned Loop
through its runtime port. The built-in executor is a lifecycle smoke path for one deterministic
output role. Structured work, hybrid work, and non-deterministic work use an
injected executor.

## Explicit Runtime Memory service

Runtime Memory is absent from a default request. Setting
`context.shared_runtime_memory=True` is not sufficient by itself. The manager
must also receive a typed service:

```python
manager = SpawnedTaskManager(
    starting_loop,
    executor,
    runtime_memory=run_note_board,
)
```

The executor then receives `request.runtime_memory`, a Spawned Loop-bound
`SpawnedLoopRuntimeMemoryPort` with `write`, `read`, and `search`. It does not receive
the service's ledger or the spawning Loop's ledger. A shared-memory request
without the service fails before spawning a Loop.

## Optional large-text input offload

`SpawnedTaskManager` can receive the existing typed `ContextArtifactManager`:

```python
manager = SpawnedTaskManager(
    starting_loop,
    executor,
    context_artifacts=context_artifact_manager,
)
```

For a fresh Spawned Loop, text input ports are evaluated by that manager's deterministic
offload policy. Large text is stored through the configured existing artifact
store and replaced by a `ContextArtifactRef` before the executor sees the
request. Small text and non-text values keep their exact original types and
values inline. Delegation creates no second artifact store and never gives the
executor the store object.

## Lifecycle operations

The manager has one small lifecycle surface:

- `start(spec)` runs a synchronous executor;
- `start_async(spec)` schedules an asynchronous executor;
- `status(task_id)` returns one safe snapshot;
- `update(task_id, update)` adds typed inputs or an instruction;
- `cancel(task_id)` closes an active Spawned Loop;
- `list()` returns safe snapshots in creation order;
- `wait(task_id)` waits for one asynchronous Spawned Loop;
- `wait_all(..., timeout_seconds=...)` waits within a required join bound and
  cancels work still active at that bound;
- `join(...)` is the same bounded ordered join operation;
- `checkpoint(task_id)` and `checkpoints()` serialize lifecycle state; and
- `restore_checkpoint(...)` or `restore_checkpoint_json(...)` restores durable
  terminal metadata.

`SpawnedTaskStatus` is a closed enum with queued, running, succeeded, failed,
canceled, and interrupted states. A task cannot be updated after it reaches a
terminal state.

An asynchronous executor is still a Spawned Loop executor. It does not gain a
different authority model. A caller can launch several spawned Loops through an
event loop and observe each Spawned Loop through the same manager.

When `DelegationBudget.wall_time_seconds` is set, the manager applies that bound
around the asynchronous executor await. A timeout cancels executor work, closes
the Spawned Loop, and publishes `FAILED` with `DEADLINE_EXCEEDED`. A synchronous Python
call cannot be forcibly stopped safely in-process, so the wall-time field is an
asynchronous executor boundary. Use a process sandbox for untrusted or blocking
synchronous work.

## Durable Spawned Loop checkpoints

`SpawnedTaskCheckpoint` uses schema `spawned_task_checkpoint/v2` and binds its body
to `checkpoint_digest`.

```text
SpawnedTaskCheckpoint
├── identity and specification
│   ├── task ID
│   ├── complete typed DelegationSpec
│   ├── LoopRoleIdentity
│   └── LoopRelationship with a spawning Loop ID
├── lifecycle metadata
│   ├── status and update count
│   └── step and model-call counters
└── terminal result
    ├── typed output ports and summary
    └── terminal code, error code, and error
```

The JSON form contains no `Loop`, ledger, coroutine, task object, workspace, or
executor. Schema version, known fields, typed nested contracts, state/result
consistency, budgets, and the digest all fail closed.

Restoring a succeeded, failed, canceled, or interrupted checkpoint preserves
its exact terminal result. Restoring a queued or running checkpoint does not
pretend that Python resumed a coroutine. It creates an `INTERRUPTED` terminal
result with `INTERRUPTED_ON_RESTORE`, while preserving the task ID, role
relationship, update count, completed-step count, model-call count, and error
metadata. Restored terminal tasks have no live Spawned Loop and therefore create no
orphan.

## What the manager checks

The manager checks the request before it creates a Spawned Loop:

1. The spawning Loop can delegate the selected mode.
2. The Loop contract mode matches the selected mode.
3. The profile is registered and allows the mode.
4. Required profile fields and capabilities are present.
5. Contract effects fit the delegation constraints.
6. Any authority passed to another Spawned Loop fits the spawning Loop's
   authority.

It checks the result before it publishes it:

1. The Spawned Loop reached a terminal state.
2. The executor returned the correct task identifier.
3. Successful output roles exactly match the Loop contract.
4. Required summary policy is satisfied.
5. Iteration, model-call, and output ceilings were not exceeded.
6. Asynchronous wall time did not exceed the declared deadline.

These checks do not prove that a concrete value is semantically correct. Use a
versioned `ContractDefinition` and an independent evaluator for that decision.

## Current boundary

The manager enforces output and call counts after an executor returns and
enforces the optional wall-time deadline around asynchronous executor work. A
workspace or provider adapter must still enforce network access, filesystem
access, spend, process resources, and blocking synchronous wall time while work
is running. The workspace policy reference lets that adapter resolve the correct
policy without coupling delegation to one sandbox product.

Run the focused offline checks:

```bash
PYTHONPATH=src python -c \
  "from loop_engine.loop.delegation_runtime import self_test; print(self_test())"
```
