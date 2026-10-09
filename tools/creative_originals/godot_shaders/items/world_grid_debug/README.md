# World-space prototyping grid

Grid coordinates are world positions divided by `cell_size`, taken from the plane perpendicular to the dominant axis of the world normal, so floors use X and Z and walls use the matching vertical plane. Line coverage is the distance to the nearest grid line divided by its screen-space derivative, which keeps lines `line_pixels` wide at any distance without aliasing. Every `major_every` cells a thicker line is drawn; on floors the X and Z axes through the origin are tinted red and blue.

## When to use it

Use it on blockout geometry, test levels and editor tools where scale and alignment must be readable at a glance.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/world_grid_debug/`. `material.tres` loads the shader from `res://baltor/godot_shaders/world_grid_debug/world_grid_debug.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `base_color` | vec4 | source_color | (0.32, 0.34, 0.38, 1) | Fill colour between lines. |
| `minor_color` | vec4 | source_color | (0.48, 0.5, 0.55, 1) | Colour of the minor grid lines. |
| `major_color` | vec4 | source_color | (0.82, 0.84, 0.88, 1) | Colour of the major grid lines. |
| `cell_size` | float | hint_range(0.05, 10.0) | 0.5 | Size of one grid cell in world units. |
| `major_every` | int | hint_range(1, 20) | 4 | Number of cells between major lines. |
| `line_pixels` | float | hint_range(0.5, 4.0) | 1.2 | Width of the minor lines in pixels. |
| `show_axes` | bool | none | true | Tint the world X and Z axis lines on horizontal surfaces. |
| `fade_distance` | float | hint_range(1.0, 200.0) | 40.0 | Distance in metres at which the lines have faded out. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.8 | Surface roughness. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Grey surfaces with crisp light grid lines, heavier every few cells, and red and blue axis lines on the floor.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Sloped surfaces snap to the nearest axis plane, so lines stretch on 45 degree slopes. The grid is fixed in world space and slides across moving objects. Lines thinner than one pixel fade instead of vanishing.

## Technique

- Screen-space derivative (fwidth) line anti-aliasing
- Dominant-axis planar projection
