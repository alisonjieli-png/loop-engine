# Ordered dithering to few colours or one bit

The 8 x 8 Bayer threshold is computed from the cell position by interleaving the bits of X and Y (the recursive Bayer construction), so no matrix table is needed. The screen is sampled once per `dot_scale` cell, contrast is adjusted, and each channel is quantized with the threshold added before flooring, which turns intermediate tones into regular dot patterns. In one-bit mode luminance is compared with the threshold and mapped to two colours.

## When to use it

Use it for one-bit and handheld-console looks, retro computer styles, newspaper-like rendering and as a deliberate texture in stylized games.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_bayer_dither/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_bayer_dither/post_bayer_dither.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `levels` | int | hint_range(2, 16) | 4 | Levels per channel in colour mode. |
| `dot_scale` | float | hint_range(1.0, 8.0) | 2.0 | Size of one dither cell in screen pixels. |
| `one_bit` | bool | none | false | Reduce to two colours by luminance instead of per-channel levels. |
| `dark_color` | vec4 | source_color | (0.1, 0.08, 0.16, 1) | Dark colour in one-bit mode. |
| `light_color` | vec4 | source_color | (0.92, 0.9, 0.8, 1) | Light colour in one-bit mode. |
| `contrast` | float | hint_range(0.5, 2.0) | 1.1 | Contrast applied before dithering. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene reduced to four levels per channel with a fine crosshatch-like dot pattern.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Ordered dithering shows a regular grid pattern by design. When the output is scaled by a non-integer factor the pattern beats into moire. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- 8 x 8 Bayer threshold from bit interleaving
- Ordered dithering quantization
- One-bit luminance dither
