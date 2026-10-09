# Palette swap by colour keys

For each key, the RGB distance between the texel and the key decides a weight that is 1 inside `tolerance` and fades to 0 over `softness`. The texel moves toward the target colour by that weight. With `keep_shading`, the target is scaled by the ratio of the texel's brightness to the key's brightness, so anti-aliased edges and shading variations survive the swap.

## When to use it

Use it for team or player colours, enemy and item variants, unlockable skins and day or night palettes without duplicating sprite sheets.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_color_key_swap/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_color_key_swap/sprite_color_key_swap.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `key_1` | vec4 | source_color | (0.95, 0.6, 0.25, 1) | First colour to replace. |
| `target_1` | vec4 | source_color | (0.25, 0.8, 0.75, 1) | Replacement for the first colour. |
| `key_2` | vec4 | source_color | (0.85, 0.35, 0.3, 1) | Second colour to replace. |
| `target_2` | vec4 | source_color | (0.2, 0.45, 0.9, 1) | Replacement for the second colour. |
| `key_3` | vec4 | source_color | (0.55, 0.2, 0.35, 1) | Third colour to replace. |
| `target_3` | vec4 | source_color | (0.15, 0.15, 0.45, 1) | Replacement for the third colour. |
| `tolerance` | float | hint_range(0.0, 1.0) | 0.16 | RGB distance within which a texel counts as the key colour. |
| `softness` | float | hint_range(0.0, 0.5) | 0.1 | Extra distance over which the replacement fades out. |
| `keep_shading` | bool | none | true | Scale the target by the texel's brightness relative to the key, keeping shading. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The orange, red and purple sprite recoloured to teal, blue and navy.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Matching is by RGB distance, so similar colours elsewhere in the sprite can be caught; author sprites with distinct key colours. Three pairs per material.

## Technique

- Colour keying by RGB distance with soft tolerance
- Shading preservation by luminance ratio
