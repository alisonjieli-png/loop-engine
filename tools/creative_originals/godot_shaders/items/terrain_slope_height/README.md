# Noise terrain with height and slope splatting

The vertex stage samples fBm at the world X and Z position and lifts the vertex by the part above `sea_level`, so lower ground stays flat as water. Two extra samples give finite-difference slopes for the normal. The fragment stage starts from grass, adds a sand band just above sea level, switches to rock where the normal is steeper than `rock_slope`, caps high flat ground with snow above `snow_line`, and paints flat water below sea level.

## When to use it

Use it for quick landscapes, island and level prototypes, strategy map previews and distant scenery; tile several planes, they line up because the noise uses world coordinates.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/terrain_slope_height/`. `material.tres` loads the shader from `res://baltor/godot_shaders/terrain_slope_height/terrain_slope_height.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `height_scale` | float | hint_range(0.0, 5.0) | 1.4 | Height of the tallest land above sea level, in metres. |
| `frequency` | float | hint_range(0.05, 4.0) | 0.45 | Noise frequency per world unit; lower gives broader hills. |
| `noise_octaves` | int | hint_range(1, 8) | 5 | Noise octaves; more gives rougher detail. |
| `sea_level` | float | hint_range(0.0, 1.0) | 0.38 | Normalized height below which the ground is flat water. |
| `water_color` | vec4 | source_color | (0.12, 0.35, 0.55, 1) | Colour of water areas. |
| `sand_color` | vec4 | source_color | (0.82, 0.74, 0.52, 1) | Colour of the beach band. |
| `grass_color` | vec4 | source_color | (0.25, 0.48, 0.18, 1) | Colour of flat low land. |
| `rock_color` | vec4 | source_color | (0.42, 0.38, 0.34, 1) | Colour of steep slopes. |
| `snow_color` | vec4 | source_color | (0.94, 0.96, 1, 1) | Colour of high ground. |
| `sand_band` | float | hint_range(0.0, 0.2) | 0.035 | Height of the beach band above sea level. |
| `rock_slope` | float | hint_range(0.0, 1.0) | 0.78 | Normal Y below which a slope is rock. |
| `snow_line` | float | hint_range(0.0, 1.0) | 0.72 | Normalized height where snow starts. |

## Inputs

- A subdivided PlaneMesh; the demo uses 128 x 128 subdivisions on 8 x 8 metres.

## Output

Rolling green islands with beaches, rocky slopes and snowy peaks in a flat blue sea.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Collision and gameplay height must be computed separately on the CPU with the same noise. Normals come from finite differences with a fixed step and lose detail on very rough settings. Water is flat colour with no waves. Each vertex samples the fBm three times.

## Technique

- Fractional Brownian motion heightfield displacement
- Finite-difference normals
- Height and slope based texture splatting
- Value noise with quintic interpolation and fractional Brownian motion
