# Ice with surface and inner Voronoi cracks

Crack lines are the borders of Voronoi cells, found where the distances to the nearest and second nearest feature points are almost equal. A second, differently scaled crack layer is sampled at UVs shifted by the view direction in tangent space, so it slides against the surface layer as the camera moves and reads as cracks inside the ice. The body colour deepens where the surface faces the viewer, and a weak emissive Fresnel rim gives a frosty edge.

## When to use it

Use it for ice blocks, frozen lakes, crystals of frost, glaciers and frozen props in stylized or semi-realistic scenes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/ice_crack_voronoi/`. `material.tres` loads the shader from `res://baltor/godot_shaders/ice_crack_voronoi/ice_crack_voronoi.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `ice_color` | vec4 | source_color | (0.62, 0.82, 0.95, 1) | Colour of thin ice at grazing angles. |
| `deep_color` | vec4 | source_color | (0.12, 0.32, 0.58, 1) | Colour of ice seen head-on. |
| `crack_color` | vec4 | source_color | (0.95, 0.98, 1, 1) | Colour of the crack lines. |
| `cell_scale` | float | hint_range(1.0, 30.0) | 5.0 | Number of crack cells across the UV range. |
| `crack_width` | float | hint_range(0.0, 0.2) | 0.035 | Width of the crack lines in cell units. |
| `inner_depth` | float | hint_range(0.0, 0.5) | 0.15 | Apparent depth of the inner crack layer. |
| `inner_strength` | float | hint_range(0.0, 1.0) | 0.55 | Visibility of the inner cracks. |
| `frost_rim` | float | hint_range(0.0, 4.0) | 1.2 | Brightness of the frosty edge glow. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.12 | Roughness of the ice away from the cracks. |

## Inputs

- A mesh with UVs and tangents (Godot primitive meshes have both).

## Output

Pale blue ice with bright fracture lines on top and fainter fractures that shift inside as you move.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The inner layer is a single parallax offset, not refraction or real volume; at grazing angles it smears. Not transparent; objects behind the ice are not visible. Crack density follows the mesh UVs, so stretched UVs give stretched cells.

## Technique

- Voronoi (Worley) cell borders from F2 - F1
- Tangent-space parallax offset for a second layer
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
