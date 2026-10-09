# 2D flame with rising turbulence

Coordinates start at the bottom centre of the rectangle. A slow noise bends them sideways more at the top, and five-octave fBm scrolling upward supplies turbulence. A teardrop width that shrinks with height masks the flame. The combined heat value falls with height, so the flame burns out at its tips; four colour stops map heat to colour and alpha fades the cold edge to transparent.

## When to use it

Use it for torches, candles, campfires, burning UI elements and fire on 2D props.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/fire_flame_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/fire_flame_2d/fire_flame_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (1, 0.97, 0.75, 1) | Colour of the hottest core. |
| `inner_color` | vec4 | source_color | (1, 0.75, 0.2, 1) | Colour of the inner flame. |
| `outer_color` | vec4 | source_color | (0.95, 0.3, 0.05, 1) | Colour of the outer flame. |
| `smoke_color` | vec4 | source_color | (0.3, 0.05, 0.02, 1) | Colour of the faint tips before they vanish. |
| `rise_speed` | float | hint_range(0.0, 5.0) | 1.8 | Upward speed of the turbulence. |
| `turbulence` | float | hint_range(0.0, 1.0) | 0.4 | Sideways wobble growing with height. |
| `base_width` | float | hint_range(0.1, 1.0) | 0.5 | Width of the flame at its base, in rectangle widths. |
| `height` | float | hint_range(0.2, 1.2) | 0.85 | Height where the flame closes, in rectangle heights. |
| `noise_scale` | float | hint_range(1.0, 12.0) | 4.0 | Frequency of the turbulence. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A tall flickering flame with a pale core, yellow and orange body and dark red tips.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Flat 2D effect with no light emission; add a PointLight2D to light the scene. The shape is symmetric on average, so very wide flames look like a column.

## Technique

- Height-weighted coordinate wobble
- Rising fractional Brownian motion with heat ramp
- Value noise with quintic interpolation and fractional Brownian motion
