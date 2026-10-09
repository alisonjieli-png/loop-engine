# CRT monitor with curvature, scanlines and shadow mask

Screen coordinates are pushed outward by an amount that grows with the squared distance from the centre, which curves the picture like convex glass; samples that land outside the screen and the rounded corners are black. A cosine along the curved vertical coordinate draws scanlines every `scanline_pixels` screen pixels, every third screen column keeps only red, green or blue to imitate an aperture grille, a blurred mip level adds phosphor glow, and a vignette darkens the edges.

## When to use it

Use it for retro games, arcade cabinets in 3D, security camera feeds, terminals and nostalgic menus.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_crt_monitor/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_crt_monitor/post_crt_monitor.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `curvature` | float | hint_range(0.0, 0.5) | 0.12 | Barrel curvature of the glass. |
| `scanline_pixels` | float | hint_range(2.0, 12.0) | 3.0 | Scanline period in screen pixels (kept above two pixels to avoid moire). |
| `scanline_strength` | float | hint_range(0.0, 1.0) | 0.45 | Darkness between scanlines. |
| `mask_strength` | float | hint_range(0.0, 1.0) | 0.3 | Strength of the red, green and blue aperture stripes. |
| `mask_pixels` | float | hint_range(1.0, 6.0) | 1.0 | Width of one mask stripe in screen pixels. |
| `glow` | float | hint_range(0.0, 1.0) | 0.25 | Bloom added from a blurred mip level. |
| `vignette` | float | hint_range(0.0, 2.0) | 0.6 | Darkening toward the edges. |
| `corner_radius` | float | hint_range(0.0, 0.2) | 0.04 | Radius of the rounded black corners. |
| `brightness` | float | hint_range(0.5, 2.0) | 1.2 | Overall gain to compensate for the darkening. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene curved inside a rounded tube frame with fine dark scanlines, coloured stripes and a soft glow.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The aperture mask is tied to screen pixels and creates moire when the output is scaled. Curvature crops the picture edges. Glow depends on the screen texture's mipmaps. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Barrel coordinate warp
- Cosine scanlines
- Aperture grille mask by screen column
- Mip-level glow
