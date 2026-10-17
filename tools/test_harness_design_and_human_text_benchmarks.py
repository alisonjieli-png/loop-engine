"""Unit tests for tools/harness_design_and_human_text_benchmarks.py."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_TOOLS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TOOLS_DIR.parent
for _p in (_TOOLS_DIR, _REPO_ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import harness_design_and_human_text_benchmarks as bench  # noqa: E402


class HarnessDesignAndHumanTextBenchmarksTest(unittest.TestCase):
    """Verify Track 1 (9x4 harnesses/models), Track 2 (6 design gates), Track 3 (6 prose gates), and known-wrong controls."""

    def test_track_1_cross_harness_and_model_capability_36_cells(self) -> None:
        envelopes = bench.build_track_envelopes()
        env = envelopes[bench.SLOT_HARNESS_CAPABILITY]
        res = env.execute({"slot_id": bench.SLOT_HARNESS_CAPABILITY})
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, "progressive_3tool_lsh_preturn_evaluator")
        self.assertEqual(len(res.layers_verified), 7)

        payload = res.payload
        self.assertEqual(payload["harness_count"], 9)
        self.assertEqual(payload["model_tier_count"], 4)
        self.assertEqual(payload["total_cells"], 36)

        harness_names = {c["harness_name"] for c in payload["cells"]}
        self.assertEqual(
            harness_names,
            {
                "Claude Code",
                "Codex CLI",
                "Cursor",
                "Windsurf",
                "Cline",
                "Roo Code",
                "OpenCode",
                "Pi",
                "OpenMuse / Personal Agent",
            },
        )
        model_tiers = {c["model_tier"] for c in payload["cells"]}
        self.assertEqual(
            model_tiers,
            {
                "gemma4:31b",
                "qwen3-coder:30b",
                "glm-5.3",
                "claude-sonnet / gpt-5-codex",
            },
        )

        without_summary = payload["without_baltor_summary"]
        with_summary = payload["with_baltor_summary"]
        self.assertEqual(without_summary["initial_schema_token_cost"], 2617)
        self.assertLess(with_summary["initial_schema_token_cost"], 650)
        self.assertEqual(without_summary["relevant_tool_invocation_recall"], 0.0)
        self.assertEqual(with_summary["relevant_tool_invocation_recall"], 1.0)
        self.assertEqual(with_summary["negative_turn_abstention"], 1.0)
        self.assertGreater(
            with_summary["mean_first_attempt_task_pass_rate"],
            without_summary["mean_first_attempt_task_pass_rate"],
        )

    def test_track_2_design_layout_motion_and_creative_qa_6_benchmarks(self) -> None:
        envelopes = bench.build_track_envelopes()
        env = envelopes[bench.SLOT_DESIGN_AND_VISUAL]
        res = env.execute({"slot_id": bench.SLOT_DESIGN_AND_VISUAL})
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, "wcag_reelkit_and_layout_gate_engine")

        payload = res.payload
        self.assertEqual(payload["benchmark_count"], 6)
        self.assertEqual(payload["without_baltor_pass_count"], 0)
        self.assertEqual(payload["with_baltor_pass_count"], 6)
        self.assertEqual(payload["with_baltor_pass_rate"], 1.0)

        by_id = {b["benchmark_id"]: b for b in payload["benchmarks"]}
        self.assertEqual( tuple(by_id.keys()), bench.DESIGN_BENCHMARK_IDS)

        wcag = by_id["design_wcag_aaa_contrast_and_palette_harmony"]
        self.assertAlmostEqual(wcag["without_baltor_value"], 1.65, places=2)
        self.assertGreaterEqual(wcag["with_baltor_value"], 7.0)

        safe_zone = by_id["design_vertical_1080x1920_safe_zone_compliance"]
        self.assertGreater(safe_zone["without_baltor_value"], 0)
        self.assertEqual(safe_zone["with_baltor_value"], 0)

        grid_320 = by_id["design_responsive_grid_and_narrow_viewport_320px"]
        self.assertGreater(grid_320["without_baltor_value"], 0)
        self.assertEqual(grid_320["with_baltor_value"], 0)

        brand_sep = by_id["design_multi_brand_visual_identity_separation"]
        self.assertEqual(brand_sep["with_baltor_value"], 1.0)

        motion = by_id["design_procedural_motion_60fps_pacing_and_hook"]
        self.assertTrue(motion["with_baltor_passed"])
        self.assertLess(motion["with_baltor_value"]["static_frame_share_pct"], 5.0)
        self.assertEqual(motion["with_baltor_value"]["audio_lufs"], -14.0)

        rev = by_id["design_revision_survival_without_full_regeneration"]
        self.assertEqual(rev["without_baltor_value"], 0.0)
        self.assertEqual(rev["with_baltor_value"], 1.0)

    def test_track_3_human_like_text_and_technical_prose_6_benchmarks(self) -> None:
        envelopes = bench.build_track_envelopes()
        env = envelopes[bench.SLOT_HUMAN_LIKE_TEXT]
        res = env.execute({"slot_id": bench.SLOT_HUMAN_LIKE_TEXT})
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, "humanizer_strict_rule_gate")

        payload = res.payload
        self.assertEqual(payload["benchmark_count"], 6)
        self.assertEqual(payload["without_baltor_pass_count"], 0)
        self.assertEqual(payload["with_baltor_pass_count"], 6)
        self.assertEqual(payload["with_baltor_pass_rate"], 1.0)

        by_id = {b["benchmark_id"]: b for b in payload["benchmarks"]}
        self.assertEqual(tuple(by_id.keys()), bench.TEXT_BENCHMARK_IDS)
        self.assertEqual(by_id["text_zero_ai_slop_lexicon_score"]["without_baltor_value"], 7)
        self.assertEqual(by_id["text_zero_ai_slop_lexicon_score"]["with_baltor_value"], 0)
        self.assertEqual(by_id["text_sentence_length_burstiness_and_cadence"]["without_baltor_value"], 0.0)
        self.assertGreaterEqual(by_id["text_sentence_length_burstiness_and_cadence"]["with_baltor_value"], 4.0)
        self.assertEqual(by_id["text_positive_boundary_framing_compliance"]["with_baltor_value"], 0)
        self.assertEqual(by_id["text_plain_customer_vocabulary_score"]["with_baltor_value"], 0)
        self.assertEqual(by_id["text_empirical_denominator_and_receipt_grounding"]["with_baltor_value"], 3)
        self.assertTrue(by_id["text_reading_ease_and_scannability"]["with_baltor_passed"])

    def test_envelope_automatic_fallback_cascade_across_all_three_tracks(self) -> None:
        envelopes = bench.build_track_envelopes()
        r1 = envelopes[bench.SLOT_HARNESS_CAPABILITY].execute(
            {"slot_id": bench.SLOT_HARNESS_CAPABILITY}, simulate_recoveries=2
        )
        self.assertTrue(r1.succeeded)
        self.assertEqual(r1.selected_engine, "deterministic_harness_matrix_fallback_evaluator")
        self.assertEqual(len(r1.attempted_engines), 3)

        r2 = envelopes[bench.SLOT_DESIGN_AND_VISUAL].execute(
            {"slot_id": bench.SLOT_DESIGN_AND_VISUAL}, simulate_recoveries=2
        )
        self.assertTrue(r2.succeeded)
        self.assertEqual(r2.selected_engine, "deterministic_design_contract_fallback")
        self.assertEqual(len(r2.attempted_engines), 3)

        r3 = envelopes[bench.SLOT_HUMAN_LIKE_TEXT].execute(
            {"slot_id": bench.SLOT_HUMAN_LIKE_TEXT}, simulate_recoveries=3
        )
        self.assertTrue(r3.succeeded)
        self.assertEqual(r3.selected_engine, "deterministic_lexical_cleaner")
        self.assertEqual(len(r3.attempted_engines), 4)

    def test_known_wrong_controls_block_all_bad_inputs(self) -> None:
        controls = bench.run_known_wrong_controls()
        self.assertEqual(len(controls), 6)
        for ctrl in controls:
            self.assertTrue(ctrl["blocked_before_engine"], msg=f"Known-wrong control failed: {ctrl}")

        envelopes = bench.build_track_envelopes()
        bad_carrier = envelopes[bench.SLOT_HARNESS_CAPABILITY].execute({"slot_id": "wrong_slot"})
        self.assertFalse(bad_carrier.succeeded)
        self.assertIsNotNone(bad_carrier.refusal)
        self.assertEqual(bad_carrier.refusal.code, "invalid_benchmark_carrier")

    def test_run_all_benchmarks_aggregate_report(self) -> None:
        report = bench.run_all_benchmarks()
        self.assertTrue(report["all_tracks_succeeded"])
        self.assertTrue(report["all_known_wrong_blocked"])


if __name__ == "__main__":
    unittest.main()
