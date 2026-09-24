# Providers and keys

Deterministic loops need no provider. Hybrid and non-deterministic loops use
`ModelGateway` when they need a language model.

## Built-in providers

| Provider | Environment variable | Meaning |
|---|---|---|
| Ollama Cloud | `OLLAMA_API_KEY` | Hosted Ollama API. |
| Mistral | `MISTRAL_API_KEY` | Mistral hosted API. |
| OpenRouter | `OPENROUTER_API_KEY` | OpenAI-compatible gateway to several upstream providers. |
| OpenCode Zen zero-cost shortcut | `OPENCODE_ZEN_API_KEY` | Resolves one current zero-cost OpenAI-compatible model for the run. |
| OpenCode Go task compilation | `OPENCODE_GO_API_KEY` | Direct OpenAI-compatible OpenCode Go route for one advisory task review. |
| Custom endpoint | Supplied in `CustomEndpoint` | OpenAI-compatible or native Ollama server. |

Ollama Cloud is reachable two ways: through the built-in `ollama_cloud`
provider (its key comes from `OLLAMA_API_KEY` in the environment or the
repository `.env`; a `credential_env` on a `kind: builtin` provider is recorded
but the built-in adapter reads its own variable), or as a `kind: custom`
provider at `https://ollama.com` with `wire: ollama`, whose key comes from the
variable its `credential_env` names. A local Ollama server is the same custom
endpoint at its own URL, such as `http://127.0.0.1:11434`; `locality` is
descriptive only and changes no behaviour. On the Ollama wire both paths send
`think: false` unless the declaration says otherwise (`think: on`, or
`think: model` to leave the model's default), because a reasoning model spends
the output ceiling thinking before it answers. A model that cannot run
without thinking refuses `think: false` with HTTP 400, which the gateway
classifies as `invalid_request` (a configuration fault that stops the route,
naming the reason); declare `think: model` for such a model. A custom
provider whose `credential_env` variable is unset refuses before sending a
request, as the built-in adapters do.

A model enters the universe only with a source-backed output maximum
(`MODEL_OUTPUT_CAPABILITIES` in the built-in adapter, or `max_output` with
its source on a custom endpoint); generation on a model without one is
refused as `unknown_model_output_limit`, never run at a guessed ceiling.
`ollama_client.learn_output_capability(model)` asks the service to name a
model's ceiling: one streamed request for far more output than any model
allows, on the OpenAI-compatible path, where a refusal names the exact
maximum (the source every table entry already cites). Only a refusal that
names exactly one number yields a capability; an accepted request is closed
on its first byte and recorded as acceptance without a ceiling, since a
server may clamp silently. `learn_output_capabilities(models)` does this for
a listing and stops at the first refusal by allowance or credential. On
September 14, 2026 it read the maxima of the thirteen listed models that
lacked one, so all nineteen models Ollama Cloud lists carry a source-backed
maximum in the built-in table.

The model listing (`/api/tags`) is not readiness: on the evening of
September 13, 2026 the key listed twenty models while every generation was
refused with HTTP 429 "weekly usage limit" and no `Retry-After`. The gateway
names that refusal `usage_limit_reached`, an allowance that resets on the
provider's calendar, apart from `rate_limited`, a throttle that clears in
seconds.

## GPT-6 Astra adapter status

The repository contains an offline-tested, text-only OpenAI Responses adapter
for `gpt-6-astra`. It is not in the default route table, provider discovery,
failover order, tiers, or runtime settings. Setting `OPENAI_API_KEY` therefore
does not activate it or authorize paid use.

The adapter has 21 of 21 local contract checks. A separate demand, pricing,
availability, locality, capability, and candidate-authority policy has 38 of 38
offline checks. Both suites made zero provider calls and read no credential.
The policy is hard-quarantined and cannot construct an executable route. It
still needs issued one-use spending authority, trusted-clock availability,
exact adapter and credential binding, invocation-budget enforcement, an
authorized live probe, and a bounded product-path test. Tool calls, structured
output, async tools, and mid-turn steering are not implemented. See the dated
[GPT-6 Astra readiness note](../context/GPT-6-ASTRA-READINESS-2026-09-04.md).

## Library provider verification

The CLI command `loop-engine configure` only inspects credential references.
It makes zero provider calls. The Python helper below is a different,
explicit verification operation and does contact configured providers.

```python
from loop_engine import configure

access = configure()
print(access.explain())
```

`configure()` performs a small real call for each configured provider. A key is
reported as working only when the provider answers.

This check may consume tokens. Run it only when provider calls are authorized.

## Add an OpenAI-compatible provider with one file

Copy a reviewed `provider_route_bundle/v2` YAML file into:

```text
.loop-engine/extensions/providers/
```

Then inspect the route without contacting it:

```bash
loop-engine extensions providers
loop-engine models inventory
```

The repository includes reviewed example templates for Z.ai, Groq, Gemini,
Cerebras, and Cloudflare under
[`examples/23_drop_in_extensions/provider_templates/`](../../examples/23_drop_in_extensions/provider_templates/).
Availability and pricing can change. Review the cited provider source before
copying a template.

See [Provider endpoint landscape](provider-endpoint-landscape.md) for the
supported protocol and authentication families, additional compatible
services, and the difference between zero price, a recurring quota, trial
credit, local inference, community capacity, and user-pays access.

Only exact zero-price routes activate automatically when their credential is
present. Free-plan quotas, trial credits, paid routes, and unknown prices need
`--allow-paid-extension-routes` because charges may begin after the allowance.

### Custom endpoint TLS policy

A `kind: custom` provider in the settings file declares how its certificate is
verified. `tls_verification: default` uses the system trust store.
`tls_verification: ca_file` with `tls_ca_file: /path/to/root.pem` trusts one
declared private authority and keeps hostname checking on; use it for an
origin that serves a private or Cloudflare Origin CA certificate.
`tls_verification: skip` disables verification for exactly that endpoint and
exposes the bearer key to anyone on the network path, so prefer `ca_file`. The
selected policy appears in `loop-engine configure`, in the provider
description, and as a `tls_verification_policy` event in the run's model
routing history.

Two more fields finish the trust for an origin reached by one name that
presents a certificate for another. `tls_server_name` is the name the
certificate must prove; the connection still goes to the endpoint host.
`tls_pinned_sha256` is the SHA-256 of the leaf certificate, for example the
value `openssl x509 -noout -fingerprint -sha256` prints, colons allowed. Both
are accepted by `CustomEndpoint`, `ProviderSettings`, `LOOP_ENGINE_ENDPOINTS`
and a generation provider binding; the settings file does not accept them
yet. An endpoint with `ca_file`, a server name or a pin must use `https://`,
follows no redirect and refuses plain HTTP. A server that cannot prove the
declared identity is refused with `tls_trust_refused` before the request
line, the headers or the key are sent, and the attempt counts zero physical
requests.

Select a settings-declared provider for a solve with
`--compile-provider <provider_id>`; for a `kind: custom` provider the key is
read from that provider's `credential_env` variable, and for a built-in
provider from the variable the built-in adapter owns.

## Preferred first setup

```bash
export OLLAMA_API_KEY="your-key"
loop-engine doctor
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --allow-unbounded-total-tokens
```

`doctor` validates configuration without a provider call. `models probe`
performs one real call. A solve should not continue when the probe fails.

The example explicitly permits that one call without a total-token ceiling;
the route's known output capacity and timeout still apply. It may incur
charges. A strict `--max-total-tokens` policy requires a qualified exact-request
bound. Missing qualification causes a pre-dispatch refusal; a larger guessed
number does not supply the missing bound.

## CLI setup

Export one key, inspect it without a call, probe it once, then use the bounded
quickstart profile:

```bash
export OLLAMA_API_KEY="your-key"       # Ollama Cloud
# or
export MISTRAL_API_KEY="your-key"      # Mistral
# or
export OPENROUTER_API_KEY="your-key"   # OpenRouter
# or
export OPENCODE_ZEN_API_KEY="your-key" # OpenCode Zen zero-cost catalog
# or
export OPENCODE_GO_API_KEY="your-key"  # OpenCode Go task review

loop-engine configure
loop-engine solve --file task.txt --quickstart
```

For a disposable terminal session, the direct key flags are
`--ollama-api-key`, `--mistral-api-key`, `--openrouter-api-key`,
`--opencode-zen-api-key`, and `--opencode-go-api-key`. Omitting the value reads
the standard environment variable or opens a hidden prompt.

The OpenRouter and OpenCode Zen shortcuts accept a route only when current
catalog facts establish an exact compatible zero-cost model and output limit.

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

## Permit failover on one solve path

Quickstart selects one configured provider. Add the failover policy when that
provider has more than one exact route with a source-backed output contract:

```bash
loop-engine solve --file task.txt --quickstart --allow-model-failover
```

The selected route runs first. A retryable network, availability, timeout,
incomplete-response, empty-response, output-limit, or validation failure may
continue to the next authorized route. Authentication, invalid-request, and
model-identity failures remain refusals. An explicit `--model-id` remains
pinned and disables alternate model selection.

This is one `ModelGateway` policy inside the same solve. It does not create a
second solve runtime or silently substitute deterministic output for a failed
model call. Every physical attempt retains provider, exact model, route,
completion reason, usage, elapsed time, and failure code.

Cross-provider failover uses an authorized settings route plan with each
provider credential available to the current process. A key supplied in an
older shell or process is not automatically available in a later process.

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
