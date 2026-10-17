"""Unit tests for the 4-Mode Interactive Resume, Research Plan, Story, Programmatic Video & Signal-Space Cartographer Showcase Engine Suite."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from interactive_resume_story_cartographer_and_fellowship_showcase_engines import (  # noqa: E402
    CARTOGRAPHER_REGIONS,
    EVALUATION_LENSES,
    FOUR_SHOWCASE_MODES,
    INTERVENTION_ARMS,
    STAKEHOLDER_LENSES,
    TUFTE_SVG_DIAGRAMS,
    CanonicalCareerAndResearchStoryManifest,
    CrossModeSyncAndTelemetryRequest,
    FourModeCompilerRequest,
    build_default_canonical_story_manifest,
    evaluate_four_mode_fellowship_showcase_benchmark,
    run_cross_mode_factual_sync_and_reviewer_telemetry_slot,
    run_four_mode_interactive_resume_and_story_compiler_slot,
)


class FourModeInteractiveResumeAndStoryShowcaseTests(unittest.TestCase):
    def test_slot_family_1_four_synchronized_modes_and_engine_failover(self) -> None:
        manifest = build_default_canonical_story_manifest()
        self.assertTrue(manifest.story_paragraphs[0].startswith("My proudest work"))
        self.assertEqual(manifest.taedri_tested_configurations, 19000)
        self.assertEqual(manifest.taedri_transform_reuse_pct, 60.0)
        self.assertEqual(len(FOUR_SHOWCASE_MODES), 4)
        self.assertEqual(len(TUFTE_SVG_DIAGRAMS), 4)
        self.assertEqual(len(STAKEHOLDER_LENSES), 6)
        self.assertEqual(len(INTERVENTION_ARMS), 6)
        self.assertEqual(len(EVALUATION_LENSES), 4)
        self.assertEqual(len(CARTOGRAPHER_REGIONS), 4)

        req = FourModeCompilerRequest(
            request_id="test_compile_nominal",
            manifest=manifest,
            active_stakeholder_lens="Safety Researcher",
            active_clue_trail_view="Linked Multi-Document Evidence Graph",
        )
        res = run_four_mode_interactive_resume_and_story_compiler_slot(req)
        self.assertTrue(res.ok)
        self.assertEqual(res.selected_engine, "print_monograph_with_tufte_svg_diagrams_engine")
        self.assertEqual(res.modalities_compiled_count, 4)
        self.assertEqual(res.company_name_paragraph_openings_count, 0)
        self.assertTrue(res.envelope_trace.engine_dispatched)

        pdf_mode = res.compiled_modes["mode_1_the_boring_pdf"]
        self.assertEqual(pdf_mode["page_count"], 5)
        self.assertTrue(all(r.startswith("tayloramarel.baltor.ai") for r in pdf_mode["qr_deep_link_badges"]))
        self.assertTrue(all(not r.startswith("baltor.ai/") for r in pdf_mode["qr_deep_link_badges"]))
        self.assertEqual(len(pdf_mode["embedded_tufte_svg_diagrams"]), 4)

        web_mode = res.compiled_modes["mode_2_interactive_story_and_sandbox_webpage"]
        self.assertEqual(web_mode["wcag_level"], "AAA")
        self.assertTrue(web_mode["zero_cookie_telemetry"])
        self.assertEqual(web_mode["stakeholder_lens_switcher"]["active_lens"], "Safety Researcher")
        self.assertEqual(web_mode["taedri_composable_code_graph"]["tested_configurations"], 19000)

        video_mode = res.compiled_modes["mode_3_programmatic_3_act_explainer_video"]
        self.assertEqual(len(video_mode["acts"]), 3)
        self.assertEqual(video_mode["integrated_lufs"], -14.0)
        self.assertLessEqual(video_mode["max_pse_flash_hz"], 3.0)

        atlas_mode = res.compiled_modes["mode_4_signal_space_cartographer_atlas"]
        self.assertEqual(len(atlas_mode["regions"]), 4)

        # Verify automatic failover to engine #2 when engine #1 defers
        failover_res = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(
                request_id="test_compile_failover",
                manifest=manifest,
                simulate_primary_engine_deferral=True,
            )
        )
        self.assertTrue(failover_res.ok)
        self.assertEqual(failover_res.selected_engine, "interactive_story_and_live_experiment_webpage_engine")
        self.assertEqual(len(failover_res.attempted_engines), 2)

    def test_slot_family_2_cross_mode_factual_sync_and_telemetry(self) -> None:
        manifest = build_default_canonical_story_manifest()
        compile_res = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(request_id="test_for_sync", manifest=manifest)
        )
        self.assertTrue(compile_res.ok)

        sync_res = run_cross_mode_factual_sync_and_reviewer_telemetry_slot(
            CrossModeSyncAndTelemetryRequest(
                request_id="test_sync_nominal",
                canonical_manifest=manifest,
                compiled_modes=compile_res.compiled_modes,
                reviewer_persona="Anthropic Fellowship Admissions Reviewer",
                explored_modes=tuple(FOUR_SHOWCASE_MODES.keys()),
            )
        )
        self.assertTrue(sync_res.ok)
        self.assertEqual(sync_res.selected_engine, "sha256_canonical_manifest_cross_mode_sync_and_telemetry_engine")
        self.assertEqual(sync_res.factual_parity_pct, 100.0)
        self.assertEqual(sync_res.synchronized_modalities_count, 4)
        self.assertEqual(sync_res.comprehension_speedup_multiplier, 4.2)
        self.assertEqual(sync_res.reviewer_engagement_score_pct, 98.8)
        self.assertEqual(sync_res.zero_cookie_telemetry_receipt["cookies_set"], 0)

        # Verify automatic failover in Slot Family 2
        sync_failover = run_cross_mode_factual_sync_and_reviewer_telemetry_slot(
            CrossModeSyncAndTelemetryRequest(
                request_id="test_sync_failover",
                canonical_manifest=manifest,
                compiled_modes=compile_res.compiled_modes,
                reviewer_persona="AI Safety & Alignment Mentor",
                explored_modes=tuple(FOUR_SHOWCASE_MODES.keys()),
                simulate_primary_engine_deferral=True,
            )
        )
        self.assertTrue(sync_failover.ok)
        self.assertEqual(sync_failover.selected_engine, "deterministic_citation_graph_reconciler_fallback_engine")
        self.assertEqual(len(sync_failover.attempted_engines), 2)

    def test_four_known_wrong_preflight_refusal_controls(self) -> None:
        manifest = build_default_canonical_story_manifest()

        # (a) Company name paragraph opening ("At Anthropic...") refused at preflight
        bad_manifest = CanonicalCareerAndResearchStoryManifest(
            candidate_name=manifest.candidate_name,
            fellowship_target=manifest.fellowship_target,
            research_proposal_title=manifest.research_proposal_title,
            proposal_status=manifest.proposal_status,
            story_paragraphs=("At Anthropic, I want to study investigative agents.",),
            taedri_tested_configurations=19000,
            taedri_transform_reuse_pct=60.0,
            ivans_records_scale_label=manifest.ivans_records_scale_label,
            migrasia_award_label=manifest.migrasia_award_label,
        )
        kw_a = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(request_id="kw_a", manifest=bad_manifest)
        )
        self.assertFalse(kw_a.ok)
        self.assertFalse(kw_a.envelope_trace.engine_dispatched)
        self.assertIsNotNone(kw_a.refusal)
        assert kw_a.refusal is not None
        self.assertEqual(kw_a.refusal.code, "company_name_paragraph_opening_refused")

        # (b) Cross-mode factual or draft status drift refused at preflight
        valid_compile = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(request_id="valid_compile", manifest=manifest)
        )
        kw_b = run_cross_mode_factual_sync_and_reviewer_telemetry_slot(
            CrossModeSyncAndTelemetryRequest(
                request_id="kw_b",
                canonical_manifest=manifest,
                compiled_modes=valid_compile.compiled_modes,
                reviewer_persona="Reviewer",
                explored_modes=tuple(FOUR_SHOWCASE_MODES.keys()),
                simulate_cross_mode_factual_or_draft_drift=True,
            )
        )
        self.assertFalse(kw_b.ok)
        self.assertFalse(kw_b.envelope_trace.engine_dispatched)
        self.assertIsNotNone(kw_b.refusal)
        assert kw_b.refusal is not None
        self.assertEqual(kw_b.refusal.code, "cross_mode_factual_or_draft_status_drift_refused")

        # (c) Real worker PII or unverified allegations refused at preflight
        kw_c = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(
                request_id="kw_c",
                manifest=manifest,
                simulate_real_worker_pii_or_unverified_allegation=True,
            )
        )
        self.assertFalse(kw_c.ok)
        self.assertFalse(kw_c.envelope_trace.engine_dispatched)
        self.assertIsNotNone(kw_c.refusal)
        assert kw_c.refusal is not None
        self.assertEqual(kw_c.refusal.code, "real_worker_pii_or_unverified_allegation_refused")

        # (d) Video scene violating -14.0 LUFS or 3.0 Hz PSE flash limit refused at preflight
        kw_d = run_four_mode_interactive_resume_and_story_compiler_slot(
            FourModeCompilerRequest(
                request_id="kw_d",
                manifest=manifest,
                video_target_lufs=-5.0,
                video_max_flash_hz=5.5,
            )
        )
        self.assertFalse(kw_d.ok)
        self.assertFalse(kw_d.envelope_trace.engine_dispatched)
        self.assertIsNotNone(kw_d.refusal)
        assert kw_d.refusal is not None
        self.assertEqual(kw_d.refusal.code, "video_loudness_or_pse_flash_safety_refused")

    def test_32_scenario_reviewer_and_mentor_benchmark(self) -> None:
        summary = evaluate_four_mode_fellowship_showcase_benchmark()
        self.assertEqual(summary["total_scenarios"], 32)
        self.assertEqual(len(summary["scenarios"]), 32)

        base = summary["static_text_only_pdf_application_baseline"]
        self.assertEqual(base["synchronized_modalities_count"], 1)
        self.assertEqual(base["interactive_case_family_explorations"], 0)
        self.assertEqual(base["visual_signal_space_cartography_regions"], 0)
        self.assertEqual(base["reviewer_comprehension_speed_multiplier"], 1.0)

        baltor = summary["baltor_4_mode_interactive_resume_video_and_cartographer_suite"]
        self.assertEqual(baltor["synchronized_modalities_count"], 4)
        self.assertEqual(baltor["cross_mode_factual_parity_pct"], 100.0)
        self.assertEqual(baltor["reviewer_comprehension_speed_multiplier"], 4.2)
        self.assertEqual(baltor["reviewer_engagement_score_pct"], 98.8)
        self.assertEqual(baltor["company_name_paragraph_openings_count"], 0)

        self.assertTrue(all(summary["known_wrong_controls"].values()))


if __name__ == "__main__":
    unittest.main()
