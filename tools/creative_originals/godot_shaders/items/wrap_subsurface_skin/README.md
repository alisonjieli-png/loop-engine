# Wrap lighting with subsurface tint and back light

Wrap lighting shifts the Lambert term by `wrap` so light reaches past the 90 degree terminator. The difference between the wrapped and the plain term is the band where light would have scattered under the surface; that band is tinted with `scatter_color`, which gives the red terminator of skin. A translucency term compares the view direction with the light direction bent by the normal, so thin parts glow when lit from behind. A soft Blinn-Phong highlight finishes it.

## When to use it

Use it for stylized and semi-realistic skin, wax, candles, soap, fruit, leaves and marble statues lit from the side or behind.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/wrap_subsurface_skin/`. `material.tres` loads the shader from `res://baltor/godot_shaders/wrap_subsurface_skin/wrap_subsurface_skin.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.88, 0.68, 0.58, 1) | Surface colour. |
| `scatter_color` | vec4 | source_color | (0.85, 0.2, 0.12, 1) | Colour of light scattered under the surface. |
| `wrap` | float | hint_range(0.0, 1.0) | 0.45 | How far light wraps past the terminator (0 is plain Lambert). |
| `scatter_width` | float | hint_range(0.0, 1.0) | 0.35 | How quickly the scatter tint ramps in within the wrap band. |
| `translucency` | float | hint_range(0.0, 2.0) | 0.6 | Strength of the light seen through thin parts. |
| `translucency_power` | float | hint_range(1.0, 16.0) | 4.0 | Tightness of the back light around the light direction. |
| `translucency_distortion` | float | hint_range(0.0, 1.0) | 0.25 | How much the normal bends the back light direction. |
| `specular_strength` | float | hint_range(0.0, 1.0) | 0.25 | Brightness of the highlight. |
| `specular_power` | float | hint_range(2.0, 128.0) | 24.0 | Blinn-Phong exponent of the highlight. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Peach-coloured shapes lit from behind and the side with a warm red glow along the shadow edge and through the thin capsule.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

An approximation without real thickness: translucency is the same on thick and thin parts unless you scale it per object. Wrap lighting brightens shadowed regions, so cast shadows look softer than the light. Not energy conserving.

## Technique

- Wrap lighting ((N.L + w) / (1 + w))
- Terminator scatter band tint
- View and light direction translucency with normal distortion
- Blinn-Phong specular
