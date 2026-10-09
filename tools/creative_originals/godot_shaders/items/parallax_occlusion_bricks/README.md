# Parallax occlusion mapped procedural bricks

The view direction is expressed in tangent space and the ray is stepped from the surface into a heightfield, `steps` layers deep and `depth_scale` UV units long at the deepest. The heightfield is procedural: staggered brick rows with bevelled edges and sunken mortar. The first layer below the height is refined by linear interpolation with the previous step. The found UV is then used for the colour (mortar or brick with per-brick variation) and for a normal map from height differences.

## When to use it

Use it for walls, floors and paving that need depth on a flat mesh, especially at oblique views where plain normal maps look flat.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/parallax_occlusion_bricks/`. `material.tres` loads the shader from `res://baltor/godot_shaders/parallax_occlusion_bricks/parallax_occlusion_bricks.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `brick_color` | vec4 | source_color | (0.62, 0.26, 0.18, 1) | Base colour of the bricks. |
| `mortar_color` | vec4 | source_color | (0.72, 0.7, 0.66, 1) | Colour of the mortar. |
| `bricks_across` | float | hint_range(1.0, 20.0) | 4.0 | Bricks per UV unit horizontally. |
| `bricks_down` | float | hint_range(1.0, 40.0) | 8.0 | Brick rows per UV unit vertically. |
| `mortar_width` | float | hint_range(0.0, 0.2) | 0.06 | Width of the mortar gap in brick units. |
| `bevel` | float | hint_range(0.0, 0.3) | 0.08 | Width of the rounded brick edge. |
| `depth_scale` | float | hint_range(0.0, 0.2) | 0.05 | Apparent depth of the mortar in UV units. |
| `steps` | int | hint_range(4, 64) | 24 | Ray-march steps; more removes stair artefacts at grazing angles. |
| `color_variation` | float | hint_range(0.0, 1.0) | 0.35 | Per-brick brightness variation. |

## Inputs

- A mesh with UVs and tangents (Godot primitive meshes have both).

## Output

A red brick wall whose mortar lines look recessed and whose bricks occlude each other at angles.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The silhouette stays flat: only the interior of the surface shows depth. Shadows and depth are the flat surface's. Cost grows with `steps`. Strongly curved surfaces bend the illusion. The march runs in UV space, so non-square UV scaling skews the depth.

## Technique

- Parallax occlusion mapping with linear refinement (Tatarchuk 2006)
- Procedural staggered brick heightfield
- Normal map from height differences
