# Pixel-exact sprite outline

For each transparent texel the shader searches a neighbourhood of `thickness` texels. If any neighbour is opaque (alpha at or above `alpha_cutoff`) the texel becomes outline colour. `rounded` picks a round search shape (Euclidean distance); turned off, the shape is a diamond (Manhattan distance), which keeps the hard steps pixel art expects. Opaque texels keep the sprite colour, or become transparent with `outline_only` to draw just the line.

## When to use it

Use it to highlight a hovered or selected sprite, mark pickups, or add a clean border to pixel art characters. For a soft glow instead of a hard line use `sprite_soft_glow`.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_pixel_outline/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_pixel_outline/sprite_pixel_outline.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `outline_color` | vec4 | source_color | (1, 1, 1, 1) | Colour of the outline; alpha sets its opacity. |
| `thickness` | int | hint_range(0, 8) | 2 | Outline width in texels. |
| `alpha_cutoff` | float | hint_range(0.01, 1.0) | 0.5 | Alpha at which a texel counts as part of the shape. |
| `rounded` | bool | none | true | Round search shape when on, diamond shape when off. |
| `outline_only` | bool | none | false | Hide the sprite and keep only the outline. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A sprite texture with transparent space around the shape, assigned to the node as usual. The outline is drawn inside the texture's rectangle, so leave a margin at least `thickness` texels wide.

## Output

The sprite with a solid line of the chosen colour hugging its silhouette.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The outline cannot extend past the texture rectangle; trim or pad sprites accordingly. Cost grows with the square of `thickness` (up to 289 samples at 8). With texture filtering on and the sprite scaled, edges are as soft as the texture sampling. Texture atlases need padding between regions or neighbouring sprites bleed into the outline.

## Technique

- Neighbourhood alpha dilation
- Euclidean and Manhattan distance kernels
