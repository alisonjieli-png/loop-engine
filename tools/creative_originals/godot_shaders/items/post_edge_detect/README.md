# Full-screen ink edges from depth and colour

A full-screen pass that reads the screen and depth textures. For each pixel it samples a 3 x 3 neighbourhood. Depth is turned into inverse view depth, which changes linearly across any flat surface, so its Laplacian stays near zero on planes and spikes at silhouettes and creases. Luminance goes through a Sobel filter to catch borders between colours on the same surface. The larger response, past `threshold`, becomes a line. `paper_mix` blends the scene toward a paper colour for a sketch look.

## When to use it

Use it for technical illustration, comic and sketch looks, or to make 3D shapes read clearly at small sizes. It outlines everything on screen at once, unlike per-mesh outline materials.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_edge_detect/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_edge_detect/post_edge_detect.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_nearest |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `line_color` | vec4 | source_color | (0.05, 0.05, 0.08, 1) | Colour of the ink lines; alpha sets their opacity. |
| `line_width` | float | hint_range(0.5, 4.0) | 1.0 | Sampling distance in pixels; larger values give thicker lines. |
| `depth_sensitivity` | float | hint_range(0.0, 50.0) | 8.0 | Gain on the depth Laplacian (silhouettes and creases). |
| `color_sensitivity` | float | hint_range(0.0, 10.0) | 1.5 | Gain on the luminance Sobel response (colour borders). |
| `threshold` | float | hint_range(0.0, 2.0) | 0.3 | Edge response where lines start. |
| `paper_mix` | float | hint_range(0.0, 1.0) | 0.0 | How far the scene colour is blended toward `paper_color`. |
| `paper_color` | vec4 | source_color | (0.96, 0.94, 0.88, 1) | Background tint used by `paper_mix`. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

The scene with dark lines along silhouettes, creases and colour borders, optionally faded toward paper.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Lines are found in screen space, so their width is in pixels and does not scale with distance. Transparent objects are not in the depth buffer and only get colour edges. Very distant geometry can produce faint depth lines from precision. The pass sees only what is drawn before it; draw order relative to other transparent passes is not controlled.

## Technique

- Laplacian of inverse view depth for silhouette and crease detection
- Sobel operator on luminance
- Depth reconstruction with INV_PROJECTION_MATRIX
