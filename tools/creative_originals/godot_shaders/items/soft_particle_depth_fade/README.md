# Soft particle card with depth fade

For each pixel of the card the shader reads the depth of the opaque scene behind it and subtracts the card's own depth. Where the gap is smaller than `fade_distance`, alpha ramps down to zero, so a puff that intersects the floor or a crate fades into it instead of showing a straight cut. Alpha also fades between two distances from the camera, so cards do not pop when the camera moves through them. The sprite texture (a soft radial gradient by default) supplies colour and base alpha.

## When to use it

Use it for smoke, dust, fog sprites, glows and any alpha-blended card or particle that touches geometry.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/soft_particle_depth_fade/`. `material.tres` loads the shader from `res://baltor/godot_shaders/soft_particle_depth_fade/soft_particle_depth_fade.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `sprite` | sampler2D | source_color, hint_default_white, filter_linear |  | Sprite image with alpha; the default is a procedural soft disc. |
| `tint` | vec4 | source_color | (0.8, 0.82, 0.88, 0.8) | Colour and opacity multiplier. |
| `fade_distance` | float | hint_range(0.01, 4.0) | 0.6 | Gap in metres over which the card fades into geometry. |
| `camera_fade_near` | float | hint_range(0.0, 5.0) | 0.3 | Camera distance in metres where the card is invisible. |
| `camera_fade_far` | float | hint_range(0.0, 10.0) | 0.8 | Camera distance in metres where the camera fade ends. |
| `fade_power` | float | hint_range(0.25, 4.0) | 1.0 | Curve of the depth fade; above 1 keeps the edge harder. |

## Inputs

- Optional: a sprite texture with alpha for `sprite` (the bundled material uses a procedural one).

## Output

Soft grey puffs that blend smoothly into the floor and the crate where they intersect.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Only opaque geometry is in the depth buffer; cards do not soften against each other. The gap is measured along the view axis. Unshaded: combine with `smoke_billboard` ideas for lit puffs. Cards are sorted per object.

## Technique

- Soft particles by scene depth difference
- Camera-distance fade
- Depth reconstruction with INV_PROJECTION_MATRIX
