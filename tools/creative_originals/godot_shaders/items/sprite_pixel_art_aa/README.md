# Smooth nearest sampling for scaled pixel art

With linear filtering, a texture lookup at a texel edge blends the two texels. The shader moves every lookup to the nearest texel edge plus an offset scaled by how many texels one screen pixel covers (from `fwidth`). Inside a texel the offset saturates and the lookup lands on the texel centre, which is flat colour; across an edge the lookup sweeps through the bilinear blend within one screen pixel. The result looks like nearest filtering but with anti-aliased edges at any rotation or scale.

## When to use it

Use it for pixel art sprites and tiles that rotate, scale or move smoothly, camera zoom in pixel art games and high-resolution rendering of low-resolution art.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_pixel_art_aa/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_pixel_art_aa/sprite_pixel_art_aa.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node. Set the node's `texture_filter` to Linear.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `edge_sharpness` | float | hint_range(0.25, 4.0) | 1.0 | Width of the blend at texel edges in screen pixels (1 is one pixel, higher is sharper). |
| `enabled` | bool | none | true | Turn the technique off to compare with plain linear filtering. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A pixel art texture on a Sprite2D whose `texture_filter` is set to Linear (as in `demo.tscn`).

## Output

A 24-pixel sprite scaled seven times with crisp, flat texels and smooth edges.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Requires the node's texture filter set to Linear; with Nearest filtering it has no effect. Mipmaps must be off or the blend smears when minified.

## Technique

- Anti-aliased nearest-neighbour sampling (bilinear blend confined to one screen pixel at texel edges)
- Screen-space derivatives of texel coordinates
