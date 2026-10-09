# Procedural fire on a camera-facing card

The vertex stage replaces the card's rotation with the camera's, keeping its position and scale, so the quad always faces the viewer. In the fragment stage, coordinates are distorted by two scrolling noise channels, more strongly toward the top, and fractal noise rising over time gives the turbulence. A flame silhouette that narrows with height masks the result. The remaining heat value selects colours from tip red through orange to a pale core, drawn additively.

## When to use it

Use it for torches, campfires, candles, burning debris and fire on props where a particle system is too heavy or overkill.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/fire_billboard/`. `material.tres` loads the shader from `res://baltor/godot_shaders/fire_billboard/fire_billboard.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (1, 0.95, 0.6, 1) | Colour of the hottest part. |
| `mid_color` | vec4 | source_color | (1, 0.5, 0.08, 1) | Colour of the main flame body. |
| `tip_color` | vec4 | source_color | (0.6, 0.05, 0.02, 1) | Colour of the coolest edges and tips. |
| `rise_speed` | float | hint_range(0.0, 5.0) | 1.6 | Upward speed of the turbulence. |
| `noise_scale` | float | hint_range(1.0, 20.0) | 5.0 | Frequency of the turbulence. |
| `distortion` | float | hint_range(0.0, 1.0) | 0.35 | Sideways warping that grows with height. |
| `flame_width` | float | hint_range(0.1, 1.0) | 0.55 | Width of the flame at its base, in card units. |
| `flame_height` | float | hint_range(0.2, 1.5) | 0.9 | Height where the flame closes, in card units. |
| `intensity` | float | hint_range(0.0, 4.0) | 1.6 | Brightness multiplier. |

## Inputs

- A QuadMesh placed where the fire burns; its bottom edge is the base of the flame.

## Output

A flickering flame with a pale core and red tips that faces the camera from every angle.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

A single card: seen from directly above the flame flattens. Additive blending means it cannot occlude and looks weak on bright backgrounds. It casts no light; add an OmniLight3D for that.

## Technique

- Spherical billboard by replacing the modelview rotation
- Height-weighted domain distortion
- Fractional Brownian motion turbulence with a heat colour ramp
- Value noise with quintic interpolation and fractional Brownian motion
