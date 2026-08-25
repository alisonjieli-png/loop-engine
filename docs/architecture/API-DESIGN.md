# Typed API design

Loop Engine uses typed request, configuration, contract, and result objects at
operational boundaries. A public function should not expose a long list of
values that several callers must keep in the same order.

## Main rules

1. Group values that change together in one frozen data class.
2. Give loop inputs and outputs named, versioned roles.
3. Validate a graph connection before either loop executes.
4. Keep permissions, effort, model thinking power, and step profile separate.
5. Return one typed result that preserves failures and unknown values.
6. Keep compatibility wrappers thin and point new code to the typed path.

Examples in the current runtime include:

| Boundary | Typed objects |
|---|---|
| Loop definition and start | `LoopDefinition`, `LoopDefinitionRef`, `LoopStartRequest` |
| Loop services | `LoopRuntimeContext`, `InternalRuntimeMechanics` |
| Static DAG | `LoopGraphDefinition`, `LoopGraphVertex`, `LoopGraphEdge` |
| Runtime defaults | `RuntimeSettings`, `LoopConfigOverride` |
| Model work | `ModelTask`, `ModelPolicyRequest`, `ModelGatewayRequest` |
| Provider-pinned work | `ProviderPinnedRequest` |
| Campaign execution | `CampaignSpec`, `CampaignRunOptions` |
| Context classification | `ContextFacetSpec` |
| Loop connection | `LoopConnectionSpec`, `LoopPortBinding`, `LoopConnectionResult` |

## Parameter cap

Conformance limits a new public function or method to nine visible
parameters. A smaller signature is preferred. The cap catches interfaces that
need a typed object before they spread to more callers.

The repository still has named legacy exceptions. Each exception in
`src/loop_engine/forbidden_paths.json` includes a replacement plan. A new
exception should not be added to make a check pass. Refactor the boundary or
explain why it implements a common low-level provider protocol.

Run the checks:

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

## Typed loop connections

A producer loop declares output roles. A consumer loop declares input roles.
`validate_loop_connection()` checks both contracts before execution. Different
role names require a named Adapter Loop.

Read [Typed loop connections](../guides/typed-loop-connections.md) for a worked
example.
