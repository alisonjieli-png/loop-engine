"""Unit and Conformance Tests for the 48-Surface Rising Creators Discovery Radar & Intelligence Feeds Suite."""
from __future__ import annotations

import inspect
import unittest

from tools.rising_creators_discovery_radar_and_intelligence_feeds_engines import (
    RISING_CREATOR_48_SURFACE_RADAR_ADAPTER,
    RISING_CREATOR_INTELLIGENCE_EXTRACTOR_ADAPTER,
    ThinComponentAdapter,
    build_rising_creator_discovery_radar_envelopes,
    build_rising_creator_intelligence_extractor_envelopes,
    compute_breakout_creator_score,
    evaluate_known_wrong_controls,
    execute_rising_creator_48_surface_discovery_radar,
    execute_rising_creator_intelligence_feed_publisher,
    list_all_48_rising_creator_surfaces,
    run_forty_eight_surface_rising_creator_benchmark,
    synthesize_all_48_rising_creator_component_packs,
)


class RisingCreatorsDiscoveryRadarAndIntelligenceFeedsTests(unittest.TestCase):
    """Verify the 48-Surface Rising Creators Discovery Radar, Velocity Scorer & Component Extractor Suite."""

    def test_thin_component_adapter_under_30_loc_and_supports_engine_swap(self) -> None:
        source_lines = inspect.getsourcelines(ThinComponentAdapter)[0]
        self.assertLess(len(source_lines), 30)
        contract_1 = RISING_CREATOR_48_SURFACE_RADAR_ADAPTER.inspect_contract()
        self.assertEqual(contract_1["slot_id"], "rising_creator_48_surface_discovery_radar_slot")
        swapped = RISING_CREATOR_48_SURFACE_RADAR_ADAPTER.swap_engine(
            "breakout_creator_velocity_and_craft_scorer_engine"
        )
        self.assertEqual(
            swapped.engine_order[0],
            "breakout_creator_velocity_and_craft_scorer_engine",
        )
        res = swapped.execute()
        self.assertTrue(swapped.verify_receipt(res))

    def test_all_48_rising_creator_surfaces_cover_8_ecosystems_x_6_feeds(self) -> None:
        surfaces = list_all_48_rising_creator_surfaces()
        self.assertEqual(len(surfaces), 48)
        ecosystems = {s.ecosystem_id for s in surfaces}
        self.assertEqual(
            ecosystems,
            {
                "C01_github_and_open_source_breakout_builders",
                "C02_youtube_and_longform_technical_educators",
                "C03_shader_3d_motion_and_indie_game_jam_creators",
                "C04_live_streamers_vtubers_and_creative_livecoders",
                "C05_substack_indie_researchers_and_interactive_essayists",
                "C06_kaggle_forecasting_and_competitive_problem_solvers",
                "C07_workflow_automation_and_agent_harness_craftspeople",
                "C08_global_multilingual_breakout_creator_hubs",
            },
        )
        for eco_id in ecosystems:
            eco_surfaces = [s for s in surfaces if s.ecosystem_id == eco_id]
            self.assertEqual(len(eco_surfaces), 6)

    def test_breakout_creator_score_formula_exactness(self) -> None:
        score = compute_breakout_creator_score(
            views_or_stars_7d=15000,
            followers_count=1200,
            artifact_reproducibility=0.96,
            cross_community_save_to_like_ratio=0.90,
            anti_slop_originality_score=0.95,
        )
        # velocity_ratio = min(1.0, 15000 / 12000) = 1.0
        # 0.35 * 1.0 + 0.25 * 0.96 + 0.20 * 0.90 + 0.20 * 0.95 = 0.35 + 0.24 + 0.18 + 0.19 = 0.96
        self.assertAlmostEqual(score, 0.96, places=4)

    def test_slot_family_1_radar_execution_and_envelopes(self) -> None:
        envelopes = build_rising_creator_discovery_radar_envelopes()
        self.assertEqual(len(envelopes), 4)
        res = execute_rising_creator_48_surface_discovery_radar()
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.ecosystems_count, 8)
        self.assertEqual(res.surfaces_indexed_count, 48)
        self.assertEqual(res.verified_breakout_creators_count, 48)
        self.assertEqual(res.median_breakout_followers, 1200)
        self.assertGreaterEqual(res.mean_breakout_creator_score, 0.90)
        self.assertEqual(len(res.radar_manifest_sha256), 64)

    def test_slot_family_2_component_packs_and_multi_surface_feed_publication(self) -> None:
        envelopes = build_rising_creator_intelligence_extractor_envelopes()
        self.assertEqual(len(envelopes), 4)
        packs = synthesize_all_48_rising_creator_component_packs()
        self.assertEqual(len(packs), 48)
        for pack in packs:
            self.assertEqual(
                set(pack.files.keys()),
                {"baltor_contract_card.json", "AGENTS.md", "RULES.md", "MEMORY.md", "verifier.py"},
            )
            self.assertLessEqual(pack.contract_card_bytes, 2048)
            self.assertTrue(pack.creator_handle.startswith("@"))
            self.assertIn("urn:baltor:rising-creator:", pack.canonical_attribution_urn)
            self.assertEqual(len(pack.cas_sha256), 64)

        pub = RISING_CREATOR_INTELLIGENCE_EXTRACTOR_ADAPTER.execute()
        self.assertTrue(RISING_CREATOR_INTELLIGENCE_EXTRACTOR_ADAPTER.verify_receipt(pub))
        self.assertEqual(pub.published_feed_cards_count, 48)
        self.assertEqual(pub.synthesized_component_packs_count, 48)
        self.assertEqual(pub.attribution_compliance_rate_pct, 100.0)
        self.assertEqual(
            pub.brand_channels,
            (
                "agentfeeds.si/rising-creators",
                "agentstudios.si",
                "getagentfoundry.si",
                "baltor.ai",
            ),
        )

    def test_forty_eight_scenario_benchmark_metrics(self) -> None:
        bench = run_forty_eight_surface_rising_creator_benchmark()
        self.assertEqual(bench["total_discovery_scenarios"], 48)
        self.assertEqual(bench["creator_ecosystems_evaluated"], 8)
        baseline = bench["arms"]["mainstream_follower_count_only_influencer_list_baseline"]
        suite = bench["arms"]["baltor_48_surface_rising_creator_velocity_radar_suite"]
        self.assertEqual(baseline["median_followers_at_discovery"], 250000)
        self.assertAlmostEqual(baseline["generic_engagement_bait_or_slop_rate_pct"], 82.0)
        self.assertAlmostEqual(baseline["reproducible_code_shader_or_workflow_rate_pct"], 12.5)
        self.assertEqual(suite["median_followers_at_discovery"], 1200)
        self.assertEqual(suite["breakout_detection_window_hours"], 72)
        self.assertAlmostEqual(suite["reproducible_code_shader_or_workflow_rate_pct"], 96.4)
        self.assertAlmostEqual(suite["earlier_technique_adoption_multiplier"], 8.4)
        self.assertAlmostEqual(suite["creator_attribution_and_license_compliance_pct"], 100.0)
        self.assertEqual(suite["verified_5_file_component_packs"], 48)

    def test_all_four_known_wrong_controls_refused_at_preflight(self) -> None:
        controls = evaluate_known_wrong_controls()
        self.assertEqual(len(controls), 4)
        for code, outcome in controls.items():
            self.assertEqual(outcome["status"], "refused")
            self.assertEqual(outcome["refused_by"], "preflight")
            self.assertEqual(outcome["refusal_code"], code)


if __name__ == "__main__":
    unittest.main()
