# Typed Loop connections

Loop Engine checks a connection before either Loop runs. The authoritative
graph stores exact Loop definitions and named input and output roles.

## Two levels of checking

`LoopContract` checks whether a producer role can feed a consumer role.
`LoopGraphDefinition` checks that every graph vertex resolves to a complete
definition, every edge names real ports, and the complete graph is acyclic.

```text
LoopDefinition
└── LoopContract
    ├── input_roles
    └── output_roles

LoopGraphDefinition
├── LoopGraphVertex with exact LoopDefinitionRef
├── LoopGraphEdge with source and target endpoints
├── graph input and output ports
└── graph validation
```

## Check two contracts

```python
from loop_engine.loop.loop_contract import (
    LoopConnectionSpec,
    LoopContract,
    validate_loop_connection,
)

prepare = LoopContract(
    name="prepare-features",
    execution_mode="code_only",
    input_roles=("raw_rows/v1",),
    output_roles=("feature_matrix/v1",),
    role="solution",
)

score = LoopContract(
    name="score-model",
    execution_mode="code_only",
    input_roles=("feature_matrix/v1",),
    output_roles=("scores/v1",),
    role="solution",
)

result = validate_loop_connection(
    LoopConnectionSpec(producer=prepare, consumer=score)
)

assert result.compatible
```

An empty binding list matches consumer inputs to producer outputs with the
same role name.

## Use an Adapter Loop for conversion

An edge carries a value. It cannot transform the value. Different role names
require a named Adapter Loop with its own definition, operation, tests, and
event history.

```python
from loop_engine.loop.loop_contract import LoopPortBinding

binding = LoopPortBinding(
    source_output="feature_matrix/v1",
    target_input="feature_matrix/v2",
    adapter_loop_ref="loop://adapters/features-v1-to-v2",
)
```

At the graph level, the Adapter is an explicit `LoopGraphVertex` with purpose
`adapter`. Two ordinary edges connect the producer to the Adapter and the
Adapter to the consumer. `LoopGraphEdge.metadata` rejects hidden callable,
script, command, operation, tool, and adapter fields.

## Build the authoritative graph

The graph API uses these immutable objects:

| Object | Purpose |
|---|---|
| `LoopDefinitionRegistry` | Resolves exact definition ID, version, and digest references. |
| `LoopGraphVertex` | Binds one executable vertex to a `LoopDefinitionRef`, selected mode, purpose, and operation reference. |
| `LoopGraphEndpoint` | Names one role on one vertex. |
| `LoopGraphEdge` | Connects source and target endpoints without executing hidden work. |
| `LoopGraphInputPort` | Maps an external typed input to one or more vertices. |
| `LoopGraphOutputPort` | Maps one vertex output to an external typed output. |
| `LoopGraphStage` | Groups a primary attempt and typed fallbacks. |
| `LoopGraphGroup` | Defines one pipeline, route, or ensemble under an explicit controller Loop. |
| `LoopGraphDefinition` | Binds the complete DAG to a semantic version and content digest. |

Each vertex either embeds its exact `LoopDefinition` or resolves it through a
`LoopDefinitionRegistry`. `validate()` refuses an unresolved reference or a
digest mismatch.

## What graph validation checks

Validation rejects:

- duplicate or unresolved vertices;
- changed definition content;
- a mode outside the definition, graph policy, or installed executors;
- a relationship that conflicts with the role or edge;
- a missing or incompatible input or output role;
- hidden conversion work on an edge;
- a fallback stage without an explicit Router Loop;
- a cycle;
- a graph input, output, stage, group, route, or evaluator that points to
  missing work;
- a graph whose serialized content does not match its digest.

## Current value-schema limit

Port roles are versioned names such as `feature_matrix/v1`. The graph checks
that those names match. It does not yet enforce every value property such as
array shape, unit, encoding, optional field, numeric range, or table column at
every connection.

Use a deterministic Validator Loop at important boundaries until the graph has
a shared versioned value-schema contract. See
[validate a customer import](../../examples/10_validate_customer_import/) for
a runnable Solution example.
