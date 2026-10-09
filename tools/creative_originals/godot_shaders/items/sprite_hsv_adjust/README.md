# Hue, saturation, value and sepia adjustment

Each texel is converted from RGB to hue, saturation and value with the hexcone model, the hue is rotated, saturation and value are scaled, and the colour is converted back. Contrast pivots around middle grey. Finally the colour can be faded toward its luminance (greyscale) or toward a warm brown toning of that luminance (sepia). Alpha and the node's modulate are kept.

## When to use it

Use it for colour variants of enemies and items, frozen, poisoned or petrified states, flashbacks and old-photo looks, and quick art tuning without editing textures.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_hsv_adjust/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_hsv_adjust/sprite_hsv_adjust.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `hue_shift_degrees` | float | hint_range(-180.0, 180.0) | 0.0 | Rotation of the hue in degrees. |
| `saturation` | float | hint_range(0.0, 3.0) | 1.0 | Saturation multiplier. |
| `value` | float | hint_range(0.0, 3.0) | 1.0 | Brightness (value) multiplier. |
| `contrast` | float | hint_range(0.0, 3.0) | 1.0 | Contrast around middle grey. |
| `grayscale` | float | hint_range(0.0, 1.0) | 0.0 | Fade toward greyscale. |
| `sepia` | float | hint_range(0.0, 1.0) | 0.0 | Fade toward a warm sepia tone. |

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The orange sprite rotated to cool blue and green hues with a little more saturation.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Hue rotation in HSV is not perceptually uniform, so some hues change brightness as they rotate. Greys have no hue to rotate.

## Technique

- RGB to HSV hexcone conversion and back
- Luminance-based greyscale and sepia toning
