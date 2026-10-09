# Wet cobblestones with rain puddles and ripples

Cobblestones are Voronoi cells in world X and Z; the border between nearest and second nearest cell gives grout, and each cell gets its own brightness. `wetness` darkens albedo and lowers roughness everywhere. A fractal noise mask plus a grout bonus marks low areas that become mirror-smooth puddles. Inside puddles, every cell of a ripple grid emits an expanding ring at a random phase; the ring profile's slope bends the normal map so drops ripple the reflections.

## When to use it

Use it for rainy streets, courtyards and paths; animate `wetness` and `puddle_amount` as rain starts and stops.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/wet_puddles/`. `material.tres` loads the shader from `res://baltor/godot_shaders/wet_puddles/wet_puddles.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `stone_color` | vec4 | source_color | (0.5, 0.46, 0.42, 1) | Base colour of the stones. |
| `grout_color` | vec4 | source_color | (0.22, 0.2, 0.18, 1) | Colour of the gaps between stones. |
| `stone_scale` | float | hint_range(1.0, 40.0) | 7.0 | Stones per world unit. |
| `grout_width` | float | hint_range(0.0, 0.3) | 0.08 | Width of the gaps in cell units. |
| `wetness` | float | hint_range(0.0, 1.0) | 0.6 | Darkening and gloss from rain over the whole surface. |
| `puddle_amount` | float | hint_range(0.0, 1.0) | 0.45 | Share of the ground covered by puddles. |
| `puddle_scale` | float | hint_range(0.1, 10.0) | 0.8 | Frequency of the puddle mask in world units. |
| `puddle_tint` | vec4 | source_color | (0.16, 0.17, 0.19, 1) | Colour of the water in puddles. |
| `ripple_strength` | float | hint_range(0.0, 1.0) | 0.5 | Normal tilt of the raindrop rings. |
| `ripple_density` | float | hint_range(1.0, 30.0) | 6.0 | Ripple cells per world unit. |
| `ripple_speed` | float | hint_range(0.1, 4.0) | 1.2 | Rings per second in each cell. |

## Inputs

- A horizontal surface; the pattern uses world X and Z.

## Output

Dark glossy cobblestones with flat reflective puddles that ripple under falling drops.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Puddles are flat colour with sky and sun reflections only; scene reflections need a ReflectionProbe or screen-space reflections (Forward+). Ripples are a normal-map effect; the surface is not displaced. Designed for horizontal ground: walls get stretched stones.

## Technique

- Voronoi cobblestones with F2 - F1 grout
- Noise-masked puddles
- Expanding ring ripples as normal map slopes
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
