# The Loop object and step profiles

`Loop` is the only executable graph vertex in Loop Engine. A Loop can perform
work, spawn another Loop, query Intelligence, retrieve an Intelligence item,
or pass a typed value to a connected Solution Loop.

## Relationship and role are separate

```text
Loop
├── relationship: Starting | Spawned by | Queried by | Retrieved by | Connected from
├── role: Practitioner | Intelligence | Solution
├── exact role profile
├── selected run mode
├── typed input and output ports
├── loop condition and exit condition
└── outgoing relationship
```

A Starting Solution is not a separate runtime profile. It is a Starting
relationship paired with a Solution role profile. An explicit compatibility
reader can load immutable records that use the retired topology shape. Current
records write `LoopRoleIdentity` and `LoopRelationship` fields only.

## What defines one loop

| Setting | Purpose |
|---|---|
| Goal | States the work to complete. |
| Operational relationship | States whether this is Starting, Spawned by, Queried by, Retrieved by, or Connected from. |
| Role profile | States whether this is Practitioner, Intelligence, or Solution work. |
| Contract | Defines accepted inputs, outputs, and effects. |
| Allowed modes | Limits which mode this Loop may select. |
| Preferred modes | Sets the order used to select one permitted mode. |
| Delegated modes | Limits which modes this loop may grant loops it starts. |
| Step profile | Defines the steps, their order, and any repetition. |
| Effort setting | Limits iterations, intelligence retrieval, and model calls. |
| Exit condition | Defines the exact accepted or terminal state. |
| Loop condition | Defines when this Loop node may continue. |
| Outgoing relationship | Defines whether the next edge spawns, queries, retrieves, or connects. |
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

## Spawn a Practitioner Loop

```python
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger
from loop_engine.loop.loop_role import (
    LoopRelationship,
    LoopRole,
    LoopRoleIdentity,
)

ledger = LoopLedger()
starting_loop = Loop(
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
    identity=LoopRoleIdentity(
        LoopRole.PRACTITIONER,
        "practitioner.reference_nine_step",
    ),
    relationship=LoopRelationship.starting(),
)

research = starting_loop.spawn(
    "interpret an ambiguous carrier policy",
    LoopConfig(
        framework="custom",
        custom_steps=("research",),
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",),
        llm_thinking_power="high",
        max_depth=2,
    ),
    identity=LoopRoleIdentity(
        LoopRole.PRACTITIONER,
        "practitioner.research",
    ),
    relationship=LoopRelationship.spawned_by(starting_loop.loop_id),
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
    identity=LoopRoleIdentity(
        LoopRole.PRACTITIONER,
        "practitioner.verifier",
    ),
    relationship=LoopRelationship.spawned_by(research.loop_id),
)
```

The Starting Practitioner is deterministic. It starts a non-deterministic
research Practitioner. The research Practitioner starts a deterministic
verifier Practitioner. All three write to one event log. Their relationships,
roles, profiles, and selected modes remain separate.

For a complete practical example, see
[reconcile invoices](../../../examples/06_reconcile_invoices/).
