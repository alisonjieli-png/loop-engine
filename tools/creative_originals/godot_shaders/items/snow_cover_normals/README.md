# Snow cover on upward-facing surfaces

Coverage compares the world-space normal's Y component with a threshold set by `snow_amount`: 0 leaves the mesh bare, 0.5 covers surfaces facing up to the horizon, 1 covers everything. Fractal noise added to the normal term wobbles the snow line. The same coverage pushes vertices out along the normal by `snow_lift` so snow sits on top of edges. Hashed world cells add tiny glints that brighten when the reflected view lines up with a fixed light direction.

## When to use it

Use it for winter versions of props and terrain without new textures, for snowfall that builds up over time (animate `snow_amount`), and for frosted tops of rocks and roofs.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/snow_cover_normals/`. `material.tres` loads the shader from `res://baltor/godot_shaders/snow_cover_normals/snow_cover_normals.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `base_color` | vec4 | source_color | (0.36, 0.3, 0.26, 1) | Colour of the uncovered surface. |
| `base_roughness` | float | hint_range(0.0, 1.0) | 0.85 | Roughness of the uncovered surface. |
| `base_pattern_scale` | float | hint_range(0.5, 40.0) | 12.0 | Frequency of the grain pattern on the uncovered surface. |
| `snow_color` | vec4 | source_color | (0.95, 0.97, 1, 1) | Colour of the snow. |
| `snow_amount` | float | hint_range(0.0, 1.0) | 0.55 | How far down from straight up the snow reaches (0 to 1). |
| `snow_sharpness` | float | hint_range(0.01, 0.5) | 0.06 | Softness of the snow border. |
| `noise_scale` | float | hint_range(0.5, 30.0) | 5.0 | Frequency of the noise on the snow border in world units. |
| `noise_strength` | float | hint_range(0.0, 1.0) | 0.35 | How strongly the noise moves the border. |
| `snow_lift` | float | hint_range(0.0, 0.1) | 0.015 | Vertex push along the normal under the snow, in object units. |
| `sparkle_density` | float | hint_range(0.0, 1.0) | 0.25 | Share of world cells that glint. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Rock-coloured objects with white snow caps on their tops and upward slopes, with small glints.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Coverage ignores occlusion: surfaces under overhangs still get snow if they face up. The vertex lift needs smooth normals and enough vertices; on hard-edged meshes it opens seams. Sparkle direction is fixed, not tied to the scene light.

## Technique

- World-space normal coverage mask
- 3D value noise border perturbation
- Hashed glints
