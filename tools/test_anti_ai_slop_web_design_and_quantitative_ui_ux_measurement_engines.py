"""Tests for Anti-AI-Slop Web Design, 1,200-Question Quantitative UI/UX Measurement & Public-Good Skills Engine Suite."""

from __future__ import annotations

from collections.abc import Mapping
import unittest

from tools.anti_ai_slop_web_design_and_quantitative_ui_ux_measurement_engines import (
    ThinComponentAdapter,
    build_public_good_pack_synthesizer_envelope,
    build_ui_ux_measurement_envelope,
    generate_1200_ui_ux_questions,
    run_ui_ux_anti_slop_benchmark,
)


class AntiAISlopWebDesignAndQuantitativeUIUXMeasurementTest(unittest.TestCase):
    def test_1200_diagnostic_questions_and_editorial_profile_metrics(self) -> None:
        questions = generate_1200_ui_ux_questions()
        self.assertEqual(len(questions), 1200)

        adapter = ThinComponentAdapter(build_ui_ux_measurement_envelope())
        res = adapter.execute(
            {
                "surface_url": "tayloramarel.baltor.ai",
                "viewport_width_px": 1280.0,
                "viewport_height_px": 900.0,
                "visible_character_count": 1880,
                "visible_word_count": 295,
                "content_occupied_area_px2": 340000.0,
                "content_container_max_width_px": 680.0,
                "heading_margin_top_px": 48.0,
                "heading_margin_bottom_px": 12.0,
                "single_column_editorial": True,
                "detected_ai_slop_tropes": [],
            }
        )
        self.assertTrue(adapter.verify_receipt(res))
        assert isinstance(res.value, Mapping)
        metrics = res.value["quantitative_metrics"]
        self.assertLessEqual(metrics["tpsi_viewport_chars_per_sq_in"], 40.0)
        self.assertGreaterEqual(metrics["macro_whitespace_ratio"], 0.65)
        self.assertGreaterEqual(metrics["directional_heading_proximity_ratio"], 3.5)
        self.assertEqual(metrics["padding_4pt_8pt_harmonic_consistency"], 1.0)
        self.assertEqual(res.value["diagnostic_question_bank_count"], 1200)
        self.assertGreaterEqual(
            res.value["saliency_heatmap"]["visual_clarity_score_0_100"],
            80.0,
        )

    def test_known_wrong_controls_refuse_ai_slop_and_excessive_tpsi(self) -> None:
        adapter = ThinComponentAdapter(build_ui_ux_measurement_envelope())

        # Control 1: Refuse AI-slop icon-card grids / cartoon SVG boxes
        slop_res = adapter.execute(
            {
                "detected_ai_slop_tropes": [
                    "slop_02_three_column_generic_icon_card_grid",
                    "slop_03_cartoon_svg_placeholder_thumbnails_in_boxes",
                ],
                "reject_ai_slop": True,
            }
        )
        self.assertFalse(slop_res.ok)
        assert slop_res.refusal is not None
        self.assertEqual(slop_res.refusal.code, "ai_slop_design_tropes_refused")

        # Control 2: Refuse excessive Text Per Square Inch (TPSI) crowding
        tpsi_res = adapter.execute(
            {
                "viewport_width_px": 800.0,
                "viewport_height_px": 600.0,
                "visible_character_count": 15000,
                "max_allowed_tpsi": 150.0,
            }
        )
        self.assertFalse(tpsi_res.ok)
        assert tpsi_res.refusal is not None
        self.assertEqual(
            tpsi_res.refusal.code,
            "excessive_text_per_square_inch_density_refused",
        )

        # Control 3: Refuse insufficient macro whitespace ratio
        wsr_res = adapter.execute(
            {
                "viewport_width_px": 1000.0,
                "viewport_height_px": 800.0,
                "content_occupied_area_px2": 720000.0,
                "min_whitespace_ratio": 0.55,
            }
        )
        self.assertFalse(wsr_res.ok)
        assert wsr_res.refusal is not None
        self.assertEqual(
            wsr_res.refusal.code,
            "insufficient_whitespace_ratio_refused",
        )

    def test_public_good_and_editorial_skill_packs_and_benchmark(self) -> None:
        pack_adapter = ThinComponentAdapter(build_public_good_pack_synthesizer_envelope())
        res = pack_adapter.execute({})
        self.assertTrue(pack_adapter.verify_receipt(res))
        assert isinstance(res.value, Mapping)
        self.assertEqual(res.value["synthesized_pack_count"], 6)
        for pack in res.value["packs"]:
            self.assertEqual(len(pack["files"]), 5)
            self.assertEqual(len(pack["sha256"]), 64)

        report = run_ui_ux_anti_slop_benchmark()
        self.assertEqual(report.diagnostic_questions_verified, 1200)
        self.assertGreater(
            report.editorial_restraint_clarity_score,
            report.ai_slop_baseline_clarity_score + 40.0,
        )
        self.assertLess(
            report.editorial_restraint_ttff_ms,
            report.ai_slop_baseline_ttff_ms,
        )


if __name__ == "__main__":
    unittest.main()
