# Operational slot handshake and envelope hardening, October 16, 2026

Kind: verification record of operational, transport, and export engine slot
hardening, dated October 16, 2026. It keeps its bytes; later work belongs in a
new record. Roadmap steps: S-6.30, S-6.43, and S-6.61. Reference modules:
[envelope.py](../../src/loop_engine/core/engines/envelope.py),
[envelope_preflight.py](../../src/loop_engine/core/engines/envelope_preflight.py),
[envelope_tracking.py](../../src/loop_engine/core/engines/envelope_tracking.py),
[component_envelope_coverage_baseline.yaml](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml),
[slot_handshake_hardening_engines.py](../../tools/slot_handshake_hardening_engines.py),
and
[test_slot_handshake_hardening_engines.py](../../tools/test_slot_handshake_hardening_engines.py).

## Outcome

Eight operational, transport, and export engine slots now run through complete,
swappable seven-layer component envelope adapters with multi-engine fallback
chains and deterministic known-wrong controls. Every slot passes all seven
envelope layers (`frustration_avoidance`, `carrier`, `handshake`, `account`,
`tracking`, `preflight`, and `nested_envelopes`), recovers on a declared
transient primary engine outage without repeating any effect, and refuses
malformed, replayed, cross-tenant, unauthorized, or secret-leaking requests
before any engine effect runs.

```text
Seven-layer component envelope (outermost first)
├── 1. frustration_avoidance  whitespace and header normalization, idempotency deduplication, recovery hints
├── 2. carrier                SlotCarrierEnvelope (contract_version, schema_digest, payload_sha256)
├── 3. handshake              protocol version match, lease HMAC, webhook window, MCP tool visibility
├── 4. account                tenant binding, active account check, quota check, cross-tenant isolation
├── 5. tracking               EngineSelectionReceipt, latency and outcome counters, ref_... correlation ID
├── 6. preflight              secret and personal-data scrubbing, memory byte ceiling, idempotency ledger
└── 7. nested_envelopes       parent-to-nested EnvelopeFrame inheritance and effect authority attenuation
```

## Where this fits

In [component_envelope_coverage_baseline.yaml](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml),
several operational, transport, and export slots recorded `none` coverage
across multiple envelope layers (`run_history_export`, `usage_export`,
`failure_journal`, and `runtime_memory`), while four companion operational
surfaces (`paired_agent_transport`, `telemetry_sink`, `billing_settlement`, and
`mcp_bridge`) needed concrete seven-layer adapter contracts and fallback chains
verified in isolation before catalog-wide wiring.

 Implementing the adapters and verification harness in
[slot_handshake_hardening_engines.py](../../tools/slot_handshake_hardening_engines.py)
and
[test_slot_handshake_hardening_engines.py](../../tools/test_slot_handshake_hardening_engines.py)
proves each layer's runtime contract against the canonical types in
[envelope.py](../../src/loop_engine/core/engines/envelope.py) without mutating
shared catalog files on concurrent branches.

## Current behavior across the seven envelope layers

Each request enters `SevenLayerSlotHub.execute` as a typed `SlotEnvelopeRequest`
and passes the seven layers in order:

1. **Layer 1 (`frustration_avoidance`)**: Trims and collapses interior
   whitespace across string fields, normalizes request header names to
   lowercase, short-circuits rapid retries that carry the same `idempotency_key`
   and `payload_sha256`, refuses conflicting payloads that reuse an
   `idempotency_key` (`idempotency_payload_conflict`), and wraps every refusal
   in an `EnvelopeRefusal` (`envelope_refusal/v1`) with a plain-English
   explanation, next action, and retry rule.
2. **Layer 2 (`carrier`)**: Wraps the normalized payload in a
   `SlotCarrierEnvelope` (`slot_carrier_envelope/v1`) and verifies
   `contract_version`, `schema_digest`, `payload_sha256`, required fields, and
   closed field sets before handshake negotiation.
3. **Layer 3 (`handshake`)**: Evaluates `negotiate_handshake` over
   `EnvelopeHandshakeRequest` and each engine's `EnvelopeHandshakeDeclaration`
   (`envelope_handshake_verdict/v1`). In addition, `paired_agent_transport`
   verifies the lease expiration, monotonic sequence number, and HMAC-SHA256
   frame signature; `billing_settlement` verifies the Stripe `t=...,v1=...`
   HMAC signature and five-minute timestamp tolerance window; and `mcp_bridge`
   enforces exact Model Context Protocol versions (`2025-06-18` or
   `2024-11-05`) and filters staff-only tools from customer principals.
