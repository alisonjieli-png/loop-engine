"""Tests and known-wrong controls for the Expanded Humanization Skill Pack (12 Voice &
Editorial Engines), Design Skill Pack (12 Visual/Motion/3D/UI Engines), and
Audience-Parametric Visual/Video Tuner Suite.
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

import advanced_humanizer_and_design_skill_pack_engines as suite  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS  # noqa: E402


class AdvancedHumanizerAndDesignSkillPackTests(unittest.TestCase):
    """Verify all 3 slot families, 24 skill bundles, 6 audience cohorts, and 4 known-wrong controls."""

    def test_slot1_twelve_humanization_skills_and_four_swappable_engines(self) -> None:
        self.assertEqual(len(suite.HUMANIZER_12_SKILLS), 12)
        self.assertGreaterEqual(len(suite.SIXTY_PLUS_LLM_CLICHES), 60)
        for skill in suite.HUMANIZER_12_SKILLS:
            self.assertEqual(skill.slot_id, suite.SLOT_HUMANIZER_PACK)
            self.assertTrue(skill.agents_md_snippet.strip())
            self.assertTrue(skill.rules_md_snippet.strip())
            self.assertTrue(skill.memory_md_snippet.strip())
            self.assertTrue(skill.verifier_id.startswith("verify_"))

        slot = suite.AdvancedHumanizerSkillPackSlot()
        raw_slop = (
            "What Baltor is not: a toy wrapper. It's not just a catalog, it's a seamless game-changer — "
            "moreover, Loop Engine serves 5,000 reviewed components and baltor_reviewed Loop nodes to delve into the tapestry."
        )
        for idx, register in enumerate(suite.VOICE_REGISTERS):
            res = slot.humanize(
                raw_slop,
                surface="marketing_homepage",
                voice_register=register,
                request_id=f"test_hum_reg_{idx}",
            )
            self.assertTrue(res.accepted)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")
            out = res.output
            self.assertFalse(out["reviewed_qualifier_present"])
            self.assertFalse(out["defensive_not_clause_present"])
            self.assertEqual(out["em_dash_count"], 0)
            self.assertGreaterEqual(int(out["cliches_removed"]), 4)
            self.assertGreaterEqual(float(out["sigma_words_after"]), 5.5)
            self.assertNotIn("Loop Engine", out["cleaned_text"])
            self.assertNotIn("reviewed components", out["cleaned_text"].lower())
            self.assertNotIn("baltor_reviewed", out["cleaned_text"].lower())

        # Verify engine swapping across all 4 engines
        for eng in (
            suite.ENGINE_PLAIN_ENGLISH_NO_REVIEWED,
            suite.ENGINE_BURSTINESS_CLICHE_SURGEON,
            suite.ENGINE_CHANNEL_VOICE_ADAPTER,
            suite.ENGINE_LEXICAL_SCRUBBER_FALLBACK,
        ):
            swapped = slot.humanize(raw_slop, preferred_engine=eng, request_id=f"test_swap_{eng}")
            self.assertTrue(swapped.accepted)
            self.assertEqual(swapped.selected_engine, eng)

    def test_slot2_twelve_design_skills_and_wcag_aaa_safe_zone_verification(self) -> None:
        self.assertEqual(len(suite.DESIGN_12_SKILLS), 12)
        for skill in suite.DESIGN_12_SKILLS:
            self.assertEqual(skill.slot_id, suite.SLOT_DESIGN_PACK)
            self.assertTrue(skill.agents_md_snippet.strip())
            self.assertTrue(skill.rules_md_snippet.strip())
            self.assertTrue(skill.memory_md_snippet.strip())
            self.assertTrue(skill.verifier_id.startswith("verify_"))

        slot = suite.AdvancedDesignSkillPackSlot()
        res = slot.direct_design(
            brand_domain="baltor.ai",
            cookie_prefix="__Host-baltor",
            fg_hex="#141824",
            bg_hex="#FAF6F0",
            accent_hex="#D95D24",
            modular_scale_ratio=1.25,
            viewport_320px_overflow_px=0,
            safe_zone_x=(90, 950),
            safe_zone_y=(220, 1480),
            pse_flash_hz=1.5,
            audio_lufs=-14.0,
            audio_true_peak_dbtp=-1.2,
            request_id="test_design_aaa_01",
        )
        self.assertTrue(res.accepted)
        self.assertGreaterEqual(float(res.output["wcag_contrast_ratio"]), 15.0)
        self.assertTrue(res.output["wcag_aaa_passed"])
        self.assertEqual(res.output["viewport_320px_overflow_px"], 0)
        self.assertTrue(res.output["vertical_9x16_safe_zone_verified"])
        self.assertTrue(res.output["three_d_skybox_and_three_point_lighting_ready"])
        self.assertEqual(res.output["design_skills_verified_count"], 12)

    def test_slot3_audience_parametric_tuner_across_six_cohorts(self) -> None:
        tuner = suite.AudienceParametricContentTunerSlot()
        base_copy = (
            "What Baltor is not: a toy. It's not just a search index, it's a seamless game-changer — "
            "Loop Engine gives your workflow 2,400 reviewed components to delve into."
        )
        distinct_styles = set()
        distinct_registers = set()
        for idx, cohort in enumerate(suite.SIX_CANONICAL_AUDIENCE_COHORTS):
            res = tuner.tune_for_audience(cohort, base_copy, request_id=f"test_cohort_{idx}")
            self.assertTrue(res.accepted)
            out = res.output
            distinct_styles.add(out["visual_material_style"])
            distinct_registers.add(out["voice_register"])
            self.assertGreaterEqual(float(out["wcag_contrast_ratio"]), 7.0)
            self.assertEqual(out["viewport_320px_overflow_px"], 0)
            self.assertGreaterEqual(float(out["tuned_copy_sigma_words"]), 5.5)
            self.assertFalse(out["reviewed_qualifier_present"])

        self.assertEqual(len(distinct_styles), 6)
        self.assertGreaterEqual(len(distinct_registers), 4)

    def test_four_known_wrong_controls_blocked_at_layer3_and_layer6(self) -> None:
        humanizer = suite.AdvancedHumanizerSkillPackSlot()
        design = suite.AdvancedDesignSkillPackSlot()

        # Control A: public copy using 'reviewed components' or 'What Baltor is not' / antithetical AI slop
        ctrl_a = humanizer.humanize(
            "Browse 1,500 reviewed components. What Baltor is not: a slow chatbot.",
            strict_public_copy_guard=True,
            request_id="test_ctrl_a",
        )
        self.assertFalse(ctrl_a.accepted)
        self.assertEqual(ctrl_a.layer_verdicts["preflight"], "refused")
        self.assertEqual(ctrl_a.refusal.code, "reviewed_component_qualifier_or_antithetical_slop_rejected")

        # Control B: flat robotic sentence cadence (sigma_L < 2.0 words)
        ctrl_b = humanizer.humanize(
            "The worker reads the file now. The module runs the task now. The system writes the log now.",
            require_human_burstiness=True,
            request_id="test_ctrl_b",
        )
        self.assertFalse(ctrl_b.accepted)
        self.assertEqual(ctrl_b.layer_verdicts["preflight"], "refused")
        self.assertEqual(ctrl_b.refusal.code, "flat_robotic_sentence_cadence_rejected")

        # Control C: low WCAG contrast (< 4.5:1) or 320px horizontal overflow
        ctrl_c = design.direct_design(
            fg_hex="#999999",
            bg_hex="#FAF6F0",
            viewport_320px_overflow_px=18,
            request_id="test_ctrl_c",
        )
        self.assertFalse(ctrl_c.accepted)
        self.assertEqual(ctrl_c.layer_verdicts["preflight"], "refused")
        self.assertEqual(ctrl_c.refusal.code, "low_wcag_contrast_or_320px_overflow_rejected")

        # Control D: cross-brand cookie/palette leakage across isolated domains
        ctrl_d = design.direct_design(
            brand_domain="agentbriefs.si",
            cookie_prefix="__Host-baltor",
            request_id="test_ctrl_d",
        )
        self.assertFalse(ctrl_d.accepted)
        self.assertEqual(ctrl_d.layer_verdicts["handshake"], "refused")
        self.assertEqual(ctrl_d.refusal.code, "cross_brand_palette_or_cookie_leak_rejected")

    def test_benchmark_runner_completes_cleanly(self) -> None:
        report = suite.run_all_benchmarks()
        self.assertEqual(report["humanizer_skills_count"], 12)
        self.assertEqual(report["design_skills_count"], 12)
        self.assertEqual(len(report["audience_cohorts_tuned"]), 6)
        for ctrl_ok in report["known_wrong_controls"].values():
            self.assertTrue(ctrl_ok)


if __name__ == "__main__":
    unittest.main()
