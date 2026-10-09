# Lava lamp metaballs

Each metaball contributes `size^2 / distance^2` to a field; where the sum passes `threshold` the pixel is inside a blob, so nearby balls fuse smoothly. Centres move along Lissajous curves with different rates. The field's finite-difference gradient acts as a surface normal for a highlight, and the field just outside the surface adds a glow.

## When to use it

Use it for lava lamps, slime and liquid UI backgrounds, organic loading animations and music visualizers.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/metaball_blobs_2d/`. `material.tres` loads the shader from `res://baltor/godot_shaders/metaball_blobs_2d/metaball_blobs_2d.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `blob_color` | vec4 | source_color | (1, 0.35, 0.25, 1) | Colour of the blobs. |
| `highlight_color` | vec4 | source_color | (1, 0.85, 0.45, 1) | Colour of lit blob tops. |
| `background_top` | vec4 | source_color | (0.2, 0.05, 0.3, 1) | Background colour at the top. |
| `background_bottom` | vec4 | source_color | (0.45, 0.08, 0.25, 1) | Background colour at the bottom. |
| `blob_count` | int | hint_range(1, 12) | 7 | Number of metaballs. |
| `blob_size` | float | hint_range(0.01, 0.2) | 0.06 | Radius scale of each metaball in UV units. |
| `threshold` | float | hint_range(0.5, 4.0) | 1.0 | Field value where the surface lies; higher shrinks the blobs. |
| `speed` | float | hint_range(0.0, 3.0) | 0.4 | Speed of the blobs along their paths. |
| `rim_glow` | float | hint_range(0.0, 2.0) | 0.6 | Glow around the blobs. |

## Inputs

- A ColorRect (or any CanvasItem) sized to the area to fill; UVs span 0 to 1 across it.

## Output

Orange blobs with yellow highlights flowing and merging over a purple gradient.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Cost grows with blob count times three field evaluations per pixel. Blobs are 2D: no occlusion or depth.

## Technique

- Metaballs (summed inverse-square field, after Blinn 1982)
- Lissajous motion paths
- Gradient-based shading
