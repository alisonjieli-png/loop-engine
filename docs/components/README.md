# Loop Engine components

This section explains Loop Engine from the shared runtime outward. Read the
pages in this order if the system is new to you.

| Order | Component | Main question |
|---:|---|---|
| 1 | [The Loop object and step profiles](loop-object/) | What runs, and what controls one run? |
| 2 | [Loop Practitioner](practitioner/) | How does Loop Engine build and test a solution? |
| 3 | [Solution Canvas](solution-canvas/) | What does the finished solution contain and run? |
| 4 | [Static Architecture and extensions](static-architecture/) | Which shared services and registered plugins support every loop? |
| 5 | [The four intelligence layers](intelligence-layers/) | What reusable context, code, history, solutions, and user guidance can a loop search? |

Self-improvement is a Practitioner workflow, not another component. Read
[Self-improvement as a Practitioner task](self-improvement/) after the core
component map.

The [Loop profile ontology](loop-object/LOOP-PROFILE-ONTOLOGY.md) classifies
one Loop object as Practitioner, Intelligence, or Solution work. It does not
add another runtime or replace the intelligence layers.

The short version is:

1. A task enters a Loop Practitioner.
2. Practitioner loops build and verify the work.
3. They may produce a Solution Canvas.
4. Solution loops in that Canvas produce the result.
5. Self-improvement tasks ask the same Practitioner to review history and stage candidates.
6. Practitioner and Solution loops use the same Loop object and Static Architecture.

The [main README](../../README.md) shows this complete relationship in one
diagram.
