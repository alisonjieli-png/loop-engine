# Topographic contour lines with elevation tints

World height divided by `interval` gives a coordinate whose integer crossings are contour lines; the distance to the nearest crossing divided by its screen-space derivative keeps every line `line_pixels` wide on flat and steep ground alike. Every `major_every` lines a thicker index contour is drawn. Height between `height_low` and `height_high` picks a hypsometric tint from green through sand to brown, optionally stepped into flat bands like a printed map.

## When to use it

Use it for map and strategy views, terrain editors, hiking and GIS visualization, height debugging and architectural site models.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/topographic_contours/`. `material.tres` loads the shader from `res://baltor/godot_shaders/topographic_contours/topographic_contours.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `interval` | float | hint_range(0.01, 50.0) | 0.1 | Height between contour lines in metres. |
| `major_every` | int | hint_range(1, 20) | 5 | Number of lines between thicker index contours. |
| `line_pixels` | float | hint_range(0.5, 4.0) | 1.0 | Width of minor lines in pixels. |
| `line_color` | vec4 | source_color | (0.35, 0.22, 0.12, 1) | Colour of the contour lines. |
| `height_low` | float | hint_range(-100.0, 100.0) | -0.5 | World height of the lowest tint. |
| `height_high` | float | hint_range(-100.0, 100.0) | 0.6 | World height of the highest tint. |
| `low_tint` | vec4 | source_color | (0.55, 0.75, 0.5, 1) | Tint of low ground. |
| `mid_tint` | vec4 | source_color | (0.9, 0.85, 0.6, 1) | Tint of middle heights. |
| `high_tint` | vec4 | source_color | (0.72, 0.55, 0.42, 1) | Tint of high ground. |
| `tint_steps` | int | hint_range(0, 32) | 8 | Number of flat tint bands; 0 gives a smooth gradient. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Hills shaded in green, sand and brown bands with brown contour rings that thicken every fifth line.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

On flat areas exactly at a contour height the line covers the whole surface. Lines on near-vertical walls bunch together. Heights are world Y, so the material must not move vertically to keep the map stable.

## Technique

- Derivative anti-aliased iso-lines of world height
- Hypsometric tinting with optional steps
