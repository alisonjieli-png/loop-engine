# Parallax fog bands

Each layer samples fBm stretched horizontally, drifting sideways at its own speed so layers slide past each other. A vertical mask makes each layer densest near a ground line and fade upward; deeper layers sit slightly higher and fainter. The summed coverage becomes the alpha of the fog colour.

## When to use it

Use it for misty valleys, swamps, graveyards, mornings over fields and atmospheric parallax backgrounds.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/fog_layers_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/fog_layers_2d/fog_layers_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `fog_color` | vec4 | source_color | (0.85, 0.88, 0.92, 1) | Colour and opacity of the fog. |
| `density` | float | hint_range(0.0, 2.0) | 0.9 | Overall fog opacity. |
| `ground_line` | float | hint_range(0.0, 1.0) | 0.8 | Screen height (0 top, 1 bottom) where fog is densest. |
| `fog_height` | float | hint_range(0.05, 1.0) | 0.45 | How far above the ground line the fog reaches. |
| `drift_speed` | float | hint_range(-0.5, 0.5) | 0.04 | Horizontal drift speed of the nearest layer. |
| `scale` | float | hint_range(0.5, 12.0) | 3.0 | Size of the fog features. |
| `layers` | int | hint_range(1, 6) | 3 | Number of fog layers. |

## Inputs

- A ColorRect above the scene covering the area that should show fog.

## Output

Soft white fog banks drifting across the lower half of the city scene.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Fog does not interact with scene depth: every layer covers everything under it. Large rectangles with many layers cost several fBm evaluations per pixel.

## Technique

- Layered drifting fractional Brownian motion
- Height masks per layer
- Value noise with quintic interpolation and fractional Brownian motion
