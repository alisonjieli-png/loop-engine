# Loop Engine components

Kind: component explanations, one guide per architecture component.

This section explains Loop Engine from the shared runtime outward. Read the
pages in this order if the system is new to you.

| Order | Component | Main question |
|---:|---|---|
| 1 | [The Loop object and step profiles](loop-object/) | What runs, and what controls one run? |
| 2 | [Loop Practitioner](practitioner/) | How does Loop Engine build and test a solution? |
| 3 | [Solution Canvas](solution-canvas/) | What does the finished solution contain and run? |
| 4 | [Core Architecture](core-architecture/) | How do Intelligence Search and Retrieval, Web Research, and Custom Plugins support Loops? |
| 5 | [The four intelligence layers](intelligence-layers/) | Open folders for reusable context, code, history, solutions, and user guidance. Off on the main line, which serves the harness family alone. |
| 6 | [The hosted intelligence service](service-runtime/) | How does a customer's engine reach the reviewed catalogue, and what is recorded? |
| 7 | [Typed decision engines](typed-decisions/) | How is a closed-set judgment asked and admitted? |
| 8 | [Configuration space and adaptive search](configuration-search/) | Which configurations exist for one step, and how are candidates proposed? |
| 9 | [Managed records](managed-records/) | How is a durable, revisioned note read and revised? |

Self-improvement is a Practitioner workflow, not another component. Read
[Self-improvement as a Practitioner task](self-improvement/) after the core
component map.

Every functional component follows the
[functional component standard](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md):
one fixed, typed and versioned edge contract, one engine slot, and engines,
written here or adapted from an outside project, that a host can install,
select, test and replace without changing a caller. The design and its
reasons are in
[engines behind fixed edges](../architecture/ENGINES-BEHIND-FIXED-EDGES.md).

Every source directory that runs a registered operational boundary is mapped to
the guide that owns it in
[the component guide map](COMPONENT-GUIDE-MAP.yaml). The check in
`tools/check_component_guides.py` refuses a registered boundary whose directory
has no guide, and a guide that names a command, a record type, a refusal code or
a class the source does not define. It reads each name whole: a class member
must be defined on that class, and a value that only a check spells to show it
is refused does not count. A name that no runtime module defines, such as a
value in an example measurement's data, is declared in the map with the
repository file that holds it, and the check reads that file. Run it after
changing a guide:

```bash
PYTHONPATH=src python tools/check_component_guides.py
```

Add `--run-documented-checks` to also run every self-test command these guides
tell a reader to run. That takes several minutes and needs the package
installed, so it runs in continuous integration rather than by default. It is
the only rule that catches a command naming a report field the source builds at
run time, which is how the four configuration search commands were found to
raise `KeyError` on September 21, 2026.

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
Starting Solution connects to Solution pipeline Loops and only
spawns a Solution Loop for real dynamic work. Every Loop keeps its own mode,
step profile, budget, and contract.

The short version is:

1. A task enters a Loop Practitioner.
2. Practitioner loops build and verify the work.
3. They may produce a Solution Canvas.
4. Solution loops in that Canvas produce the result.
5. Self-improvement tasks ask the same Practitioner to review history and stage candidates.
6. Practitioner, Intelligence, and Solution Loops use the same Loop object.
   They may use the three Core Architecture capability groups when permitted.

The [main README](../../README.md) shows this complete relationship in one
diagram.
