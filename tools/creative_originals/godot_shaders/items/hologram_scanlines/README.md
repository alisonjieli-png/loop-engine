# Hologram with scanlines, flicker and slice glitches

The material is unshaded and additive, so it only brightens what is behind it. Scanlines are a sine of world height, scrolled by `TIME` and sharpened toward a square wave. A Fresnel term brightens the outline; back faces are drawn too (`cull_disabled`) so the inside shows through. Two hash streams drive glitches: in the vertex stage, random horizontal slices of the mesh jump sideways for one time slot, and in the fragment stage the whole hologram dips in brightness at random frames.

## When to use it

Use it for holographic projections, sci-fi interfaces in 3D, ghost previews of objects being placed, and transmissions from characters.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/hologram_scanlines/`. `material.tres` loads the shader from `res://baltor/godot_shaders/hologram_scanlines/hologram_scanlines.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `holo_color` | vec4 | source_color | (0.25, 0.85, 1, 1) | Colour of the hologram light. |
| `line_density` | float | hint_range(10.0, 400.0) | 110.0 | Scanlines per world unit of height (times 2 pi). |
| `line_speed` | float | hint_range(-4.0, 4.0) | 0.5 | Scroll speed of the scanlines in world units per second. |
| `line_sharpness` | float | hint_range(0.0, 1.0) | 0.6 | Blend from soft sine lines (0) to hard square lines (1). |
| `line_strength` | float | hint_range(0.0, 1.0) | 0.4 | Brightness the scanlines add. |
| `rim_power` | float | hint_range(0.5, 8.0) | 2.0 | Exponent of the edge glow; higher keeps it thinner. |
| `base_strength` | float | hint_range(0.0, 1.0) | 0.18 | Uniform brightness over the whole surface. |
| `flicker_amount` | float | hint_range(0.0, 1.0) | 0.3 | Brightness drop on random flicker frames. |
| `glitch_offset` | float | hint_range(0.0, 0.3) | 0.05 | Largest sideways jump of a glitching slice, in object units. |
| `glitch_rate` | float | hint_range(0.0, 20.0) | 5.0 | Glitch time slots per second. |
| `glitch_bands` | float | hint_range(1.0, 40.0) | 10.0 | Number of horizontal slices per world unit of height. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A translucent cyan figure with moving horizontal lines, a bright outline, flicker and slice jumps.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Additive blending cannot darken, so the hologram is invisible against white. The slice glitch moves vertices along the object X axis and needs enough vertical subdivisions to cut cleanly. Not depth sorted against other transparent objects.

## Technique

- Additive unshaded transparency
- World-space sine scanlines
- Facing ratio rim
- Hashed time slots for flicker and vertex glitches
