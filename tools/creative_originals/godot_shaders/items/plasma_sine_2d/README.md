# Classic sine plasma with a cosine palette

Four sine waves are summed: one along X, one along Y, one along the diagonal and one of the distance from a slowly moving centre, each moving with time at its own rate. The sum, scaled to 0..1 and offset by a steadily increasing time term, indexes a cosine palette `a + b cos(2 pi (c t + d))` whose four RGB parameters are uniforms, so the colours cycle like the palette rotation of old demos.

## When to use it

Use it for retro demoscene backgrounds, music visualizers, loading screens, magic effects and placeholder animated textures.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/plasma_sine_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/plasma_sine_2d/plasma_sine_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `scale` | float | hint_range(1.0, 30.0) | 8.0 | Size of the plasma pattern; higher gives more waves. |
| `speed` | float | hint_range(0.0, 5.0) | 1.0 | Animation speed of the waves. |
| `palette_offset` | vec4 | source_color | (0.5, 0.5, 0.5, 1) | Palette offset term a (RGB) in a + b cos(2 pi (c t + d)). |
| `palette_amplitude` | vec4 | source_color | (0.5, 0.5, 0.5, 1) | Palette amplitude term b (RGB). |
| `palette_frequency` | vec4 | source_color | (1, 1, 1, 1) | Palette frequency term c (RGB). |
| `palette_phase` | vec4 | source_color | (0, 0.33, 0.67, 1) | Palette phase term d (RGB). |
| `cycle_speed` | float | hint_range(0.0, 2.0) | 0.15 | Palette cycling speed. |
| `color_steps` | int | hint_range(0, 32) | 0 | Quantize the palette into steps for a retro look; 0 keeps it smooth. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

Smoothly flowing rainbow bands that swirl around a wandering centre.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Pure function of position and time: no texture detail. Palette parameters outside 0..1 can clip.

## Technique

- Sum of sine fields (plasma)
- Cosine colour palette a + b cos(2 pi (c t + d))
- Palette cycling
