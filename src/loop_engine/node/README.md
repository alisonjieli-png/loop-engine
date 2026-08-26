# Node Ontology

## Constitutional Rule

`Node` is an ontological category and package namespace.

`LoopNode` is the only concrete graph-addressable operational Node in
Loop Engine.

There is no concrete generic `Node` class.

Never create:

- `ConfigurationNode`
- `StringNode`
- `CodeNode`
- `ContractNode`
- `PractitionerNode`
- `IntelligenceNode`
- `SolutionNode`
- run-mode-specific Node classes
- plugin-defined Node classes

Reusable behavior is represented through versioned `LoopNodePreset`
records. Typed values, contracts, policies, configurations, references,
results, and receipts are objects contained by or returned from a
`LoopNode`. They are not Nodes.

## LoopNode composition

```text
LoopNode
├── Definition
│   ├── Purpose
│   ├── Contracts
│   ├── Procedure
│   ├── Execution
│   ├── Intelligence Seeking
│   ├── Control
│   ├── Verification
│   ├── Routing
│   ├── Permissions
│   ├── Inheritance
│   ├── Compatibility
│   └── Observability Requirements
├── Invocation
│   ├── Input Values
│   ├── Goal Bindings
│   ├── Context Bindings
│   ├── Parent Delegation
│   ├── Allowed Overrides
│   └── Invocation Metadata
└── Runtime
    ├── Identity
    ├── Topology
    ├── Resolved Configuration
    ├── Runtime State
    ├── Runtime Memory
    ├── Child LoopNode Handles
    ├── Chronicle
    └── Outcome
```

## Atomicity boundary

Create a Child LoopNode when work needs:

```text
├── an independent goal
├── an independent contract
├── an independent budget
├── independent permissions
├── independent verification
├── independent retry or repair
├── independent scheduling
├── independent delegation
└── a separate Chronicle identity
```

Keep work as an implementation primitive when it is:

```text
├── a local function call
├── serialization
├── hashing
├── one database-driver operation
├── one provider-SDK call
├── a small calculation
└── another implementation detail governed by the current LoopNode
```

## Presets

Common behaviors are represented by versioned LoopNode presets:

```text
core.loop_node_preset.configuration_provider@1.0.0
core.loop_node_preset.record_lookup@1.0.0
core.loop_node_preset.validator@1.0.0
core.loop_node_preset.transform@1.0.0
core.loop_node_preset.composite@1.0.0
```

A preset is a partial typed configuration. It is never a subclass, a
runtime, an executor, or a permission grant.

## Related invariants

- LE-NODE-001 through LE-NODE-009
- LE-CONFIG-001, LE-CONFIG-002
- LE-PERM-001
- LE-VERSION-001

See `docs/architecture/CONSTITUTION.md` and `architecture.yaml`.
