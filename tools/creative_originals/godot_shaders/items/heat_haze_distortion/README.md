# Heat haze distortion card

The card draws after the opaque scene and shows a copy of what is behind it, displaced by a two-channel value noise field that scrolls upward over the card's UVs. The displacement is masked so it fades at the card's sides and bottom, weakens toward the top (`top_fade`, UV v is 0 at the top) and falls off with distance from the camera. A faint warm tint can be added inside the mask.

## When to use it

Use it above fires, engines, exhausts, hot roads, lava and desert horizons. Face the card toward the camera (or make it a billboard) for best results.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/heat_haze_distortion/`. `material.tres` loads the shader from `res://baltor/godot_shaders/heat_haze_distortion/heat_haze_distortion.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | Copy of the opaque scene behind the card (filled by Godot). |
| `strength` | float | hint_range(0.0, 0.1) | 0.018 | Largest screen-space offset. |
| `noise_scale` | float | hint_range(1.0, 40.0) | 9.0 | Frequency of the distortion noise across the card. |
| `rise_speed` | float | hint_range(0.0, 5.0) | 1.4 | Upward scroll speed of the noise. |
| `edge_softness` | float | hint_range(0.01, 0.5) | 0.25 | Width of the fade at the card edges in UV units. |
| `top_fade` | float | hint_range(0.0, 1.0) | 0.6 | How much the effect weakens toward the top of the card. |
| `distance_falloff` | float | hint_range(0.0, 1.0) | 0.15 | How quickly the effect weakens with camera distance. |
| `tint_amount` | float | hint_range(0.0, 0.3) | 0.04 | Warm tint added inside the distortion. |

## Inputs

- A QuadMesh or other card placed over the hot area.

## Output

A shimmering patch where the scene behind ripples upward.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Screen-space: it cannot show what is off screen and cannot distort other transparent objects. A card seen edge-on disappears. The distortion is an artistic noise field, not a refraction calculation.

## Technique

- Screen texture offset by scrolling value noise
- UV and distance based effect masks
- Value noise with quintic interpolation and fractional Brownian motion
