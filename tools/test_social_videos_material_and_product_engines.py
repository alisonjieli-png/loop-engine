#!/usr/bin/env python3
"""Unit tests for `tools/social_videos_material_and_product_engines.py`."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _rel in ("src", "tools"):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import social_videos_material_and_product_engines as svmp  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    EnvelopeRefusal,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    STEP_REPAIRED,
    VERDICT_READY,
    VERDICT_REPAIRED,
)


class TactileMaterialShaderSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = svmp.ComponentEnvelope(
            svmp.SLOT_TACTILE_MATERIAL_SHADER,
            svmp.WIRE_TACTILE_SHADER_V1,
            svmp.TACTILE_SHADER_ENGINES,
        )

    def test_twelve_tactile_material_families_without_vs_with_baltor(self) -> None:
        self.assertEqual(len(svmp.TACTILE_MATERIAL_SPECS), 12)
        expected_ids = (
            "pbr_ultra_texture",
            "low_poly_faceted",
            "claymation_stopmotion",
            "refractive_glass",
            "glazed_ceramic_kintsugi",
            "subsurface_jelly",
            "liquid_chrome",
            "thin_film_iridescence",
            "velvet_felt_plush",
            "papercraft_layered",
            "bioluminescent_holo",
            "cel_gouache_animated",
        )
        self.assertEqual(tuple(s.material_id for s in svmp.TACTILE_MATERIAL_SPECS), expected_ids)

        for spec in svmp.TACTILE_MATERIAL_SPECS:
            without = svmp.evaluate_tactile_material_physics(spec, with_baltor=False)
            self.assertFalse(without["energy_conserving"])
            self.assertGreater(without["outgoing_radiance"], without["radiance_budget"])
            self.assertEqual(without["micro_detail_layers_active"], 0)

            res = self.envelope.execute(
                request_id=f"test_{spec.material_id}",
                payload_eval_fn=lambda s=spec: svmp.evaluate_tactile_material_physics(s, with_baltor=True),
            )
            self.assertIsInstance(res, svmp.ComponentEnvelopeResult)
            assert isinstance(res, svmp.ComponentEnvelopeResult)
            self.assertEqual(res.engine_id, svmp.ENGINE_BALTOR_MICROFACET_BRDF)
            self.assertFalse(res.fallback_used)
            self.assertEqual(res.preflight_report.verdict, VERDICT_READY)
            self.assertTrue(res.payload["energy_conserving"])
            self.assertLessEqual(res.payload["outgoing_radiance"], res.payload["radiance_budget"])
            self.assertEqual(res.payload["micro_detail_layers_active"], 3)
            self.assertGreater(res.payload["physical_fidelity_score"], without["physical_fidelity_score"])
            self.assertEqual(
                res.nested_qa_frame.path,
                (svmp.SLOT_TACTILE_MATERIAL_SHADER, svmp.SLOT_NESTED_BRDF_QA_GATE),
            )

    def test_low_poly_barycentric_catchlight_and_claymation_boil_on_threes(self) -> None:
        low_poly = svmp.TACTILE_MATERIAL_SPECS[1]
        edge_hit = svmp.evaluate_tactile_material_physics(
            low_poly, with_baltor=True, barycentric_coords=(0.02, 0.49, 0.49)
        )
        interior_hit = svmp.evaluate_tactile_material_physics(
            low_poly, with_baltor=True, barycentric_coords=(0.25, 0.35, 0.40)
        )
        self.assertAlmostEqual(edge_hit["low_poly_catchlight"], 0.12)
        self.assertAlmostEqual(interior_hit["low_poly_catchlight"], 0.0)

        clay = svmp.TACTILE_MATERIAL_SPECS[2]
        buckets = [
            svmp.evaluate_tactile_material_physics(clay, with_baltor=True, frame_index=f)["boil_bucket"]
            for f in range(9)
        ]
        self.assertEqual(buckets, [0, 0, 0, 1, 1, 1, 2, 2, 2])

    def test_swappable_shader_engine_failover_and_exhaustion(self) -> None:
        spec = svmp.TACTILE_MATERIAL_SPECS[0]
        res_second = self.envelope.execute(
            request_id="failover_to_three",
            payload_eval_fn=lambda: svmp.evaluate_tactile_material_physics(spec, with_baltor=True),
            simulated_fault_engines=frozenset({svmp.ENGINE_BALTOR_MICROFACET_BRDF}),
        )
        self.assertIsInstance(res_second, svmp.ComponentEnvelopeResult)
        assert isinstance(res_second, svmp.ComponentEnvelopeResult)
        self.assertEqual(res_second.engine_id, svmp.ENGINE_THREE_WEBGL_PBR)
        self.assertTrue(res_second.fallback_used)

        res_third = self.envelope.execute(
            request_id="failover_to_cpu_scanline",
            payload_eval_fn=lambda: svmp.evaluate_tactile_material_physics(spec, with_baltor=True),
            simulated_fault_engines=frozenset(
                {svmp.ENGINE_BALTOR_MICROFACET_BRDF, svmp.ENGINE_THREE_WEBGL_PBR}
            ),
        )
        self.assertIsInstance(res_third, svmp.ComponentEnvelopeResult)
        assert isinstance(res_third, svmp.ComponentEnvelopeResult)
        self.assertEqual(res_third.engine_id, svmp.ENGINE_CPU_SCANLINE_SHADER)
        self.assertTrue(res_third.fallback_used)


class ExoticMaterialAndProductStudioSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = svmp.ComponentEnvelope(
            svmp.SLOT_EXOTIC_PRODUCT_STUDIO,
            svmp.WIRE_EXOTIC_STUDIO_V1,
            svmp.EXOTIC_STUDIO_ENGINES,
        )

    def test_seven_exotic_materials_and_nine_reflective_products(self) -> None:
        self.assertEqual(len(svmp.EXOTIC_MATERIAL_SPECS), 7)
        self.assertEqual(len(svmp.REFLECTIVE_PRODUCT_SPECS), 9)
        exotic_by_id = {e.exotic_id: e for e in svmp.EXOTIC_MATERIAL_SPECS}

        for prod in svmp.REFLECTIVE_PRODUCT_SPECS:
            exotic = exotic_by_id[prod.paired_exotic_id]
            without = svmp.evaluate_exotic_and_product_studio(prod, exotic, with_baltor=False)
            self.assertFalse(without["monotonic_grit_wipe"])
            self.assertAlmostEqual(without["mirror_clarity_gain"], 1.0)

            res = self.envelope.execute(
                request_id=f"studio_{prod.product_id}",
                payload_eval_fn=lambda p=prod, e=exotic: svmp.evaluate_exotic_and_product_studio(
                    p, e, with_baltor=True
                ),
            )
            self.assertIsInstance(res, svmp.ComponentEnvelopeResult)
            assert isinstance(res, svmp.ComponentEnvelopeResult)
            self.assertTrue(res.payload["monotonic_grit_wipe"])
            self.assertAlmostEqual(res.payload["mirror_clarity_gain"], 68.0)
            self.assertAlmostEqual(res.payload["hdr_reflection_norm"], 1.0, places=5)
            self.assertEqual(res.payload["twill_pattern"], (0, 0, 1, 1, 1, 1, 0, 0))


class KnownWrongAndEnvelopeLayerTests(unittest.TestCase):
    def test_five_known_wrong_controls_refuse_and_detect_unguarded_leaks(self) -> None:
        controls = svmp.run_known_wrong_controls()
        self.assertEqual(len(controls), 5)
        expected_codes = {
            "non_energy_conserving_brdf_refused",
            "non_volume_preserving_jelly_deformation_refused",
            "inverted_abbe_dispersion_refused",
            "non_monotonic_grit_polish_wipe_refused",
            "self_approving_component_promotion_refused",
        }
        self.assertEqual({c["expected_refusal_code"] for c in controls}, expected_codes)
        for item in controls:
            self.assertTrue(item["refused_when_guarded"], item["control_id"])
            self.assertTrue(item["leaked_when_guard_removed"], item["control_id"])
            self.assertTrue(item["known_wrong_detected"], item["control_id"])

    def test_preflight_self_repair_clamps_energy_violating_brdf(self) -> None:
        shader_env = svmp.ComponentEnvelope(
            svmp.SLOT_TACTILE_MATERIAL_SHADER,
            svmp.WIRE_TACTILE_SHADER_V1,
            svmp.TACTILE_SHADER_ENGINES,
        )
        pbr_spec = svmp.TACTILE_MATERIAL_SPECS[0]
        repaired_res = shader_env.execute(
            request_id="repair_energy_violation",
            payload_eval_fn=lambda: svmp.evaluate_tactile_material_physics(
                pbr_spec, with_baltor=True, override_outgoing_radiance=1.42
            ),
            allow_preflight_repair=True,
        )
        self.assertIsInstance(repaired_res, svmp.ComponentEnvelopeResult)
        assert isinstance(repaired_res, svmp.ComponentEnvelopeResult)
        self.assertEqual(repaired_res.preflight_report.verdict, VERDICT_REPAIRED)
        self.assertEqual(repaired_res.preflight_report.steps[0].outcome, STEP_REPAIRED)
        self.assertTrue(repaired_res.payload["energy_conserving"])
        self.assertLessEqual(repaired_res.payload["outgoing_radiance"], repaired_res.payload["radiance_budget"])

    def test_full_benchmark_summary_completeness(self) -> None:
        summary = svmp.run_full_material_and_product_benchmark()
        self.assertEqual(tuple(summary["envelope_layers"]), COVERAGE_LAYERS)
        self.assertEqual(summary["tactile_shader_count"], 12)
        self.assertEqual(summary["exotic_material_count"], 7)
        self.assertEqual(summary["reflective_product_count"], 9)
        self.assertEqual(summary["known_wrong_count"], 5)
        self.assertTrue(summary["all_known_wrong_detected"])


if __name__ == "__main__":
    unittest.main()
