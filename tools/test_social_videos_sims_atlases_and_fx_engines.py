"""Unit tests for Social Videos Sims, 3D Atlases, Geo-Globes, Audio-Physics, and Compositing FX Components."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))
if str(REPOSITORY / "tools") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "tools"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
)
from social_videos_sims_atlases_and_fx_engines import (  # noqa: E402
    COMPOSITING_CHARACTER_ENGINE_IDS,
    ENGINE_ANIMATED_3D_ATLAS_PARKS_STATIONS,
    ENGINE_BALL_LAB_AND_MARBLE_ORCHESTRA,
    ENGINE_CIRCLE_SWARM_AND_HEXAGON_TRAIL,
    ENGINE_GEO_FIRE_GLOBE_AND_STORIES,
    ENGINE_LIVING_3D_TRAFFIC_RAIL_FARM,
    ENGINE_OPTICAL_ILLUSION_AFTEREFFECT,
    ENGINE_PIP_AND_SCREEN_RECORDING_RIG,
    ENGINE_POINT_VORTEX_3D_EMERALD_KNOT,
    ENGINE_SHADOW_FABLES_SILHOUETTE,
    ENGINE_SOUND_SIMS_POLYPHONIC_VISUALIZER,
    ENGINE_STICK_STUDIO_AND_SMOLMERII_RIG,
    ENGINE_TRANSITIONS_AND_COMPOSITING_FX,
    LIVING_WORLDS_ENGINE_IDS,
    MATERIAL_STYLES,
    RECOVERABLE_FX_CODES,
    RECOVERABLE_LIVING_WORLD_CODES,
    RECOVERABLE_SIM_CODES,
    SATISFYING_SIMS_ENGINE_IDS,
    SLOT_COMPOSITING_FX_AND_CHARACTERS,
    SLOT_LIVING_WORLDS_AND_ATLASES,
    SLOT_SATISFYING_AND_SOUND_SIMS,
    STUDIO_PROVENANCE_MAP,
    SocialVideosStudioSlotOrchestrator,
    StudioComponentRequest,
    run_comprehensive_benchmark,
    self_test,
)


class LivingWorldsAndGeoAtlasesSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = SocialVideosStudioSlotOrchestrator(SLOT_LIVING_WORLDS_AND_ATLASES)

    def test_all_four_living_world_and_atlas_engines_execute_and_preserve_invariants(self) -> None:
        for engine_id in LIVING_WORLDS_ENGINE_IDS:
            resp = self.orchestrator.handle(
                StudioComponentRequest(
                    request_id=f"test-lw-{engine_id}",
                    slot_id=SLOT_LIVING_WORLDS_AND_ATLASES,
                    preferred_engine=engine_id,
                    material_style="photorealistic_pbr",
                )
            )
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertTrue(resp.output["zero_collision_invariant"])
            self.assertIsNotNone(resp.nested_safety_trace)

    def test_all_eight_visual_material_styles_swap_without_topology_regeneration(self) -> None:
        digests = set()
        for style in MATERIAL_STYLES:
            resp = self.orchestrator.handle(
                StudioComponentRequest(
                    request_id=f"test-style-{style}",
                    slot_id=SLOT_LIVING_WORLDS_AND_ATLASES,
                    preferred_engine=ENGINE_POINT_VORTEX_3D_EMERALD_KNOT,
                    material_style=style,
                )
            )
            self.assertTrue(resp.succeeded, style)
            self.assertEqual(resp.output["material_style"], style)
            self.assertTrue(resp.output["circulation_conserved"])
            digests.add(resp.contract_digest)
        self.assertEqual(len(digests), 8)

    def test_automatic_recovery_falls_back_across_all_four_living_world_engines(self) -> None:
        resp = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-lw-fallback",
                slot_id=SLOT_LIVING_WORLDS_AND_ATLASES,
                preferred_engine=ENGINE_LIVING_3D_TRAFFIC_RAIL_FARM,
                simulate_recoverable_deferrals=RECOVERABLE_LIVING_WORLD_CODES,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_POINT_VORTEX_3D_EMERALD_KNOT)
        self.assertEqual(resp.fallback_attempts_used, 3)

    def test_known_wrong_rail_and_traffic_collision_refused_or_repaired(self) -> None:
        refused = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-lw-collision-refused",
                slot_id=SLOT_LIVING_WORLDS_AND_ATLASES,
                preferred_engine=ENGINE_LIVING_3D_TRAFFIC_RAIL_FARM,
                parameters={"injected_collisions": 3, "block_signal_headway_s": 2.0},
                allow_self_repair=False,
            )
        )
        self.assertFalse(refused.succeeded)
        self.assertEqual(refused.outer_trace.refused_by, LAYER_PREFLIGHT)
        self.assertFalse(refused.outer_trace.engine_dispatched)
        assert refused.refusal is not None
        self.assertEqual(refused.refusal.code, "rail_traffic_block_collision_refused")

        repaired = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-lw-collision-repaired",
                slot_id=SLOT_LIVING_WORLDS_AND_ATLASES,
                preferred_engine=ENGINE_LIVING_3D_TRAFFIC_RAIL_FARM,
                parameters={"injected_collisions": 3, "block_signal_headway_s": 2.0},
                allow_self_repair=True,
            )
        )
        self.assertTrue(repaired.succeeded)
        assert repaired.preflight_report is not None
        self.assertEqual(repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertTrue(repaired.output["zero_collision_invariant"])


class SatisfyingPhysicsAndSoundSimsSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = SocialVideosStudioSlotOrchestrator(SLOT_SATISFYING_AND_SOUND_SIMS)

    def test_all_four_satisfying_and_sound_sim_engines_execute(self) -> None:
        for engine_id in SATISFYING_SIMS_ENGINE_IDS:
            resp = self.orchestrator.handle(
                StudioComponentRequest(
                    request_id=f"test-sim-{engine_id}",
                    slot_id=SLOT_SATISFYING_AND_SOUND_SIMS,
                    preferred_engine=engine_id,
                    material_style="refractive_glass_crystal",
                )
            )
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertLessEqual(resp.output["max_sync_drift_ms"], 1.0)

    def test_automatic_recovery_falls_back_across_satisfying_sim_engines(self) -> None:
        resp = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-sim-fallback",
                slot_id=SLOT_SATISFYING_AND_SOUND_SIMS,
                preferred_engine=ENGINE_BALL_LAB_AND_MARBLE_ORCHESTRA,
                simulate_recoverable_deferrals=RECOVERABLE_SIM_CODES,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_OPTICAL_ILLUSION_AFTEREFFECT)
        self.assertEqual(resp.fallback_attempts_used, 3)

    def test_known_wrong_pse_flash_violation_and_audio_clipping_refused_or_repaired(self) -> None:
        pse_refused = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-pse-refused",
                slot_id=SLOT_SATISFYING_AND_SOUND_SIMS,
                preferred_engine=ENGINE_OPTICAL_ILLUSION_AFTEREFFECT,
                parameters={"flash_rate_hz": 7.2},
                allow_self_repair=False,
            )
        )
        self.assertFalse(pse_refused.succeeded)
        self.assertEqual(pse_refused.outer_trace.refused_by, LAYER_HANDSHAKE)
        self.assertFalse(pse_refused.outer_trace.engine_dispatched)
        assert pse_refused.refusal is not None
        self.assertEqual(pse_refused.refusal.code, "pse_harding_flash_rate_violation")

        audio_refused = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-audio-refused",
                slot_id=SLOT_SATISFYING_AND_SOUND_SIMS,
                preferred_engine=ENGINE_SOUND_SIMS_POLYPHONIC_VISUALIZER,
                parameters={"av_desync_frames": 3.0, "true_peak_dbtp": 1.4},
                allow_self_repair=False,
            )
        )
        self.assertFalse(audio_refused.succeeded)
        self.assertEqual(audio_refused.outer_trace.refused_by, LAYER_PREFLIGHT)
        assert audio_refused.refusal is not None
        self.assertEqual(audio_refused.refusal.code, "audio_visual_sync_or_clipping_violation")

        audio_repaired = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-audio-repaired",
                slot_id=SLOT_SATISFYING_AND_SOUND_SIMS,
                preferred_engine=ENGINE_SOUND_SIMS_POLYPHONIC_VISUALIZER,
                parameters={"av_desync_frames": 3.0, "true_peak_dbtp": 1.4},
                allow_self_repair=True,
            )
        )
        self.assertTrue(audio_repaired.succeeded)
        assert audio_repaired.preflight_report is not None
        self.assertEqual(audio_repaired.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertLessEqual(audio_repaired.output["true_peak_dbtp"], -1.0)


class CompositingFxAndCharacterPacksSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = SocialVideosStudioSlotOrchestrator(SLOT_COMPOSITING_FX_AND_CHARACTERS)

    def test_all_four_compositing_and_character_engines_execute(self) -> None:
        for engine_id in COMPOSITING_CHARACTER_ENGINE_IDS:
            resp = self.orchestrator.handle(
                StudioComponentRequest(
                    request_id=f"test-fx-{engine_id}",
                    slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                    preferred_engine=engine_id,
                    material_style="cel_animated_ink",
                )
            )
            self.assertTrue(resp.succeeded, engine_id)
            self.assertEqual(resp.selected_engine, engine_id)
            self.assertTrue(resp.output["safe_zone_compliant"])

    def test_automatic_recovery_falls_back_across_compositing_and_character_engines(self) -> None:
        resp = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-fx-fallback",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_TRANSITIONS_AND_COMPOSITING_FX,
                simulate_recoverable_deferrals=RECOVERABLE_FX_CODES,
            )
        )
        self.assertTrue(resp.succeeded)
        self.assertEqual(resp.selected_engine, ENGINE_STICK_STUDIO_AND_SMOLMERII_RIG)
        self.assertEqual(resp.fallback_attempts_used, 3)

    def test_known_wrong_pip_focal_and_keepout_occlusion_refused_or_repaired(self) -> None:
        refused = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-pip-refused",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_PIP_AND_SCREEN_RECORDING_RIG,
                parameters={"pip_bbox": (240, 720, 620, 1700)},
                allow_self_repair=False,
            )
        )
        self.assertFalse(refused.succeeded)
        self.assertEqual(refused.outer_trace.refused_by, LAYER_PREFLIGHT)
        assert refused.preflight_report is not None
        self.assertEqual(refused.preflight_report.verdict, VERDICT_REFUSED)
        assert refused.refusal is not None
        self.assertEqual(refused.refusal.code, "pip_focal_or_keepout_zone_occlusion")

        repaired = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-pip-repaired",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_PIP_AND_SCREEN_RECORDING_RIG,
                parameters={"pip_bbox": (240, 720, 620, 1700)},
                allow_self_repair=True,
            )
        )
        self.assertTrue(repaired.succeeded)
        self.assertTrue(repaired.output["safe_zone_compliant"])

    def test_carrier_handshake_and_account_layer_refusals(self) -> None:
        bad_style = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-bad-style",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_SHADOW_FABLES_SILHOUETTE,
                material_style="nonexistent_shader",
            )
        )
        self.assertFalse(bad_style.succeeded)
        self.assertEqual(bad_style.outer_trace.refused_by, LAYER_CARRIER)

        bad_version = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-bad-version",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_SHADOW_FABLES_SILHOUETTE,
                requested_versions=("v99",),
            )
        )
        self.assertFalse(bad_version.succeeded)
        self.assertEqual(bad_version.outer_trace.refused_by, LAYER_HANDSHAKE)

        unentitled = self.orchestrator.handle(
            StudioComponentRequest(
                request_id="test-unentitled",
                slot_id=SLOT_COMPOSITING_FX_AND_CHARACTERS,
                preferred_engine=ENGINE_SHADOW_FABLES_SILHOUETTE,
                account_entitled=False,
            )
        )
        self.assertFalse(unentitled.succeeded)
        self.assertEqual(unentitled.outer_trace.refused_by, LAYER_ACCOUNT)

    def test_comprehensive_benchmark_and_provenance_coverage(self) -> None:
        report = self_test()
        self.assertEqual(report["total_slots"], 3)
        self.assertEqual(report["total_engines"], 12)
        self.assertEqual(report["total_studio_families"], 16)
        self.assertEqual(report["total_studio_sources"], 18)
        self.assertEqual(sum(len(v) for v in STUDIO_PROVENANCE_MAP.values()), 18)
        comparison = run_comprehensive_benchmark()["without_vs_with_baltor"]
        self.assertEqual(comparison["with_baltor"]["unhandled_rail_or_pip_collisions"], 0)
        self.assertEqual(comparison["with_baltor"]["material_style_swap_cost_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
