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

The same figure must also show:

- the shared Loop object used by Practitioner, Intelligence, and Solution Loops;
- the three run modes: deterministic, hybrid, and non-deterministic;
- step profiles with one step, five steps, nine steps, or a custom sequence;
- Practitioner loops that may start more Practitioner loops;
- Solution Canvas nodes that are Solution loops;
- self-improvement shown as a task entering the Loop Practitioner, not as a
  separate runtime role;
- Static Architecture supporting every loop;
- a separate Retrieval Engine service with lexical, vector, and hybrid modes;
- built-in adapters, manual plugin registration, and future plugin packaging;
- all four intelligence layers;
- Runtime Memory as current-run state; and
- Run History, reports, and playback as saved run history.

Do not use the nine-step sequence as the first figure. It is detail about one
step profile, not the full product map.

## V2: one Loop object

Show one Loop with its goal, typed contract, selected mode, step profile,
budget, loop condition, exit condition, relationships, and event log.

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
The Capability Directory is a separate search for something executable under
the loop's contract and permissions. Do not merge these two searches.

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

Show what will run for a new input. Use a left-to-right graph whose operational
nodes are Solution loops. Show typed connections, declared modes, and named
fallbacks when they matter.

Use this caption when the distinction needs to be explicit:

> The Practitioner graph shows how Loop Engine built the work. The Solution
> Canvas shows what runs now.

Do not imply that declared hybrid or non-deterministic Canvas modes have a
separate execution adapter today. The current in-process runner uses a
deterministic component loop for each operation.

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
