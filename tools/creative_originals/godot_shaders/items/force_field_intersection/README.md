# Force field with glowing contact lines

The shield is unshaded and additive and writes no depth, so the depth texture holds only the opaque scene. For each fragment the shader reconstructs the scene's linear depth behind it and compares it with the shield's own view depth (`-VERTEX.z`). A small gap means the shield touches geometry there, and a band of width `contact_width` lights up. A Fresnel rim modulated by scrolling sine bands adds the outline; back faces are drawn so the far side of the bubble shows.

## When to use it

Use it for shields, barriers, area-of-effect domes, scanner volumes and selection bubbles that should show where they meet the ground and objects.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/force_field_intersection/`. `material.tres` loads the shader from `res://baltor/godot_shaders/force_field_intersection/force_field_intersection.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `field_color` | vec4 | source_color | (0.3, 0.7, 1, 1) | Colour of the field light. |
| `base_strength` | float | hint_range(0.0, 1.0) | 0.06 | Uniform brightness over the whole surface. |
| `rim_power` | float | hint_range(0.5, 8.0) | 3.0 | Exponent of the silhouette glow; higher keeps it thinner. |
| `rim_strength` | float | hint_range(0.0, 4.0) | 1.1 | Brightness of the silhouette glow. |
| `contact_width` | float | hint_range(0.01, 2.0) | 0.18 | Distance in metres over which the contact glow fades. |
| `contact_strength` | float | hint_range(0.0, 8.0) | 2.5 | Brightness of the contact glow. |
| `band_frequency` | float | hint_range(1.0, 60.0) | 14.0 | Number of bands along the UV v axis. |
| `band_speed` | float | hint_range(-4.0, 4.0) | 0.6 | Band scroll speed in bands per second. |
| `band_strength` | float | hint_range(0.0, 1.0) | 0.35 | How much the bands modulate the rim. |

## Inputs

- Opaque geometry intersecting the shield; transparent objects are not in the depth buffer.

## Output

A faint blue bubble with a bright outline, moving bands and bright lines where it cuts the floor and objects.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The contact test compares depths along the view ray, so the glow band widens where the shield meets a surface at a shallow angle. Additive blending cannot darken. Depth reconstruction uses the CURRENT_RENDERER define to pick the depth range convention; only the Compatibility path ran.

## Technique

- Scene depth reconstruction with INV_PROJECTION_MATRIX
- Depth difference intersection glow
- Facing ratio rim with scrolling sine bands
