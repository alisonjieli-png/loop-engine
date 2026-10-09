# 2D laser beam with core, glow and sparks

The beam runs along the rectangle's U axis. Its vertical distance from the centre line, divided by a noise-wobbled width, gives a sharp core and an exponential glow. Pulses slide along the beam over time. An elliptical flare sits at the left end and an impact glow at the right end, broken up by noise around its angle so it sparkles. Alpha follows the brightness so the rectangle blends over the scene.

## When to use it

Use it for laser weapons, tractor beams, security lasers, scanners and connecting lines between UI elements (stretch and rotate the rectangle to aim it).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/laser_beam_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/laser_beam_2d/laser_beam_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (1, 0.95, 0.95, 1) | Colour of the hot core. |
| `beam_color` | vec4 | source_color | (1, 0.15, 0.3, 1) | Colour of the glow. |
| `core_width` | float | hint_range(0.0, 0.3) | 0.04 | Core thickness in rectangle heights. |
| `glow_width` | float | hint_range(0.0, 0.5) | 0.18 | Glow reach in rectangle heights. |
| `flicker` | float | hint_range(0.0, 1.0) | 0.3 | Noisy variation of the beam width along its length. |
| `pulse_speed` | float | hint_range(-10.0, 10.0) | 3.0 | Speed of the pulses along the beam. |
| `pulse_spacing` | float | hint_range(0.05, 1.0) | 0.2 | Distance between pulses in rectangle widths. |
| `flare_size` | float | hint_range(0.0, 0.5) | 0.18 | Size of the flare at the emitter (left end). |
| `impact_size` | float | hint_range(0.0, 0.5) | 0.12 | Size of the impact glow at the right end. |

## Inputs

- A ColorRect stretched along the beam (rotate it to aim).

## Output

A red laser with a white core crossing the rectangle, flared at the left and sparkling at the right.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Stretching the rectangle stretches the glow; adjust widths to its aspect. The beam is straight.

## Technique

- Distance-based core and exponential glow
- Noise-modulated width
- Endpoint flares
- Value noise with quintic interpolation and fractional Brownian motion
