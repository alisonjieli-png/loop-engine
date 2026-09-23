# Provider refusal recovery with an unknown model identity

September 23, 2026. Isolated repair against the integrated accounting/identity
successors. The parent CI export `e7e70a75` failed the owning embodiment check
`test_a_page_in_the_providers_place_keeps_its_typed_code_and_its_call_count`.
This work reproduces that failure without any model or network request.

## Cause

The custom endpoint and gateway correctly reported `invalid_response_body` when a
fixture returned an HTML sign-in page. They also correctly left the answering model
unknown. `HarnessModelCall` then rejected that empty model field, causing the native
harness adapter to raise. The semantic wrapper classified the missing adapter result
as uncertain call accounting and `provider_attempt_contract_violated`. The final
trial therefore ended as `NO_PROGRESS`, even though the physical call was known and
the typed provider-outage code still existed in its evidence.

The correct test remains unchanged in intent: this is a classified provider outage,
with every observed physical request counted. Missing model identity and missing
usage do not mean that the number of requests is unknown.

## Repair and authority binding

- A `HarnessModelCall` may retain `model=""` only for a failed observation with a
  nonempty error code and an exact canonical gateway Loop reference. Empty identity
  is still refused for success, unbound calls and untyped failures.
- ModelGateway supplies its already selected typed `ModelRoute` to the canonical
  model invocation boundary. Before the callback runs, that boundary records an
  explicit `model_request_binding/v1` inside the existing invocation event. Its
  closed fields are `record_type`, `provider`, `model` and `route`.
- The harness reference validator still requires exactly one fresh invocation
  boundary and completion/failure event, matching Loop ownership, semantic identity,
  Loop definition identity/version/digest, provider, observed model, outcome and
  usage. For unknown observed identity, it additionally requires the exact binding
  version/field set, nonempty string values, and matching provider and route.
- Authorization then compares that **requested** provider/model/route with the
  harness request's allowed identities, or its exact primary provider/model.
  A missing, malformed, stale or unapproved binding refuses. No model name is
  inferred from the objective, and no missing observed identity is filled in.
- Semantic failure envelopes preserve the last physical attempt's reported model,
  including unknown. The previous primary-route model fallback is removed.

This adds a passive versioned binding to the existing canonical event; it creates no
new event store or runtime. Existing adapter request/result field shapes are unchanged.
An unknown-model record without the new binding is refused rather than reinterpreted.
The binding records the requested route; it does not claim the provider actually
answered with that model.

## Verification

- The original failing check now reports `PROVIDER_UNAVAILABLE`, retains
  `invalid_response_body`, and matches the fixture transport's actual call count.
  Recovery can issue another separately counted fixture request; counts are not
  forced to one.
- The owning **106 embodiment tests pass**. The trial check now also verifies that
  semantic and physical reported model identities remain empty, requested model is
  recorded separately, and token usage remains unknown.
- **211 owning boundary checks pass**: external harness 86, semantic harness 22,
  gateway 22, custom endpoint 70 and canonical encapsulation 11.
- **11 combined identity/recovery unit tests pass**, including four new focused
  cases. An unapproved requested model is refused despite a valid failed canonical
  call. Invalid/missing binding versions, changed provider/route, wrong owner and
  successful unknown identity are refused.
- Four in-memory guard mutations are detected, including reintroducing the semantic
  fallback and replacing the actual requested binding with the authorized primary.
  Changed source/tests introduce no Ruff findings; the new fault runner is clean.

[Evidence](../../artifacts/provider-refusal-recovery-2026-09-23/README.md) keeps the
failed trial state, known-wrong checks and intermediate fixture repairs. The normal
review virtual environment lacked DuckDB, so these checks used the same existing
MCP2 environment as the failed full CI run; no dependency was installed.

These are fixture and contract checks. They establish recovery/accounting behavior,
not live provider availability, task completion, or newly qualified intelligence.
