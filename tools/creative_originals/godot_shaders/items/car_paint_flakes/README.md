# Two-tone car paint with metal flakes and clear coat

The base colour blends from `face_color` where the surface faces the viewer to `edge_color` at grazing angles, the colour flip of pearl and candy paints. Object space is cut into tiny cubic cells; a hash keeps a share of them as flakes and gives each a random direction. Flake pixels get a normal tilted toward that direction, full metalness and low roughness, so Godot's own lighting makes each flake flash at a different angle. The clear coat outputs add a second glossy layer on top.

## When to use it

Use it for vehicles, toys, helmets, guitars and other lacquered metallic surfaces.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/car_paint_flakes/`. `material.tres` loads the shader from `res://baltor/godot_shaders/car_paint_flakes/car_paint_flakes.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `face_color` | vec4 | source_color | (0.55, 0.04, 0.08, 1) | Paint colour seen head-on. |
| `edge_color` | vec4 | source_color | (0.18, 0.02, 0.12, 1) | Paint colour at grazing angles. |
| `flip_power` | float | hint_range(0.5, 6.0) | 1.6 | How far the face colour reaches toward the edges. |
| `base_roughness` | float | hint_range(0.0, 1.0) | 0.38 | Roughness of the paint between flakes. |
| `flake_density` | float | hint_range(0.0, 1.0) | 0.12 | Share of cells that hold a flake. |
| `flake_scale` | float | hint_range(50.0, 2000.0) | 900.0 | Flake cells per object unit; higher gives finer glitter. |
| `flake_tilt` | float | hint_range(0.0, 1.0) | 0.35 | How far flake normals deviate from the surface normal. |
| `flake_color` | vec4 | source_color | (1, 0.9, 0.85, 1) | Tint of the flakes. |
| `clearcoat_amount` | float | hint_range(0.0, 1.0) | 1.0 | Strength of the clear coat layer. |
| `clearcoat_gloss` | float | hint_range(0.0, 1.0) | 0.95 | Gloss of the clear coat (1 minus its roughness). |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Deep red paint that turns purple at the edges, sparkling with tiny flakes under a glossy coat.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Flakes are one pixel or smaller at a distance and then shimmer; they are not filtered. Flake size is tied to object units, so scaled objects need a different `flake_scale`. The clear coat outputs depend on renderer support; the Compatibility run showed the base and flakes.

## Technique

- Facing-ratio colour flip
- Hashed object-space flake cells with perturbed normals
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
- Clear coat layer through CLEARCOAT outputs
