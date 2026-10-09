# ASCII text rendering of the screen

The screen is divided into square cells. Each cell reads the scene from the mip level whose texel matches the cell size, which is the cell's average colour. Its luminance picks one of ten glyphs ordered by ink coverage: blank, dot, colon, dash, equals, plus, percent, hash, at and a full block. Glyphs are 5 x 5 bitmaps stored as integers in the shader; the pixel's position inside the cell selects a bit.

## When to use it

Use it for hacker and terminal aesthetics, retro computer scenes, stylized menus and as an accessibility-unfriendly gag mode.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_ascii_glyphs/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_ascii_glyphs/post_ascii_glyphs.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `cell_pixels` | float | hint_range(4.0, 32.0) | 8.0 | Size of one character cell in screen pixels. |
| `use_scene_color` | bool | none | true | Colour each glyph with its cell's colour instead of `text_color`. |
| `text_color` | vec4 | source_color | (0.4, 1, 0.5, 1) | Single glyph colour when `use_scene_color` is off. |
| `background_color` | vec4 | source_color | (0.02, 0.03, 0.04, 1) | Colour behind the glyphs. |
| `contrast` | float | hint_range(0.5, 3.0) | 1.3 | Contrast of the brightness that selects glyphs. |
| `color_boost` | float | hint_range(0.5, 3.0) | 1.4 | Brightness multiplier for coloured glyphs. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene redrawn as coloured characters, dense glyphs in bright areas and dots in dark ones.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Ten glyph levels and a 5 x 5 grid limit detail; the cell size should be at least 6 pixels for legible glyphs. Mip averaging is box filtered. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Luminance-indexed glyph selection
- Bitmap glyphs packed into integers
- Cell averaging by mip level
