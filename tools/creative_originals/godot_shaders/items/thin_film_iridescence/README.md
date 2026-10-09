# Thin-film interference iridescence

Light reflecting off the top and bottom of a thin film travels different distances; whether the two reflections add or cancel depends on the wavelength. The shader computes the optical path difference `2 n d cos(theta_t)` from the film index, the thickness and the refraction angle, and evaluates a cosine interference term at red, green and blue wavelengths (with the half-wave phase shift of the top reflection). The result tints a metallic, glossy reflection. Thickness varies with drifting 3D noise and thins toward the top like a draining bubble.

## When to use it

Use it for soap bubbles, oil on water, beetle shells, anodized titanium, pearl coatings and sci-fi visors.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/thin_film_iridescence/`. `material.tres` loads the shader from `res://baltor/godot_shaders/thin_film_iridescence/thin_film_iridescence.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `film_index` | float | hint_range(1.0, 2.5) | 1.33 | Refractive index of the film (water is about 1.33). |
| `thickness_min_nm` | float | hint_range(0.0, 1500.0) | 250.0 | Thinnest film thickness in nanometres. |
| `thickness_max_nm` | float | hint_range(0.0, 1500.0) | 750.0 | Thickest film thickness in nanometres. |
| `swirl_scale` | float | hint_range(0.1, 10.0) | 2.0 | Frequency of the thickness swirls in object units. |
| `swirl_speed` | float | hint_range(0.0, 2.0) | 0.15 | Drift speed of the swirls. |
| `opacity` | float | hint_range(0.0, 1.0) | 0.35 | Opacity seen head-on; edges become opaque. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.05 | Roughness of the reflection. |
| `base_color` | vec4 | source_color | (0.02, 0.02, 0.03, 1) | Colour under the film. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A clear bubble whose reflections shimmer in bands of magenta, green and gold that drift.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Two-beam approximation at three wavelengths, not a spectral integration: colours are plausible, not exact. Multiple reflections inside the film are ignored. Transparency uses Godot's alpha blending and is not sorted per pixel.

## Technique

- Thin-film interference from the optical path difference 2 n d cos(theta)
- Per-channel wavelength evaluation
- Value noise with quintic interpolation and fractional Brownian motion in 3D
