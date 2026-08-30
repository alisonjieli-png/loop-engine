# Provider endpoint landscape

This guide separates wire compatibility from price. A service can speak the
same API as another service while using different models, quotas, privacy
terms, or billing rules.

The review date for this page is 2026-08-29. Provider catalogs and free access
change often. A provider file is a reviewed snapshot, not a permanent promise
that a model is free or reachable.

## Endpoint families

```text
Model endpoint
├── OpenAI-compatible
│   ├── Chat Completions
│   └── Responses
├── Provider-native message API
│   ├── Anthropic Messages
│   ├── Gemini generateContent
│   ├── Cohere Chat v2
│   └── Ollama native chat
├── Cloud-authenticated API
│   ├── Amazon Bedrock Converse or Invoke
│   ├── Microsoft Foundry with Entra ID or API-key auth
│   └── Google Cloud with application credentials
├── Asynchronous submit-and-poll API
├── Browser or signed-in user-pays API
└── Local OpenAI-compatible server
```

Loop Engine can execute `openai_chat` and `ollama_chat` provider files today.
It can record the other families without pretending that the current generic
adapter can execute them.

## Authentication families

| Manifest value | Current behavior |
|---|---|
| `bearer_env` | Reads one environment variable and sends a bearer token. |
| `header_env` | Reads one environment variable and sends it in a named header such as `x-api-key` or `api-key`. |
| `none` | Sends no credential. Useful for local and documented keyless endpoints. |
| `aws_sigv4` | Declared and inspectable. Needs a reviewed signing adapter. |
| `google_adc` | Declared and inspectable. Needs a reviewed application-credentials adapter. |
| `azure_entra` | Declared and inspectable. Needs a reviewed Entra token adapter. |
| `browser_session` | Declared and inspectable. It is not treated as a backend API key. |
| `plugin` | Names a reviewed plugin authentication adapter. Discovery alone does not execute it. |

Secrets never belong in provider YAML, endpoint URLs, static headers, settings
summaries, extension snapshots, or Run History.

## Services that fit the current generic adapter

The following services publish an OpenAI-compatible Chat Completions route or
can expose one. Most use bearer authentication. Microsoft Foundry also has
API-key-header variants.

| Service family | Compatibility source | Access note |
|---|---|---|
| Z.ai | [API overview](https://docs.z.ai/api-reference/introduction) | Some exact models may be zero-price. Verify current model pricing. |
| Groq | [OpenAI compatibility](https://console.groq.com/docs/openai) | A Free Plan exists, with model-specific limits. |
| Google Gemini | [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) | Free and paid tiers are project and model dependent. |
| Cloudflare Workers AI | [OpenAI compatibility](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/) | Account ID is part of the endpoint. Free allocation and paid use are separate states. |
| OpenRouter | [API reference](https://openrouter.ai/docs/api/reference/overview) | Free model availability rotates. Loop Engine resolves exact zero-price candidates from the live catalog. |
| Vercel AI Gateway | [OpenAI compatibility](https://vercel.com/docs/ai-gateway/openai-compat) | Gateway credit is not the same as a zero-price model. |
| Mistral | [API reference](https://docs.mistral.ai/api/) | Free mode and paid mode must remain distinct. |
| SambaNova Cloud | [API overview](https://docs.sambanova.ai/cloud/docs/api-reference/overview) | Limits depend on the account and model. |
| OpenCode Zen | [Zen models](https://opencode.ai/docs/zen/) | The service generally charges per request. Loop Engine accepts a zero-cost route only when the live list and typed metadata both establish it for that run. |
| NVIDIA NIM | [API reference](https://docs.api.nvidia.com/nim/reference/) | Developer endpoints and limits are model dependent. |
| Hugging Face Inference Providers | [OpenAI client guide](https://huggingface.co/docs/inference-providers/guides/openai) | Monthly credit and routed providers can change. |
| Pollinations | [Official repository](https://github.com/pollinations/pollinations) | Treat account, Pollen, and model terms as changing provider facts. |
| DeepInfra | [OpenAI-compatible API](https://docs.deepinfra.com/api-reference/introduction) | The current docs describe usage-priced inference. Do not label it free without account evidence. |
| Fireworks AI | [API concepts](https://docs.fireworks.ai/getting-started/concepts) | OpenAI and Anthropic shapes exist. Current serverless routes are priced unless a separate plan says otherwise. |
| Nebius Token Factory | [API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction) | OpenAI-compatible. Account credit and prices need live inspection. |
| OVHcloud AI Endpoints | [OpenAI-compatible example](https://help.ovhcloud.com/csm/en-ie-public-cloud-ai-endpoints-function-calling?id=kb_article_view&sysparm_article=KB0071914) | Official examples include limited anonymous access and authenticated access. |
| Local Ollama | [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) | Local compute. No hosted token price, but hardware and electricity are not zero cost. |
| LM Studio, vLLM, llama.cpp, LocalAI | Their OpenAI-compatible server documentation | Local or self-hosted. The endpoint owner supplies exact model and output-limit facts. |

An OpenAI-compatible label is not enough by itself. The route still needs an
exact model, output maximum, credential reference, price class, data policy,
and supported capability list.

## Services that need another adapter

These are common standards, not edge cases:

- Anthropic's direct API uses `POST /v1/messages`, `x-api-key` or bearer
  authentication, and a required API version header. See the
  [official API overview](https://platform.claude.com/docs/en/api/overview).
- Cohere Chat v2 uses its own response shape even though Cohere also offers
  compatibility surfaces. See the
  [Chat v2 reference](https://docs.cohere.com/v2/reference/chat).
- Amazon Bedrock supports Converse, Invoke, OpenAI-compatible Chat
  Completions and Responses, and Anthropic Messages. Authentication and
  endpoint choice still matter. See
  [Bedrock API families](https://docs.aws.amazon.com/bedrock/latest/userguide/apis.html).
- Microsoft Foundry offers OpenAI v1 routes, API-key headers, and Entra ID.
  See the
  [endpoint guide](https://learn.microsoft.com/en-us/azure/ai-studio/ai-services/concepts/endpoints).
- Browser user-pays APIs and volunteer compute APIs have different identity,
  privacy, availability, and retry semantics from a backend provider key.
- Submit-and-poll services need job identity, polling limits, cancellation,
  and terminal-state handling. They should not be forced through a synchronous
  Chat Completions adapter.

## Free access is not one state

Loop Engine records these access classes separately:

```text
zero_price
recurring_quota
rolling_credit
trial_credit
community
local
user_pays
paid
unknown
```

Only source-backed zero-price routes and local routes enter automatic tiers by
default. Other access classes remain visible but need explicit opt-in. This
prevents an exhausted free allowance from silently becoming a paid call.

## Providers not yet shipped as reviewed templates

Lists on forums and aggregator sites also mention services such as Aion Labs,
LLM7, BazaarLink, Gaia nodes, AI Horde, ModelScope, SiliconFlow, Baidu,
Alibaba Model Studio, and regional gateways. They can be useful, but Loop
Engine should not ship a reviewed route file until current first-party sources
establish:

- the exact endpoint and protocol;
- authentication and regional requirements;
- whether access is recurring, promotional, community, or paid;
- the exact model and maximum output;
- retention and training policy;
- failure and quota behavior.

Users can still add a provider file immediately. Unsupported protocol or auth
combinations remain inspectable and return a clear inactive reason.
