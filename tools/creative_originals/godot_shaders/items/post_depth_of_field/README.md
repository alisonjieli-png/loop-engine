# Depth of field with a golden-angle bokeh gather

For every pixel and every sample, the circle of confusion is the depth's distance outside the sharp zone, scaled to at most `max_blur_pixels`. Samples lie on a golden-angle (Vogel) spiral that fills a disc evenly. A sample contributes only if both the centre and the sample are blurred enough to reach each other, which keeps sharp objects from leaking into blurred backgrounds and blurred backgrounds from smearing over sharp edges.

## When to use it

Use it for cinematic focus, character close-ups, photo modes, miniature scenes and directing attention in cutscenes (animate the focus distance).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_depth_of_field/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_depth_of_field/post_depth_of_field.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `focus_distance` | float | hint_range(0.1, 100.0) | 2.4 | Distance in metres that is perfectly sharp. |
| `focus_range` | float | hint_range(0.0, 20.0) | 0.4 | Half-width in metres of the sharp zone around the focus distance. |
| `blur_falloff` | float | hint_range(0.1, 20.0) | 2.5 | Distance beyond the sharp zone over which blur reaches its maximum. |
| `max_blur_pixels` | float | hint_range(0.0, 32.0) | 9.0 | Largest blur radius in screen pixels. |
| `samples` | int | hint_range(4, 64) | 32 | Number of gather samples; more gives smoother bokeh. |
| `show_focus` | bool | none | false | Tint the in-focus zone red to tune the focus. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with the red sphere sharp and the far pillars and floor softly blurred.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A gather approximation: out-of-focus foreground cannot spread over in-focus objects behind it (no scatter). Each sample reads depth again, so the cost is twice the sample count in texture reads. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Circle of confusion from linear depth
- Golden-angle (Vogel) disc sampling
- Mutual radius weighting to limit bleeding
