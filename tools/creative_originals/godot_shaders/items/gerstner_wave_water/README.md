# Gerstner wave ocean surface

Each of three waves follows the Gerstner model: points move in circles, so crests sharpen and troughs flatten as `steepness` rises. The waves travel in directions spread around `direction_degrees`, with wavelengths of 1, 0.57 and 0.33 times `wavelength` and deep-water speeds from the dispersion relation. Positions use world X and Z so neighbouring tiles line up. Tangent and binormal derivatives are summed analytically to build the normal, and crest height mixes in a foam colour.

## When to use it

Use it for oceans, lakes and stylized seas seen from above the surface. Tile several planes with the same material for a larger sea; the waves line up across tiles.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/gerstner_wave_water/`. `material.tres` loads the shader from `res://baltor/godot_shaders/gerstner_wave_water/gerstner_wave_water.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `deep_color` | vec4 | source_color | (0.02, 0.1, 0.18, 1) | Water colour when looking straight down. |
| `shallow_color` | vec4 | source_color | (0.06, 0.38, 0.45, 1) | Water colour at grazing angles. |
| `crest_color` | vec4 | source_color | (0.8, 0.92, 0.95, 1) | Colour of foam on wave crests. |
| `amplitude` | float | hint_range(0.0, 2.0) | 0.22 | Height of the largest wave in metres. |
| `wavelength` | float | hint_range(0.5, 20.0) | 3.5 | Length of the largest wave in metres. |
| `steepness` | float | hint_range(0.0, 1.0) | 0.65 | Crest sharpness from 0 (sine waves) to 1 (looping limit). |
| `speed` | float | hint_range(0.0, 4.0) | 1.0 | Time scale of the wave motion. |
| `direction_degrees` | float | hint_range(0.0, 360.0) | 25.0 | Travel direction of the main wave around the Y axis. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.06 | Roughness of the water surface. |
| `crest_threshold` | float | hint_range(0.0, 1.0) | 0.55 | Normalized height where crest foam starts. |

## Inputs

- A subdivided PlaneMesh (or other flat grid); the demo uses 120 x 120 subdivisions.

## Output

A rolling sea with sharp crests, light foam on top and sun glints.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The plane must be dense enough for the shortest wave or the shape aliases. No transparency, refraction or depth fade (see `toon_water_foam` for depth-based shading). The CPU does not know the wave height, so floating objects need the same formula in a script.

## Technique

- Gerstner (trochoidal) waves with deep-water dispersion
- Analytic tangent and binormal sums for normals
- World-space wave phase for seamless tiling
