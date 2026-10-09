# UV checker with direction ramps and stretch map

UVs scaled by `cells` give a checker whose colours are tinted by two ramps: red grows along U and green along V, so the direction and seams of the layout are obvious. Each cell has a red marker in its lowest U and V corner, which shows mirroring and rotation. Cell borders are drawn with derivative anti-aliasing. With `show_stretch` the screen-space rates of change of U and V are compared: green where texels are square, red where U is stretched, blue where V is.

## When to use it

Use it while unwrapping and importing models, to find flipped islands, seams, mismatched texel density and stretched UVs before texturing.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/uv_checker_grid/`. `material.tres` loads the shader from `res://baltor/godot_shaders/uv_checker_grid/uv_checker_grid.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `cells` | float | hint_range(1.0, 64.0) | 8.0 | Checker cells per UV unit. |
| `dark_color` | vec4 | source_color | (0.18, 0.18, 0.2, 1) | Dark checker colour. |
| `light_color` | vec4 | source_color | (0.82, 0.82, 0.85, 1) | Light checker colour. |
| `direction_tint` | float | hint_range(0.0, 1.0) | 0.45 | Strength of the U and V colour ramps. |
| `line_pixels` | float | hint_range(0.0, 4.0) | 1.0 | Width of the cell border lines in pixels. |
| `show_stretch` | bool | none | false | Overlay the stretch heat map. |
| `stretch_range` | float | hint_range(1.0, 8.0) | 3.0 | Stretch ratio shown as full red or full blue. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Objects covered in a tinted checker with corner markers that reveal the UV direction on every face.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The stretch map compares screen-space derivatives, so it depends on the viewing angle; judge stretch facing the surface. UVs outside 0 to 1 repeat the ramps. Unshaded, so it shows no lighting.

## Technique

- Checker with directional ramps and corner markers
- Derivative anti-aliased cell lines
- UV stretch ratio from screen-space derivatives
