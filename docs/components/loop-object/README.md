# The Loop object and step profiles

The `Loop` is the shared runtime object in Loop Engine. Each operational node
is a loop. A loop can perform work itself or start another loop for a bounded
part of the task.

## What defines one loop

| Setting | Purpose |
|---|---|
| Goal | States the work to complete. |
| Contract | Defines accepted inputs, outputs, and effects. |
| Allowed modes | Limits how the loop may perform its work. |
| Preferred modes | Sets the order in which allowed modes are tried. |
| Delegated modes | Limits which modes this loop may grant loops it starts. |
| Step profile | Defines the steps, their order, and any repetition. |
| Effort setting | Limits iterations, intelligence retrieval, and model calls. |
| Stop condition | Defines success or another terminal state. |
| Depth limit | Limits how far the loop may start more loops. |
| Event log | Records decisions, attempts, modes, outputs, and failures. |

## Three run modes

| Mode | Meaning |
|---|---|
| `deterministic` | Uses code, rules, calculation, and search. It does not call a language model. |
| `hybrid` | Uses code first and may call a language model for a specific unresolved step. |
| `non_deterministic` | A language model leads the step while the loop controls tools, limits, logging, and verification. |

Mode is local to each loop. The mode a loop uses does not become the mode of a
loop it starts.

`allowable_modes` controls this loop. `delegated_modes` is a separate authority
setting that controls the loops it may start. This separation permits a
deterministic loop to start a non-deterministic research loop and permits that
research loop to start a deterministic validator.

## Step profiles

A step profile answers two questions: which steps run, and in what order? The
current implementation stores this shape in `LoopConfig.framework` and
`LoopConfig.custom_steps`. Reusable shapes are provided as Loop Templates.

| Public profile | Built-in template | Shape |
|---|---|---|
| Atomic code | `atomic_code_only` | One bounded `act` step. |
| Compact | `compact_five_beat` | Load, choose, act, check, commit. |
| Reference Practitioner | `reference_nine_step` | Orient, reconcile, assess, decide, determine how, act, verify, integrate, route. |
| Custom | `custom_user_supplied` or a validated custom configuration | From 1 to 200 ordered steps. Steps may repeat. |

The nine-step profile is a useful reference. It is not required for every
loop. Loop Engine also contains task-specific templates for research, repair,
experiments, review, improvement, and external workers.

Two bundled templates are candidates. Candidate templates cannot configure a
loop until they are reviewed and registered.

## Five settings that stay separate

The word profile can become unclear, so the public documentation separates
three ideas.

| Public term | Current code | What it changes |
|---|---|---|
| Loop profile | `LoopProfileSpec` | Purpose, required fields, capabilities, and compatibility. |
| Step profile | `framework`, `custom_steps`, Loop Template | Steps, order, and repetition. |
| Effort setting | `power` | Work limits such as iterations and model-call budget. |
| Model thinking power | `llm_thinking_power` | The configured model tier for a hybrid or non-deterministic loop. |
| Operating settings | `OperatingProfile`, `delegated_modes` | Permissions, provider access, delegation authority, and optimization preferences. |

Changing effort or model thinking power does not grant more permissions. Read
the [Loop profile ontology](LOOP-PROFILE-ONTOLOGY.md) for the versioned
Practitioner, Intelligence, and Solution hierarchy.

## Starting another loop

```python
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger

ledger = LoopLedger()
root = Loop(
    "assemble the verified delivery plan",
    LoopConfig(
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=(
            "deterministic", "hybrid", "non_deterministic"
        ),
        max_depth=2,
    ),
    ledger=ledger,
)

research = root.spawn(
    "interpret an ambiguous carrier policy",
    LoopConfig(
        framework="custom",
        custom_steps=("research",),
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",),
        llm_thinking_power="high",
        max_depth=2,
    ),
)

validation = research.spawn(
    "verify the extracted cutoff time",
    LoopConfig(
        framework="custom",
        custom_steps=("validate",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        max_depth=2,
    ),
)
```

The root is deterministic. The research loop is non-deterministic. The
validation loop is deterministic. All three share one event log, and the mode
of each loop remains visible.

For a complete practical example, see
[reconcile invoices](../../../examples/06_reconcile_invoices/).
