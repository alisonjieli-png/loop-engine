# Lit smoke puff on a camera-facing card

The quad faces the camera through the vertex stage. A three-dimensional fBm, with time as the third axis, churns the puff shape and its density, and alpha falls off with a noise-wobbled radius. Instead of the flat card normal, the fragment writes a view-space sphere normal (blended by `roundness`) bent by finite differences of the noise, so Godot's own lights shade the puff with a lit side, a shadow side and lumpy detail.

## When to use it

Use it for smoke columns, dust clouds, explosions' aftermath and steam, alone or as the draw material of particles (the billboard works per instance).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/smoke_billboard/`. `material.tres` loads the shader from `res://baltor/godot_shaders/smoke_billboard/smoke_billboard.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `smoke_color` | vec4 | source_color | (0.62, 0.62, 0.65, 1) | Albedo of the smoke. |
| `density` | float | hint_range(0.0, 2.0) | 1.0 | Opacity multiplier. |
| `noise_scale` | float | hint_range(0.5, 12.0) | 3.5 | Frequency of the puff detail. |
| `churn_speed` | float | hint_range(0.0, 3.0) | 0.35 | Speed the noise evolves. |
| `softness` | float | hint_range(0.05, 1.0) | 0.45 | Width of the soft outer falloff. |
| `roundness` | float | hint_range(0.0, 1.0) | 0.7 | Blend from a flat facing normal (0) to a full sphere normal (1). |
| `detail_normal` | float | hint_range(0.0, 2.0) | 0.6 | Strength of the noise in the normal. |

## Inputs

- A QuadMesh; scene lights shade it.

## Output

A grey puff of smoke lit from one side with soft, churning edges.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Lit as a single sphere-like shell, not as a volume: no self-shadowing or light scattering. Overlapping puffs are sorted per object, not per pixel. Seven fBm evaluations of four octaves per pixel cost a lot on large puffs.

## Technique

- Spherical billboard
- Fake sphere normals on a card for lighting
- Finite-difference noise normals
- Value noise with quintic interpolation and fractional Brownian motion in 3D (space and time)
