# Screen-space glass refraction with dispersion

Reading the screen texture makes the object draw after the opaque scene with a copy of what is behind it. The shader offsets the lookup by the view-space normal, scaled by an approximate thickness that is larger at the edges, which bends the background like a lens. The red and blue channels use slightly larger and smaller offsets for dispersion. A mip level read (`frost`) blurs the view for frosted glass. A Fresnel term fades toward a reflection colour at grazing angles.

## When to use it

Use it for glass balls, bottles, windows, lenses, water drops, crystals and frosted panels in scenes without screen-space reflections.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/glass_refraction/`. `material.tres` loads the shader from `res://baltor/godot_shaders/glass_refraction/glass_refraction.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `screen_texture` | sampler2D | hint_screen_texture, filter_linear_mipmap |  | Copy of the opaque scene behind the object (filled by Godot). |
| `tint` | vec4 | source_color | (0.85, 0.95, 1, 1) | Colour the transmitted light takes on. |
| `refraction_strength` | float | hint_range(0.0, 0.3) | 0.08 | Screen-space offset of the refraction. |
| `dispersion` | float | hint_range(0.0, 1.0) | 0.25 | Extra offset difference between the colour channels. |
| `frost` | float | hint_range(0.0, 6.0) | 0.0 | Mip level of the screen read; higher blurs more. |
| `fresnel_power` | float | hint_range(0.5, 8.0) | 4.0 | Exponent of the edge reflection curve. |
| `fresnel_strength` | float | hint_range(0.0, 1.0) | 0.6 | Strength of the edge reflection. |
| `reflection_color` | vec4 | source_color | (0.9, 0.95, 1, 1) | Colour shown at grazing angles in place of a real reflection. |
| `thickness_tint` | float | hint_range(0.0, 1.0) | 0.35 | How much the tint depends on the apparent thickness. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

A clear sphere that magnifies and bends the scene behind it with coloured fringes at the edges.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Screen-space: objects outside the screen or in front of the glass cannot be refracted, and edges of the screen clamp. Other transparent objects are not in the screen copy. The reflection is a flat colour, not the environment. Unshaded, so scene lights add no highlight.

## Technique

- Screen texture refraction offset by view-space normals
- Per-channel offsets for chromatic dispersion
- Mip level blur for frosted glass
- Fresnel-style edge blend