4. **Layer 4 (`account`)**: Binds `AccountScopeContext`, verifies that the
   account is active, enforces tenant quota limits, and blocks cross-tenant
   payloads (`cross_tenant_isolation_violation`) or nested tenant switches
   (`nested_cross_tenant_violation`).
5. **Layer 5 (`tracking`)**: Verifies the hash-chained `EnvelopeJournalEntry`
   (`envelope_journal_entry/v1`) history via `journal_chain`, records
   `journal_intent` before dispatch and `journal_outcome` after dispatch,
   assigns a deterministic `ref_...` correlation identifier, updates
   `SlotTrackingMetrics`, and emits an `EngineSelectionReceipt`
   (`engine_selection_receipt/v1`).
6. **Layer 6 (`preflight`)**: Executes `run_preflight` (`envelope_preflight_report/v1`).
   For `run_history_export`, `telemetry_sink`, and `failure_journal`, preflight
   scans for unredacted secrets (`sk-...`, `whsec_...`, `rk_live_...`,
   `ghp_...`, `Bearer ...`, private keys) and personal data (email addresses
   and Social Security number patterns), either refusing the export
   (`preflight_secret_or_pii_blocked`) or applying a bounded pure
   `EnvelopeSelfRepair` to scrub the fields in memory. For `runtime_memory`,
   preflight enforces the 4,096-byte note ceiling
   (`preflight_memory_byte_ceiling_exceeded`). For `billing_settlement` and
   `usage_export`, preflight checks the durable idempotency ledger before any
   mutation (`preflight_duplicate_settlement_blocked` and
   `preflight_duplicate_meter_event_blocked`).
7. **Layer 7 (`nested_envelopes`)**: Enters nested slot calls via `enter_nested`
   on the parent `EnvelopeFrame` (`envelope_frame/v1`), sharing the parent's
   `RecoveryAllowance` and deadline while attenuating granted effects so a
   nested slot can never escalate authority (`nested_authority_escalation_refused`),
   loop in a cycle (`envelope_cycle`), or exceed `MAXIMUM_ENVELOPE_DEPTH`
   (`envelope_depth_exceeded`).

## Eight-slot by seven-layer verification matrix

| Slot | Primary engine | Fallback engine | `frustration_avoidance` | `carrier` | `handshake` | `account` | `tracking` | `preflight` | `nested_envelopes` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `run_history_export` | `trace_span_exporter` | `trajectory_exporter` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `usage_export` | `provider_meter_events` | `no_export` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `failure_journal` | `in_service_journal` | `ring_buffer_failure_journal` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `runtime_memory` | `run_note_board` | `bounded_scratchpad_board` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `paired_agent_transport` | `signed_https_polling_transport` | `websocket_lease_transport` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `telemetry_sink` | `jsonl_structured_sink` | `otlp_batch_sink` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `billing_settlement` | `stripe_webhook_reconciler` | `prepaid_credit_ledger` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |
| `mcp_bridge` | `stdio_jsonrpc_bridge` | `http_sse_mcp_bridge` | `full` | `full` | `full` | `full` | `full` | `full` | `full` |

## Primary versus fallback engine benchmark

Running `run_eight_slot_benchmark()` in
[slot_handshake_hardening_engines.py](../../tools/slot_handshake_hardening_engines.py)
measures primary dispatch, two-attempt fallback recovery when the primary
engine raises `TransientEngineUnavailableError`, and idempotent retry
deduplication across all eight slots:

| Slot | Primary engine | Primary latency (ms) | Fallback engine | Fallback latency (ms) | Dedup retry latency (ms) | Fallback attempts | Nested slot verified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `run_history_export` | `trace_span_exporter` | 0.94 | `trajectory_exporter` | 0.74 | 0.10 | 2 | `telemetry_sink` (depth 1) |
| `usage_export` | `provider_meter_events` | 0.51 | `no_export` | 0.67 | 0.08 | 2 | `telemetry_sink` (depth 1) |
| `failure_journal` | `in_service_journal` | 0.44 | `ring_buffer_failure_journal` | 0.53 | 0.05 | 2 | `telemetry_sink` (depth 1) |
| `runtime_memory` | `run_note_board` | 0.38 | `bounded_scratchpad_board` | 0.69 | 0.06 | 2 | `telemetry_sink` (depth 1) |
| `paired_agent_transport` | `signed_https_polling_transport` | 0.59 | `websocket_lease_transport` | 0.80 | 0.07 | 2 | `telemetry_sink` (depth 1) |
| `telemetry_sink` | `jsonl_structured_sink` | 0.42 | `otlp_batch_sink` | 0.60 | 0.07 | 2 | `failure_journal` (depth 1) |
| `billing_settlement` | `stripe_webhook_reconciler` | 0.86 | `prepaid_credit_ledger` | 1.42 | 0.09 | 2 | `telemetry_sink` (depth 1) |
| `mcp_bridge` | `stdio_jsonrpc_bridge` | 0.40 | `http_sse_mcp_bridge` | 0.53 | 0.06 | 2 | `telemetry_sink` (depth 1) |

