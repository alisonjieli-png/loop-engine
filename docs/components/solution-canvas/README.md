# Solution Canvas and Solution loops

A Solution Canvas describes the finished solution. It says which operations
run, which mode each operation declares, which parameters it receives, and
which fallback operations it may try.

Every operational node in the Canvas is a `SolutionLoopSpec`. Each node runs
through the shared loop envelope, so it has an identity, a failure location,
an event history, and a fallback path.

## Practitioner tree compared with Solution Canvas

| View | Question it answers | Contents |
|---|---|---|
| Practitioner loop tree | How did we build and test this? | Research, choices, attempts, reviews, and loops started during the build. |
| Solution Canvas | What will run for the next input? | Solution loops, operations, modes, parameters, connections, and fallbacks. |

The two views may refer to the same task, but they are not the same graph.

## Main records

| Record | Purpose |
|---|---|
| `SolutionLoopSpec` | Defines one solution loop and its operation. |
| `SolutionSpec` | Defines one loop graph or a composition of solutions. |
| `LoopGraphSpec` | Defines typed connections and named Adapter Loops. |
| Compiled solution plan | Freezes resolved operations and the exact composition. |

A solution can also combine other solutions by averaging, voting, weighted
averaging, ordered fallback, evaluated selection, or routing.

## Current execution boundary

`SolutionSpec` validates the three mode names and refuses a node whose mode is
outside the Canvas permissions. The current in-process runner then executes
each operation through a deterministic component loop. Separate hybrid and
non-deterministic Canvas execution adapters are not implemented yet.

This means a declared Canvas mode is currently validation and run metadata. It
does not make the operation call a language model.

## Compile and inspect before running

`compile_solution()` checks that operations exist and that the composition is
valid. `render_canvas()` creates Mermaid and JSON views from the same compiled
plan. `run_solution()` executes the validated graph and records its trace.

See [validate a customer import](../../../examples/10_validate_customer_import/)
for a realistic deterministic Canvas with multiple operations and a fallback.
