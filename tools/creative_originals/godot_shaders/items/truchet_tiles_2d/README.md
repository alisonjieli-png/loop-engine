# Animated Truchet tile pattern

Each tile contains two quarter circles centred on opposite corners; a hash of the tile picks whether the tile is mirrored. Because every arc meets the tile edge at its midpoint, neighbouring arcs always connect and form long winding paths. The distance to the nearest arc draws the line with derivative anti-aliasing, and an angle-based coordinate along the arc carries pulses of light.

## When to use it

Use it for backgrounds, puzzle and maze art, tech panels, loading screens and decorative borders.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/truchet_tiles_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/truchet_tiles_2d/truchet_tiles_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `line_color` | vec4 | source_color | (0.95, 0.85, 0.55, 1) | Colour of the curves. |
| `background_color` | vec4 | source_color | (0.1, 0.12, 0.2, 1) | Colour between the curves. |
| `flow_color` | vec4 | source_color | (1, 0.4, 0.3, 1) | Colour of the light running along the curves. |
| `cells` | float | hint_range(2.0, 60.0) | 10.0 | Tiles across the rectangle. |
| `line_width` | float | hint_range(0.01, 0.4) | 0.12 | Curve width as a share of a tile. |
| `flow_speed` | float | hint_range(-4.0, 4.0) | 1.0 | Speed of the running light. |
| `flow_spacing` | float | hint_range(0.1, 2.0) | 0.5 | Distance between running light pulses. |
| `seed` | int | hint_range(0, 1000) | 3 | Selects a different random tiling. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

A navy field covered in interlocking cream curves with red pulses travelling along them.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The flow coordinate is continuous within a tile but its direction can reverse between tiles, so pulses do not follow a whole path consistently.

## Technique

- Truchet tiling with quarter-circle arcs (Smith's variant)
- Hashed tile orientation
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
