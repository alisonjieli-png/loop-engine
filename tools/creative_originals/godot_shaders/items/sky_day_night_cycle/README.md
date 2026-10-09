# Day and night sky driven by the sun height

The shader reads the first directional light (`LIGHT0_DIRECTION`) as the sun. Its elevation drives a day factor that blends night and day zenith and horizon colours, and a dusk factor that peaks when the sun is near the horizon and pushes the horizon toward `sunset_glow`, more strongly on the side facing the sun. A sun disc of angular radius `sun_size` and a halo follow the light. Stars come from a hash of a 3D grid over view directions, twinkle with `TIME`, and fade in as the day factor drops.

## When to use it

Use it for games with a time of day: rotate the DirectionalLight3D and the sky follows. It also works as a fixed stylized sky when the light is static.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sky_day_night_cycle/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sky_day_night_cycle/sky_day_night_cycle.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Create a Sky resource, set `material.tres` as its `sky_material`, and use the Sky in an Environment whose Background Mode is Sky. A DirectionalLight3D in the scene provides the sun direction where the shader reads it.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `day_zenith` | vec4 | source_color | (0.16, 0.38, 0.82, 1) | Colour straight up in full day. |
| `day_horizon` | vec4 | source_color | (0.62, 0.78, 0.95, 1) | Colour at the horizon in full day. |
| `sunset_glow` | vec4 | source_color | (1, 0.48, 0.2, 1) | Horizon and halo colour when the sun is low. |
| `night_zenith` | vec4 | source_color | (0.01, 0.015, 0.05, 1) | Colour straight up at night. |
| `night_horizon` | vec4 | source_color | (0.05, 0.07, 0.16, 1) | Colour at the horizon at night. |
| `ground_color` | vec4 | source_color | (0.16, 0.15, 0.14, 1) | Colour below the horizon, darkened at night. |
| `horizon_falloff` | float | hint_range(0.5, 10.0) | 3.0 | Exponent of the zenith to horizon blend; higher keeps the horizon colour lower. |
| `sun_size` | float | hint_range(0.001, 0.2) | 0.03 | Angular radius of the sun disc in radians. |
| `halo_strength` | float | hint_range(0.0, 4.0) | 0.8 | Brightness of the glow around the sun. |
| `star_density` | float | hint_range(0.0, 1.0) | 0.35 | Share of grid cells that hold a star. |
| `star_brightness` | float | hint_range(0.0, 4.0) | 1.4 | Brightness of the stars at full night. |

## Inputs

- A DirectionalLight3D in the scene. Its direction is the sun; without one the sun sits at a fixed low angle.

## Output

A gradient sky with a sun and halo that changes from day blue through an orange sunset to a starry night as the light's elevation changes.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Stylized, not a physical atmosphere: colours come from the uniforms, not from scattering. Stars are point-like only at moderate field of view; at very wide angles grid cells can show. Only the first directional light is read. Sky radiance for reflections updates with Godot's sky process mode.

## Technique

- Elevation-driven colour blending
- Angular sun disc with smoothstep edge
- Hashed 3D grid star field on view directions
