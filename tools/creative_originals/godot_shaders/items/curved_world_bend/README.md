# Curved world bend by camera distance

Each vertex is moved in world space: its horizontal distance from the camera, minus a flat radius, is squared and scaled by `curvature` and subtracted from its height, and optionally added sideways for a curving road. The vertex is converted back to object space, so the effect works on any mesh with this material while gameplay positions stay flat. The fragment stage draws a world-space checker so the bend is visible.

## When to use it

Use it for endless runners, cosy small-world games, horizon drop-off effects and stylized racing; add the vertex function to every material in the scene for a consistent bend.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/curved_world_bend/`. `material.tres` loads the shader from `res://baltor/godot_shaders/curved_world_bend/curved_world_bend.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `curvature` | float | hint_range(0.0, 0.2) | 0.02 | Downward bend per square metre of distance. |
| `sideways_curvature` | float | hint_range(-0.2, 0.2) | 0.0 | Sideways bend per square metre of distance; 0 keeps the road straight. |
| `flat_radius` | float | hint_range(0.0, 20.0) | 2.0 | Distance around the camera that stays flat, in metres. |
| `color_a` | vec4 | source_color | (0.85, 0.82, 0.75, 1) | First checker colour. |
| `color_b` | vec4 | source_color | (0.35, 0.55, 0.75, 1) | Second checker colour. |
| `checker_size` | float | hint_range(0.1, 10.0) | 1.0 | Checker cell size in world units. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.8 | Surface roughness. |

## Inputs

- Meshes with enough vertices along the bend (the demo road has 200 rows); other scene materials need the same vertex code to match.

## Output

A checkered road and blocks that curve down and to the side toward the horizon.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Visual only: physics, raycasts and culling use the unbent positions, so objects near the frustum edge can pop. Normals are not updated for the bend. Large flat polygons do not bend; subdivide them.

## Technique

- World-space quadratic vertex bend by camera distance
- World checker pattern
