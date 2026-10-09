# Noise dissolve with a burning edge

Fractal value noise is sampled at the object-space position, so the pattern sticks to the mesh as it moves. Fragments whose noise value is below the cut level are discarded; `dissolve` maps 0 to an intact mesh and 1 to a fully removed one. The noise distance above the cut gives two bands: a thin emissive edge blending from `edge_color` to `ember_color`, and a wider charred band where albedo darkens and roughness rises. Back faces are drawn so the hollow inside shows through the holes.

## When to use it

Use it for death and despawn effects, burning paper or cloth, teleport-out transitions and revealing objects. Animate `dissolve` from a script or AnimationPlayer, or enable `loop_animation` for previews.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/noise_dissolve_burn/`. `material.tres` loads the shader from `res://baltor/godot_shaders/noise_dissolve_burn/noise_dissolve_burn.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.82, 0.78, 0.72, 1) | Surface colour before burning. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.6 | Surface roughness before burning. |
| `dissolve` | float | hint_range(0.0, 1.0) | 0.45 | Progress from 0 (intact) to 1 (gone). |
| `noise_scale` | float | hint_range(0.5, 20.0) | 4.0 | Frequency of the noise in object units; higher gives smaller holes. |
| `edge_width` | float | hint_range(0.0, 0.2) | 0.04 | Width of the glowing edge in noise units. |
| `char_width` | float | hint_range(0.0, 0.3) | 0.08 | Width of the darkened band behind the edge in noise units. |
| `edge_color` | vec4 | source_color | (1, 0.42, 0.06, 1) | Colour of the outer edge glow. |
| `ember_color` | vec4 | source_color | (1, 0.9, 0.55, 1) | Colour of the hottest part of the edge. |
| `edge_emission` | float | hint_range(0.0, 12.0) | 5.0 | Emission strength of the edge. |
| `loop_animation` | bool | none | false | Animate the dissolve back and forth instead of using `dissolve`. |
| `loop_speed` | float | hint_range(0.0, 2.0) | 0.2 | Cycles per second of the looping animation. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A mesh with holes eaten into it, rimmed by orange glowing edges and a dark charred border.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Discard disables some early depth optimizations, so large dissolving meshes cost more to draw. The inside of the mesh is the back faces, lit as the outside. Shadows use the same discard and match the holes. The noise is value noise, so its lattice can show at very low scales.

## Technique

- Value noise with quintic interpolation and fractional Brownian motion in 3D object space
- Alpha-tested dissolve with distance bands
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
