# Interior mapping of fake rooms behind windows

UVs are divided into a grid of window cells. In each cell the view direction, converted to tangent space and scaled to the cell and `room_depth`, defines a ray from the window into a unit box behind the facade. The nearest of the three candidate planes (a side wall, the floor or ceiling, the back wall) is the visible surface; it gets wallpaper stripes, floor planks or a ceiling lamp. A hash per room picks a tint and whether the light is on, deeper hits are darker, and window frames are drawn over the cell borders. Room colour is emitted so lit windows glow at night.

## When to use it

Use it for city buildings, skyscraper facades, trains and ships with many windows where modelling rooms is too expensive.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/interior_mapping_rooms/`. `material.tres` loads the shader from `res://baltor/godot_shaders/interior_mapping_rooms/interior_mapping_rooms.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `rooms_across` | float | hint_range(1.0, 20.0) | 4.0 | Window cells per UV unit horizontally. |
| `rooms_down` | float | hint_range(1.0, 20.0) | 4.0 | Window cells per UV unit vertically. |
| `room_depth` | float | hint_range(0.1, 3.0) | 1.0 | Depth of each room relative to its width. |
| `wall_color` | vec4 | source_color | (0.78, 0.72, 0.62, 1) | Colour of room walls. |
| `floor_color` | vec4 | source_color | (0.42, 0.3, 0.2, 1) | Colour of room floors. |
| `ceiling_color` | vec4 | source_color | (0.92, 0.92, 0.9, 1) | Colour of room ceilings. |
| `frame_color` | vec4 | source_color | (0.16, 0.17, 0.2, 1) | Colour of the window frames. |
| `frame_width` | float | hint_range(0.0, 0.3) | 0.08 | Width of the frames in cell units. |
| `lights_on` | float | hint_range(0.0, 1.0) | 0.6 | Share of rooms with their light on. |
| `glass_reflection` | float | hint_range(0.0, 1.0) | 0.2 | Grey sky reflection added at grazing angles. |

## Inputs

- A flat facade mesh (quad or box side) with UVs and tangents; one UV unit spans the window grid.

## Output

A wall of windows, each showing a small room with walls, floor and ceiling that shift with the view.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Rooms are boxes without furniture; all rooms share one layout. The facade must be flat and its UVs unstretched, or rooms skew. Glass reflection is a fixed colour, not the environment.

## Technique

- Interior mapping by ray-box intersection in tangent space (van Dongen 2008)
- Per-cell hashed variation
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
