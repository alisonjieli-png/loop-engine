# Lift, gamma and gain colour grading

The image goes through a white balance multiply, then lift and gain (`gain * (c + lift * (1 - c))`, so lift affects shadows most and gain highlights most), then a per-channel power for gamma where 0.5 is neutral. Contrast pivots around middle grey, saturation scales the distance from luminance, and vibrance does the same but more for colours that are not already saturated.

## When to use it

Use it to set a scene's mood (teal shadows and warm highlights, cold night, sunny afternoon), to match lighting across levels, and for day-time grading changes driven by script.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_color_grading/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_color_grading/post_color_grading.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `lift` | vec4 | source_color | (0.04, 0.02, 0.08, 1) | Colour added to the shadows (black means none). |
| `gamma` | vec4 | source_color | (0.5, 0.5, 0.52, 1) | Midtone balance per channel; 0.5 is neutral, lower brightens that channel's midtones. |
| `gain` | vec4 | source_color | (1, 0.96, 0.88, 1) | Highlight multiplier per channel (white means none). |
| `contrast` | float | hint_range(0.5, 2.0) | 1.1 | Contrast around middle grey. |
| `saturation` | float | hint_range(0.0, 2.0) | 1.1 | Overall saturation. |
| `vibrance` | float | hint_range(-1.0, 1.0) | 0.2 | Saturation change weighted toward muted colours. |
| `temperature` | float | hint_range(-1.0, 1.0) | 0.15 | White balance: positive warms, negative cools. |
| `tint` | float | hint_range(-1.0, 1.0) | 0.0 | White balance: positive adds green, negative magenta. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with slightly purple shadows, warm highlights and a little more punch.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Grades display-referred colour after tonemapping, not scene-linear values, so extreme settings clip. No lookup table input; for LUT grading use Godot's colour correction texture. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Lift, gamma and gain grading
- Contrast around a pivot
- Saturation and vibrance
- Approximate white balance multipliers
