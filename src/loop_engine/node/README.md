# Node Ontology

## Constitutional Rule

`Node` is an ontological category and package namespace.

`Loop` is the only concrete operational runtime and executable graph vertex in
Loop Engine. Historical serialized `kind: loop_node` records are not current
Node objects; the compatibility reader migrates them to `LoopDefinitionRecord`.

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

Reusable behavior is represented through versioned passive preset records.
Typed values, contracts, policies, configurations, references, results, and
reports are objects contained by or returned from a `Loop`. They are not
executable graph vertices.

## Loop composition

```text
Loop
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
    ├── Spawned Loop handles
    ├── Run History
    └── Outcome
```

## Atomicity boundary

Create a Loop Spawned by its parent when work needs:

```text
├── an independent goal
├── an independent contract
├── an independent budget
├── independent permissions
├── independent verification
├── independent retry or repair
├── independent scheduling
├── independent delegation
└── a separate Run History identity
```

Keep work as an implementation primitive when it is:

```text
├── a local function call
├── serialization
├── hashing
├── one database-driver operation
├── one provider-SDK call
├── a small calculation
└── another implementation detail governed by the current Loop
```

## Presets

Common behaviors are represented by versioned passive Loop profiles:

```text
core.loop_profile.configuration_provider@1.0.0
core.loop_profile.record_lookup@1.0.0
core.loop_profile.validator@1.0.0
core.loop_profile.transform@1.0.0
core.loop_profile.composite@1.0.0
```

A preset is a partial typed configuration. It is never a subclass, a
runtime, an executor, or a permission grant.

## Related invariants

- LE-NODE-001 through LE-NODE-009
- LE-CONFIG-001, LE-CONFIG-002
- LE-PERM-001
- LE-VERSION-001

See `docs/architecture/CONSTITUTION.md` and `architecture.yaml`.
