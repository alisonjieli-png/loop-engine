# Melting mesh with drips and a spreading puddle

Height above the base is normalized by `object_height`. Vertices drop by an amount that grows with the square of their height (the top sags most) and are clamped to the base. Around the outline, the angle picks one of `drip_count` slots; a narrow cosine lobe in each slot bulges outward from the rim down to a hashed length and ends in a rounder bead, making drips. Vertices near the base spread outward into a puddle. Melted areas take a warmer colour and turn glossy. Animate `melt` from 0 to 1, or loop it.

## When to use it

Use it for candles, ice cream, wax figures, snowmen in spring, melting ice and surreal effects.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/melt_drip_vertex/`. `material.tres` loads the shader from `res://baltor/godot_shaders/melt_drip_vertex/melt_drip_vertex.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.95, 0.85, 0.62, 1) | Colour of the solid material. |
| `melted_color` | vec4 | source_color | (0.98, 0.75, 0.45, 1) | Colour of melted areas. |
| `melt` | float | hint_range(0.0, 1.0) | 0.45 | Melt progress from 0 (solid) to 1. |
| `object_height` | float | hint_range(0.1, 10.0) | 1.2 | Height of the mesh in object units, centred on its origin. |
| `sag` | float | hint_range(0.0, 1.0) | 0.35 | How far the top sinks at full melt, as a share of height. |
| `drip_length` | float | hint_range(0.0, 1.0) | 0.25 | Longest drip length as a share of the height. |
| `drip_thickness` | float | hint_range(0.0, 0.2) | 0.05 | How far drips bulge out from the surface, in object units. |
| `drip_count` | int | hint_range(1, 24) | 9 | Number of drips around the outline. |
| `puddle_spread` | float | hint_range(0.0, 1.0) | 0.4 | How far the base spreads outward. |
| `loop_animation` | bool | none | false | Melt and recover over time instead of using `melt`. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A mesh centred on its origin with enough height subdivisions; set `object_height`.

## Output

A wax candle sagging at the top with drips running down its sides and a widened base.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Normals are not recomputed, so lighting on the sagged shape is approximate. Volume is not conserved. Drips are placed by angle around the Y axis, which suits round objects best.

## Technique

- Height-weighted vertex sag with base clamp
- Angular slots with cosine lobes for drips
- Base spread for a puddle
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
