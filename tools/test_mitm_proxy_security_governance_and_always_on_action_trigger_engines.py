"""Unit tests for the Authorized Man-in-the-Middle (MITM) Proxy Best-Practice
Security Governance & 12 Always-On Harness-Independent Action Trigger Engine Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

TOOLS_DIR = Path(__file__).resolve().parent
REPOSITORY = TOOLS_DIR.parent
for p in (TOOLS_DIR, REPOSITORY / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from mitm_proxy_security_governance_and_always_on_action_trigger_engines import (  # noqa: E402
    ALL_8_MITM_SECURITY_BEST_PRACTICES,
    ALL_12_ALWAYS_ON_PROXY_TRIGGERS,
    ALL_24_UNCOOPERATIVE_HARNESS_SCENARIOS,
    ENGINE_BALTOR_ALWAYS_ON_MITM_PROXY_GATEWAY,
    ENGINE_DETERMINISTIC_WIRE_INTERCEPTOR,
    ENGINE_ENVELOPE_VAULT_AND_SSRF_GUARD,
    ENGINE_EXTERNAL_CLIENT_HARNESS_ALONE_BASELINE,
    ENGINE_MID_FLIGHT_TOOL_SYNTHESIS,
    ENGINE_PROVENANCE_LEDGER_AND_SSE_GUARD,
    PROXY_DISPOSITION_DIRECT_REPLY,
    PROXY_DISPOSITION_ENRICHED_PASS_THROUGH,
    PROXY_DISPOSITION_MID_FLIGHT_TOOL,
    SLOT_ALWAYS_ON_ACTION_TRIGGERS,
    SLOT_AUTHORIZED_MITM_GOVERNANCE,
    AlwaysOnProxyActionTriggerSlot,
    AuthorizedMitmSecurityGovernanceSlot,
    run_known_wrong_controls,
    run_mitm_proxy_and_always_on_triggers_benchmark,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
)


class MitmProxySecurityGovernanceAndTriggersTests(unittest.TestCase):
    def test_12_always_on_triggers_and_8_mitm_best_practices_catalog(self) -> None:
        self.assertEqual(len(ALL_12_ALWAYS_ON_PROXY_TRIGGERS), 12)
        self.assertEqual(len(ALL_8_MITM_SECURITY_BEST_PRACTICES), 8)
        self.assertEqual(len(ALL_24_UNCOOPERATIVE_HARNESS_SCENARIOS), 24)

        expected_triggers = {
            "T01_preturn_contract_card_and_formula_injection",
            "T02_untouched_ast_symbol_digest_preservation",
            "T03_3d_horizon_lighting_and_9x16_safe_zone_guard",
            "T04_timeseries_and_tabular_zero_lookahead_gate",
            "T05_dual_local_and_public_pii_secret_anonymizer",
            "T06_logjam_and_redundant_convergence_breakout",
            "T07_skills_state_and_memory_checkpoint_sync",
            "T08_humanizer_anti_slop_and_ftc_disclosure_surgeon",
            "T09_token_and_dollar_budget_downshift_guard",
            "T10_idempotent_effect_and_webhook_reconciler",
            "T11_sprouting_keyword_and_search_miss_telemetry",
            "T12_signed_cognitive_receipt_and_header_attestation",
        }
        self.assertEqual({t.trigger_id for t in ALL_12_ALWAYS_ON_PROXY_TRIGGERS}, expected_triggers)

    def test_slot_family_1_always_on_12_action_triggers_across_dispositions(self) -> None:
        slot = AlwaysOnProxyActionTriggerSlot()

        # Mid-flight tool and verifier execution (Cursor dropping AGENTS.md)
        r_mid = slot.intercept_and_trigger_all_12_actions(
            "SCEN_01",
            preferred_engine=ENGINE_DETERMINISTIC_WIRE_INTERCEPTOR,
            request_id="test_trig_scen_01",
        )
        self.assertTrue(r_mid.accepted)
        self.assertEqual(r_mid.slot_id, SLOT_ALWAYS_ON_ACTION_TRIGGERS)
        self.assertEqual(r_mid.selected_engine, ENGINE_DETERMINISTIC_WIRE_INTERCEPTOR)
        for layer in COVERAGE_LAYERS:
            self.assertEqual(r_mid.layer_verdicts[layer], "full")
        self.assertTrue(r_mid.output["all_12_triggers_fired"])
        self.assertEqual(r_mid.output["triggered_actions_count"], 12)
        self.assertEqual(r_mid.output["proxy_disposition"], PROXY_DISPOSITION_MID_FLIGHT_TOOL)
        self.assertEqual(r_mid.output["unredacted_pii_leak_count"], 0)

        # Direct synthetic/cached reply from L0 (Cursor routine JSON check)
        r_direct = slot.intercept_and_trigger_all_12_actions(
            "SCEN_03",
            preferred_engine=ENGINE_MID_FLIGHT_TOOL_SYNTHESIS,
            request_id="test_trig_scen_03",
        )
        self.assertTrue(r_direct.accepted)
        self.assertEqual(r_direct.selected_engine, ENGINE_MID_FLIGHT_TOOL_SYNTHESIS)
        self.assertEqual(r_direct.output["proxy_disposition"], PROXY_DISPOSITION_DIRECT_REPLY)
        self.assertEqual(r_direct.output["tokens_saved"], 14200)

        # Enriched upstream pass-through with logjam breakout & PII scrubbing (LangChain RAG)
        r_pass = slot.intercept_and_trigger_all_12_actions(
            "SCEN_16",
            preferred_engine=ENGINE_DETERMINISTIC_WIRE_INTERCEPTOR,
            request_id="test_trig_scen_16",
        )
        self.assertTrue(r_pass.accepted)
        self.assertEqual(r_pass.output["proxy_disposition"], PROXY_DISPOSITION_ENRICHED_PASS_THROUGH)
        self.assertTrue(r_pass.output["stalled_logjam_broken"])
        self.assertTrue(r_pass.output["pii_or_secrets_scrubbed"])
        headers = r_pass.output["response_headers"]
        self.assertIn("X-Baltor-Proxy-Mode", headers)
        self.assertIn("X-Baltor-Triggered-Actions", headers)
        self.assertIn("X-Baltor-Tokens-Saved", headers)
        self.assertIn("X-Baltor-Receipt-HMAC", headers)

    def test_slot_family_2_authorized_mitm_security_governance_and_paired_lan_lease(self) -> None:
        gov = AuthorizedMitmSecurityGovernanceSlot()
        res = gov.govern_proxy_wire_exchange(
            "SCEN_05",
            preferred_engine=ENGINE_ENVELOPE_VAULT_AND_SSRF_GUARD,
            request_id="test_gov_01",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_AUTHORIZED_MITM_GOVERNANCE)
        self.assertEqual(res.output["best_practices_count"], 8)
        self.assertEqual(res.output["envelope_encryption_cipher"], "AES-256-GCM")
        self.assertTrue(res.output["memory_frame_zeroed_after_call"])
        self.assertFalse(res.output["proxy_intervention_ledger_entry"]["silent_mutation"])
        self.assertTrue(res.output["sse_streaming_integrity"]["sse_chunk_framing_valid"])
        self.assertLessEqual(res.output["scoped_ephemeral_lease"]["lease_ttl_seconds"], 900)

        # LAN host (192.168.50.10) is permitted ONLY when authenticated_paired_websocket_lease=True
        res_lan_leased = gov.govern_proxy_wire_exchange(
            "SCEN_06",
            preferred_engine=ENGINE_PROVENANCE_LEDGER_AND_SSE_GUARD,
            request_id="test_gov_lan_leased",
            extra_payload={
                "upstream_host": "192.168.50.10",
                "authenticated_paired_websocket_lease": True,
            },
        )
        self.assertTrue(res_lan_leased.accepted)
        self.assertEqual(res_lan_leased.selected_engine, ENGINE_PROVENANCE_LEDGER_AND_SSE_GUARD)
        self.assertEqual(res_lan_leased.output["upstream_host_verified"], "192.168.50.10")

        # LAN host without paired WebSocket lease is refused at Layer 6 preflight
        res_lan_unleased = gov.govern_proxy_wire_exchange(
            "SCEN_06",
            request_id="test_gov_lan_unleased",
            extra_payload={
                "upstream_host": "192.168.50.10",
                "authenticated_paired_websocket_lease": False,
            },
        )
        self.assertFalse(res_lan_unleased.accepted)
        self.assertEqual(res_lan_unleased.layer_verdicts[LAYER_PREFLIGHT], LAYER_REFUSED)
        assert res_lan_unleased.refusal is not None
        self.assertEqual(
            res_lan_unleased.refusal.code,
            "ssrf_upstream_target_or_unleased_lan_refused",
        )

    def test_benchmark_24_uncooperative_client_harness_scenarios(self) -> None:
        bench = run_mitm_proxy_and_always_on_triggers_benchmark()
        self.assertEqual(bench["total_uncooperative_scenarios"], 24)
        self.assertEqual(bench["total_always_on_triggers"], 12)
        self.assertEqual(bench["total_mitm_security_best_practices"], 8)
        self.assertTrue(bench["all_24_scenarios_executed_through_7_layer_envelope"])

        ext = bench["relying_on_external_client_harness_alone_without_proxy"]
        self.assertEqual(ext["engine_id"], ENGINE_EXTERNAL_CLIENT_HARNESS_ALONE_BASELINE)
        self.assertEqual(ext["trigger_compliance_pct"], "12.5%")
        self.assertEqual(ext["task_pass_rate_pct"], "45.8%")
        self.assertAlmostEqual(ext["mean_wasted_retry_loops_per_task"], 4.2)

        baltor = bench["baltor_always_on_mitm_cloud_proxy_gateway"]
        self.assertEqual(baltor["engine_id"], ENGINE_BALTOR_ALWAYS_ON_MITM_PROXY_GATEWAY)
        self.assertEqual(baltor["trigger_compliance_pct"], "100.0%")
        self.assertEqual(baltor["total_action_triggers_verified"], 288)
        self.assertEqual(baltor["task_pass_rate_pct"], "97.9%")
        self.assertEqual(baltor["infinite_retry_loops_observed"], 0)
        self.assertEqual(baltor["unredacted_pii_or_secret_leaks"], 0)
        self.assertLess(baltor["mean_proxy_wire_overhead_ms"], 4.5)

    def test_four_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        expected_codes = {
            "recursive_proxy_hop_limit_exceeded_refused",
            "ssrf_upstream_target_or_unleased_lan_refused",
            "unaudited_silent_proxy_mutation_refused",
            "cross_tenant_byok_vault_key_reuse_refused",
        }
        observed_codes = set()
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"])
            self.assertEqual(ctrl["refused_by_layer"], LAYER_PREFLIGHT)
            self.assertTrue(ctrl["refused_before_engine"])
            observed_codes.add(ctrl["actual_refusal_code"])
        self.assertEqual(observed_codes, expected_codes)


if __name__ == "__main__":
    unittest.main()
