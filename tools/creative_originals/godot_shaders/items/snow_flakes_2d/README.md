# Drifting snowfall overlay

The rectangle is divided into cells that scroll down and sideways over time. A hash decides whether a cell holds a flake, where in the cell it sits and how large it is; its horizontal position also swings on a sine with its own speed. Three layers with smaller, slower and fainter flakes give depth. The rectangle stays transparent between flakes.

## When to use it

Use it for winter scenes, Christmas and seasonal UI, snowstorms (raise density and wind) and cosy backgrounds.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/snow_flakes_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/snow_flakes_2d/snow_flakes_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `snow_color` | vec4 | source_color | (1, 1, 1, 0.9) | Colour and opacity of the flakes. |
| `density` | float | hint_range(0.0, 1.0) | 0.55 | Share of cells holding a flake. |
| `fall_speed` | float | hint_range(0.0, 2.0) | 0.15 | Fall speed in rectangle heights per second. |
| `sway` | float | hint_range(0.0, 1.0) | 0.35 | Sideways sway of each flake. |
| `wind` | float | hint_range(-1.0, 1.0) | 0.1 | Constant sideways drift. |
| `flake_scale` | float | hint_range(4.0, 60.0) | 14.0 | Flake cells across the near layer. |
| `aspect` | float | hint_range(0.2, 5.0) | 1.0 | Width to height ratio of the rectangle. |

## Inputs

- A ColorRect above the scene covering the area that should show snow.

## Output

A city scene behind white snowflakes of three sizes drifting down.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Flakes are soft discs, not crystal shapes. Each flake is confined to its cell, so very large sway values clip at cell borders.

## Technique

- Scrolling hashed cells with per-flake sway
- Layered depth
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
