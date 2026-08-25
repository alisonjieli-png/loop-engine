# Loops and modes

## Every executable graph vertex is a Loop

Loop Engine uses one `Loop` runtime object. A Loop can perform bounded work or
start another Loop for a smaller part of the task. Practitioner loops build and
verify work. Solution loops run a finished Solution Canvas.

Each Loop has:

- a goal;
- an input and output contract;
- allowed and preferred run modes;
- delegated modes for loops it starts;
- a step profile;
- an effort setting and budget;
- model thinking power when the loop permits a model;
- a loop condition and an exit condition;
- a depth limit; and
- an event log.

Read [The Loop object and step profiles](../components/loop-object/) for the
complete definition.

A Loop profile classifies the loop as Practitioner, Intelligence, or Solution
work. It is separate from the step profile and run mode. Read the
[Loop profile ontology](../components/loop-object/LOOP-PROFILE-ONTOLOGY.md).

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
    delegated_modes=("deterministic", "hybrid", "non_deterministic"),
    llm_thinking_power="medium",
)
```

Allowed modes control the current loop. Preferred modes set its order. A
deterministic loop stays deterministic even when a model provider is
configured.

Delegated modes are separate. They control which modes the loop may grant a
loop it starts. This allows deterministic to start non-deterministic,
non-deterministic to start deterministic, and hybrid to start either. The
operating policy may still restrict delegation.

`llm_thinking_power` selects a configured model tier for hybrid or
non-deterministic work. It is invalid on a deterministic-only loop. Read
[Runtime settings and model tiers](settings.md).

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

## Exit conditions

```python
LoopConfig(exit_condition="steps_complete")
LoopConfig(exit_condition="accepted_success")
```

`steps_complete` requires the configured sequence to finish.
`accepted_success` finishes after one accepted iteration. An exit condition is
part of the Loop definition. A budget is a safety limit, not a successful
exit.

## Spawn a Practitioner Loop

```python
from loop_engine.loop.recursive_loop import Loop, LoopConfig, LoopLedger

ledger = LoopLedger()
starting_loop = Loop("prepare a quarterly plan", LoopConfig(), ledger=ledger)
numbers = starting_loop.spawn("gather current numbers")
assumption = numbers.spawn("check one assumption")
```

The Loops share the event log. Reports use the recorded relationships to show
the Practitioner graph. `max_depth` limits dynamic spawning.

## Practitioner and Solution loops

Practitioner loops explain how work was built. A Solution Canvas explains what
runs for a new input.

Self-improvement is a task given to the Loop Practitioner. It is not a fourth
runtime role.

- Read [Loop Practitioner](../components/practitioner/).
- Read [Solution Canvas](../components/solution-canvas/).
- Read [Self-improvement as a Practitioner task](../components/self-improvement/).

## Intelligence and run history

Loops can search Context Intelligence, Code Intelligence, Runtime History and
Solution Intelligence, and User Feedback Intelligence.
Runtime Memory is a separate temporary note board for the current run.

The event log records step attempts, mode decisions, searches, model calls,
outputs, and failures. See [Reports](reports.md) for text, Markdown, HTML, JSON,
live viewing, and playback.
