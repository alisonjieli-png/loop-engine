# Twist deformation around the vertical axis

Each vertex is rotated around the object Y axis by an angle proportional to its height above `pivot_height`, so the bottom stays put and the top turns furthest. A sine of time scales an extra angle for a wobbling twist. Normals and tangents get the same rotation, which keeps lighting close to right for moderate twists. Stripes are computed from the undeformed position, so they wind around the shape and show the twist.

## When to use it

Use it for screws, drills, candy, twisted columns, tornado meshes, magical totems and cartoon squash and twist animation.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/twist_deform/`. `material.tres` loads the shader from `res://baltor/godot_shaders/twist_deform/twist_deform.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.85, 0.55, 0.25, 1) | Main colour. |
| `stripe_color` | vec4 | source_color | (0.3, 0.15, 0.08, 1) | Colour of the stripes that reveal the twist. |
| `twist_degrees_per_unit` | float | hint_range(-720.0, 720.0) | 160.0 | Twist angle per object unit of height. |
| `pivot_height` | float | hint_range(-5.0, 5.0) | -0.6 | Object height that does not rotate. |
| `wobble_degrees` | float | hint_range(0.0, 180.0) | 30.0 | Extra twist that oscillates over time, per unit of height. |
| `wobble_speed` | float | hint_range(0.0, 10.0) | 1.5 | Speed of the wobble. |
| `stripes` | float | hint_range(0.0, 20.0) | 6.0 | Stripe count across the object (0 removes them). |
| `roughness` | float | hint_range(0.0, 1.0) | 0.5 | Surface roughness. |

## Inputs

- A mesh with enough vertical subdivisions (the demo box uses 48).

## Output

An orange and brown striped bar twisted into a spiral that winds back and forth.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Normals ignore the shear term of the twist, so strong twists look slightly off in lighting. Collision and culling use the untwisted shape. Low vertex counts produce faceted spirals.

## Technique

- Height-proportional rotation about an axis (twist modifier)
- Rotating normals and tangents with the vertex
