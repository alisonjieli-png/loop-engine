# Flowing lava from domain-warped noise

The heat field is fractional Brownian motion sampled at coordinates that are themselves offset by two layers of fBm (domain warping), which folds the pattern into swirls and streaks like flowing rock. The inner layer is offset by `TIME`, so the swirls churn while the whole field scrolls along `flow_angle_degrees`. Low heat becomes rough dark crust, high heat becomes emissive molten colour that brightens toward `lava_bright`.

## When to use it

Use it for lava lakes, magma rivers, volcanic planets and hot metal; it maps on any mesh with UVs.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/lava_domain_warp/`. `material.tres` loads the shader from `res://baltor/godot_shaders/lava_domain_warp/lava_domain_warp.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `crust_color` | vec4 | source_color | (0.07, 0.05, 0.05, 1) | Colour of the cooled crust. |
| `lava_dark` | vec4 | source_color | (0.62, 0.07, 0.02, 1) | Colour of cooler molten areas. |
| `lava_bright` | vec4 | source_color | (1, 0.66, 0.16, 1) | Colour of the hottest molten areas. |
| `scale` | float | hint_range(0.5, 20.0) | 3.0 | Pattern frequency across the UV range. |
| `flow_speed` | float | hint_range(0.0, 2.0) | 0.12 | Scroll speed of the whole field in UV units per second. |
| `flow_angle_degrees` | float | hint_range(0.0, 360.0) | 20.0 | Scroll direction in UV space. |
| `warp_strength` | float | hint_range(0.0, 4.0) | 1.8 | Amount of domain warping; 0 gives plain fBm. |
| `crust_amount` | float | hint_range(0.0, 1.0) | 0.5 | Share of the surface covered by crust. |
| `crust_edge` | float | hint_range(0.01, 0.3) | 0.06 | Softness of the crust border. |
| `emission_strength` | float | hint_range(0.0, 10.0) | 3.0 | Brightness of the molten glow. |

## Inputs

- A mesh with UV coordinates.

## Output

Black crust plates drifting over swirling orange glowing lava.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Twelve fBm evaluations of four octaves per pixel make it one of the heavier shaders here; lower octaves for mobile. Flat: no displacement or normal relief. UV seams show where the mesh UVs are discontinuous.

## Technique

- Domain warping of fractional Brownian motion (warp of a warp)
- Value noise with quintic interpolation and fractional Brownian motion
- Threshold crust mask with smoothstep
