# Wind sway for 2D plants and banners

The vertex stage measures how far each vertex is from the planted edge (`base_v`) in texture space and shifts it sideways by a sine sway plus a one-sided gust wave, both scaled by that distance raised to `stiffness`. The sway phase and the gust use the node's canvas position, so plants in a row ripple like grass in passing wind. On a plain Sprite2D only the corners move, which shears the top.

## When to use it

Use it for bushes, grass, flowers, hanging banners (set `base_v` to 0) and trees in 2D scenes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_wind_sway/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_wind_sway/sprite_wind_sway.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `strength` | float | hint_range(0.0, 64.0) | 14.0 | Sideways sway of the top in pixels. |
| `speed` | float | hint_range(0.0, 10.0) | 1.6 | Sway speed. |
| `gust_strength` | float | hint_range(0.0, 64.0) | 10.0 | Extra push of the travelling gust in pixels. |
| `gust_wavelength` | float | hint_range(50.0, 2000.0) | 600.0 | Distance between gusts in pixels. |
| `gust_speed` | float | hint_range(0.0, 1000.0) | 220.0 | Speed of the gust wave in pixels per second. |
| `stiffness` | float | hint_range(0.5, 4.0) | 1.5 | Exponent of the bend; higher keeps more of the lower part still. |
| `base_v` | float | hint_range(0.0, 1.0) | 1.0 | UV v of the planted edge (1 is the bottom of the texture). |

## Inputs

- Sprites whose planted edge is at the bottom (or set `base_v`).

## Output

Four plant sprites leaning and swaying at different phases above the ground.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A Sprite2D has four vertices, so it shears rather than curves; use a subdivided Polygon2D or MeshInstance2D for a curved bend. Large shears push the sprite beyond its bounding rectangle used for culling.

## Technique

- Vertex shear weighted by distance from a pinned edge
- Travelling one-sided sine gusts
- Phase from node position
