# Hit flash, blink and silhouette modes

The sprite colour (texture times modulate) is blended with `flash_color` by `flash_amount` in one of three ways: a mix, an additive brighten, or a flat silhouette that keeps only the alpha. With `auto_blink` the amount is switched on and off at `blink_rate` by a square wave, which is how many games show invulnerability. Alpha is never changed, so the shape stays exact.

## When to use it

Use it for damage feedback, invulnerability frames, selection pulses, freeze or poison tints and 'who's that' silhouettes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_hit_flash/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_hit_flash/sprite_hit_flash.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `flash_color` | vec4 | source_color | (1, 1, 1, 1) | Colour of the flash. |
| `flash_amount` | float | hint_range(0.0, 1.0) | 0.0 | Flash strength from 0 to 1; animate it from a script on hit. |
| `mode` | int | hint_range(0, 2) | 0 | 0 mix toward the colour, 1 add the colour, 2 flat silhouette in the colour. |
| `auto_blink` | bool | none | false | Blink the flash on and off over time. |
| `blink_rate` | float | hint_range(0.5, 30.0) | 12.0 | Blinks per second. |
| `blink_duty` | float | hint_range(0.0, 1.0) | 0.5 | Share of each blink cycle that shows the flash. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The sprite tinted strongly toward red as on a damage frame.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

One flash colour at a time. Driving `flash_amount` per instance needs separate materials (or instance uniforms in your own variant).

## Technique

- Colour blend modes
- Square-wave blinking
