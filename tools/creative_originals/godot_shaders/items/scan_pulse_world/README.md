# Full-screen world scan pulse from depth

A full-screen pass reconstructs each pixel's view-space position from the depth buffer and converts it to world space with the inverse view matrix. The distance from that world point to the pulse centre is compared with a radius that grows with time and wraps every `pulse_period` seconds. A bright ring marks the wavefront; behind it a trail fades over `trail_length` metres and shows a world-aligned 3D grid. Pixels further than `max_distance` (the sky) are left alone.

## When to use it

Use it for scanner and sonar abilities, detective vision, area reveals, level transitions and sci-fi HUD effects that must touch every surface without changing materials.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/scan_pulse_world/`. `material.tres` loads the shader from `res://baltor/godot_shaders/scan_pulse_world/scan_pulse_world.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `pulse_color` | vec4 | source_color | (0.25, 1, 0.85, 1) | Colour of the ring, trail and grid. |
| `center_x` | float | hint_range(-50.0, 50.0) | 0.0 | World X of the pulse origin. |
| `center_y` | float | hint_range(-50.0, 50.0) | 0.0 | World Y of the pulse origin. |
| `center_z` | float | hint_range(-50.0, 50.0) | 0.0 | World Z of the pulse origin. |
| `pulse_speed` | float | hint_range(0.1, 50.0) | 4.0 | Ring expansion speed in metres per second. |
| `pulse_period` | float | hint_range(0.5, 20.0) | 3.0 | Seconds between pulses. |
| `ring_width` | float | hint_range(0.01, 2.0) | 0.15 | Width of the bright wavefront in metres. |
| `trail_length` | float | hint_range(0.0, 10.0) | 2.5 | Length of the fading trail behind the ring in metres. |
| `grid_size` | float | hint_range(0.05, 5.0) | 0.5 | Spacing of the grid shown in the trail. |
| `max_distance` | float | hint_range(1.0, 500.0) | 100.0 | Pixels further than this (in metres) are not scanned. |

## Inputs

- A world position for the pulse origin (set the three centre uniforms from a script).

## Output

The scene with a glowing cyan ring sweeping outward over floors and objects, leaving a gridded trail.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Only opaque geometry is in the depth buffer, so transparent objects are not scanned. The grid uses 3D world coordinates, so it shows lines on all faces. One pulse centre at a time.

## Technique

- World position reconstruction from depth with inverse projection and view matrices
- Distance-based expanding ring with trail
- Derivative anti-aliased 3D grid
