# Pixelation with nearest-colour palette mapping

The pass divides the screen into `pixel_size` blocks and samples the scene once at each block centre. A 2 x 2 ordered dither nudges the colour before it is matched against every cell of the palette strip; the closest colour by a luminance-weighted distance wins. The bundled palette is an eight-colour strip built from a GradientTexture1D with hard steps; replace it with any palette image one pixel tall.

## When to use it

Use it for retro and pixel-art styled 3D games, demakes, palette-limited art directions and stylized menus.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_pixelate_palette/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_pixelate_palette/post_pixelate_palette.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_nearest |  | The rendered scene behind the pass (filled by Godot). |
| `palette` | sampler2D | source_color, filter_nearest, repeat_disable |  | Palette strip: `palette_size` equal-width colour cells from left to right. |
| `palette_size` | int | hint_range(2, 32) | 8 | Number of colours in the palette strip. |
| `pixel_size` | float | hint_range(1.0, 32.0) | 4.0 | Size of each block in screen pixels. |
| `dither_strength` | float | hint_range(0.0, 1.0) | 0.35 | Ordered dither applied before the palette lookup. |
| `palette_mix` | float | hint_range(0.0, 1.0) | 1.0 | Blend between the pixelated colour (0) and the palette colour (1). |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.
- Optional: a palette image (N colours side by side) for `palette`.

## Output

The scene as chunky 4-pixel blocks reduced to an eight-colour retro palette.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Blocks sample one point, so thin details can vanish between frames as the camera moves. Palette matching is a weighted RGB distance, not a perceptual colour space. Cost grows with `palette_size`. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Block pixelation by sampling block centres
- Nearest palette colour search
- 2 x 2 ordered dithering
