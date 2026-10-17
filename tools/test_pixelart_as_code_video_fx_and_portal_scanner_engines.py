"""Tests and known-wrong controls for `tools/pixelart_as_code_video_fx_and_portal_scanner_engines.py`."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import pixelart_as_code_video_fx_and_portal_scanner_engines as pxl_suite  # noqa: E402


class PixelArtAsCodeVideoFxAndPortalScannerTests(unittest.TestCase):
    """Verify all 3 slot families, 11 engines, Fourier epicycles, CA mass conservation, and 4 known-wrong controls."""

    def test_slot1_pixelart_as_code_and_pixel_logic_four_engines(self) -> None:
        env = pxl_suite.build_pixelart_as_code_envelope()
        for eng in pxl_suite.PIXELART_SLOT_ENGINES:
            res = env.execute(
                {
                    "record_type": "baltor.pixelart_and_logic.request.v1",
                    "request_id": f"test_pxl_{eng}",
                    "palette_name": "PICO-8",
                    "grid_width": 16,
                    "grid_height": 16,
                    "scale_factor": 4,
                    "nearest_neighbor_only": True,
                    "texture_filter": "THREE.NearestFilter",
                    "symmetry_mode": "bilateral_x",
                    "ca_ticks": 8,
                },
                preferred_engine=eng,
            )
            self.assertEqual(res["status"], "ok")
            out = res["result"]
            self.assertEqual(out["selected_engine"], eng)
            self.assertEqual(out["sprite_sheet_atlas"]["frame_count"], 12)
            self.assertEqual(out["sprite_sheet_atlas"]["symmetry_mismatch_count"], 0)
            self.assertTrue(out["cellular_and_isometric_logic"]["mass_conserved"])

    def test_slot2_video_fx_fourier_rig_and_transform_four_engines(self) -> None:
        env = pxl_suite.build_video_fx_fourier_envelope()
        for eng in pxl_suite.VIDEO_FX_SLOT_ENGINES:
            res = env.execute(
                {
                    "record_type": "baltor.video_fx_fourier.request.v1",
                    "request_id": f"test_vfx_{eng}",
                    "frame_count": 16,
                    "fourier_harmonics_m": 4,
                    "lightning_flash_hz": 1.8,
                    "homography_determinant": 1.04,
                },
                preferred_engine=eng,
            )
            self.assertEqual(res["status"], "ok")
            out = res["result"]
            self.assertEqual(out["selected_engine"], eng)
            self.assertEqual(out["fourier_epicycle_rig"]["epicycle_count"], 9)
            self.assertLessEqual(out["fourier_epicycle_rig"]["reconstruction_rmse"], 0.05)
            self.assertTrue(out["multi_plane_broll_and_weather_fx"]["bt1702_photosensitive_safe"])

    def test_slot3_portal_project_scanner_and_db_ingester_three_engines(self) -> None:
        env = pxl_suite.build_portal_project_scanner_envelope()
        for eng in pxl_suite.PORTAL_SCANNER_SLOT_ENGINES:
            res = env.execute(
                {
                    "record_type": "baltor.portal_project_scanner.request.v1",
                    "request_id": f"test_portal_{eng}",
                    "projects": pxl_suite.default_emerging_project_candidates(),
                },
                preferred_engine=eng,
            )
            self.assertEqual(res["status"], "ok")
            out = res["result"]
            self.assertEqual(out["selected_engine"], eng)
            self.assertEqual(out["scanned_project_count"], 12)
            self.assertEqual(out["ingested_project_count"], 12)
            self.assertEqual(out["rule6_dual_engine_parity_rate"], 1.0)

    def test_benchmark_and_all_four_known_wrong_controls(self) -> None:
        bench = pxl_suite.run_pixelart_video_fx_and_portal_benchmark()
        self.assertEqual(bench["total_engines_verified"], 11)
        for ctrl_name, passed in bench["known_wrong_controls"].items():
            self.assertTrue(passed, msg=f"Known-wrong control {ctrl_name} failed!")


if __name__ == "__main__":
    unittest.main()
