# Universal Loop standard

Status: current reference.

This page defines the shared rules for an operational loop in Loop Engine. The
runtime and conformance tests remain the executable authority.

## 1. Runtime identity

Each executable graph vertex is a `Loop`. Practitioner, Intelligence, and
Solution are roles of this same runtime. A search, model call, validation, repair,
or bounded external worker must use a Loop envelope when it becomes active
work.

Contracts, configuration, saved plans, graph edges, policies, and event data
describe work. They are not separate runtime types.

## 2. Required loop definition

A runnable loop declares:

| Field | Requirement |
|---|---|
| Goal | Name the bounded work. |
| Definition identity | Name the Loop definition, semantic version, and SHA-256 content digest. |
| Role profile | Select a registered Practitioner, Intelligence, or Solution profile. |
| Contract | Define accepted inputs, outputs, and effects. |
| Configuration facts | Store immutable JSON facts that affect execution. |
| Supported modes | Limit the modes the Loop may use. |
| Installed executors | Name the modes that the current runtime can physically execute. |
| Preferred modes | Order the permitted modes. |
| Step profile | Define the steps, order, and repetition. |
| Loop condition | Define when another iteration may run. |
| Effort setting | Bound iterations, retrieval, model calls, and related work. |
| Exit condition | Define success or another terminal state. |
| Replay guarantee | State what a later replay can reproduce. |
| Depth limit | Bound loops started by loops. |
| Capabilities and permissions | Name required services, permitted effects, and resource authority. |

A missing or invalid required field fails before execution.

## 3. Three modes

The public mode order is:

1. Deterministic
2. Hybrid
3. Non-deterministic

Mode is selected for one Loop instance. A Loop may not exceed its profile and
operating policy. A spawning Loop may grant fewer permissions, but it cannot
grant more than it has.

Effort does not grant permissions.

A semantic mode without an installed executor fails before work.

## 4. Step profiles

Step profile and mode remain independent.

- Atomic code runs one bounded action.
- Compact runs five steps.
- Reference Practitioner runs nine steps.
- Custom runs a validated bounded sequence from 1 to 200 steps.

The reference nine-step profile is not a universal execution law. Custom
profiles may reorder or repeat steps.

## 5. Attempts, loop conditions, and exit conditions

An attempt does not automatically complete a Loop. A failed deterministic
attempt can move to an allowed fallback mode. The Loop continues only while
its loop condition permits another iteration. It finishes successfully only
when its exit condition is satisfied.

The event history keeps attempts, accepted work, iterations, loops started,
and terminal states separate.

## 6. Three Loop roles

A Practitioner Loop graph records how work was understood, built, and tested.
A Solution Canvas describes what runs for a new input.

Every executable Canvas vertex is a Solution Loop. The current in-process
Canvas runner uses a deterministic Solution Loop for each operation. It
refuses hybrid and non-deterministic Solution execution because those adapters
are not implemented.

A self-improvement Practitioner task reviews a bounded population of verified
Run History records and the current Intelligence Library. It can audit, mine,
compare, generate, and stage candidates. Its `logical_kind` is
`search_improvement`, so it cannot approve or promote its own output.

## 7. One graph authority

`LoopGraphDefinition` is the authoritative static DAG. Every vertex contains
an exact `LoopDefinitionRef`. Every edge names a source port, target port, and
relationship. An Adapter must be an explicit Loop vertex. An edge cannot
contain hidden execution.

Graph validation checks definition digests, selected modes, executor coverage,
typed roles, relationships, graph inputs and outputs, groups, and cycles.
`SolutionSpec` and `Canvas` build or project that graph. They are not parallel
graph authorities.

## 8. Intelligence and memory

Loops may search four persistent intelligence layers:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is temporary and belongs to the current run. It is not a fifth
persistent layer. Temporary notes do not promote themselves.

Candidate Context uses the experimental tier and remains outside normal
retrieval. A review path must request candidates explicitly.

## 9. Runtime context

Every Loop receives a `LoopRuntimeContext`. Its public Core Architecture
ports are Intelligence Search and Retrieval, Web Research, and Custom Plugins.
Internal mechanics contain providers, settings, workspaces, approvals, stores,
Runtime Memory, events, reports, playback, MCP, skills, and trace export.

A derived context may remove capabilities, permissions, or executors. It may
not add them.

## 10. History and replay

Every material action writes a typed event. The Run History stores the saved
event history and verifies its chain. Reports, live views, and playback are
projections of that history.

Playback reads saved events. It does not rerun the original effects.

A loop states one replay guarantee: exact, event-equivalent,
evidence-equivalent, or non-replayable. A seed or a zero temperature does not
prove exact replay.

## 11. Authority boundaries

- A loop cannot widen its own permissions.
- A loop that searches for improvements cannot approve its own candidate.
- Model and network calls stay behind declared adapters.
- Secrets do not enter prompts, Runtime Memory, or run evidence.
- External effects require the permissions and checks defined by the loop
  contract.
- Missing evidence remains missing. It does not become zero or success.

## 12. Verification

Run the complete behavior suite and architecture checks:

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

Do not copy a fixed suite count into this page. Use the command output for the
current total and current result.
