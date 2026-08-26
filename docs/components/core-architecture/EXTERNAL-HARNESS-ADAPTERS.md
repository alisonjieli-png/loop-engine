# External harness adapters

Loop Engine has one typed boundary for optional agent harness packages. Package
detection does not prove that an adapter works. None of the four optional
packages is installed in the verified environment, so no package-backed
adapter has run there.

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

Every request names the provider and model separately from the harness. It also
carries the exact provider-backed output maximum. `HarnessRuntimeBinding`
connects that identity to one configured SDK model or client. The binding uses
a non-secret configuration reference. A mismatched provider, model, SDK object
kind, or output maximum fails before package import or model use.

## Current built-in paths

| Adapter | Maximum-output boundary | Current status and wired behavior |
|---|---|---|
| Pydantic AI | `ModelSettings.max_tokens` | The adapter also passes request and total-token limits through `UsageLimits`. It requires a provider-bound SDK model. Package-backed execution remains unproven in the verified environment. |
| Deep Agents | `HarnessRuntimeBinding.output_limit` | Deep Agents has no single run argument for this value. The supplied SDK model must already enforce the exact maximum. The adapter disables application tools, skills, memory, and subagents, then applies a bounded graph recursion limit. Package-backed execution remains unproven. |
| OpenAI Agents SDK | `ModelSettings.max_tokens` | The adapter requires a provider-bound SDK model. It also applies a turn limit, requests usage data, and disables SDK tracing. Package-backed execution remains unproven. |
| Microsoft Agent Framework | `create_harness_agent(max_output_tokens=...)` | The adapter wraps a provider-bound client with a physical call ceiling. It disables web search, file memory, compaction, todos, mode management, and automatic tool approval. Package-backed execution remains unproven. |

The package paths contain current SDK calls, but local tests stop at the typed
boundaries. They do not substitute a fixture response for a real provider run.
An integration claim still needs the optional package, a real configured
provider, recorded usage, and an independently checked task result.

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

The local contract tests use temporary directories, injected local runners,
provider-binding checks, and SDK argument builders. They do not install an
optional harness, call a model provider, or establish task quality.

```bash
PYTHONPATH=src python3 -c \
  "from loop_engine.core.external_harness import self_test; print(self_test())"
PYTHONPATH=src python3 -c \
  "from loop_engine.core.external_harness_adapters import self_test; print(self_test())"
```

Adapter completion remains separate from independent task acceptance.

## SDK references

The package calls follow the current primary documentation:

- [Pydantic AI model settings](https://ai.pydantic.dev/agent/#model-run-settings)
- [Deep Agents model configuration](https://docs.langchain.com/oss/python/deepagents/models)
- [OpenAI Agents `ModelSettings`](https://openai.github.io/openai-agents-python/ref/model_settings/)
- [Microsoft Agent Framework harness](https://github.com/microsoft/agent-framework/tree/main/python/samples/02-agents/harness)

The [saved ABI check](../../evidence/external-harness-abi-check-2026-08-25.json)
records current package versions, separately checked SDK signatures, failed
combined dependency resolution, and the limits of those checks.
