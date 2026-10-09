# Active camouflage cloak with a reveal sweep

Height along the object (normalized by `object_height`, plus noise) is compared with a threshold set by `cloak`: below it the surface is cloaked, above it the normal material shows. Cloaked pixels output only emission: a copy of the scene behind, offset by the view-space normal and by drifting 3D noise so the outline shimmers, with a faint coloured rim. A bright seam marks the moving boundary. Animate `cloak` from 0 to 1 to vanish from the feet up.

## When to use it

Use it for stealth abilities, predator-style cloaking, teleport-in reveals and ghost effects on characters and vehicles.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/cloak_reveal/`. `material.tres` loads the shader from `res://baltor/godot_shaders/cloak_reveal/cloak_reveal.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | Copy of the scene behind the object (filled by Godot). |
| `albedo` | vec4 | source_color | (0.6, 0.62, 0.66, 1) | Colour of the visible part. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.5 | Roughness of the visible part. |
| `cloak` | float | hint_range(0.0, 1.0) | 0.55 | Progress from 0 (fully visible) to 1 (fully cloaked). |
| `object_height` | float | hint_range(0.1, 10.0) | 1.5 | Height of the mesh in object units, centred on its origin. |
| `distortion` | float | hint_range(0.0, 0.1) | 0.025 | Screen offset of the refraction and shimmer. |
| `shimmer_speed` | float | hint_range(0.0, 5.0) | 1.2 | Speed of the shimmer noise. |
| `edge_noise` | float | hint_range(0.0, 1.0) | 0.25 | Noise added to the reveal boundary. |
| `seam_color` | vec4 | source_color | (0.4, 0.9, 1, 1) | Colour of the boundary seam and rim. |
| `seam_width` | float | hint_range(0.0, 0.2) | 0.04 | Width of the seam in normalized height. |
| `rim_visibility` | float | hint_range(0.0, 1.0) | 0.3 | How much the outline shows while cloaked. |

## Inputs

- A mesh centred on its origin; set `object_height` to its height.

## Output

A capsule whose lower half has turned into a rippling see-through shape with a glowing seam above.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The cloaked part still writes depth and casts shadows; turn shadows off on the node while cloaked if needed. Screen-space refraction cannot show objects behind other transparent surfaces or off screen. The reveal runs along the object's Y axis only.

## Technique

- Screen texture refraction with animated noise offsets
- Noise-perturbed height threshold reveal
- Emission-only cloaked region
- Value noise with quintic interpolation and fractional Brownian motion
