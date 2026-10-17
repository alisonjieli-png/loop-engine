"""Tests and known-wrong controls for the Portable Anywhere-Launch Two-Way Spider/Benchmark
Workers, Sprouting Keyword/Trend Detector, and Self-Prioritizing Autonomous Discovery Queue.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import portable_two_way_spider_worker_and_self_prioritizing_trend_engines as spider_suite  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class PortableTwoWaySpiderWorkerAndSelfPrioritizingTrendTests(unittest.TestCase):
    """Verify both slot families, all 6 engines, 7 envelope layers, and 4 known-wrong controls."""

    def test_slot1_portable_two_way_lease_heartbeat_and_offline_spool_fallback(self) -> None:
        slot = spider_suite.PortableTwoWaySpiderWorkerSlot()

        for idx, profile in enumerate(spider_suite.PORTABLE_LAUNCH_PROFILES):
            rpc_method = spider_suite.TWO_WAY_RPC_METHODS[idx % len(spider_suite.TWO_WAY_RPC_METHODS)]
            res = slot.execute_worker_cycle(
                worker_id=f"portable_worker_{idx}",
                launch_profile=profile,
                rpc_method=rpc_method,
                request_id=f"test_lease_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, spider_suite.ENGINE_TWO_WAY_LEASE_HEARTBEAT)
            self.assertEqual(res.output["launch_profile"], profile)
            self.assertEqual(res.output["negotiated_rpc_method"], rpc_method)
            self.assertTrue(str(res.output["fencing_token"]).startswith("fence_v1_10_"))
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

        # Verify deterministic offline spool fallback when disconnected
        offline_res = slot.execute_worker_cycle(
            worker_id="portable_worker_laptop",
            launch_profile="laptop_127_0_0_1",
            rpc_method="submit_candidate_bundle",
            offline_disconnected=True,
            request_id="test_offline_spool_01",
        )
        self.assertTrue(offline_res.accepted)
        self.assertEqual(offline_res.selected_engine, spider_suite.ENGINE_OFFLINE_SPOOL_FALLBACK)
        self.assertEqual(offline_res.output["status"], "spooled_locally_for_reconnect")
        self.assertEqual(offline_res.output["offline_spool_depth"], 1)

    def test_slot1_github_mit_and_owner_repo_spider_rule_6_dual_engines(self) -> None:
        slot = spider_suite.PortableTwoWaySpiderWorkerSlot()
        res = slot.execute_worker_cycle(
            operation_mode="github_and_owner_repo_harvest",
            request_id="test_repo_harvest_01",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.selected_engine, spider_suite.ENGINE_MULTI_SOURCE_GITHUB_SPIDER)
        self.assertEqual(res.output["harvested_count"], 9)
        self.assertEqual(res.output["permissive_or_owner_license_ratio"], 1.0)
        self.assertEqual(res.output["rule_6_external_plus_native_pair_ratio"], 1.0)

        repo_ids = {r["repo_id"] for r in res.output["harvested_repositories"]}
        for expected_repo in (
            "alisonjieli-png/loop-engine",
            "alisonjieli-png/baltor-library",
            "Amarel-Taylor-Scott/stock-research",
            "Amarel-Taylor-Scott/philippines-wins-everyday",
            "aidonerightcorp/solutiongraph",
            "local/roll_watch",
            "local/suspicious_networks_analysis",
            "local/ollama-loop-behavior-lab",
            "local/ai_agent_security_comp",
        ):
            self.assertIn(expected_repo, repo_ids)

    def test_slot1_live_model_and_harness_benchmark_scraper(self) -> None:
        slot = spider_suite.PortableTwoWaySpiderWorkerSlot()
        res = slot.execute_worker_cycle(
            operation_mode="live_benchmark_scrape",
            request_id="test_benchmark_scrape_01",
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.selected_engine, spider_suite.ENGINE_LIVE_BENCHMARK_SCRAPER)
        self.assertEqual(res.output["scraped_leaderboards_count"], 9)
        scraped_ids = {b["benchmark_id"] for b in res.output["leaderboard_updates"]}
        for expected_bm in (
            "GIFT-Eval",
            "fev-bench",
            "SWE-bench",
            "LiveCodeBench",
            "Artificial Analysis",
            "LMSYS Arena",
            "HuggingFace FineEnvs/multi-harness-rl",
            "Kaggle Competitions",
            "ArXiv CS.AI/CS.LG",
        ):
            self.assertIn(expected_bm, scraped_ids)

    def test_slot2_sprouting_keyword_velocity_and_evoi_self_prioritizer(self) -> None:
        slot = spider_suite.SproutingTrendAndSearchSelfPrioritizerSlot()

        # Verify CUSUM + EMA velocity engine directly
        vel_res = slot.prioritize_sprouting_trends(
            engine_preference=spider_suite.ENGINE_KUSUM_EMA_VELOCITY,
            request_id="test_kusum_ema_01",
        )
        self.assertTrue(vel_res.accepted)
        self.assertEqual(vel_res.selected_engine, spider_suite.ENGINE_KUSUM_EMA_VELOCITY)
        self.assertEqual(vel_res.output["sprouting_keywords_detected"], 7)
        for item in vel_res.output["ranked_queue"]:
            self.assertTrue(item["sprouting_detected"])
            self.assertGreater(float(item["velocity_v_dot"]), 0.0)
            self.assertGreater(float(item["acceleration_v_ddot"]), 0.0)

        # Verify 1-click Human Steering Pin elevates target to #1 in EVOI queue
        pin_info = slot.apply_human_steering("SolidCraft", "pin")
        self.assertEqual(pin_info["human_steering_multiplier"], 10.0)

        evoi_res = slot.prioritize_sprouting_trends(
            engine_preference=spider_suite.ENGINE_EVOI_QUEUE_PRIORITIZER,
            request_id="test_evoi_pin_01",
        )
        self.assertTrue(evoi_res.accepted)
        self.assertEqual(evoi_res.selected_engine, spider_suite.ENGINE_EVOI_QUEUE_PRIORITIZER)
        self.assertEqual(evoi_res.output["top_priority_keyword"], "SolidCraft")
        self.assertLess(float(evoi_res.output["average_detection_lag_minutes"]), 15.0)
        self.assertEqual(float(evoi_res.output["manual_founder_hours_per_day"]), 0.0)

    def test_known_wrong_controls_and_head_to_head_benchmark(self) -> None:
        spider_slot = spider_suite.PortableTwoWaySpiderWorkerSlot()
        trend_slot = spider_suite.SproutingTrendAndSearchSelfPrioritizerSlot()

        # Control A: Stale fencing token epoch rejected at Layer 3 (handshake)
        stale_res = spider_slot.execute_worker_cycle(
            worker_fencing_epoch=3,
            request_id="test_ctrl_a_stale_fence",
        )
        self.assertFalse(stale_res.accepted)
        self.assertEqual(stale_res.layer_verdicts["handshake"], LAYER_REFUSED)
        self.assertIsNotNone(stale_res.refusal)
        assert stale_res.refusal is not None
        self.assertEqual(stale_res.refusal.code, "stale_fencing_token_rejected")

        # Control B: Copyleft/unlicensed repository rejected from public MIT/Apache-2.0 tier at Layer 6 (preflight)
        copyleft_res = spider_slot.execute_worker_cycle(
            candidate_spdx_license="AGPL-3.0-only",
            target_catalog_tier="public_mit_apache_tier",
            request_id="test_ctrl_b_copyleft",
        )
        self.assertFalse(copyleft_res.accepted)
        self.assertEqual(copyleft_res.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(copyleft_res.refusal)
        assert copyleft_res.refusal is not None
        self.assertEqual(copyleft_res.refusal.code, "copyleft_or_unlicensed_repo_rejected")

        # Control C: Public spider SSRF targeting private RFC1918 or cloud metadata IP rejected at Layer 6 (preflight)
        ssrf_res = spider_slot.execute_worker_cycle(
            target_url="http://192.168.50.10:8080/internal-admin",
            worker_network_scope="public_spider",
            request_id="test_ctrl_c_ssrf_rfc1918",
        )
        self.assertFalse(ssrf_res.accepted)
        self.assertEqual(ssrf_res.layer_verdicts["preflight"], LAYER_REFUSED)
        self.assertIsNotNone(ssrf_res.refusal)
        assert ssrf_res.refusal is not None
        self.assertEqual(ssrf_res.refusal.code, "ssrf_private_or_metadata_ip_rejected")

        # Control D: Human steering Veto override immediately blocks synthesis at Layer 1 (frustration_avoidance)
        veto_res = trend_slot.prioritize_sprouting_trends(
            target_keyword="NoisyHypeRepo",
            steering_action="veto",
            request_id="test_ctrl_d_veto",
        )
        self.assertFalse(veto_res.accepted)
        self.assertEqual(veto_res.layer_verdicts["frustration_avoidance"], LAYER_REFUSED)
        self.assertIsNotNone(veto_res.refusal)
        assert veto_res.refusal is not None
        self.assertEqual(veto_res.refusal.code, "human_steering_veto_enforced")

        # Full benchmark summary check
        bench = spider_suite.run_portable_spider_and_trend_benchmarks()
        self.assertTrue(bench["all_known_wrong_controls_passed"])
        h2h = bench["head_to_head"]
        self.assertEqual(
            h2h[spider_suite.ENGINE_MANUAL_FOUNDER_BASELINE]["manual_founder_forum_reading_hours_per_day"],
            2.5,
        )
        self.assertEqual(
            h2h[spider_suite.ENGINE_AUTONOMOUS_TWO_WAY_SUITE]["manual_founder_forum_reading_hours_per_day"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
