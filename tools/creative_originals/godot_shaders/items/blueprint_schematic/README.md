# Blueprint x-ray with dashed hidden lines

Contours come from the facing ratio: where the surface turns away from the viewer `N.V` drops and a line is drawn. Back faces are rendered too; their contours are hidden edges, so they are broken into screen-space dashes and drawn fainter, the drafting convention for hidden lines. Front faces get a graph paper grid from object-space coordinates with derivative anti-aliasing. The body is a translucent unshaded fill, so the result reads as a drawing whatever the lighting.

## When to use it

Use it for x-ray views, build or placement previews, technical overlays, schematic modes and highlighting hidden objects.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/blueprint_schematic/`. `material.tres` loads the shader from `res://baltor/godot_shaders/blueprint_schematic/blueprint_schematic.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `fill_color` | vec4 | source_color | (0.08, 0.26, 0.58, 0.25) | Colour and opacity of the translucent body. |
| `line_color` | vec4 | source_color | (0.9, 0.96, 1, 1) | Colour of contours and grid. |
| `contour_width` | float | hint_range(0.0, 0.6) | 0.25 | Facing ratio below which contour lines appear. |
| `dash_pixels` | float | hint_range(2.0, 40.0) | 10.0 | Length of the dashes on hidden contours, in pixels. |
| `hidden_opacity` | float | hint_range(0.0, 1.0) | 0.55 | Opacity of the dashed hidden contours. |
| `grid_size` | float | hint_range(0.01, 1.0) | 0.1 | Spacing of the graph paper grid in object units. |
| `grid_opacity` | float | hint_range(0.0, 1.0) | 0.25 | Opacity of the grid lines. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A transparent blue object drawn with white contour lines, dashed where they are behind the surface, over faint grid paper.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Contour lines come from the facing ratio, so flat faces seen edge-on fill completely and creases between flat faces are not drawn. Dashes run diagonally in screen space and do not follow the curve. Not sorted against other transparent objects.

## Technique

- Facing ratio contours
- Back-face rendering with screen-space dashes for hidden lines
- Derivative anti-aliased object-space grid
