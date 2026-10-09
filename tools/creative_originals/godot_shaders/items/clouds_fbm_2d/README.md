# Drifting 2D clouds with self-shading

Six octaves of fBm give a cloud density field that drifts with the wind. A smoothstep around `1 - coverage` turns it into cloud shapes with soft edges. A second sample a short step toward the sun estimates whether denser cloud lies between this point and the light; where it does, the colour moves toward `cloud_shadow`, which gives the clouds rounded, lit tops and grey bellies.

## When to use it

Use it for 2D sky backgrounds, parallax layers, weather in side-scrollers and menu screens.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/clouds_fbm_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/clouds_fbm_2d/clouds_fbm_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `sky_top` | vec4 | source_color | (0.25, 0.5, 0.88, 1) | Sky colour at the top. |
| `sky_bottom` | vec4 | source_color | (0.7, 0.85, 0.98, 1) | Sky colour at the bottom. |
| `cloud_light` | vec4 | source_color | (1, 1, 1, 1) | Colour of sunlit cloud parts. |
| `cloud_shadow` | vec4 | source_color | (0.55, 0.6, 0.72, 1) | Colour of shaded cloud parts. |
| `coverage` | float | hint_range(0.0, 1.0) | 0.5 | Share of the sky covered by clouds. |
| `softness` | float | hint_range(0.01, 0.5) | 0.15 | Softness of the cloud edges. |
| `scale` | float | hint_range(0.5, 20.0) | 3.0 | Number of cloud features across the rectangle. |
| `wind_speed` | float | hint_range(-1.0, 1.0) | 0.03 | Drift speed in UV units per second. |
| `sun_angle_degrees` | float | hint_range(0.0, 360.0) | 300.0 | Direction toward the sun in UV space (degrees, 270 is up). |
| `shading` | float | hint_range(0.0, 2.0) | 1.0 | Strength of the self-shading. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A blue sky gradient with white puffy clouds shaded grey on one side.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

One shading step, not light marching, so thick clouds lack depth. Clouds repeat with no structure at very large scales.

## Technique

- Fractional Brownian motion density with coverage threshold
- Offset-sample self-shadowing
- Value noise with quintic interpolation and fractional Brownian motion
