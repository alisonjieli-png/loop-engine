# Stained glass window from Voronoi cells

Voronoi cells of the UV plane become glass panes: the cell's random value picks one of four glass colours, and two octaves of noise mottle the colour like hand-made glass. Where the distances to the nearest and second nearest cell points are close, a dark lead came line is drawn, and the outer border of the UV square gets a frame. The glass is emitted at `backlight` strength as if daylight shone through, and is slightly transparent.

## When to use it

Use it for church and castle windows, lamps, magical doors, puzzle panels and decorative glass.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/stained_glass_cells/`. `material.tres` loads the shader from `res://baltor/godot_shaders/stained_glass_cells/stained_glass_cells.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `glass_a` | vec4 | source_color | (0.75, 0.12, 0.15, 1) | First glass colour. |
| `glass_b` | vec4 | source_color | (0.12, 0.3, 0.75, 1) | Second glass colour. |
| `glass_c` | vec4 | source_color | (0.95, 0.75, 0.15, 1) | Third glass colour. |
| `glass_d` | vec4 | source_color | (0.15, 0.55, 0.25, 1) | Fourth glass colour. |
| `lead_color` | vec4 | source_color | (0.06, 0.06, 0.07, 1) | Colour of the lead lines and frame. |
| `cell_scale` | float | hint_range(1.0, 30.0) | 6.0 | Panes per UV unit. |
| `lead_width` | float | hint_range(0.0, 0.3) | 0.07 | Width of the lead lines in cell units. |
| `backlight` | float | hint_range(0.0, 4.0) | 1.6 | Brightness of light shining through the glass. |
| `mottling` | float | hint_range(0.0, 1.0) | 0.35 | Colour unevenness inside each pane. |
| `glass_opacity` | float | hint_range(0.0, 1.0) | 0.85 | Opacity of the glass panes. |

## Inputs

- A quad or window mesh with UVs spanning the window.

## Output

A glowing window of irregular red, blue, gold and green panes framed by black lead.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Panes are random cells, not a designed picture. The glow is emission, not light cast into the room; pair it with a light or a projected texture for coloured light on the floor. Transparency is not sorted per pixel.

## Technique

- Voronoi panes with F2 - F1 lead lines
- Palette selection by cell hash
- Emission as backlight
- Value noise with quintic interpolation and fractional Brownian motion
