# Loop Practitioner

The Loop Practitioner is the role that builds a solution. Practitioner loops
understand the task, search for useful intelligence, choose a method, perform
the work, test the result, and decide what happens next.

It is a role of the shared `Loop` runtime, not a second runtime. The public
`PractitionerLoop` name is an alias of `Loop`. Public documentation uses
"Loop Practitioner" so it does not conflict with other internal classes that
use the shorter word `Practitioner`.

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

## The Practitioner loop tree

When one Practitioner loop starts another, the event log records the
relationship. A report can then show a loop tree such as:

```text
prepare quarterly plan
  gather current numbers
  draft objectives
    check one assumption
  verify the final plan
```

This tree explains how the work was built. It is not the finished solution
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
