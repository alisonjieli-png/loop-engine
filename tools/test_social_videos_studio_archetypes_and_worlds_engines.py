"""Tests for tools/social_videos_studio_archetypes_and_worlds_engines.py.

Verifies:
1. Slot Family 1 (`brand_editorial_and_four_styles_card_slot`):
   - Canonical AgentFeeds / Baltor Warm Editorial Design Contract palette tokens
     (`#FAF6F0`, `#141824`, `#D95D24`, `#E6DFD3`, `#0F1420`, `#2ECC71`) and
     five verified editorial hooks.
   - All four LuxePrompting Four Styles System Cards (`SYSTEMS_01_slow_request_queue_lane`,
     `NETWORKS_02_percolation_cascade`, `TINY_ROBOT_STORIES_03_last_package_sunrise`,
     `ALGORITHM_THEATER_04_four_sorts_race`) with WCAG AAA contrast >= 7.0:1 and
     TikTok/Reels keep-out compliance.
2. Slot Family 2 (`lanternfall_worlds_and_math_physics_chaos_slot`):
   - All three Lanternfall 3D Low-Poly Worlds (`LANTERNFALL_01_SKYBOUND`,
     `LANTERNFALL_02_MOONWATER`, `LANTERNFALL_03_HEXRISE`).
   - All four mathematical and physical chaos visualizations
     (`three_body_choreography`, `quantum_landau_wavefunctions`,
     `hilbert_space_filling_curve`, `kuramoto_coupled_metronomes`).
3. Slot Family 3 (`repeatable_studio_archetypes_and_story_bibles_slot`):
   - All nine repeatable studio production archetypes and seven tactile material
     shader styles (`photorealistic_pbr`, `ultra_displacement_texture`,
     `faceted_low_poly`, `stop_motion_clay`, `refractive_borosilicate_glass`,
     `glazed_kiln_ceramic`, `anodized_brushed_metal`).
   - All four multi-part story bibles (`surviving_the_ai_hype_cycle`,
     `bex_and_mara_zombie_universe`, `the_deploy`, `signal_rule_1`) with
     cross-episode continuity handshakes.
4. Multi-engine fallback chains in the 7-layer `ComponentEnvelope`, `Without Baltor`
   vs `With Baltor` benchmark comparison, and all five known-wrong controls.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import social_videos_studio_archetypes_and_worlds_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    ENVELOPE_LAYERS,
    EnvelopeRefusal,
    EnvelopeTrace,
)


class SocialVideosStudioArchetypesAndWorldsTests(unittest.TestCase):
    def test_slot_1_warm_editorial_contract_and_luxe_four_styles_cards(self) -> None:
        res = suite.execute_studio_slot(suite.SLOT_BRAND_EDITORIAL_AND_FOUR_STYLES)
        self.assertEqual(res.status, "answered")
        self.assertEqual(res.selected_engine_id, "editorial_contract_and_luxe_card_engine")
        self.assertIsInstance(res.trace, EnvelopeTrace)
        self.assertEqual(res.trace.to_dict()["record_type"], "envelope_trace/v1")

        palette = res.payload["palette_tokens"]
        self.assertEqual(palette["warm_editorial_cream"], "#FAF6F0")
        self.assertEqual(palette["charcoal_navy_ink"], "#141824")
        self.assertEqual(palette["burnt_orange_accent"], "#D95D24")
        self.assertEqual(palette["soft_sand_border"], "#E6DFD3")
        self.assertEqual(palette["dark_navy_ops_card"], "#0F1420")
        self.assertEqual(palette["emerald_live_status_light"], "#2ECC71")

        self.assertEqual(len(res.payload["editorial_hooks"]), 5)
        self.assertIn("Don't be a meat proxy", res.payload["editorial_hooks"])
        self.assertIn("Leave a task. Keep the limits", res.payload["editorial_hooks"])

        cards = res.payload["luxe_cards"]
        self.assertEqual(len(cards), 4)
        card_ids = [c["card_id"] for c in cards]
        self.assertEqual(
            card_ids,
            [
                "SYSTEMS_01_slow_request_queue_lane",
                "NETWORKS_02_percolation_cascade",
                "TINY_ROBOT_STORIES_03_last_package_sunrise",
                "ALGORITHM_THEATER_04_four_sorts_race",
            ],
        )
        self.assertTrue(res.payload["all_cards_wcag_aaa"])
        self.assertTrue(res.payload["all_cards_keep_out_compliant"])

    def test_slot_2_lanternfall_worlds_and_math_physics_chaos_invariants(self) -> None:
        res = suite.execute_studio_slot(suite.SLOT_LANTERNFALL_AND_CHAOS)
        self.assertEqual(res.status, "answered")
        self.assertTrue(res.payload["all_invariants_passed"])

        worlds = res.payload["lanternfall_worlds"]
        self.assertEqual(len(worlds), 3)
        self.assertEqual(
            [w["world_id"] for w in worlds],
            [
                "LANTERNFALL_01_SKYBOUND",
                "LANTERNFALL_02_MOONWATER",
                "LANTERNFALL_03_HEXRISE",
            ],
        )
        self.assertTrue(all(w["keep_out_Clear"] for w in worlds))

        three_body = res.payload["three_body_choreography"]
        self.assertTrue(three_body["energy_conserved"])
        self.assertLessEqual(three_body["relative_energy_drift"], 1e-4)

        quantum = res.payload["quantum_landau_wavefunctions"]
        self.assertTrue(quantum["normalization_valid"])
        self.assertAlmostEqual(quantum["normalization_sum"], 1.0, places=6)
        self.assertEqual(quantum["phase_quadrants_covered"], 4)

        hilbert = res.payload["hilbert_space_filling_curve"]
        self.assertTrue(hilbert["locality_valid"])
        self.assertEqual(hilbert["max_manhattan_step"], 1)
        self.assertEqual(hilbert["min_manhattan_step"], 1)

        kuramoto = res.payload["kuramoto_coupled_metronomes"]
        self.assertTrue(kuramoto["synchronized"])
        self.assertGreaterEqual(kuramoto["order_parameter_r"], 0.85)

    def test_slot_3_nine_studio_archetypes_material_styles_and_four_story_bibles(self) -> None:
        res = suite.execute_studio_slot(
            suite.SLOT_STUDIO_ARCHETYPES_AND_BIBLES,
            {"revised_material_style": "refractive_borosilicate_glass"},
        )
        self.assertEqual(res.status, "answered")
        self.assertTrue(res.payload["revision_survived"])
        self.assertEqual(len(res.payload["archetypes"]), 9)
        self.assertEqual(len(res.payload["story_bibles"]), 4)
        self.assertEqual(len(res.payload["material_shader_styles_supported"]), 7)
        for bible in res.payload["story_bibles"]:
            self.assertTrue(bible["continuity_verified"])
            self.assertEqual(len(bible["continuity_handshake_digest"]), 16)

    def test_multi_engine_fallback_across_all_three_slots(self) -> None:
        for slot_id, engines in suite.SLOT_ENGINE_ORDERS.items():
            res = suite.execute_studio_slot(
                slot_id,
                {"simulate_recoverable_deferrals": (engines[0], engines[1])},
            )
            self.assertEqual(res.status, "answered")
            self.assertEqual(res.selected_engine_id, engines[2])
            self.assertEqual(res.attempted_engines, engines)

    def test_all_five_known_wrong_controls_refuse_in_preflight(self) -> None:
        controls = suite.run_known_wrong_controls()
        self.assertEqual(len(controls), 5)
        for ctrl in controls:
            self.assertTrue(
                ctrl["rejected_before_effect"],
                f"Control {ctrl['control_id']} did not reject: {ctrl}",
            )
            self.assertEqual(ctrl["actual_refusal_code"], ctrl["expected_refusal_code"])

    def test_without_vs_with_baltor_benchmark_improvements(self) -> None:
        bench = suite.run_without_vs_with_baltor_benchmark()
        self.assertEqual(bench["envelope_layers_verified"], ENVELOPE_LAYERS)
        self.assertEqual(bench["coverage_layers_verified"], COVERAGE_LAYERS)
        without = bench["without_baltor"]
        with_b = bench["with_baltor"]
        for metric_key in without:
            self.assertGreater(with_b[metric_key], without[metric_key])
            self.assertEqual(with_b[metric_key], 1.0)


if __name__ == "__main__":
    unittest.main()
