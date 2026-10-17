"""Unit and conformance tests for RepoDir.com 3,480-URL Scanner, Video Studio & Auto-Discovery Ad Funnel Engines."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))
if str(_REPOSITORY_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "tools"))

from repodir_scanner_video_studio_and_auto_discovery_ad_engines import (  # noqa: E402
    AD_CAMPAIGN_ENGINE_IDS,
    ENGINE_FOUNDER_AD_PACK_COUNTER,
    ENGINE_PER_TOOL_LANDING_PAGE,
    ENGINE_REPODIR_CARD_SYNTHESIZER,
    ENGINE_REPODIR_LSH_ROUTER,
    ENGINE_REPODIR_SITEMAP_SCANNER,
    ENGINE_THREE_ACT_TOOL_VIDEO,
    REPODIR_AI_TOOL_URL_COUNT,
    REPODIR_COLLECTION_URL_COUNT,
    REPODIR_REPO_URL_COUNT,
    REPODIR_SITEMAP_TOTAL_URLS,
    REPODIR_TOPIC_URL_COUNT,
    REPODIR_TOTAL_INDEXED_TOOLS,
    SCANNER_INDEXER_ENGINE_IDS,
    SLOT_REPODIR_AD_CAMPAIGN,
    SLOT_REPODIR_SCANNER_INDEXER,
    SLOT_REPODIR_VIDEO_STUDIO,
    SUPPORTED_HARNESSES,
    VIDEO_STUDIO_ENGINE_IDS,
    run_repodir_3480_url_funnel_benchmark,
    run_repodir_auto_discovery_ad_campaign,
    run_repodir_per_tool_video_studio,
    run_repodir_scanner_and_component_indexer,
)
from loop_engine.core.engines.envelope import ENVELOPE_LAYERS, root_frame  # noqa: E402
from loop_engine.core.engines.envelope_preflight import VERDICT_READY, VERDICT_REPAIRED  # noqa: E402


class RepoDirScannerVideoStudioAndAdFunnelTests(unittest.TestCase):
    """Verify all 3 RepoDir slot families, 7-layer ComponentEnvelope traces, benchmarks, and known-wrong controls."""

    def test_slot1_sitemap_inventory_and_contract_card_synthesis(self) -> None:
        for engine_id in SCANNER_INDEXER_ENGINE_IDS:
            res = run_repodir_scanner_and_component_indexer(
                engine_id=engine_id,
                search_query="fast terminal directory jump",
                cached_commit_shas={"ajeetdsouza-zoxide": "9f8b2a1c4d5e6f708192a3b4c5d6e7f801234567"},
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["slot_id"], SLOT_REPODIR_SCANNER_INDEXER)
            self.assertEqual(res["envelope_layers"], ENVELOPE_LAYERS)
            self.assertTrue(res["envelope_trace"]["engine_dispatched"])
            self.assertEqual(res["preflight_report"]["verdict"], VERDICT_READY)

            inv = res["sitemap_inventory"]
            self.assertEqual(inv["total_sitemap_urls"], REPODIR_SITEMAP_TOTAL_URLS)
            self.assertEqual(inv["repo_urls"], REPODIR_REPO_URL_COUNT)
            self.assertEqual(inv["ai_tool_urls"], REPODIR_AI_TOOL_URL_COUNT)
            self.assertEqual(inv["topic_urls"], REPODIR_TOPIC_URL_COUNT)
            self.assertEqual(inv["collection_urls"], REPODIR_COLLECTION_URL_COUNT)
            self.assertEqual(inv["total_indexable_tools"], REPODIR_TOTAL_INDEXED_TOOLS)
            self.assertEqual(res["unchanged_skipped_count"], 1)

            for card in res["synthesized_component_cards"]:
                self.assertLessEqual(card["contract_card_bytes"], 2048)
                self.assertLess(card["contract_card_tokens"], 200)
                self.assertEqual(len(card["matryoshka_64bit_lsh_signature"]), 16)
                self.assertEqual(card["supported_harnesses"], SUPPORTED_HARNESSES)
                self.assertTrue(card["baltor_native_engine_id"].startswith("baltor_"))

    def test_slot1_natural_language_auto_discovery_queries(self) -> None:
        cases = (
            ("fast terminal directory jump", "ajeetdsouza-zoxide"),
            ("mathematical explainer animation", "3b1b-manim"),
            ("browser console mcp server", "agentdeskai-browser-tools-mcp"),
            ("claude code agent skills", "addyosmani-agent-skills"),
            ("open source zapier workflow automation", "activepieces-activepieces"),
            ("semantic code context vector search", "zilliztech-claude-context"),
        )
        for query, expected_slug in cases:
            res = run_repodir_scanner_and_component_indexer(
                engine_id=ENGINE_REPODIR_LSH_ROUTER,
                search_query=query,
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["auto_discovery_probe"]["top_1_slug"], expected_slug)
            self.assertLess(res["auto_discovery_probe"]["routing_latency_ms"], 1.4)

    def test_slot1_self_repair_and_known_wrong_controls(self) -> None:
        repaired = run_repodir_scanner_and_component_indexer(
            engine_id=ENGINE_REPODIR_CARD_SYNTHESIZER,
            unnormalized_slug_whitespace=True,
            enable_self_repair=True,
        )
        self.assertEqual(repaired["status"], "ok")
        self.assertEqual(repaired["preflight_report"]["verdict"], VERDICT_REPAIRED)

        refused_slug = run_repodir_scanner_and_component_indexer(
            unnormalized_slug_whitespace=True,
            enable_self_repair=False,
        )
        self.assertEqual(refused_slug["status"], "refused")
        self.assertEqual(refused_slug["refusal"]["code"], "repodir_slug_whitespace_drift")

        refused_robots = run_repodir_scanner_and_component_indexer(robots_txt_allow_root=False)
        self.assertEqual(refused_robots["status"], "refused")
        self.assertEqual(refused_robots["refusal"]["code"], "robots_or_unapproved_license_refused")
        self.assertFalse(refused_robots["envelope_trace"]["engine_dispatched"])

        refused_license = run_repodir_scanner_and_component_indexer(force_unapproved_spdx_license="GPL-3.0-only")
        self.assertEqual(refused_license["status"], "refused")
        self.assertEqual(refused_license["refusal"]["code"], "robots_or_unapproved_license_refused")

    def test_slot2_per_tool_video_studio_and_safe_zone_controls(self) -> None:
        parent = root_frame(SLOT_REPODIR_SCANNER_INDEXER)
        for engine_id in VIDEO_STUDIO_ENGINE_IDS:
            res = run_repodir_per_tool_video_studio(
                tool_slug="3b1b-manim",
                engine_id=engine_id,
                parent_frame=parent,
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["slot_id"], SLOT_REPODIR_VIDEO_STUDIO)
            self.assertEqual(res["envelope_frame_depth"], 1)
            self.assertEqual(len(res["three_act_timeline"]), 3)
            self.assertEqual(res["render_profiles"]["vertical_9_16"]["width_px"], 1080)
            self.assertEqual(res["render_profiles"]["vertical_9_16"]["height_px"], 1920)
            self.assertEqual(res["render_profiles"]["landscape_16_9"]["width_px"], 1920)
            self.assertEqual(res["render_profiles"]["landscape_16_9"]["height_px"], 1080)
            self.assertEqual(res["broadcast_compliance"]["ebu_r128_integrated_lufs"], -14.0)
            self.assertLessEqual(res["broadcast_compliance"]["harding_pse_max_flash_hz"], 3.0)

        bad_safe_zone = run_repodir_per_tool_video_studio(
            safe_zone_margins_px={"top_px": 80, "bottom_px": 200, "right_px": 100, "left_px": 40},
        )
        self.assertEqual(bad_safe_zone["status"], "refused")
        self.assertEqual(bad_safe_zone["refusal"]["code"], "tiktok_reels_safe_zone_violation_refused")
        self.assertFalse(bad_safe_zone["envelope_trace"]["engine_dispatched"])

        bad_slop = run_repodir_per_tool_video_studio(
            custom_copy_override="Let us delve into this game-changer tool.",
        )
        self.assertEqual(bad_slop["status"], "refused")
        self.assertEqual(bad_slop["refusal"]["code"], "ai_slop_or_reviewed_qualifier_refused")

        bad_reviewed = run_repodir_per_tool_video_studio(
            custom_copy_override="Baltor indexes 3,452 reviewed repos.",
        )
        self.assertEqual(bad_reviewed["status"], "refused")
        self.assertEqual(bad_reviewed["refusal"]["code"], "ai_slop_or_reviewed_qualifier_refused")

    def test_slot3_auto_discovery_ad_campaign_and_zero_adspend_controls(self) -> None:
        for engine_id in AD_CAMPAIGN_ENGINE_IDS:
            res = run_repodir_auto_discovery_ad_campaign(
                tool_slug="ajeetdsouza-zoxide",
                engine_id=engine_id,
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["slot_id"], SLOT_REPODIR_AD_CAMPAIGN)
            self.assertEqual(res["engineering_adspend_usd"], 0.0)
            self.assertEqual(res["privacy_safe_measurement"]["third_party_tracking_cookies"], 0)
            self.assertTrue(res["privacy_safe_measurement"]["aggregate_link_counter_only"])
            self.assertEqual(len(res["platform_ad_packs"]), 4)

        bad_adspend = run_repodir_auto_discovery_ad_campaign(
            engine_id=ENGINE_FOUNDER_AD_PACK_COUNTER,
            engineering_adspend_usd=25.0,
        )
        self.assertEqual(bad_adspend["status"], "refused")
        self.assertEqual(bad_adspend["refusal"]["code"], "engineering_adspend_refused")
        self.assertFalse(bad_adspend["envelope_trace"]["engine_dispatched"])

        bad_disclosure = run_repodir_auto_discovery_ad_campaign(
            engine_id=ENGINE_PER_TOOL_LANDING_PAGE,
            include_paid_link_disclosure=False,
        )
        self.assertEqual(bad_disclosure["status"], "refused")
        self.assertEqual(bad_disclosure["refusal"]["code"], "missing_paid_link_disclosure_refused")

        bad_engine = run_repodir_auto_discovery_ad_campaign(engine_id="nonexistent_engine")
        self.assertEqual(bad_engine["status"], "refused")
        self.assertEqual(bad_engine["refusal"]["code"], "engine_handshake_incompatible")

    def test_full_3480_url_funnel_benchmark(self) -> None:
        bench = run_repodir_3480_url_funnel_benchmark()
        self.assertEqual(bench["sitemap_total_urls"], 3480)
        self.assertEqual(bench["curated_github_repos"], 3452)
        self.assertEqual(bench["curated_ai_tools"], 7)
        self.assertEqual(bench["total_tools_indexed"], 3459)
        baltor_metrics = bench["comparison"]["baltor_repodir_auto_discovery_and_video_funnel"]
        self.assertEqual(baltor_metrics["engineering_adspend_usd"], 0.0)
        self.assertGreater(baltor_metrics["prompt_token_reduction_pct"], 95.0)
        self.assertEqual(baltor_metrics["render_ready_9_16_and_16_9_tool_videos"], 3459)
        self.assertEqual(bench["live_probe_summary"]["matched_slug"], "3b1b-manim")


if __name__ == "__main__":
    unittest.main()
