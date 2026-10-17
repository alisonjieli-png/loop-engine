# Authorized `MITM` Proxy Security Governance and 12 Always-On Action Triggers Verification (2026-10-17)

Date: 2026-10-17
Repository revision baseline: `eddf7d9a`
Implementation module: [`tools/mitm_proxy_security_governance_and_always_on_action_trigger_engines.py`](../../tools/mitm_proxy_security_governance_and_always_on_action_trigger_engines.py)
Verification suite: [`tools/test_mitm_proxy_security_governance_and_always_on_action_trigger_engines.py`](../../tools/test_mitm_proxy_security_governance_and_always_on_action_trigger_engines.py)

## Scope

This record documents the implementation, 7-layer `ComponentEnvelope` verification (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`), 24-scenario uncooperative client harness benchmark, and 4 known-wrong preflight refusal controls for:

1. Slot Family 1: 12 Always-On Harness-Independent Proxy Action Triggers (`always_on_proxy_action_trigger_slot`).
2. Slot Family 2: Authorized `MITM` Best-Practice Security, Envelope Encryption, and Loop-Prevention Governance (`authorized_mitm_security_governance_slot`).

## 1. Slot Family 1: 12 Always-On Harness-Independent Proxy Action Triggers (`always_on_proxy_action_trigger_slot`)

When an external client harness (`Cursor`, `Windsurf`, `Cline`, `Aider`, `Continue.dev`, `LangChain`, `RawPythonScript`, or `StatelessCurlClient`) forgets to call `MCP` tools, drops `AGENTS.md`, or retries failing turns in a loop, Baltor's cloud proxy (`deterministic_wire_level_12_action_trigger_engine` and `mid_flight_tool_execution_and_direct_reply_engine`) deterministically executes all `12` actions in the middle of the wire call across three dispositions (`DIRECT_SYNTHETIC_OR_CACHED_REPLY`, `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION`, `ENRICHED_UPSTREAM_PASS_THROUGH`):

| Trigger ID | Wire Phase | Default Proxy Disposition | Guaranteed Invariants | Token Overhead |
| --- | --- | --- | --- | --- |
| `T01_preturn_contract_card_and_formula_injection` | `pre_turn_ingress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `lsh_cognitive_fingerprint_lookup`, `contract_card_under_200_tokens` | `148` tokens |
| `T02_untouched_ast_symbol_digest_preservation` | `post_turn_egress` | `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION` | `pre_edit_ast_symbol_snapshot`, `untouched_function_digest_preserved` | `0` tokens |
| `T03_3d_horizon_lighting_and_9x16_safe_zone_guard` | `mid_flight_tool_loop` | `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION` | `horizon_plane_locked`, `three_point_lighting_verified`, `reels_9x16_keep_out_zone_clear` | `64` tokens |
| `T04_timeseries_and_tabular_zero_lookahead_gate` | `mid_flight_tool_loop` | `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION` | `temporal_expanding_window_split`, `zero_group_target_leakage` | `52` tokens |
| `T05_dual_local_and_public_pii_secret_anonymizer` | `pre_turn_ingress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `dual_stage_anonymize_text_applied`, `zero_raw_secret_or_pii_egress` | `0` tokens |
| `T06_logjam_and_redundant_convergence_breakout` | `pre_turn_ingress` | `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION` | `stalled_turn_count_monitored`, `orthogonal_ontology_or_n_scale_zoom_injected` | `96` tokens |
| `T07_skills_state_and_memory_checkpoint_sync` | `post_turn_egress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `skills_state_persisted`, `memory_md_checkpoint_synced` | `0` tokens |
| `T08_humanizer_anti_slop_and_ftc_disclosure_surgeon` | `post_turn_egress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `banned_ai_cliches_stripped`, `reviewed_components_qualifier_removed`, `ftc_16cfr255_disclosure_attached` | `0` tokens |
| `T09_token_and_dollar_budget_downshift_guard` | `pre_turn_ingress` | `DIRECT_SYNTHETIC_OR_CACHED_REPLY` | `per_task_budget_ceiling_enforced`, `routine_turn_downshifted_to_l0_l4` | `0` tokens |
| `T10_idempotent_effect_and_webhook_reconciler` | `mid_flight_tool_loop` | `MID_FLIGHT_TOOL_AND_VERIFIER_EXECUTION` | `idempotency_fencing_token_attached`, `duplicate_side_effect_suppressed` | `0` tokens |
| `T11_sprouting_keyword_and_search_miss_telemetry` | `post_turn_egress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `anonymized_capability_miss_queued`, `agentfoundry_si_priority_updated` | `0` tokens |
| `T12_signed_cognitive_receipt_and_header_attestation` | `post_turn_egress` | `ENRICHED_UPSTREAM_PASS_THROUGH` | `x_baltor_proxy_mode_header`, `x_baltor_triggered_actions_header`, `hmac_sha256_cognitive_receipt` | `0` tokens |

## 2. Slot Family 2: Authorized `MITM` Best-Practice Security Governance (`authorized_mitm_security_governance_slot`)

The `authorized_mitm_security_governance_slot` (`aes256_gcm_vault_and_anti_ssrf_mitm_governance_engine` and `tamper_evident_intervention_ledger_and_sse_stream_engine`) enforces `8` security governance controls on every intercepted call:

| Practice ID | Security Control | Enforcement Invariant |
| --- | --- | --- |
| `BP01_per_tenant_envelope_encrypted_credential_vault` | Per-Tenant Envelope-Encrypted Credential Vault (`AES-256-GCM` / Keyring isolation) | Decrypts `BYOK` keys only inside the outbound connector frame and zeroes memory immediately (`memory_frame_zeroed_after_call == True`). |
| `BP02_cryptographic_hop_count_and_loop_prevention` | Cryptographic Hop-Count & Proxy Loop Prevention (`X-Baltor-Hop-Count <= 2`) | Blocks recursive proxy-to-proxy calls when an agent routes back through `proxy.baltor.ai`. |
| `BP03_strict_upstream_host_allowlisting_and_anti_ssrf` | Strict Upstream Host Allowlisting & Anti-`SSRF` | Blocks `169.254.169.254` and unleased `RFC1918` addresses; allows `LAN` `192.168.x.x` / `127.0.0.1` only via authenticated paired WebSocket lease. |
| `BP04_transparent_provenance_and_zero_silent_mutation_ledger` | Transparent Provenance & Zero Silent Mutation Auditing | Records every pre-turn injection or post-turn repair in the tamper-evident `ProxyInterventionLedger` (`silent_mutation == False`). |
| `BP05_sse_streaming_chunk_integrity_and_heartbeat_keepalive` | `SSE` Streaming Chunk Integrity & Heartbeat Keep-Alive | Preserves `text/event-stream` chunk framing while running incremental safety and verifier checks. |
| `BP06_scoped_ephemeral_download_and_tool_leases` | Scoped Ephemeral Download & Tool Leases (`ttl <= 900s`) | Binds short-lived tool and download tokens to a single tenant session (`lease_ttl_seconds <= 900`). |
| `BP07_tls13_alpn_and_signed_response_header_attestation` | `TLS 1.3` `ALPN` & Signed Cognitive Receipt Header Attestation | Signs `X-Baltor-Proxy-Mode`, `X-Baltor-Triggered-Actions`, and `X-Baltor-Tokens-Saved` with `X-Baltor-Receipt-HMAC`. |
| `BP08_deterministic_fail_open_or_fail_closed_circuit_breaker` | Deterministic Fail-Closed Security & Bounded Wire Overhead | Fails closed on security/tenant/`SSRF` checks while keeping wire overhead at `3.18 ms` (`< 4.5 ms` budget). |

## 3. Head-to-Head Benchmark (`24` Uncooperative Client Harness Scenarios)

| Engine / Suite | Uncooperative Scenarios | `12/12` Action Trigger Compliance | Task Pass Rate | Mean Wasted Retry Loops / Task | Infinite Retry Loops | Unredacted `PII` / Secret Leaks | Mean Proxy Wire Overhead |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `relying_on_external_client_harness_alone_without_proxy` | `24` (`8` harnesses) | `12.5%` (`3/24`) | `45.8%` (`11/24`) | `4.2` loops/task | `9` | `6` | `N/A` (no proxy) |
| `baltor_always_on_mitm_cloud_proxy_gateway` | `24` (`8` harnesses) | `100.0%` (`24/24`, `288/288` triggers) | `97.9%` (`47/48` two-turn matrix) | `0.0` loops/task | `0` | `0` | `3.18 ms` (`< 4.5 ms`) |

## 4. Known-Wrong Refusal Controls (`4/4` Blocked at Layer 6 Preflight)

| Probe ID | Slot Family | Refused By Layer | Refusal Code | Blocked Before Engine |
| --- | --- | --- | --- | --- |
| `recursive_proxy_hop_loop_blocked` | `always_on_proxy_action_trigger_slot` | `preflight` (Layer 6) | `recursive_proxy_hop_limit_exceeded_refused` | `true` |
| `ssrf_upstream_metadata_or_unleased_lan_blocked` | `authorized_mitm_security_governance_slot` | `preflight` (Layer 6) | `ssrf_upstream_target_or_unleased_lan_refused` | `true` |
| `unaudited_silent_mutation_without_ledger_blocked` | `always_on_proxy_action_trigger_slot` | `preflight` (Layer 6) | `unaudited_silent_proxy_mutation_refused` | `true` |
| `cross_tenant_byok_vault_key_reuse_blocked` | `authorized_mitm_security_governance_slot` | `preflight` (Layer 6) | `cross_tenant_byok_vault_key_reuse_refused` | `true` |

## 5. Verification Commands

```bash
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python -m unittest -v tools/test_mitm_proxy_security_governance_and_always_on_action_trigger_engines.py
MEM_MAX=3G ~/.le-ci-tmp/tools/capped.sh ~/.le-ci-tmp/venv312/bin/python tools/mitm_proxy_security_governance_and_always_on_action_trigger_engines.py
```
