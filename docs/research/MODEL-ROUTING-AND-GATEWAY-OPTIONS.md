# Model routing and gateway options

Checked on 2026-08-25 against official documentation and repositories.

Loop Engine already has a provider-neutral invocation boundary in
`ModelGateway`. It should keep that boundary. The missing part is a separate
model-selection policy that chooses a logical model tier before the gateway
makes a call.

## Keep three decisions separate

These decisions solve different problems:

1. **Mode selection** decides whether a loop is deterministic, hybrid, or
   non-deterministic.
2. **Model selection** chooses a model tier and specialization for a model
   step.
3. **Provider execution** sends the request, applies timeouts, and handles
   provider failures.

A provider outage must not silently become a request for a stronger model.
Provider failover should try another endpoint for the same approved model or
equivalent route. Model escalation should happen only after a typed quality
failure, an explicit task requirement, or a verifier failure. Both need their
own limits and event records.

## Recommended Loop Engine shape

Add a small policy interface in front of `ModelGateway`. Do not put model
selection inside provider adapters.

```text
Loop mode policy
    -> ModelSelectionRequest
    -> ModelSelectionPolicy
    -> ModelSelectionDecision
    -> ModelGatewayRequest
    -> ModelGateway
    -> ProviderAdapter
```

`ModelSelectionRequest` should carry the task type, input and output
contracts, requested thinking power, optional specialization, permitted
localities, privacy rules, budget, and prior typed failures.

`ModelSelectionDecision` should carry the selected tier, ordered route names,
selection rule, policy version, confidence when one exists, estimated routing
overhead, and allowed escalation steps. This gives the Run History a clear
answer to "why did this model run?"

Use four ordered thinking-power tiers: `small`, `medium`, `high`, and `max`.
Treat specialization as a separate field such as `code`, `legal`, `vision`, or
`local_private`. A specialized model is not always stronger than a general
model.

Provider parameters such as Ollama's `reasoning_effort` are also separate.
The selected route may translate the Loop Engine tier into a provider-specific
reasoning setting when that provider and model support it. Ollama's
[OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility)
accepts `none`, `low`, `medium`, and `high` reasoning effort for supported
thinking models.

## Default selection order

Use the cheapest decision method that has earned authority on the current
task population:

1. An explicit route pinned by the caller.
2. A deterministic rule based on the loop profile, contract, task type,
   privacy, and limits.
3. A local classifier that can abstain.
4. A learned router calibrated on accepted Loop Engine runs.
5. A hosted router, only when its added call, disclosure, and latency are
   allowed and measured.

The router must not cost more than it saves. Record selection latency,
selection tokens, route changes, task result, and final provider cost as
separate fields. Compare the router against a fixed-route baseline on the same
frozen tasks and evaluator.

## Option review

