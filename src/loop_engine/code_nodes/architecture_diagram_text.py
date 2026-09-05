"""Shared explanatory text for generated architecture diagrams.

This module holds passive text rendered by ``architecture_diagram``. It does
not define architecture, execute work, or create another graph authority.
Keeping the complete trees here lets every generated view start from the same
classification without pushing the renderer over its source-size limit.
"""

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
