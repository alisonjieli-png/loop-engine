# Demoscene tunnel from polar coordinates

For each pixel the angle around the vanishing point gives the position around the tunnel wall and the inverse of the distance gives the depth along it, the perspective mapping of a cylinder seen from inside. Adding time to the depth moves the wall toward the viewer. The wall coordinate picks a checker of `segments` by `depth_rings`, optionally twisted with depth, and an exponential fade darkens the far end. The centre drifts slightly for a sense of motion.

## When to use it

Use it for warp and hyperspace sequences, retro intros, loading screens, rhythm game backgrounds and portal interiors.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/tunnel_polar_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/tunnel_polar_2d/tunnel_polar_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `color_a` | vec4 | source_color | (0.95, 0.4, 0.2, 1) | First wall colour. |
| `color_b` | vec4 | source_color | (0.15, 0.1, 0.35, 1) | Second wall colour. |
| `speed` | float | hint_range(-4.0, 4.0) | 1.2 | Speed of travel into the tunnel. |
| `twist` | float | hint_range(-2.0, 2.0) | 0.3 | Rotation of the pattern with depth. |
| `segments` | int | hint_range(2, 32) | 12 | Number of checker segments around the wall. |
| `depth_rings` | float | hint_range(1.0, 20.0) | 6.0 | Checker rings per unit of depth. |
| `fog` | float | hint_range(0.0, 4.0) | 1.4 | Darkening toward the vanishing point. |
| `center_x` | float | hint_range(-0.5, 0.5) | 0.0 | Horizontal offset of the vanishing point. |
| `center_y` | float | hint_range(-0.5, 0.5) | 0.0 | Vertical offset of the vanishing point. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

An orange and purple checkered tunnel rushing toward the viewer into darkness.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The pattern pinches at the vanishing point; the fade hides it. Checkers alias near the centre without mipmapped textures.

## Technique

- Polar to tunnel mapping (angle and inverse radius)
- Scrolling checker texture coordinates
