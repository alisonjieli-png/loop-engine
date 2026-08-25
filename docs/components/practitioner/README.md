# Loop Practitioner

The Loop Practitioner is the role that builds a solution. Practitioner loops
understand the task, search for useful intelligence, choose a method, perform
the work, test the result, and decide what happens next.

It is a role of the shared `Loop` runtime, not a second runtime. The public
`PractitionerLoop` name is an exact alias of `Loop`. The package API does not
export a separate `Practitioner` class. Internal planning algorithms use service
names and run inside a `Loop` envelope.

## Starting and Spawned Practitioner identities

```text
Practitioner role profile
├── Starting Practitioner
│   └── Begins a run without a spawning Loop
└── Spawned Practitioner
    ├── researcher  -> practitioner.research
    ├── solver      -> practitioner.solver
    └── verifier    -> practitioner.verifier
```

Starting and Spawned by are relationship kinds, not Practitioner subclasses. The
same researcher, solver, or verifier profile can be Starting when that work is
the entry task. A Starting Intelligence or Starting Solution can delegate one
of these Spawned Practitioner profiles when its mode authority and contract
permit it.

Spawning and querying are different relationships:

```text
Task
└── Starting Practitioner
    ├── spawns a Practitioner subproblem Loop when work needs its own contract
    └── queries an Intelligence Query Loop when work needs intelligence
```

The Intelligence Query Loop is not labeled as a Spawned Practitioner. It keeps
the Intelligence role and a query relationship.

## What it does

1. Reconstruct the current task and accepted state.
2. Search the four intelligence layers for relevant context, code, prior work,
   and user guidance.
3. Choose an allowed run mode and a suitable step profile.
4. Perform bounded work or start another loop for a smaller question.
5. Verify the output against the task contract.
6. Integrate accepted work and decide whether to continue or stop.

A Practitioner can use the reference nine-step profile, a compact profile, an
atomic profile, or a custom profile. The role does not require nine steps.

## The Practitioner Loop graph

When one Practitioner Loop spawns another, the event log records a typed
relationship. A report can then show a graph such as:

```text
prepare quarterly plan
  gather current numbers
  draft objectives
    check one assumption
  verify the final plan
```

This graph explains how the work was built. It is not the finished Solution
graph.

## What it can produce

A Practitioner run may return a direct result. It may also produce a
[Solution Canvas](../solution-canvas/) that can be compiled, inspected, and
run again without repeating the build process.

The deterministic callable wrapper `as_practitioner_loop()` is useful for a
bounded five-step task. It is one convenient entry point, not the complete
definition of the Loop Practitioner role.

For nested Practitioner loops with a custom step profile, see
[reconcile invoices](../../../examples/06_reconcile_invoices/).

## Typed spawning

Use `SpawnedTaskManager` with a Practitioner `LoopProfileRef`, or use the
synchronous `spawn_practitioner_loop()` helper. Both paths create the Spawned
Loop through `Loop.spawn()`.

Injected executors receive a `SpawnedLoopRuntimePort`, not the internal `Loop`
or shared ledger. See
[Spawned Loop delegation](../../guides/spawned-loop-delegation.md).
