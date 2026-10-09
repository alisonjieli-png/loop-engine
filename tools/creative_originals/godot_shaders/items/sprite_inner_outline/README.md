# Inner outline along a sprite's edge

Each opaque texel searches a disc of `width` texels for a transparent neighbour (texels outside the texture count as transparent). If it finds one, it lies on the inside edge and takes the line colour; otherwise it keeps the sprite colour multiplied by the node's modulate. Transparent texels stay transparent, so the outline never grows the sprite's footprint.

## When to use it

Use it for selection highlights that must not overlap neighbours (tiles, inventory icons, packed sprites), hover states and stylized borders on cut-out art.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_inner_outline/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_inner_outline/sprite_inner_outline.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `line_color` | vec4 | source_color | (1, 0.95, 0.4, 1) | Colour of the inner line. |
| `width` | int | hint_range(1, 8) | 2 | Line width in texels. |
| `alpha_cutoff` | float | hint_range(0.01, 1.0) | 0.5 | Alpha at which a texel counts as part of the shape. |
| `keep_interior` | bool | none | true | Draw the sprite inside the line; off leaves only the line. |
| `pulse_speed` | float | hint_range(0.0, 12.0) | 0.0 | Pulse frequency of the line brightness; 0 keeps it steady. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The sprite's blobs with a yellow border running just inside their edges.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Cost grows with the square of `width`. With texture filtering and scaling, edges are as soft as the sampled alpha. Atlas regions need padding or neighbouring sprites count as opaque.

## Technique

- Neighbourhood alpha erosion test
- Disc-shaped search kernel
