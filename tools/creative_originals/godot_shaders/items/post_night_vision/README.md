# Night vision goggles

The scene's luminance is amplified and a blurred mip level adds blooming around bright areas, as an image intensifier does. Per-pixel hashed noise that changes every 1/30 second adds sensor grain, every other row is darkened, and the result is drawn in phosphor green. Two overlapping circles (or one) cut out the goggle view and a vignette darkens toward the edges.

## When to use it

Use it for stealth, horror and military games, surveillance views and thermal or night vision gadgets.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_night_vision/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_night_vision/post_night_vision.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `phosphor` | vec4 | source_color | (0.35, 1, 0.45, 1) | Colour of the phosphor screen. |
| `gain` | float | hint_range(0.5, 6.0) | 2.4 | Amplification of the scene luminance. |
| `glow` | float | hint_range(0.0, 2.0) | 0.6 | Bloom from a blurred mip level. |
| `noise_amount` | float | hint_range(0.0, 1.0) | 0.25 | Strength of the animated sensor noise. |
| `scanline_strength` | float | hint_range(0.0, 1.0) | 0.15 | Darkness of every other pixel row. |
| `binocular` | bool | none | true | Two overlapping circles when on, one circle when off. |
| `mask_radius` | float | hint_range(0.2, 1.0) | 0.46 | Radius of the viewing circles. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene in bright noisy green inside two overlapping circular eyepieces on black.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Amplifies the displayed image, not scene light levels: dark areas stay dark. The mask is drawn in screen space and must be adjusted for very wide aspect ratios. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Luminance amplification with mip bloom
- Hashed temporal sensor noise
- Binocular circle mask
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
