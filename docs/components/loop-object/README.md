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

Mode is a permission. A loop may permit one or more modes. A loop that starts
another loop cannot give it permissions that the starting loop does not have.

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

## Three different settings

The word profile can become unclear, so the public documentation separates
three ideas.

| Public term | Current code | What it changes |
|---|---|---|
| Step profile | `framework`, `custom_steps`, Loop Template | Steps, order, and repetition. |
| Effort setting | `power` | Work limits such as iterations and model-call budget. |
| Operating settings | `OperatingProfile` | Permissions, provider access, and optimization preferences. |

Changing effort does not grant more permissions.

## Starting another loop

```python
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger

ledger = LoopLedger()
root = Loop(
    "prepare the delivery plan",
    LoopConfig(
        allowable_modes=("deterministic", "hybrid"),
        preferred_modes=("deterministic", "hybrid"),
        max_depth=2,
    ),
    ledger=ledger,
)

child = root.spawn("check carrier cutoff times")
```

The root and the loop it starts share one event log. Reports can rebuild the
relationship without treating the second loop as a different runtime type.

For a complete practical example, see
[reconcile invoices](../../../examples/06_reconcile_invoices/).
