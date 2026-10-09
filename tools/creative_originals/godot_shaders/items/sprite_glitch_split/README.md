# Sprite glitch with RGB split and slice jumps

Time is cut into slots. In each slot a hash picks some horizontal slices to jump sideways by a random amount. The red channel is sampled to one side and the blue to the other by a split that also varies per slot, and the alpha becomes the maximum of the three channel alphas so split edges show coloured fringes outside the original shape. A few thin rows flash bright.

## When to use it

Use it for hacked or corrupted characters, holograms, spawn-in effects, cyberpunk UI and damage states.

## Install

Copy this folder into your project at `res://baltor/godot_shaders/sprite_glitch_split/`. `material.tres` loads the shader from `res://baltor/godot_shaders/sprite_glitch_split/sprite_glitch_split.gdshader`, and `demo.tscn` loads `material.tres` from the same folder, so the files work without edits at that path. To use another folder, change the `path=` lines in `material.tres` and `demo.tscn`. The Python files, `component.json`, `verification/` and `preview.png` are not needed at run time.

Assign `material.tres` to the `material` property of a CanvasItem: a Sprite2D, TextureRect, ColorRect, Label or any other 2D node.

Open `demo.tscn` to see the effect.

## Uniforms

| Uniform | Type | Hint | Default | Effect |
|---|---|---|---|---|
| `split` | float | hint_range(0.0, 0.1) | 0.02 | Base horizontal offset between red and blue channels in UV units. |
| `slice_strength` | float | hint_range(0.0, 0.3) | 0.08 | Largest sideways jump of a glitching slice in UV units. |
| `slice_count` | float | hint_range(2.0, 64.0) | 18.0 | Number of horizontal slices. |
| `glitch_rate` | float | hint_range(0.0, 30.0) | 8.0 | Glitch time slots per second. |
| `glitch_share` | float | hint_range(0.0, 1.0) | 0.25 | Share of slices that jump in each slot. |
| `band_flash` | float | hint_range(0.0, 1.0) | 0.3 | Brightness of random thin scan bands. |

## Inputs

- A Sprite2D (or other textured CanvasItem) with transparent space around its shape, assigned to the node as usual.

## Output

The sprite torn into shifted slices with red and blue fringes.

## Renderer status

Compiled and rendered in Godot 4.7.2 with the Compatibility renderer (OpenGL 3 on Mesa llvmpipe under Xvfb). The check found no shader or script error, and the demo scene rendered a frame that differs from the same scene without the shader. Forward+ and Mobile were not run. The shader is written for Godot 4.3 and later; only 4.7.2 was run.

## Limits

Displacement stays inside the texture rectangle. Glitch timing is global (all sprites with the material glitch together).

## Technique

- Time-slotted hashed slice displacement
- Per-channel offset sampling
- MurmurHash3 32-bit finalizer over prime-combined lattice coordinates as a hash
