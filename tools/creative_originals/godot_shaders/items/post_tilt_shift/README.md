# Tilt-shift miniature effect

The blur radius depends only on the vertical screen distance from a sharp band, not on depth, which is what a tilted lens produces and why viewers read the scene as a small model. Sixteen samples on a golden-angle disc blur each pixel by that radius. Saturation and contrast are raised because miniature photos are usually bright and colourful.

## When to use it

Use it for city builders, strategy and management games, dioramas, top-down views and toy-like cinematics.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_tilt_shift/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_tilt_shift/post_tilt_shift.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `focus_center` | float | hint_range(0.0, 1.0) | 0.55 | Screen height of the sharp band (0 top, 1 bottom). |
| `focus_width` | float | hint_range(0.0, 0.8) | 0.12 | Half-height of the fully sharp band. |
| `blur_ramp` | float | hint_range(0.01, 1.0) | 0.3 | Screen distance over which blur grows to its maximum. |
| `max_blur_pixels` | float | hint_range(0.0, 24.0) | 8.0 | Largest blur radius in pixels. |
| `saturation` | float | hint_range(0.0, 2.0) | 1.35 | Saturation boost for the toy-like look. |
| `contrast` | float | hint_range(0.5, 2.0) | 1.1 | Contrast boost. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with a sharp middle band and blurred top and bottom, colours boosted like a toy model.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Blur ignores depth, so foreground objects crossing the sharp band stay sharp where they should not. Works best with high, tilted camera angles. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Screen-position based blur band
- Golden-angle disc blur
- Saturation and contrast boost
