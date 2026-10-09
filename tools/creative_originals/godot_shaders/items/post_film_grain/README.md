# Animated film grain with luminance response

Grain is a hash of the screen cell (`grain_size` pixels) and the current grain frame, so the pattern changes at a film-like rate instead of every render frame. Three more hashes give per-channel grain mixed in by `color_grain`. A parabola of luminance scales the grain so midtones carry the most and pure black and white the least, as film does. A small random exposure change per frame adds flicker.

## When to use it

Use it for cinematic and analog looks, horror atmosphere, flashbacks, and to hide colour banding in dark gradients.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_film_grain/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_film_grain/post_film_grain.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `amount` | float | hint_range(0.0, 1.0) | 0.35 | Grain strength. |
| `grain_size` | float | hint_range(1.0, 6.0) | 1.6 | Size of a grain cell in screen pixels. |
| `color_grain` | float | hint_range(0.0, 1.0) | 0.25 | Blend from monochrome (0) to independent colour grain (1). |
| `midtone_bias` | float | hint_range(0.0, 1.0) | 0.7 | How much grain concentrates in midtones instead of being even. |
| `frames_per_second` | float | hint_range(1.0, 60.0) | 24.0 | Rate at which the grain pattern changes. |
| `flicker` | float | hint_range(0.0, 0.2) | 0.03 | Random exposure change per grain frame. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with fine flickering grain most visible in its midtones.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Hashed white noise, not a scanned film stock: grain has no clumping or shape. Visible grain changes with resolution because it is sized in screen pixels. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Hashed per-cell noise updated at a fixed frame rate
- Luminance-dependent grain response
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
