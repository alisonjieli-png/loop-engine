# Woven fabric with thread relief and sheen

UVs scaled by `threads` form a grid of crossings. In each cell either the warp or the weft thread is on top; plain weave alternates like a checker, twill shifts the pattern one cell per row to form diagonal ribs. The top thread is shaded as a rounded strand: a sine profile across it darkens its sides and a cosine slope tilts the normal map, so lights catch each thread. Gaps between threads are dark, value noise stretched along each thread adds fibres, and Godot's `RIM` output gives the cloth sheen.

## When to use it

Use it for clothes, upholstery, flags, sails, rugs and tablecloths seen up close, where a flat texture lacks thread detail.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/fabric_weave_sheen/`. `material.tres` loads the shader from `res://baltor/godot_shaders/fabric_weave_sheen/fabric_weave_sheen.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `warp_color` | vec4 | source_color | (0.22, 0.32, 0.55, 1) | Colour of the lengthwise threads. |
| `weft_color` | vec4 | source_color | (0.75, 0.72, 0.65, 1) | Colour of the crosswise threads. |
| `threads` | float | hint_range(4.0, 400.0) | 60.0 | Threads per UV unit. |
| `twill` | bool | none | true | Twill (diagonal ribs) when on, plain weave when off. |
| `thread_gap` | float | hint_range(0.0, 0.4) | 0.12 | Gap between neighbouring threads as a share of a cell. |
| `relief` | float | hint_range(0.0, 1.0) | 0.6 | Strength of the thread relief in the normal map. |
| `fuzz` | float | hint_range(0.0, 1.0) | 0.25 | Fibre noise along the threads. |
| `sheen` | float | hint_range(0.0, 1.0) | 0.6 | Rim sheen amount (Godot's RIM output). |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A mesh with UVs and tangents; thread size follows the UV scale.

## Output

A blue and cream twill cloth with visible rounded threads and diagonal ribs.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Threads alias into moire when they get smaller than a few pixels; lower `threads` for distant cloth. Relief is a normal map only. The rim sheen depends on renderer support for the RIM output.

## Technique

- Plain and twill weave from a cell over/under rule
- Rounded thread profile as a normal map
- Directional fibre noise
- RIM output for cloth sheen
