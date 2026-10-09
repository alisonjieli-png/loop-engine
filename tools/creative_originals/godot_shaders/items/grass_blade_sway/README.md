# Grass blades swaying in travelling wind gusts

Height along the blade comes from the UV (0 at the root, 1 at the tip of a vertical QuadMesh). The bend grows with the square of the height so roots stay planted. Wind strength is modulated by value noise of the blade's world root position scrolled along the wind direction, so gusts sweep across the field as waves. A per-blade phase from a position hash adds flutter. The push is applied in world space and converted back to object space, with a small drop to keep blade length. Fragments outside a tapering width are discarded to shape the blade.

## When to use it

Use it for grass cards, reeds, wheat and small plants placed as separate meshes or MultiMesh instances.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/grass_blade_sway/`. `material.tres` loads the shader from `res://baltor/godot_shaders/grass_blade_sway/grass_blade_sway.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `root_color` | vec4 | source_color | (0.12, 0.26, 0.08, 1) | Colour at the root. |
| `tip_color` | vec4 | source_color | (0.58, 0.78, 0.3, 1) | Colour at the tip. |
| `wind_angle_degrees` | float | hint_range(0.0, 360.0) | 30.0 | Wind direction around the Y axis. |
| `wind_strength` | float | hint_range(0.0, 1.0) | 0.25 | Bend at the tip at full gust, in metres. |
| `gust_scale` | float | hint_range(0.05, 2.0) | 0.35 | Size of gust patches; lower gives broader gusts. |
| `gust_speed` | float | hint_range(0.0, 5.0) | 1.2 | Speed gusts travel across the field. |
| `flutter` | float | hint_range(0.0, 0.3) | 0.05 | Fast per-blade shiver. |
| `taper` | float | hint_range(0.0, 1.0) | 0.9 | How narrow the blade becomes at the tip. |
| `translucency` | float | hint_range(0.0, 1.0) | 0.4 | Light passing through the blade from behind. |

## Inputs

- Grass cards whose UV v runs from 1 at the root to 0 at the tip (a vertical QuadMesh with its origin at the root, as in the demo); enough vertical subdivisions to bend smoothly.

## Output

A patch of tapered grass blades leaning and waving as gusts pass.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Blades bend but do not keep exact length or collide. Per-blade variation uses the instance origin, so all blades sharing one mesh instance move together. Discard-based shape costs fill rate on dense fields. Shadows follow the moving shape.

## Technique

- Height-weighted vertex bending
- Scrolling world-space value noise gusts
- Position-hash phase variation
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
