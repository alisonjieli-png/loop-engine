# Start a Codex session in Loop Engine

Use `/home/username/loop-engine` as the workspace directory for Loop Engine work.
This repository is separate from `/home/username/taedri.dev`.

## First message for a new session

```text
Work only in /home/username/loop-engine for this task.

Read AGENTS.md first. Then inspect the current branch, revision, dirty state,
active processes, and concurrent writers. Preserve all existing changes.

Read README.md and docs/components/README.md. Follow only the component guides
needed for the task. Use humanizer-context.md for public writing.

Loop Engine has one universal Loop runtime. Starting, Spawned by, Queried by,
Retrieved by, and Connected from are relationships. Practitioner,
Intelligence, and Solution are roles. Run mode, step profile, thinking power,
typed contract, budget, permissions, loop condition, and exit condition are
separate settings.

Use detailed tree diagrams to explain every hierarchy. Start from this tree
and extend one branch at a time:

Operational runtime type
└── Loop
    ├── LoopDefinition: ID, version, digest, profile, contract, modes, conditions, authority
    ├── LoopRuntimeContext: three public capability ports plus internal mechanics
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Purpose and domain categories
    ├── Selected mode: deterministic, hybrid, or non-deterministic
    ├── Budget, permissions, and effects
    ├── Model settings when model use is allowed
    └── Run History events

Authoritative static graph
└── LoopGraphDefinition
    ├── exact LoopDefinitionRef per executable vertex
    ├── typed edges
    ├── graph inputs and outputs
    └── graph version and content digest

Never use runtime type, role, profile, category, mode, or settings as
interchangeable terms.

Treat /home/username/taedri.dev only as a semantic design reference. Do not
copy files or create parallel registries. State a missing invariant, map it to
an existing Loop Engine boundary, implement the smallest typed extension, and
verify it inside Loop Engine.

Do not commit, push, call a paid provider, rerun a completed benchmark, or
perform external effects unless the current request authorizes that action.
```

## Reading order

1. [`AGENTS.md`](../../AGENTS.md)
2. [`README.md`](../../README.md)
3. [Contract index](../contracts/README.md)
4. [Taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
5. [Component map](../components/README.md)
6. [Older reference-source boundaries](REFERENCE-SOURCES.md) only when older
   repository material may be relevant
7. [Loop object and profiles](../components/loop-object/README.md)
8. [Intelligence layers](../components/intelligence-layers/README.md)
9. [Core Architecture](../components/core-architecture/README.md)
10. [Solution Canvas](../components/solution-canvas/README.md)
11. [Case studies](../../case-studies/README.md) only when the task concerns
   measured full-system runs

For broad continued development rather than one narrow task, use the
[governing OpenCode and Codex prompt](../prompts/LOOP-ENGINE-GOVERNING-DEVELOPMENT-PROMPT.md).

## Working-directory check

Run this before changing files:

```bash
pwd
git rev-parse --show-toplevel
git remote get-url origin
git status --short --branch
```

The first two paths should both resolve to `/home/username/loop-engine`. The
remote should resolve to the Loop Engine GitHub repository.

## What not to include

Do not paste the full Taedri Constitution, Taedri reference manual, old Loop
Intelligence README, historical benchmark transcripts, or an entire prior chat
into a new Loop Engine session. Those sources contain project-specific or
stale details that can override the simpler Loop Engine architecture.

Bring over one verified invariant at a time. Keep its source revision and
reason visible in the resulting design note or change.
