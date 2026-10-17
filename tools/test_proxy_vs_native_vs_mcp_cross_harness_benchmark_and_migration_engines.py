"""Tests for tools/proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines.py.

Verifies:
1. Slot Family 1 (`web_portal_proxy_onboarding_config_slot`): all 12 client proxy profiles,
   all 4 proxy intervention policies (`auto_direct_or_augment`, `strict_verifier_self_heal`,
   `cheap_model_downshift_first`, `shadow_telemetry_only`), all 3 onboarding engines,
   and 7-layer `ComponentEnvelope` enforcement.
2. Slot Family 2 (`four_integration_path_gauntlet_evaluator_slot`): 12 clients x 4 integration
   paths (`48` cells) across `30` high-failure tasks, proving P0 (`44.2%`), P1 (`79.5%`,
   `20.5%` tool-skipping gap), P2 (`96.8%`, `100.0%` trigger reliability), and P3 (`99.2%`,
   `-88.4%` token spend, `-95.1%` dollar spend).
3. All 4 known-wrong controls (`raw_upstream_secret_in_client_config_rejected`,
   `insecure_public_http_proxy_baseurl_rejected`,
   `missing_upstream_429_503_fallback_policy_rejected`,
   `self_approved_benchmark_receipt_rejected`).
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import proxy_vs_native_vs_mcp_cross_harness_benchmark_and_migration_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_PREFLIGHT  # noqa: E402


class ProxyVsNativeVsMcpCrossHarnessBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = suite.run_full_proxy_onboarding_and_gauntlet_benchmark()

    def test_full_suite_passes_all_slots_and_envelope_layers(self) -> None:
        self.assertTrue(self.report["passed"])
        self.assertEqual(self.report["envelope_layers"], list(COVERAGE_LAYERS))
        self.assertEqual(self.report["slots"], list(suite.ALL_SLOTS))

    def test_all_twelve_client_profiles_and_four_intervention_policies(self) -> None:
        bundles = self.report["onboarding_bundles"]
        self.assertEqual(len(bundles), 12)
        expected_profiles = (
            "claude_code_cli_proxy_profile",
            "openai_codex_cli_proxy_profile",
            "cursor_ide_override_baseurl_profile",
            "windsurf_cline_roocode_proxy_profile",
            "opencode_baltor_and_vanilla_opencode_proxy_profile",
            "pi_pie_minimal_agent_proxy_profile",
            "openclaw_autonomous_agent_proxy_profile",
            "hermes_persistent_state_proxy_profile",
            "dot_personal_assistant_proxy_profile",
            "aider_and_continue_dev_proxy_profile",
            "python_ts_openai_anthropic_sdk_profile",
            "ollama_local_and_cloud_bridge_profile",
        )
        dl_prefix = suite._endpoint("https", "baltor.ai/dl/tmp/")
        for pid in expected_profiles:
            self.assertIn(pid, bundles)
            entry = bundles[pid]
            self.assertTrue(entry["accepted"])
            bundle = entry["bundle"]
            self.assertTrue(bundle["scoped_proxy_token_is_btr_scoped"])
            self.assertFalse(bundle["raw_upstream_secret_exposed"])
            self.assertTrue(bundle["upstream_connectivity_verified"])
            self.assertTrue(
                bundle["signed_temporary_bundle_download_url"].startswith(dl_prefix)
            )

        self.assertEqual(
            bundles["claude_code_cli_proxy_profile"]["bundle"]["base_url"],
            suite._endpoint("https", "baltor.ai/anthropic/v1"),
        )
        self.assertEqual(
            bundles["openai_codex_cli_proxy_profile"]["bundle"]["base_url"],
            suite._endpoint("https", "baltor.ai/v1"),
        )
        self.assertEqual(
            bundles["ollama_local_and_cloud_bridge_profile"]["bundle"]["base_url"],
            suite._endpoint("https", "baltor.ai/ollama"),
        )

        for pol in suite.INTERVENTION_POLICIES:
            self.assertTrue(self.report["policy_verifications"][pol])

    def test_onboarding_engine_cascade_and_fallback_selection(self) -> None:
        res_sidecar = suite.generate_portal_proxy_onboarding_bundle(
            "acct_sidecar_01",
            "pi_pie_minimal_agent_proxy_profile",
            preferred_engine=suite.ENG_ONBOARD_LOOPBACK_SIDECAR,
        )
        self.assertTrue(res_sidecar.accepted)
        self.assertEqual(res_sidecar.selected_engine, suite.ENG_ONBOARD_LOOPBACK_SIDECAR)
        self.assertEqual(
            res_sidecar.fallback_chain_tried,
            (suite.ENG_ONBOARD_PORTAL_BUNDLE, suite.ENG_ONBOARD_LOOPBACK_SIDECAR),
        )
        self.assertEqual(res_sidecar.output["base_url"], suite._endpoint("http", "127.0.0.1:8787/v1"))

        res_manual = suite.generate_portal_proxy_onboarding_bundle(
            "acct_manual_01",
            "python_ts_openai_anthropic_sdk_profile",
            preferred_engine=suite.ENG_ONBOARD_MANUAL_ENV_FALLBACK,
        )
        self.assertTrue(res_manual.accepted)
        self.assertEqual(res_manual.selected_engine, suite.ENG_ONBOARD_MANUAL_ENV_FALLBACK)
        self.assertEqual(res_manual.fallback_chain_tried, suite.ONBOARDING_ENGINES)

    def test_four_integration_path_48_cell_gauntlet_metrics(self) -> None:
        gauntlet = self.report["gauntlet"]
        self.assertEqual(gauntlet["total_clients"], 12)
        self.assertEqual(gauntlet["total_paths"], 4)
        self.assertEqual(gauntlet["total_cells"], 48)
        self.assertEqual(gauntlet["high_failure_tasks_evaluated"], 30)

        summaries = gauntlet["path_summaries"]
        p0 = summaries[suite.PATH_P0_RAW]
        p1 = summaries[suite.PATH_P1_PASSIVE_MCP]
        p2 = summaries[suite.PATH_P2_PROXY_MITM]
        p3 = summaries[suite.PATH_P3_PROXY_NATIVE_FORK]

        self.assertAlmostEqual(p0["pass_rate_pct"], 44.2, places=1)
        self.assertAlmostEqual(p0["auto_trigger_reliability_pct"], 0.0, places=1)
        self.assertAlmostEqual(p0["mean_cost_usd"], 0.082, places=3)

        self.assertAlmostEqual(p1["pass_rate_pct"], 79.5, places=1)
        self.assertAlmostEqual(p1["tool_skipping_gap_pct"], 20.5, places=1)

        self.assertAlmostEqual(p2["pass_rate_pct"], 96.8, places=1)
        self.assertAlmostEqual(p2["auto_trigger_reliability_pct"], 100.0, places=1)
        self.assertAlmostEqual(p2["tool_skipping_gap_pct"], 0.0, places=1)

        self.assertAlmostEqual(p3["pass_rate_pct"], 99.2, places=1)
        self.assertAlmostEqual(p3["auto_trigger_reliability_pct"], 100.0, places=1)
        self.assertAlmostEqual(p3["token_spend_delta_vs_p0_pct"], -88.4, places=1)
        self.assertAlmostEqual(p3["dollar_spend_delta_vs_p0_pct"], -95.1, places=1)

    def test_all_four_known_wrong_controls_refuse_and_leak_when_disabled(self) -> None:
        controls = self.report["known_wrong_controls"]
        self.assertEqual(len(controls), 4)
        expected_codes = {
            "raw_upstream_secret_in_client_config_rejected",
            "insecure_public_http_proxy_baseurl_rejected",
            "missing_upstream_429_503_fallback_policy_rejected",
            "self_approved_benchmark_receipt_rejected",
        }
        observed_codes = set()
        for ctrl in controls:
            self.assertTrue(ctrl["known_wrong_detected"], f"Control failed: {ctrl}")
            self.assertTrue(ctrl["leaked_when_removed"], f"Control did not leak when removed: {ctrl}")
            observed_codes.add(ctrl["observed_refusal_code"])
        self.assertEqual(observed_codes, expected_codes)

        bad_token_res = suite.generate_portal_proxy_onboarding_bundle(
            "acct_direct_check",
            "claude_code_cli_proxy_profile",
            client_token_override=suite._fixture_token("sk", "proj-raw-openai-sample"),
        )
        self.assertFalse(bad_token_res.accepted)
        self.assertIsNotNone(bad_token_res.trace)
        self.assertEqual(bad_token_res.trace.refused_by, LAYER_PREFLIGHT)


if __name__ == "__main__":
    unittest.main()
