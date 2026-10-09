# Scrolling neon grid floor

Grid coordinates come from world X and Z divided by `cell_size`, with Z offset by time so the floor appears to move toward the viewer. Each line is drawn twice: a crisp core `line_pixels` wide using screen-space derivatives, and a wider soft halo from the distance in cell units. The line colour blends from `near_color` to `far_color` with camera distance, and the far floor fades into `haze_color` to meet the sky.

## When to use it

Use it for synthwave and retro-futuristic scenes, title screens, music visualizers and arcade racers.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/neon_grid_floor/`. `material.tres` loads the shader from `res://baltor/godot_shaders/neon_grid_floor/neon_grid_floor.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `near_color` | vec4 | source_color | (1, 0.2, 0.75, 1) | Line colour near the camera. |
| `far_color` | vec4 | source_color | (0.2, 0.8, 1, 1) | Line colour far away. |
| `floor_color` | vec4 | source_color | (0.03, 0, 0.06, 1) | Colour between the lines. |
| `haze_color` | vec4 | source_color | (0.35, 0.05, 0.4, 1) | Colour the far floor fades into. |
| `cell_size` | float | hint_range(0.1, 10.0) | 1.0 | Grid cell size in world units. |
| `line_pixels` | float | hint_range(0.5, 6.0) | 1.5 | Width of the crisp line core in pixels. |
| `glow_width` | float | hint_range(0.0, 0.5) | 0.12 | Width of the soft halo in cell units. |
| `scroll_speed` | float | hint_range(-10.0, 10.0) | 1.5 | Scroll speed in cells per second. |
| `haze_distance` | float | hint_range(1.0, 200.0) | 40.0 | Distance in metres where the haze is complete. |
| `intensity` | float | hint_range(0.0, 4.0) | 1.6 | Brightness of the lines. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A dark purple floor ruled with pink lines that turn cyan toward a hazy horizon and scroll forward.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The halo is in world units, so it thins on screen with distance while the core stays pixel sized. Unshaded: no reflections of the lines. Very distant lines merge into haze rather than moire only because of the fade.

## Technique

- Derivative anti-aliased grid lines
- Distance-based colour and haze blend
- Scrolling world-space coordinates
