# Jelly wobble with squash and stretch

Every `bounce_period` seconds the motion restarts and decays exponentially with `damping`. The vertical scale oscillates by `squash_amount` around the base of the mesh, and the horizontal scale changes by the inverse square root so volume stays roughly constant. Upper vertices also sway sideways with the square of their height, so the base stays planted. The body is glossy and partly transparent at its centre, with a soft emissive core and backlight.

## When to use it

Use it for slimes, jellies, puddings, bouncy pickups and cartoon creatures. Drive it from a script by replacing `TIME` with a uniform if each impact should start its own bounce.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/jelly_wobble/`. `material.tres` loads the shader from `res://baltor/godot_shaders/jelly_wobble/jelly_wobble.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `jelly_color` | vec4 | source_color | (0.35, 0.9, 0.45, 0.82) | Body colour; alpha sets the opacity seen head-on. |
| `core_color` | vec4 | source_color | (0.85, 1, 0.6, 1) | Colour of the inner glow. |
| `bounce_period` | float | hint_range(0.3, 5.0) | 1.6 | Seconds between bounces. |
| `squash_amount` | float | hint_range(0.0, 0.5) | 0.18 | Largest vertical squash as a fraction of height. |
| `wobble_amount` | float | hint_range(0.0, 0.5) | 0.12 | Largest sideways sway at the top, in object units. |
| `wobble_frequency` | float | hint_range(1.0, 30.0) | 11.0 | Oscillation speed of squash and sway. |
| `damping` | float | hint_range(0.0, 10.0) | 3.0 | How quickly each bounce settles. |
| `object_height` | float | hint_range(0.1, 5.0) | 1.0 | Height of the mesh in object units (the demo capsule is 1). |
| `gloss` | float | hint_range(0.0, 1.0) | 0.9 | Glossiness of the surface. |

## Inputs

- A mesh centred on its origin; set `object_height` to its height so the base stays planted.

## Output

A green translucent blob that bounces, squashes and sways back to rest every 1.6 seconds.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Normals are not updated for the deformation, so lighting is slightly off at full squash. The bounce is a timed loop, not a physics response. Transparency means it is not depth sorted against other transparent objects.

## Technique

- Exponentially damped oscillation
- Volume-preserving squash and stretch
- Height-weighted vertex sway
