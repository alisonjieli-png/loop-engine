# Circuit board traces with travelling pulses

UVs are cut into a grid and a hash assigns each cell one of five kinds: a horizontal run, a vertical run, a corner, a via ring with a drilled pad, or nothing. Distances to the cell's segments or ring give an anti-aliased copper mask. Each trace also has a coordinate along its length; on a hashed share of cells a bright pulse travels along that coordinate over time and is emitted in `pulse_color`.

## When to use it

Use it for sci-fi panels, tech floors, cyber worlds, computer interiors and menu backgrounds.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/circuit_trace_pulses/`. `material.tres` loads the shader from `res://baltor/godot_shaders/circuit_trace_pulses/circuit_trace_pulses.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `board_color` | vec4 | source_color | (0.04, 0.22, 0.12, 1) | Solder mask colour. |
| `copper_color` | vec4 | source_color | (0.78, 0.6, 0.3, 1) | Colour of the copper traces. |
| `pulse_color` | vec4 | source_color | (0.3, 1, 0.9, 1) | Colour of the travelling signals. |
| `cells` | float | hint_range(2.0, 80.0) | 14.0 | Grid cells per UV unit. |
| `trace_width` | float | hint_range(0.02, 0.3) | 0.09 | Width of traces in cell units. |
| `via_radius` | float | hint_range(0.05, 0.4) | 0.18 | Radius of via rings in cell units. |
| `pulse_speed` | float | hint_range(0.0, 5.0) | 1.2 | Pulse speed in trace lengths per second. |
| `pulse_share` | float | hint_range(0.0, 1.0) | 0.45 | Share of traces carrying pulses. |
| `glow` | float | hint_range(0.0, 6.0) | 2.5 | Brightness of the pulses. |

## Inputs

- A mesh with UVs.

## Output

A green board covered in copper lines, corners and rings with cyan sparks running along some lines.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Traces are chosen per cell independently, so many end at cell borders without connecting; it reads as decoration, not a routed circuit. Thin traces alias at small sizes.

## Technique

- Hashed cell tile selection
- Segment and ring distance fields
- Phase-shifted pulses along a trace parameter
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
