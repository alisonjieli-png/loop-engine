# Geometry debug views: normals, tangents, UV, depth

A single integer uniform selects what the surface shows. Directions (world normal, view normal, tangent, binormal) are mapped from -1..1 to colour 0..1, so +X is red, +Y green and +Z blue. UV shows red and green ramps, vertex colour shows the mesh's colour attribute (white when absent), depth shows repeating bands every `depth_band` metres, and world position shows a random colour per world cell. Back faces can be flipped so their normals read like front faces.

## When to use it

Use it to inspect imported meshes (flipped normals, broken tangents, missing vertex colours), check world orientation, and explain shader inputs while building materials.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/normal_debug_view/`. `material.tres` loads the shader from `res://baltor/godot_shaders/normal_debug_view/normal_debug_view.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `mode` | int | hint_range(0, 7) | 0 | 0 world normal, 1 view normal, 2 tangent, 3 binormal, 4 UV, 5 vertex colour, 6 depth bands, 7 world cells. |
| `depth_band` | float | hint_range(0.05, 10.0) | 0.5 | Spacing of the depth bands in metres. |
| `position_cell` | float | hint_range(0.05, 10.0) | 0.25 | Size of the world position cells. |
| `flip_back_faces` | bool | none | true | Show back faces with their normal flipped toward the viewer. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Meshes coloured by their world-space normals (red, green and blue per axis) in the default mode.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Debug output only: unshaded and not meant for final art. Tangent and binormal modes need meshes with tangents. Normals are the interpolated vertex normals after any normal map is ignored.

## Technique

- Direction to colour mapping (n * 0.5 + 0.5)
- Mode switch in one material
