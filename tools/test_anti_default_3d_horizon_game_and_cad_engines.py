"""Tests and known-wrong controls for Anti-Default-LLM 3D Horizon & Spatial Scale Guard
(`td3d` / `worm3d` Upgrader) and Tinkercad, `Jumpstart-3D` (`3dxd`), `FluidCAD`, and `SolidCraft`
Parametric Code-CAD Suite.
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

import anti_default_3d_horizon_game_and_cad_engines as suite3d  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS  # noqa: E402


class AntiDefault3DHorizonGameAndCadEnginesTests(unittest.TestCase):
    """Verify all 3 slot families, local td3d/worm3d upgrades, 7 envelope layers, and 4 known-wrong controls."""

    def test_slot1_baseline_vs_four_swappable_3d_horizon_engines_and_local_td3d_worm3d(self) -> None:
        slot = suite3d.AntiDefault3DHorizonAndWorldScaleSlot()

        # Baseline control: unassisted LLM postage-stamp void
        baseline = slot.evaluate_baseline_without_baltor()
        self.assertEqual(baseline["engine_id"], suite3d.BASELINE_POSTAGE_STAMP_VOID)
        self.assertEqual(baseline["horizon_continuity_score"], 0.0)
        self.assertAlmostEqual(float(baseline["ground_to_far_clip_ratio"]), 0.102, places=3)
        self.assertEqual(baseline["depth_layers"], 1)
        self.assertFalse(baseline["has_skydome"])

        # All 4 swappable Baltor 3D World & Horizon Engines
        for idx, eng in enumerate(suite3d.SLOT1_ENGINES):
            res = slot.upgrade_scene(
                {
                    "preferred_engine": eng,
                    "scene_id": f"scene_{idx}",
                    "arena_span": 20.4,
                    "camera_far": 240.0,
                    "ground_radius": 216.0,
                    "duration_sec": 10.0,
                    "auto_upgrade_postage_stamp": True,
                },
                request_id=f"test_s1_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, eng)
            self.assertGreaterEqual(float(res.output["ground_to_far_clip_ratio"]), 0.85)
            self.assertGreaterEqual(float(res.output["far_to_arena_ratio"]), 8.0)
            self.assertGreaterEqual(float(res.output["duration_sec"]), 6.0)
            self.assertTrue(res.output["fog_matches_horizon"])
            self.assertEqual(res.output["depth_layers"], 3)
            self.assertGreater(float(res.output["horizon_continuity_score"]), 0.90)
            self.assertLessEqual(float(res.output["frame_time_ms"]), 16.6)
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

        # Upgrade actual local td3d.html and worm3d.html specs
        for html_name in ("td3d.html", "worm3d.html"):
            upgraded = slot.upgrade_local_html_file(
                Path("/home/username") / html_name,
                request_id=f"test_local_{html_name}",
            )
            self.assertTrue(upgraded["accepted"])
            self.assertEqual(upgraded["before_without_baltor"]["horizon_continuity_score"], 0.0)
            self.assertEqual(upgraded["before_without_baltor"]["depth_layers"], 1)
            self.assertGreaterEqual(float(upgraded["after_with_baltor"]["ground_to_far_clip_ratio"]), 0.85)
            self.assertEqual(upgraded["after_with_baltor"]["depth_layers"], 3)
            self.assertTrue(upgraded["after_with_baltor"]["within_60fps_budget"])

    def test_slot2_five_swappable_tinkercad_3dxd_fluidcad_solidcraft_and_slicer_engines(self) -> None:
        slot = suite3d.Tinkercad3dxdFluidcadSolidcraftCadSlot()
        for idx, eng in enumerate(suite3d.SLOT2_ENGINES):
            res = slot.synthesize_cad_component(
                {
                    "preferred_engine": eng,
                    "part_name": f"turret_housing_{idx}",
                    "z_min_mm": 0.0,
                    "vertices": 16,
                    "edges": 32,
                    "faces": 16,
                    "genus": 1,
                    "min_wall_thickness_mm": 1.8,
                    "snap_fit_clearance_mm": 0.20,
                    "max_overhang_deg": 35.0,
                },
                request_id=f"test_s2_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, eng)
            self.assertEqual(float(res.output["workplane_z_min_mm"]), 0.0)
            self.assertTrue(res.output["bed_adhesion_verified"])
            self.assertTrue(res.output["is_hole_booleans_grouped"])
            self.assertTrue(res.output["watertight_2_manifold"])
            self.assertEqual(res.output["euler_characteristic"], 0)
            self.assertGreaterEqual(float(res.output["min_wall_thickness_mm"]), 1.2)
            self.assertGreaterEqual(float(res.output["snap_fit_clearance_mm"]), 0.20)
            self.assertFalse(res.output["supports_required"])
            for layer in COVERAGE_LAYERS:
                self.assertEqual(res.layer_verdicts[layer], "full")

    def test_slot3_three_d_and_cad_harness_files_generator(self) -> None:
        slot = suite3d.ThreeDAndCadHarnessFilesSlot()
        for idx, eng in enumerate(suite3d.SLOT3_ENGINES):
            res = slot.generate_harness_pack(
                {"preferred_engine": eng},
                request_id=f"test_s3_{idx}",
            )
            self.assertTrue(res.accepted)
            self.assertEqual(res.selected_engine, eng)
            files = res.output["files"]
            self.assertIn("AGENTS.md", files)
            self.assertIn(".cursor/rules/3d-horizon-and-cad.mdc", files)
            self.assertIn("MEMORY.md", files)
            self.assertIn("0.85 * camera.far", files["AGENTS.md"])
            self.assertIn("0.20mm", files["AGENTS.md"])

    def test_known_wrong_controls_catch_and_refuse_all_four_bad_cases_plus_handshake(self) -> None:
        slot1 = suite3d.AntiDefault3DHorizonAndWorldScaleSlot()
        slot2 = suite3d.Tinkercad3dxdFluidcadSolidcraftCadSlot()

        # (a) Postage-stamp 3D scene in solid black void without horizon sky/fog match
        ctrl_a = slot1.upgrade_scene(
            {
                "arena_span": 20.4,
                "camera_far": 200.0,
                "ground_radius": 20.4,
                "has_skydome": False,
                "fog_matches_horizon": False,
                "auto_upgrade_postage_stamp": False,
            },
            request_id="test_ctrl_a",
        )
        self.assertFalse(ctrl_a.accepted)
        self.assertIsNotNone(ctrl_a.refusal)
        assert ctrl_a.refusal is not None
        self.assertEqual(ctrl_a.refusal.code, "postage_stamp_void_scene_rejected")
        self.assertEqual(ctrl_a.layer_verdicts["preflight"], "refused")

        # (b) 3D game animation shorter than 3.0s or enabling software-trap unbudgeted CPU bloom
        ctrl_b = slot1.upgrade_scene(
            {
                "arena_span": 20.4,
                "camera_far": 240.0,
                "ground_radius": 216.0,
                "duration_sec": 2.0,
                "unbudgeted_cpu_bloom": True,
                "auto_upgrade_postage_stamp": True,
            },
            request_id="test_ctrl_b",
        )
        self.assertFalse(ctrl_b.accepted)
        self.assertIsNotNone(ctrl_b.refusal)
        assert ctrl_b.refusal is not None
        self.assertEqual(ctrl_b.refusal.code, "cramped_duration_or_software_trap_rejected")
        self.assertEqual(ctrl_b.layer_verdicts["preflight"], "refused")

        # (c) Tinkercad / CAD part floating at z_min = +4.5mm above the print bed
        ctrl_c = slot2.synthesize_cad_component(
            {
                "part_name": "floating_tinkercad_gear",
                "z_min_mm": 4.5,
                "auto_snap_to_workplane": False,
            },
            request_id="test_ctrl_c",
        )
        self.assertFalse(ctrl_c.accepted)
        self.assertIsNotNone(ctrl_c.refusal)
        assert ctrl_c.refusal is not None
        self.assertEqual(ctrl_c.refusal.code, "floating_cad_part_off_workplane_rejected")
        self.assertEqual(ctrl_c.layer_verdicts["preflight"], "refused")

        # (d) Non-manifold mesh or zero-clearance (0.00mm) snap-fit joint that would fuse solid
        ctrl_d = slot2.synthesize_cad_component(
            {
                "part_name": "zero_clearance_non_manifold_clip",
                "z_min_mm": 0.0,
                "vertices": 8,
                "edges": 12,
                "faces": 5,
                "genus": 0,
                "non_manifold_edges": 2,
                "min_wall_thickness_mm": 0.8,
                "snap_fit_clearance_mm": 0.0,
            },
            request_id="test_ctrl_d",
        )
        self.assertFalse(ctrl_d.accepted)
        self.assertIsNotNone(ctrl_d.refusal)
        assert ctrl_d.refusal is not None
        self.assertEqual(ctrl_d.refusal.code, "non_manifold_or_zero_clearance_rejected")
        self.assertEqual(ctrl_d.layer_verdicts["preflight"], "refused")

        # Layer 3 handshake stale release_digest check
        stale_hs = slot1.upgrade_scene(
            {
                "arena_span": 20.4,
                "cached_card_release_digest": "sha256:stale_digest_v0",
            },
            request_id="test_stale_hs",
        )
        self.assertFalse(stale_hs.accepted)
        self.assertEqual(stale_hs.layer_verdicts["handshake"], "refused")

    def test_comprehensive_benchmark_runner_and_controls(self) -> None:
        report = suite3d.run_comprehensive_3d_horizon_and_cad_benchmark()
        self.assertEqual(len(report["slot1_horizon_engines"]), 4)
        self.assertEqual(len(report["slot2_cad_engines"]), 5)
        self.assertEqual(len(report["slot3_harness_packs"]), 3)
        for key, blocked in report["known_wrong_controls"].items():
            self.assertTrue(blocked, msg=f"Known-wrong control {key} did not block!")


if __name__ == "__main__":
    unittest.main()
