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

- the shared Loop object used by Practitioner, Solution, and Self-Improvement loops;
- the three run modes: deterministic, hybrid, and non-deterministic;
- step profiles with one step, five steps, nine steps, or a custom sequence;
- Practitioner loops that may start more Practitioner loops;
- Solution Canvas nodes that are Solution loops;
- a Self-Improvement Loop that reviews history and intelligence, seeds domains,
  and stages candidates only;
- Static Architecture supporting all three roles;
- a separate Retrieval Engine node with lexical, vector, and hybrid modes;
- built-in adapters and extension points, with external plugins labeled as
  potential rather than shipped;
- all four intelligence layers;
- Runtime Memory as current-run state; and
- Chronicle, reports, and playback as saved run history.

Do not use the nine-step sequence as the first figure. It is detail about one
step profile, not the full product map.

## V2: one Loop object

Show one loop with its goal, contract, mode, step profile, budget, stop
condition, parent relationship, started loops, and event log.

If the figure includes a mode, use the public order:

1. Deterministic
2. Hybrid
3. Non-deterministic

If the figure includes step profiles, show atomic, compact, reference
nine-step, and custom. State that the nine-step profile is a reference, not a
universal rule.

## V3: Practitioner loop tree

Show how the solution was built. A root Practitioner loop may start research,
review, tool, or verification loops. Each loop card should show its own mode,
status, and bounded goal.

Use "starts" in public labels. The diagram may use parent and child in a
technical note when it explains the permission clamp.

## V4: Static Architecture and intelligence

Show Static Architecture as shared services, not as a sequence of work. It can
contain the Capability Directory, Retrieval Engine, providers, validation,
stores, Chronicle, Studio, and Runtime Memory.

The Retrieval Engine searches classified records across the four layers. Its
current backends are a fixed selectable set, not an external plugin registry.
The Capability Directory is a separate search for something executable under
the loop's contract and permissions. Do not merge these two searches.

Show all four persistent intelligence layers:

1. Context Intelligence
2. Code Intelligence
3. Previous Run & Solution Intelligence
4. User Intelligence

Runtime Memory must remain outside those four layers because it is temporary
and belongs to the current run.

## V5: Solution Canvas

Show what will run for a new input. Use a left-to-right graph whose operational
nodes are Solution loops. Show typed connections, declared modes, and named
fallbacks when they matter.

Use this caption when the distinction needs to be explicit:

> The Practitioner tree shows how Loop Engine built the work. The Solution
> Canvas shows what runs now.

Do not imply that declared hybrid or non-deterministic Canvas modes have a
separate execution adapter today. The current in-process runner uses a
deterministic component loop for each operation.

## V6: run history

Use a horizontal timeline for Chronicle events. Show the newest event on the
right. Live views may reveal events as they arrive. Playback must use saved
events and must not rerun the original work.

## V7: Self-Improvement Loop

Use a simple cycle:

```text
Run -> Review history and intelligence -> Stage candidates -> Independent review -> Improve the four layers -> Next run
```

Domain Context seeding is one Self-Improvement task. Nothing should appear to
promote itself. Candidate work must remain visibly separate from reviewed and
accepted work.

## Review checklist

- The first figure starts with a task and ends with a result.
- Practitioner, Solution, and Self-Improvement loops are distinct roles of one
  runtime.
- Each visible loop has a mode when mode detail matters.
- The four intelligence layers are all present in system maps.
- Runtime Memory is separate from persistent intelligence.
- External plugins are described as potential until plugin loading exists.
- Labels use plain English and can be read without the rest of the document.
- Lines do not cross labels, and text remains readable on a narrow screen.
