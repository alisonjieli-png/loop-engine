"""Tests for Reel Reverse-Engineering Composer DAG, 2.5D Video Composer, 2D Game Physics Harvester & Multi-Genre Video Factory."""
from __future__ import annotations

import unittest

from tools.reel_reverse_engineer_2d_games_and_multi_genre_video_factory_engines import (
    HARVESTED_2D_GAME_AND_ML_REPOS,
    REEL_AND_VIDEO_FACTORY_ENVELOPE,
    REUSABLE_12_STEP_VIDEO_DAG,
    compute_fourier_epicycle_ladder,
    execute_reel_reverse_engineer_and_video_factory_suite,
)


class ReelReverseEngineerAndVideoFactoryTests(unittest.TestCase):
    def test_envelope_and_12_step_dag(self) -> None:
        self.assertEqual(
            REEL_AND_VIDEO_FACTORY_ENVELOPE.component,
            "reel_frame_by_frame_reverse_engineer_and_dag_slot",
        )
        self.assertEqual(len(REUSABLE_12_STEP_VIDEO_DAG), 12)
        self.assertEqual(len(HARVESTED_2D_GAME_AND_ML_REPOS), 5)

    def test_fourier_epicycle_ladder_error_decreases_monotonically(self) -> None:
        ladder = compute_fourier_epicycle_ladder()
        self.assertEqual(len(ladder), 7)
        errors = [item.relative_l2_error_pct for item in ladder]
        self.assertEqual(errors, sorted(errors, reverse=True))
        self.assertLess(ladder[-1].relative_l2_error_pct, 0.5)

    def test_full_suite_execution_covers_all_requested_series(self) -> None:
        res = execute_reel_reverse_engineer_and_video_factory_suite({"run_all": True})
        self.assertEqual(res.status, "ok")
        val = res.value
        self.assertEqual(val["curated_reels_reverse_engineered"], 75)
        self.assertEqual(
            val["consistent_2d_to_video_composer"]["supported_aspect_ratios"],
            ("9:16", "16:9", "1:1", "4:5"),
        )
        self.assertIn(
            "goodwill_ai_intake_scanner_and_standing_order_router",
            val["animated_startup_pitches_and_top5_feed_cta"]["flagship_startup_pitch"]["pitch_id"],
        )
        self.assertIn(
            "agentfeeds.si",
            val["animated_startup_pitches_and_top5_feed_cta"]["daily_top5_aiml_series_cta"],
        )

    def test_known_wrong_refusals(self) -> None:
        for flag, expected_code in (
            ("cyclic_composer_dag", "cyclic_video_composer_dag_refused"),
            ("camera_frustum_out_of_bounds", "camera_frustum_out_of_canvas_bounds_refused"),
            ("high_velocity_without_swept_aabb", "high_velocity_collision_tunneling_risk_refused"),
            ("unverified_historical_or_politician_quote", "unverified_or_fabricated_quote_attribution_refused"),
            ("top5_episode_missing_agent_feed", "top5_episode_missing_live_agent_feed_card_refused"),
        ):
            ref = execute_reel_reverse_engineer_and_video_factory_suite({flag: True})
            self.assertEqual(ref.status, "refused")
            self.assertEqual(ref.refusal.code, expected_code)


if __name__ == "__main__":
    unittest.main()
