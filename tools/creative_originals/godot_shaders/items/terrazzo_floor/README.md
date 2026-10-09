# Terrazzo with random coloured chips

World X and Z are divided into jittered cells; a hash decides whether each cell holds a chip and how large it is. Each pixel finds the chip with the smallest distance scaled by its size, so large chips claim more space and small ones stay small. Value noise roughens the chip edges, a hash picks one of four chip colours with brightness variation, and the cement between chips gets a fine dark speckle.

## When to use it

Use it for floors, counters, stairs and walls in interiors, shops and architectural visualization.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/terrazzo_floor/`. `material.tres` loads the shader from `res://baltor/godot_shaders/terrazzo_floor/terrazzo_floor.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `matrix_color` | vec4 | source_color | (0.88, 0.86, 0.82, 1) | Colour of the cement between chips. |
| `chip_a` | vec4 | source_color | (0.85, 0.45, 0.35, 1) | First chip colour. |
| `chip_b` | vec4 | source_color | (0.25, 0.42, 0.55, 1) | Second chip colour. |
| `chip_c` | vec4 | source_color | (0.9, 0.78, 0.45, 1) | Third chip colour. |
| `chip_d` | vec4 | source_color | (0.28, 0.28, 0.3, 1) | Fourth chip colour. |
| `chip_scale` | float | hint_range(1.0, 60.0) | 12.0 | Chip cells per world unit. |
| `chip_density` | float | hint_range(0.0, 1.0) | 0.65 | Share of cells that hold a chip. |
| `chip_size` | float | hint_range(0.1, 0.6) | 0.38 | Typical chip radius in cell units. |
| `edge_roughness` | float | hint_range(0.0, 0.3) | 0.12 | Irregularity of the chip edges. |
| `speckle` | float | hint_range(0.0, 1.0) | 0.35 | Darkness of the fine speckle in the cement. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.25 | Roughness of the polished surface. |

## Inputs

- A horizontal surface; the pattern uses world X and Z.

## Output

A pale polished floor scattered with irregular terracotta, blue, ochre and grey chips.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Chips are limited to neighbouring cells, so a chip larger than about one cell is clipped. Projected from above in world space, so walls show stretched chips. Flat: no relief between chips and matrix.

## Technique

- Size-weighted jittered Voronoi chips
- Noise-perturbed chip edges
- Hashed palette selection
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
