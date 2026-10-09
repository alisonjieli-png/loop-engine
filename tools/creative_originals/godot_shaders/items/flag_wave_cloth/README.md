# Waving flag with a pinned edge

The flag's displacement is a function of UV: a travelling sine along U plus a faster ripple that also varies along V, multiplied by U so the pole edge (U = 0) stays fixed. A quadratic droop pulls the free end down. Normals are rebuilt from finite-difference derivatives of the same function, so lighting follows the folds. The face colour is a stripe count and an emblem disc, multiplied by an optional texture.

## When to use it

Use it for flags, banners, sails, pennants and hanging cloth signs that only need to wave, not collide.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/flag_wave_cloth/`. `material.tres` loads the shader from `res://baltor/godot_shaders/flag_wave_cloth/flag_wave_cloth.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `flag_texture` | sampler2D | source_color, hint_default_white |  | Optional image multiplied with the pattern (white by default). |
| `stripe_a` | vec4 | source_color | (0.1, 0.25, 0.6, 1) | First stripe colour. |
| `stripe_b` | vec4 | source_color | (0.95, 0.95, 0.92, 1) | Second stripe colour, and the plain colour when `stripes` is 0. |
| `emblem_color` | vec4 | source_color | (0.9, 0.7, 0.15, 1) | Colour of the disc emblem. |
| `stripes` | int | hint_range(0, 12) | 5 | Number of horizontal stripes; 0 disables them. |
| `amplitude` | float | hint_range(0.0, 0.5) | 0.12 | Wave height at the free edge in object units. |
| `wavelength` | float | hint_range(0.1, 4.0) | 0.9 | Length of the main wave in UV units. |
| `speed` | float | hint_range(0.0, 10.0) | 3.0 | Wave speed. |
| `droop` | float | hint_range(0.0, 0.5) | 0.06 | Downward sag of the free edge. |
| `flutter` | float | hint_range(0.0, 1.0) | 0.35 | Strength of the faster secondary ripple. |

## Inputs

- A QuadMesh (or plane) with enough subdivisions along U; the pole side must be at U = 0.
- Optional: a flag image for `flag_texture`.

## Output

A striped flag with a gold disc rippling in waves that start at the pole.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Not a cloth simulation: no gravity response to orientation, no wind direction and no collision. Normals come from the UV-space function, assuming an unscaled quad, so strongly non-uniform scale skews lighting. Shadows follow the moving shape.

## Technique

- Travelling sine waves weighted by distance from a pinned edge
- Finite-difference normals of a displacement function
