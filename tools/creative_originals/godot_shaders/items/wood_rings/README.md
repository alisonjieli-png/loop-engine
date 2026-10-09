# Procedural wood with growth rings and grain

The trunk axis is the object Z axis, slightly tilted by `axis_tilt_degrees` so planks show the familiar arches. The distance from that axis, wobbled by stretched 3D noise, is divided into rings; the late part of each ring becomes a dark band whose sharpness is adjustable, and each ring gets its own brightness from a hash. Fine value noise stretched along the axis adds grain streaks. Because everything is a function of 3D position, cut faces show rings and long faces show flame-like grain.

## When to use it

Use it for planks, furniture, crates, logs, handles and wooden props, especially procedurally cut or generated geometry without UVs.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/wood_rings/`. `material.tres` loads the shader from `res://baltor/godot_shaders/wood_rings/wood_rings.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `early_wood` | vec4 | source_color | (0.78, 0.56, 0.34, 1) | Colour of the light part of each ring. |
| `late_wood` | vec4 | source_color | (0.45, 0.26, 0.13, 1) | Colour of the dark band of each ring. |
| `ring_density` | float | hint_range(1.0, 60.0) | 18.0 | Rings per object unit of radius. |
| `ring_sharpness` | float | hint_range(0.0, 1.0) | 0.7 | How narrow and sharp the dark bands are. |
| `distortion` | float | hint_range(0.0, 2.0) | 0.6 | Irregularity of the rings. |
| `grain_density` | float | hint_range(10.0, 400.0) | 140.0 | Frequency of the grain streaks across the axis. |
| `grain_strength` | float | hint_range(0.0, 1.0) | 0.25 | Contrast of the grain streaks. |
| `axis_tilt_degrees` | float | hint_range(0.0, 45.0) | 4.0 | Tilt of the trunk axis around X. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.65 | Surface roughness. |

## Inputs

- A mesh whose object Z axis runs along the grain (rotate the node to change it).

## Output

A plank with arched grain on top and a log end showing concentric growth rings.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Solid texture in object space: scaling the object scales the rings. No knots, pores or normal relief. Rings are centred on the object origin; offset the mesh to move the pith.

## Technique

- Solid (3D) texturing
- Distance-from-axis growth rings with noise distortion
- Axis-stretched value noise grain
- Value noise with quintic interpolation and fractional Brownian motion
