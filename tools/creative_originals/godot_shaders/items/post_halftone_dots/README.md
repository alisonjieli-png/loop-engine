# CMYK halftone print screens

The scene (read from a slightly blurred mip level) is converted to cyan, magenta, yellow and key (black) ink amounts. Each ink has its own dot grid rotated to the traditional screen angles (15, 75, 0 and 45 degrees) so the grids do not form moire. In each grid cell a dot's area is proportional to the ink amount, and dots are anti-aliased with derivatives. Inks multiply onto the paper colour like subtractive printing.

## When to use it

Use it for comic book and pop art looks, printed matter in games, retro magazines and stylized cutscenes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_halftone_dots/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_halftone_dots/post_halftone_dots.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `dot_spacing` | float | hint_range(2.0, 40.0) | 7.0 | Distance between dot centres in screen pixels. |
| `dot_softness` | float | hint_range(0.0, 2.0) | 0.8 | Anti-aliasing width of dot edges. |
| `paper_color` | vec4 | source_color | (0.97, 0.95, 0.9, 1) | Colour of the paper. |
| `ink_strength` | float | hint_range(0.0, 1.5) | 1.0 | Scales ink amounts; above 1 prints heavier. |
| `monochrome` | bool | none | false | Print a single black screen from luminance instead of four inks. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene printed as overlapping cyan, magenta, yellow and black dot screens on cream paper.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Dots sample the ink at each pixel, not at the cell centre, so dot edges follow image edges slightly. The RGB to CMYK conversion is the naive formula without colour management. Dot spacing is in screen pixels. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- CMYK separation
- Rotated halftone screens at traditional angles
- Dot area proportional to ink
- Subtractive compositing
