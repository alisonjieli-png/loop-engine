# Box-projected decal from the depth buffer

The material sits on a unit BoxMesh scaled to the decal's volume and draws its back faces without a depth test, so its pixels cover everything inside the box from any viewpoint. Each pixel rebuilds the scene's view position from the depth buffer, converts it to world and then to the box's local space; points outside the unit cube are discarded. The local X and Z become decal UVs. A normal rebuilt from screen derivatives of the world position fades the decal on surfaces steep to the box's up axis, and edges fade near the box faces. The default artwork is a striped hazard disc, multiplied by an optional texture.

## When to use it

Use it for floor markings, bullet holes, scorch marks, graffiti, puddle stains and level design decals that must wrap over uneven floors and props (especially in the Compatibility renderer, where Godot's Decal node is limited).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/depth_decal_projector/`. `material.tres` loads the shader from `res://baltor/godot_shaders/depth_decal_projector/depth_decal_projector.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `decal_texture` | sampler2D | source_color, hint_default_white, filter_linear |  | Optional image multiplied with the emblem (white by default). |
| `decal_color` | vec4 | source_color | (0.95, 0.75, 0.1, 1) | Main emblem colour. |
| `accent_color` | vec4 | source_color | (0.08, 0.08, 0.08, 1) | Colour of the ring and stripes. |
| `opacity` | float | hint_range(0.0, 1.0) | 0.9 | Overall decal opacity. |
| `angle_fade` | float | hint_range(0.0, 1.0) | 0.4 | Facing ratio below which the decal fades on steep surfaces. |
| `edge_fade` | float | hint_range(0.0, 0.5) | 0.05 | Fade distance near the box faces, in box units. |
| `stripe_count` | int | hint_range(0, 24) | 10 | Number of hazard stripes across the disc (0 removes them). |
| `ring_width` | float | hint_range(0.0, 0.5) | 0.12 | Width of the outer ring as a share of the radius. |

## Inputs

- A unit BoxMesh node scaled and rotated to the decal volume; its local Y is the projection axis.
- Optional: a decal image for `decal_texture`.

## Output

A yellow and black hazard disc painted across the floor and wrapping onto the crate inside the box.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Projects onto every opaque surface in the box, including moving characters; filter with layers if needed. Transparent objects are not in the depth buffer. The decal does not receive lighting (unshaded). Reconstructed normals are flat per pixel quad and can flicker at depth discontinuities.

## Technique

- Deferred (screen-space) decal by depth reconstruction into box space
- Normal from derivatives of the reconstructed position
- Procedural emblem
