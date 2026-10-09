# Screen-space ambient occlusion from depth only

The pass rebuilds the view-space position of each pixel from depth and its normal from screen derivatives of that position. It projects a world-space radius to pixels at that depth and gathers points on a golden-angle disc, rotated per pixel by a hash to break up banding. Each neighbour that sits above the surface (positive angle to the normal beyond `bias`) and inside the radius adds occlusion; the average darkens the scene colour toward a tint.

## When to use it

Use it for contact shadows and crease darkening in the Compatibility and Mobile renderers, or as a stylized AO pass with a coloured tint.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_depth_ao_approx/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_depth_ao_approx/post_depth_ao_approx.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | The scene depth buffer (filled by Godot). |
| `radius` | float | hint_range(0.05, 3.0) | 0.45 | World radius in metres searched for occluders. |
| `intensity` | float | hint_range(0.0, 4.0) | 1.4 | Strength of the darkening. |
| `samples` | int | hint_range(4, 32) | 16 | Samples per pixel. |
| `bias` | float | hint_range(0.0, 0.3) | 0.03 | Angle bias that avoids self-occlusion on flat surfaces. |
| `max_pixels` | float | hint_range(4.0, 128.0) | 48.0 | Cap on the screen radius for objects very close to the camera. |
| `shadow_tint` | vec4 | source_color | (0, 0, 0.05, 1) | Colour occluded areas move toward. |
| `show_occlusion` | bool | none | false | Show the occlusion term alone in greyscale. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with soft darkening where objects meet the floor and in corners.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Applied after lighting, so it also darkens directly lit areas. Noisy without a blur pass (the per-pixel rotation trades banding for grain). Derivative normals break at object edges and give thin halos there. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Screen-space ambient occlusion with normal-oriented hemisphere test
- Golden-angle disc with per-pixel rotation
- Normals from derivatives of reconstructed position
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
