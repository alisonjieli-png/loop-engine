# Velvet lighting with grazing sheen

Velvet looks dark where it faces you and bright where fibres stand at grazing angles. `light()` uses a softened wrap diffuse for the dark core, then adds a sheen in `sheen_color` that grows with `1 - N.V` raised to `sheen_power` and with how much the surface faces the light. Light coming from behind the object adds a back-scatter term at the silhouette. Faint value noise varies the core colour like pile.

## When to use it

Use it for velvet, plush toys, upholstery, curtains, moss, peach skin and soft costumes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/velvet_sheen/`. `material.tres` loads the shader from `res://baltor/godot_shaders/velvet_sheen/velvet_sheen.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `core_color` | vec4 | source_color | (0.35, 0.03, 0.12, 1) | Colour of the fabric facing the viewer. |
| `sheen_color` | vec4 | source_color | (1, 0.55, 0.7, 1) | Colour of the grazing sheen. |
| `sheen_power` | float | hint_range(0.5, 8.0) | 2.2 | Exponent of the sheen; higher keeps it at the silhouette. |
| `sheen_strength` | float | hint_range(0.0, 3.0) | 1.2 | Brightness of the sheen. |
| `back_scatter` | float | hint_range(0.0, 2.0) | 0.5 | Extra sheen when lit from behind. |
| `diffuse_softness` | float | hint_range(0.0, 1.0) | 0.5 | Wrap of the diffuse core. |
| `fiber_noise` | float | hint_range(0.0, 1.0) | 0.15 | Variation of the core colour. |

## Inputs

None. The effect is procedural and needs no texture or script.

## Output

Deep raspberry velvet shapes with pink, glowing edges where the surface turns away.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Empirical lighting, not a microfibre model; not energy conserving. Sheen also appears on surfaces facing away from the light at grazing angles through the back-scatter term. Environment light adds a plain term.

## Technique

- Grazing-angle sheen lobe
- Wrapped diffuse
- Back-scatter at the silhouette
