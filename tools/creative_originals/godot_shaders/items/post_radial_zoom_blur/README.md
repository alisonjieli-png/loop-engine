# Radial zoom blur toward a point

Each pixel averages samples taken along the line from itself toward the zoom centre, covering a share `strength` of the distance. Pixels near the centre get almost no blur and edges get the most, the look of a camera zooming during the exposure. A per-pixel hash offsets the samples so banding turns into fine noise.

## When to use it

Use it for speed boosts, dashes, impacts, teleport and warp moments, and dramatic focus pulls (animate `strength`).

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_radial_zoom_blur/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_radial_zoom_blur/post_radial_zoom_blur.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `center_x` | float | hint_range(0.0, 1.0) | 0.5 | Horizontal position of the zoom centre (0 to 1). |
| `center_y` | float | hint_range(0.0, 1.0) | 0.5 | Vertical position of the zoom centre (0 to 1). |
| `strength` | float | hint_range(0.0, 0.5) | 0.12 | Share of the distance to the centre each streak covers. |
| `samples` | int | hint_range(2, 48) | 20 | Samples along each streak. |
| `clear_radius` | float | hint_range(0.0, 1.0) | 0.15 | Radius around the centre that stays sharp. |
| `streak_boost` | float | hint_range(0.0, 1.0) | 0.15 | Brightness added to the streaks. |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene streaking outward from the middle with the centre still sharp.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Streaks only sample what is on screen, so content entering from off screen does not streak in. Very high strength with few samples shows stepping. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Radial blur by sampling toward a centre
- Per-pixel jittered sample offsets
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
