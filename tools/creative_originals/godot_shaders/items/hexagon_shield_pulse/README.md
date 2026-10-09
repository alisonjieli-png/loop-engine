# Hexagon shield with travelling pulses

UVs are scaled and folded onto a hexagonal lattice by testing two rectangular grids offset by half a cell and keeping the nearer centre. The hexagon distance of the offset from that centre gives a border mask. A pulse wave sweeps up the object's height and brightens whole bands of cells, a hash of each cell and the current time slot makes a few cells flicker, and a Fresnel rim outlines the shape. Everything is added to the scene behind.

## When to use it

Use it for sci-fi shields, energy domes, force barriers, tech surfaces and holographic armour.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/hexagon_shield_pulse/`. `material.tres` loads the shader from `res://baltor/godot_shaders/hexagon_shield_pulse/hexagon_shield_pulse.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `edge_color` | vec4 | source_color | (0.3, 0.8, 1, 1) | Colour of the hexagon borders. |
| `fill_color` | vec4 | source_color | (0.1, 0.35, 0.8, 1) | Colour of lit cell interiors. |
| `hex_scale` | float | hint_range(2.0, 60.0) | 14.0 | Hexagon rows per UV unit. |
| `edge_width` | float | hint_range(0.0, 0.3) | 0.06 | Width of the border glow in cell units. |
| `pulse_speed` | float | hint_range(-4.0, 4.0) | 0.6 | Speed of the climbing pulse. |
| `pulse_spacing` | float | hint_range(0.1, 4.0) | 1.2 | Distance between pulses in object units of height. |
| `flicker_rate` | float | hint_range(0.0, 20.0) | 3.0 | Flicker time slots per second. |
| `flicker_share` | float | hint_range(0.0, 1.0) | 0.1 | Share of cells lit in each flicker slot. |
| `rim_strength` | float | hint_range(0.0, 2.0) | 0.8 | Brightness of the silhouette rim. |

## Inputs

- A mesh with UVs; on a sphere the cells shrink toward the poles.

## Output

A glowing hexagon-tiled bubble with bands of cells lighting up as pulses climb it.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Cells follow the mesh UVs, so they distort where UVs are stretched (sphere poles, seams). Additive blending cannot darken.

## Technique

- Hexagonal lattice from two offset rectangular grids
- Hexagon distance border mask
- Height-based pulse wave with hashed cell flicker
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
