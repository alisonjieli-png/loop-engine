# External harness adapters

Loop Engine has one typed boundary for optional agent harness packages. Package
detection is not runtime integration proof. In this installation, none of the
four optional packages is available, so no package-backed adapter has run.

## Integration and comparison are separate

```text
Loop Engine
├── Normal Loop Engine execution
│   └── Practitioner, Intelligence, and Solution Loops run in Loop Engine
├── Optional external harness integration
│   └── One selected Loop delegates bounded work through a typed adapter
└── Published harness comparison research
    └── Reads source-backed published results and runs no competitor
```

The OpenML-CC18 and DS-1000 case studies used normal Loop Engine execution.
They did not call an external harness adapter.

The published comparison catalog also does not use these adapters. It reviews
results already published by harness authors or benchmark providers. See
[Compare published harness benchmark evidence](../../guides/complex-task-comparisons.md).

An adapter is useful only when a caller explicitly wants one Loop to use an
external package for bounded agent mechanics. Loop Engine still owns the task
contract, mode and effect policy, Intelligence references, provider identity,
model output maximum, physical-call accounting, independent evaluator,
Run History, and acceptance decision.

Today these are integration contracts with local protocol checks. They are not
four completed live integrations. Do not use their presence to claim that an
external package ran, improved a score, or participated in a case study.

Every request names the model provider and model separately from the harness.
It also carries an exact provider-backed maximum output record. An adapter may
execute only when it can pass that exact value to its model boundary. Otherwise
it reports unavailable or refuses before importing the package or calling a
model.

## Current built-in paths

| Adapter | Maximum-output boundary | Current status and wired behavior |
|---|---|---|
| Pydantic AI Harness | None verified | Built-in execution refuses before import. The adapter does not claim subagents, memory, skills, MCP, sandbox, or approvals. |
| Deep Agents | None verified | Built-in execution refuses before import. The adapter does not claim filesystem, compaction, memory, skills, MCP, sandbox, or approvals. |
| OpenAI Agents SDK | `ModelSettings.max_tokens` | The offline contract proves that the exact resolved maximum reaches this argument. It also wires a turn limit, usage reporting, and disabled tracing. Package-backed execution remains unproven here. |
| Microsoft Agent Framework | `create_harness_agent(max_output_tokens=...)` | The offline contract proves that the exact resolved maximum reaches this argument. It also wires a configured counted client, iteration limit, disabled web search, and disabled file memory. Package-backed execution remains unproven here. |

An injected runner is application code. It receives the resolved typed request,
but it is not evidence that the named package works. Normalization records
`max_output_tokens_used` only when a built-in boundary applied the value or an
injected runner returns a matching typed output-limit record.

## Output storage

An available adapter must receive a `ContextArtifactManager` through
`HarnessServices.artifact_store` before execution. Loop Engine stores the raw
text or canonical JSON output by digest first.

- Small output stays inline and retains a `HarnessArtifactRef` to the raw data.
- Large output is removed from the result body. The result contains the typed
  `HarnessArtifactRef` instead.
- An adapter-supplied `HarnessArtifactRef` must resolve in the same context
  artifact store and match its digest-derived object key.
- A missing manager refuses before the adapter runs.
- A storage or serialization failure becomes a typed failed result. It does not
  publish the uncaptured body.

The local contract tests use temporary directories, injected local runners, and
SDK argument builders. They do not install or import an optional harness, call a
model provider, or establish task quality.

```bash
PYTHONPATH=src python3 -c \
  "from loop_engine.static_architecture.external_harness import self_test; print(self_test())"
PYTHONPATH=src python3 -c \
  "from loop_engine.static_architecture.external_harness_adapters import self_test; print(self_test())"
```

Adapter completion remains separate from independent task acceptance.
