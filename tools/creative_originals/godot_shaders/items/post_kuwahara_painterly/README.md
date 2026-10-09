# Kuwahara painterly filter

Around every pixel, four square regions (upper left, upper right, lower left, lower right, each including the centre row and column) are sampled at once. For each region the mean colour and the variance are accumulated. The pixel takes the mean of the most uniform region, so it never averages across a strong edge: flat areas smooth into patches, edges stay sharp, and fine texture is replaced by painterly blobs.

## When to use it

Use it for painted, watercolour-like and storybook looks, dream sequences and stylized cutscenes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_kuwahara_painterly/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_kuwahara_painterly/post_kuwahara_painterly.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_nearest |  | The rendered scene behind the pass (filled by Godot). |
| `radius` | int | hint_range(1, 8) | 4 | Size of each square region in samples; larger gives broader strokes. |
| `sample_spacing` | float | hint_range(0.5, 3.0) | 1.0 | Distance between samples in pixels. |
| `saturation` | float | hint_range(0.0, 2.0) | 1.2 | Saturation adjustment of the result. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene smoothed into flat painterly patches with crisp boundaries between objects.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Cost is (2r + 1) squared samples per pixel: radius 4 reads 81 samples, radius 8 reads 289, which is heavy at high resolution. Square regions produce blocky artefacts at large radii (anisotropic variants avoid them). The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Kuwahara filter (four-quadrant minimum variance mean, Kuwahara et al. 1976)
