"""Tests and known-wrong controls for the 8-slot 7-layer component envelope hardening engines."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import slot_handshake_hardening_engines as hardening  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    ENGINE_SOURCE,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_TRACKING,
    MAXIMUM_ENVELOPE_DEPTH,
    PURE_EFFECT,
    RETRY_AFTER_WAIT,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import VERDICT_REPAIRED  # noqa: E402


class SlotHandshakeHardeningTest(unittest.TestCase):
    """Verify all 8 operational slots across all 7 envelope layers and known-wrong controls."""

    def test_eight_slot_benchmark_matrix_is_complete_and_verified(self) -> None:
        report = hardening.run_eight_slot_benchmark()
        self.assertEqual(report["record_type"], hardening.BENCHMARK_REPORT_RECORD_TYPE)
        self.assertEqual(report["slot_count"], 8)
        self.assertEqual(report["layer_count"], 7)
        self.assertTrue(report["all_verified"])
        for slot_id in hardening.HARDENED_SLOTS:
            self.assertIn(slot_id, report["verification_matrix"])
            row = report["verification_matrix"][slot_id]
            for layer in COVERAGE_LAYERS:
                self.assertEqual(row[layer], "full", f"{slot_id}.{layer} was not full")

    def test_layer1_frustration_avoidance_normalization_and_idempotency(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        req = hardening.make_valid_request(
            hardening.SLOT_TELEMETRY_SINK,
            idempotency_key="  idem_norm_01  ",
            payload_overrides={"stream_name": "  telemetry   main   stream  "},
        )
        req = replace(req, headers={"  X-Trace-Source  ": "  edge   worker  "})
        first = hub.execute(req)
        self.assertTrue(first.accepted)
        self.assertFalse(first.deduplicated)
        self.assertEqual(first.normalized_headers.get("x-trace-source"), "edge worker")
        self.assertEqual(first.output["stream_name"], "telemetry main stream")

        # Rapid retry with identical idempotency key and payload returns deduplicated cached result.
        second = hub.execute(req)
        self.assertTrue(second.accepted)
        self.assertTrue(second.deduplicated)
        self.assertEqual(second.receipt.outcome, hardening.OUTCOME_DEDUPLICATED)
        self.assertEqual(second.receipt.correlation_id, first.receipt.correlation_id)

        # Known-wrong control: reusing idempotency key with mutated payload is refused with recovery hints.
        conflicting = hardening.make_valid_request(
            hardening.SLOT_TELEMETRY_SINK,
            idempotency_key="idem_norm_01",
            payload_overrides={"stream_name": "different_stream_name"},
        )
        conflict_out = hub.execute(conflicting)
        self.assertFalse(conflict_out.accepted)
        self.assertIsNotNone(conflict_out.refusal)
        self.assertEqual(conflict_out.refusal.code, "idempotency_payload_conflict")
        self.assertTrue(conflict_out.refusal.next_action.endswith("."))

        # Known-wrong control: blank idempotency key is refused.
        blank_idem = replace(req, idempotency_key="   ")
        blank_out = hub.execute(blank_idem)
        self.assertFalse(blank_out.accepted)
        self.assertEqual(blank_out.refusal.code, "missing_idempotency_key")

    def test_layer2_carrier_version_schema_and_payload_digest_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        for slot_id in hardening.HARDENED_SLOTS:
            valid = hardening.make_valid_request(slot_id, idempotency_key=f"carrier_ok_{slot_id}")

            bad_version = replace(
                valid,
                idempotency_key=f"carrier_ver_{slot_id}",
                contract_version="wrong_contract/v99",
            )
            out_ver = hub.execute(bad_version)
            self.assertFalse(out_ver.accepted)
            self.assertEqual(out_ver.trace.refused_by, LAYER_CARRIER)
            self.assertEqual(out_ver.refusal.code, "carrier_contract_version_mismatch")

            bad_schema = replace(
                valid,
                idempotency_key=f"carrier_schema_{slot_id}",
                schema_digest="f" * 64,
            )
            out_schema = hub.execute(bad_schema)
            self.assertFalse(out_schema.accepted)
            self.assertEqual(out_schema.trace.refused_by, LAYER_CARRIER)
            self.assertEqual(out_schema.refusal.code, "carrier_schema_digest_mismatch")

            bad_sha = replace(
                valid,
                idempotency_key=f"carrier_sha_{slot_id}",
                payload_sha256="a" * 64,
            )
            out_sha = hub.execute(bad_sha)
            self.assertFalse(out_sha.accepted)
            self.assertEqual(out_sha.trace.refused_by, LAYER_CARRIER)
            self.assertEqual(out_sha.refusal.code, "carrier_payload_digest_mismatch")

            extra_payload = {**valid.payload, "undeclared_extra_field": "forbidden"}
            bad_fields = replace(
                valid,
                idempotency_key=f"carrier_fields_{slot_id}",
                payload=extra_payload,
                payload_sha256=hardening.compute_payload_sha256(hardening.normalize_value(extra_payload)),
            )
            out_fields = hub.execute(bad_fields)
            self.assertFalse(out_fields.accepted)
            self.assertEqual(out_fields.trace.refused_by, LAYER_CARRIER)
            self.assertEqual(out_fields.refusal.code, "carrier_schema_fields_invalid")

    def test_layer3_handshake_paired_agent_transport_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        valid = hardening.make_valid_request(
            hardening.SLOT_PAIRED_AGENT_TRANSPORT,
            idempotency_key="paired_valid_1",
            payload_overrides={"sequence": 10},
        )
        ok_out = hub.execute(valid)
        self.assertTrue(ok_out.accepted)

        # Sequence replay (sequence <= 10) must be refused at handshake.
        replay_req = hardening.make_valid_request(
            hardening.SLOT_PAIRED_AGENT_TRANSPORT,
            idempotency_key="paired_replay_1",
            payload_overrides={"sequence": 10},
        )
        replay_out = hub.execute(replay_req)
        self.assertFalse(replay_out.accepted)
        self.assertEqual(replay_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(replay_out.refusal.code, "paired_transport_sequence_replay")

        # Expired lease must be refused at handshake.
        expired_req = hardening.make_valid_request(
            hardening.SLOT_PAIRED_AGENT_TRANSPORT,
            idempotency_key="paired_expired_1",
            payload_overrides={"sequence": 11, "lease_expires_at": 1792170000.0},
            now_epoch=1792173600.0,
        )
        expired_out = hub.execute(expired_req)
        self.assertFalse(expired_out.accepted)
        self.assertEqual(expired_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(expired_out.refusal.code, "paired_transport_lease_expired")

        # Forged HMAC signature must be refused at handshake.
        forged_req = hardening.make_valid_request(
            hardening.SLOT_PAIRED_AGENT_TRANSPORT,
            idempotency_key="paired_forged_1",
            payload_overrides={"sequence": 12},
            lease_signing_material="wrong_signing_key_material",
        )
        forged_out = hub.execute(forged_req)
        self.assertFalse(forged_out.accepted)
        self.assertEqual(forged_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(forged_out.refusal.code, "paired_transport_signature_invalid")

    def test_layer3_handshake_billing_settlement_stripe_webhook_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        valid = hardening.make_valid_request(
            hardening.SLOT_BILLING_SETTLEMENT,
            idempotency_key="billing_valid_1",
        )
        self.assertTrue(hub.execute(valid).accepted)

        # Stale timestamp outside the 300s window is refused.
        stale_req = hardening.make_valid_request(
            hardening.SLOT_BILLING_SETTLEMENT,
            idempotency_key="billing_stale_1",
            payload_overrides={"event_id": "evt_stale_02"},
            now_epoch=1792173600.0,
        )
        stale_sig = hardening.sign_stripe_webhook(
            "whsec_key_v1_1122334455667788",
            1792173600 - 900,
            stale_req.payload,
        )
        stale_req = replace(stale_req, headers={"stripe-signature": stale_sig})
        stale_out = hub.execute(stale_req)
        self.assertFalse(stale_out.accepted)
        self.assertEqual(stale_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(stale_out.refusal.code, "webhook_timestamp_outside_window")

        # Forged webhook signature is refused.
        forged_req = hardening.make_valid_request(
            hardening.SLOT_BILLING_SETTLEMENT,
            idempotency_key="billing_forged_1",
            payload_overrides={"event_id": "evt_forged_03"},
            webhook_signing_material="whsec_wrong_key_00000000",
        )
        forged_out = hub.execute(forged_req)
        self.assertFalse(forged_out.accepted)
        self.assertEqual(forged_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(forged_out.refusal.code, "webhook_signature_invalid")

    def test_layer3_handshake_mcp_bridge_version_and_tool_visibility_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        for mcp_ver in hardening.SUPPORTED_MCP_VERSIONS:
            req = hardening.make_valid_request(
                hardening.SLOT_MCP_BRIDGE,
                idempotency_key=f"mcp_ok_{mcp_ver}",
                payload_overrides={"mcp_protocol_version": mcp_ver, "tool_name": "baltor_search"},
            )
            self.assertTrue(hub.execute(req).accepted)

        # Unsupported MCP protocol version is refused.
        bad_ver_req = hardening.make_valid_request(
            hardening.SLOT_MCP_BRIDGE,
            idempotency_key="mcp_bad_ver",
            payload_overrides={"mcp_protocol_version": "2020-01-01"},
        )
        bad_ver_out = hub.execute(bad_ver_req)
        self.assertFalse(bad_ver_out.accepted)
        self.assertEqual(bad_ver_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(bad_ver_out.refusal.code, "mcp_protocol_version_unsupported")

        # Customer attempting to invoke staff-only tool is refused.
        customer_staff_tool = hardening.make_valid_request(
            hardening.SLOT_MCP_BRIDGE,
            idempotency_key="mcp_cust_staff_tool",
            principal_role=hardening.PRINCIPAL_CUSTOMER,
            payload_overrides={"tool_name": "staff_audit_export"},
        )
        cust_out = hub.execute(customer_staff_tool)
        self.assertFalse(cust_out.accepted)
        self.assertEqual(cust_out.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(cust_out.refusal.code, "mcp_tool_visibility_refused")

        # Staff principal invoking staff-only tool succeeds.
        staff_req = hardening.make_valid_request(
            hardening.SLOT_MCP_BRIDGE,
            idempotency_key="mcp_staff_ok",
            principal_role=hardening.PRINCIPAL_STAFF,
            payload_overrides={"tool_name": "staff_audit_export"},
        )
        self.assertTrue(hub.execute(staff_req).accepted)

    def test_layer4_account_isolation_status_and_quota_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        base = hardening.make_valid_request(
            hardening.SLOT_RUN_HISTORY_EXPORT,
            idempotency_key="acct_base",
            tenant_id="tenant_alpha",
        )
        # Cross-tenant mismatch
        cross = hardening.make_valid_request(
            hardening.SLOT_RUN_HISTORY_EXPORT,
            idempotency_key="acct_cross",
            tenant_id="tenant_alpha",
            payload_overrides={"tenant_id": "tenant_other"},
        )
        cross_out = hub.execute(cross)
        self.assertFalse(cross_out.accepted)
        self.assertEqual(cross_out.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(cross_out.refusal.code, "cross_tenant_isolation_violation")

        # Suspended account
        suspended_acct = replace(base.account, account_status="suspended")
        suspended_req = replace(base, idempotency_key="acct_suspended", account=suspended_acct)
        suspended_out = hub.execute(suspended_req)
        self.assertFalse(suspended_out.accepted)
        self.assertEqual(suspended_out.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(suspended_out.refusal.code, "account_not_active")

        # Exhausted quota
        over_quota_acct = replace(base.account, quota_limit=10, consumed_units=10, requested_units=1)
        over_quota_req = replace(base, idempotency_key="acct_quota", account=over_quota_acct)
        quota_out = hub.execute(over_quota_req)
        self.assertFalse(quota_out.accepted)
        self.assertEqual(quota_out.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(quota_out.refusal.code, "account_quota_exhausted")
        self.assertEqual(quota_out.refusal.retry, RETRY_AFTER_WAIT)
        self.assertEqual(quota_out.refusal.retry_after_seconds, 60)

    def test_layer5_tracking_receipt_metrics_and_journal_chain_integrity(self) -> None:
        hub = hardening.SevenLayerSlotHub()
        req = hardening.make_valid_request(
            hardening.SLOT_FAILURE_JOURNAL,
            idempotency_key="track_journal_1",
        )
        out = hub.execute(req)
        self.assertTrue(out.accepted)
        self.assertTrue(out.receipt.correlation_id.startswith("ref_"))
        self.assertEqual(len(out.receipt.journal_entry_digests), 2)
        metrics = hub.metrics_for(hardening.SLOT_FAILURE_JOURNAL).to_dict()
        self.assertEqual(metrics["completed_count"], 1)
        self.assertGreater(metrics["mean_latency_ms"], 0.0)

        # Known-wrong control: dropping the first entry from the journal chain causes tracking layer refusal.
        entries = list(hub.journal_for(hardening.SLOT_FAILURE_JOURNAL))
        hub._journal_entries[hardening.SLOT_FAILURE_JOURNAL] = [entries[1]]
        # Bypass idempotency cache with same request digest by clearing cache entry only
        hub._idempotency_cache.clear()
        tampered_out = hub.execute(req)
        self.assertFalse(tampered_out.accepted)
        self.assertEqual(tampered_out.trace.refused_by, LAYER_TRACKING)
        self.assertEqual(tampered_out.refusal.code, "journal_chain_broken")

    def test_layer6_preflight_secret_scrubbing_memory_ceiling_and_idempotency_ledger(self) -> None:
        hub = hardening.SevenLayerSlotHub()

        # Secret and PII in export slots: blocked when allow_preflight_repair=False, scrubbed when True.
        for export_slot, field_name, leaky_value in (
            (
                hardening.SLOT_RUN_HISTORY_EXPORT,
                "spans",
                [{"name": "step", " leaked": "Bearer secret_token_value_123456 and alice@example.com"}],
            ),
            (
                hardening.SLOT_TELEMETRY_SINK,
                "events",
                [{"msg": "key sk-proj1234567890abcdef and ssn 123-45-6789"}],
            ),
            (
                hardening.SLOT_FAILURE_JOURNAL,
                "summary",
                "Failed with token ghp_1234567890abcdefghijklmnop for bob@example.org",
            ),
        ):
            blocked_req = hardening.make_valid_request(
                export_slot,
                idempotency_key=f"pf_block_{export_slot}",
                payload_overrides={field_name: leaky_value},
                allow_preflight_repair=False,
            )
            blocked_out = hub.execute(blocked_req)
            self.assertFalse(blocked_out.accepted)
            self.assertEqual(blocked_out.trace.refused_by, LAYER_PREFLIGHT)
            self.assertEqual(blocked_out.refusal.code, "preflight_secret_or_pii_blocked")

            repaired_req = hardening.make_valid_request(
                export_slot,
                idempotency_key=f"pf_repair_{export_slot}",
                payload_overrides={field_name: leaky_value},
                allow_preflight_repair=True,
            )
            repaired_out = hub.execute(repaired_req)
            self.assertTrue(repaired_out.accepted)
            self.assertIsNotNone(repaired_out.preflight_report)
            self.assertEqual(repaired_out.preflight_report.verdict, VERDICT_REPAIRED)

        # Runtime memory byte ceiling check
        oversized_req = hardening.make_valid_request(
            hardening.SLOT_RUNTIME_MEMORY,
            idempotency_key="pf_mem_oversized",
            payload_overrides={"note_body": "x" * 5000},
        )
        oversized_out = hub.execute(oversized_req)
        self.assertFalse(oversized_out.accepted)
        self.assertEqual(oversized_out.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(oversized_out.refusal.code, "preflight_memory_byte_ceiling_exceeded")

        # Billing settlement and usage export idempotency ledger checks
        bill_1 = hardening.make_valid_request(
            hardening.SLOT_BILLING_SETTLEMENT,
            idempotency_key="pf_bill_1",
            payload_overrides={"event_id": "evt_unique_ledger_99"},
        )
        self.assertTrue(hub.execute(bill_1).accepted)
        bill_replay = hardening.make_valid_request(
            hardening.SLOT_BILLING_SETTLEMENT,
            idempotency_key="pf_bill_2_different_idem_key",
            payload_overrides={"event_id": "evt_unique_ledger_99"},
        )
        bill_replay_out = hub.execute(bill_replay)
        self.assertFalse(bill_replay_out.accepted)
        self.assertEqual(bill_replay_out.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(bill_replay_out.refusal.code, "preflight_duplicate_settlement_blocked")

        usage_1 = hardening.make_valid_request(
            hardening.SLOT_USAGE_EXPORT,
            idempotency_key="pf_usage_1",
            payload_overrides={"meter_event_id": "meter_unique_ledger_99"},
        )
        self.assertTrue(hub.execute(usage_1).accepted)
        usage_replay = hardening.make_valid_request(
            hardening.SLOT_USAGE_EXPORT,
            idempotency_key="pf_usage_2_different_idem_key",
            payload_overrides={"meter_event_id": "meter_unique_ledger_99"},
        )
        usage_replay_out = hub.execute(usage_replay)
        self.assertFalse(usage_replay_out.accepted)
        self.assertEqual(usage_replay_out.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(usage_replay_out.refusal.code, "preflight_duplicate_meter_event_blocked")

    def test_layer7_nested_envelopes_attenuation_cycle_and_depth_controls(self) -> None:
        hub = hardening.SevenLayerSlotHub()

        # Authority escalation control: parent grants only pure, child requests network -> refused.
        child_network_req = hardening.make_valid_request(
            hardening.SLOT_PAIRED_AGENT_TRANSPORT,
            idempotency_key="nested_child_net",
        )
        parent_pure_only = replace(
            hardening.make_valid_request(
                hardening.SLOT_MCP_BRIDGE,
                idempotency_key="nested_parent_pure",
                nested_invocations=(child_network_req,),
            ),
            granted_effects=(PURE_EFFECT,),
        )
        esc_out = hub.execute(parent_pure_only)
        self.assertFalse(esc_out.accepted)
        self.assertEqual(esc_out.refusal.code, "nested_authority_escalation_refused")

        # Nested cross-tenant hop control: parent is tenant_alpha, child is tenant_beta -> refused.
        child_other_tenant = hardening.make_valid_request(
            hardening.SLOT_TELEMETRY_SINK,
            idempotency_key="nested_child_other_tenant",
            tenant_id="tenant_beta",
        )
        parent_tenant_alpha = hardening.make_valid_request(
            hardening.SLOT_MCP_BRIDGE,
            idempotency_key="nested_parent_alpha",
            tenant_id="tenant_alpha",
            nested_invocations=(child_other_tenant,),
        )
        tenant_hop_out = hub.execute(parent_tenant_alpha)
        self.assertFalse(tenant_hop_out.accepted)
        self.assertEqual(tenant_hop_out.refusal.code, "nested_cross_tenant_violation")

        # Envelope cycle control: parent slot invoking the same slot_id in nested_invocations -> refused.
        self_child = hardening.make_valid_request(
            hardening.SLOT_TELEMETRY_SINK,
            idempotency_key="nested_cycle_child",
        )
        cycle_parent = hardening.make_valid_request(
            hardening.SLOT_TELEMETRY_SINK,
            idempotency_key="nested_cycle_parent",
            nested_invocations=(self_child,),
        )
        cycle_out = hub.execute(cycle_parent)
        self.assertFalse(cycle_out.accepted)
        self.assertEqual(cycle_out.refusal.code, "envelope_cycle")

        # Depth bound control: entering past MAXIMUM_ENVELOPE_DEPTH is refused.
        deep_frame = root_frame("root_slot_0")
        for idx in range(1, MAXIMUM_ENVELOPE_DEPTH + 1):
            from loop_engine.core.engines.envelope import enter_nested
            deep_frame = enter_nested(deep_frame, f"nested_slot_{idx}")
        over_depth_req = replace(
            hardening.make_valid_request(
                hardening.SLOT_TELEMETRY_SINK,
                idempotency_key="nested_over_depth",
            ),
            parent_frame=deep_frame,
        )
        depth_out = hub.execute(over_depth_req)
        self.assertFalse(depth_out.accepted)
        self.assertEqual(depth_out.refusal.code, "envelope_depth_exceeded")

    def test_multi_engine_fallback_and_exhaustion_across_all_eight_slots(self) -> None:
        default_engines = hardening.build_default_slot_engines()

        def _always_fail(_payload: dict, _headers: dict) -> dict:
            raise hardening.TransientEngineUnavailableError(
                "upstream_transient_unavailable",
                "Simulated upstream outage.",
            )

        for slot_id in hardening.HARDENED_SLOTS:
            primary_spec, fallback_spec = default_engines[slot_id]

            # 1. Primary fails -> fallback succeeds
            fb_hub = hardening.SevenLayerSlotHub(
                engines_by_slot={
                    **default_engines,
                    slot_id: (
                        replace(primary_spec, execute_fn=_always_fail),
                        fallback_spec,
                    ),
                }
            )
            req = hardening.make_valid_request(slot_id, idempotency_key=f"fb_chain_{slot_id}")
            fb_out = fb_hub.execute(req)
            self.assertTrue(fb_out.accepted)
            self.assertTrue(fb_out.receipt.fallback_occurred)
            self.assertEqual(fb_out.receipt.selected_engine_id, fallback_spec.engine_id)
            self.assertEqual(fb_out.receipt.attempt_count, 2)
            self.assertEqual(fb_out.receipt.outcome, hardening.OUTCOME_FALLBACK_COMPLETED)

            # 2. Both primary and fallback fail -> refused by ENGINE_SOURCE
            exhausted_hub = hardening.SevenLayerSlotHub(
                engines_by_slot={
                    **default_engines,
                    slot_id: (
                        replace(primary_spec, execute_fn=_always_fail),
                        replace(fallback_spec, execute_fn=_always_fail),
                    ),
                }
            )
            ex_req = hardening.make_valid_request(slot_id, idempotency_key=f"fb_exhaust_{slot_id}")
            ex_out = exhausted_hub.execute(ex_req)
            self.assertFalse(ex_out.accepted)
            self.assertEqual(ex_out.trace.refused_by, ENGINE_SOURCE)
            self.assertEqual(ex_out.receipt.attempt_count, 2)
            self.assertEqual(ex_out.receipt.outcome, hardening.OUTCOME_REFUSED)


if __name__ == "__main__":
    unittest.main()
