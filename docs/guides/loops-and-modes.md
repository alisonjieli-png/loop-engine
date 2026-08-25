# Loops and modes

## Each operational node is a loop

Loop Engine uses one `Loop` runtime object. A Loop can perform bounded work or
start another Loop for a smaller part of the task. Practitioner loops,
Solution loops, and Self-Improvement loops are roles of this same runtime.

Each loop has:

- a goal;
- an input and output contract;
- allowed and preferred run modes;
- a step profile;
- an effort setting and budget;
- a stop condition;
- a depth limit; and
- an event log.

Read [The Loop object and step profiles](../components/loop-object/) for the
complete definition.

## Three run modes

| Mode | How it runs |
|---|---|
| `deterministic` | Uses code, rules, calculation, and search. It does not call a language model. |
| `hybrid` | Uses code first and may call a language model for a specific unresolved step. |
| `non_deterministic` | A language model leads the step while the loop controls tools, limits, logging, and verification. |

```python
from loop_engine.loop.recursive_loop import LoopConfig

config = LoopConfig(
    allowable_modes=("deterministic", "hybrid"),
    preferred_modes=("deterministic", "hybrid"),
)
```

Allowed modes are permissions. Preferred modes set the order within those
permissions. A deterministic loop stays deterministic even when a model
provider is configured.

A loop that starts another loop cannot grant a mode that it does not have.

## Step profiles

Step profile and run mode answer different questions.

- The run mode says how a step may be performed.
- The step profile says which steps run and in what order.

| Profile | Shape |
|---|---|
| Atomic code | One bounded action. |
| Compact | Load, choose, act, check, commit. |
| Reference Practitioner | Orient, reconcile, assess, decide, determine how, act, verify, integrate, route. |
| Custom | From 1 to 200 caller-defined steps. Steps may repeat. |

The code stores this shape in `framework` and `custom_steps`. Reusable shapes
are stored as Loop Templates. The nine-step profile is a reference, not a
requirement.

## Stop conditions

```python
LoopConfig(stop_condition="run_to_completion")
LoopConfig(stop_condition="success_once")
```

`run_to_completion` follows the configured sequence and budget.
`success_once` stops after one accepted iteration. A stop condition is part of
the loop definition, not an error-handling shortcut.

## Starting another loop

```python
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger

ledger = LoopLedger()
root = Loop("prepare a quarterly plan", LoopConfig(), ledger=ledger)
numbers = root.spawn("gather current numbers")
assumption = numbers.spawn("check one assumption")
```

The loops share the event log. Reports use the recorded relationships to show
the loop tree. `max_depth` keeps the tree bounded.

## Three Loop roles

Practitioner loops explain how work was built. A Solution Canvas explains what
runs for a new input.

A Self-Improvement Loop reviews history and intelligence, then stages
candidates for independent review.

- Read [Loop Practitioner](../components/practitioner/).
- Read [Solution Canvas](../components/solution-canvas/).
- Read [Self-improvement and domain seeding](../components/self-improvement/).

## Intelligence and run history

Loops can search Context, Code, Previous Run & Solution, and User Intelligence.
Runtime Memory is a separate temporary note board for the current run.

The event log records step attempts, mode decisions, searches, model calls,
outputs, and failures. See [Reports](reports.md) for text, Markdown, HTML, JSON,
live viewing, and playback.
