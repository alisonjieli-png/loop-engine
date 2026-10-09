# Posterize in perceptual steps

Each channel (or the luminance) is raised to `1 / gamma`, scaled to `levels - 1` steps, rounded and mapped back through the same curve, so the steps can be biased toward shadows or highlights. In luminance-only mode the colour is scaled to the quantized brightness, which keeps hues smooth while tones band. A small softness turns hard steps into short ramps.

## When to use it

Use it for comic and poster looks, pop art, cel-like full-screen stylization and low-colour retro grading.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_posterize_gamma/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_posterize_gamma/post_posterize_gamma.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `levels` | int | hint_range(2, 32) | 5 | Number of tone levels per channel. |
| `gamma` | float | hint_range(0.3, 3.0) | 1.0 | Curve applied before quantizing; values above 1 add steps in the darks. |
| `luminance_only` | bool | none | false | Quantize only brightness and keep the hue continuous. |
| `edge_softness` | float | hint_range(0.0, 0.5) | 0.0 | Softens the jump between levels (0 is hard). |
| `saturation` | float | hint_range(0.0, 2.0) | 1.15 | Saturation adjustment before quantizing. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene flattened into five crisp tone steps per channel with slightly boosted saturation.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Smooth gradients such as the sky turn into visible bands by design. Per-channel quantizing can shift hues in dark areas. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Gamma-biased quantization
- Luminance-only posterization by rescaling
