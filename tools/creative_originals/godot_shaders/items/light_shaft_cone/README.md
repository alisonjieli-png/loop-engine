# Fake volumetric light cone with dust

The beam is an open cone drawn additively without writing depth. The facing ratio is high across the middle of the cone as seen by the camera and low at its sides, so raising it to `edge_softness` gives soft beam edges that read as a volume. Brightness decays exponentially along the cone's V coordinate (from the apex). Slowly falling 3D noise specks add dust. Where the cone passes into the floor or an object, the depth gap shrinks and the beam fades out instead of clipping.

## When to use it

Use it for spotlights in fog, light through windows, stage lights, lighthouse beams and torch cones, where real volumetric fog is unavailable (the Compatibility and Mobile renderers) or too costly.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/light_shaft_cone/`. `material.tres` loads the shader from `res://baltor/godot_shaders/light_shaft_cone/light_shaft_cone.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `depth_texture` | sampler2D | hint_depth_texture, filter_nearest |  | Scene depth buffer (filled by Godot). |
| `beam_color` | vec4 | source_color | (1, 0.92, 0.7, 1) | Colour of the light. |
| `intensity` | float | hint_range(0.0, 4.0) | 0.9 | Brightness of the beam. |
| `edge_softness` | float | hint_range(0.1, 8.0) | 2.5 | Exponent of the facing ratio; higher narrows the visible core. |
| `length_falloff` | float | hint_range(0.0, 4.0) | 1.4 | Exponential fade along the beam. |
| `dust_amount` | float | hint_range(0.0, 1.0) | 0.5 | Visibility of drifting dust specks. |
| `dust_scale` | float | hint_range(5.0, 200.0) | 60.0 | Frequency of the dust noise. |
| `dust_speed` | float | hint_range(0.0, 1.0) | 0.05 | Falling speed of the dust. |
| `contact_fade` | float | hint_range(0.01, 2.0) | 0.4 | Depth gap in metres over which the beam fades into geometry. |

## Inputs

- An open cone mesh (a CylinderMesh with a small top radius and no caps) with V running from the apex.
- Optional: a SpotLight3D with the same aim to light the scene.

## Output

A warm, soft-edged shaft of light with floating dust that fades where it reaches the floor and statue.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Not a light: it does not illuminate anything. It ignores occluders inside the cone (no shadowed shafts). Additive, so it is invisible on bright backgrounds. Seen from inside the cone it looks flat.

## Technique

- Facing ratio volume approximation
- Exponential falloff along the beam
- Soft depth contact fade
- Value noise with quintic interpolation and fractional Brownian motion dust
