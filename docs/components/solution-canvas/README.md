# Solution Canvas and Solution loops

A Solution Canvas describes the finished solution. It says which operations
run, which mode each operation declares, which parameters it receives, and
which fallback operations it may try.

Every executable graph vertex in the Canvas must resolve to a Solution Loop.
The current `SolutionLoopSpec` identifies an operation, mode, ports,
parameters, and fallbacks. The contract index records the fields that still
need consolidation into a complete versioned Loop definition.

## Solution Loops connect unless work branches dynamically

```text
Starting Solution Loop
├── Connected Solution Loop: solution.atomic_component
├── Connected Solution Loop: solution.validator
├── Connected Solution Loop: solution.pipeline
└── dynamic route selected
    └── Spawned Solution Loop
        ├── solution.router_fallback
        ├── repair branch
        └── dynamic ensemble member
```

A Starting Solution is not a special runtime or a separate Starting-only
profile. It is the first Solution Loop for one Canvas execution. Deterministic
pipeline steps are Connected Solution Loops because typed values flow through
declared ports. They are not described as Spawned merely because they are not
the starting node.

Router and fallback are two public aliases for the current combined
`solution.router_fallback` profile. They describe which part of that profile a
caller needs without creating two new runtimes.

Use Spawned Solution only when execution creates a real dynamic branch, such
as a selected fallback, repair, or dynamic ensemble member. That Loop records
the Solution Loop that spawned it.

The public relationship view is explicit:

```text
Practitioner-owned execution
└── Starting Practitioner
    └── builds a Solution Canvas
        └── Starting Solution Loop
            ├── Connected Solution Loop
            ├── Connected Solution Loop
            └── may spawn a dynamic Solution branch
```

Each Solution Loop displays its exact role profile, selected mode, typed
input and output ports, loop condition, exit condition, and outgoing
relationship. The Canvas may restrict permitted node modes. It does not have
one execution mode of its own.

## Practitioner graph compared with Solution Canvas

| View | Question it answers | Contents |
|---|---|---|
| Practitioner Loop graph | How did we build and test this? | Research, choices, attempts, reviews, and Loops started during the build. |
| Solution Canvas | What will run for the next input? | Solution loops, operations, modes, parameters, connections, and fallbacks. |

The two views may refer to the same task, but they are not the same graph.

## Current records and consolidation gap

| Record | Purpose |
|---|---|
| `SolutionLoopSpec` | Defines one solution loop and its operation. |
| `SolutionSpec` | Defines one loop graph or a composition of solutions. |
| `LoopGraphSpec` | Defines typed connections and named Adapter Loops. |
| Compiled solution plan | Freezes resolved operations and the exact composition. |

A solution can also combine other solutions by averaging, voting, weighted
averaging, ordered fallback, evaluated selection, or routing.

These records are not yet one authoritative graph contract. `Canvas` also
stores candidate alternatives by slot. The target is one versioned
`LoopGraphDefinition` with explicit typed edges. A Solution Canvas will then
be a candidate matrix and projection over that graph, not a separate execution
authority. Read the [contract index](../../contracts/) for the current gap.

## Current execution boundary

`SolutionSpec.validate()` checks declaration shape, permitted node modes, member
bounds, and typed port connections. It accepts all three declared mode names
when the Canvas policy allows them. This does not assign one mode to the whole
Canvas or pipeline.

Adapter coverage is a separate preflight. The current in-process adapter can
execute deterministic leaves only. If any leaf declares `hybrid` or
`non_deterministic`, `run_solution()` refuses the run before it initializes a
runtime Solution loop or calls an operation. Separate hybrid and
non-deterministic Canvas execution adapters are not implemented yet.

This separation preserves a valid portable declaration without pretending the
installed adapter can execute a mode it does not implement.

## Compile and inspect before running

`compile_solution()` checks that operations exist and that the composition is
valid. `render_canvas()` creates Mermaid and JSON views from the same compiled
plan. `run_solution()` executes the validated graph and records its event log.

See [validate a customer import](../../../examples/10_validate_customer_import/)
for a realistic deterministic Canvas with multiple operations and a fallback.