| Option | What it is | Overhead and control | Fit with `ModelGateway` | Decision |
|---|---|---|---|---|
| Loop Engine deterministic policy | Local rules over typed request fields and prior accepted results | No model call and no network request | Native policy before invocation | **Adopt now** |
| [LiteLLM](https://docs.litellm.ai/docs/routing) | Python SDK and self-hosted proxy for provider access, load balancing, retries, cooldowns, and fallback | A proxy hop. Some strategies need Redis. Its documentation warns that usage-based routing adds significant latency from Redis operations. | Expose a LiteLLM proxy as one OpenAI-compatible provider. Disable nested retries or import its attempt telemetry. | **Wrap, do not require** |
| [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) | Hosted provider selection for a chosen model, with ordering, price, latency, throughput, privacy, and fallback controls | One hosted inference path. Internal provider fallback can hide physical attempts unless metadata is requested. | Keep the model choice in Loop Engine. Request [router metadata](https://openrouter.ai/docs/guides/features/router-metadata) and map each reported provider attempt into the Run History. | **Adopt as an optional provider feature** |
| [OpenRouter Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router) | Hosted prompt-based model selection across a curated model pool | Model membership can change. Selection and execution are handled by an external service. | Use only in a pinned comparison arm. Do not treat it as a fixed-model result. | **Observe and benchmark** |
| [Ollama](https://docs.ollama.com/api/introduction) | Local and hosted model runtime with native and OpenAI-compatible APIs | No built-in cross-model quality router is documented. The caller chooses the model. | Register local Ollama models as explicit routes. Let Loop Engine choose the tier and model. | **Adopt as a provider** |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | Self-hosted strong-versus-weak model selector with matrix factorization, weighted ranking, BERT, and model-based routers | Local inference cost depends on the selected router. Its bundled routers were trained on an older GPT-4 and Mixtral pair. Thresholds need calibration on representative requests. | Wrap only its selection output. Let `ModelGateway` invoke the chosen route and keep provider accounting. | **Evaluate as a policy plugin** |
| [Semantic Router](https://github.com/aurelio-labs/semantic-router) | Intent and route classifier based on embeddings, with local encoders and abstention | One embedding operation per decision plus index lookup. It routes by semantic class, not measured model quality. | Good candidate for choosing a specialization or task family. It should not decide escalation by itself. | **Evaluate for specialization routing** |
| [TensorZero](https://www.tensorzero.com/docs/gateway/) | Self-hosted Rust gateway with provider access, schemas, observability, evaluation, experiments, retries, and fallback | Separate service and data plane. TensorZero reports sub-millisecond gateway overhead, but Loop Engine has not measured that claim. | Treat it as one external gateway endpoint. Avoid duplicate retries. Its provider and variant events need Run History mapping if it controls fallback. | **Wrap for deployments that already use it** |
| [Not Diamond](https://docs.notdiamond.ai/docs/quickstart-routing) | Hosted model selector that returns a recommended provider and model before the caller invokes it | Adds a routing API call, network latency, another data processor, and separate billing terms. Custom routers require evaluation data. | A clean `ModelSelectionPolicy` adapter is possible because selection and invocation are already separate. | **Observe until net savings are measured** |
| [Arch Router and Plano](https://github.com/katanemo/plano/tree/main/demos/llm_routing/claude_code_router) | Self-hosted 1.5B preference-aligned routing model and proxy configuration | Local model inference is heavier than rules or embeddings. It can route to local Ollama and hosted providers. | Possible policy plugin for task-to-model preferences. It overlaps with gateway and agent controls when deployed as a proxy. | **Observe and compare with cheaper policies** |
| [Martian Router SDK](https://withmartian.github.io/martian-sdk-python/api/routers_client.html) | Hosted router creation, training, and execution API | Requires router training and a hosted service. The public SDK documentation is limited compared with the options above. | Keep out of the runtime until current availability, costs, privacy, and telemetry are verified. | **Observe only** |

No single project is a direct successor to RouteLLM. Current products split
into full gateways, local classifiers, and hosted model selectors. Loop Engine
should keep those categories interchangeable instead of choosing one package
as the architecture.

Unify was not selected for an adapter proposal. The current official
[Unify documentation](https://docs.unify.ai/basics/overview) describes an
agent platform, not a narrow provider-neutral router contract that improves on
the options above. Recheck it only if a stable routing API and public telemetry
contract are published.

## Failover and escalation rules

Use typed failure classes. A single generic `failed` flag is not enough.

| Failure | First response | May escalate model tier? |
|---|---|---|
| Missing credential | Stop that route and report configuration error | No |
| Authentication failure | Stop that provider and report configuration error | No |
| Rate limit or provider outage | Try an allowed provider route in the same tier | No |
| Timeout | Retry within the route budget, then try the same tier | Not by itself |
| Invalid output shape | Run bounded deterministic repair or retry the same tier | After the retry budget |
| Verifier rejects substance | Record the failed answer and select the next approved tier | Yes |
| Budget exhausted | Stop with an incomplete result | No |

An external gateway can perform failover, but then Loop Engine needs its
per-attempt provider, model, status, tokens, latency, and cost data. If the
gateway cannot return those facts, configure one attempt in the external
gateway and keep failover in `ModelGateway`.

## Telemetry contract

Every selection and physical call should expose these fields:

- Selection policy ID and version.
- Requested and selected thinking-power tier.
- Specialization, if any.
- Candidate routes and the exclusion reason for rejected routes.
- Selection latency, tokens, and cost. Use unknown when a value is absent.
- Provider, model, endpoint route, attempt number, and failure class.
- Input tokens, output tokens, elapsed time, and provider-reported cost.
- Validator result, verifier result, and escalation reason.
- Final task result and the evaluator that accepted or rejected it.

LiteLLM supports callbacks and gateway logging through its
[observability interfaces](https://docs.litellm.ai/docs/observability/callbacks).
TensorZero exports OpenTelemetry and stores structured inference data through
its [gateway](https://www.tensorzero.com/docs/gateway/). OpenRouter can return
attempt details through opt-in router metadata. These formats differ, so Loop
Engine needs one typed import boundary rather than provider-specific fields in
the Run History.

## Evaluation plan

Start with an offline routing benchmark before routing live paid calls.
[RouterBench](https://github.com/withmartian/routerbench) provides an
extensible evaluation framework and precomputed model outcomes. RouteLLM also
ships evaluation support for MMLU, GSM8K, and MT-Bench. These are useful router
tests, but they do not establish performance on Loop Engine's task mix.

The first Loop Engine comparison should use accepted historical runs where at
least two models answered the same frozen task under the same evaluator. Test
static tier rules, a random control, Semantic Router, and one RouteLLM policy.
Report task acceptance, model cost, router overhead, latency, abstention rate,
and escalation rate. Do not promote a router based only on its own training
set.

## Implementation decision

Keep `ModelGateway` and its provider adapters. Add a typed
`ModelSelectionPolicy` extension point, a deterministic default policy, and a
versioned YAML mapping from thinking-power tiers to route names. Store secret
references in YAML and secret values in environment variables.

Do not add LiteLLM, RouteLLM, Semantic Router, TensorZero, Not Diamond, Arch,
or Martian as required dependencies. Each can be tested through an optional
adapter or an OpenAI-compatible custom endpoint. Promote an adapter only after
it beats the deterministic policy on a frozen Loop Engine population after
including routing overhead.
