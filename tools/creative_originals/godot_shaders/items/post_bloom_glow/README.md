# Single-pass bloom from screen mip levels

Godot's screen texture has mipmaps, each level a box-filtered half-size copy. The pass reads levels 1 to `levels`, two slightly offset samples each to smooth the blocky upsampling, applies a soft-knee bright pass to each, and sums them with geometric weights. The result is a glow that is tight from the low levels and wide from the high ones, added over the original image.

## When to use it

Use it for glowing lights, emissive materials, sunsets, magic and neon in renderers or projects where the built-in Glow effect is unavailable or needs a different look.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_bloom_glow/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_bloom_glow/post_bloom_glow.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `threshold` | float | hint_range(0.0, 1.0) | 0.62 | Luminance above which pixels glow. |
| `knee` | float | hint_range(0.0, 0.5) | 0.15 | Softness of the threshold. |
| `intensity` | float | hint_range(0.0, 4.0) | 1.3 | Brightness of the added glow. |
| `levels` | int | hint_range(1, 6) | 5 | Number of mip levels summed; more gives a wider halo. |
| `spread` | float | hint_range(0.0, 1.0) | 0.6 | Weight ratio between successive levels; higher favours the wide halo. |
| `tint` | vec4 | source_color | (1, 0.92, 0.8, 1) | Colour of the glow. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with soft warm halos around its brightest areas.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Mip levels are box filtered, so the glow is less smooth than a separable Gaussian chain and can flicker on small moving highlights. The bright pass works on display colours, not HDR values. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Soft-knee bright pass
- Bloom from summed screen mip levels
- Geometric level weighting
