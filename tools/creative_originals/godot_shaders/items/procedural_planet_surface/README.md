# Procedural planet surface with oceans, biomes and ice caps

Every pixel uses the object-space direction of the sphere surface, optionally rotated around Y over time, as the input to 3D noise, so there are no UV seams or pole pinching. Six-octave fBm decides continents against `sea_level`, ridged noise raises mountain chains on land, and ocean colour lightens toward the coast. Land blends from lowland to desert near the equator where a second noise is dry, and to highland with height. Polar caps follow latitude with a noisy edge, and the highest peaks get snow. Water is glossy and land rough. `seed` shifts the noise to a different world.

## When to use it

Use it for planets in space games, strategy maps, menu backdrops and generated worlds; change `seed` for endless variations.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/procedural_planet_surface/`. `material.tres` loads the shader from `res://baltor/godot_shaders/procedural_planet_surface/procedural_planet_surface.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `deep_ocean` | vec4 | source_color | (0.02, 0.08, 0.25, 1) | Colour of deep water. |
| `shallow_ocean` | vec4 | source_color | (0.08, 0.35, 0.55, 1) | Colour of water near coasts. |
| `lowland` | vec4 | source_color | (0.2, 0.42, 0.16, 1) | Colour of fertile low land. |
| `desert` | vec4 | source_color | (0.78, 0.66, 0.4, 1) | Colour of dry equatorial land. |
| `highland` | vec4 | source_color | (0.45, 0.38, 0.3, 1) | Colour of high ground. |
| `ice` | vec4 | source_color | (0.94, 0.96, 1, 1) | Colour of ice caps and snowy peaks. |
| `continent_scale` | float | hint_range(0.5, 8.0) | 1.8 | Size of continents; higher gives more, smaller landmasses. |
| `sea_level` | float | hint_range(0.0, 1.0) | 0.52 | Noise height below which the surface is ocean. |
| `mountain_strength` | float | hint_range(0.0, 1.0) | 0.5 | Height of mountain ridges on land. |
| `ice_latitude` | float | hint_range(0.0, 1.0) | 0.78 | Absolute latitude (0 equator, 1 pole) where caps begin. |
| `desert_band` | float | hint_range(0.0, 1.0) | 0.3 | Latitude range around the equator that can be desert. |
| `spin_speed` | float | hint_range(-1.0, 1.0) | 0.05 | Rotation of the pattern around Y in radians per second. |
| `seed` | int | hint_range(0, 1000) | 7 | Offset that selects a different planet. |

## Inputs

- A sphere centred on its origin (directions come from vertex positions).

## Output

A rotating Earth-like planet with blue oceans, green and tan continents, brown highlands and white poles.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Colour only: the surface is not displaced and has no normal relief. About thirteen octaves of 3D value noise per pixel are costly for full-screen planets. Biomes follow simple rules (height, latitude, one dryness noise), not climate.

## Technique

- 3D fractional Brownian motion on the unit sphere
- Ridged noise mountain chains
- Height and latitude biome rules
- Value noise with quintic interpolation and fractional Brownian motion
