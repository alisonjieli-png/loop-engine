# Universal component prompt suite

Use the prompts in this order:

1. [Implementation mandate](UNIVERSAL-COMPONENT-IMPLEMENTATION-MANDATE.md)
   for the primary coding session.

2. [Adversarial architecture review](ADVERSARIAL-COMPONENT-ARCHITECTURE-REVIEW.md)
   in a fresh independent session after each hard checkpoint.

3. [Component ideation and conformity](COMPONENT-IDEATION-AND-CONFORMITY.md)
   before adding a class, subsystem, folder, public term, or framework.

4. [Continuous component conformance](CONTINUOUS-COMPONENT-CONFORMANCE.md)
   after each meaningful implementation batch or commit.

5. [Strict everything-is-a-Loop primitives](STRICT-EVERYTHING-IS-A-LOOP-PRIMITIVES.md)
   for native string, JSON, mapping, path, command, and schema migration.

All four prompts use the same architectural distinction:

```text
passive Loop component
→ versioned, typed, digest-pinned information

independently governed operation
→ the sole executable Loop runtime
```

They do not authorize an active `LoopNode` class, another runtime, another
graph authority, another intelligence layer, or a task-specific generic
solver branch.
