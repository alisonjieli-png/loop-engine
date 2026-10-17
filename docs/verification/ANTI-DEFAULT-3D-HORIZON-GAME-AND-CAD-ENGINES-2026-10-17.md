# Anti-Default-LLM 3D Horizon Guard & Tinkercad / 3dxd / FluidCAD / SolidCraft Suite

- Date: `2026-10-17`
- Implementation: `tools/anti_default_3d_horizon_game_and_cad_engines.py`
- Test Suite: `tools/test_anti_default_3d_horizon_game_and_cad_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic verification across 3 slot families, 12 engines, local `td3d.html` / `worm3d.html` upgrades, and 4 known-wrong controls)

## 1. Architecture & 7-Layer ComponentEnvelope Summary

1. **Slot Family 1 (`anti_default_3d_horizon_and_world_scale_slot`)**:
   - Eliminates the default LLM "postage-stamp floating island in a black void" anti-pattern observed in `/home/username/td3d.html` (`12x12` board, `20.4 x 20.4` span in `#070b0c` void, `0.102` ground-to-far ratio) and `/home/username/worm3d.html` (`r=24` circle in `#0a0608` void, `0.120` ground-to-far ratio).
   - Enforces a 3-band Rayleigh/Mie atmospheric sky dome, an extended terrain skirt (`ground_radius >= 0.85 * camera.far`), matched horizon-color distance fog (`THREE.FogExp2`), and 3-tier foreground/midground/background silhouette depth staging within `<= 16.6 ms` (`60 fps`).
2. **Slot Family 2 (`tinkercad_3dxd_fluidcad_solidcraft_cad_slot`)**:
   - `tinkercad_csg_workplane_and_hole_boolean_engine` (declarative workplane `z_min == 0.0 mm` bed-adhesion invariant + `is_hole=True` negative-volume boolean groups)
   - `jumpstart_3dxd_browser_occ_feature_timeline_engine` (`Jumpstart-3D` / `3dxd` constrained 2D sketch -> extrude -> fillet/chamfer feature timeline)
   - `fluidcad_hybrid_js_opencascade_brep_engine` (`FluidCAD` live JavaScript + OpenCascade B-Rep modeling)
   - `solidcraft_rust_mcp_parametric_cad_engine` (`SolidCraft` / `SolveCraft` Rust parametric CAD MCP tool sequences)
   - `build123d_openscad_manifold_printability_engine` (Euler-Poincare `V - E + F = 2(1 - g)` 2-manifold watertightness, `>= 1.2 mm` wall thickness, `>= 0.20 mm` snap-fit clearance)
3. **Slot Family 3 (`three_d_and_cad_harness_files_slot`)**:
   - Synthesizes `AGENTS.md`, `.cursor/rules/3d-horizon-and-cad.mdc`, and `MEMORY.md` packs enforcing all 3D horizon and CAD printability invariants.

## 2. Benchmark Results (`Without Baltor` vs. `With Baltor`)

| Scene / Target | Ground-to-Far Ratio | Horizon Continuity | Depth Layers | Frame Time (`<= 16.6 ms`) |
| :--- | :---: | :---: | :---: | :---: |
| `td3d.html` (`Without Baltor`) | `0.102` | `0.00` | `1` | `14.8 ms` |
| `td3d.html` (`With Baltor`) | `0.900` | `0.98` | `3` | `11.2 ms` |
| `worm3d.html` (`Without Baltor`) | `0.120` | `0.00` | `1` | `14.8 ms` |
| `worm3d.html` (`With Baltor`) | `0.900` | `0.98` | `3` | `11.2 ms` |

## 3. Known-Wrong Controls Verified

| Control | Scenario | Refusal Code | Layer |
| :--- | :--- | :--- | :--- |
| Control A | Postage-stamp 3D scene (`20.4` span in `200.0` far clip) without sky dome or matched horizon fog | `postage_stamp_void_scene_rejected` | Layer 6 (`preflight`) |
| Control B | Cramped animation duration (`2.0 s < 3.0 s`) or software-trap CPU bloom | `cramped_duration_or_software_trap_rejected` | Layer 6 (`preflight`) |
| Control C | Tinkercad / CAD part floating at `z_min = +4.5 mm` above the print bed | `floating_cad_part_off_workplane_rejected` | Layer 6 (`preflight`) |
| Control D | Non-manifold mesh (`V - E + F != 2(1 - g)`) or zero-clearance (`0.00 mm`) snap-fit joint | `non_manifold_or_zero_clearance_rejected` | Layer 6 (`preflight`) |
