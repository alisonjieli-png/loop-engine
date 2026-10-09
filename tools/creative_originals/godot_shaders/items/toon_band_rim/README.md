# Toon shading in bands with a rim light

A custom `light()` function replaces Godot's lighting with flat bands. The light term is a half-Lambert value multiplied by attenuation and shadow, cut into `bands` steps with an adjustable soft edge. Dark bands are tinted by `shadow_tint` instead of going black. A rim term from the angle between the normal and the view direction is added as specular light, so it keeps its own colour on any albedo, and `rim_light_bias` fades it on the side away from the light.

## When to use it

Use it for cartoon characters, stylized props and any scene where lighting should read as clear shapes. Combine it with `outline_inverted_hull` for an ink line.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/toon_band_rim/`. `material.tres` loads the shader from `res://baltor/godot_shaders/toon_band_rim/toon_band_rim.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `base_color` | vec4 | source_color | (0.32, 0.55, 0.85, 1) | Albedo of the surface. |
| `shadow_tint` | vec4 | source_color | (0.18, 0.16, 0.36, 1) | Colour the darkest band moves toward, multiplied by the light colour. |
| `bands` | int | hint_range(1, 8) | 3 | Number of flat light bands. |
| `band_softness` | float | hint_range(0.0, 0.3) | 0.04 | Width of the blend between bands, as a fraction of one band. |
| `rim_color` | vec4 | source_color | (1, 0.93, 0.78, 1) | Colour of the rim light. |
| `rim_width` | float | hint_range(0.0, 1.0) | 0.32 | How far the rim reaches in from the silhouette. |
| `rim_strength` | float | hint_range(0.0, 4.0) | 1.4 | Brightness of the rim. |
| `rim_light_bias` | float | hint_range(0.0, 1.0) | 0.65 | 0 keeps the rim all around the silhouette; 1 keeps it only on the lit side. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A mesh lit in flat colour bands with tinted shadows and a bright edge toward the light.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Stylized and not physically based. Each light adds its own bands, so several lights stack into extra steps. Ambient light from the environment is added unbanded. Band edges alias at grazing angles without multisample anti-aliasing.

## Technique

- Half-Lambert diffuse term
- Quantized lighting with a smoothstep band edge
- View-angle rim term (1 - N.V) masked by the light term
