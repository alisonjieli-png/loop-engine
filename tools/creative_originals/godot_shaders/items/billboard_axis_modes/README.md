# Billboard modes: spherical or upright cylindrical

The vertex stage rebuilds the card's model-view matrix. Spherical mode takes all three axes from the camera's rotation, so the card faces the viewer from any angle. Cylindrical mode keeps the world Y axis as the card's up and turns only around it toward the camera, so a tree seen from above stays upright instead of lying down. Both keep the node's position and scale. The fragment stage applies an alpha cut-out texture and can bend the normal toward world up so cards light like vegetation, not like flat walls.

## When to use it

Use it for tree and bush impostors, characters drawn as cards, signs, glows and distant props; cylindrical for anything that stands on the ground.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/billboard_axis_modes/`. `material.tres` loads the shader from `res://baltor/godot_shaders/billboard_axis_modes/billboard_axis_modes.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `card_texture` | sampler2D | source_color, hint_default_white, filter_linear_mipmap |  | Card image with alpha; the default is a procedural round canopy. |
| `tint` | vec4 | source_color | (1, 1, 1, 1) | Colour multiplier. |
| `mode` | int | hint_range(0, 1) | 1 | 0 spherical (fully facing), 1 cylindrical (upright around world Y). |
| `alpha_cutoff` | float | hint_range(0.0, 1.0) | 0.5 | Alpha below which pixels are discarded. |
| `shade_as_upright` | bool | none | true | Blend the normal toward world up for softer foliage lighting. |

Godot has no hint for `bool` uniforms; they show as a checkbox.

## Inputs

- Card textures with alpha, and quads whose origin sits at the base for cylindrical mode (the demo uses `center_offset`).

## Output

Round green tree cards standing upright and turning to face the camera as it moves.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Cards rotate in the vertex stage, so frustum culling and shadows use the unrotated mesh bounds; give nodes a margin. Shadow maps render the card facing the light camera, not the main camera. Cylindrical mode degenerates when the camera is exactly above the card.

## Technique

- Spherical billboard from the inverse view rotation
- Axis-locked cylindrical billboard
- Alpha cut-out with bent normals
