---
folder_id: ontology
parent: ""
ontology_version: 1.0.0
---

# Ontology

This package is the closed foundational vocabulary of Loop Engine. It
defines what a persistent record is, how records are classified, which
folders may hold them, and how the three physical storage roots combine
into one logical catalog.

It adds no runtime. There is still exactly one operational runtime type,
the Loop, and work starts only through `LoopStartRequest`.

## The two foundational object classes

The system needs two object definitions, and only these two:

```text
Node                        (passive persistent record at rest)
├── identity: object_id, version, content_digest
├── kind: node | loop_node
├── artifact_kind: loop_definition, loop_graph, intelligence_record,
│                 contract, binding, code_unit, policy
├── source_class: core | learned | plugin
├── layer: one of the four intelligence layers, when any
├── lifecycle: draft, candidate, validated, registered,
│              preferred, deprecated, retired
├── parent_collection
└── typed input roles and output roles

LoopNode(Node)              (the only executable specialization)
├── role: practitioner | intelligence | solution
├── role_profile_id and version
├── supported_modes: deterministic, hybrid, non_deterministic
├── step profile
├── loop condition and exit condition
└── effects, permissions, required capabilities
```

A `Node` never runs. A `LoopNode` names work that can run; it is a
definition at rest, not a live process. A `LoopNode` becomes live only
when its exact definition reference resolves through the existing
registry and starts through `LoopStartRequest`. Both classes are
projections of existing authoritative contracts, so their digests match
the runtime definitions they describe and neither view can drift from
the other silently.

## What folders mean

Folder paths are the persistent architecture made visible:

```text
Path sentence                      Meaning
intelligence / code / core         Domain -> Layer -> Provenance
kernel / executor                  Substrate concern -> member
governance / candidates            Lifecycle area -> member
runtime / runtime_memory           Run scope -> member
```

A canonical path reads like an architectural sentence that stops at
provenance. Everything more specific is an attribute of a record, not a
folder. Artifact type, Loop role, category, and topic live in manifest
records and catalog attributes so that large collections can be queried,
moved into a database later, and never require new directories.
Long term, a learned collection is a database with references to files;
the folder tree stays small and stable while record counts grow.

## Three physical roots, one logical catalog

```text
Core package (read only)  ──┐
                            ├──> UnifiedCatalog ──> search, resolver, checks
Learned instance root    ──┤   (loop_engine.ontology.catalog)
~/.loop-engine/intelligence |
                            │
Declared plugin roots    ───┘
```

Provenance changes where bytes live, never how work executes. Core,
learned, and plugin records all resolve through the same catalog, and no
root can overwrite another.

## Responsibilities stay separate

```text
Folder path      identifies what kind of object lives here
README.md        explains local meaning, rules, relationships
manifest.yaml    machine-readable identity, digests, payloads, pointers
Code             implements behavior in already-mapped modules
ontology_checks  proves all four views agree
index.json       generated navigation snapshot, never hand edited
```

## Validation

Run `python -m loop_engine --ontology-check`. The check proves every
semantic folder exists, every README front matter matches this table,
required manifests parse, no Python appears in data roots, retired terms
stay out, duplicate object ids are refused, payload digests verify, and
`index.json` is current. Every detector is canary-proven by an
adversarial fixture before the live tree is judged.
