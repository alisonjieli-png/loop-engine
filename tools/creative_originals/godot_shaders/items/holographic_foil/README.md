# Holographic trading card foil

Two view-dependent terms build a hue. A broad diagonal sweep over the card shifts with the tangent-space view direction, so tilting the card slides rainbow bands across it. The card is also split into tiles, each with a random grating direction; the view component along that direction offsets the hue per tile, which gives the faceted look of diffraction foil. Rare hashed cells flash white at certain angles. The rainbow is mixed over a print colour and drives metalness.

## When to use it

Use it for collectible cards, stickers, packaging, badges and UI cards shown in 3D.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/holographic_foil/`. `material.tres` loads the shader from `res://baltor/godot_shaders/holographic_foil/holographic_foil.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material_override` of a MeshInstance3D, or to one of its surface material slots.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `print_color` | vec4 | source_color | (0.12, 0.14, 0.3, 1) | Colour of the printed card under the foil. |
| `foil_strength` | float | hint_range(0.0, 1.0) | 0.8 | Mix between print colour and foil. |
| `band_frequency` | float | hint_range(0.5, 20.0) | 4.0 | Number of rainbow bands across the card. |
| `view_shift` | float | hint_range(0.0, 10.0) | 3.0 | How fast the colours move as the view angle changes. |
| `tile_count` | float | hint_range(1.0, 60.0) | 14.0 | Diffraction tiles per UV unit. |
| `tile_contrast` | float | hint_range(0.0, 1.0) | 0.5 | How strongly each tile's grating offsets the hue. |
| `sparkle_density` | float | hint_range(0.0, 1.0) | 0.15 | Share of tiny cells that sparkle. |
| `saturation` | float | hint_range(0.0, 1.0) | 0.85 | Saturation of the rainbow. |

## Inputs

- A mesh with UVs and tangents (a thin box or quad as a card).

## Output

A dark card covered in rainbow foil that shifts and glitters as it tilts.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Artistic, not a diffraction calculation. Colours depend on the view angle only, not on light positions. Tiles and sparkles are aligned to UVs and alias when the card is small on screen.

## Technique

- View-dependent hue shift in tangent space
- Per-tile grating directions from a hash
- HSV-style hue to RGB conversion
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
