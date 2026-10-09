# Low-poly flat shading with per-facet colour

The cross product of the screen-space derivatives of the view-space position is the true normal of the triangle being drawn, so writing it as the normal flattens smooth shading into facets on any mesh. A hash of the quantized face normal brightens or darkens each facet slightly, a world-height gradient colours the object from bottom to top, and the vertex stage nudges vertices by a hash of their position (shared vertices move together, so the mesh stays closed).

## When to use it

Use it for low-poly art styles, stylized terrain and rocks, and to give imported smooth meshes a faceted look without re-exporting them.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/low_poly_flat_shading/`. `material.tres` loads the shader from `res://baltor/godot_shaders/low_poly_flat_shading/low_poly_flat_shading.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `low_color` | vec4 | source_color | (0.18, 0.42, 0.3, 1) | Colour at `gradient_bottom` height. |
| `high_color` | vec4 | source_color | (0.85, 0.82, 0.55, 1) | Colour at `gradient_top` height. |
| `gradient_bottom` | float | hint_range(-5.0, 5.0) | -0.6 | World height where the gradient starts. |
| `gradient_top` | float | hint_range(-5.0, 5.0) | 0.6 | World height where the gradient ends. |
| `facet_variation` | float | hint_range(0.0, 0.5) | 0.12 | Brightness variation between facets. |
| `jitter` | float | hint_range(0.0, 0.3) | 0.06 | Random vertex displacement in object units. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.9 | Surface roughness. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A faceted sphere with visibly flat triangles shaded in greens fading to sand at the top.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Derivative normals are per 2 x 2 pixel block, so tiny triangles get noisy normals. Jitter moves vertices by a hash of their quantized position: vertices closer than 1/50 object unit can merge their offsets. Shadows use the jittered shape.

## Technique

- Face normals from screen-space derivatives (cross of dFdx and dFdy)
- Hashed per-facet colour variation
- Position-hashed vertex jitter
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
