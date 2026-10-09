# Hair with Kajiya-Kay shifted highlights

Hair reflects light in a cone around each strand, so highlights form bands across the strand direction. The fragment stage takes the strand direction from the V tangent (`-BINORMAL`) and a per-strand random offset from noise along U, and passes both to `light()`. There the Kajiya-Kay term uses the sine of the angle between the strand and the half vector. Two lobes are shifted along the normal by different amounts, which moves them apart along the strand: a sharp white primary and a broader secondary tinted by the hair colour.

## When to use it

Use it for hair cards and hair meshes, fur strips, anime-style hair with highlight bands, and brushed fibre materials.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/hair_strand_highlight/`. `material.tres` loads the shader from `res://baltor/godot_shaders/hair_strand_highlight/hair_strand_highlight.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `root_color` | vec4 | source_color | (0.12, 0.06, 0.03, 1) | Hair colour at UV v = 0. |
| `tip_color` | vec4 | source_color | (0.45, 0.25, 0.12, 1) | Hair colour at UV v = 1. |
| `secondary_tint` | vec4 | source_color | (0.85, 0.55, 0.3, 1) | Tint of the secondary highlight. |
| `primary_shift` | float | hint_range(-1.0, 1.0) | 0.1 | Shift of the primary highlight along the strand. |
| `secondary_shift` | float | hint_range(-1.0, 1.0) | -0.15 | Shift of the secondary highlight along the strand. |
| `primary_exponent` | float | hint_range(4.0, 512.0) | 160.0 | Sharpness of the primary highlight. |
| `secondary_exponent` | float | hint_range(4.0, 512.0) | 40.0 | Sharpness of the secondary highlight. |
| `strand_noise` | float | hint_range(0.0, 1.0) | 0.4 | Per-strand variation of the highlight position. |
| `strand_count` | float | hint_range(10.0, 2000.0) | 400.0 | Number of noise strands across U. |
| `highlight_strength` | float | hint_range(0.0, 2.0) | 0.6 | Overall highlight brightness. |

## Inputs

- Hair geometry whose UV v runs along the strands, with tangents.

## Output

A brown sphere with a bright, ragged highlight band across its strands and a warmer second band.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

No transparency, depth sorting or self-shadowing of strands: pair it with alpha-tested cards for strand silhouettes. Strand direction comes from UV layout; badly unwrapped hair gives broken bands.

## Technique

- Kajiya-Kay strand specular (1989) with two shifted lobes (after Scheuermann 2004)
- Per-strand noise jitter
- Fragment-to-light varyings
