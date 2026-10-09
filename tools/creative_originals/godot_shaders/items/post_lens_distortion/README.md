# Radial lens distortion with auto fit

Screen coordinates are centred and corrected for aspect, then scaled by `1 + k1 r^2 + k2 r^4`, the radial part of the Brown-Conrady lens model. With barrel distortion the corners would sample outside the screen, so `auto_fit` measures where the corner lands and zooms in to compensate. Anything still outside is black, and a gentle rim darkening imitates lens falloff.

## When to use it

Use it for fisheye and wide-angle camera looks, action cameras, security cameras, VR-like warps and impact punches (animate k1).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_lens_distortion/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_lens_distortion/post_lens_distortion.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `k1` | float | hint_range(-1.0, 1.0) | 0.22 | Second-order radial coefficient: positive gives barrel, negative pincushion. |
| `k2` | float | hint_range(-1.0, 1.0) | 0.06 | Fourth-order radial coefficient for stronger edge bending. |
| `auto_fit` | bool | none | true | Zoom in so barrel distortion leaves no empty corners. |
| `zoom` | float | hint_range(0.5, 2.0) | 1.0 | Extra zoom factor. |
| `edge_darkening` | float | hint_range(0.0, 1.0) | 0.3 | Darkening toward the corners. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene bulging outward with bent straight lines and slightly darker corners.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Sampling the already rendered frame loses resolution at the centre when zoomed. Tangential (decentring) distortion is not modelled. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Brown-Conrady radial distortion polynomial
- Automatic fit scale from the corner radius
