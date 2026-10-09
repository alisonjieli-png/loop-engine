# Squash and stretch bounce for sprites

The vertex stage finds the pivot in the sprite's local pixels from the vertex position and its UV, so any offset or centring works. Vertices are scaled around that pivot: vertically by `1 + stretch`, horizontally by the inverse square root so the area stays roughly constant. The looping bounce stretches on the way up, squashes on landing and lifts the sprite with a hop; a fixed stretch lets a script drive impacts.

## When to use it

Use it for jumping characters, slimes, bouncing pickups, UI pop-ins and button presses.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_squash_stretch/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_squash_stretch/sprite_squash_stretch.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `amount` | float | hint_range(0.0, 0.8) | 0.22 | Largest squash or stretch as a share of the height. |
| `speed` | float | hint_range(0.0, 20.0) | 5.0 | Bounce speed in radians per second. |
| `pivot_u` | float | hint_range(0.0, 1.0) | 0.5 | Horizontal pivot in UV units (0.5 is the centre). |
| `pivot_v` | float | hint_range(0.0, 1.0) | 1.0 | Vertical pivot in UV units (1 is the bottom). |
| `use_fixed_stretch` | bool | none | false | Use `fixed_stretch` instead of the looping bounce. |
| `fixed_stretch` | float | hint_range(-0.8, 0.8) | 0.0 | Stretch set by a script: negative squashes, positive stretches. |
| `hop_height` | float | hint_range(0.0, 200.0) | 24.0 | Height of the hop in pixels during the looping bounce. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The disc squashed wide and flat against the ground line.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Scaling a four-vertex quad gives uniform squash, not a bulge. The hop moves only the drawing, not the node, so collision does not follow it.

## Technique

- Volume-preserving squash and stretch
- Pivot recovered from vertex position and UV
