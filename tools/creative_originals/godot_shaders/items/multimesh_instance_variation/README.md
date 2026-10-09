# Per-instance variation for MultiMesh crowds

Every value comes from hashing `INSTANCE_ID` with a different salt through the MurmurHash3 finalizer, so no per-instance data needs to be uploaded. The vertex stage stretches each instance's height around its base, adds a sine bob with a per-instance phase, and computes a colour by rotating the base colour's hue around the grey axis and scaling its brightness. The fragment stage applies that colour.

## When to use it

Use it for crowds of props, forests of pillars or crystals, city blocks, audience members, crop fields and any MultiMesh where identical copies look artificial.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/multimesh_instance_variation/`. `material.tres` loads the shader from `res://baltor/godot_shaders/multimesh_instance_variation/multimesh_instance_variation.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `base_color` | vec4 | source_color | (0.25, 0.6, 0.85, 1) | Colour that instance hues vary around. |
| `hue_variation` | float | hint_range(0.0, 1.0) | 0.35 | Range of hue rotation as a share of the full circle. |
| `brightness_variation` | float | hint_range(0.0, 1.0) | 0.3 | Range of brightness variation. |
| `height_variation` | float | hint_range(0.0, 2.0) | 0.8 | Range of height scaling. |
| `bob_height` | float | hint_range(0.0, 1.0) | 0.12 | Height of the bobbing motion in object units. |
| `bob_speed` | float | hint_range(0.0, 10.0) | 2.0 | Speed of the bobbing motion. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.6 | Surface roughness. |

## Inputs

- A MultiMeshInstance3D; meshes should have their base near object y = -0.25 (or edit `base` in the shader).

## Output

A field of blue, teal and violet boxes of different heights bobbing out of step.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Variation is tied to the instance index, so reordering instances changes their looks. INSTANCE_ID is 0 for a plain MeshInstance3D, so all copies look the same there. Normals are not adjusted for the height stretch (fine for boxes and columns).

## Technique

- Hashed INSTANCE_ID per-instance randomness (MurmurHash3 finalizer)
- Hue rotation about the grey axis (Rodrigues rotation)
- Per-instance phase animation
