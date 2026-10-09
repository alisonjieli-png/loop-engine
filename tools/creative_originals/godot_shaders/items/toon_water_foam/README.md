# Toon water with depth bands and contact foam

The water is a transparent unshaded surface that writes no depth. For each pixel the shader reconstructs the depth of the opaque scene behind it and subtracts the water's own depth, giving the water thickness along the view ray. That thickness is cut into `color_steps` flat colours between `shallow_color` and `deep_color` (alpha included, so shallow water shows more of the bed). Where the thickness is below a noise-wobbled `foam_distance`, a hard foam band appears, which outlines rocks, shores and anything floating. Thin contour lines of a drifting fBm field add ripples.

## When to use it

Use it for stylized lakes, rivers, ponds and coasts where shorelines and objects should get foam outlines without hand-placed decals.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/toon_water_foam/`. `material.tres` loads the shader from `res://baltor/godot_shaders/toon_water_foam/toon_water_foam.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `shallow_color` | vec4 | source_color | (0.38, 0.86, 0.85, 0.7) | Colour and opacity of the shallowest step. |
| `deep_color` | vec4 | source_color | (0.05, 0.32, 0.55, 0.95) | Colour and opacity of the deepest step. |
| `depth_range` | float | hint_range(0.05, 5.0) | 1.0 | Water thickness in metres that reaches the deep colour. |
| `color_steps` | int | hint_range(1, 8) | 3 | Number of flat colour steps between shallow and deep. |
| `foam_color` | vec4 | source_color | (1, 1, 1, 1) | Colour and opacity of foam and ripple lines. |
| `foam_distance` | float | hint_range(0.0, 1.0) | 0.18 | Water thickness in metres below which foam appears. |
| `foam_noise_scale` | float | hint_range(1.0, 40.0) | 9.0 | Frequency of the noise that breaks up the foam edge. |
| `foam_speed` | float | hint_range(0.0, 2.0) | 0.25 | Drift speed of the foam noise. |
| `ripple_amount` | float | hint_range(0.0, 1.0) | 0.35 | Opacity of the ripple lines; 0 removes them. |
| `ripple_scale` | float | hint_range(0.5, 20.0) | 3.0 | Frequency of the ripple pattern. |

## Inputs

- Opaque terrain or objects below and through the water surface.

## Output

Banded turquoise water with white foam rings around rocks and along the shallows.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Thickness is measured along the view ray, not vertically, so it grows at grazing angles. Transparent objects are not in the depth buffer and get no foam. Unshaded: the sun does not light the water. Flat surface; combine with a vertex wave shader for motion.

## Technique

- Depth buffer water thickness
- Quantized colour steps
- Noise-perturbed contact foam
- Value noise with quintic interpolation and fractional Brownian motion
