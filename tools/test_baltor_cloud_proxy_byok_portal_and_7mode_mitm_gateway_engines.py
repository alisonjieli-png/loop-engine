"""Unit tests for the Baltor Cloud Proxy Web-Portal BYOK Credential Vault,
4-Protocol Endpoint Emulator, Signed Ephemeral Download Broker, and 7-Mode
Authorized Man-in-the-Middle (MITM) Intelligent Proxy Gateway Engine Suite.
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

from baltor_cloud_proxy_byok_portal_and_7mode_mitm_gateway_engines import (  # noqa: E402
    ALL_4_WIRE_PROTOCOL_EMULATORS,
    ALL_6_BYOK_UPSTREAM_PROVIDERS,
    ALL_7_MITM_PROXY_MODES,
    ALL_7_PROXY_MODE_SPECS,
    ALL_35_CLOUD_PROXY_BENCHMARK_TASKS,
    EMULATOR_ANTHROPIC_MESSAGES,
    EMULATOR_OLLAMA_CHAT,
    EMULATOR_OPENAI_CHAT_COMPLETIONS,
    EMULATOR_OPENAI_RESPONSES,
    ENGINE_BALTOR_7MODE_CLOUD_PROXY,
    ENGINE_DIRECT_UPSTREAM_WITHOUT_PROXY,
    MODE_M1_DIRECT_EMULATED_RESPONDER,
    MODE_M2_CONTEXT_CONCATENATING_PASSTHROUGH,
    MODE_M3_PROXY_SIDE_TOOL_LOOP,
    MODE_M4_POST_RESPONSE_VERIFIER_HEAL,
    MODE_M5_CHEAP_TO_FRONTIER_SPLIT,
    MODE_M6_SPECULATIVE_PARALLEL_RACE,
    MODE_M7_FAIL_OPEN_PASSTHROUGH,
    SLOT_CLOUD_PROXY_BYOK_EMULATOR,
    SLOT_SEVEN_MODE_MITM_PROXY,
    CloudProxyByokPortalAndEmulatorSlot,
    SevenModeMitmProxyOrchestratorSlot,
    run_baltor_cloud_proxy_7mode_benchmark,
    run_known_wrong_controls,
)
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_PREFLIGHT, LAYER_REFUSED  # noqa: E402


class BaltorCloudProxyByokAnd7ModeMitmTests(unittest.TestCase):
    def test_catalog_counts_4_emulators_6_providers_7_modes_35_requests(self) -> None:
        self.assertEqual(len(ALL_4_WIRE_PROTOCOL_EMULATORS), 4)
        self.assertEqual(len(ALL_6_BYOK_UPSTREAM_PROVIDERS), 6)
        self.assertEqual(len(ALL_7_MITM_PROXY_MODES), 7)
        self.assertEqual(len(ALL_7_PROXY_MODE_SPECS), 7)
        self.assertEqual(len(ALL_35_CLOUD_PROXY_BENCHMARK_TASKS), 35)

    def test_slot_family_1_portal_byok_vault_4_protocol_emulators_and_signed_download(self) -> None:
        portal = CloudProxyByokPortalAndEmulatorSlot()
        expected_wire_headers = {
            EMULATOR_OPENAI_CHAT_COMPLETIONS: "POST /v1/chat/completions",
            EMULATOR_ANTHROPIC_MESSAGES: "POST /v1/messages",
            EMULATOR_OPENAI_RESPONSES: "POST /v1/responses",
            EMULATOR_OLLAMA_CHAT: "POST /api/chat",
        }
        for idx, (emulator, expected_wire) in enumerate(expected_wire_headers.items()):
            res = portal.provision_portal_byok_and_emulate_endpoint(
                upstream_provider="openai",
                wire_emulator=emulator,
                artifact_slug="sqlite-fair-queue-wal-kit",
                request_id=f"test_emulator_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_CLOUD_PROXY_BYOK_EMULATOR)
            self.assertEqual(res.selected_engine, emulator)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")
            out = res.output
            self.assertEqual(out["portal_route"], "/account/proxy-vault")
            self.assertTrue(str(out["virtual_proxy_key"]).startswith("btr_proxy_"))
            self.assertFalse(out["plaintext_byok_exposed"])
            self.assertEqual(out["emulated_wire_response"]["wire_protocol"], expected_wire)
            dl = out["signed_download_bundle"]
            self.assertIn("https://baltor.ai/dl/lease_", dl["temporary_download_url"])
            self.assertIn("?sig=", dl["temporary_download_url"])
            self.assertIn("https://agentfeeds.si/v1/streams/", dl["agentfeeds_pointer_uri"])

    def test_slot_family_2_all_7_mitm_proxy_modes(self) -> None:
        mitm = SevenModeMitmProxyOrchestratorSlot()
        representative_tasks = (
            ("PROXY_01", MODE_M1_DIRECT_EMULATED_RESPONDER),
            ("PROXY_06", MODE_M2_CONTEXT_CONCATENATING_PASSTHROUGH),
            ("PROXY_11", MODE_M3_PROXY_SIDE_TOOL_LOOP),
            ("PROXY_16", MODE_M4_POST_RESPONSE_VERIFIER_HEAL),
            ("PROXY_21", MODE_M5_CHEAP_TO_FRONTIER_SPLIT),
            ("PROXY_26", MODE_M6_SPECULATIVE_PARALLEL_RACE),
            ("PROXY_31", MODE_M7_FAIL_OPEN_PASSTHROUGH),
        )
        for task_id, expected_mode in representative_tasks:
            res = mitm.execute_proxy_request(task_id, request_id=f"test_mode_{task_id}")
            self.assertTrue(res.accepted)
            self.assertEqual(res.slot_id, SLOT_SEVEN_MODE_MITM_PROXY)
            self.assertEqual(res.selected_engine, expected_mode)
            self.assertEqual(res.output["loop_vertex_class"], "Loop")
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

        # Verify M1 zero-token short-circuit
        m1_res = mitm.execute_proxy_request("PROXY_01", request_id="test_m1_check")
        self.assertTrue(m1_res.output["short_circuited_without_upstream_llm"])
        self.assertEqual(m1_res.output["proxy_upstream_tokens"], 0)
        self.assertLess(m1_res.output["proxy_latency_ms"], 2.5)

        # Verify M3 server-side tool loop interception
        m3_res = mitm.execute_proxy_request("PROXY_11", request_id="test_m3_check")
        self.assertGreater(m3_res.output["intercepted_server_side_tool_calls"], 0)

        # Verify M4 surgical self-heal gate
        m4_res = mitm.execute_proxy_request("PROXY_16", request_id="test_m4_check")
        self.assertTrue(m4_res.output["surgical_m4_self_heal_applied"])

    def test_4_known_wrong_controls_refused_at_preflight(self) -> None:
        kw = run_known_wrong_controls()
        self.assertTrue(kw["all_4_controls_refused"])
        controls = kw["controls"]
        self.assertEqual(
            controls["control_a_byok_credential_exposure"]["refusal_code"],
            "byok_credential_exposure_refused",
        )
        self.assertEqual(
            controls["control_b_upstream_host_credential_mismatch"]["refusal_code"],
            "upstream_host_credential_mismatch_refused",
        )
        self.assertEqual(
            controls["control_c_ephemeral_download_signature_invalid"]["refusal_code"],
            "ephemeral_download_signature_invalid_refused",
        )
        self.assertEqual(
            controls["control_d_m4_unverified_safety_critical_release"]["refusal_code"],
            "m4_unverified_safety_critical_release_refused",
        )
        for item in controls.values():
            self.assertFalse(item["accepted"])
            self.assertEqual(item["layer"], LAYER_PREFLIGHT)

    def test_frustration_avoidance_idempotency_conflict_refused(self) -> None:
        portal = CloudProxyByokPortalAndEmulatorSlot()
        first = portal.provision_portal_byok_and_emulate_endpoint(
            upstream_provider="openai",
            request_id="dup_proxy_req",
        )
        self.assertTrue(first.accepted)
        conflict = portal.provision_portal_byok_and_emulate_endpoint(
            upstream_provider="anthropic",
            request_id="dup_proxy_req",
        )
        self.assertFalse(conflict.accepted)
        self.assertEqual(conflict.layer_verdicts["frustration_avoidance"], LAYER_REFUSED)
        self.assertIsNotNone(conflict.refusal)
        assert conflict.refusal is not None
        self.assertEqual(conflict.refusal.code, "idempotency_payload_conflict")

    def test_35_request_benchmark_metrics(self) -> None:
        report = run_baltor_cloud_proxy_7mode_benchmark()
        self.assertEqual(report["total_requests_evaluated"], 35)
        comp = report["comparison"]
        direct = comp[ENGINE_DIRECT_UPSTREAM_WITHOUT_PROXY]
        proxy = comp[ENGINE_BALTOR_7MODE_CLOUD_PROXY]

        self.assertEqual(direct["verified_pass_count"], 17)
        self.assertEqual(direct["verified_pass_rate_pct"], 48.6)
        self.assertEqual(proxy["verified_pass_count"], 34)
        self.assertEqual(proxy["verified_pass_rate_pct"], 97.1)
        self.assertGreaterEqual(proxy["upstream_token_reduction_pct"], 84.0)
        self.assertGreaterEqual(proxy["mean_dollar_cost_reduction_pct"], 93.0)
        self.assertEqual(proxy["m1_direct_short_circuit_mean_latency_ms"], 1.8)


if __name__ == "__main__":
    unittest.main()