## Known-wrong controls

The suite in
[test_slot_handshake_hardening_engines.py](../../tools/test_slot_handshake_hardening_engines.py)
verifies that each layer refuses its known-wrong inputs before any downstream
layer or engine executes:

| Layer | Known-wrong control | Refusal code | Refused by |
| --- | --- | --- | --- |
| `frustration_avoidance` | Reused `idempotency_key` with altered payload bytes | `idempotency_payload_conflict` | `carrier` |
| `frustration_avoidance` | Empty or whitespace-only `idempotency_key` | `missing_idempotency_key` | `carrier` |
| `carrier` | Unsupported `contract_version` on any of the 8 slots | `carrier_contract_version_mismatch` | `carrier` |
| `carrier` | Tampered `schema_digest` or `payload_sha256` | `carrier_schema_digest_mismatch`, `carrier_payload_digest_mismatch` | `carrier` |
| `carrier` | Undeclared extra payload field or missing required field | `carrier_schema_fields_invalid` | `carrier` |
| `handshake` | Replayed or non-monotonic sequence on `paired_agent_transport` | `paired_transport_sequence_replay` | `handshake` |
| `handshake` | Expired lease or forged HMAC on `paired_agent_transport` | `paired_transport_lease_expired`, `paired_transport_signature_invalid` | `handshake` |
| `handshake` | Stale Stripe webhook timestamp (`> 300s`) or forged HMAC on `billing_settlement` | `webhook_timestamp_outside_window`, `webhook_signature_invalid` | `handshake` |
| `handshake` | Unsupported MCP version (`2020-01-01`) or customer calling `staff_audit_export` on `mcp_bridge` | `mcp_protocol_version_unsupported`, `mcp_tool_visibility_refused` | `handshake` |
| `account` | Payload `tenant_id` differing from authenticated `AccountScopeContext.tenant_id` | `cross_tenant_isolation_violation` | `account` |
| `account` | Suspended account status or exhausted quota allowance | `account_not_active`, `account_quota_exhausted` | `account` |
| `tracking` | Dropped or reordered `EnvelopeJournalEntry` in the slot's journal chain | `journal_chain_broken` | `tracking` |
| `preflight` | Unredacted bearer token, API key, email, or SSN in export payload (`allow_preflight_repair=False`) | `preflight_secret_or_pii_blocked` | `preflight` |
| `preflight` | Runtime memory note exceeding 4,096 UTF-8 bytes | `preflight_memory_byte_ceiling_exceeded` | `preflight` |
| `preflight` | Duplicate `event_id` or `meter_event_id` in settlement or usage ledger | `preflight_duplicate_settlement_blocked`, `preflight_duplicate_meter_event_blocked` | `preflight` |
| `nested_envelopes` | Nested slot requesting `network` when parent only holds `pure` | `nested_authority_escalation_refused` | `handshake` |
| `nested_envelopes` | Nested slot switching tenant, repeating a slot on `frame.path`, or exceeding depth 4 | `nested_cross_tenant_violation`, `envelope_cycle`, `envelope_depth_exceeded` | `account`, `carrier` |

## Main limits and deeper references

- **Scope.** The adapters in
  [slot_handshake_hardening_engines.py](../../tools/slot_handshake_hardening_engines.py)
  run in memory against the canonical envelope records in
  [envelope.py](../../src/loop_engine/core/engines/envelope.py) so that
  verification is deterministic and offline. Raising the declarative rows in
  [component_envelope_coverage.yaml](../../src/loop_engine/data/component_envelope_coverage.yaml)
  and
  [component_envelope_coverage_baseline.yaml](../../src/loop_engine/data/component_envelope_coverage_baseline.yaml)
  is reserved for the coordinating merge after the layer worktree lands.
- **References.** Read
  [ADR-COMPONENT-ENVELOPE-LAYERS.md](../architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
  and
  [FUNCTIONAL-COMPONENT-STANDARD.md](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
  for the complete layer rules.
