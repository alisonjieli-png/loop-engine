# Retro console look: vertex snapping and affine textures

The vertex stage computes the clip position itself and rounds the projected X and Y to a `snap_width` x `snap_height` grid before writing `POSITION`, so vertices jump between grid points as objects move. It also passes the UV multiplied by clip W together with W; dividing them in the fragment stage undoes perspective-correct interpolation, giving affine texture warping on large polygons. The colour is a checker times an optional texture, quantized to `color_levels` per channel with a 4 x 4 ordered dither.

## When to use it

Use it for retro and horror games in the style of early 3D consoles, demakes, and nostalgic menus.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/ps1_vertex_snap/`. `material.tres` loads the shader from `res://baltor/godot_shaders/ps1_vertex_snap/ps1_vertex_snap.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo_texture` | sampler2D | source_color, hint_default_white, filter_nearest |  | Optional texture multiplied with the checker (white by default). |
| `color_a` | vec4 | source_color | (0.85, 0.75, 0.55, 1) | First checker colour. |
| `color_b` | vec4 | source_color | (0.45, 0.25, 0.2, 1) | Second checker colour. |
| `checker_cells` | float | hint_range(1.0, 32.0) | 6.0 | Checker cells per UV unit. |
| `snap_width` | float | hint_range(40.0, 640.0) | 160.0 | Horizontal resolution of the vertex snapping grid. |
| `snap_height` | float | hint_range(30.0, 480.0) | 120.0 | Vertical resolution of the vertex snapping grid. |
| `affine_amount` | float | hint_range(0.0, 1.0) | 1.0 | Blend from perspective-correct (0) to affine (1) texture mapping. |
| `color_levels` | float | hint_range(2.0, 64.0) | 32.0 | Colour levels per channel (32 gives 15-bit colour). |
| `dither_amount` | float | hint_range(0.0, 1.0) | 0.6 | Strength of the ordered dither before quantizing. |

## Inputs

- Optional: a low-resolution texture for `albedo_texture`.

## Output

A checkered floor and crate whose texture bends across large triangles and whose edges sit on a coarse grid, with dithered colour.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Affine warping depends on triangle size: finely subdivided meshes show little of it. Snapping happens in screen space, so the jitter is visible only with motion. Lighting is still Godot's per-pixel lighting, not per-vertex Gouraud.

## Technique

- Clip-space vertex quantization
- Affine texture mapping by dividing W-weighted UVs
- 15-bit colour quantization with 4 x 4 Bayer dithering
