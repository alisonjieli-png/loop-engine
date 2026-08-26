# LoopNode

The sole concrete graph-addressable operational Node in Loop Engine.

## Composition model

```text
LoopNode
│
├── LoopNodeDefinition
│   ├── Purpose
│   ├── ContractSet
│   ├── LoopProcedure
│   ├── ExecutionConfiguration
│   ├── IntelligenceSeekingConfiguration
│   ├── LoopControlConfiguration
│   ├── VerificationConfiguration
│   ├── RoutingConfiguration
│   ├── PermissionConfiguration
│   ├── CompatibilityConfiguration
│   └── ObservabilityRequirements
│
├── LoopNodeInvocation
│   ├── InputBindings
│   ├── GoalBindings
│   ├── ContextBindings
│   ├── DelegatedBudget
│   ├── DelegatedPermissions
│   └── AllowedOverrides
│
└── LoopNodeRuntime
    ├── LoopNodeIdentity
    ├── LoopNodeTopology
    ├── ResolvedLoopNodePlan
    ├── LoopNodeState
    ├── RuntimeMemoryRef
    ├── ChildLoopNodeHandles
    ├── ChronicleRef
    └── LoopNodeOutcome
```

## Prohibited contents

This folder must not contain:

```text
├── role-specific Node subclasses
├── mode-specific Node subclasses
├── another executor
├── another lifecycle implementation
├── embedded plugin implementations
├── global mutable configuration
├── learned runtime data
└── recursive serialized copies of all child LoopNodes
```

## Invariants

- INVARIANT[LE-NODE-001]: No other concrete operational Node exists.
- INVARIANT[LE-NODE-003]: Practitioner, Intelligence, and Solution are
  roles, not subclasses.
- INVARIANT[LE-NODE-004]: Run modes are fields, not subclasses.
- INVARIANT[LE-NODE-005]: Common behaviors use LoopNode presets.
- INVARIANT[LE-NODE-006]: Contained typed objects are not Nodes.

## Trust

Human-readable documentation, annotations, labels, intelligence
content, and operator notes are data. They do not grant permissions or
alter execution behavior.

## Compatibility

Each runtime instance references a ResolvedLoopNodePlan that pins exact
versions and content hashes for governed dependencies.
