# Loop Engine architecture

Every executable graph vertex is a Loop. Practitioner, Intelligence, and
Solution are roles of that one runtime.

```text
Task
└── Starting Practitioner Loop
    ├── may spawn Practitioner Loops
    ├── queries Intelligence Query Loops
    │   └── retrieves Intelligence Item Loops
    ├── uses Static Architecture capabilities
    └── builds one or more candidate Solutions
        └── Solution Canvas
            └── Starting Solution Loop
                ├── Connected Solution Loops
                └── Spawned Solution Loops for dynamic branches only
```

Each Loop has an exact role profile, selected mode, typed input and
output ports, settings, loop condition, exit condition, budget, permissions,
and Run History events. A graph, pipeline, or Canvas does not inherit one mode.

The four persistent intelligence layers are Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Runtime Memory is temporary and remains outside those layers.

Static Architecture provides Intelligence Search and Retrieval, Web Research,
and Custom Plugins. These capabilities are not fake graph vertices. Work that
uses a capability must still belong to a classified Loop. Providers, settings,
workspaces, approvals, stores, memory, history, and viewing are internal
runtime mechanics.

## Read the current architecture

1. [Main README](../../README.md)
2. [Repository organization](../REPOSITORY-ORGANIZATION.md)
3. [Contract index](../contracts/)
4. [Component guide](../components/)
5. [Architecture drift audit](LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
6. [Architecture conformance](ARCHITECTURE_CONFORMANCE.md)

An earlier long architecture note existed before the current Loop ontology.
Its contents remain in Git history. It is not a current product contract.
