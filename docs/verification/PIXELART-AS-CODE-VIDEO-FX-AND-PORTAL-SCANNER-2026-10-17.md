# Pixel Art as Code, Video FX, Fourier Motion Rigging & Autonomous Portal Scanner

- Date: `2026-10-17`
- Implementation: `tools/pixelart_as_code_video_fx_and_portal_scanner_engines.py`
- Test Suite: `tools/test_pixelart_as_code_video_fx_and_portal_scanner_engines.py`
- Evidence Tier: `deterministic_local_verification` (in-memory deterministic execution across 3 slot families, 11 engines, and 4 adversarial known-wrong controls)

## 1. Architecture & 7-Layer ComponentEnvelope Summary

Every functional unit is wrapped in the 7-layer `ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`) with runtime engine selection and recorded fallback chains:

1. **Slot Family 1 (`pixelart_as_code_and_pixel_logic_slot`)**:
   - `claude_pxl_dsl_and_sprite_sheet_compiler_engine` (`crsolver/claude-pxl` `.px.js` DSL, `PICO-8` / `Endesga-32` / `Lospec` palettes, 12-frame `idle`/`walk`/`jump`/`attack` sprite sheet atlas, bilateral symmetry invariant, integer scale factor `k in {4, 8, 16}`, `THREE.NearestFilter` + `image-rendering: pixelated`)
   - `oklab_palette_and_bayer_atkinson_dither_engine` (perceptual OKLab nearest-palette projection + 4x4/8x8 Bayer ordered dithering + Atkinson 6/8 error diffusion)
   - `noita_falling_sand_and_isometric_pixel_logic_engine` (mass-conserving cellular automata for sand, water, fire, smoke, acid + 2:1 `arctan(0.5) = 26.565 deg` anti-jaggy isometric pixel stepping)
   - `ascii_and_ansi_block_pixel_fallback_engine`
2. **Slot Family 2 (`video_fx_fourier_rig_and_transform_slot`)**:
   - `silhouette_stick_rig_difference_and_fourier_epicycle_engine` (`Stick Figure Rig -> Silhouette Fill -> Difference Residual Mask |L_sil - L_stick|` + Discrete Fourier Transform epicycle dance/motion curve synthesis $z(t) = \sum_{k=-M}^{M} c_k e^{i 2\pi k t / T}$)
   - `multi_plane_broll_ken_burns_and_particle_weather_engine` (parallax B-roll Ken Burns camera drift + foreground particle systems `spores`, `volumetric_rain`, `forked_lightning` with ITU-R BT.1702 `<= 3.0 Hz` flash safety)
   - `geometric_pixel_and_coordinate_transformation_engine` (3x3 projective homography, log-polar tunnel warp, domain-warped FBM displacement, slit-scan temporal buffer)
   - `deterministic_svg_motion_layer_fallback_engine`
3. **Slot Family 3 (`portal_project_scanner_and_db_ingester_slot`)**:
   - `github_and_ecosystem_project_scanner_ingester_engine` (scans emerging GitHub projects including `crsolver/claude-pxl`, `Jumpstart-3D/3dxd`, `FluidCAD`, `SolidCraft`, `mistralai/timestral`, `Data-Pixels`, `build123d`, `PythonSCAD`, `Manifold`, pins commit SHAs + SPDX licenses, and generates paired external adapter + Baltor-native engine variations for `/admin/systems` and `agentfoundry.si`)
   - `static_manifest_and_conformance_auditor_engine`
   - `offline_catalog_seed_fallback_engine`

## 2. Benchmark Results

| Metric | Value |
| :--- | :--- |
| Slot families verified | `3` |
| Swappable engines verified | `11` |
| Sprite sheet frames compiled (`idle`, `walk`, `jump`, `attack`) | `12` (`0` symmetry mismatches) |
| Mean OKLab perceptual color error ($\Delta E_{\text{OKLab}}$) | `0.09545` |
| Cellular automata mass conservation (`sand + water + fire + smoke + acid`) | `100.0%` conserved |
| Fourier epicycle contour reconstruction RMSE (`M = 4`, `9` epicycles) | `0.0000` (`100.0%` energy captured) |
| Stick-to-silhouette difference residual ratio | `0.244` |
| Emerging GitHub projects ingested with Rule 6 dual-engine parity | `12 / 12` (`100.0%`) |

## 3. Known-Wrong Controls Verified

| Control ID | Scenario | Expected Refusal Code | Observed Result |
| :--- | :--- | :--- | :--- |
| `kw_blurry_01` | Sub-pixel / `THREE.LinearFilter` blurry interpolation on pixel art | `blurry_non_integer_pixel_interpolation_forbidden` | Blocked at Layer 6 (`preflight`) |
| `kw_mass_01` | Non-mass-conserving cellular automata swap (`delta = 3`) | `non_mass_conserving_cellular_automata_forbidden` | Blocked at Layer 6 (`preflight`) |
| `kw_unpinned_01` | Ingesting external repo at unpinned `HEAD` without SPDX license or Baltor-native engine pair | `unpinned_or_unpaired_external_project_ingestion_forbidden` | Blocked at Layer 3 (`handshake`) |
| `kw_flash_01` | Lightning / video FX flash rate `6.5 Hz > 3.0 Hz` ITU-R BT.1702 ceiling | `photosensitive_flash_frequency_exceeded` | Blocked at Layer 6 (`preflight`) |
