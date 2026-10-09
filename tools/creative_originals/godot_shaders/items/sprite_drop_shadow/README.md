# Soft drop shadow inside the sprite rectangle

The shadow is the sprite's own alpha read at an offset position, blurred with a 5 x 5 Gaussian-weighted kernel whose spacing grows with `softness`. The sprite is then composited over the shadow with the standard over operator, so semi-transparent sprite edges blend correctly into the shadow.

## When to use it

Use it for UI icons, cards, buttons, pickups and characters on flat backgrounds where a separate shadow node would be clumsy.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_drop_shadow/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_drop_shadow/sprite_drop_shadow.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `shadow_color` | vec4 | source_color | (0, 0, 0.05, 0.6) | Colour and opacity of the shadow. |
| `offset_x` | float | hint_range(-32.0, 32.0) | 7.0 | Horizontal shadow offset in texels (positive is right). |
| `offset_y` | float | hint_range(-32.0, 32.0) | 7.0 | Vertical shadow offset in texels (positive is down). |
| `softness` | float | hint_range(0.0, 8.0) | 2.5 | Blur radius of the shadow in texels. |

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual. Effects outside the shape are drawn inside the texture rectangle, so the texture needs a margin.

## Output

An orange disc floating above the background with a soft dark shadow to its lower right.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Effects outside the shape are drawn inside the texture rectangle, so the texture needs a margin. Offsets larger than the margin are cut at the texture edge. The shadow ignores what lies under the sprite (it is not a light).

## Technique

- Offset alpha sampling with a Gaussian kernel
- Porter-Duff over compositing
