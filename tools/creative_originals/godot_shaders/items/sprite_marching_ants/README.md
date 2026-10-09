# Marching ants selection outline

A texel lies on the edge when any neighbour within `width` texels is on the other side of the alpha cutoff. Edge texels outside (or inside) the shape get a dash colour chosen by a diagonal stripe pattern in screen space that slides with time, so dashes appear to crawl around the outline. Other texels show the sprite.

## When to use it

Use it for selection in editors and level tools, RTS unit selection, highlighting interactive objects and drag-and-drop targets.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_marching_ants/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_marching_ants/sprite_marching_ants.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `dash_dark` | vec4 | source_color | (0.05, 0.05, 0.05, 1) | Colour of the dark dashes. |
| `dash_light` | vec4 | source_color | (1, 1, 1, 1) | Colour of the light dashes. |
| `dash_pixels` | float | hint_range(2.0, 32.0) | 6.0 | Length of each dash in screen pixels. |
| `speed` | float | hint_range(-40.0, 40.0) | 12.0 | Dash movement in screen pixels per second. |
| `width` | int | hint_range(1, 4) | 1 | Thickness of the line in texels. |
| `outside` | bool | none | true | Draw the line just outside the shape; off draws it just inside. |
| `alpha_cutoff` | float | hint_range(0.01, 1.0) | 0.5 | Alpha at which a texel counts as part of the shape. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The sprite outlined by small alternating black and white dashes.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Dashes follow a screen-space diagonal pattern, not the arc length of the outline, so their spacing varies with edge direction. Effects outside the shape are drawn inside the texture rectangle, so the texture needs a margin.

## Technique

- Edge detection by neighbourhood alpha comparison
- Animated screen-space dash pattern
