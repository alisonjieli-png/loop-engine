# Gooch cool to warm technical shading

A custom `light()` replaces the diffuse term with Gooch's blend: the light term `(1 + N.L) / 2` moves the colour from a cool tone (blue plus a share of the surface colour) to a warm tone (yellow plus a share of the surface colour). Shadowed sides stay readable because they turn blue instead of black. A Blinn-Phong highlight adds white specular, and the fragment stage darkens grazing angles to suggest silhouette lines.

## When to use it

Use it for technical drawings, product and part previews, educational 3D, and editors where shape must read from every side. Keep environment ambient light low; it is added on top unchanged.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/gooch_cool_warm/`. `material.tres` loads the shader from `res://baltor/godot_shaders/gooch_cool_warm/gooch_cool_warm.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `surface_color` | vec4 | source_color | (0.72, 0.66, 0.58, 1) | Object colour mixed into both tones. |
| `cool_color` | vec4 | source_color | (0.08, 0.16, 0.55, 1) | Tone for surfaces facing away from the light. |
| `warm_color` | vec4 | source_color | (0.62, 0.48, 0.08, 1) | Tone for surfaces facing the light. |
| `cool_mix` | float | hint_range(0.0, 1.0) | 0.25 | Share of the surface colour in the cool tone. |
| `warm_mix` | float | hint_range(0.0, 1.0) | 0.5 | Share of the surface colour in the warm tone. |
| `highlight_strength` | float | hint_range(0.0, 2.0) | 0.7 | Brightness of the specular highlight. |
| `shininess` | float | hint_range(1.0, 256.0) | 48.0 | Blinn-Phong exponent; higher gives a smaller highlight. |
| `edge_darkening` | float | hint_range(0.0, 1.0) | 0.7 | How dark the silhouette band becomes. |
| `edge_width` | float | hint_range(0.0, 0.6) | 0.22 | Facing ratio below which the silhouette band starts. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A mesh in blue to yellow shading with a white highlight and darkened outline band.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Non-photorealistic. Shadows from other objects are not darkened (Gooch shading ignores cast shadows except in the highlight); environment ambient light adds a uniform term. Edge darkening is a facing-ratio approximation: flat faces seen edge-on darken entirely.

## Technique

- Gooch cool-to-warm shading (Gooch et al. 1998)
- Blinn-Phong specular
- Facing-ratio silhouette darkening
