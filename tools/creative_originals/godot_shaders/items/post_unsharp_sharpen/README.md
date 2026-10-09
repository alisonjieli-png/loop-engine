# Unsharp mask sharpening

A 3 x 3 binomial (approximately Gaussian) blur is built from nine samples spaced `radius_pixels` apart. The difference between the centre and the blur is the fine detail; adding it back scaled by `amount` steepens edges. A smooth threshold suppresses the effect where the detail is tiny, so noise and gradients stay clean, and luminance-only mode adds the same detail to all channels to avoid coloured halos.

## When to use it

Use it to restore crispness after upscaling, TAA or FXAA, to give a stylized crisp look, or to make UI-like 3D text readable.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_unsharp_sharpen/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_unsharp_sharpen/post_unsharp_sharpen.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_nearest |  | The rendered scene behind the pass (filled by Godot). |
| `amount` | float | hint_range(0.0, 3.0) | 1.2 | How much detail is added back. |
| `radius_pixels` | float | hint_range(0.5, 4.0) | 1.0 | Distance of the blur samples in pixels; larger sharpens coarser detail. |
| `threshold` | float | hint_range(0.0, 0.2) | 0.01 | Detail smaller than this is left alone. |
| `luminance_only` | bool | none | true | Sharpen brightness only, which avoids colour fringes. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with crisper edges and slightly stronger texture.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Over-sharpening creates bright and dark halos along edges. Sharpening also enhances aliasing and noise above the threshold. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Unsharp masking with a 3 x 3 binomial blur
- Detail threshold
- Luminance-only detail
