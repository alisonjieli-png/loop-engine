# Cutaway along a world plane with solid caps

The plane is given by two angles and an offset along its normal, in world space. Fragments in front of the plane are discarded. Back faces are drawn, so where a closed mesh is cut open the inside surface shows; those back-facing pixels get a flat cap colour and a normal facing back along the plane, which reads as a solid cross section. Pixels near the plane on both sides glow in `edge_color`. An optional sweep moves the plane back and forth.

## When to use it

Use it for cross sections of machines, buildings and anatomy, x-ray inspection tools, level editors that cut walls, and reveal or build-up effects.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/clip_plane_cutaway/`. `material.tres` loads the shader from `res://baltor/godot_shaders/clip_plane_cutaway/clip_plane_cutaway.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `albedo` | vec4 | source_color | (0.35, 0.55, 0.85, 1) | Colour of the outer surface. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.45 | Roughness of the outer surface. |
| `cap_color` | vec4 | source_color | (0.9, 0.3, 0.25, 1) | Colour of the cut inside surfaces. |
| `edge_color` | vec4 | source_color | (1, 0.85, 0.4, 1) | Colour of the glow along the cut. |
| `plane_pitch_degrees` | float | hint_range(-90.0, 90.0) | 0.0 | Tilt of the plane normal up or down. |
| `plane_yaw_degrees` | float | hint_range(-180.0, 180.0) | 35.0 | Direction of the plane normal around Y. |
| `plane_offset` | float | hint_range(-10.0, 10.0) | 0.0 | Distance of the plane from the world origin along its normal. |
| `edge_width` | float | hint_range(0.0, 0.2) | 0.02 | Width of the edge glow in metres. |
| `sweep_speed` | float | hint_range(0.0, 2.0) | 0.0 | Speed of the back-and-forth sweep; 0 keeps the plane still. |
| `sweep_range` | float | hint_range(0.0, 10.0) | 0.5 | Distance the sweep travels each way. |

## Inputs

- Closed meshes (open meshes show their real back faces as caps). Several objects can share the material and are cut by the same plane.

## Output

A sphere and ring sliced open diagonally with red cut faces, a glowing seam and the inner core visible.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Caps are the inside of the mesh, not new geometry: overlapping inner surfaces show through each other and the cap shading is flat. Discard disables some depth optimizations. Shadows are cut by the same plane.

## Technique

- World-space plane clipping with discard
- Back faces as cross-section caps
- Edge distance glow
