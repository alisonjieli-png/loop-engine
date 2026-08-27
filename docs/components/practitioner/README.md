# Loop Practitioner

The Loop Practitioner is the role that builds a solution. Practitioner Loops
understand the task, search for useful intelligence, choose a method, perform
the work, test the result, and decide what happens next.

It is a role of the shared `Loop` runtime, not a second runtime. The package
root exports no alternate Practitioner runtime class. Internal planning
algorithms use service names and run inside a classified `Loop` envelope.

## Starting and Spawned Practitioner identities

```text
Registered Practitioner profiles
├── practitioner.reference_nine_step
├── practitioner.compact_five_step
├── practitioner.research
├── practitioner.solver
├── practitioner.verifier
├── practitioner.self_improvement
└── practitioner.code_execution
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
3. Select a mode supported by the definition and an installed executor.
4. Perform bounded work or spawn another Loop for a smaller question.
5. Verify the output against the task contract.
6. Integrate accepted work and evaluate the loop and exit conditions.

A Practitioner can use a registered reference, compact, research, solver,
verifier, self-improvement, or code-execution profile. A validated extension
may add another versioned profile. The role does not require nine steps.

## Ambiguity during orientation

Missing text does not always require a question. The task compiler records one
typed disposition for each required value:

```text
provided
delegated_choice
needs_clarification
```

`delegated_choice` applies only when the task wording and registered template
policy permit it. The disposition includes constraint references and
dependencies. Orient may then discover candidates and use the shared typed
resolution contract. It cannot accept an unchecked model suggestion.
An explicit instruction to ask, or not to choose, overrides a delegation cue.

`needs_clarification` applies when the choice could change the contract,
authority, safety, cost, or acceptance result and the user has not delegated
it. Unknown remains unknown until a governed operation resolves it.

Task compilation supports two interaction modes:

```text
ask_when_material
└── ask only when an unresolved value can materially change the work

autonomous
├── use a registered delegated-choice policy when safe
└── return abstain_required when no safe policy exists
```

Autonomous mode never waits indefinitely, but it can still end without a
selection. Terminal abstention is preferable to invented facts or permissions.

Templates may expose optional task feedback slots. A value supplied through a
slot becomes structured task input. If the user supplies nothing, a permitted
autonomous choice continues under the same constraints. Ongoing advice during
or after a run still belongs to User Feedback Intelligence; task feedback does
not create another feedback store.

See [compile five text tasks](../../../examples/20_compile_text_tasks/) for
ready, clarification-required, and autonomous-abstention outcomes.

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

The deterministic callable wrapper `as_practitioner_loop()` remains a
compatibility entry point for bounded work. It composes a complete definition
and restricted runtime context before execution. New low-level integrations
should use `LoopDefinition` and `LoopStartRequest` directly.

For nested Practitioner loops with a custom step profile, see
[reconcile invoices](../../../examples/06_reconcile_invoices/).

## Typed spawning

Use `SpawnedTaskManager` with a Practitioner `LoopProfileRef`, or use the
synchronous `spawn_practitioner_loop()` helper. Both paths create the Spawned
Loop through `Loop.spawn()` and bind the exact definition identity.

Injected executors receive a `SpawnedLoopRuntimePort`, not the internal `Loop`
or shared ledger. See
[Spawned Loop delegation](../../guides/spawned-loop-delegation.md).
