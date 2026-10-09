# Morphing signed distance shapes

Each shape is a signed distance function: negative inside, positive outside, zero on the edge. Morphing linearly blends the distances of two consecutive shapes, which interpolates the outline smoothly. The fill and the outline are anti-aliased with `fwidth`, the glow decays exponentially with positive distance, and optional contour lines show the distance field itself.

## When to use it

Use it for crisp UI icons and badges at any resolution, shape transitions, tutorials about distance fields, and animated logos.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sdf_shape_morph_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sdf_shape_morph_2d/sdf_shape_morph_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `fill_color` | vec4 | source_color | (0.95, 0.45, 0.55, 1) | Colour inside the shape. |
| `outline_color` | vec4 | source_color | (1, 1, 1, 1) | Colour of the outline. |
| `glow_color` | vec4 | source_color | (1, 0.5, 0.7, 1) | Colour of the outer glow. |
| `background_color` | vec4 | source_color | (0.1, 0.08, 0.16, 1) | Background colour. |
| `morph_speed` | float | hint_range(0.0, 3.0) | 0.4 | Shapes per second when animating. |
| `shape_index` | float | hint_range(0.0, 4.0) | 2.5 | Fixed position in the shape sequence (0 circle, 1 box, 2 star, 3 heart; fractions blend). |
| `animate` | bool | none | true | Cycle through the shapes over time instead of using `shape_index`. |
| `size` | float | hint_range(0.05, 0.5) | 0.3 | Shape size in UV units. |
| `outline_width` | float | hint_range(0.0, 0.05) | 0.012 | Outline width in UV units. |
| `glow_width` | float | hint_range(0.0, 0.3) | 0.08 | Reach of the outer glow in UV units. |
| `show_contours` | bool | none | false | Show faint iso-distance lines outside and inside the shape. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A pink shape halfway between a star and a heart with a white outline, glow and distance contours.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The star and heart functions are approximate distances (bounded but not exact), so outlines vary slightly in width. Blending distances does not preserve exact area during a morph.

## Technique

- 2D signed distance functions
- Distance blending for morphing
- Derivative anti-aliasing of iso-lines
