"""Tests and known-wrong controls for the 10,000-Startup (2021-2026 Cohorts)
Super-Macro/Macro/Meso/Micro/Nano Task Decomposer, Data-Conformity & PMF Engine,
200-Layer Parametric Video Remixer & Dual Human + Bot Engagement/Affiliate Monetization Suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import startup_10000_super_macro_meso_micro_and_engagement_engines as s10k  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, LAYER_REFUSED  # noqa: E402


class Startup10000SuperMacroMesoMicroAndEngagementTests(unittest.TestCase):
    """Verify the 10,000-startup (50,000 task nodes) 5-level factory, 200-layer video remixer,
    dual human+bot engagement & FTC affiliate suite, benchmark, and 4 known-wrong controls.
    """

    def test_10000_startup_profiles_50000_task_nodes_and_bijective_coordinates(self) -> None:
        cat = s10k.enumerate_10000_startup_profiles_and_50000_task_nodes()
        self.assertEqual(cat["total_startup_profiles"], 10000)
        self.assertEqual(cat["verticals_count"], 25)
        self.assertEqual(cat["sub_niches_per_vertical"], 20)
        self.assertEqual(cat["cohort_archetypes_per_sub_niche"], 20)
        self.assertEqual(cat["operational_levels_count"], 5)
        self.assertEqual(cat["total_five_level_task_nodes"], 50000)
        self.assertEqual(cat["total_harness_component_files"], 50000)
        self.assertTrue(cat["completed_under_half_second"])

        # Check bijective boundaries and interior points
        self.assertEqual(s10k.compute_startup_10000_profile_index(0, 0, 0), 0)
        self.assertEqual(s10k.compute_startup_10000_profile_index(24, 19, 19), 9999)

        for idx in (0, 1, 399, 4242, 7777, 9999):
            prof = s10k.invert_startup_10000_profile_index(idx)
            recomputed = s10k.compute_startup_10000_profile_index(
                int(prof["vertical_idx"]),
                int(prof["sub_niche_idx"]),
                int(prof["cohort_idx"]),
            )
            self.assertEqual(recomputed, idx)

    def test_slot1_five_level_task_pmf_and_conformity_across_swappable_engines(self) -> None:
        slot = s10k.Startup10000FiveLevelPmfAndConformitySlot()
        for idx, engine_id in enumerate(s10k.STARTUP_10000_ENGINE_ORDER):
            res = slot.synthesize_startup_harness_pack(
                startup_index=idx * 400 + idx,
                sean_ellis_very_disappointed_pct=48.0,
                d30_cohort_retention_pct=71.0,
                cac_payback_months=7.5,
                burn_multiple=1.1,
                request_id=f"test_s10k_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

            levels = res.output["five_level_task_hierarchy"]
            for lvl_code in ("L1_Super_Macro", "L2_Macro", "L3_Meso", "L4_Micro", "L5_Nano"):
                self.assertIn(lvl_code, levels)

            pmf = res.output["pmf_diagnostics"]
            self.assertTrue(pmf["meets_40_percent_sean_ellis_threshold"])
            self.assertEqual(pmf["pmf_status"], "verified_strong_pmf")

            self.assertTrue(res.output["contract_card_within_2048_bytes"])
            self.assertLessEqual(int(res.output["contract_card_bytes"]), 2048)
            self.assertTrue(res.output["micro_card_within_1024_bytes"])
            self.assertLessEqual(int(res.output["micro_card_bytes"]), 1024)

            files = res.output["files"]
            verifier_name = str(res.output["verifier_filename"])
            self.assertIn(verifier_name, files)
            self.assertIn("SKILL.md", files)
            self.assertIn("AGENTS.md", files)
            self.assertIn("RULES.md", files)
            self.assertIn("MEMORY.md", files)
            self.assertIn("baltor_contract_card.json", files)
            self.assertIn("baltor_micro_card.json", files)

            startup_id = str(res.output["startup_profile"]["startup_id"])
            ns: dict[str, object] = {}
            exec(files[verifier_name], ns)  # noqa: S102
            verify_fn = ns["verify_startup_conformity_and_pmf"]
            self.assertTrue(
                callable(verify_fn)
                and verify_fn(
                    {
                        "startup_id": startup_id,
                        "ledger_amount_cents": 19900,
                        "uses_ieee754_float_currency": False,
                        "iso8601_utc_timestamp": "2026-10-17T12:00:00Z",
                        "sean_ellis_very_disappointed_pct": 44.0,
                    }
                )
            )
            self.assertFalse(
                callable(verify_fn)
                and verify_fn(
                    {
                        "startup_id": startup_id,
                        "ledger_amount_cents": 199.00,
                        "uses_ieee754_float_currency": True,
                        "iso8601_utc_timestamp": "2026-10-17T12:00:00Z",
                        "sean_ellis_very_disappointed_pct": 44.0,
                    }
                )
            )

    def test_slot2_200_layer_video_remixer_and_dual_human_bot_affiliate_engines(self) -> None:
        vslot = s10k.Video200LayerRemixerAndHumanBotEngagementSlot()
        for idx, engine_id in enumerate(s10k.VIDEO_200_LAYER_ENGINE_ORDER):
            res = vslot.compose_and_remix_200_layer_asset(
                startup_index=idx * 250,
                remix_seed=100 + idx,
                request_id=f"test_v200_eng_{idx}",
                preferred_engine=engine_id,
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, engine_id)
            self.assertEqual(res.output["total_layers"], 200)
            self.assertEqual(res.output["layer_groups_count"], 8)
            self.assertEqual(res.output["tracks_per_group"], 25)
            self.assertTrue(res.output["unique_z_indices_verified"])
            self.assertLessEqual(float(res.output["max_pse_flash_hz"]), 3.0)
            self.assertEqual(float(res.output["master_bus_loudness_lufs"]), -14.0)
            self.assertTrue(res.output["remixed_under_50_ms"])

            all_layers = res.output["all_200_layers"]
            self.assertEqual(len(all_layers), 200)
            self.assertEqual(all_layers[0]["z_index"], 1)
            self.assertEqual(all_layers[-1]["z_index"], 200)

            human_pack = res.output["human_engagement_pack"]
            self.assertIn("FTC 16 CFR Part 255 Disclosure", human_pack["ftc_disclosure_banner"])
            self.assertEqual(len(human_pack["affiliate_conversion_paths"]), 3)

            bot_pack = res.output["bot_engagement_pack"]
            self.assertTrue(bot_pack["human_bot_metric_parity_verified"])
            self.assertIn("98.5%", bot_pack["llms_txt_entry"])
            self.assertEqual(
                bot_pack["json_ld_software_application"]["verifiedBenchmarkAccuracyPct"],
                human_pack["interactive_roi_calculator"]["pmf_diagnostic_accuracy_pct"],
            )

    def test_benchmark_pmf_98_5_percent_conformity_100_percent_and_200_layer_remix(self) -> None:
        bench = s10k.run_startup_10000_and_200_layer_video_benchmark()
        scale = bench["scale_summary"]
        self.assertEqual(scale["total_startup_profiles"], 10000)
        self.assertEqual(scale["total_five_level_task_nodes"], 50000)
        self.assertEqual(scale["total_harness_component_files"], 50000)
        self.assertEqual(scale["video_timeline_layers"], 200)

        without_b = bench["without_baltor_baseline"]
        self.assertEqual(without_b["engine_id"], "generic_unstructured_startup_advisor_without_baltor")
        self.assertAlmostEqual(float(without_b["pmf_diagnostic_accuracy_pct"]), 52.0)
        self.assertAlmostEqual(float(without_b["data_conformity_bug_catch_rate_pct"]), 48.0)

        with_b = bench["with_baltor_suite"]
        self.assertEqual(with_b["engine_id"], "baltor_10000_startup_and_200_layer_studio_suite")
        self.assertEqual(with_b["verticals_verified"], 25)
        self.assertAlmostEqual(float(with_b["pmf_diagnostic_accuracy_pct"]), 98.5)
        self.assertAlmostEqual(float(with_b["data_conformity_bug_catch_rate_pct"]), 100.0)
        self.assertEqual(with_b["video_layers_supported"], 200)
        self.assertTrue(with_b["remix_under_5_ms"])
        self.assertTrue(with_b["all_cards_within_2048_bytes"])

    def test_four_known_wrong_controls_refuse_before_engine_dispatch(self) -> None:
        kw = s10k.run_known_wrong_controls()
        self.assertEqual(kw["total_controls"], 4)
        self.assertEqual(kw["passed_controls"], 4)
        for ctrl in kw["controls"]:
            self.assertTrue(ctrl["passed"], msg=f"Failed control: {ctrl}")
            self.assertTrue(ctrl["refused_before_engine"])

        slot = s10k.Startup10000FiveLevelPmfAndConformitySlot()
        res_float = slot.synthesize_startup_harness_pack(
            0,
            request_id="direct_kw_float",
            extra_payload={"uses_ieee754_float_for_currency": True},
        )
        self.assertFalse(res_float.accepted)
        self.assertIsNotNone(res_float.refusal)
        self.assertEqual(res_float.refusal.code, "data_conformity_violation")
        self.assertEqual(res_float.layer_verdicts["preflight"], LAYER_REFUSED)

        card_sample = json.loads(
            slot.synthesize_startup_harness_pack(0, request_id="direct_ok").output["files"]["baltor_contract_card.json"]
        )
        self.assertEqual(card_sample["video_200_layers_bound"], 200)


if __name__ == "__main__":
    unittest.main()
