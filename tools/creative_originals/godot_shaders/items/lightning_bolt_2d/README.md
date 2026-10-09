# Procedural lightning bolt with branches

The bolt is a curve x(y): a straight line from start to end plus five octaves of value noise along y, each half as strong and about twice as frequent, which gives the self-similar zigzag of lightning. A sine keeps both ends anchored. A branch leaves the main bolt at a random height and wanders off to one side, thinning out. The distance to these curves gives a sharp core and an exponential glow. Every strike period re-seeds the noise, and the bolt flickers during the visible part.

## When to use it

Use it for storms, spells, tesla coils, electric traps and damage effects in 2D games and UI.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/lightning_bolt_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/lightning_bolt_2d/lightning_bolt_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (1, 1, 1, 1) | Colour of the bolt core. |
| `glow_color` | vec4 | source_color | (0.55, 0.6, 1, 1) | Colour of the surrounding glow. |
| `jaggedness` | float | hint_range(0.0, 0.5) | 0.18 | Sideways displacement of the bolt. |
| `core_width` | float | hint_range(0.001, 0.05) | 0.006 | Width of the bright core in UV units. |
| `glow_width` | float | hint_range(0.01, 0.5) | 0.08 | Reach of the glow in UV units. |
| `strike_rate` | float | hint_range(0.1, 10.0) | 1.5 | Strikes per second; each strike gets a new shape. |
| `visible_share` | float | hint_range(0.05, 1.0) | 0.6 | Share of each strike period the bolt is visible. |
| `branch_amount` | float | hint_range(0.0, 1.0) | 0.6 | Length and brightness of the side branch. |
| `start_x` | float | hint_range(0.0, 1.0) | 0.45 | Horizontal position where the bolt starts at the top. |
| `end_x` | float | hint_range(0.0, 1.0) | 0.55 | Horizontal position where the bolt ends at the bottom. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A white jagged bolt with a blue glow running down the dark rectangle, with one side branch.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Distance is measured horizontally, so near-horizontal bolts thin out; keep bolts mostly vertical or rotate the rectangle. One branch per strike.

## Technique

- Fractal (octave) noise displacement of a line
- Distance-based core and glow
- Re-seeding per strike
- Value noise with quintic interpolation and fractional Brownian motion
