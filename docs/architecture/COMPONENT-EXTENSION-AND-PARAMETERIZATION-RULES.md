# Component extension and parameterization rules

Use this order before adding a public type or module:

```text
same contract, different value
→ parameter

same behavior bundle, different defaults
→ profile

hard authority or eligibility rule
→ policy

different algorithm behind one contract
→ strategy

different provider, backend, or protocol
→ adapter

different sequence or dependency structure
→ procedure or LoopGraphDefinition

different durable semantic meaning
→ passive component kind

independently governed operation
→ another Loop using the same runtime

different lifecycle, persistence authority, or stateful protocol
→ service boundary
```

Do not create a new runtime, task-specific solver class, role subclass, step
subclass, provider-specific architecture, or folder for one variation.

## Atomic operations

A semantic primitive is a registered `AtomicPrimitiveDefinition`, not a Python
subclass. It defaults to deterministic mode and returns `LoopValue`.

Add an intrinsic only when no registered primitive can express the finite
native operation. An intrinsic addition must be pure, task agnostic, provider
agnostic, storage agnostic, and free of policy or permission decisions.

Physical fusion is an executor optimization. It may combine compatible pure
atomic Loops only when no permission, effect, retry, cancellation,
verification, checkpoint, or return boundary is crossed. Logical identities
and Run History must remain complete.

## Inheritance

The `Loop` runtime is sealed. Use composition, Protocol, strategy, adapter, and
data-level profile composition. Inheritance is allowed only for genuine
substitutability with explicit schema and lifecycle rules.

## New component checklist

Before adding a component, record:

- the unmet semantic meaning;
- current components inspected;
- why a parameter, profile, policy, strategy, adapter, procedure, composition,
  or mutation is insufficient;
- static or executable status;
- source of truth and folder owner;
- input and output contracts;
- authority and explicit prohibited authority;
- version, digest, scope, lifecycle, compatibility, and migration;
- interactions and context handoff;
- positive, negative, mutation, and generalization tests;
- rollback and learning instrumentation.
