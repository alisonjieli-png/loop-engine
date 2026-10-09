# Radar display with sweep and fading blips

Polar coordinates around the disc centre give the radius and angle. Range rings are thin bands at fractions of the radius and spokes are thin wedges at equal angles. The sweep angle advances with time; how far each pixel lags behind it sets a squared phosphor trail. Blips are hashed into a coarse grid of cells; each one's brightness depends on how long ago the sweep crossed its angle, so it flares at the sweep line and decays over the turn.

## When to use it

Use it for cockpit and console displays, minimaps shown on in-world screens, submarine sonar, and sci-fi user interfaces in 3D.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/radar_sweep_disc/`. `material.tres` loads the shader from `res://baltor/godot_shaders/radar_sweep_disc/radar_sweep_disc.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_color` | vec4 | source_color | (0, 0.06, 0.03, 1) | Background colour of the display. |
| `phosphor_color` | vec4 | source_color | (0.25, 1, 0.45, 1) | Colour of lines, sweep and blips. |
| `sweep_speed` | float | hint_range(-6.0, 6.0) | 1.2 | Rotation speed in radians per second; negative turns the other way. |
| `trail_angle` | float | hint_range(0.1, 6.28) | 1.8 | Angular length of the phosphor trail in radians. |
| `range_rings` | int | hint_range(1, 10) | 4 | Number of range rings. |
| `spokes` | int | hint_range(0, 24) | 8 | Number of radial spokes; 0 hides them. |
| `line_width` | float | hint_range(0.001, 0.05) | 0.006 | Width of rings and spokes in disc units. |
| `blip_density` | float | hint_range(0.0, 1.0) | 0.12 | Share of grid cells that hold a blip. |
| `blip_size` | float | hint_range(0.005, 0.1) | 0.025 | Radius of a blip in disc units. |
| `blip_cells` | float | hint_range(2.0, 40.0) | 10.0 | Grid cells across the disc used to place blips. |

## Inputs

- A quad or disc with UVs spanning 0 to 1. Replace the hashed blips with uniforms or a texture for real contacts.

## Output

A dark green radar screen with rings and spokes, a bright rotating sweep and blips that light up as it passes.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Blips are decorative hash positions, not data. Thin lines alias when the display is small on screen. Unlit, so it ignores scene lighting.

## Technique

- Polar coordinate rings, spokes and sweep
- Angle-lag phosphor decay
- Hashed cell blips
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
