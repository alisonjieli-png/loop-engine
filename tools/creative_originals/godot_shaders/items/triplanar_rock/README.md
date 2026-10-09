# Procedural triplanar rock with surface-gradient bump

World position is projected onto the YZ, XZ and XY planes; each projection samples a rock layer (a five-octave fBm body plus thin cracks from the crest of ridged noise). The three samples are blended with weights from the world normal raised to `blend_sharpness`, which hides the projection seams. The same blended height drives a bump mapping step that perturbs the normal with screen-space derivatives of position and height, so no tangents or UVs are needed.

## When to use it

Use it for boulders, cliffs, cave walls and greybox geometry where UVs are missing or stretched, and for scaled or procedurally generated meshes that should share one continuous texture.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/triplanar_rock/`. `material.tres` loads the shader from `res://baltor/godot_shaders/triplanar_rock/triplanar_rock.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `rock_light` | vec4 | source_color | (0.58, 0.55, 0.5, 1) | Colour of raised rock areas. |
| `rock_dark` | vec4 | source_color | (0.3, 0.28, 0.26, 1) | Colour of lower rock areas. |
| `crevice_color` | vec4 | source_color | (0.12, 0.11, 0.1, 1) | Colour of the cracks. |
| `scale` | float | hint_range(0.1, 10.0) | 1.6 | Pattern frequency per world unit. |
| `blend_sharpness` | float | hint_range(1.0, 16.0) | 6.0 | How quickly the projections switch at oblique angles. |
| `crack_amount` | float | hint_range(0.0, 1.0) | 0.5 | Visibility of the cracks. |
| `bump_strength` | float | hint_range(0.0, 4.0) | 1.2 | Strength of the normal perturbation. |
| `roughness` | float | hint_range(0.0, 1.0) | 0.9 | Surface roughness. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Grey-brown stone with darker cracks and bumpy lighting that wraps seamlessly around any shape.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

The pattern is fixed in world space: moving the object slides it through the texture (use object space for movable props). Screen-space bumps can shimmer on distant or tiny surfaces and are flat in shadow. Three projections cost three times the noise.

## Technique

- Triplanar projection with normal-power blend weights
- Bump mapping with the surface gradient from screen-space derivatives (Mikkelsen 2010)
- Value noise with quintic interpolation and fractional Brownian motion
- Ridged noise cracks
