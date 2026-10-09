# Pen hatching driven by lighting

`light()` computes the Lambert tone with shadows and compares it with four thresholds. Below each threshold another layer of parallel lines is added: diagonal, the opposite diagonal, horizontal, then a denser vertical layer, so tone builds up the way an illustrator cross-hatches. Lines are measured along rotated UV coordinates and anti-aliased with screen-space derivatives. Inked pixels receive no light, so they show the dark ambient term on paper-coloured albedo.

## When to use it

Use it for sketchbook, comic, engraving and blueprint-like illustrated styles, and for tutorial or storybook scenes.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/lit_hatching/`. `material.tres` loads the shader from `res://baltor/godot_shaders/lit_hatching/lit_hatching.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `paper_color` | vec4 | source_color | (0.96, 0.94, 0.88, 1) | Colour of the paper (the albedo). |
| `line_density` | float | hint_range(10.0, 400.0) | 90.0 | Lines per UV unit. |
| `line_width` | float | hint_range(0.05, 0.9) | 0.35 | Line width as a share of the line spacing. |
| `level_1` | float | hint_range(0.0, 1.0) | 0.8 | Tone below which the first diagonal layer appears. |
| `level_2` | float | hint_range(0.0, 1.0) | 0.55 | Tone below which the crossing diagonal layer appears. |
| `level_3` | float | hint_range(0.0, 1.0) | 0.32 | Tone below which horizontal lines appear. |
| `level_4` | float | hint_range(0.0, 1.0) | 0.15 | Tone below which dense vertical lines appear. |
| `ink_strength` | float | hint_range(0.0, 1.0) | 0.92 | How dark the ink makes the lit term (1 removes it). |

## Inputs

- A mesh with reasonably even UVs; keep the environment ambient light low so shadows stay dark.

## Output

Paper-white shapes shaded with layers of crossing ink lines that thicken toward the shadow side.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Lines follow UVs, so seams and stretched UVs show in the strokes. Each light adds its own hatching. Ambient light is added unhatched. Lines alias into moire when UV density is far higher than screen pixels.

## Technique

- Tonal hatching layers by light thresholds
- Derivative anti-aliased procedural lines
- Custom light function
