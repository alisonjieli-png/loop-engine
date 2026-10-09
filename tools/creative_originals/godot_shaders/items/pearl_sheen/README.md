# Pearlescent sheen with orient colours

The body colour is multiplied by an orient tint that cycles through three colours as the facing ratio changes, so a sphere shows rings of pink, green and gold from centre to edge, the way nacre shifts. The tint is weaker where the surface faces the viewer. A satin roughness gives a broad soft highlight, a faint emissive core adds depth, and a cool rim brightens the silhouette.

## When to use it

Use it for pearls, shells, porcelain, lacquered toys, pearlescent plastics and decorative props.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/pearl_sheen/`. `material.tres` loads the shader from `res://baltor/godot_shaders/pearl_sheen/pearl_sheen.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `body_color` | vec4 | source_color | (0.93, 0.9, 0.86, 1) | Base colour of the pearl. |
| `tint_a` | vec4 | source_color | (1, 0.78, 0.86, 1) | First orient tint. |
| `tint_b` | vec4 | source_color | (0.78, 1, 0.88, 1) | Second orient tint. |
| `tint_c` | vec4 | source_color | (1, 0.92, 0.7, 1) | Third orient tint. |
| `orient_strength` | float | hint_range(0.0, 1.0) | 0.55 | How strongly the tints colour the body. |
| `orient_bands` | float | hint_range(0.5, 6.0) | 1.6 | How many times the tint cycle repeats from centre to edge. |
| `satin_roughness` | float | hint_range(0.0, 1.0) | 0.32 | Roughness of the highlight. |
| `inner_glow` | float | hint_range(0.0, 1.0) | 0.12 | Soft emissive glow toward the centre. |
| `rim_color` | vec4 | source_color | (0.75, 0.85, 1, 1) | Colour of the edge brightening. |
| `rim_strength` | float | hint_range(0.0, 1.0) | 0.25 | Brightness of the edge. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Creamy white spheres with soft pastel colour rings and a satin highlight.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

An artistic angle-based tint, not interference optics (see `thin_film_iridescence` for that). The colour rings are centred on the view, so they move with the camera. Emission keeps a glow even in darkness.

## Technique

- Facing-ratio driven three-colour tint cycle
- Satin highlight from moderate roughness
- Emissive core and rim
