# Colour vision deficiency simulation

The scene colour is converted from sRGB to linear light, multiplied by a 3 x 3 simulation matrix for the selected deficiency, blended with the original by `severity`, and converted back. The dichromacy matrices are the published full-severity values of Machado, Oliveira and Fernandes (2009); achromatopsia uses Rec. 709 luminance. A split view keeps the left half unchanged for side-by-side checks.

## When to use it

Use it during development to test user interfaces, team colours, heat maps, puzzles and status indicators for colour-blind accessibility, and as an accessibility preview option in settings menus.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_color_blindness/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_color_blindness/post_color_blindness.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `mode` | int | hint_range(0, 3) | 1 | 0 protanopia (no red cones), 1 deuteranopia (no green cones), 2 tritanopia (no blue cones), 3 achromatopsia (no colour). |
| `severity` | float | hint_range(0.0, 1.0) | 1.0 | Blend from normal vision (0) to the full deficiency (1). |
| `split_view` | bool | none | false | Show unmodified colours on the left half for comparison. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene as seen with deuteranopia: reds and greens collapse toward ochre and olive while blues remain.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A simulation for testing, not a correction filter, and only for typical dichromacy. Individual vision varies. The pass assumes the screen texture holds sRGB-encoded colour. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Machado et al. 2009 colour vision deficiency matrices
- sRGB to linear conversion
- Rec. 709 luminance for achromatopsia
