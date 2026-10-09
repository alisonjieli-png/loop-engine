# Layered rain streaks overlay

Coordinates are sheared by `slant` so rain falls at an angle, then split into thin columns. In each column a hash sets a phase, a speed variation and whether it rains at all; a sawtooth of time gives a streak with a bright head and a fading tail. Three layers with wider spacing, slower speed and lower opacity sit behind the near one for depth. The rectangle is transparent except for the streaks.

## When to use it

Use it over 2D scenes, parallax backgrounds and UI for rainy weather; combine with `post_film_grain` or a dark tint for storms.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/rain_streaks_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/rain_streaks_2d/rain_streaks_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `rain_color` | vec4 | source_color | (0.75, 0.82, 0.95, 0.55) | Colour and opacity of the rain. |
| `density` | float | hint_range(0.0, 1.0) | 0.5 | Share of columns carrying rain. |
| `speed` | float | hint_range(0.0, 5.0) | 1.6 | Fall speed. |
| `slant` | float | hint_range(-1.0, 1.0) | 0.25 | Horizontal slant of the streaks (wind). |
| `streak_length` | float | hint_range(0.02, 0.5) | 0.12 | Length of a streak in rectangle heights. |
| `columns` | float | hint_range(10.0, 300.0) | 90.0 | Number of rain columns across the near layer. |
| `aspect` | float | hint_range(0.2, 5.0) | 1.0 | Width to height ratio of the rectangle, so streaks keep their shape. |

## Inputs

- A ColorRect above the scene covering the area that should show rain.

## Output

A city scene behind fine slanted streaks of rain in three depths.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Streaks pass in front of everything in the rectangle; there are no splashes (see `particles_rain_splash`). Set `aspect` to the rectangle's width over height.

## Technique

- Column-based hashed streaks
- Sheared coordinates for slanted rain
- Layered parallax
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
