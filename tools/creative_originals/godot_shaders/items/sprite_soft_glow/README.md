# Soft outer glow around a sprite

Around each texel the shader samples the sprite's alpha on `rings` concentric circles out to `radius` texels, `directions` samples per ring, weighting inner rings more. The weighted average is high next to the shape and falls off smoothly with distance. That glow is composited under the sprite with the over operator and pulses with a sine of time.

## When to use it

Use it for power-ups, magic items, highlighted characters, selection auras and neon UI icons.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_soft_glow/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_soft_glow/sprite_soft_glow.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `glow_color` | vec4 | source_color | (0.4, 0.85, 1, 1) | Colour and opacity of the glow. |
| `radius` | float | hint_range(1.0, 24.0) | 10.0 | Reach of the glow in texels. |
| `intensity` | float | hint_range(0.0, 4.0) | 1.6 | Brightness of the glow before clamping. |
| `rings` | int | hint_range(1, 6) | 3 | Number of sampling rings; more gives a smoother falloff. |
| `directions` | int | hint_range(4, 24) | 12 | Samples per ring. |
| `pulse_speed` | float | hint_range(0.0, 10.0) | 2.0 | Pulse frequency. |
| `pulse_depth` | float | hint_range(0.0, 1.0) | 0.3 | How much the pulse dims the glow; 0 disables it. |

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual. Effects outside the shape are drawn inside the texture rectangle, so the texture needs a margin.

## Output

An orange disc surrounded by a soft cyan halo on a dark background.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Effects outside the shape are drawn inside the texture rectangle, so the texture needs a margin. Cost is rings times directions samples per pixel (36 by default).

## Technique

- Ring-sampled alpha gathering (radial blur of the mask)
- Over compositing of a halo
