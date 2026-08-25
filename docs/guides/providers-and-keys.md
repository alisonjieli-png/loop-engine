# Providers and keys

Deterministic loops need no provider. Hybrid and non-deterministic loops use
`ModelGateway` when they need a language model.

## Built-in providers

| Provider | Environment variable | Meaning |
|---|---|---|
| Ollama Cloud | `OLLAMA_API_KEY` | Hosted Ollama API. |
| Mistral | `MISTRAL_API_KEY` | Mistral hosted API. |
| OpenRouter | `OPENROUTER_API_KEY` | OpenAI-compatible gateway to several upstream providers. |
| Custom endpoint | Supplied in `CustomEndpoint` | OpenAI-compatible or native Ollama server. |

Ollama Cloud is not local Ollama. Configure a local Ollama server as a custom
endpoint with `wire="ollama"` and `locality="local"`.

## Check configured providers

```python
from loop_engine import configure

access = configure()
print(access.explain())
```

`configure()` performs a small real call for each configured provider. A key is
reported as working only when the provider answers.

This check may consume tokens. Run it only when provider calls are authorized.

With no working provider:

```text
Modes available: deterministic
```

With at least one working provider:

```text
Modes available: deterministic, hybrid, non_deterministic
```

## Provider discovery and model classification

`ModelRoster` lists reachable models by three jobs:

| Role | Use |
|---|---|
| `decide_label` | Classification, routing, and short decisions. |
| `generate` | General generation work. |
| `reason` | Models whose provider declares reasoning support or higher cost. |

The classification uses provider catalog facts such as price, context length,
reasoning support, and tool support. It is a routing hint, not a measured
quality ranking.

## Use the model gateway

```python
from loop_engine import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
)

gateway = ModelGateway()
result = gateway.invoke(ModelGatewayRequest(
    "Return the safest next action as one JSON object.",
    ModelGatewayConfig(
        route_names=(
            "cloud.default",
            "cloud.mistral",
            "cloud.openrouter",
        ),
        max_route_attempts=3,
        max_total_tokens=4000,
    ),
))
```

Every physical attempt runs as a model loop. `result.attempts` keeps the
provider, model, route, split token usage, validation state, elapsed time, and
failure reason for each attempt.

The first successful valid result wins. If every provider fails, the gateway
returns a model failure. It does not substitute a deterministic answer and call
it a model result.

## Pin one provider

A provider comparison must pin one route:

```python
config = ModelGatewayConfig(
    route_names=("cloud.mistral",),
    allow_failover=False,
    max_route_attempts=1,
)
```

This keeps a Mistral arm from becoming an OpenRouter arm after failure.

## Use configured advice

```python
from loop_engine import advice_function

advise = advice_function(access)
if advise is not None:
    text, usage = advise("Which validation should run next?")
```

`advice_function()` uses `ModelGateway` and only the providers verified in the
supplied `ModelAccess` object.

## Token accounting

The gateway keeps input and output tokens separately. When the provider does
not return usage, the values remain `None`. They are not converted to zero.

```python
result.input_tokens
result.output_tokens
result.accounting_complete
```

A complete money ceiling still needs a versioned price record for each route.
The current gateway enforces physical call and provider-reported token limits.

## Standard configuration objects

- `ProviderSpec`
- `ModelProviderCapabilities`
- `ModelRoute`
- `RouteRegistry`
- `RoutePolicy`
- `ModelGatewayConfig`
- `ModelGatewayRequest`
- `ModelGatewayResult`
- `ReasoningRequest`
- `PromptAssemblySpec`
- `ModelInvocationRequest`
- `ModelInvocationResult`
- `OperatingProfile`
- `SolverConfig`

Read [Model gateway and provider configuration](../components/static-architecture/MODEL-GATEWAY.md)
for the complete object map and custom endpoint example.
