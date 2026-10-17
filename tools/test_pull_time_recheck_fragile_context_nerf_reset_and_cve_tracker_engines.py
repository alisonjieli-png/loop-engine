"""Unit tests for the Fragile / Volatile Pull-Time-Recheck Context Engine,
Live Tool-Nerf & Coding-Reset Telemetry Miner, Positive/Negative Social
Intelligence & CVE Vulnerability Tracker + Challenger Re-Ranker Suite.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from pull_time_recheck_fragile_context_nerf_reset_and_cve_tracker_engines import (  # noqa: E402
    ALL_6_VOLATILITY_CLASSES,
    ALL_48_VOLATILE_RECHECK_NERF_CVE_SCENARIOS,
    COMPACT_CARD_BYTES,
    COVERAGE_LAYERS,
    ENGINE_BALTOR_PULL_TIME_RECHECK_NERF_RESET_SOCIAL_AND_CVE_RERANKER_SUITE,
    ENGINE_CONTINUOUS_CHALLENGER_EXPLORER_AND_MULTIDIMENSIONAL_RERANKER,
    ENGINE_EVERY_PULL_AND_EVENT_TRIGGERED_REVALIDATOR,
    ENGINE_STATIC_CACHED_RAG_AND_FIXED_RANKING_BASELINE,
    EXTENDED_POLICY_OR_LEGAL_CARD_BYTES,
    FRAGILE_CONTEXT_RECHECK_ADAPTER,
    LAYER_PREFLIGHT,
    NERF_RESET_SOCIAL_CVE_RERANKER_ADAPTER,
    SEVEN_RANKING_DIMENSIONS,
    SLOT_FRAGILE_CONTEXT_AND_PULL_TIME_RECHECK,
    SLOT_TOOL_NERF_CODING_RESET_SOCIAL_AND_CVE_RERANKER,
    UNRESTRICTED_BUNDLE_BYTES,
    VOLATILITY_CLASS_V1,
    VOLATILITY_CLASS_V2,
    VOLATILITY_CLASS_V3,
    VOLATILITY_CLASS_V4,
    VOLATILITY_CLASS_V5,
    VOLATILITY_CLASS_V6,
    classify_fragile_and_volatile_context,
    compute_coding_reset_telemetry,
    detect_tool_nerf_and_capability_degradation,
    evaluate_cve_and_rerank_challengers,
    evaluate_pull_time_recheck_nerf_reset_and_cve_suite,
    fuse_positive_and_negative_social_intelligence,
    govern_elastic_byte_and_file_length_policy,
    invoke_fragile_context_recheck_slot,
    invoke_nerf_reset_social_cve_reranker_slot,
    revalidate_fragile_context_on_pull,
    run_known_wrong_refusal_controls,
)


class PullTimeRecheckFragileContextNerfResetAndCveTrackerTests(unittest.TestCase):
    """Verify Slot Family 1, Slot Family 2, 48-scenario benchmarks, and 4 known-wrong controls."""

    def test_v1_to_v6_fragility_and_volatility_classifier(self) -> None:
        self.assertEqual(len(ALL_6_VOLATILITY_CLASSES), 6)
        v1 = classify_fragile_and_volatile_context("ftc_16_cfr_255", ("law", "cfr"))
        v2 = classify_fragile_and_volatile_context("app_store_policy", ("platform_policy", "tos"))
        v3 = classify_fragile_and_volatile_context("token_tariff_table", ("pricing", "tariff"))
        v4 = classify_fragile_and_volatile_context("mcp_abi_surface", ("sdk_contract", "abi"))
        v5 = classify_fragile_and_volatile_context("oauth_jwks_probe", ("tls_cert", "oauth_discovery"))
        v6 = classify_fragile_and_volatile_context("aho_corasick_automaton", ("math_primitive",))

        self.assertEqual(v1.volatility_class, VOLATILITY_CLASS_V1)
        self.assertTrue(v1.revalidate_on_every_pull)
        self.assertTrue(v1.requires_effective_date_or_repeal_check)

        self.assertEqual(v2.volatility_class, VOLATILITY_CLASS_V2)
        self.assertTrue(v2.revalidate_on_every_pull)

        self.assertEqual(v3.volatility_class, VOLATILITY_CLASS_V3)
        self.assertTrue(v3.revalidate_on_every_pull)

        self.assertEqual(v4.volatility_class, VOLATILITY_CLASS_V4)
        self.assertFalse(v4.revalidate_on_every_pull)
        self.assertIn("upstream_release_tag", v4.trigger_watch_set)

        self.assertEqual(v5.volatility_class, VOLATILITY_CLASS_V5)
        self.assertTrue(v5.revalidate_on_every_pull)
        self.assertTrue(v5.requires_liveness_probe)

        self.assertEqual(v6.volatility_class, VOLATILITY_CLASS_V6)
        self.assertFalse(v6.revalidate_on_every_pull)
        self.assertIsNone(v6.cache_ttl_seconds)

    def test_every_pull_revalidator_and_elastic_byte_governor(self) -> None:
        v1 = classify_fragile_and_volatile_context("eu_ai_act_card", ("eu_ai_act",))
        cached = {"component_id": "eu_ai_act_card", "revision": 7, "content_sha256": "sha256:old"}
        probe = {
            "upstream_sha256": "sha256:new_2026_10",
            "trigger_fired": True,
            "repealed_or_superseded": False,
            "effective_date_active": True,
            "updated_clauses": ("Article 50 transparency obligations active",),
        }
        patched, receipt = revalidate_fragile_context_on_pull(v1, cached, probe)
        self.assertTrue(receipt.patched_in_flight)
        self.assertEqual(receipt.served_revision, 8)
        self.assertEqual(patched["revision"], 8)
        self.assertEqual(patched["status"], "revalidated_patched_in_flight")
        self.assertLess(receipt.recheck_latency_ms, 1.0)

        elastic = govern_elastic_byte_and_file_length_policy(
            payload_bytes=48_000,
            line_count=1250,
            profile="extended_policy_or_legal_card",
            caller_max_file_lines=None,
        )
        self.assertEqual(elastic["compact_card_bytes"], COMPACT_CARD_BYTES)
        self.assertEqual(elastic["extended_policy_or_legal_card_bytes"], EXTENDED_POLICY_OR_LEGAL_CARD_BYTES)
        self.assertEqual(elastic["unrestricted_bundle_bytes"], UNRESTRICTED_BUNDLE_BYTES)
        self.assertTrue(elastic["within_elastic_envelope"])
        self.assertTrue(elastic["mem_max_3g_safe"])

    def test_coding_reset_miner_and_tool_nerf_detector(self) -> None:
        telemetry = compute_coding_reset_telemetry(
            component_id="comp_flaky_regex_parser",
            model_name="Qwen3-Coder",
            invocations=100,
            event_counts={
                "git_reset_hard": 5,
                "git_checkout_file": 3,
                "git_revert": 2,
                "ctrl_z_undo_bursts": 2,
                "post_turn_human_deletes": 1,
                "test_failure_rollbacks": 1,
            },
        )
        self.assertEqual(telemetry["coding_reset_rate_pct"], 14.0)
        self.assertTrue(telemetry["fragile_under_current_model"])
        self.assertEqual(telemetry["routing_action"], "demote_and_route_to_automated_repair")

        nerf = detect_tool_nerf_and_capability_degradation(
            tool_id="openai_dots_muse_virtual_desktop_dialog",
            baseline_pass_rate=0.96,
            recent_pass_Window=(0.80, 0.70, 0.60, 0.50),
            recent_refusal_rate=0.31,
            reported_nerf_signatures=("virtual_desktop_file_dialog_blocked",),
            sovereign_workaround_id="baltor_unnerfed_xdotool_cdp_file_chooser_engine",
        )
        self.assertTrue(nerf["nerf_detected"])
        self.assertEqual(
            nerf["active_component_after_check"],
            "baltor_unnerfed_xdotool_cdp_file_chooser_engine",
        )

    def test_social_intelligence_fusion_and_cve_challenger_reranker(self) -> None:
        social = fuse_positive_and_negative_social_intelligence(
            component_id="comp_challenger_simd_rust_v3",
            reports=(
                {"source": "hacker_news", "polarity": "positive", "practitioner_credibility": 0.92, "has_repro_or_benchmark": True, "account_age_days": 900, "burst_coordination_score": 0.03},
                {"source": "x_astroturf", "polarity": "negative", "practitioner_credibility": 0.12, "has_repro_or_benchmark": False, "account_age_days": 2, "burst_coordination_score": 0.95},
            ),
        )
        self.assertEqual(social["filtered_astroturf_count"], 1)
        self.assertGreater(social["social_practitioner_net_sentiment"], 0.70)

        res = invoke_nerf_reset_social_cve_reranker_slot({"model_name": "Claude Fable 5.1"})
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_TOOL_NERF_CODING_RESET_SOCIAL_AND_CVE_RERANKER)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        reranked = res.output["cve_and_challenger_reranking"]
        self.assertIn("comp_vulnerable_parser_cve_2026_4412", reranked["quarantined_component_ids"])
        self.assertLess(reranked["cve_quarantine_latency_ms"], 0.5)
        self.assertEqual(reranked["selected_top_component_id"], "comp_challenger_simd_rust_v3")
        top_cand = reranked["ranked_candidates"][0]
        self.assertEqual(set(top_cand["dimensions"].keys()), set(SEVEN_RANKING_DIMENSIONS))

    def test_thin_component_adapter_contract_receipt_and_hot_swap(self) -> None:
        c1 = FRAGILE_CONTEXT_RECHECK_ADAPTER.inspect_contract()
        c2 = NERF_RESET_SOCIAL_CVE_RERANKER_ADAPTER.inspect_contract()
        self.assertEqual(c1["slot_id"], SLOT_FRAGILE_CONTEXT_AND_PULL_TIME_RECHECK)
        self.assertEqual(c2["slot_id"], SLOT_TOOL_NERF_CODING_RESET_SOCIAL_AND_CVE_RERANKER)
        self.assertLess(c1["loc"], 30)

        r1 = invoke_fragile_context_recheck_slot({"component_id": "comp_nec_code"})
        self.assertTrue(FRAGILE_CONTEXT_RECHECK_ADAPTER.verify_receipt(r1))

        swapped_s1 = FRAGILE_CONTEXT_RECHECK_ADAPTER.swap_engine(
            ENGINE_EVERY_PULL_AND_EVENT_TRIGGERED_REVALIDATOR
        )
        self.assertEqual(swapped_s1.engine_order[0], ENGINE_EVERY_PULL_AND_EVENT_TRIGGERED_REVALIDATOR)
        swapped_s2 = NERF_RESET_SOCIAL_CVE_RERANKER_ADAPTER.swap_engine(
            ENGINE_CONTINUOUS_CHALLENGER_EXPLORER_AND_MULTIDIMENSIONAL_RERANKER
        )
        self.assertEqual(
            swapped_s2.engine_order[0],
            ENGINE_CONTINUOUS_CHALLENGER_EXPLORER_AND_MULTIDIMENSIONAL_RERANKER,
        )
        self.assertTrue(FRAGILE_CONTEXT_RECHECK_ADAPTER.preflight({"component_id": "ok"}).ready)
        self.assertTrue(NERF_RESET_SOCIAL_CVE_RERANKER_ADAPTER.preflight({"model_name": "Gemma 4"}).ready)

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "unverified_fragile_pull_time_context_blocked": "unverified_fragile_pull_time_context_refused",
            "vulnerable_cve_component_recommendation_blocked": "vulnerable_cve_component_recommendation_refused",
            "nerfed_or_high_reset_tool_top_rank_blocked": "nerfed_or_high_reset_tool_top_rank_refused",
            "unverified_social_astroturf_override_blocked": "unverified_social_astroturf_override_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_48_scenario_benchmark_suite(self) -> None:
        self.assertEqual(len(ALL_48_VOLATILE_RECHECK_NERF_CVE_SCENARIOS), 48)
        report = evaluate_pull_time_recheck_nerf_reset_and_cve_suite()
        self.assertEqual(report["scenario_count"], 48)
        self.assertEqual(report["volatility_class_count"], 6)
        self.assertTrue(report["all_scenarios_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_STATIC_CACHED_RAG_AND_FIXED_RANKING_BASELINE]
        suite = report["benchmarks"][
            ENGINE_BALTOR_PULL_TIME_RECHECK_NERF_RESET_SOCIAL_AND_CVE_RERANKER_SUITE
        ]
        self.assertEqual(base["pull_time_reverification_rate_v1_v5_pct"], 0.0)
        self.assertEqual(base["stale_or_repealed_policy_citation_rate_pct"], 68.8)
        self.assertEqual(suite["pull_time_reverification_rate_v1_v5_pct"], 100.0)
        self.assertEqual(suite["pull_time_reverification_latency_ms"], 0.62)
        self.assertEqual(suite["stale_or_repealed_policy_citation_rate_pct"], 0.0)
        self.assertEqual(suite["tool_nerf_and_coding_reset_adaptation_rate_pct"], 100.0)
        self.assertEqual(suite["critical_cve_quarantine_rate_pct"], 100.0)
        self.assertLess(suite["critical_cve_quarantine_latency_ms"], 0.45)
        self.assertEqual(suite["continuous_challenger_improvement_gain_pct"], 31.4)


if __name__ == "__main__":
    unittest.main()
