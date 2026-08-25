# Contract index

This page points to the contract objects that the current runtime uses. It is
an index, not another specification. The linked code is authoritative for
implemented behavior. The [architecture drift audit](../architecture/LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md)
records the remaining consolidation work.

The [taxonomy, ontology, and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
shows how these contracts fit into one Loop hierarchy.

## Contract map

| Boundary | Current contract objects | Status | Remaining consolidation gap |
|---|---|---|---|
| Loop identity, profile, and configuration | [`LoopRoleIdentity` and `LoopRelationship`](../../src/loop_engine/loop/loop_role.py), [`LoopProfileRef` and `LoopProfileSpec`](../../src/loop_engine/loop/loop_profile_catalog.py), [`LoopProfileBindingRequest`](../../src/loop_engine/loop/loop_profile_ontology.py), [`LoopConfig`](../../src/loop_engine/loop/recursive_loop.py), [`LoopContract`](../../src/loop_engine/loop/loop_contract.py), and [`EffectiveLoopSpec`](../../src/loop_engine/loop/effective_spec.py) | Partially consolidated. Role, relationship, profile, mode policy, conditions, and typed role names have dedicated objects. | One immutable, versioned, digest-bound `LoopDefinition` does not yet combine these fields. The `Loop` constructor does not yet require one registered bound definition. |
| Typed ports and edges | [`LoopPortBinding`, `LoopConnectionSpec`, and `validate_loop_connection`](../../src/loop_engine/loop/loop_contract.py), [`LoopPortValue`](../../src/loop_engine/loop/delegation_runtime.py), and [`LoopPortRef` and `LoopEdgeSpec`](../../src/loop_engine/code_nodes/solution_graph.py) | Role-name compatibility is checked before selected connections run. Delegation carries immutable values. | Port roles are strings. A versioned `PortSpec` must still define schemas, shapes, units, optionality, encodings, and value validation at every edge. |
| Graph definition | [`LoopGraphSpec`](../../src/loop_engine/code_nodes/solution_graph.py), [`SolutionSpec`](../../src/loop_engine/code_nodes/solution_canvas.py), and [`Canvas`](../../src/loop_engine/loop/canvas.py) | Several graph records exist and selected paths validate adjacent contracts. | There is no single authoritative `LoopGraphDefinition`. Every executable vertex must resolve an exact versioned and digest-bound Loop definition. Solution Canvas and run views should become projections of that graph. |
| Spawned Loop delegation | [`DelegationSpec`, `SpawnedTaskManager`, `SpawnedExecutionRequest`, and `SpawnedLoopResult`](../../src/loop_engine/loop/delegation_runtime.py), plus [`SpawnedTaskCheckpoint`](../../src/loop_engine/loop/spawned_task_checkpoint.py) | Typed spawning, private context, budgets, lifecycle control, cancellation, and durable task metadata are implemented. | The built-in executor is deterministic. Standard hybrid and non-deterministic executors still need to use the same Model Gateway, runtime context, limits, and event log. |
| Static Architecture capabilities | [`CapabilityHandshake`](../../src/loop_engine/static_architecture/capability_directory.py), the [Retrieval Engine](../../src/loop_engine/static_architecture/retrieval.py), the [Brave Web Research example](../../src/loop_engine/static_architecture/brave_search.py), and [`McpServerSpec` and `McpCallRequest`](../../src/loop_engine/static_architecture/mcp_adapter.py) | Intelligence Search and Retrieval, Web Research, and manually registered Custom Plugins have typed discovery or request boundaries. | One shared capability-handshake version policy is still missing. External retrieval registration and automatic plugin discovery are not shipped. |
| Internal runtime mechanics | [`ModelGatewayConfig`, `ModelGatewayRequest`, and `ModelGatewayResult`](../../src/loop_engine/static_architecture/model_gateway.py), [`WorkspaceSpec`](../../src/loop_engine/static_architecture/workspace_contracts.py), and [`EffectSpec` and `ApprovalRequest`](../../src/loop_engine/loop/effect_approval.py) | Model access, workspaces, and approvals use typed internal requests and policies. They support Loops but are not peer Static Architecture groups. | A standard permission-limited `LoopRuntimeContext` does not yet give every Loop the same internal service ports. Missing required mechanics do not yet fail through one common preflight. |
| Run History and event log | [`LoopLedger`](../../src/loop_engine/loop/recursive_loop.py), [`RunHistory` and `RunHistoryEvent`](../../src/loop_engine/static_architecture/run_history.py), and the [reports and playback guide](../guides/reports.md) | One run can save ordered, hash-linked events for reports and playback. Current records use semantic Loop relationships. | One full relationship-DAG projection is still missing. Every event must resolve to the same versioned Loop and graph definitions used at execution time. |
| Settings | [`RuntimeSettings`, `LoopDefaults`, `ModelSettings`, and `ModelTier`](../../src/loop_engine/static_architecture/runtime_settings.py), the [settings loader](../../src/loop_engine/static_architecture/settings_loader.py), and the [settings guide](../guides/settings.md) | YAML and environment loading produce typed provider, model, search, and Loop defaults. | Settings are not yet one versioned object bound into every Loop definition and instance. Per-run overrides still need one typed compatibility check against the selected profile, mode, budget, and permissions. |

## Required direction

The target is one definition and one graph:

```text
LoopDefinition
├── identity and semantic version
├── exact role profile
├── typed input and output PortSpecs
├── supported modes and installed executors
├── step profile
├── settings schema
├── loop condition and exit condition
├── budgets, permissions, and effects
├── required Static Architecture capabilities
├── required internal runtime mechanics
└── Run History event contract

LoopGraphDefinition
├── versioned LoopDefinition references
├── explicit typed edges
├── graph inputs and outputs
└── graph validation policy
```

A Loop instance selects one permitted mode. A Canvas, pipeline, or graph does
not inherit one mode. Every executable graph vertex must resolve a Loop
definition before execution.
