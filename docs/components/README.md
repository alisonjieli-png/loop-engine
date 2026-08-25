# Loop Engine components

This section explains Loop Engine from the shared runtime outward. Read the
pages in this order if the system is new to you.

| Order | Component | Main question |
|---:|---|---|
| 1 | [The Loop object and step profiles](loop-object/) | What runs, and what controls one run? |
| 2 | [Loop Practitioner](practitioner/) | How does Loop Engine build and test a solution? |
| 3 | [Solution Canvas](solution-canvas/) | What does the finished solution contain and run? |
| 4 | [Static Architecture](static-architecture/) | How do Intelligence Search and Retrieval, Web Research, and Custom Plugins support Loops? |
| 5 | [The four intelligence layers](intelligence-layers/) | What reusable context, code, history, solutions, and user guidance can a loop search? |

Self-improvement is a Practitioner workflow, not another component. Read
[Self-improvement as a Practitioner task](self-improvement/) after the core
component map.

The [Loop profile ontology](loop-object/LOOP-PROFILE-ONTOLOGY.md) classifies
one Loop object as Practitioner, Intelligence, or Solution work. It does not
add another runtime or replace the intelligence layers.

```text
One universal Loop runtime
├── LoopDefinition: versioned, digest-bound execution contract
├── LoopRuntimeContext: restricted services, permissions, and executors
├── Relationship
│   ├── Starting
│   ├── Spawned by
│   ├── Queried by
│   ├── Retrieved by
│   └── Connected from
└── Role profile
    ├── Practitioner
    ├── Intelligence
    └── Solution

One authoritative static DAG
└── LoopGraphDefinition
    ├── exact LoopDefinitionRef per executable vertex
    ├── typed edges and explicit Adapter Loops
    └── graph version and content digest
```

A Starting Practitioner may spawn a Practitioner subproblem Loop and query an
Intelligence Query Loop. The Query Loop retrieves Intelligence Item Loops. A
Starting Solution connects to deterministic Solution pipeline Loops and only
spawns a Solution Loop for real dynamic work. Every Loop keeps its own mode,
step profile, budget, and contract.

The short version is:

1. A task enters a Loop Practitioner.
2. Practitioner loops build and verify the work.
3. They may produce a Solution Canvas.
4. Solution loops in that Canvas produce the result.
5. Self-improvement tasks ask the same Practitioner to review history and stage candidates.
6. Practitioner, Intelligence, and Solution Loops use the same Loop object.
   They may use the three Static Architecture capability groups when permitted.

The [main README](../../README.md) shows this complete relationship in one
diagram.
