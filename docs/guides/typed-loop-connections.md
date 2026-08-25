# Typed loop connections

A graph can check whether one loop's output fits another loop's input before
either loop runs. The check uses the existing `LoopContract` on each loop.

## Two checks have different jobs

`LoopContract` describes the roles at a loop boundary. For example, a feature
loop can produce `feature_matrix/v1`, and a scoring loop can require
`feature_matrix/v1`.

`ContractDefinition` checks a concrete Python value. It can check field types,
required fields, allowed values, ranges, and row counts.

Use both checks:

1. Check the connection before execution.
2. Validate the concrete value when the producer returns it.

The first check prevents invalid wiring. The second check prevents invalid data
from crossing a valid wire.

## Check one connection

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
)

score = LoopContract(
    name="score-model",
    execution_mode="hybrid",
    input_roles=("feature_matrix/v1",),
    output_roles=("scores/v1",),
)

connection = LoopConnectionSpec(producer=prepare, consumer=score)
result = validate_loop_connection(connection)

assert result.compatible
```

An empty `bindings` tuple asks Loop Engine to match inputs and outputs with the
same role name. Use an explicit binding when you want to check one port.

## Require an Adapter Loop for a conversion

Different role names do not connect by accident. Name the Adapter Loop that
performs the conversion.

```python
from loop_engine.loop.loop_contract import LoopPortBinding

score_v2 = LoopContract(
    name="score-model-v2",
    execution_mode="hybrid",
    input_roles=("feature_matrix/v2",),
    output_roles=("scores/v1",),
)

binding = LoopPortBinding(
    source_output="feature_matrix/v1",
    target_input="feature_matrix/v2",
    adapter_loop_ref="loop://adapters/features-v1-to-v2",
)

connection = LoopConnectionSpec(
    producer=prepare,
    consumer=score_v2,
    bindings=(binding,),
)
```

The adapter reference does not prove that the conversion is correct. The
Adapter Loop still needs its own contract, tests, and value validation.

## Validate a graph against its loops

A typed graph uses `LoopVertexSpec` to attach each `LoopContract` to its loop
reference. `LoopGraphSpec.validate()` then checks every edge against both loop
contracts.

```python
from loop_engine.code_nodes.solution_graph import (
    LoopEdgeSpec,
    LoopGraphSpec,
    LoopPortRef,
    LoopVertexSpec,
)

graph = LoopGraphSpec(
    "customer-risk",
    edges=(
        LoopEdgeSpec(
            LoopPortRef("prepare", "features", "feature_matrix/v1"),
            LoopPortRef("score", "features", "feature_matrix/v1"),
        ),
    ),
    vertices=(
        LoopVertexSpec("prepare", prepare),
        LoopVertexSpec("score", score),
    ),
)

report = graph.validate()
assert report["valid"]
```

Validation refuses an edge when:

- the producer does not declare the edge's output role;
- the consumer does not declare the edge's input role;
- the roles differ and no Adapter Loop is named;
- an edge names a loop outside the graph;
- the graph contains a cycle.

String-only `loop_refs` remain supported for existing callers. Add typed
vertices when the graph must verify actual loop contracts.

## Current limit

The graph check validates declared compatibility. It does not run a loop,
inspect a value, or establish that two equal role names have the same meaning.
Use versioned role names, register concrete `ContractDefinition` objects, and
test each producer and adapter against those definitions.
