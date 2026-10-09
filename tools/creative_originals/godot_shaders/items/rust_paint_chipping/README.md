# Painted metal with chips, rust and streaks

Three masks come from 3D noise in world space. Where fractal noise passes a threshold set by `chipping`, the paint is gone and bare metal shows (metallic and smoother). A band of the same noise just below the threshold becomes rust around each chip. A second noise stretched vertically by `streak_length` adds rust streaks that run down the surface. Rust colour varies between a light and a dark tone, and roughness follows the layers.

## When to use it

Use it for barrels, machinery, vehicles, ships, railings and post-apocalyptic props that need wear without texture painting.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/rust_paint_chipping/`. `material.tres` loads the shader from `res://baltor/godot_shaders/rust_paint_chipping/rust_paint_chipping.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `paint_color` | vec4 | source_color | (0.2, 0.42, 0.35, 1) | Colour of the intact paint. |
| `metal_color` | vec4 | source_color | (0.62, 0.62, 0.64, 1) | Colour of bare metal under chips. |
| `rust_color` | vec4 | source_color | (0.48, 0.22, 0.08, 1) | Light rust colour. |
| `rust_dark` | vec4 | source_color | (0.22, 0.1, 0.05, 1) | Dark rust colour. |
| `scale` | float | hint_range(0.5, 20.0) | 4.0 | Noise scale per world unit. |
| `chipping` | float | hint_range(0.0, 1.0) | 0.35 | Share of the surface where paint has flaked off. |
| `rust_spread` | float | hint_range(0.0, 0.5) | 0.12 | Width of the rust band around chips. |
| `streak_amount` | float | hint_range(0.0, 1.0) | 0.5 | Strength of the downward rust streaks. |
| `streak_length` | float | hint_range(0.5, 10.0) | 3.0 | Vertical stretch of the streaks. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Green painted shapes with silver chipped patches ringed by rust and faint rust runs.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Wear is placed by noise, not by edges or cavities, so it does not favour corners. World-space masks slide over moving objects; switch to object space for props that move. No relief between paint and metal.

## Technique

- Layered thresholds of 3D fBm for paint, metal and rust
- Vertically stretched noise for streaks
- Value noise with quintic interpolation and fractional Brownian motion
