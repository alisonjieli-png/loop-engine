# Streamlined setup, user capability profiles, and payment emulation verification (2026-10-16)

This report records the design, implementation, head-to-head benchmarks, and
known-wrong control verification of the three-slot, twelve-engine onboarding,
user capability profiling, and payment lifecycle emulation suite in
[tools/streamlined_setup_and_user_profile_engines.py](../../tools/streamlined_setup_and_user_profile_engines.py)
and
[tools/test_streamlined_setup_and_user_profile_engines.py](../../tools/test_streamlined_setup_and_user_profile_engines.py).

## Outcome and scope

Every functional boundary across zero-question harness setup, privacy-safe
session and capability profiling (`user_capability_profile/v1`), and
end-to-end payment and entitlement emulation runs inside the seven-layer
component envelope defined in
[src/loop_engine/core/engines/envelope.py](../../src/loop_engine/core/engines/envelope.py),
[src/loop_engine/core/engines/envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
and
[src/loop_engine/core/engines/envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py).

All eight unit tests in
[tools/test_streamlined_setup_and_user_profile_engines.py](../../tools/test_streamlined_setup_and_user_profile_engines.py),
all nine harness onboarding checks, all eight canonical persona clusters, all
fifteen common user use cases, the seven-stage payment and Founding-slot
emulation, and all eight `removed_*` known-wrong controls pass with zero leaks
of customer email addresses, credentials, or raw prompt text.

## Where the suite fits in the Loop architecture

Every executable graph vertex in Loop Engine is a `Loop`. Onboarding
configurations, `user_capability_profile/v1` records, Matryoshka vectors, LSH
signatures, and Stripe subscription snapshots are passive records or engine
adapters invoked by a `Loop`, never separate executable graph vertices.

```text
Loop
├── Relationship: Starting, Spawned by, Queried by, Retrieved by, Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Category: organization and search taxonomy across library components
└── Settings: contract, loop condition, exit condition, budget, and permissions
    ├── Discrete cognitive or act step Loop node behavioral guarantees:
    │   ├── Narrowly scoped assignment with selected context and resources
    │   ├── Separately initialized harnesses and permitted harness changes
    │   ├── Expectation checks and iteration until declared completion conditions
    │   ├── Continued production of alternative outputs when configured
    │   ├── Protection against repeated external effects before retry
    │   └── Separation of output publication from Loop completion
    └── Engine slots used by Loop steps across onboarding, profiling, and billing:
        ├── Slot 1: streamlined_setup_orchestrator
        │   ├── Engine 1A: zero_question_workspace_auto_detector
        │   ├── Engine 1B: jev_llm_rule_inference_setup_engine
        │   ├── Engine 1C: progressive_single_click_oauth_setup_engine
        │   └── Engine 1D: minimal_guided_fallback_setup_engine
        ├── Slot 2: user_capability_profiler (user_capability_profile/v1)
        │   ├── Engine 2A: matryoshka_session_embedding_profiler
        │   ├── Engine 2B: lsh_persona_and_usecase_clusterer
        │   ├── Engine 2C: bayesian_outcome_affinity_updater
        │   └── Engine 2D: ephemeral_in_session_profile_fallback
        └── Slot 3: payment_and_entitlement_emulator
            ├── Engine 3A: free_dec2026_basic_grant_engine
            ├── Engine 3B: stripe_signed_webhook_entitlement_engine
            ├── Engine 3C: founding_slot_atomic_lease_engine
            └── Engine 3D: offline_idempotent_reconciliation_fallback_engine
```

A discrete cognitive or act step Loop node receives a narrowly scoped
assignment, selected context and resources, separately initialized harnesses,
and explicit rules for permitted harness changes. It runs expectation checks,
iterates until declared completion conditions are met, can continue producing
alternative outputs when configured, protects against repeated external
effects, and keeps publication of an output separate from completion of the
step.

## Slot Family 1: `streamlined_setup_orchestrator`

### Nine-harness question audit and transport key verification

An audit of user setup across all nine supported harnesses showed that seven
legacy manual onboarding questions (`mcp_transport_key`, `os_platform`,
`language_stack`, `token_ceiling_bytes`, `top_k_cards`,
`pre_turn_hook_threshold`, and `initial_feed_bundles`) can be inferred
deterministically from workspace markers (`pyproject.toml`, `package.json`,
`Cargo.toml`) and the harness configuration target. This reduces onboarding from
seven manual inputs to zero manual questions and a single copy-paste command.

| Harness ID | Display name | Config marker | Exact MCP transport key | Legacy manual questions | Streamlined questions | One-command install |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- |
| `claude_code` | Claude Code | `.claude/settings.json` | `http` | 7 | 0 | `npx @baltor/setup --harness claude-code` |
| `codex` | Codex | `.codex/config.toml` | `http_transport` | 7 | 0 | `npx @baltor/setup --harness codex` |
| `cursor` | Cursor | `.cursor/mcp.json` | `url` | 7 | 0 | `npx @baltor/setup --harness cursor` |
| `windsurf` | Windsurf | `.codeium/windsurf/mcp_config.json` | `serverUrl` | 7 | 0 | `npx @baltor/setup --harness windsurf` |
| `cline` | Cline | `.cline/mcp_settings.json` | `streamableHttp` | 7 | 0 | `npx @baltor/setup --harness cline` |
| `roo_code` | Roo Code | `.roo/mcp.json` | `streamable-http` | 7 | 0 | `npx @baltor/setup --harness roo-code` |
| `opencode` | OpenCode | `opencode.json` | `remote` | 7 | 0 | `npx @baltor/setup --harness opencode` |
| `pi` | Pi | `.pi/agent/settings.json` | `mcp_endpoint` | 7 | 0 | `npx @baltor/setup --harness pi` |
| `chatgpt_app` | ChatGPT App | `.openai/chatgpt_app.json` | `sse_or_streamable_http` | 7 | 0 | `npx @baltor/setup --harness chatgpt-app` |

### Swappable setup engines and cascade fallback

| Engine ID | Primary mechanism | Manual questions asked | Legacy questions saved | Token ceiling (bytes) | `top_k` | Fallback role |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `zero_question_workspace_auto_detector` | Inspects harness marker, OS, and `pyproject.toml`, `package.json`, and `Cargo.toml` files | 0 | 7 | 16384 | 6 | Primary zero-question detector when workspace read authority is granted |
| `jev_llm_rule_inference_setup_engine` | Deterministic System-1 rule inference over workspace markers and first prompt hint | 0 | 7 | 16384 | 6 | First fallback when workspace file inspection is off but a first prompt signal is present |
| `progressive_single_click_oauth_setup_engine` | OAuth 2.1 Dynamic Client Registration with mandatory `S256` PKCE verification | 0 | 7 | 16384 | 6 | Second fallback for GUI and hosted clients without local workspace markers |
| `minimal_guided_fallback_setup_engine` | Single-question conservative defaults when all inspection and GUI OAuth grants are off | 1 | 6 | 16384 | 4 | Terminal deterministic fallback guaranteeing completion in restricted sandboxes |

## Slot Family 2: `user_capability_profiler` (`user_capability_profile/v1`)

### Layer 3 `require_same_space` handshake and Layer 6 PII scrubber

Every `user_capability_profiler` engine enforces two mandatory envelope guards:

1. **Layer 3 (`handshake`) `require_same_space` check**: Verifies that
   `model_id` (`baltor-matryoshka-embed-v1`), `dimension` (`64` sliced from
   `256`), `l2_normalized` (`True`), and `quantization_mode`
   (`float32_plus_binary64`) match the canonical space before comparing or
   updating vectors. Any foreign or unnormalized vector space is refused at
   `LAYER_HANDSHAKE`.
2. **Layer 6 (`preflight`) PII and secret scrubber**: Scrubs API keys
   (`baltor_`, `sk-`, `ghp_`, `Bearer`), email addresses, and local home paths
   (`/home/...`, `/Users/...`) before computing embeddings, and sets
   `raw_prompt_retained=False` on every emitted `user_capability_profile/v1`
   record.

### Swappable profiling engines

| Engine ID | Representation and update rule | Vector dimension | Binary signature | Account persistence | Primary use |
| :--- | :--- | ---: | :--- | :--- | :--- |
| `matryoshka_session_embedding_profiler` | Incremental `256d -> 64d` Matryoshka L2-normalized float vector plus 64-bit sign bits | 64 | `0x...` (64-bit) | Yes | Fast cosine and Hamming similarity across session and long-term domain affinity |
| `lsh_persona_and_usecase_clusterer` | Multi-band token SimHash LSH clustering into 8 personas and 15 common use cases | 64 | `0x...` (64-bit) | Yes | Zero-model-call routing to canonical persona feed bundles |
| `bayesian_outcome_affinity_updater` | Beta-Bernoulli posterior update over `card_inspected`, `material_downloaded`, `kept_in_worktree`, and `tests_passed` | 64 | `0x...` (64-bit) | Yes |Re-weights capability families from verified downstream outcomes |
| `ephemeral_in_session_profile_fallback` | In-memory session-only profile with `persisted_to_account=False` | 64 | `0x...` (64-bit) | No | Zero-persistence fallback when account profile storage is disabled |

### Eight canonical personas and fifteen verified user use cases

The LSH clusterer deterministically maps all fifteen benchmark user questions
(`UC-01` through `UC-15`) across all eight canonical personas:

- `fullstack_builder`: `UC-01` (Next.js API and auth flow), `UC-02` (idempotent
  Stripe checkout webhook wiring).
- `ml_kaggle_practitioner`: `UC-03` (LightGBM cross-validation fold pipeline),
  `UC-04` (Matryoshka embedding quantization alignment).
- `systems_infra_engineer`: `UC-05` (SQLite WAL lock contention debugging),
  `UC-06` (Fly multi-region health check canary).
- `creative_motion_technologist`: `UC-07` (editable Three.js shader motion
  timeline), `UC-08` (parametric SVG typography kinetic rig).
- `public_good_researcher`: `UC-09` (Open Knowledge citation reproducibility),
  `UC-10` (open dataset benchmark provenance card).
- `security_auditor`: `UC-11` (preflight PII scrubber and secret redaction
  audit), `UC-12` (OAuth PKCE `S256` challenge verification).
- `autonomous_afk_operator`: `UC-13` (overnight Practitioner Loop with budget
  cap), `UC-14` (AgentAFK mobile approval gate notification).
- `executive_evaluator`: `UC-15` (Pareto latency and completion rate comparison
  across engines).

## Slot Family 3: `payment_and_entitlement_emulator`

The payment and entitlement emulator verifies the four billing engines
(`free_dec2026_basic_grant_engine`, `stripe_signed_webhook_entitlement_engine`,
`founding_slot_atomic_lease_engine`, and
`offline_idempotent_reconciliation_fallback_engine`) across all seven stages of
the commercial lifecycle:

1. **Stage 1 (Basic $9 plan free through December 2026)**: Grants Basic plan
   entitlement at `0` cents (`free_through_utc="2026-12-31T23:59:59Z"`) under
   Layer 6 promotional window preflight verification.
2. **Stage 2 (Pro $49 Stripe Checkout session and Privacy Notice wire check)**:
   Verifies against `POST_PARAMETERS` in
   [src/loop_engine/core/service_runtime/stripe_sessions.py](../../src/loop_engine/core/service_runtime/stripe_sessions.py)
   that `/v1/customers` carries only `metadata[loop_engine_tenant_id]` and
   `/v1/checkout/sessions` carries only the admitted price and return parameters,
   confirming `email_leaked_to_stripe=False`.
3. **Stage 3 (Signed webhook settlement)**: Verifies HMAC-SHA256 `t=...,v1=...`
   webhook signatures within the 300-second replay window and computes paid
   access through `paid_access_until` in
   [src/loop_engine/core/service_runtime/billing.py](../../src/loop_engine/core/service_runtime/billing.py)
   including the three-day `RENEWAL_GRACE_SECONDS` (`259200` seconds) allowance.
4. **Stage 4 (Founding 10-slot atomic lease and release)**: Verifies that the
   tenth concurrent Founding Member lease succeeds, the eleventh concurrent
   request is refused at the ten-slot cap (`FOUNDING_SLOT_CAP = 10`), and
   releasing an active lease immediately allows a waiting requester to acquire
   the freed slot.
5. **Stage 5 (Idempotent duplicate webhook replay refusal)**: Replaying an
   already-settled `evt_pro_settlement_001` webhook delivery is deterministically
   refused without duplicate state transitions.
6. **Stage 6 (Scheduled cancellation and renewal)**: Verifies through
   `StripeSubscriptionState` that a subscription with `cancel_at=period_end_sec`
   retains paid access until `period_end_sec` without adding post-period renewal
   grace, while a renewed subscription (`in_002`) extends access by 30 days plus
   `RENEWAL_GRACE_SECONDS`.

## Known-wrong controls

All eight `removed_*` known-wrong controls in `run_known_wrong_controls()` pass:

| Control ID | Fault injected | Expected refusal layer or check | Observed reason code |
| :--- | :--- | :--- | :--- |
| `removed_same_space_embedding_handshake_guard` | Foreign `128d` `int8` embedding space passed to `matryoshka_session_embedding_profiler` | `LAYER_HANDSHAKE` | `embedding_space_mismatch_model_id` |
| `removed_profile_pii_and_secret_preflight_guard` | Unredacted `baltor_` credential, email, and `/home/...` path with `allow_auto_scrub_pii=False` | `LAYER_PREFLIGHT` | `preflight_pii_or_secret_rejected` |
| `removed_stripe_wire_email_leak_guard` | Injecting `customer_email` into `/v1/checkout/sessions` wire parameters | `verify_stripe_wire_params_privacy_safe` | `privacy_violation_stripe_wire_param_customer_email` |
| `removed_webhook_hmac_signature_verification_guard` | Forged `v1=0000...` Stripe webhook HMAC header | `verify_webhook_hmac_signature` | `webhook_hmac_mismatch` |
| `removed_duplicate_webhook_idempotency_guard` | Replaying settled event ID `evt_settled_001` | Webhook idempotency set | `duplicate_webhook_event_ignored` |
| `removed_founding_ten_slot_cap_guard` | Requesting an 11th concurrent Founding Member slot when 10 are active | Founding slot atomic cap | `founding_slot_cap_reached` |
| `removed_workspace_inspection_authority_guard` | Calling `zero_question_workspace_auto_detector` with `workspace_read_granted=False` | `LAYER_PREFLIGHT` (cascades to fallback) | `workspace_inspection_disabled` |
| `removed_pkce_s256_challenge_guard` | Calling `progressive_single_click_oauth_setup_engine` with `pkce_code_challenge_method="plain"` | `LAYER_HANDSHAKE` | `oauth_pkce_s256_required` |

## Reproduction commands and limits

Run the unit test suite and CLI audit from the repository root:

```bash
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_streamlined_setup_and_user_profile_engines.py
PYTHONPATH=src:tools ~/.le-ci-tmp/venv312/bin/python tools/streamlined_setup_and_user_profile_engines.py
```

Current limits:

- All onboarding, embedding profile, and Stripe webhook emulations run
  deterministically in memory so continuous integration executes offline with
  zero network calls or live Stripe mutations.
- Live Stripe checkout and webhook settlement remain governed by the production
  service runtime in
  [src/loop_engine/core/service_runtime/stripe_sessions.py](../../src/loop_engine/core/service_runtime/stripe_sessions.py)
  and
  [src/loop_engine/core/service_runtime/billing.py](../../src/loop_engine/core/service_runtime/billing.py).
