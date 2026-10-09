# X-ray silhouette where an object is hidden

The material draws without a depth test, so the whole object reaches the fragment stage even where walls cover it. For each pixel it reads the opaque scene depth (the object writes no depth, so it is not in the buffer) and compares it with its own view depth. Where the object is in front, it outputs its normal lit albedo. Where it is behind, it outputs only emission in `xray_color`: a Fresnel rim plus a translucent fill with diagonal stripes, blended with alpha.

## When to use it

Use it for player characters, teammates, objectives and loot that must stay readable behind walls in third-person, strategy and tactics games.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/occlusion_silhouette_xray/`. `material.tres` loads the shader from `res://baltor/godot_shaders/occlusion_silhouette_xray/occlusion_silhouette_xray.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `albedo` | vec4 | source_color | (0.8, 0.45, 0.2, 1) | Colour of the visible part. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.6 | Roughness of the visible part. |
| `xray_color` | vec4 | source_color | (0.25, 0.75, 1, 1) | Colour of the hidden silhouette. |
| `xray_fill` | float | hint_range(0.0, 1.0) | 0.35 | Opacity of the silhouette interior. |
| `xray_rim_power` | float | hint_range(0.5, 8.0) | 2.0 | Exponent of the silhouette edge glow. |
| `depth_bias` | float | hint_range(0.0, 0.5) | 0.02 | Distance in metres a pixel must be behind geometry to count as hidden. |
| `pattern_density` | float | hint_range(0.0, 400.0) | 120.0 | Density of diagonal stripes in the silhouette. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A character whose exposed part is shaded normally and whose part behind the wall shows as a glowing blue outline with a striped fill.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Without a depth test the object does not sort against itself: concave meshes can show far parts over near ones, so it suits convex characters and props best. The object is drawn in the transparent pass, so it casts no shadow from this material and does not occlude other transparent objects.

## Technique

- Depth test disabled with per-pixel occlusion test against the depth buffer
- Fresnel rim silhouette with screen-space stripes
