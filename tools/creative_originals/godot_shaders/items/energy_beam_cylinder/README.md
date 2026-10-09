# Energy beam with scrolling core and jitter

The beam draws additively, so it only adds light. The facing ratio is highest along the middle of the cylinder as seen from the camera, and raising it to `core_sharpness` gives a hot white core fading to the beam colour at the sides. Value noise and evenly spaced pulses scroll along the V coordinate. The ends fade over `end_fade` of the length, and the vertex stage scales the radius with fast noise for a crackling jitter.

## When to use it

Use it for lasers, tractor beams, lightning-gun bolts, energy tethers and charging effects.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/energy_beam_cylinder/`. `material.tres` loads the shader from `res://baltor/godot_shaders/energy_beam_cylinder/energy_beam_cylinder.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (1, 0.95, 0.85, 1) | Colour of the beam centre. |
| `beam_color` | vec4 | source_color | (1, 0.3, 0.15, 1) | Colour toward the beam edges. |
| `intensity` | float | hint_range(0.0, 6.0) | 2.0 | Overall brightness. |
| `core_sharpness` | float | hint_range(0.5, 10.0) | 3.0 | How narrow the bright core is. |
| `scroll_speed` | float | hint_range(-10.0, 10.0) | 3.0 | Speed of the noise and pulses along the beam. |
| `noise_scale` | float | hint_range(1.0, 40.0) | 10.0 | Frequency of the noise along the beam. |
| `pulse_spacing` | float | hint_range(0.05, 1.0) | 0.25 | Distance between pulses in V units. |
| `pulse_strength` | float | hint_range(0.0, 2.0) | 0.6 | Brightness of the pulses. |
| `end_fade` | float | hint_range(0.0, 0.5) | 0.08 | Length of the fade at each end in V units. |
| `jitter` | float | hint_range(0.0, 0.2) | 0.03 | Radial wobble of the vertices. |

## Inputs

- An open CylinderMesh (or any tube) with V running along its length.

## Output

A glowing orange beam with a white core and bright pulses travelling along it.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Additive, so it is invisible on white backgrounds. Thin beams far from the camera alias without MSAA. The core is computed per pixel from the facing ratio, so very low radial segment counts show facets.

## Technique

- Facing ratio core brightness
- Scrolling value noise and periodic pulses
- Vertex radial jitter
- Value noise with quintic interpolation and fractional Brownian motion
