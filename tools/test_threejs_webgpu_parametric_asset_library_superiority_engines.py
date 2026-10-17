"""Unit tests for the 120-Generator Parametric Three.js r170+, WebGPU WGSL, React-Three-Fiber, glTF 2.0 & 4K MSDF Asset Library Engine Suite."""

from __future__ import annotations

import json
import unittest

from tools.threejs_webgpu_parametric_asset_library_superiority_engines import (
    EIGHT_QUANTITATIVE_SUPERIORITY_DIMENSIONS,
    FIVE_EXPORT_TARGETS,
    TEN_PARAMETRIC_ASSET_FAMILIES,
    ParametricThreeJSWebGPUAssetCatalogAndCompilerEngine,
    ThinComponentAdapter,
    ThreeJSAssetsVsBaltorHeadToHeadBenchmarkEngine,
    compile_parametric_generator_exports,
    run_all_threejs_webgpu_parametric_asset_library_benchmarks,
)


def test_120_generators_and_5_export_targets_compiler() -> None:
    assert len(TEN_PARAMETRIC_ASSET_FAMILIES) == 10
    expected_family_ids = (
        "F01_instanced_urban_skylines_and_emissive_window_atlases",
        "F02_first_person_parkour_gloves_ik_arms_and_vault_obstacles",
        "F03_webgpu_tsl_and_glsl_raymarched_forcefields_and_postfx",
        "F04_oklab_pbr_anisotropic_metals_clearcoat_and_glass_materials",
        "F05_noun_project_svg_to_watertight_manifold_3d_gltf_extruders",
        "F06_scientific_3d_embedding_manifolds_and_logit_lens_surfaces",
        "F07_procedural_foliage_terrain_and_water_caustics_simulators",
        "F08_arcade_vehicles_drones_and_rigid_body_rapier_colliders",
        "F09_4k_msdf_hud_reticles_radars_and_spatial_ui_holopanels",
        "F10_procedural_webaudio_spatial_hrtf_and_collision_sfx_pairs",
    )
    assert tuple(f["family_id"] for f in TEN_PARAMETRIC_ASSET_FAMILIES) == expected_family_ids
    assert sum(len(f["generators"]) for f in TEN_PARAMETRIC_ASSET_FAMILIES) == 120

    exports = compile_parametric_generator_exports(
        "brutalist_megatower_instanced_facade",
        "F01_instanced_urban_skylines_and_emissive_window_atlases",
        {"instances": 10240, "roughness": 0.2, "metallic": 0.85},
    )
    assert tuple(exports.keys()) == FIVE_EXPORT_TARGETS
    assert "THREE.InstancedMesh" in exports["threejs_r170_esm"]
    assert "<RigidBody" in exports["react_three_fiber_tsx"]
    assert "@compute @workgroup_size(64)" in exports["webgpu_wgsl_compute_and_frag"]
    gltf_doc = json.loads(exports["gltf_2_0_manifold_json"])
    assert gltf_doc["extras"]["watertight_2_manifold"] is True
    assert gltf_doc["extras"]["euler_characteristic_chi"] == 2
    card_doc = json.loads(exports["baltor_taedri_contract_card"])
    assert card_doc["collider_ready"] is True


def test_catalog_and_compiler_slot_and_known_wrong_controls() -> None:
    engine = ParametricThreeJSWebGPUAssetCatalogAndCompilerEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "parametric_threejs_webgpu_asset_catalog_and_compiler_slot")
    res = adapter.execute({})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True
    assert res["summary"]["family_count"] == 10
    assert res["summary"]["generators_per_family"] == 12
    assert res["summary"]["total_parametric_generators"] == 120
    assert res["summary"]["export_target_count"] == 5
    assert res["summary"]["max_window_instances_single_draw_call"] >= 10000

    # Known-wrong control 1: non-manifold or self-intersecting glTF mesh refused
    ref1 = adapter.execute({"non_manifold_mesh": True})
    assert ref1["status"] == "refused"
    assert ref1["error"]["code"] == "non_manifold_or_self_intersecting_gltf_mesh_refused"

    # Known-wrong control 4: unverified or proprietary asset license refused
    ref4 = adapter.execute({"unverified_or_proprietary_asset_license": True})
    assert ref4["status"] == "refused"
    assert ref4["error"]["code"] == "unverified_or_proprietary_asset_license_refused"


def test_head_to_head_benchmark_slot_and_known_wrong_controls() -> None:
    engine = ThreeJSAssetsVsBaltorHeadToHeadBenchmarkEngine()
    assert engine.preflight().ready is True
    assert engine.recovery_policy().maximum_automatic_attempts == 3

    adapter = ThinComponentAdapter(engine, "threejsassets_vs_baltor_head_to_head_benchmark_slot")
    res = adapter.execute({})
    assert res["status"] == "ok"
    assert adapter.verify_receipt(res) is True
    assert len(EIGHT_QUANTITATIVE_SUPERIORITY_DIMENSIONS) == 8
    assert res["summary"]["quantitative_dimensions_evaluated"] == 8
    assert res["summary"]["baltor_wins_count"] == 8
    assert res["summary"]["draw_call_reduction_factor_x"] == 5000.0
    assert res["static_directory_threejsassets_baseline"]["sustained_fps_5000_props"] == 14.0
    assert res["baltor_120_generator_parametric_asset_forge"]["sustained_fps_5000_props"] == 60.0
    assert res["baltor_120_generator_parametric_asset_forge"]["physics_collider_readiness_pct"] == 100.0

    # Known-wrong control 2: unbatched high draw-call scene regression refused
    ref2 = adapter.execute({"unbatched_high_draw_call_scene": True})
    assert ref2["status"] == "refused"
    assert ref2["error"]["code"] == "unbatched_high_draw_call_scene_regression_refused"

    # Known-wrong control 3: missing physics collider hull refused
    ref3 = adapter.execute({"missing_physics_collider_hull": True})
    assert ref3["status"] == "refused"
    assert ref3["error"]["code"] == "missing_physics_collider_hull_refused"


def test_end_to_end_threejs_webgpu_asset_library_suite() -> None:
    suite = run_all_threejs_webgpu_parametric_asset_library_benchmarks()
    assert suite["status"] == "ok"
    assert suite["all_receipts_verified"] is True


class ThreeJSWebGPUParametricAssetLibraryTests(unittest.TestCase):
    def test_all(self) -> None:
        test_120_generators_and_5_export_targets_compiler()
        test_catalog_and_compiler_slot_and_known_wrong_controls()
        test_head_to_head_benchmark_slot_and_known_wrong_controls()
        test_end_to_end_threejs_webgpu_asset_library_suite()


if __name__ == "__main__":
    unittest.main()
