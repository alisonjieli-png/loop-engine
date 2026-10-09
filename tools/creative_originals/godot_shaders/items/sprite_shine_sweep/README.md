# Shine sweep across a sprite

UV coordinates are projected on a direction at `angle_degrees`; a band at a position that moves from beyond one corner to beyond the opposite corner is brightened. A timer moves the band during `sweep_time` and holds it off the sprite during `pause_time`, or a script sets `progress_override`. The added light is multiplied by alpha so only the sprite's shape shines.

## When to use it

Use it on buttons, coins, cards, rare items, logos and achievement icons to draw attention.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_shine_sweep/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_shine_sweep/sprite_shine_sweep.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `shine_color` | vec4 | source_color | (1, 1, 0.95, 1) | Colour of the shine. |
| `angle_degrees` | float | hint_range(-90.0, 90.0) | 30.0 | Direction the band travels across the sprite. |
| `band_width` | float | hint_range(0.01, 0.6) | 0.14 | Width of the band in UV units. |
| `softness` | float | hint_range(0.0, 1.0) | 0.5 | Share of the band that fades softly. |
| `intensity` | float | hint_range(0.0, 2.0) | 0.9 | Brightness of the shine. |
| `sweep_time` | float | hint_range(0.1, 5.0) | 0.8 | Seconds one sweep takes. |
| `pause_time` | float | hint_range(0.0, 10.0) | 1.4 | Seconds between sweeps. |
| `progress_override` | float | hint_range(-1.0, 1.0) | -1.0 | Fixed sweep position from 0 to 1 for scripted control; negative uses the timer. |

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The sprite with a bright diagonal band of light across its middle.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The band moves in UV space, so in an atlas it sweeps across the whole atlas region. It brightens additively and can clip on light sprites.

## Technique

- Projected band along a direction
- Timed sweep with pause
