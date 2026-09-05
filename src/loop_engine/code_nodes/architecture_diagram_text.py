"""Shared explanatory text for generated architecture diagrams.

This module holds passive text rendered by ``architecture_diagram``. It does
not define architecture, execute work, or create another graph authority.
Keeping the complete trees here lets every generated view start from the same
classification without pushing the renderer over its source-size limit.
"""

import json


DIAGRAM_PREAMBLE = """\
Generated from the typed model in
`src/loop_engine/code_nodes/architecture_diagram.py`. Every code-backed
element names a module that must exist. A self-test fails if one stops
existing, so a rename breaks the diagram instead of leaving it quietly wrong.

These are renderings. The typed model is the record. A diagram language can
express things the system does not do, so each element carries an evidence
state: `implemented` has a current execution path, `partial` has a real
contract or incomplete path, `shadow` observes without changing the solve,
and `target` is planned rather than shipped."""

LOOP_CLASSIFICATION_TREE = """\
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records"""

ROLE_PROFILE_TREE = """\
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator"""

__all__ = (
    "DIAGRAM_PREAMBLE",
    "LOOP_CLASSIFICATION_TREE",
    "ROLE_PROFILE_TREE",
)


def record_access_model(model_type, element_type, relationship_type):
    """Build the typed storage view without expanding the shared renderer."""
    return model_type(
        key="record-access", level="component",
        title="Typed record access and distinct storage authorities",
        note=("Store and artifact boxes are internal mechanics, not executable "
              "Loop graph vertices. Managed notes use a tool; committed Run "
              "History has a separate immutable owner. PostgreSQL remains a target."),
        elements=(
            element_type("caller", "Developer or operational Loop", "container",
                    "Submits a typed record request under host-granted scope.",
                    "loop.recursive_loop"),
            element_type("operations", "Managed record operations", "component",
                    "Schema, scope, exact effect approval and revision checks.",
                    "core.record_operations", evidence_state="partial"),
            element_type("query", "Catalog query contract", "component",
                    "One closed filter contract; no LLM SQL text.", "catalog.query"),
            element_type("files", "Immutable package JSONL", "store",
                    "Shipped read-only records; not a mutable notes document.",
                    "catalog.stores.package_jsonl"),
            element_type("duckdb", "DuckDB file query adapter", "component",
                    "Bounded JSONL reads with typed filters; no file CRUD.",
                    "catalog.stores.duckdb_files", evidence_state="partial"),
            element_type("sqlite", "Local SQLite records", "store",
                    "Scoped mutable heads with atomic version preconditions.",
                    "catalog.stores.sqlite_store"),
            element_type("artifacts", "Immutable revision artifacts", "store",
                    "Digest-addressed document revisions with prior references.",
                    "core.context_artifacts"),
            element_type("history", "Canonical Run History", "store",
                    "Append-only execution evidence; not edited by note CRUD.",
                    "core.run_history"),
            element_type("postgres", "Server record adapter", "external",
                    "Future qualified multi-process database backend.",
                    evidence_state="target"),
        ),
        relationships=(
            relationship_type("caller", "operations", "requests",
                         carries="typed operation, expected revision, document"),
            relationship_type("operations", "query", "compiles bounded reads",
                         carries="host-enforced namespace and typed predicates"),
            relationship_type("query", "files", "reads through adapter",
                         carries="record cards and selected values"),
            relationship_type("query", "duckdb", "uses optional SQL implementation",
                         carries="bound literals and declared source files"),
            relationship_type("duckdb", "files", "scans without writing",
                         carries="JSONL record bytes"),
            relationship_type("operations", "artifacts", "stores after approval",
                         carries="immutable revision bytes and digest"),
            relationship_type("operations", "sqlite", "commits after artifact write",
                         carries="current reference with atomic precondition"),
            relationship_type("query", "sqlite", "queries",
                         carries="scoped record results"),
            relationship_type("operations", "history", "host may persist owning Loop events",
                         carries="operation metadata; no automatic CLI history write"),
            relationship_type("query", "postgres", "could use qualified adapter",
                         carries="same typed request with declared capabilities"),
        ))


_C4_KINDS = {"person": "Person", "system": "System", "external": "System_Ext",
             "container": "Container", "store": "ContainerDb",
             "component": "Component"}


def render_c4_plantuml(model) -> str:
    """Render C4-PlantUML; retain the legacy function name for callers.

    This is not Structurizr DSL. No deployment containment is inferred from
    the order of elements. The fixed standard-library include needs no remote
    source fetch when rendering with a compatible installed PlantUML.
    """
    lines = ["@startuml", "!include <C4/C4_Component>",
             "' Generated from the typed model; do not edit by hand."]
    aliases = {item.key: f"element_{i}"
               for i, item in enumerate(model.elements)}
    for item in model.elements:
        kind = _C4_KINDS.get(item.kind, "Component")
        description = (f"[{item.evidence_state}] {item.description}"
                       if item.description else f"[{item.evidence_state}]")
        arguments = [aliases[item.key], json.dumps(item.name)]
        if item.kind in ("container", "store", "component"):
            arguments.append(json.dumps(item.module or "unspecified"))
        arguments.append(json.dumps(description))
        lines.append(f"{kind}({', '.join(arguments)})")
    lines.append("")
    for edge in model.relationships:
        label = edge.label or "uses"
        lines.append(
            f"Rel({aliases[edge.source]}, {aliases[edge.target]}, "
            f"{json.dumps(label)}, {json.dumps(edge.carries)})")
    lines.append("@enduml")
    return "\n".join(lines)
