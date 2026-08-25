# Universal Loop standard

Status: current reference.

This page defines the shared rules for an operational loop in Loop Engine. The
runtime and conformance tests remain the executable authority.

## 1. Runtime identity

Each operational node is a `Loop`. Practitioner, Solution, and Self-Improvement
loops are roles of this same runtime. A search, model call, validation, repair,
or bounded external worker must use a Loop envelope when it becomes active
work.

Contracts, configuration, saved plans, graph edges, policies, and event data
describe work. They are not separate runtime types.

## 2. Required loop definition

A runnable loop declares:

| Field | Requirement |
|---|---|
| Goal | Name the bounded work. |
| Contract | Define accepted inputs, outputs, and effects. |
| Logical kind | State whether the loop executes, represents task repetition, or searches for improvement. |
| Allowed modes | Limit the modes the loop may use. |
| Preferred modes | Order the permitted modes. |
| Step profile | Define the steps, order, and repetition. |
| Effort setting | Bound iterations, retrieval, model calls, and related work. |
| Stop condition | Define success or another terminal state. |
| Replay guarantee | State what a later replay can reproduce. |
| Depth limit | Bound loops started by loops. |

A missing or invalid required field fails before execution.

## 3. Three modes

The public mode order is:

1. Deterministic
2. Hybrid
3. Non-deterministic

Mode is a permission. A loop may not exceed its allowed modes. A loop that
starts another loop may grant fewer permissions, but it cannot grant more than
it has.

Effort does not grant permissions.

## 4. Step profiles

Step profile and mode remain independent.

- Atomic code runs one bounded action.
- Compact runs five steps.
- Reference Practitioner runs nine steps.
- Custom runs a validated bounded sequence from 1 to 200 steps.

The reference nine-step profile is not a universal execution law. Custom
profiles may reorder or repeat steps.

## 5. Attempts, accepted work, and stopping

An attempt does not automatically complete a loop. A failed deterministic
attempt can move to an allowed fallback mode. The loop stops only when its
declared condition is satisfied or another terminal state occurs.

The event history keeps attempts, accepted work, iterations, loops started,
and terminal states separate.

## 6. Three Loop roles

A Practitioner loop tree records how work was understood, built, and tested.
A Solution Canvas describes what runs for a new input.

Every operational Canvas node is a Solution loop. The current in-process
Canvas runner uses a deterministic component loop for each operation. Hybrid
and non-deterministic Canvas modes are validated and recorded, but separate
execution adapters for those modes are not implemented yet.

A Self-Improvement Loop reviews a bounded population of verified Chronicle
history and the current Intelligence Library. It can audit, mine, compare,
generate, and stage candidates. Its `logical_kind` is `search_improvement`, so
it cannot approve or promote its own output.

## 7. Intelligence and memory

Loops may search four persistent intelligence layers:

1. Context Intelligence
2. Code Intelligence
3. Previous Run & Solution Intelligence
4. User Intelligence

Runtime Memory is temporary and belongs to the current run. It is not a fifth
persistent layer. Temporary notes do not promote themselves.

Candidate Context uses the experimental tier and remains outside normal
retrieval. A review path must request candidates explicitly.

## 8. History and replay

Every material action writes a typed event. The Chronicle stores the saved
event history and verifies its chain. Reports, live views, and playback are
projections of that history.

Playback reads saved events. It does not rerun the original effects.

A loop states one replay guarantee: exact, event-equivalent,
evidence-equivalent, or non-replayable. A seed or a zero temperature does not
prove exact replay.

## 9. Authority boundaries

- A loop cannot widen its own permissions.
- A loop that searches for improvements cannot approve its own candidate.
- Model and network calls stay behind declared adapters.
- Secrets do not enter prompts, Runtime Memory, or run evidence.
- External effects require the permissions and checks defined by the loop
  contract.
- Missing evidence remains missing. It does not become zero or success.

## 10. Verification

Run the complete behavior suite and architecture checks:

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

Do not copy a fixed suite count into this page. Use the command output for the
current total and current result.
