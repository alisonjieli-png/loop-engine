# Radial chromatic aberration

For each pixel the offset from the centre sets the direction and, raised to `falloff_power`, the size of a shift. Red is sampled outward and blue inward along that direction at several steps and averaged, while green stays in place. Averaging the steps turns the shift into a smooth spectral smear rather than three offset copies.

## When to use it

Use it for camera realism, impact and damage feedback (animate `strength`), dreamy or glitchy scenes and sci-fi visors.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/post_chromatic_aberration/`. `material.tres` loads the shader from `res://baltor/godot_shaders/post_chromatic_aberration/post_chromatic_aberration.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Add a MeshInstance3D with a QuadMesh of size 2 x 2 anywhere in the scene, assign `material.tres` to its `material_override` and set its `extra_cull_margin` to the maximum (16384) so it is never culled. The vertex shader stretches the quad over the whole screen, and the pass draws after opaque geometry.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | The rendered scene behind the pass (filled by Godot). |
| `strength` | float | hint_range(0.0, 0.05) | 0.012 | Largest channel shift at the corners, in screen UV units. |
| `falloff_power` | float | hint_range(0.5, 4.0) | 2.0 | How quickly the shift grows toward the edges. |
| `samples` | int | hint_range(1, 16) | 6 | Samples per channel; more gives a smoother smear. |
| `center_x` | float | hint_range(0.0, 1.0) | 0.5 | Horizontal centre of the effect (0 to 1). |
| `center_y` | float | hint_range(0.0, 1.0) | 0.5 | Vertical centre of the effect (0 to 1). |

## Inputs

- A MeshInstance3D with a 2 x 2 QuadMesh, `material.tres` as its material override and a large extra cull margin, as in `demo.tscn`.

## Output

The scene with red and blue fringes along edges that widen toward the corners.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Three channels only, so the fringe is red and blue rather than a full spectrum. Edges of the screen clamp the samples. The pass reads Godot's screen texture after opaque geometry, so transparent objects drawn after it are not processed and its order among other transparent passes is not controlled.

## Technique

- Radial per-channel UV offset
- Multi-sample averaging along the offset
