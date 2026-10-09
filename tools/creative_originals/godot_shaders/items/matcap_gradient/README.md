# Matcap shading with a procedural sphere texture

A matcap (material capture) is a picture of a lit sphere. The shader reflects the view direction about the normal in view space and maps the reflection onto the sphere picture, so every normal finds the colour the sphere has at the same orientation. Scene lights are ignored (`unshaded`). The material ships with a radial GradientTexture2D that imitates warm clay with an upper-left highlight; any square matcap image can replace it. A rim term and a derivative-based cavity term add a little shape.

## When to use it

Use it for sculpt and model previews, stylized characters that should look the same everywhere, inspection views and cheap mobile shading.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/matcap_gradient/`. `material.tres` loads the shader from `res://baltor/godot_shaders/matcap_gradient/matcap_gradient.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `matcap` | sampler2D | source_color, hint_default_white, filter_linear |  | Lit-sphere texture; the default is a procedural gradient, any matcap image works. |
| `tint` | vec4 | source_color | (1, 1, 1, 1) | Colour multiplied with the matcap. |
| `rim_strength` | float | hint_range(0.0, 2.0) | 0.25 | Brightness of the added edge light. |
| `rim_color` | vec4 | source_color | (1, 1, 1, 1) | Colour of the added edge light. |
| `cavity_strength` | float | hint_range(0.0, 1.0) | 0.3 | Darkening where the normal changes quickly between pixels. |

## Inputs

- Optional: a square matcap image assigned to `matcap` (the bundled material uses a procedural one).

## Output

Objects shaded like soft clay from the matcap colours, the same from every light setup.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Lighting is fixed to the view, so it turns with the camera and never casts or receives shadows. The cavity term only darkens where normals change within a pixel quad, which is subtle on smooth meshes. Matcaps with a visible horizon look wrong when the camera rolls.

## Technique

- Matcap (lit sphere) lookup from the view-space reflection vector
- Facing ratio rim
- Derivative cavity approximation
