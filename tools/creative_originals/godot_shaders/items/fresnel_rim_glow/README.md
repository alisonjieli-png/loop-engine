# Emissive Fresnel rim glow with pulse

The facing ratio `N.V` is 1 where the surface faces the camera and 0 at the silhouette. `pow(1 - N.V, glow_power)` turns it into a rim mask whose width the power controls. The mask scales an emission colour, so the glow shows in darkness and does not depend on lights. `inner_glow` adds a small uniform glow and a sine of `TIME` modulates the whole effect.

## When to use it

Use it to mark interactable or collectable objects, energy cores, spirits and sci-fi props, or as a selection highlight that works under any lighting.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/fresnel_rim_glow/`. `material.tres` loads the shader from `res://baltor/godot_shaders/fresnel_rim_glow/fresnel_rim_glow.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `base_color` | vec4 | source_color | (0.08, 0.1, 0.16, 1) | Albedo of the lit surface under the glow. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.35 | Surface roughness. |
| `metallic` | float | hint_range(0.0, 1.0) | 0.2 | Surface metalness. |
| `glow_color` | vec4 | source_color | (0.2, 0.85, 1, 1) | Colour of the emitted rim. |
| `glow_power` | float | hint_range(0.5, 8.0) | 2.5 | Exponent of the rim curve; higher keeps the glow closer to the edge. |
| `glow_intensity` | float | hint_range(0.0, 8.0) | 3.0 | Emission multiplier of the rim. |
| `inner_glow` | float | hint_range(0.0, 1.0) | 0.08 | Uniform glow added over the whole surface. |
| `pulse_speed` | float | hint_range(0.0, 10.0) | 2.0 | Pulse frequency in radians per second. |
| `pulse_depth` | float | hint_range(0.0, 1.0) | 0.35 | How far the pulse dims the glow; 0 disables it. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A dark surface with a bright coloured edge that breathes slowly.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

An empirical Fresnel-style curve, not a physical Fresnel term. Flat faces seen head-on get no rim, so boxes glow only at grazing angles. Without the Glow post effect the emission does not bloom past the silhouette.

## Technique

- Facing ratio rim mask (1 - N.V raised to a power)
- Emission-only highlight
