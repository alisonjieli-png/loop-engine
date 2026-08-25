# Architecture visual guidance

Status: current guidance.

Diagrams must explain Loop Engine from the outside in. Start with the task and
result. Add runtime detail only after the reader knows what the system builds.

## V1: bird's-eye system map

This is the required first figure in the README and other introductions.

Show this main path from left to right:

```text
Task -> Loop Practitioner -> Solution Canvas -> Result
```

The same figure must show only the architecture needed to orient a new reader:

- the shared Loop runtime used by Practitioner, Intelligence, and Solution;
- all four intelligence layers;
- the three Static Architecture groups;
- the Practitioner building a Solution Canvas;
- Solution Loops producing the result; and
- self-improvement labeled as a later Practitioner task, not a separate
  architecture system.

Do not place providers, models, settings, workspaces, approvals, stores,
Runtime Memory, event history, reports, playback, MCP, skills, or trace export
in this first figure. Those are internal runtime mechanics. Explain them on a
later detail figure.

Do not place the three modes or detailed step profiles in this first figure.
The next figures explain one Loop object and its controls.

Do not use the nine-step sequence as the first figure. It is detail about one
step profile, not the full product map.

## V2: one Loop object

Show one Loop with its `LoopDefinition` identity and digest, goal, typed
contract, selected mode, installed executor, step profile, runtime context,
budget, loop condition, exit condition, relationship, and event log.

If the figure includes a mode, use the public order:

1. Deterministic
2. Hybrid
3. Non-deterministic

If the figure includes step profiles, show atomic, compact, reference
nine-step, and custom. State that the nine-step profile is a reference, not a
universal rule.

## V3: Practitioner Loop graph

Show how the solution was built. A Starting Practitioner loop may start research,
review, tool, or verification loops. Each loop card should show its own mode,
status, and bounded goal.

Use `Spawned by` in a relationship label. Do not imply that queried,
retrieved, or connected Loops were spawned.

## V4: Static Architecture and intelligence

Show exactly three Static Architecture capability groups: Intelligence Search
and Retrieval, Web Research, and Custom Plugins. Do not draw providers,
settings, workspaces, approvals, stores, Runtime Memory, Run History, reports,
playback, or provider adapters as peer Static Architecture components. Those
are internal runtime mechanics.

The Retrieval Engine searches classified records across the four layers. Its
current backends are a fixed selectable set, not an external plugin registry.
Custom Plugin discovery is a separate search for something executable under
the Loop's contract and permissions. Do not merge these two searches.

Both searches return body-free `LoopRef` objects. Show selection before
materialization or execution. Capability discovery must be visibly local and
effect-free. Network, secret, file-write, and process effects begin in the
selected capability loop.

Show all four persistent intelligence layers:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory must remain outside those four layers because it is temporary
and belongs to the current run.

## V5: Solution Canvas

Show what will run for a new input. Use a left-to-right graph whose executable
vertices are Solution Loops. Show typed connections, declared modes, and named
fallbacks when they matter.

Use this caption when the distinction needs to be explicit:

> The Practitioner graph shows how Loop Engine built the work. The Solution
> Canvas shows what runs now.

Do not imply that declared hybrid or non-deterministic Canvas modes have a
built-in execution adapter today. The current in-process runner executes
deterministic Solution leaves only and fails preflight for other leaf modes.

## V6: run history

Use a horizontal timeline for Run History events. Show the newest event on the
right. Live views may reveal events as they arrive. Playback must use saved
events and must not rerun the original work.

## V7: self-improvement Practitioner workflow

Use a simple cycle:

```text
Self-improvement task -> Loop Practitioner -> Review history and intelligence -> Stage candidates -> Independent review
```

Domain Context seeding is one self-improvement task. Nothing should appear to
promote itself. Candidate work must remain visibly separate from reviewed and
accepted work.

## Review checklist

- The first figure starts with a task and ends with a result.
- Self-improvement enters the Loop Practitioner as a task and is not shown as a
  third runtime role.
- Each visible loop has a mode when mode detail matters.
- The four intelligence layers are all present in system maps.
- Runtime Memory is separate from persistent intelligence.
- Manual plugins are distinguished from future auto-discovery and marketplace
  packaging.
- Labels use plain English and can be read without the rest of the document.
- Lines do not cross labels, and text remains readable on a narrow screen.
