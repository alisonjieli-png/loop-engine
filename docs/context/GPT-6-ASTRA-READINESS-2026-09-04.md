# GPT-6 Astra readiness, 2026-09-04

Status: offline adapter and quarantined route-policy prototype. The executable
route gate is hard-disabled. This page does not claim that an OpenAI route is
configured or that a provider call succeeded.

## Official facts checked

The following facts were checked against official OpenAI documentation on
2026-09-04:

| Item | Documented value |
|---|---|
| API model ID | `gpt-6-astra` |
| Context window | 1,050,000 tokens |
| Maximum output | 128,000 tokens |
| Reasoning effort | `low`, `medium`, `high`, `xhigh`, and `max` |
| Tool calling | Use the Responses API |
| Unsupported sampling parameters | Remove `temperature`, `top_p`, and `top_logprobs` |
| Fine-tuning | Not supported for this model |
| Standard input price | $10 per million tokens |
| Standard cached-input price | $1 per million tokens |
| Standard cache-write price | $12.50 per million tokens |
| Standard output price | $50 per million tokens |

Sources:

- [GPT-6 Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Using GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model)

OpenAI describes access as a rollout. Loop Engine has not made an authorized
probe of this model. Account access, rate limits, latency, billing, and route
health therefore remain unknown for this repository.

## Keep the core model-neutral

```text
Loop
├── owns the typed semantic responsibility
├── receives explicit model and effect authority
├── calls a provider through an internal adapter
├── verifies the candidate result
└── records exact provider, model, usage, and outcome evidence
```

GPT-6 Astra is one possible model realization. It is not a new Loop role,
profile, run mode, capability group, or runtime type. Astra-specific request
parameters belong in a provider capability record and adapter. They do not
belong in the universal Loop contract.

The large documented context window is not a reason to load the prompt
archive, old transcripts, or the full development history. Start with
`AGENTS.md`, one current session packet when available, and one selected
continuation brief. Load component documents and evidence only when the active
work needs them.

## Current implementation and gaps

Loop Engine now has an internal, explicit-only OpenAI Responses adapter for
the exact `gpt-6-astra` model. Offline injected-transport checks prove that it:

- sends text requests to `/v1/responses`;
- requests the source-backed 128,000-token output maximum;
- accepts only `low`, `medium`, `high`, `xhigh`, and `max` reasoning effort;
- requests Standard processing explicitly with `service_tier="default"`;
- omits `temperature`, `top_p`, log-probability, and tool fields;
- preserves provider-reported usage, response status, incomplete details,
  response identity, and service tier through the model gateway;
- rejects tool-call output instead of executing it; and
- rejects a missing or different provider-reported model identity;
- hides authorization headers from object representations;
- requires the exact word `READY` in its live-verification response; and
- hashes private prompt text in safe summaries and excludes raw provider error
  messages from normalized evidence.

The current result is 21 of 21 offline adapter checks passed with zero network
calls and zero environment credential reads. A second offline suite passes 38
of 38 quarantined policy checks. It adds:

- one typed demand record for purpose, thinking power, call count, token
  limits, service tier, locality, modality, and optional capabilities;
- one candidate paid-route envelope bound to the exact provider, model, route,
  credential reference, locality, service tier, call budget, token budget, and
  maximum cost;
- one versioned mapping from Loop thinking power to supported Astra reasoning
  effort;
- one source-backed pricing record with the documented long-context and
  service-tier multipliers;
- one provider-availability and locality snapshot candidate;
- a digest over the complete demand, authority candidate, availability,
  reasoning, capability, and evaluation-time inputs; and
- an unconditional refusal that prevents construction of an executable
  `ModelRoute` or `ProviderSpec` plan.

The candidate envelope is not execution authority. It has no trusted issuer,
one-use consumption, revocation, or use-time budget enforcement. Historical
availability and capability labels are also caller-supplied records. The hard
quarantine remains in place until those facts resolve through existing Loop
Engine authority and effect services.

