# Context handoff ontology

Loop Engine preserves task hierarchy without copying every body into every
Spawned Loop.

## Context levels

```text
global task
├── original immutable request
└── normalized accepted interpretation
    ├── long-horizon outcome
    ├── medium-horizon checkpoint
    ├── short-horizon action group
    ├── parent assignment
    └── local Spawned Loop assignment
```

These levels are separate references. A summary cannot replace the original
request, and a local assignment cannot silently discard a global constraint.

## Context states

```text
available to request
→ the receiving Loop may ask for it under policy

available by reference
→ identity, version, digest, scope, and cost are visible

materialized
→ the body has been loaded for the receiving Loop

placed in model context
→ the body is present in one LLMWorkPacket

selected for a decision
→ the current action cites it as decision input
```

Do not infer one state from another.

## Accepted handoff contract

A complete `LoopHandoffEnvelope` or existing equivalent must carry:

- parent and Spawned Loop refs;
- reason for delegation;
- global and normalized task refs;
- long-, medium-, short-, parent-, and local task refs;
- current checkpoint;
- supplied facts, assumptions, and unknowns;
- selected intelligence, memory, and question refs;
- available context manifest and materialized payload refs;
- capability snapshot;
- typed input, output, confidence, verification, and return contracts;
- permissions, budget, deadline, cancellation, and stop conditions;
- integration instructions and provenance.

The current runtime already owns typed spawned work, relationships, budgets,
cancellation, terminal records, and return behavior. Full horizon-stack and
demand-pull component fields remain a checkpoint. Do not describe them as
verified until their tests pass.

## Demand pull

A receiving Loop can request missing context with:

```text
ContextNeedRequest
├── missing context kind
├── reason
├── expected decision change
├── minimum acceptable form
├── privacy requirement
├── size or token budget
└── urgency
```

The parent or an Intelligence Loop may return a body, summary, reference,
canonical projection, denial, instruction to proceed, or reroute decision. The
negotiation is governed Loop work.

## Isolation

Never include parent private scratch, sibling private state, raw model
reasoning, unrelated user data, unrestricted history, or credentials merely
because the receiving Loop has the same Starting Loop task.

Permission is not transferred with context. A Spawned Loop receives explicit
equal or narrower authority.
