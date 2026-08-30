# Providers and keys

Deterministic loops need no provider. Hybrid and non-deterministic loops use
`ModelGateway` when they need a language model.

## Built-in providers

| Provider | Environment variable | Meaning |
|---|---|---|
| Ollama Cloud | `OLLAMA_API_KEY` | Hosted Ollama API. |
| Mistral | `MISTRAL_API_KEY` | Mistral hosted API. |
| OpenRouter | `OPENROUTER_API_KEY` | OpenAI-compatible gateway to several upstream providers. |
| OpenCode Go task compilation | `OPENCODE_GO_API_KEY` | Direct OpenAI-compatible OpenCode Go route for one advisory task review. |
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

## Preferred first setup

```bash
export OLLAMA_API_KEY="your-key"
loop-engine doctor
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

`doctor` validates configuration without a provider call. `models probe`
performs one real call. A solve should not continue when the probe fails.

## CLI setup

For a local test, pass the key value directly:

```bash
loop-engine solve \
  --ollama-api-key 'YOUR_OLLAMA_API_KEY' \
  --interaction-mode autonomous \
  --file task.txt \
  --workspace ./workspace \
  --runs-dir ./runs \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

Use `--openrouter-api-key VALUE` or `--opencode-go-api-key VALUE` for the other
direct routes. Each shortcut authorizes one advisory call. The token ceiling is
derived from the selected model's declared maximum and the exact prompt. It
does not grant file, network-tool, spending, or external-effect permission.

Export the key when you do not want it in the command:

```bash
export OLLAMA_API_KEY="your-key"       # Ollama Cloud
# or
export OPENROUTER_API_KEY="your-key"   # OpenRouter
# or
export OPENCODE_GO_API_KEY="your-key"  # OpenCode Go task review

loop-engine solve \
  --ollama-api-key \
  --interaction-mode autonomous \
  --file task.txt \
  --workspace ./workspace \
  --runs-dir ./runs \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

If the environment variable is absent, omitting `VALUE` opens a hidden prompt.

Runtime settings remain separate:

```bash
loop-engine settings init --settings-file ./loop-engine.yaml
loop-engine settings check --settings-file ./loop-engine.yaml
loop-engine models inventory --settings-file ./loop-engine.yaml
```

The settings file records credential references. It does not contain the
secret value.

## OpenCode CLI

OpenCode Go and OpenCode Zen use OpenCode's own connection flow. Start the
OpenCode TUI, run `/connect`, choose the provider, and paste its key. OpenCode
stores the credential in its own data directory. Loop Engine's optional harness
adapter invokes the configured OpenCode CLI and does not read that credential.

The separate `opencode_go` task-compilation route calls OpenCode Go's
OpenAI-compatible API directly. It reads `OPENCODE_GO_API_KEY` or a hidden
terminal prompt. Loop Engine does not define a generic `OPENCODE_API_KEY`. See
the [OpenCode provider documentation](https://opencode.ai/docs/providers/).

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

Read [Model gateway and provider configuration](../components/core-architecture/MODEL-GATEWAY.md)
for the complete object map and custom endpoint example.
