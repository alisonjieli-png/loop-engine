# Added-file extensions

Loop Engine can discover added files without changing its source code. The
files configure or propose work through existing authorities. They do not
create another runtime, registry, intelligence layer, or permission system.

## Roots and folders

```text
Extension roots
├── project: .loop-engine/extensions
├── user: ~/.config/loop-engine/extensions
├── environment: LOOP_ENGINE_EXTENSION_ROOTS
└── explicit: --extension-root PATH
    ├── providers/*.yaml
    ├── capabilities/*.yaml
    ├── skills/*/SKILL.md
    ├── plugins/*/loop-engine-plugin.json
    └── intelligence/
        ├── context/plugin/manifest.yaml
        ├── code/plugin/manifest.yaml
        ├── runtime_history_solution/plugin/manifest.yaml
        └── user_feedback/plugin/manifest.yaml
```

Absent conventional roots are normal. A missing explicitly configured root is
an error. Symlink roots and symlink extension files are refused.

## Resolution

```text
added files
→ deterministic Intelligence Loop discovery
→ schema, path, version, and digest checks
→ exact duplicate deduplication
→ conflicting identity refusal
→ ExtensionSnapshot
→ each item enters its existing authority
```

| Added file | Existing authority | Result after discovery |
|---|---|---|
| Provider route | `ProviderSettings` and `ModelGateway` | Inspectable exact route; eligible zero-price or local route activates when its required configuration exists. |
| Capability | Capability contracts and plugin/skill binding | Candidate description only. It cannot execute. |
| Skill | `SkillRegistry` and `SkillAdmissionRecord` | Candidate skill. Task use requires independent admission. |
| Plugin | `PluginBundleManifest` | Passive discovered bundle. Exact skill admissions still govern resolution. |
| Intelligence | `UnifiedCatalog` | Plugin-provenance candidate or validated record. It cannot self-register or self-promote. |

## Provider routes

A provider route file describes one exact provider and model. This matches the
current `ProviderSettings` contract instead of adding a provider-specific
runtime class.

```yaml
schema_version: provider_route_bundle/v2
bundle_id: zai_glm47_flash
version: 1.0.0
description: Reviewed zero-price Z.ai route.
sources:
  - kind: protocol
    url: https://docs.z.ai/api-reference/introduction
    observed_at: 2026-08-29
  - kind: model
    url: https://docs.z.ai/guides/llm/glm-4.7
    observed_at: 2026-08-29
  - kind: pricing
    url: https://docs.z.ai/guides/overview/pricing
    observed_at: 2026-08-29
provider:
  enabled: true
  auth:
    kind: bearer_env
    credential_env: ZAI_API_KEY
    header: ""
    plugin_ref: ""
  endpoint: https://api.z.ai/api/paas/v4
  model: glm-4.7-flash
  protocol: openai_chat
  locality: cloud
  counts_as_evidence: true
  maximum_output_tokens: 131072
  maximum_output_source: Z.ai model and API documentation
  purposes: [counted_generation, decide_label]
  headers: {}
routing:
  tiers: [medium, high]
  access_class: zero_price
pricing:
  input_cost_per_million: 0
  output_cost_per_million: 0
quota:
  scope: account
  requests_per_minute: null
  requests_per_day: null
  tokens_per_minute: null
  tokens_per_day: null
  concurrency: null
  credit_amount: null
  reset: provider_defined
capabilities: [text, structured_output, tools, reasoning, streaming]
data_policy:
  confidential_allowed: null
  training_use: unknown
  retention: provider_defined
  regions: []
health:
  catalog_refresh_seconds: 86400
  probe_timeout_seconds: 60
```

Provider access classes remain distinct:

```text
zero_price
→ provider facts say input and output price are zero
→ may auto-activate when its credential exists

recurring_quota
→ recurring free plan allowance
→ requires --allow-paid-extension-routes because billing may follow the quota

rolling_credit
→ recurring monetary credit rather than a zero-price model
→ requires --allow-paid-extension-routes

trial_credit
→ one-time or expiring promotional credit
→ requires --allow-paid-extension-routes because billing may follow the quota

community
→ volunteer or decentralized capacity with variable availability
→ requires --allow-paid-extension-routes and non-sensitive task policy

local
→ user-owned inference with no provider token charge
→ may auto-activate when the local route needs no credential

user_pays
→ a browser or signed-in end user owns usage and billing
→ never treated as a backend API key route

paid
→ known billable route
→ requires --allow-paid-extension-routes

unknown
→ no reliable price evidence
→ requires --allow-paid-extension-routes
```

Every provider bundle also carries one or more `sources` with a fact kind,
exact URL, and observation date. Supported source kinds are `protocol`,
`model`, `pricing`, `quota`, `data_policy`, and `model_metadata`. Discovery
fails when provenance is absent. The health policy says when a later authorized
operation should refresh provider facts; discovery itself remains offline.

The file may use non-secret endpoint variables such as
`${CLOUDFLARE_ACCOUNT_ID}`. Credential, token, password, key, secret, and auth
variables are prohibited in URL templates. Provider files cannot define
Authorization, API-key, cookie, or proxy-authorization headers. Credentials
come only from a declared environment variable or a reviewed authentication
adapter.

Authentication is independent from the wire protocol:

```text
bearer_env
→ secret is read from credential_env and sent as an Authorization bearer token

header_env
→ secret is read from credential_env and sent in the declared header
→ supports endpoints that require x-api-key, api-key, or another key header

none
→ no credential is sent

aws_sigv4, google_adc, azure_entra, browser_session, plugin
→ the route remains visible but inactive until a matching reviewed adapter is installed
```

Static `headers` are only for non-secret routing metadata. A secret header
must use `header_env`; its value never enters the manifest, settings summary,
Run History, or extension snapshot.

Provider manifests can describe `openai_chat`, `openai_responses`,
`anthropic_messages`, `gemini_generate_content`, `ollama_chat`, `cohere_chat`,
`bedrock_converse`, `bedrock_invoke`, `async_generate_poll`, and
`browser_user_pays`. The current generic gateway installs executors for
`openai_chat` and `ollama_chat` when authentication is `bearer_env`,
`header_env`, or `none`. Other protocol and authentication combinations remain
visible and inactive until a compatible adapter is installed.

## Capability candidates

Capability files describe a possible operation and how an admitted integration
could provide it.

```yaml
schema_version: capability_candidate/v1
capability_ref: plugin.example.summarize
version: 1.0.0
description: Candidate summarization capability.
input_roles: [text]
output_roles: [summary]
permissions: []
effects: []
implementation:
  kind: skill
  ref: summary-skill
tags: [summary]
lifecycle: candidate
```

Supported implementation references are `skill`, `mcp`, `external_service`,
and `sandbox_command`. Discovery does not load modules, run commands, contact
services, or admit the referenced implementation.

The Practitioner may see these candidates as unavailable possibilities. It
cannot select one as executable until a registered capability executor and the
required authority exist.

## Commands

```bash
loop-engine extensions discover
loop-engine extensions providers
loop-engine extensions capabilities
loop-engine extensions skills
loop-engine extensions plugins
loop-engine extensions intelligence
```

Use `--format json` for exact paths, versions, content digests, and inactive
route reasons. Discovery performs no provider call.

## Current boundary

This release discovers exact provider routes from files. It does not yet use a
generic live-catalog mapping file to create new route files automatically.
OpenRouter and OpenCode have provider-specific live free-model discovery, while
other providers use reviewed exact route files. A future catalog mapping must
remain an authorized provider-read operation and must write a new immutable
snapshot rather than silently changing a reviewed run.
