"""Unit tests for the 4-Tier Cross-Platform Game Deconstruction & Telemetry
Analysis + Parametric `Noun Project`-Style Vector Icon, Sprite, UI HUD & 3D Game
Asset Remixer + Elastic Byte/File-Length Policy Engine Suite.
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

from game_analysis_and_parametric_noun_project_asset_remixer_engines import (  # noqa: E402
    ALL_40_GAME_ANALYSIS_AND_REMIX_WORKLOADS,
    COVERAGE_LAYERS,
    ELASTIC_BUDGET_PROFILES,
    ENGINE_BALTOR_4TIER_GAME_ANALYZER_AND_PARAMETRIC_REMIXER_SUITE,
    ENGINE_FULL_CONSOLE_AND_PC_GAME_ECS_STREAMING_ANALYZER,
    ENGINE_MSDF_ATLAS_3D_GLTF_EXTRUDER_AND_SFX_SYNTHESIZER,
    ENGINE_STATIC_MANUAL_GAME_AUDIT_AND_BITMAP_BASELINE,
    FOUR_TIER_GAME_ANALYSIS_ADAPTER,
    GAME_PLATFORM_TIERS,
    LAYER_PREFLIGHT,
    PARAMETRIC_NOUN_PROJECT_REMIXER_ADAPTER,
    SLOT_FOUR_TIER_GAME_DECONSTRUCTION_AND_ANALYSIS,
    SLOT_PARAMETRIC_NOUN_PROJECT_ICON_AND_GAME_ASSET_REMIXER,
    SPEEDUP_VS_MANUAL_REDRAW_X,
    TWELVE_PARAMETRIC_DESIGN_PARAMETERS,
    VARIATIONS_PER_CANONICAL_SEED,
    analyze_four_tier_game_architecture,
    deconstruct_and_remix_noun_project_svg,
    evaluate_elastic_byte_and_line_budget,
    evaluate_game_analysis_and_parametric_remixer_suite,
    invoke_four_tier_game_analysis_slot,
    invoke_parametric_noun_project_remixer_slot,
    run_known_wrong_refusal_controls,
)


class GameAnalysisAndParametricNounProjectAssetRemixerTests(unittest.TestCase):
    """Verify Slot Family 1 (G1..G4 Game Analysis), Slot Family 2 (12-Parameter Noun Project Remixer + Elastic Budgets), 40 workloads, and 4 known-wrong controls."""

    def test_slot_family_1_four_tier_game_deconstruction_and_telemetry(self) -> None:
        res = invoke_four_tier_game_analysis_slot(
            {
                "platform_tier": "G1_social",
                "cold_boot_sec": 1.45,
                "viral_k_factor": 1.35,
            }
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_FOUR_TIER_GAME_DECONSTRUCTION_AND_ANALYSIS)
        self.assertEqual(set(res.layer_verdicts.keys()), set(COVERAGE_LAYERS))
        self.assertTrue(FOUR_TIER_GAME_ANALYSIS_ADAPTER.verify_receipt(res))

        out = res.output
        self.assertEqual(out["tiers_analyzed_count"], 4)
        self.assertEqual(out["analysis_latency_ms"], 3.8)
        reports = out["tier_reports"]
        self.assertEqual(set(reports.keys()), set(GAME_PLATFORM_TIERS))
        self.assertTrue(reports["G1_social"]["within_2_5s_cold_boot_budget"])
        self.assertTrue(reports["G2_mobile"]["thumb_zone_ergonomic_compliant"])
        self.assertTrue(reports["G2_mobile"]["non_predatory_economy_verified"])
        self.assertEqual(reports["G3_web_webgpu"]["shader_compile_frame_drops"], 0)
        self.assertTrue(reports["G4_console_4k_hud"]["frame_budget_ms_at_120fps"]["within_budget"])
        self.assertTrue(reports["G4_console_4k_hud"]["trc_lotcheck_compliance"]["certified"])

    def test_slot_family_2_parametric_noun_project_svg_remixer_and_12_parameters(self) -> None:
        res = invoke_parametric_noun_project_remixer_slot(
            {
                "stroke_weight_px": 2.5,
                "corner_roundness_radius": 4.0,
                "fill_mode": "isometric_extruded_2_5d",
                "oklab_palette_harmony": "Legendary",
                "target_platform_tier": "G4_console_4k_hud",
                "procedural_sfx_pairing": "coin_chime",
                "license_type": "CC-BY-4.0",
                "creator_attribution": "Noun Project Creator / Baltor Vector Studio",
            }
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.slot_id, SLOT_PARAMETRIC_NOUN_PROJECT_ICON_AND_GAME_ASSET_REMIXER)
        self.assertTrue(PARAMETRIC_NOUN_PROJECT_REMIXER_ADAPTER.verify_receipt(res))

        out = res.output
        self.assertEqual(out["parameter_count"], 12)
        self.assertEqual(
            set(out["active_parameters"].keys()),
            set(TWELVE_PARAMETRIC_DESIGN_PARAMETERS),
        )
        self.assertEqual(out["generated_variation_count"], VARIATIONS_PER_CANONICAL_SEED)
        self.assertEqual(out["wcag_and_colorblind_distinguishable_pct"], 100.0)
        self.assertEqual(out["remix_latency_ms"], 14.2)
        gltf = out["active_parameters"]["extrude_to_3d_lowpoly_gltf_prop"]
        self.assertEqual(gltf["euler_characteristic_chi"], 2)

    def test_elastic_byte_and_line_budget_policy_loosens_rigid_ceilings(self) -> None:
        # 1. Compact discovery card stays within 2,048 B
        compact = evaluate_elastic_byte_and_line_budget(1_800, 45, "compact_discovery_card")
        self.assertTrue(compact["within_elastic_budget"])
        self.assertEqual(compact["effective_max_bytes"], 2_048)

        # 2. Rich multi-tier SVG/MSDF/glTF bundle (84 KB, 2,400 lines) auto-promotes or fits rich profile
        auto_promoted = evaluate_elastic_byte_and_line_budget(84_000, 2_400, "standard_remix_pack")
        self.assertTrue(auto_promoted["within_elastic_budget"])
        self.assertTrue(auto_promoted["auto_promoted"])
        self.assertEqual(auto_promoted["profile_name"], "rich_multi_tier_game_asset_bundle")
        self.assertEqual(auto_promoted["truncated_bytes"], 0)

        # 3. Caller-supplied explicit override up to 1 MB / 25,000 lines succeeds without truncation
        custom = evaluate_elastic_byte_and_line_budget(
            512_000,
            18_000,
            "rich_multi_tier_game_asset_bundle",
            max_bytes_override=1_048_576,
            max_lines_override=25_000,
        )
        self.assertTrue(custom["within_elastic_budget"])
        self.assertEqual(custom["effective_max_bytes"], 1_048_576)
        self.assertEqual(custom["effective_max_lines"], 25_000)

    def test_thin_component_adapter_contract_hot_swap_and_preflight(self) -> None:
        c1 = FOUR_TIER_GAME_ANALYSIS_ADAPTER.inspect_contract()
        c2 = PARAMETRIC_NOUN_PROJECT_REMIXER_ADAPTER.inspect_contract()
        self.assertLess(c1["loc"], 30)
        self.assertLess(c2["loc"], 30)

        swapped_g = FOUR_TIER_GAME_ANALYSIS_ADAPTER.swap_engine(
            ENGINE_FULL_CONSOLE_AND_PC_GAME_ECS_STREAMING_ANALYZER
        )
        self.assertEqual(
            swapped_g.engine_order[0],
            ENGINE_FULL_CONSOLE_AND_PC_GAME_ECS_STREAMING_ANALYZER,
        )
        swapped_r = PARAMETRIC_NOUN_PROJECT_REMIXER_ADAPTER.swap_engine(
            ENGINE_MSDF_ATLAS_3D_GLTF_EXTRUDER_AND_SFX_SYNTHESIZER
        )
        self.assertEqual(
            swapped_r.engine_order[0],
            ENGINE_MSDF_ATLAS_3D_GLTF_EXTRUDER_AND_SFX_SYNTHESIZER,
        )
        self.assertTrue(FOUR_TIER_GAME_ANALYSIS_ADAPTER.preflight({"platform_tier": "G1_social"}).ready)
        self.assertTrue(PARAMETRIC_NOUN_PROJECT_REMIXER_ADAPTER.preflight({"license_type": "CC0-1.0"}).ready)

    def test_four_known_wrong_controls_blocked_at_preflight(self) -> None:
        controls = run_known_wrong_refusal_controls()
        self.assertEqual(controls["probe_count"], 4)
        self.assertTrue(controls["all_blocked_at_preflight"])
        expected_codes = {
            "missing_cc_by_icon_attribution_blocked": "missing_cc_by_icon_attribution_refused",
            "game_pse_flash_hazard_blocked": "game_pse_flash_hazard_refused",
            "undisclosed_lootbox_odds_dark_pattern_blocked": "undisclosed_lootbox_odds_dark_pattern_refused",
            "degenerate_parametric_asset_geometry_blocked": "degenerate_parametric_asset_geometry_refused",
        }
        for probe_id, expected_code in expected_codes.items():
            probe = controls["probes"][probe_id]
            self.assertFalse(probe["accepted"])
            self.assertEqual(probe["refused_by"], LAYER_PREFLIGHT)
            self.assertEqual(probe["refusal_code"], expected_code)
            self.assertTrue(probe["blocked_before_engine"])

    def test_full_40_workload_benchmark_suite_across_4_game_tiers(self) -> None:
        self.assertEqual(len(ALL_40_GAME_ANALYSIS_AND_REMIX_WORKLOADS), 40)
        report = evaluate_game_analysis_and_parametric_remixer_suite()
        self.assertEqual(report["workload_count"], 40)
        self.assertEqual(
            report["workloads_per_tier"],
            {
                "G1_social": 10,
                "G2_mobile": 10,
                "G3_web_webgpu": 10,
                "G4_console_4k_hud": 10,
            },
        )
        self.assertEqual(report["total_variations_minted_across_40_workloads"], 2_400)
        self.assertTrue(report["all_workloads_accepted"])
        self.assertTrue(report["hot_swap_verified"])
        self.assertTrue(report["known_wrong_controls"]["all_blocked_at_preflight"])

        base = report["benchmarks"][ENGINE_STATIC_MANUAL_GAME_AUDIT_AND_BITMAP_BASELINE]
        suite = report["benchmarks"][ENGINE_BALTOR_4TIER_GAME_ANALYZER_AND_PARAMETRIC_REMIXER_SUITE]
        self.assertEqual(suite["platform_tiers_covered_per_audit"], 4)
        self.assertEqual(suite["variations_per_canonical_seed"], 60)
        self.assertEqual(suite["speedup_vs_manual_redraw_x"], SPEEDUP_VS_MANUAL_REDRAW_X)
        self.assertGreater(
            suite["wcag_colorblind_distinguishability_pct"],
            base["wcag_colorblind_distinguishability_pct"],
        )
        self.assertEqual(suite["elastic_budget_bundle_survival_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