The conservative cost calculation assumes that every allowed input token is
billed at the higher fresh-input or cache-write rate and that every allowed
output token is used. It does not assume a cache discount. Under that method,
one Standard-tier call with a 1,000-token input allowance and the full
128,000-token output allowance has a maximum exposure of $6.412500. One call
at a derived 922,000-token input allowance and 128,000-token maximum output has
a maximum exposure of $32.650000 after the documented long-context multipliers.
The input allowance is the documented context window minus the maximum output;
OpenAI does not publish it as a separate input maximum. These are conservative
planning bounds, not execution authority or expected invoices.

The adapter remains absent from the default route table, discovery, failover
order, tiers, and runtime settings. The route-policy prototype cannot construct
an executable plan. An `OPENAI_API_KEY` value alone therefore cannot activate
the route or authorize spending. The current test process had no
`OPENAI_API_KEY`, so no live probe was attempted.

This does not prove account access, live request compatibility, realized
price, latency, quality, structured output, tool execution, async tools,
mid-turn steering, or cancellation. The thinking-power mapping is tested
policy data. It is not evidence that one effort value is optimal for a task.

Before describing Loop Engine as GPT-6 Astra ready, prove all of the following:

1. Bind paid use to an issued, expiring, revocable, one-use effect decision and
   enforce call, token, and cost ceilings at the actual invocation boundary.
2. Bind trusted-clock availability, the exact adapter and credential resolver,
   one requested purpose, Standard service-tier transport, and the global
   endpoint at use time.
3. Implement separate qualified paths for regional endpoints, Flex, Batch, or
   priority processing before offering those choices.
4. Connect Loop thinking power to the exact per-call reasoning effort without
   allowing gateway evidence and wire behavior to disagree.
5. Implement and verify structured output and the Responses API tool path.
6. Record the exact provider response, token usage when reported, latency,
   cost state, and failure classification.
7. Run one authorized probe, then a bounded product-path test. A configured
   key or a successful offline fixture is not provider evidence.

Fine-tuning plans for smaller or specialized models remain separate. The
official model page states that GPT-6 Astra itself does not support
fine-tuning.

## Separate configured-provider canary

A model-neutral provider canary used the already configured Ollama Cloud route
after explicit one-call authorization. It is not an Astra call and does not
weaken the Astra quarantine.

The request used `cloud.default` with `deepseek-v4-flash:0731`, a physical-call
ceiling of 1, and a total-token ceiling of 70,000. The provider declared an
exact 65,536-token output maximum through its response path. The accepted call
used 66 input tokens and 130 output tokens, reported 196 total tokens, and took
1.167 seconds. Provider usage was complete.

The private evidence record is
`~/.loop-engine/evidence/live-model-ollama_cloud-20260904T154049Z.json`. Its
SHA-256 is
`7212657bf01fc7c5345d41afcb9a065943a2ad11d8f1b2e1e75962ea2cd6a26f`.
It stores prompt and output digests, not their raw text or credentials.

This proves one live provider adapter, route, maximum-output discovery path,
exact grader, and usage record. It does not prove a live assisted-versus-fresh
pair, task-solving quality, Astra access, or cost because the provider route
has no source-backed monetary price record.

## Current universal-solver continuation

The public offline solve path now carries hydrated prior-stage material to an
injected provider adapter, records an explicit model disposition, and links one
selected action through exact selection, execution, and verification
occurrence references. Every active advisory or fresh run records a pre-run
control manifest. The current fixture is explicitly `mechanism_only`; six
control facts remain unresolved, and its semantic verifier uses the same
Practitioner model path.

The current evidence and exact limits are in the
[predictive-state, procedural-memory, and stage-assistance report](../verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md).
This does not prove a valid assisted-versus-fresh comparison or change the
Astra route quarantine. The next high-information step is one canonical,
stage-local control application and SQLite rebuild before a bounded live pair.

## Guidance for an Astra development session

Use the same repository authority as every other coding-agent session. Read
the compact start page and exactly one broad continuation brief:

- [Start a coding-agent session](CODEX-START-HERE.md)
- [Continue the universal solver](../prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md)

If a generated `session_handoff/v1` packet is supplied, recompute its HEAD and
worktree checks before trusting it. A process ID, file timestamp, or old
handoff does not establish ownership of dirty files.
