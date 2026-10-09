# Inverted hull outline pass

The pass renders only back faces (`cull_front`) after pushing every vertex out along its normal by `thickness` in object units. Where the enlarged back faces show around the original mesh they read as an outline. `distance_scaling` multiplies the width by the view distance so the line stays closer to a constant pixel width as the object moves away, capped by `max_thickness`.

## When to use it

Use it on characters and props in toon or comic styles, together with any base material (for example `toon_band_rim`). It is cheap and per object, unlike a full-screen edge pass.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/outline_inverted_hull/`. `material.tres` loads the shader from `res://baltor/godot_shaders/outline_inverted_hull/outline_inverted_hull.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Set `material.tres` as the `next_pass` of the mesh's existing material. The pass draws after the base material, so the base look is kept.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `outline_color` | vec4 | source_color | (0.04, 0.03, 0.07, 1) | Colour of the outline. |
| `thickness` | float | hint_range(0.0, 0.2) | 0.015 | Push distance along the normal in object units (before distance scaling). |
| `distance_scaling` | float | hint_range(0.0, 1.0) | 0.6 | 0 keeps a fixed width in object units; 1 scales the width with view distance. |
| `max_thickness` | float | hint_range(0.0, 0.5) | 0.08 | Upper limit of the push distance after scaling. |

## Inputs

- A mesh with smooth normals and an existing base material; set `material.tres` as that material's `next_pass`.

## Output

The mesh with a solid dark contour around its silhouette and along outer edges.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Hard-edged meshes (split normals, for example a BoxMesh) show gaps at the corners because each face moves along its own normal; use smoothed normals for those. Width is in object units, so non-uniform scale changes it. Inner creases are not outlined. The hull can poke through nearby geometry.

## Technique

- Inverted hull (back-face extrusion along normals)
- View-distance width compensation
