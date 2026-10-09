# Parallax starfield with twinkling layers

Three layers use grids of different sizes. In each layer a hash decides whether a cell holds a star and where it sits; the distance to it gives a soft dot. Larger cells (bigger, brighter stars) scroll slowest and small cells fastest, which reads as depth. Each star twinkles at its own rate and gets a colour between blue and warm white. A faint fBm haze tints the background.

## When to use it

Use it for space backgrounds, title screens, shooter backdrops, night skies in 2D and loading screens.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/starfield_parallax_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/starfield_parallax_2d/starfield_parallax_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `space_color` | vec4 | source_color | (0.01, 0.01, 0.04, 1) | Background colour of space. |
| `nebula_tint` | vec4 | source_color | (0.12, 0.05, 0.2, 1) | Colour of the faint nebula haze. |
| `density` | float | hint_range(0.0, 1.0) | 0.45 | Share of cells that hold a star. |
| `scroll_speed` | float | hint_range(-2.0, 2.0) | 0.05 | Scroll speed of the nearest layer in UV units per second. |
| `scroll_angle_degrees` | float | hint_range(0.0, 360.0) | 200.0 | Scroll direction. |
| `twinkle_speed` | float | hint_range(0.0, 10.0) | 3.0 | Twinkle frequency. |
| `star_scale` | float | hint_range(10.0, 200.0) | 60.0 | Cells per UV unit of the middle layer. |
| `brightness` | float | hint_range(0.0, 3.0) | 1.3 | Overall brightness. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A dark purple space with many small blue and warm stars at three sizes.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Stars are placed per grid cell, so their density is regular at large scales. Very fast scrolling streaks nothing; it only translates the layers.

## Technique

- Hashed per-cell star placement
- Multi-layer parallax scrolling
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
